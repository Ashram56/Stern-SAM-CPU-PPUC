"""Minimal KiCad 9 schematic writer: places library symbols, wires, labels and
power symbols, and packs blocks of parts onto a page. Used to create the first
draft of the SAM CPU schematic; the .kicad_sch files are the source of truth
afterwards."""
import math, uuid as _uuid, os, sys, copy
sys.path.insert(0, os.path.dirname(__file__))
from sexp import Sym, dump, find, find1, fmtnum
import libs

GRID = 1.27
NS = _uuid.UUID('6c1f3c57-6c2e-4d4b-9a7e-5a3d1f0c2b11')
def uid(*key):
    return str(_uuid.uuid5(NS, '/'.join(str(k) for k in key)))

def snap(v, g=GRID):
    return round(round(v / g) * g, 4)

POWER_NETS = {'GND': 'power:GND', '+5V': 'power:+5V', '+3V3': 'power:+3V3',
              '+12V': 'power:+12V', '-12V': 'power:-12V', '+1V1': 'power:+1V1'}
# direction vectors in screen coordinates (y down)
DIRS = {'L': (-1, 0), 'R': (1, 0), 'U': (0, -1), 'D': (0, 1)}

class SymDef:
    _cache = {}
    def __init__(self, lib_id):
        lib, name = lib_id.split(':')
        self.lib_id = lib_id
        self.sexp = libs.get_symbol(lib, name)
        self.pins = libs.pins(self.sexp)
        self.props = {p[1]: p for p in find(self.sexp, 'property')}
        self.is_power = find1(self.sexp, 'power') is not None
        # body bbox from graphics (lib coords, y up)
        xs, ys = [], []
        for sub in find(self.sexp, 'symbol'):
            for g in sub[2:]:
                if not isinstance(g, list): continue
                if g[0] == 'rectangle':
                    for k in ('start', 'end'):
                        e = find1(g, k); xs.append(float(e[1])); ys.append(float(e[2]))
                elif g[0] in ('polyline', 'bezier'):
                    for p in find(find1(g, 'pts'), 'xy'):
                        xs.append(float(p[1])); ys.append(float(p[2]))
                elif g[0] == 'circle':
                    c = find1(g, 'center'); r = float(find1(g, 'radius')[1])
                    xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
        for p in self.pins:
            xs.append(p['x']); ys.append(p['y'])
        self.bbox = (min(xs), min(ys), max(xs), max(ys)) if xs else (-2, -2, 2, 2)
    @classmethod
    def get(cls, lib_id):
        if lib_id not in cls._cache: cls._cache[lib_id] = SymDef(lib_id)
        return cls._cache[lib_id]
    def units(self):
        return sorted({p['unit'] for p in self.pins if p['unit'] > 0}) or [1]

def rot(x, y, r):
    """rotate lib vector (y up) CCW by r degrees, return screen offset (y down)."""
    a = math.radians(r)
    rx = x * math.cos(a) - y * math.sin(a)
    ry = x * math.sin(a) + y * math.cos(a)
    return (round(rx, 4), round(-ry, 4))

def pin_outward(angle, r):
    """screen direction pointing away from the body for a pin with lib angle."""
    # pin angle = direction from connection point toward body (lib coords)
    a = (angle + r) % 360
    return {0: 'L', 180: 'R', 90: 'D', 270: 'U'}[a]

def is_two_pin(part):
    return part.lib_id.startswith('Device:') and len({p['number'] for p in part.sd.pins}) == 2

def two_pin_vertical(part):
    ps = [rot(p['x'], p['y'], part.rot) for p in part.sd.pins]
    return abs(ps[0][0] - ps[1][0]) < 0.01

class Part:
    def __init__(self, ref, lib_id, value, nets, footprint=None, unit=1, rotation=0,
                 props=None, mirror=None, dnp=False, fields=None):
        self.ref, self.lib_id, self.value = ref, lib_id, value
        self.nets = dict(nets)  # pin number -> net name ('NC' for no connect)
        self.sd = SymDef.get(lib_id)
        fpprop = self.sd.props.get('Footprint')
        self.footprint = footprint if footprint is not None else (fpprop[2] if fpprop else '')
        self.unit, self.rot = unit, rotation
        self.props = props or {}
        self.dnp = dnp
        self.x = self.y = 0.0
    def unit_pins(self):
        return [p for p in self.sd.pins if p['unit'] in (0, self.unit)]
    def pin_pos(self, number):
        for p in self.unit_pins():
            if p['number'] == str(number):
                dx, dy = rot(p['x'], p['y'], self.rot)
                return (round(self.x + dx, 4), round(self.y + dy, 4))
        raise KeyError(f'{self.ref} has no pin {number}')
    def pin(self, number):
        for p in self.unit_pins():
            if p['number'] == str(number): return p
        raise KeyError(f'{self.ref} has no pin {number}')

class Sheet:
    def __init__(self, name, filename, title, ports_dir=None, paper=None, comments=()):
        self.name, self.filename, self.title = name, filename, title
        self.items = []      # raw sexp items
        self.parts = []      # placed Part objects
        self.blocks = []
        self.ports_dir = ports_dir or {}
        self.paper = paper
        self.comments = comments
        self.port_nets = set()
        self.texts = []
        self.pwr_count = 0
    def block(self, title=None):
        b = Block(self, title)
        self.blocks.append(b)
        return b

class Block:
    """A group of parts and drawing items in local coordinates, packed later."""
    def __init__(self, sheet, title):
        self.sheet, self.title = sheet, title
        self.parts, self.wires, self.labels, self.powers, self.ncs, self.juncs = [], [], [], [], [], []
        self.xs, self.ys = [], []
        self.stub = 2.54
    # ---- placement -------------------------------------------------
    def place(self, part, x, y, auto=True, elbow='auto'):
        if elbow == 'auto':
            elbow = 'R' if is_two_pin(part) else None
        part.x, part.y = x, y
        self.parts.append(part)
        sd = part.sd
        corners = [rot(sd.bbox[0], sd.bbox[1], part.rot), rot(sd.bbox[2], sd.bbox[3], part.rot)]
        for cx, cy in corners:
            self.xs.append(x + cx); self.ys.append(y + cy)
        if is_two_pin(part) and two_pin_vertical(part):
            self.xs.append(x + 9)
        if auto:
            self.autoconnect(part, elbow=elbow)
        return part
    def autoconnect(self, part, skip=(), elbow='R'):
        done = {}
        for p in part.unit_pins():
            num = p['number']
            if num in skip: continue
            net = part.nets.get(num)
            if net is None:
                raise ValueError(f'{part.ref} pin {num} ({p["name"]}) has no net')
            pos = part.pin_pos(num)
            if pos in done:
                if done[pos] != net:
                    raise ValueError(f'{part.ref}: stacked pins at {pos} on different nets {done[pos]} / {net}')
                continue
            done[pos] = net
            d = pin_outward(p['angle'], part.rot)
            self.terminate(pos, d, net, elbow=elbow)
    def terminate(self, pos, d, net, stub=None, elbow='R'):
        """end a connection point with a stub + label / power symbol / no-connect."""
        if net == 'NC':
            self.ncs.append(pos); return
        stub = self.stub if stub is None else stub
        dx, dy = DIRS[d]
        end = (round(pos[0] + dx * stub, 4), round(pos[1] + dy * stub, 4))
        if stub:
            self.wire(pos, end)
        if net in POWER_NETS:
            self.power(end, net, d)
        elif d in 'UD' and elbow:
            e2 = (round(end[0] + DIRS[elbow][0] * 2.54, 4), end[1])
            self.wire(end, e2)
            self.label(e2, net, elbow)
        else:
            self.label(end, net, d)
    def wire(self, a, b):
        if a == b: return
        self.wires.append((a, b))
        self.xs += [a[0], b[0]]; self.ys += [a[1], b[1]]
    def path(self, *pts):
        for a, b in zip(pts, pts[1:]): self.wire(a, b)
    def junction(self, p):
        self.juncs.append(p)
    def label(self, p, net, d):
        self.labels.append((p, net, d))
        w = len(net) * 1.1 + 3
        dx, dy = DIRS[d]
        self.xs += [p[0], p[0] + dx * w]; self.ys += [p[1] + (dy * w if dy else 0), p[1] - 1.5, p[1] + 1.5]
    def power(self, p, net, d):
        self.powers.append((p, net, d))
        dx, dy = DIRS[d]
        self.xs += [p[0] - 2, p[0] + 2, p[0] + dx * 6]; self.ys += [p[1] - 2, p[1] + 2, p[1] + dy * 6]
    def bbox(self):
        return (min(self.xs), min(self.ys), max(self.xs), max(self.ys))

# ------------------------------------------------------------------------
def effects(size=1.27, justify=None, hide=False):
    e = [Sym('effects'), [Sym('font'), [Sym('size'), size, size]]]
    if justify: e.append([Sym('justify')] + [Sym(j) for j in justify.split()])
    if hide: e.append([Sym('hide'), Sym('yes')])
    return e

LABEL_ANGLE = {'R': 0, 'U': 90, 'L': 180, 'D': 270}

class Design:
    def __init__(self, project, title, rev, company, date):
        self.project, self.title, self.rev, self.company, self.date = project, title, rev, company, date
        self.sheets = []
        self.root_uuid = uid(project, 'root')
        self.pwr_n = 0
        self.flag_n = 0
    def sheet(self, *a, **k):
        s = Sheet(*a, **k); self.sheets.append(s); return s

    # --- packing ----------------------------------------------------------
    def pack(self, sheet):
        margin, gap = 15.24, 7.62
        sizes = {'A4': (297, 210), 'A3': (420, 297), 'A2': (594, 420), 'A1': (841, 594)}
        order = ['A3', 'A2', 'A1']
        if sheet.paper: order = [sheet.paper]
        for paper in order:
            W, H = sizes[paper]
            x, y, rowh = margin, margin + 7.62 + len(sheet.comments) * 2.54, 0
            ok = True; pos = []
            for b in sheet.blocks:
                x0, y0, x1, y1 = b.bbox()
                w, h = x1 - x0, y1 - y0 + (5.08 if b.title else 0)
                if x + w > W - margin and x > margin:
                    x = margin; y += rowh + gap; rowh = 0
                pos.append((b, x - x0, y - y0 + (5.08 if b.title else 0)))
                x += w + gap; rowh = max(rowh, h)
                if x - gap > W - margin or y + rowh > H - 40:  # keep title block clear
                    ok = False
            if ok: break
        sheet.paper = paper
        for b, ox, oy in pos:
            ox, oy = snap(ox, 2.54), snap(oy, 2.54)
            b.offset = (ox, oy)
    # --- output -------------------------------------------------------------
    def lib_symbols(self, sheet):
        ids = {}
        for b in sheet.blocks:
            for p in b.parts: ids[p.lib_id] = p.sd
            for _, net, _ in b.powers: ids[POWER_NETS[net]] = SymDef.get(POWER_NETS[net])
        if getattr(sheet, 'flags', None): ids['power:PWR_FLAG'] = SymDef.get('power:PWR_FLAG')
        out = [Sym('lib_symbols')]
        for lid in sorted(ids):
            s = copy.deepcopy(ids[lid].sexp)
            s[1] = lid
            out.append(s)
        return out

    def sym_instance(self, sheet, lib_id, ref, value, x, y, r, unit, footprint, pins, props, sheetpath, key,
                     hide_ref=False, dnp=False, mirror=None):
        sd = SymDef.get(lib_id)
        two_pin = None
        if lib_id.startswith('Device:') and len({p['number'] for p in sd.pins}) == 2:
            ps = [rot(p['x'], p['y'], r) for p in sd.pins]
            two_pin = 'V' if abs(ps[0][0] - ps[1][0]) < 0.01 else 'H'
        e = [Sym('symbol'), [Sym('lib_id'), lib_id], [Sym('at'), x, y, r]]
        if mirror: e.append([Sym('mirror'), Sym(mirror)])
        e += [[Sym('unit'), unit], [Sym('exclude_from_sim'), Sym('no')], [Sym('in_bom'), Sym('no' if ref.startswith('#') else 'yes')],
              [Sym('on_board'), Sym('no' if ref.startswith('#') else 'yes')], [Sym('dnp'), Sym('yes' if dnp else 'no')],
              [Sym('uuid'), uid(key)]]
        fields = {'Reference': ref, 'Value': value, 'Footprint': footprint,
                  'Datasheet': sd.props['Datasheet'][2] if 'Datasheet' in sd.props else '',
                  'Description': sd.props['Description'][2] if 'Description' in sd.props else ''}
        fields.update(props)
        for name, val in fields.items():
            lp = sd.props.get(name)
            if lp is not None:
                at = find1(lp, 'at'); px, py, pa = float(at[1]), float(at[2]), float(at[3])
                hidden = any(isinstance(z, list) and z[0] == 'hide' for z in find1(lp, 'effects')) or \
                         any(z == 'hide' for z in find1(lp, 'effects'))
                just = find1(find1(lp, 'effects'), 'justify')
                just = ' '.join(str(j) for j in just[1:]) if just else None
            else:
                px, py, pa, hidden, just = 0, 0, 0, True, None
            if name in ('Footprint', 'Datasheet', 'Description') or name not in ('Reference', 'Value'):
                hidden = True
            if name == 'Reference' and hide_ref: hidden = True
            dx, dy = rot(px, py, r)
            ang = pa  # field angles are stored relative to the symbol orientation
            if name == 'Value' and lib_id.startswith('power:') and r in (90, 270):
                ang = 90
                just = 'left'  # rotation of field + symbol flips it back where needed
            if name in ('Reference', 'Value') and two_pin is not None:
                ang = 90 if r in (90, 270) else 0
                if two_pin == 'V':
                    dx, dy, just = 2.54, (-1.27 if name == 'Reference' else 1.27), 'left'
                else:
                    dx, dy, just = 0, (-2.794 if name == 'Reference' else 2.794), None
            e.append([Sym('property'), name, val, [Sym('at'), round(x + dx, 4), round(y + dy, 4), ang],
                      effects(justify=just, hide=hidden)])
        for num in pins:
            e.append([Sym('pin'), num, [Sym('uuid'), uid(key, 'pin', num)]])
        e.append([Sym('instances'), [Sym('project'), self.project,
                  [Sym('path'), sheetpath, [Sym('reference'), ref], [Sym('unit'), unit]]]])
        return e

    def write_sheet(self, sheet, path, sheetpath, page):
        self.pack(sheet)
        items = []
        sk = sheet.filename
        n = 0
        flags = []
        for b in sheet.blocks:
            ox, oy = b.offset
            T = lambda p: (round(p[0] + ox, 4), round(p[1] + oy, 4))
            if b.title:
                x0, y0, x1, y1 = b.bbox()
                items.append([Sym('text'), b.title, [Sym('exclude_from_sim'), Sym('no')],
                              [Sym('at'), snap(x0 + ox, 1.27), snap(y0 + oy - 3.81, 1.27), 0],
                              effects(size=2.0, justify='left bottom'), [Sym('uuid'), uid(sk, 'title', b.title)]])
            for p in b.parts:
                x, y = T((p.x, p.y))
                pins = sorted({q['number'] for q in p.unit_pins()}, key=lambda s: (len(s), s))
                fp = p.footprint
                items.append(self.sym_instance(sheet, p.lib_id, p.ref, p.value, x, y, p.rot, p.unit, fp, pins,
                                               p.props, sheetpath, (sk, p.ref, p.unit), dnp=p.dnp))
            for a, c in b.wires:
                a, c = T(a), T(c)
                items.append([Sym('wire'), [Sym('pts'), [Sym('xy'), a[0], a[1]], [Sym('xy'), c[0], c[1]]],
                              [Sym('stroke'), [Sym('width'), 0], [Sym('type'), Sym('default')]],
                              [Sym('uuid'), uid(sk, 'w', a, c)]])
            for pt in b.juncs:
                pt = T(pt)
                items.append([Sym('junction'), [Sym('at'), pt[0], pt[1]], [Sym('diameter'), 0],
                              [Sym('color'), 0, 0, 0, 0], [Sym('uuid'), uid(sk, 'j', pt)]])
            for pt in b.ncs:
                pt = T(pt)
                items.append([Sym('no_connect'), [Sym('at'), pt[0], pt[1]], [Sym('uuid'), uid(sk, 'nc', pt)]])
            for pt, net, d in b.labels:
                pt = T(pt)
                ang = LABEL_ANGLE[d]
                if net in sheet.port_nets:
                    shape = sheet.ports_dir.get(net, 'bidirectional')
                    just = 'left' if ang in (0, 90) else 'right'
                    items.append([Sym('hierarchical_label'), net, [Sym('shape'), Sym(shape)],
                                  [Sym('at'), pt[0], pt[1], ang], effects(justify=just),
                                  [Sym('uuid'), uid(sk, 'hl', pt, net)]])
                else:
                    just = ('left' if ang in (0, 90) else 'right') + ' bottom'
                    items.append([Sym('label'), net, [Sym('at'), pt[0], pt[1], ang], effects(justify=just),
                                  [Sym('uuid'), uid(sk, 'l', pt, net)]])
            for pt, net, d in b.powers:
                pt = T(pt)
                lid = POWER_NETS[net]
                if net == 'GND' or net == '-12V':
                    r = {'D': 0, 'R': 90, 'U': 180, 'L': 270}[d]
                else:
                    r = {'U': 0, 'L': 90, 'D': 180, 'R': 270}[d]
                self.pwr_n += 1
                ref = '#PWR%04d' % self.pwr_n
                items.append(self.sym_instance(sheet, lid, ref, net, pt[0], pt[1], r, 1, '', ['1'], {},
                                               sheetpath, (sk, 'pwr', pt, net), hide_ref=True))
        for pt, net in getattr(sheet, 'flags', []):
            pass
        for t, (x, y) in sheet.texts:
            items.append([Sym('text'), t, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), x, y, 0],
                          effects(size=1.27, justify='left top'), [Sym('uuid'), uid(sk, 'txt', t[:40])]])
        head = [Sym('kicad_sch'), [Sym('version'), 20250114], [Sym('generator'), 'eeschema'],
                [Sym('generator_version'), '9.0'], [Sym('uuid'), self.root_uuid if sheet.filename.endswith(self.project + '.kicad_sch') else uid(sk, 'file')],
                [Sym('paper'), sheet.paper]]
        tb = [Sym('title_block'), [Sym('title'), sheet.title], [Sym('date'), self.date], [Sym('rev'), self.rev],
              [Sym('company'), self.company]]
        if sheet.comments:
            items.insert(0, [Sym('text'), '\n'.join(sheet.comments), [Sym('exclude_from_sim'), Sym('no')],
                             [Sym('at'), 15.24, 12.7, 0], effects(size=1.5, justify='left top'),
                             [Sym('uuid'), uid(sk, 'notes')]])
        head.append(tb)
        head.append(self.lib_symbols(sheet))
        doc = head + items
        return doc

def write(path, doc, root_extra=None):
    if root_extra: doc = doc + root_extra
    with open(path, 'w') as f:
        f.write(dump(doc) + '\n')

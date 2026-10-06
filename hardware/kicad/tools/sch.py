"""Schematic page builder with a small orthogonal wire router.

Parts are placed by hand (coordinates in mm). Every net that has two or more
connection points on a page is drawn as real wires between the pins; power rails
use power symbols, nets that leave the page get a global label. Nets the router
cannot draw fall back to local labels (reported, so the layout can be fixed).
"""
import heapq, math, collections, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sexp import Sym
from kigen import SymDef, Part, rot, pin_outward, uid, effects, Design
import libs

G = 1.27
def gi(v): return int(round(v / G))
def mm(n): return round(n * G, 4)

# power rails drawn with power symbols: net -> (lib symbol, hangs down?)
POWER = {'GND': ('power:GND', True), '-12V': ('power:-12V', False), '+5V': ('power:+5V', False),
         '+3V3': ('power:+3V3', False), '+12V': ('power:+12V', False), '+1V1': ('power:+1V1', False),
         '+4V5': ('power:VCC', False)}
DV = {'L': (-1, 0), 'R': (1, 0), 'U': (0, -1), 'D': (0, 1)}
OPP = {'L': 'R', 'R': 'L', 'U': 'D', 'D': 'U'}
HOR = {'L', 'R'}
LABEL_ANGLE = {'R': 0, 'U': 90, 'L': 180, 'D': 270}


def body_bbox(part):
    """graphics-only bbox of the part's unit, in screen mm (absolute)."""
    xs, ys = [], []
    for sub in [s for s in part.sd.sexp if isinstance(s, list) and s and s[0] == 'symbol']:
        u = int(sub[1].rsplit('_', 2)[1]); style = int(sub[1].rsplit('_', 2)[2])
        if style > 1 or u not in (0, part.unit): continue
        for g in sub[2:]:
            if not isinstance(g, list): continue
            pts = []
            if g[0] == 'rectangle':
                for k in ('start', 'end'):
                    e = [z for z in g if isinstance(z, list) and z[0] == k][0]; pts.append((float(e[1]), float(e[2])))
            elif g[0] in ('polyline', 'bezier'):
                pl = [z for z in g if isinstance(z, list) and z[0] == 'pts'][0]
                pts += [(float(p[1]), float(p[2])) for p in pl[1:]]
            elif g[0] == 'circle':
                c = [z for z in g if isinstance(z, list) and z[0] == 'center'][0]
                r = float([z for z in g if isinstance(z, list) and z[0] == 'radius'][0][1])
                pts += [(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)]
            elif g[0] == 'arc':
                for k in ('start', 'mid', 'end'):
                    e = [z for z in g if isinstance(z, list) and z[0] == k][0]; pts.append((float(e[1]), float(e[2])))
            for x, y in pts:
                dx, dy = rot(x, y, part.rot)
                if part.mirror == 'y': dx = -dx
                xs.append(part.x + dx); ys.append(part.y + dy)
    if not xs: return None
    return (min(xs), min(ys), max(xs), max(ys))


class Page:
    def __init__(self, name, filename, title, paper='A3', notes=()):
        self.name, self.filename, self.title, self.paper, self.notes = name, filename, title, paper, notes
        self.parts, self.ports, self.texts, self.frames = [], [], [], []
        self.label_nets = set()      # nets drawn with local labels on purpose
        self.shapes = {}
        self.stub_len = {}           # net -> power stub length override (grid units)
        self.paths = []              # (net, [(x, y) mm]) wires drawn by hand

    def add(self, part, x, y):
        part.x, part.y = round(x, 4), round(y, 4)
        self.parts.append(part)
        return part

    def port(self, net, x, y, d):
        """global label for `net` with its connection point at (x, y), text pointing d."""
        self.ports.append((net, gi(x), gi(y), d))

    def text(self, s, x, y, size=1.27):
        self.texts.append((s, x, y, size))

    def wire(self, net, pts):
        self.paths.append((net, [(gi(x), gi(y)) for x, y in pts]))

    def frame(self, title, x0, y0, x1, y1):
        self.frames.append((title, x0, y0, x1, y1))

    # ------------------------------------------------------------------ build
    def pins(self):
        out = []
        for p in self.parts:
            seen = {}
            for q in p.unit_pins():
                num = q['number']
                net = p.nets.get(num)
                if net is None:
                    raise ValueError(f'{self.name}: {p.ref} pin {num} ({q["name"]}) has no net')
                x, y = p.pin_pos(num)
                node = (gi(x), gi(y))
                if abs(mm(node[0]) - x) > 1e-3 or abs(mm(node[1]) - y) > 1e-3:
                    raise ValueError(f'{p.ref} pin {num} off grid at {x},{y}')
                if node in seen:
                    if seen[node] != net:
                        raise ValueError(f'{p.ref}: stacked pins {num} on {net} / {seen[node]}')
                    continue
                seen[node] = net
                od = pin_outward(q['angle'], p.rot)
                if p.mirror == 'y': od = {'L': 'R', 'R': 'L'}.get(od, od)
                out.append(dict(part=p, pin=q, num=num, node=node, out=od, net=net,
                                length=gi(q['length'])))
        return out

    def build(self, design, glob, sheetpath, shapes):
        self.glob = glob
        W, H = {'A4': (297, 210), 'A3': (420, 297), 'A2': (594, 420)}[self.paper]
        self.GW, self.GH = gi(W), gi(H)
        self.blocked = set()
        self.soft = set()   # text: allowed but expensive
        self.pt = {}        # node -> net (connection points: pins, wire ends, labels)
        self.hw, self.vw = {}, {}   # node -> net of a horizontal / vertical wire through it
        self.he, self.ve = {}, {}   # edge (left/top node) -> net
        self.wires = []     # (a, b, net)
        self.items = []
        self.powers = []    # (node, net, dir)
        self.labels = []    # (node, net, dir, kind)
        self.ncs = []
        self.failed = []
        sk = self.filename
        pins = self.pins()
        # ---- symbols and their field text
        self.instances = []
        for p in self.parts:
            allp = sorted({q['number'] for q in p.unit_pins()}, key=lambda s: (len(s), s))
            inst = design.sym_instance(None, p.lib_id, p.ref, p.value, p.x, p.y, p.rot, p.unit, p.footprint, allp,
                                       p.props, sheetpath, (sk, p.ref, p.unit), dnp=p.dnp, mirror=p.mirror,
                                       hide_ref=p.ref.startswith('#'))
            self.instances.append(inst)
            bb = body_bbox(p)
            if not bb:
                ps = [p.pin_pos(q['number']) for q in p.unit_pins()]
                bb = (min(x for x, _ in ps), min(y for _, y in ps), max(x for x, _ in ps), max(y for _, y in ps))
            self.block_rect(bb[0], bb[1], bb[2], bb[3])
            for prop in [z for z in inst if isinstance(z, list) and z and z[0] == 'property']:
                if any(isinstance(e, list) and e[0] == 'hide' for e in prop[4]): continue
                at = prop[3]
                self.block_text(prop[2], float(at[1]), float(at[2]), (float(at[3]) + p.rot) % 180, prop[4])
        for q in pins:
            # the pin line itself
            dx, dy = DV[q['out']]
            for k in range(1, q['length'] + 1):
                self.blocked.add((q['node'][0] - dx * k, q['node'][1] - dy * k))
        self.freepins = {q['node'] for q in pins if (q['part'].lib_id.startswith('Device:')
                         and len({z['number'] for z in q['part'].sd.pins}) == 2) or q['part'].lib_id == 'power:PWR_FLAG'}
        for q in pins:
            self.blocked.discard(q['node'])
            self.pt[q['node']] = q['net'] if q['net'] != 'NC' else ('NC', q['node'])
        # ---- no-connects
        for q in pins:
            if q['net'] == 'NC': self.ncs.append(q['node'])
        # ---- power pins: group per part side, stub + bar + one symbol
        groups = collections.defaultdict(list)
        for q in pins:
            if q['net'] in POWER:
                groups[(id(q['part']), q['out'], q['net'])].append(q)
        for (pid, d, net), qs in groups.items():
            part_pins = [z for z in pins if id(z['part']) == pid and z['out'] == d]
            axis = 1 if d in HOR else 0
            qs.sort(key=lambda z: z['node'][axis])
            runs, cur = [], [qs[0]]
            for z in qs[1:]:
                a, b = cur[-1]['node'][axis], z['node'][axis]
                between = [w for w in part_pins if a < w['node'][axis] < b and w['net'] != net]
                if b - a <= 4 and not between:
                    cur.append(z)
                else:
                    runs.append(cur); cur = [z]
            runs.append(cur)
            for run in runs:
                self.power_run(run, net, d, others=[w['node'] for w in part_pins if w['net'] != net])
        # ---- wires drawn by hand
        for net, pts in self.paths:
            for a, b in zip(pts, pts[1:]):
                nodes = self.seg_nodes(a, b)
                hor = a[1] == b[1]
                for k, n in enumerate(nodes):
                    end = n in (a, b)
                    p = self.pt.get(n)
                    bad = (p is not None and p != net) or n in self.blocked and p != net
                    other = self.hw.get(n) if hor else self.vw.get(n)
                    if other is not None and other != net: bad = True
                    if end and self.other_wire(n, net): bad = True
                    if bad:
                        raise ValueError(f'{self.name}: hand-drawn wire for {net} hits something at {mm(n[0])},{mm(n[1])} mm')
                self.add_wire(a, b, net)
        # ---- global labels (explicit ports first)
        terms = collections.defaultdict(list)   # net -> list of (node, out_dir or None)
        for q in pins:
            if q['net'] == 'NC' or q['net'] in POWER: continue
            terms[q['net']].append((q['node'], q['out']))
        for net, x, y, d in self.ports:
            self.add_label((x, y), net, d, 'global')
            terms[net].insert(0, ((x, y), OPP[d]))
        for net in list(terms):
            if (net in glob or len(terms[net]) == 1) and not any(n == net for n, *_ in self.ports):
                # stub + label on the first pin that has room
                for node, out in terms[net]:
                    if self.try_stub_label(node, out, net): break
                else:
                    self.failed.append((net, 'no room for label'))
                    self.add_label(terms[net][0][0], net, terms[net][0][1], 'global')
        # ---- route
        order = sorted(terms, key=lambda n: self.hpwl(terms[n]))
        for net in order:
            t = terms[net]
            if len(t) < 2:
                if net not in glob:
                    print(f'  {self.name}: net {net} has a single connection')
                continue
            if net in self.label_nets:
                for node, out in t:
                    if node in self.pt and self.pt[node] == net and any(l[0] == node for l in self.labels): continue
                    if not self.try_stub_label(node, out, net, kind='local'):
                        self.add_label(node, net, out, 'local')
                continue
            self.route_net(net, t)
        self.find_junctions()
        return self

    # ---------------------------------------------------------------- helpers
    def block_rect(self, x0, y0, x1, y1, into=None):
        into = self.blocked if into is None else into
        for gx in range(math.floor(x0 / G), math.ceil(x1 / G) + 1):
            for gy in range(math.floor(y0 / G), math.ceil(y1 / G) + 1):
                into.add((gx, gy))

    def block_text(self, s, x, y, ang, eff):
        w = len(s) * 1.05 + 0.3
        just = [z for z in eff if isinstance(z, list) and z[0] == 'justify']
        just = [str(j) for j in just[0][1:]] if just else []
        if ang % 180 == 0:
            x0 = x if 'left' in just else (x - w if 'right' in just else x - w / 2)
            y0 = y - 1.9 if 'bottom' in just else (y if 'top' in just else y - 0.8)
            self.block_rect(x0 + 0.2, y0 + 0.2, x0 + w - 0.2, y0 + 1.4, self.soft)
        else:
            self.block_rect(x - 0.6, y - w, x + 0.6, y + w, self.soft)

    def hpwl(self, t):
        xs = [n[0] for n, _ in t]; ys = [n[1] for n, _ in t]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    def free(self, node):
        return node not in self.blocked and node not in self.pt and node not in self.hw and node not in self.vw

    def add_wire(self, a, b, net):
        if a == b: return
        self.wires.append((a, b, net))
        if a[1] == b[1]:
            y = a[1]
            for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1): self.hw[(x, y)] = net
            for x in range(min(a[0], b[0]), max(a[0], b[0])): self.he[(x, y)] = net
        else:
            x = a[0]
            for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1): self.vw[(x, y)] = net
            for y in range(min(a[1], b[1]), max(a[1], b[1])): self.ve[(x, y)] = net
        self.pt[a] = net; self.pt[b] = net

    def add_label(self, node, net, d, kind):
        self.labels.append((node, net, d, kind))
        self.pt[node] = net
        n = len(net) * 1.27 + (9.0 if kind == 'global' else 0.6)
        dx, dy = DV[d]
        x, y = mm(node[0]), mm(node[1])
        if d in HOR:
            xe = x + dx * n
            self.block_rect(min(x, xe) + (0.6 if d == 'R' else 0), y - 1.0, max(x, xe) - (0.6 if d == 'L' else 0), y + 1.0)
        else:
            ye = y + dy * n
            self.block_rect(x - 1.0, min(y, ye) + (0.6 if d == 'D' else 0), x + 1.0, max(y, ye) - (0.6 if d == 'U' else 0))
        self.blocked.discard(node)

    def try_stub_label(self, node, out, net, stub=4, kind='global'):
        for st in (stub, stub - 2, stub + 2, stub + 4):
            if self._stub_label(node, out, net, st, kind): return True
        return False

    def _stub_label(self, node, out, net, stub, kind):
        dx, dy = DV[out]
        nodes = [(node[0] + dx * k, node[1] + dy * k) for k in range(1, stub + 1)]
        if not all(self.free(n) for n in nodes): return False
        # room for the label text
        end = nodes[-1]
        n = gi(len(net) * 1.27 + 9.0) + 1
        room = [(end[0] + dx * k, end[1] + dy * k) for k in range(1, n)]
        if not all(self.free(r) and r not in self.soft for r in room): return False
        self.add_wire(node, end, net)
        self.add_label(end, net, out, kind)
        return True

    def power_run(self, run, net, d, stub=2, others=()):
        stub = self.stub_len.get(net, stub)
        dx, dy = DV[d]
        ends = []
        for q in run:
            n = q['node']; e = (n[0] + dx * stub, n[1] + dy * stub)
            self.add_wire(n, e, net); ends.append(e)
        if len(ends) > 1:
            for a, b in zip(ends, ends[1:]): self.add_wire(a, b, net)
        down = POWER[net][1]
        if d in ('U', 'D'):
            anchor = ends[len(ends) // 2]; sd = d
        else:
            # pins facing sideways: GND hangs below the run, +V rails point up from it
            ends.sort(key=lambda e: e[1])
            anchor = ends[-1] if down else ends[0]
            sd = 'D' if down else 'U'
            near = [o for o in others if 0 < (o[1] - anchor[1]) * (1 if sd == 'D' else -1) <= 8]
            if near or not all(self.free((anchor[0] + DV[sd][0] * k, anchor[1] + DV[sd][1] * k)) for k in range(1, 4)):
                anchor, sd = (ends[0] if len(ends) == 1 else anchor), d
        self.powers.append((anchor, net, sd))
        ax, ay = anchor
        ddx, ddy = DV[sd]
        across = (-2, -1, 0, 1, 2) if sd in ('U', 'D') else (-1, 0, 1)
        for k in range(1, 5):
            for s in across:
                n = (ax + ddx * k + (s if ddy else 0), ay + ddy * k + (s if ddx else 0))
                self.blocked.add(n)

    # ---------------------------------------------------------------- router
    def other_wire(self, node, net):
        h = self.hw.get(node); v = self.vw.get(node)
        return (h is not None and h != net) or (v is not None and v != net)

    def route_net(self, net, terms):
        orig = {n: o for n, o in terms}
        terms = [(n, None if n in self.freepins else o) for n, o in terms]
        drawn = set()
        for a, b, n in self.wires:
            if n == net: drawn |= set(self.seg_nodes(a, b))
        on = [t for t in terms if t[0] in drawn]
        if on and terms[0][0] not in drawn:
            terms.remove(on[0]); terms.insert(0, on[0])
        root, rout = terms[0]
        tree = {root}
        tree_pins = {root: rout}
        # already drawn wires of this net (label stubs) belong to the tree
        for a, b, n in self.wires:
            if n == net:
                tree |= set(self.seg_nodes(a, b))
        pending = {node: out for node, out in terms[1:] if node not in tree}
        while pending:
            path = self.search(net, tree, tree_pins, pending)
            if path is None:
                # fall back to labels for whatever is left
                kind = 'global' if net in self.glob else 'local'
                for node, out in pending.items():
                    self.failed.append((net, node))
                    self.add_label(node, net, orig[node], kind)
                if not any(l[1] == net for l in self.labels if l[0] in tree):
                    self.add_label(root, net, orig[root], kind)
                return
            self.commit(path, net)
            tree |= set(path)
            del pending[path[-1]]

    def seg_nodes(self, a, b):
        if a[1] == b[1]:
            return [(x, a[1]) for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1)]
        return [(a[0], y) for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1)]

    def edge_net(self, a, b):
        if a[1] == b[1]: return self.he.get((min(a[0], b[0]), a[1]))
        return self.ve.get((a[0], min(a[1], b[1])))

    def search(self, net, tree, tree_pins, targets, margin=30):
        xs = [n[0] for n in list(tree) + list(targets)]; ys = [n[1] for n in list(tree) + list(targets)]
        x0, x1 = max(2, min(xs) - margin), min(self.GW - 2, max(xs) + margin)
        y0, y1 = max(2, min(ys) - margin), min(self.GH - 2, max(ys) + margin)
        tl = list(targets)
        tx0, tx1 = min(t[0] for t in tl), max(t[0] for t in tl)
        ty0, ty1 = min(t[1] for t in tl), max(t[1] for t in tl)
        def h(n):
            x, y = n
            return (tx0 - x if x < tx0 else (x - tx1 if x > tx1 else 0)) + (ty0 - y if y < ty0 else (y - ty1 if y > ty1 else 0))
        heap = []; best = {}; prev = {}
        cnt = 0
        for s in tree:
            if s in tree_pins:
                if any(self.edge_net(s, (s[0] + DV[d][0], s[1] + DV[d][1])) == net for d in DV): continue
                dirs = [tree_pins[s]] if tree_pins[s] else list(DV)
            else:
                if self.other_wire(s, net): continue
                dirs = list(DV)
            for d in dirs:
                st = (s, 'S' + d)
                best[st] = 0; heapq.heappush(heap, (h(s), 0, cnt, st)); cnt += 1
        BEND, CROSS, ODD = 3.0, 4.0, 0.6
        while heap:
            f, g, _, st = heapq.heappop(heap)
            if best.get(st, 1e18) < g: continue
            node, d = st
            if d.startswith('S'):
                dirs = [d[1]]; d = None
            elif d.startswith('T'):
                continue
            else:
                dirs = [d] if self.other_wire(node, net) else [z for z in DV if z != OPP[d]]
            for nd in dirs:
                b = (node[0] + DV[nd][0], node[1] + DV[nd][1])
                if not (x0 <= b[0] <= x1 and y0 <= b[1] <= y1): continue
                en = self.edge_net(node, b)
                if en is not None: continue
                cost = 1.0
                if nd in HOR and b[1] % 2: cost += ODD
                if nd not in HOR and b[0] % 2: cost += ODD
                if d is not None and nd != d:
                    if self.other_wire(node, net): continue
                    cost += BEND
                if b in targets:
                    if targets[b] is not None and OPP[targets[b]] != nd: continue
                    if self.other_wire(b, net): continue
                    ng = g + cost
                    nst = (b, 'T')
                    if ng < best.get(nst, 1e18):
                        best[nst] = ng; prev[nst] = st
                        heapq.heappush(heap, (ng, ng, cnt, nst)); cnt += 1
                    continue
                if b in self.blocked or b in tree: continue
                if b in self.soft: cost += 6
                p = self.pt.get(b)
                if p is not None: continue
                if self.other_wire(b, net):
                    # crossing: only perpendicular
                    if nd in HOR and self.hw.get(b) is not None: continue
                    if nd not in HOR and self.vw.get(b) is not None: continue
                    cost += CROSS
                ng = g + cost
                nst = (b, nd)
                if ng < best.get(nst, 1e18):
                    best[nst] = ng; prev[nst] = st
                    heapq.heappush(heap, (ng + h(b), ng, cnt, nst)); cnt += 1
        # pick best target
        cands = [(best[(t, 'T')], t) for t in targets if (t, 'T') in best]
        if not cands:
            if margin < 80: return self.search(net, tree, tree_pins, targets, margin=80)
            return None
        _, t = min(cands)
        st = (t, 'T'); path = [t]
        while st in prev:
            st = prev[st]; path.append(st[0])
        path.reverse()
        # drop the repeated start
        out = [path[0]]
        for n in path[1:]:
            if n != out[-1]: out.append(n)
        return out

    def commit(self, path, net):
        # split at bends
        pts = [path[0]]
        for i in range(1, len(path) - 1):
            a, b, c = path[i - 1], path[i], path[i + 1]
            if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]): pts.append(b)
        pts.append(path[-1])
        for a, b in zip(pts, pts[1:]): self.add_wire(a, b, net)

    def find_junctions(self):
        deg = collections.Counter()
        for a, b, n in self.wires:
            deg[a] += 1; deg[b] += 1
        mid = collections.Counter()
        for a, b, n in self.wires:
            for x in self.seg_nodes(a, b)[1:-1]:
                if x in deg: mid[x] += 2
        pinnodes = set()
        for p in self.parts:
            for q in p.unit_pins():
                x, y = p.pin_pos(q['number']); pinnodes.add((gi(x), gi(y)))
        self.juncs = []
        for node, k in deg.items():
            tot = k + mid[node] + (1 if node in pinnodes else 0)
            if tot >= 3: self.juncs.append(node)

    # ---------------------------------------------------------------- output
    def emit(self, design, sheetpath, glob_shapes):
        sk = self.filename
        items = list(self.instances)
        for a, b, net in self.wires:
            A, B = (mm(a[0]), mm(a[1])), (mm(b[0]), mm(b[1]))
            items.append([Sym('wire'), [Sym('pts'), [Sym('xy'), A[0], A[1]], [Sym('xy'), B[0], B[1]]],
                          [Sym('stroke'), [Sym('width'), 0], [Sym('type'), Sym('default')]], [Sym('uuid'), uid(sk, 'w', A, B)]])
        for n in self.juncs:
            items.append([Sym('junction'), [Sym('at'), mm(n[0]), mm(n[1])], [Sym('diameter'), 0], [Sym('color'), 0, 0, 0, 0],
                          [Sym('uuid'), uid(sk, 'j', n)]])
        for n in self.ncs:
            items.append([Sym('no_connect'), [Sym('at'), mm(n[0]), mm(n[1])], [Sym('uuid'), uid(sk, 'nc', n)]])
        for node, net, d, kind in self.labels:
            x, y = mm(node[0]), mm(node[1]); ang = LABEL_ANGLE[d]
            just = 'left' if ang in (0, 90) else 'right'
            if kind == 'global':
                shape = glob_shapes.get((self.name, net), 'bidirectional')
                w = len(net) * 1.27 + 3.4
                dx, dy = DV[d]
                items.append([Sym('global_label'), net, [Sym('shape'), Sym(shape)], [Sym('at'), x, y, ang],
                              [Sym('fields_autoplaced'), Sym('yes')], effects(justify=just),
                              [Sym('uuid'), uid(sk, 'gl', node, net)],
                              [Sym('property'), 'Intersheetrefs', '${INTERSHEET_REFS}',
                               [Sym('at'), round(x + dx * w, 4), round(y + dy * w, 4), ang],
                               effects(size=1.27, justify=just)]])
            else:
                items.append([Sym('label'), net, [Sym('at'), x, y, ang], effects(justify=just + ' bottom'),
                              [Sym('uuid'), uid(sk, 'l', node, net)]])
        for i, (node, net, d) in enumerate(self.powers):
            lid, down = POWER[net]
            if down: r = {'D': 0, 'R': 90, 'U': 180, 'L': 270}[d]
            else: r = {'U': 0, 'L': 90, 'D': 180, 'R': 270}[d]
            items.append(design.sym_instance(None, lid, '#PWR%05d' % (getattr(self, 'pwr_base', 0) + i + 1), net, mm(node[0]), mm(node[1]), r, 1, '',
                                             ['1'], {}, sheetpath, (sk, 'pwr', node, net), hide_ref=True))
        for title, x0, y0, x1, y1 in self.frames:
            items.append([Sym('rectangle'), [Sym('start'), x0, y0], [Sym('end'), x1, y1],
                          [Sym('stroke'), [Sym('width'), 0.2], [Sym('type'), Sym('dash')], [Sym('color'), 120, 120, 120, 1]],
                          [Sym('fill'), [Sym('type'), Sym('none')]], [Sym('uuid'), uid(sk, 'fr', title)]])
            items.append([Sym('text'), title, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), x0 + 1.27, y0 + 1.27, 0],
                          effects(size=1.8, justify='left top'), [Sym('uuid'), uid(sk, 'frt', title)]])
        for s, x, y, size in self.texts:
            items.append([Sym('text'), s, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), x, y, 0],
                          effects(size=size, justify='left top'), [Sym('uuid'), uid(sk, 'txt', s[:40], x, y)]])
        if self.notes:
            items.append([Sym('text'), '\n'.join(self.notes), [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), 15.24, 15.24, 0],
                          effects(size=1.5, justify='left top'), [Sym('uuid'), uid(sk, 'notes')]])
        ids = {p.lib_id: p.sd for p in self.parts}
        for _, net, _ in self.powers: ids[POWER[net][0]] = SymDef.get(POWER[net][0])
        import copy
        libsyms = [Sym('lib_symbols')]
        for lid in sorted(ids):
            s = copy.deepcopy(ids[lid].sexp); s[1] = lid; libsyms.append(s)
        head = [Sym('kicad_sch'), [Sym('version'), 20250114], [Sym('generator'), 'eeschema'], [Sym('generator_version'), '9.0'],
                [Sym('uuid'), uid(sk, 'file')], [Sym('paper'), self.paper],
                [Sym('title_block'), [Sym('title'), self.title], [Sym('date'), design.date], [Sym('rev'), design.rev],
                 [Sym('company'), design.company]], libsyms]
        return head + items

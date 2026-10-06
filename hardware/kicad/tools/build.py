"""Build the KiCad project: python3 build.py <outdir>"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
OUT = sys.argv[1]
sys.argv = [sys.argv[0], OUT]
import design
from kigen import *

D = design.D
os.makedirs(OUT, exist_ok=True)

# ---- which nets cross sheets -> hierarchical ports
use = collections.defaultdict(set)
for s in D.sheets:
    for b in s.blocks:
        for _, net, _ in b.labels:
            use[net].add(s.name)
for s in D.sheets:
    s.port_nets = {n for n, ss in use.items() if s.name in ss and len(ss) > 1}
# nets that appear only once anywhere are probably typos
cnt = collections.Counter()
for s in D.sheets:
    for b in s.blocks:
        for _, net, _ in b.labels: cnt[net] += 1
single = [n for n, c in cnt.items() if c == 1]
if single:
    print('WARNING single-use labels:', single)

# ---- sub sheets
root_uuid = D.root_uuid
sheet_syms = []
x, y = 25.4, 30.48
colw, maxh = 0, 0
pageno = 2
root_items = []
placed = []
for s in D.sheets:
    suid = uid('sheet', s.filename)
    path = f'/{root_uuid}/{suid}'
    doc = D.write_sheet(s, os.path.join(OUT, s.filename), path, pageno)
    write(os.path.join(OUT, s.filename), doc)
    ports = sorted(s.port_nets)
    placed.append((s, suid, ports, pageno))
    pageno += 1

# ---- root sheet layout: sheets in columns, ports split left / right
items = []
W, H = 594, 420
col_x = [35.56, 134.62, 233.68, 332.74]
cy = [38.1] * 4
ci = 0
for s, suid, ports, page in placed:
    half = (len(ports) + 1) // 2
    left, right = ports[:half], ports[half:]
    w = 50.8
    h = max(len(left), len(right), 3) * 2.54 + 5.08
    # choose column with the lowest fill
    ci = min(range(4), key=lambda i: cy[i])
    sx, sy = col_x[ci], cy[ci]
    cy[ci] += h + 20.32
    e = [Sym('sheet'), [Sym('at'), sx, sy], [Sym('size'), w, h], [Sym('exclude_from_sim'), Sym('no')],
         [Sym('in_bom'), Sym('yes')], [Sym('on_board'), Sym('yes')], [Sym('dnp'), Sym('no')],
         [Sym('fields_autoplaced'), Sym('yes')],
         [Sym('stroke'), [Sym('width'), 0.1524], [Sym('type'), Sym('solid')]],
         [Sym('fill'), [Sym('color'), 0, 0, 0, 0.0]], [Sym('uuid'), suid],
         [Sym('property'), 'Sheetname', s.name, [Sym('at'), sx, round(sy - 0.7116, 4), 0], effects(justify='left bottom')],
         [Sym('property'), 'Sheetfile', s.filename, [Sym('at'), sx, round(sy + h + 0.5884, 4), 0], effects(justify='left top')]]
    for side, lst in (('L', left), ('R', right)):
        for i, net in enumerate(lst):
            py = round(sy + 5.08 + i * 2.54, 4)
            px = sx if side == 'L' else round(sx + w, 4)
            shape = s.ports_dir.get(net, 'bidirectional')
            e.append([Sym('pin'), net, Sym(shape), [Sym('at'), px, py, 180 if side == 'L' else 0],
                      [Sym('uuid'), uid('sheetpin', s.filename, net)], effects(justify='left' if side == 'L' else 'right')])
            ex = px - 2.54 if side == 'L' else px + 2.54
            items.append([Sym('wire'), [Sym('pts'), [Sym('xy'), px, py], [Sym('xy'), ex, py]],
                          [Sym('stroke'), [Sym('width'), 0], [Sym('type'), Sym('default')]], [Sym('uuid'), uid('rw', s.filename, net)]])
            ang = 180 if side == 'L' else 0
            items.append([Sym('label'), net, [Sym('at'), ex, py, ang], effects(justify=('right' if side == 'L' else 'left') + ' bottom'),
                          [Sym('uuid'), uid('rl', s.filename, net)]])
    e.append([Sym('instances'), [Sym('project'), D.project, [Sym('path'), f'/{root_uuid}', [Sym('page'), str(page)]]]])
    items.append(e)

notes = ('SAM CPU replacement board, draft 0.1, drawn from docs/ARCHITECTURE.md.\n'
         'A Raspberry Pi 4 / CM4 runs PinMAME + ppuc. The RP2354B drives the original IO power driver board on J9\n'
         'and scans the switches. Connector names and pinouts follow the original CPU/Sound board 520-5246-00.\n'
         'Licence: CERN-OHL-S v2.')
items.append([Sym('text'), notes, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), 25.4, 12.7, 0],
              effects(size=1.8, justify='left top'), [Sym('uuid'), uid('rootnote')]])
root = [Sym('kicad_sch'), [Sym('version'), 20250114], [Sym('generator'), 'eeschema'], [Sym('generator_version'), '9.0'],
        [Sym('uuid'), root_uuid], [Sym('paper'), 'A3'],
        [Sym('title_block'), [Sym('title'), D.title], [Sym('date'), D.date], [Sym('rev'), D.rev], [Sym('company'), D.company]],
        [Sym('lib_symbols')]] + items + [
        [Sym('sheet_instances'), [Sym('path'), '/', [Sym('page'), '1']]], [Sym('embedded_fonts'), Sym('no')]]
write(os.path.join(OUT, D.project + '.kicad_sch'), root)

pro = {"meta": {"filename": D.project + ".kicad_pro", "version": 3},
       "schematic": {"drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0},
                     "legacy_lib_dir": "", "legacy_lib_list": []},
       "sheets": [[root_uuid, "Root"]] + [[suid, s.name] for s, suid, _, _ in placed],
       "text_variables": {}}
json.dump(pro, open(os.path.join(OUT, D.project + '.kicad_pro'), 'w'), indent=2)
print('pages:', {s.name: s.paper for s in D.sheets})
print('ports:', {s.name: len(s.port_nets) for s in D.sheets})

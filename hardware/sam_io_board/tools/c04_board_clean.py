"""Change 04 (2026-10-07), runs between the 'remove' and 'add' phases of c03_board_update.py, on
the board file text (pcbnew's SWIG proxies break once items are removed, so no pcbnew here):
- removes tracks and vias of nets that no longer exist;
- removes track ends left dangling by the removed pads: only an end lying on a removed pad, or
  on the end of a segment removed here, is cut, so the original routing is otherwise untouched
  (this also takes back the RP2040 GPIO3-18 fanout, which led to the removed input stages);
- removes the GNDPWR zone, stretches the GND zone over the whole board (refilled later by
  kicad-cli pcb drc --refill-zones --save-board);
- removes the J6-J11 terminal numbers and the fuse value from the silkscreen, renames the board.
Usage: c04_board_clean.py <netlist.xml> <board.kicad_pcb>"""
import json, re, sys
import xml.etree.ElementTree as ET
import sx

netfile, boardfile = sys.argv[1:3]
NM = 1e6
BOARD = (75.0, 39.0, 175.0, 139.0)
netnames = {n.get('name') for n in ET.parse(netfile).iter('net')}
pads = json.load(open(boardfile + '.pads.json'))
dead_boxes = {}
for n, x0, y0, x1, y1 in pads['removed']:
    dead_boxes.setdefault(n, []).append((x0 / NM, y0 / NM, x1 / NM, y1 / NM))
kept = {}
for n, layers, x0, y0, x1, y1 in pads['kept']:
    for l in layers:
        kept.setdefault((n, l), []).append((x0 / NM, y0 / NM, x1 / NM, y1 / NM))

t = open(boardfile).read()
items = sx.items(t)
drop = set()            # (start, end) spans to delete
repl = {}               # span -> new text


def net_of(s):
    m = re.search(r'\n\t\t\(net "([^"]*)"\)', s)
    return m.group(1) if m else ''


segs, vias = [], []
for h, a, b in items:
    s = t[a:b]
    if h in ('segment', 'arc'):
        st = re.search(r'\(start ([-\d.]+) ([-\d.]+)\)', s); en = re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', s)
        segs.append(dict(span=(a, b), net=net_of(s), layer=re.search(r'\(layer "([^"]+)"\)', s).group(1),
                         w=float(re.search(r'\(width ([\d.]+)\)', s).group(1)),
                         p=((float(st[1]), float(st[2])), (float(en[1]), float(en[2])))))
    elif h == 'via':
        x, y, _ = sx.at(s)
        vias.append(dict(span=(a, b), net=net_of(s), at=(x, y)))

# nets that no longer exist, and the GPIOs left unconnected (their fanout kept the old track)
gone_net = lambda n: n not in netnames or n.startswith('unconnected-')
dead = [o for o in segs + vias if gone_net(o['net'])]
segs = [o for o in segs if not gone_net(o['net'])]
vias = [o for o in vias if not gone_net(o['net'])]
for o in dead:
    drop.add(o['span'])

dead_pts = set()
inbox = lambda p, bx, m=1e-4: bx[0] - m <= p[0] <= bx[2] + m and bx[1] - m <= p[1] <= bx[3] + m


ALL_DEAD = [bx for v in dead_boxes.values() for bx in v]


def on_dead(n, p):
    # any removed pad, whatever its old net: the U3 fanout keeps its track while the pad net changes
    return p in dead_pts or any(inbox(p, bx) for bx in ALL_DEAD)


def on_seg(p, s):
    (x0, y0), (x1, y1) = s['p']
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((p[0] - x0) * dx + (p[1] - y0) * dy) / L))
    return (x0 + u * dx - p[0]) ** 2 + (y0 + u * dy - p[1]) ** 2 < 1e-6


stubs = 0
while True:
    via_pts = {(v['net'], v['at']) for v in vias}

    def loose(s, p):
        n, l = s['net'], s['layer']
        if not on_dead(n, p) or (n, p) in via_pts:
            return False
        if any(inbox(p, bx, s['w'] / 2) for bx in kept.get((n, l), ())):   # a track touches a pad with its width
            return False
        return not any(o is not s and o['net'] == n and o['layer'] == l and on_seg(p, o) for o in segs)
    gone = [s for s in segs if loose(s, s['p'][0]) or loose(s, s['p'][1])]
    gone_ids = {id(s) for s in gone}
    seg_pts = {(s['net'], p) for s in segs if id(s) not in gone_ids for p in s['p']}
    seg_layers = {}
    for s in segs:
        if id(s) not in gone_ids:
            for p in s['p']:
                seg_layers.setdefault((s['net'], p), set()).add(s['layer'])
    # a via at a cut point that no track reaches any more, or (except GND, which the zone holds on
    # both layers) that a track reaches on one layer only
    gone_v = [v for v in vias if on_dead(v['net'], v['at'])
              and len(seg_layers.get((v['net'], v['at']), ())) < (1 if v['net'] == 'GND' else 2)]
    if not gone and not gone_v:
        break
    for s in gone:
        dead_pts.update(s['p']); drop.add(s['span']); segs.remove(s); stubs += 1
    for v in gone_v:
        dead_pts.add(v['at']); drop.add(v['span']); vias.remove(v); stubs += 1

zones = 0
for h, a, b in items:
    s = t[a:b]
    if h == 'zone' and '(keepout' not in s:
        n = net_of(s)
        if n not in netnames:
            drop.add((a, b)); zones += 1
        elif n == 'GND':
            x0, y0, x1, y1 = BOARD
            pts = ' '.join(f'(xy {x} {y})' for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))
            new = re.sub(r'\(polygon\s*\(pts.*?\)\s*\)\s*\)', f'(polygon\n\t\t\t(pts\n\t\t\t\t{pts}\n\t\t\t)\n\t\t)', s,
                         count=1, flags=re.S)
            # drop the old fill, kicad-cli refills
            out = []; last = 0
            for hh, aa, bb in sx.items(new):
                if hh == 'filled_polygon':
                    out.append(new[last:aa].rstrip('\t ')); last = bb
            out.append(new[last:]); repl[(a, b)] = ''.join(out)

texts = 0
for h, a, b in items:
    s = t[a:b]
    if h != 'gr_text':
        continue
    txt = sx.name(s); x, y, _ = sx.at(s)
    if txt == 'PPUC IO_16_8_1':
        repl[(a, b)] = s.replace('"PPUC IO_16_8_1"', '"PPUC SAM_IO"')
    elif x < 90 or (x > 160 and y > 54) or txt == 'T6A':
        drop.add((a, b)); texts += 1

for a, b in sorted(drop | set(repl), reverse=True):
    if (a, b) in drop:
        while t[a - 1] in '\t ':
            a -= 1
        if t[a - 1] == '\n':
            a -= 1
        t = t[:a] + t[b:]
    else:
        t = t[:a] + repl[(a, b)] + t[b:]
open(boardfile, 'w').write(t)
print(f'tracks/vias on removed nets: {len(dead)}, dangling ends: {stubs}, zones: {zones}, silkscreen texts: {texts}')

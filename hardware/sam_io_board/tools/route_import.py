"""Routing step 2: import a Freerouting session and keep only what it added.
pcbnew's session import rewrites every track, so it runs on a copy (KiCad 10 Python, phase 'ses');
then phase 'merge' (plain Python) copies into the board the non-GND tracks and vias that do not lie
on existing copper of their net, leaving every existing track untouched.
  route_import.py ses <board> <session.ses> <copy.kicad_pcb>
  route_import.py merge <board> <copy.kicad_pcb> <refs>
Only nets with a pad on one of <refs> (comma-separated) are taken: the session also moves pieces of
untouched nets. Tracks the router necked down to 0.15 mm go back to the board's 0.2 mm."""
import os, re, sys

if sys.argv[1] == 'ses':
    import pcbnew
    b = pcbnew.LoadBoard(sys.argv[2])
    ok = pcbnew.ImportSpecctraSES(b, sys.argv[3])
    b.Save(sys.argv[4]); print('imported', ok); sys.stdout.flush(); os._exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sx
board, copy = sys.argv[2], sys.argv[3]
refs = set(sys.argv[4].split(','))


def parse(t):
    """segments and vias as (span text, kind, net, layer, points)"""
    out = []
    for h, a, b in sx.items(t):
        if h not in ('segment', 'via'):
            continue
        s = t[a:b]
        net = (re.search(r'\(net "([^"]*)"\)', s) or [None, ''])[1]
        lay = (re.search(r'\(layer "([^"]+)"\)', s) or [None, ''])[1]
        pts = [(float(x), float(y)) for x, y in re.findall(r'\((?:start|end|at) ([-\d.]+) ([-\d.]+)\)', s)]
        out.append((s, h, net, lay, pts))
    return out


def on_seg(p, a, b, tol=0.01):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return (ax + u * dx - px) ** 2 + (ay + u * dy - py) ** 2 < tol * tol


t = open(board).read()
nets = set()
for h, a, b in sx.items(t):
    if h == 'footprint' and sx.prop(t[a:b], 'Reference') in refs:
        nets |= set(re.findall(r'\(pad "[^"]*".*?\(net "([^"]*)"\)', t[a:b], re.S))
old = parse(t)
oldseg = {}
for s, h, net, lay, pts in old:
    if h == 'segment':
        oldseg.setdefault((net, lay), []).append(pts)
oldvia = {(net, round(pts[0][0], 2), round(pts[0][1], 2)) for s, h, net, lay, pts in old if h == 'via'}
add = []
for s, h, net, lay, pts in parse(open(copy).read()):
    if net == 'GND' or net not in nets:
        continue
    s = re.sub(r'\(width 0\.15\)', '(width 0.2)', s)
    if h == 'via':
        if not any(abs(x - pts[0][0]) < 0.011 and abs(y - pts[0][1]) < 0.011
                   for n, x, y in oldvia if n == net):
            add.append(s)
    elif not all(any(on_seg(p, *q) for q in oldseg.get((net, lay), [])) for p in pts):
        add.append(s)       # the session splits existing tracks: pieces lying on one are not new
end = t.rstrip().rfind(')')
t = t[:end].rstrip() + '\n\t' + '\n\t'.join(add) + '\n)\n'
open(board, 'w').write(t)
print('added', len(add), 'tracks / vias')

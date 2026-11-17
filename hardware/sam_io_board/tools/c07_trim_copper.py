"""Change 07 (2026-10-07), after c06: removes copper the smaller outline cut off (tracks and vias
below the new bottom edge) and the GND stitching vias (no track on them) under the new SAM bus parts
and around the moved mounting holes. The GND zone still ties everything together.
Usage: c07_trim_copper.py <board.kicad_pcb>"""
import re, sys
import sx

Y1 = 109.0
BUS = (76.0, 55.0, 108.0, 106.0)
HOLES = [(80.0, 104.0), (170.0, 104.0)]
path = sys.argv[1]
t = open(path).read()
net = lambda s: (re.search(r'\n\t\t\(net "([^"]*)"\)', s) or [None, ''])[1]
segs, vias = [], []
for h, a, b in sx.items(t):
    s = t[a:b]
    if h == 'segment':
        p = [(float(x), float(y)) for x, y in re.findall(r'\((?:start|end) ([-\d.]+) ([-\d.]+)\)', s)]
        segs.append(((a, b), net(s), p))
    elif h == 'via':
        vias.append(((a, b), net(s), sx.at(s)[:2]))
drop = [sp for sp, n, p in segs if any(y > Y1 - 0.5 for x, y in p)]
seg_pts = {(n, q) for sp, n, p in segs if sp not in drop for q in p}
for sp, n, (x, y) in vias:
    if y > Y1 - 0.5:
        drop.append(sp)
    elif n == 'GND' and (n, (x, y)) not in seg_pts and (
            (BUS[0] <= x <= BUS[2] and BUS[1] <= y <= BUS[3]) or
            any((x - hx) ** 2 + (y - hy) ** 2 < 5.0 ** 2 for hx, hy in HOLES)):
        drop.append(sp)
for a, b in sorted(drop, reverse=True):
    while t[a - 1] in '\t ':
        a -= 1
    t = t[:a - 1] + t[b:] if t[a - 1] == '\n' else t[:a] + t[b:]
open(path, 'w').write(t)
print('removed', len(drop), 'tracks / vias')

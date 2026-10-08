"""Ratsnest metrics: per-net minimum spanning tree over pad centres; total length and edge crossings.
Plane nets (GND, +3V3, GND_ISO) are left out: they connect through vias to their planes."""
import sys, math, json, itertools
sys.path.insert(0, '/tmp/claude-0/krt/src/py_router')
from kicad_parser import parse_kicad_pcb
SKIP = {'GND', '+3V3', 'GND_ISO', ''}
pcb = parse_kicad_pcb(sys.argv[1])
pads = {}
for ref, fp in pcb.footprints.items():
    for p in fp.pads:
        n = pcb.nets[p.net_id].name if p.net_id in pcb.nets else ''
        if not n or n in SKIP or n.startswith('unconnected-'): continue
        pads.setdefault(n, []).append((p.global_x, p.global_y))
edges = []
for n, pts in pads.items():
    pts = list(dict.fromkeys(pts))
    if len(pts) < 2: continue
    inT = {0}; d = {i: math.dist(pts[0], pts[i]) for i in range(1, len(pts))}; par = {i: 0 for i in d}
    while d:
        j = min(d, key=d.get); inT.add(j); edges.append((n, pts[par[j]], pts[j])); del d[j]
        for k in d:
            dd = math.dist(pts[j], pts[k])
            if dd < d[k]: d[k] = dd; par[k] = j
L = sum(math.dist(a, b) for _, a, b in edges)
def ccw(a, b, c): return (c[1]-a[1])*(b[0]-a[0]) - (b[1]-a[1])*(c[0]-a[0])
def cross(e, f):
    a, b = e[1], e[2]; c, d = f[1], f[2]
    if len({a, b, c, d}) < 4: return False
    return (ccw(a, b, c) * ccw(a, b, d) < 0) and (ccw(c, d, a) * ccw(c, d, b) < 0)
# grid bucket for speed
from collections import defaultdict
G = 5.0; buck = defaultdict(list)
for i, (n, a, b) in enumerate(edges):
    for gx in range(int(min(a[0], b[0])//G), int(max(a[0], b[0])//G)+1):
        for gy in range(int(min(a[1], b[1])//G), int(max(a[1], b[1])//G)+1):
            buck[(gx, gy)].append(i)
seen = set(); X = 0
for ids in buck.values():
    for i, j in itertools.combinations(ids, 2):
        if (i, j) in seen or edges[i][0] == edges[j][0]: continue
        seen.add((i, j))
        if cross(edges[i], edges[j]): X += 1
out = {'nets': len(pads), 'airwires': len(edges), 'ratsnest_mm': round(L, 1), 'crossings': X}
print(json.dumps(out))

"""List GND copper clusters (zone islands + pads + tracks + vias) not tied to the main one.
Usage: islands.py <board>"""
import pcbnew, os, sys
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
b = pcbnew.LoadBoard(sys.argv[1]); T = pcbnew.ToMM
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
g = b.FindNet('GND').GetNetCode()
LAY = (pcbnew.F_Cu, pcbnew.B_Cu)
nodes = []   # (kind, layers, SHAPE_POLY_SET per layer dict, label)
for z in b.Zones():
    if z.GetNetCode() != g: continue
    for L in LAY:
        if not z.IsOnLayer(L): continue
        ps = z.GetFilledPolysList(L)
        for i in range(ps.OutlineCount()):
            sp = pcbnew.SHAPE_POLY_SET(ps.Outline(i))
            nodes.append(('zone', {L: sp}, '%s zone %s' % (b.GetLayerName(L), [round(T(v), 2) for v in (ps.Outline(i).BBox().GetLeft(), ps.Outline(i).BBox().GetTop(), ps.Outline(i).BBox().GetRight(), ps.Outline(i).BBox().GetBottom())])))
def shp(item, L):
    s = pcbnew.SHAPE_POLY_SET(); item.TransformShapeToPolygon(s, L, 0, 5000, pcbnew.ERROR_INSIDE); return s
for t in b.GetTracks():
    if t.GetNetCode() != g: continue
    nodes.append((t.GetClass(), {L: shp(t, L) for L in LAY if t.IsOnLayer(L)}, '%s %.2f,%.2f' % (t.GetClass(), T(t.GetStart().x), T(t.GetStart().y))))
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetCode() != g: continue
        nodes.append(('pad', {L: shp(p, L) for L in LAY if p.IsOnLayer(L)}, '%s.%s' % (f.GetReference(), p.GetNumber())))
par = list(range(len(nodes)))
def find(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
bbs = []
for k, n in enumerate(nodes):
    bbs.append({L: s.BBox() for L, s in n[1].items()})
for a in range(len(nodes)):
    for c in range(a + 1, len(nodes)):
        if nodes[a][0] == 'zone' and nodes[c][0] == 'zone': continue
        for L, sa in nodes[a][1].items():
            if L not in nodes[c][1]: continue
            ba, bc = bbs[a][L], bbs[c][L]
            if not ba.Intersects(bc): continue
            sc = nodes[c][1][L]
            x = pcbnew.SHAPE_POLY_SET(sa); x.BooleanIntersection(sc)
            if x.OutlineCount():
                par[find(a)] = find(c); break
cl = {}
for k in range(len(nodes)): cl.setdefault(find(k), []).append(k)
big = max(cl.values(), key=len)
for r, v in cl.items():
    if v is big: continue
    print('cluster:', ', '.join(nodes[k][2] for k in v))
os._exit(0)

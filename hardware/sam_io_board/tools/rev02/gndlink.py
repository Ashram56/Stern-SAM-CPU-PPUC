"""Tie isolated GND clusters to the main pour with one via each, placed inside the cluster's zone
island where the other layer is main-cluster pour. Usage: gndlink.py <board> [via_d via_drill clr]"""
import pcbnew, os, sys
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'islands.py')).read().split("cl = {}")[0])
cl = {}
for k in range(len(nodes)): cl.setdefault(find(k), []).append(k)
big = max(cl.values(), key=len)
MM = pcbnew.FromMM
VD, VH, CLR = [MM(float(v)) for v in (sys.argv[2:5] if len(sys.argv) > 4 else (0.5, 0.3, 0.16))]
other = {L: [] for L in LAY}
for t in b.GetTracks():
    if t.GetNetCode() == g: continue
    for L in LAY:
        if t.IsOnLayer(L): other[L].append(t)
for f in b.GetFootprints():
    for p in f.Pads():
        for L in LAY:
            if p.IsOnLayer(L) and (p.GetNetCode() != g): other[L].append(p)
holes = [p for f in b.GetFootprints() for p in f.Pads() if p.HasHole()]
edge = b.GetBoardEdgesBoundingBox()
mainz = {L: [nodes[k][1][L] for k in big if nodes[k][0] == 'zone' and L in nodes[k][1]] for L in LAY}
def ok_via(x, y):
    c = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(x, y), VD // 2)
    for L in LAY:
        for it in other[L]:
            bb = it.GetBoundingBox()
            if bb.GetLeft() - VD > x or bb.GetRight() + VD < x or bb.GetTop() - VD > y or bb.GetBottom() + VD < y: continue
            if it.GetEffectiveShape(L).Collide(c, CLR): return False
    for p in holes:
        d = (p.GetPosition() - pcbnew.VECTOR2I(x, y)).EuclideanNorm()
        if d < VH // 2 + p.GetDrillSize().x // 2 + MM(0.3): return False
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and (t.GetPosition() - pcbnew.VECTOR2I(x, y)).EuclideanNorm() < VD + MM(0.25): return False
    return True
added = 0
for r, v in cl.items():
    if v is big: continue
    done = False
    for k in v:
        if nodes[k][0] != 'zone': continue
        (L, isl), = nodes[k][1].items()
        O = LAY[1] if L == LAY[0] else LAY[0]
        er = pcbnew.SHAPE_POLY_SET(isl); er.Deflate(VD // 2 - MM(0.05), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, 5000)
        if not er.OutlineCount(): continue
        bb = isl.BBox(); step = MM(0.05)
        y = bb.GetTop()
        while y <= bb.GetBottom() and not done:
            x = bb.GetLeft()
            while x <= bb.GetRight():
                p = pcbnew.VECTOR2I(x, y)
                if er.Contains(p) and any(z.Contains(p) for z in mainz[O]):
                    zc = [z for z in mainz[O] if z.Contains(p)][0]
                    ring = pcbnew.SHAPE_POLY_SET(zc); ring.Deflate(VD // 2, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, 5000)
                    if ring.Contains(p) and ok_via(x, y):
                        vv = pcbnew.PCB_VIA(b); vv.SetPosition(p); vv.SetWidth(VD); vv.SetDrill(VH); vv.SetNet(b.FindNet('GND')); b.Add(vv)
                        print('via', round(T(x), 2), round(T(y), 2), 'for', nodes[k][2]); done = True; added += 1; break
                x += step
            y += step
        if done: break
    if not done: print('no via for cluster', ', '.join(nodes[k][2] for k in v))
b.Save(sys.argv[1]); print('added', added); sys.stdout.flush(); os._exit(0)

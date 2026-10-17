"""Check polylines for clearance. Usage: pathchk.py <board> <spec.json>; spec: [{net, layer, pts:[[x,y]...]}, {net, via:[x,y]}]"""
import pcbnew, os, sys, json
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; T = pcbnew.ToMM
spec = json.load(open(sys.argv[2])); CL = MM(0.15)
items = list(b.GetTracks()) + [p for f in b.GetFootprints() for p in f.Pads()]
def P(q): return pcbnew.VECTOR2I(MM(q[0]), MM(q[1]))
for s in spec:
    net = s['net']
    shapes = []
    if 'via' in s:
        for L in (pcbnew.F_Cu, pcbnew.B_Cu): shapes.append((L, pcbnew.SHAPE_CIRCLE(P(s['via']), MM(0.25)), 'via %s' % s['via']))
    else:
        L = b.GetLayerID(s['layer'])
        for a, c in zip(s['pts'], s['pts'][1:]): shapes.append((L, pcbnew.SHAPE_SEGMENT(P(a), P(c), MM(0.2)), '%s-%s' % (a, c)))
    for L, sh, lab in shapes:
        for it in items:
            if it.GetNetname() == net or not it.IsOnLayer(L): continue
            if it.GetEffectiveShape(L).Collide(sh, CL):
                pos = it.GetPosition()
                print('%s %s: hits %s %s at %.2f,%.2f' % (net, lab, it.GetClass(), it.GetNetname(), T(pos.x), T(pos.y)))
print('checked'); os._exit(0)

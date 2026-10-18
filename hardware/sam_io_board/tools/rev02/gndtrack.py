"""For each isolated GND cluster, try a straight track from one of its vias/pads to the main pour.
Usage: gndtrack.py <board>"""
import pcbnew, os, sys, math
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'islands.py')).read().split("cl = {}")[0])
cl = {}
for k in range(len(nodes)): cl.setdefault(find(k), []).append(k)
big = max(cl.values(), key=len)
MM = pcbnew.FromMM; W = MM(0.2); CLR = MM(0.16)
mainz = {L: [nodes[k][1][L] for k in big if nodes[k][0] == 'zone' and L in nodes[k][1]] for L in LAY}
mainitems = {L: [nodes[k][1][L] for k in big if nodes[k][0] != 'zone' and L in nodes[k][1]] for L in LAY}
other = {L: [] for L in LAY}
for t in b.GetTracks():
    if t.GetNetCode() != g:
        for L in LAY:
            if t.IsOnLayer(L): other[L].append(t)
for f in b.GetFootprints():
    for p in f.Pads():
        for L in LAY:
            if p.IsOnLayer(L) and p.GetNetCode() != g: other[L].append(p)
gn = b.FindNet('GND')
for r, v in cl.items():
    if v is big: continue
    best = None
    for k in v:
        kind, sh, lab = nodes[k]
        if kind not in ('PCB_VIA', 'pad'): continue
        for L, s in sh.items():
            c = s.BBox().GetCenter()
            for rr in [0.4 + 0.2 * i for i in range(20)]:
                for a in range(64):
                    e = pcbnew.VECTOR2I(int(c.x + MM(rr) * math.cos(a * math.pi / 32)), int(c.y + MM(rr) * math.sin(a * math.pi / 32)))
                    inmain = any(z.Contains(e) for z in mainz[L]) or any(m.Contains(e) for m in mainitems[L])
                    if not inmain: continue
                    seg = pcbnew.SHAPE_SEGMENT(c, e, W)
                    if any(it.GetEffectiveShape(L).Collide(seg, CLR) for it in other[L]): continue
                    best = (rr, c, e, L, lab); break
                if best: break
            if best: break
        if best: break
    if best:
        rr, c, e, L, lab = best
        t = pcbnew.PCB_TRACK(b); t.SetStart(c); t.SetEnd(e); t.SetWidth(W); t.SetLayer(L); t.SetNet(gn); b.Add(t)
        print('track %.1f mm on %s from %s' % (rr, b.GetLayerName(L), lab))
    else: print('nothing for', ', '.join(nodes[k][2] for k in v))
b.Save(sys.argv[1]); sys.stdout.flush(); os._exit(0)

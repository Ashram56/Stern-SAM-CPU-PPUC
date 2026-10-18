"""Tie GND islands to the main pour: one stitching via per island where the other layer has main-pour copper.
Usage: stitch_islands.py <board>   (run again until it reports 0 islands)"""

import pcbnew, os, sys
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
b = pcbnew.LoadBoard(sys.argv[1]); T = pcbnew.ToMM; MM = pcbnew.FromMM; import math
gnd = b.FindNet('GND'); CL = MM(0.2); VD = MM(0.6); VH = MM(0.3)
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
allz = {L: [(find(k), n[1][L]) for k, n in enumerate(nodes) if n[0] == 'zone' and L in n[1]] for L in LAY}
main = {L: [nodes[k][1][L] for k in big if nodes[k][0] == 'zone' and L in nodes[k][1]] for L in LAY}
edge = b.GetBoardEdgesBoundingBox()
items = []
for t in b.GetTracks(): items.append(t)
for f in b.GetFootprints():
    for p in f.Pads(): items.append(p)
def free(x, y, layers=(pcbnew.F_Cu, pcbnew.B_Cu), ignore=None, gnd_ok=False):
    if not (edge.GetLeft() + MM(0.8) < x < edge.GetRight() - MM(0.8) and edge.GetTop() + MM(0.8) < y < edge.GetBottom() - MM(0.8)): return False
    c = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(x), int(y)), VD // 2)
    for it in items:
        if it is ignore: continue
        if gnd_ok and it.GetNetCode() == gnd.GetNetCode() and it.GetClass() != 'PAD': continue
        bb = it.GetBoundingBox()
        if bb.GetLeft() - VD > x or bb.GetRight() + VD < x or bb.GetTop() - VD > y or bb.GetBottom() + VD < y: continue
        for l in layers:
            if it.IsOnLayer(l):
                cl = CL if it.GetNetCode() != gnd.GetNetCode() else MM(0.1)
                if it.GetClass() == 'PAD' and it.GetNetCode() == gnd.GetNetCode() and it is ignore: continue
                if it.GetEffectiveShape(l).Collide(c, cl): return False
        if it.GetClass() == 'PAD' and it.HasHole():
            if math.hypot(it.GetPosition().x - x, it.GetPosition().y - y) < VD + it.GetDrillSize().x / 2 + MM(0.3): return False
    for f in b.GetFootprints():   # keep out of mounting holes
        if 'MountingHole' in str(f.GetFPID().GetLibItemName()) and math.hypot(f.GetPosition().x - x, f.GetPosition().y - y) < MM(5.2): return False
    return True
def via(x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(int(x), int(y))); v.SetWidth(VD); v.SetDrill(VH); v.SetNet(gnd); b.Add(v); v.thisown=0; items.append(v); return v
n_isl = n_via = 0; fixed = set()
for PASS in (0, 1):
  for r, v in cl.items():
      if v is big or r in fixed: continue
      n_isl += 1; done = False
      for k in v:
          if nodes[k][0] != 'zone' or done: continue
          (L, sp), = nodes[k][1].items(); O = [x for x in LAY if x != L][0]
          bb = sp.BBox(); step = MM(0.25)
          y = bb.GetTop() + step
          while y < bb.GetBottom() and not done:
              x = bb.GetLeft() + step
              while x < bb.GetRight():
                  p = pcbnew.VECTOR2I(int(x), int(y))
                  # via pad (r 0.3) fully inside both fills
                  if sp.Contains(p) and any(m.Contains(p) for m in (main[O] if PASS == 0 else [z for c, z in allz[O] if c != r])) and free(x, y, gnd_ok=True):
                      via(x, y); done = True; n_via += 1; fixed.add(r); break
                  x += step
              y += step
      if not done and PASS: print('no spot:', ', '.join(nodes[k][2] for k in v)[:150])
print('islands', n_isl, 'vias added', n_via)
b.Save(sys.argv[1]); sys.stdout.flush(); os._exit(0)

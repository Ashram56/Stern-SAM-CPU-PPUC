"""take_nets.py board sesboard out ox0 oy0 ox1 oy1 net...: for each net, our copper wholly inside O goes and DeepPCB's
(sesboard, already cut to O) comes in. Used net by net to keep only DeepPCB routes that fit our routing."""
import sys, pcbnew
m = pcbnew.LoadBoard(sys.argv[1]); r = pcbnew.LoadBoard(sys.argv[2]); x0, y0, x1, y1 = map(float, sys.argv[4:8])
names = set(sys.argv[8:]); M = pcbnew.ToMM; F = pcbnew.FromMM; hold = []
def inO(p): return x0 <= M(p.x) <= x1 and y0 <= M(p.y) <= y1
def pts(t): return [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
for t in list(m.Tracks()):
    if t.GetNetname() in names and all(inO(p) for p in pts(t)): hold.append(t); m.Remove(t)
nets = {str(k): v for k, v in m.GetNetInfo().NetsByName().items()}; n = 0
for t in r.Tracks():
    if t.GetNetname() not in names: continue
    if t.Type() == pcbnew.PCB_VIA_T:
        v = pcbnew.PCB_VIA(m); v.SetPosition(t.GetPosition()); v.SetWidth(t.GetWidth(pcbnew.F_Cu)); v.SetDrill(t.GetDrill() or F(0.3))
        v.SetViaType(t.GetViaType()); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(nets[t.GetNetname()]); m.Add(v); hold.append(v)
    else:
        s = pcbnew.PCB_TRACK(m); s.SetStart(t.GetStart()); s.SetEnd(t.GetEnd()); s.SetWidth(t.GetWidth()); s.SetLayer(t.GetLayer())
        s.SetNet(nets[t.GetNetname()]); m.Add(s); hold.append(s)
    n += 1
pcbnew.ZONE_FILLER(m).Fill(m.Zones()); m.Save(sys.argv[3]); print('taken', n)

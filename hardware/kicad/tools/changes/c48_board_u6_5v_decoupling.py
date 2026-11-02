"""c48 (board only): C32, the 100 nF on U6's +5V side, comes next to U6 pin 24. When U6 was turned 180 degrees (c21)
its capacitors stayed put, so C32 ended up by the GND pins and reached pin 24 through about 25 mm of track.
- The +5V branch from C32's old spot (27.84, 21.77) down to the via at (29.49, 33.27) goes, with that via and its
  B.Cu stub to (27.80, 34.94): it fed only C32.
- The C32 and RN3 reference texts move clear of the new pads.
- C32 sits just below pin 24 at (18.775, 32.68), between U6 and RN3, turned 180: pad 1 +5V at (19.55, 32.68) joins
  the pin 24 track on x 20.23, pad 2 GND at (18.0, 32.68) with its own GND via at (18.0, 31.6).
Coordinates as drcsum prints them (raw - 30 mm). Usage: c48_board_u6_5v_decoupling.py in.kicad_pcb out.kicad_pcb"""
import sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; F, B = pcbnew.F_Cu, pcbnew.B_Cu; O = 30.0
def pt(x, y): return pcbnew.VECTOR2I(MM(x + O), MM(y + O))
def near(a, x, y, tol=0.01): return abs(a.x - MM(x + O)) < MM(tol) and abs(a.y - MM(y + O)) < MM(tol)
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
V5, G = nets['+5V'], nets['GND']
T = b.Tracks(); tracks = [T[i] for i in range(T.size())]; keep = []
branch = [(27.84, 21.77), (27.84, 21.844), (28.371, 22.375), (30.238, 24.242), (30.238, 25.137), (29.696, 25.679),
          (29.696, 25.99), (29.449, 26.236), (29.449, 28.028), (29.67, 28.249), (29.67, 32.042), (29.67, 32.149),
          (29.449, 32.37), (29.487, 32.408), (29.487, 33.27)]
segs = set(zip(branch, branch[1:])) | {((29.487, 33.27), (29.468, 33.27)), ((29.468, 33.27), (27.797, 34.941))}
gone = 0
for t in tracks:
    if t.GetNetCode() != V5.GetNetCode(): continue
    if t.Type() == pcbnew.PCB_VIA_T:
        if near(t.GetPosition(), 29.487, 33.27): keep.append(t); b.Remove(t); gone += 1
        continue
    for a, c in segs:
        if (near(t.GetStart(), *a) and near(t.GetEnd(), *c)) or (near(t.GetStart(), *c) and near(t.GetEnd(), *a)):
            keep.append(t); b.Remove(t); gone += 1; break
assert gone == len(segs) + 1, gone
f = b.FindFootprintByReference('C32'); f.SetOrientationDegrees(180); f.SetPosition(pt(18.775, 32.68))
r = f.Reference(); r.SetTextAngleDegrees(90); r.SetPosition(pt(17.0, 32.68)); r.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0))); r.SetTextThickness(MM(0.15))   # silk clear of RN3 and J9
rn = b.FindFootprintByReference('RN3').Reference(); rn.SetTextAngleDegrees(90); rn.SetPosition(pt(21.1, 35.65))
pos = {p.GetNumber(): (round(pcbnew.ToMM(p.GetPosition().x) - O, 3), round(pcbnew.ToMM(p.GetPosition().y) - O, 3), p.GetNetname()) for p in f.Pads()}
print('C32 pads', pos); assert pos['1'][2] == '+5V' and abs(pos['1'][0] - 19.55) < 0.01
def track(n, pts, w, ly=F):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(w)); t.SetLayer(ly); t.SetNet(n); b.Add(t)
track(V5, [(19.55, 32.68), (20.233, 32.68)], 0.5)
track(G, [(18.0, 32.68), (18.0, 31.6)], 0.4)
v = pcbnew.PCB_VIA(b); v.SetPosition(pt(18.0, 31.6)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3))
v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(F, B); v.SetNet(G); b.Add(v)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2]); print('removed', gone, 'ok')

"""Give SMD pads of one net a short F.Cu stub and a via (0.6/0.3 mm) to the inner planes.
Usage: fanout_vias.py board.kicad_pcb out.kicad_pcb NET REF:PAD [REF:PAD ...]
Candidate spots on rings around the pad; the first one clear of every other net (0.2 mm, all copper layers, holes
0.5 mm apart) wins. Run it in a directory that holds the project files."""
import math, sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; mm = pcbnew.ToMM
NET = sys.argv[3]
net = b.FindNet(NET)
CL, VD, VH, TW = MM(0.2), MM(0.6), MM(0.3), MM(0.25)
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
T = b.Tracks(); others = [T[i] for i in range(T.size()) if T[i].GetNetname() != NET]
pads = [p for f in b.GetFootprints() for p in f.Pads()]
others += [p for p in pads if p.GetNetname() != NET]
holes = [x.GetPosition() for x in others if x.Type() == pcbnew.PCB_VIA_T] + \
        [(p.GetPosition(), max(p.GetDrillSize().x, p.GetDrillSize().y)) for p in pads if p.GetDrillSize().x > 0]

def clear(shape, layers):
    for x in others:
        for ly in layers:
            if x.IsOnLayer(ly) and x.GetEffectiveShape(ly).Collide(shape, CL): return False
    return True

def hole_ok(c):
    for h in holes:
        pos, d = (h, VH) if not isinstance(h, tuple) else h
        if (pos - c).EuclideanNorm() < MM(0.5) + (d + VH) / 2: return False
    return True

added = []
for spec in sys.argv[4:]:
    ref, num = spec.split(':')
    pad = [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]
    c0 = pad.GetPosition(); done = False
    for r in (0.9, 1.1, 1.3, 1.5, 1.8, 2.1, 2.5):
        for k in range(24):
            a = 2 * math.pi * k / 24
            c = c0 + pcbnew.VECTOR2I(MM(r * math.cos(a)), MM(r * math.sin(a)))
            if not hole_ok(c): continue
            if not clear(pcbnew.SHAPE_CIRCLE(c, VD // 2), CU): continue
            if not clear(pcbnew.SHAPE_SEGMENT(c0, c, TW), [pcbnew.F_Cu]): continue
            v = pcbnew.PCB_VIA(b); v.SetPosition(c); v.SetWidth(VD); v.SetDrill(VH); v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net); b.Add(v)
            t = pcbnew.PCB_TRACK(b); t.SetStart(c0); t.SetEnd(c); t.SetWidth(TW); t.SetLayer(pcbnew.F_Cu); t.SetNet(net); b.Add(t)
            holes.append(c); added.append((spec, round(mm(c.x), 2), round(mm(c.y), 2))); done = True
            break
        if done: break
    if not done: added.append((spec, 'no spot'))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
print(added)

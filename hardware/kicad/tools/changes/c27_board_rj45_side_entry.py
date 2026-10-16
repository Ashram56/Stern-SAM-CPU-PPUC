"""c27: J27/J29 OST PJ012 top-entry RJ45 (not stocked at JLCPCB) -> CONNFLY DS1128-05-S8B8P side-entry, unshielded,
through-hole (C86577). Vincent's card choice: side-entry THT at the right board edge.
Footprint from the maker's drawing C-DS1128-05-XXXXX-A: 8 pins at 1.27 mm in two rows 2.54 mm apart (same pattern as
KiCad's RJ45_Amphenol_54602-x08_Horizontal), 0.90 mm holes, two 3.25 mm pegs 11.43 mm apart, 6.35 mm in front of the
pin 1 row; body 15.15 wide, 20.64 deep, front 10.55 mm in front of the pegs.
Both jacks open on the right edge (x 172), stacked below D27; the GND_ISO area grows 7.5 mm down to y 235 and the
GND / +3V3 areas keep their 2 mm gap to it. Old J27/J29 copper is removed; A/B/GND_ISO are rerouted afterwards.
Also puts C130-C132 pin 1 back on Net-(U32-VISO) (c25 renamed the net on tracks and U32 only)."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; mm = pcbnew.ToMM
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
for r in ('C130', 'C131', 'C132'):
    for p in b.FindFootprintByReference(r).Pads():
        if p.GetNumber() == '1': p.SetNet(nets['Net-(U32-VISO)'])
EDGE, X = 172.0, 172.0 - 16.9          # front of the body on the board edge
YS = {'J27': 214.62, 'J29': 230.52}
T = b.Tracks(); tracks = [T[i] for i in range(T.size())]
keep = []
gone = []
for ref, Y in YS.items():
    f = b.FindFootprintByReference(ref)
    padnet = {p.GetNumber(): p.GetNetname() for p in f.Pads() if p.GetNumber()}
    for x in tracks:      # tracks and vias touching the old pads
        if any(p.HitTest(x.GetPosition() if x.Type() == pcbnew.PCB_VIA_T else x.GetStart()) or
               (x.Type() != pcbnew.PCB_VIA_T and p.HitTest(x.GetEnd())) for p in f.Pads()) and x not in gone:
            gone.append(x)
    old_p = list(f.Pads()); keep += old_p
    for p in old_p: f.Remove(p)
    G = f.GraphicalItems(); old_g = [G[i] for i in range(len(G))]; keep += old_g
    for g in old_g: f.Remove(g)
    f.SetOrientationDegrees(0)
    f.SetPosition(pcbnew.VECTOR2I(MM(X), MM(Y)))
    o = f.GetPosition()
    def at(lx, ly): return o + pcbnew.VECTOR2I(MM(lx), MM(ly))
    for n in range(1, 9):
        p = pcbnew.PAD(f); p.SetNumber(str(n)); p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        p.SetShape(pcbnew.PAD_SHAPE_RECTANGLE if n == 1 else pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(pcbnew.VECTOR2I(MM(1.5), MM(1.5))); p.SetDrillSize(pcbnew.VECTOR2I(MM(0.9), MM(0.9)))
        p.SetLayerSet(p.PTHMask()); f.Add(p)
        p.SetPosition(at((n - 1) * 1.27, 0 if n % 2 else -2.54)); p.SetNet(nets[padnet[str(n)]])
    for lx in (-1.27, 10.16):
        p = pcbnew.PAD(f); p.SetNumber(''); p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(pcbnew.VECTOR2I(MM(3.25), MM(3.25))); p.SetDrillSize(pcbnew.VECTOR2I(MM(3.25), MM(3.25)))
        p.SetLayerSet(p.UnplatedHoleMask()); f.Add(p); p.SetPosition(at(lx, 6.35))
    def seg(layer, x1, y1, x2, y2, w):
        s = pcbnew.PCB_SHAPE(f, pcbnew.SHAPE_T_SEGMENT); s.SetLayer(layer); s.SetWidth(MM(w))
        s.SetStart(at(x1, y1)); s.SetEnd(at(x2, y2)); f.Add(s)
    def rect(layer, x1, y1, x2, y2, w):
        for a in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)): seg(layer, *a, w)
    rect(pcbnew.F_Fab, -3.13, -3.74, 12.02, 16.9, 0.1)
    rect(pcbnew.F_CrtYd, -3.38, -3.99, 12.27, 16.9, 0.05)
    for a in ((-3.25, -3.86, 12.14, -3.86), (-3.25, -3.86, -3.25, 15.9), (12.14, -3.86, 12.14, 15.9),
              (-3.25, -1.0, -2.2, -1.0)):           # outline (not along the edge) + pin 1 tick
        seg(pcbnew.F_SilkS, *a, 0.12)
    f.SetOrientationDegrees(90)                       # front (+y) faces +x, the right edge
    f.SetFPID(pcbnew.LIB_ID('sam_cpu', 'RJ45_Connfly_DS1128-05-S8B8P_Horizontal'))
    f.Models().clear()
    f.Reference().SetPosition(pcbnew.VECTOR2I(MM(X + 6.35), MM(Y - 4.445)))
    f.Reference().SetTextAngleDegrees(90)
    f.Value().SetPosition(pcbnew.VECTOR2I(MM(X + 10.0), MM(Y - 4.445))); f.Value().SetLayer(pcbnew.F_Fab)
for x in gone: b.Remove(x)
# GND_ISO area down to y 235, GND / +3V3 notch down to 237
MOVE = {'GND_ISO': {(172.0, 227.5): (172.0, 235.0), (152.0, 227.5): (152.0, 235.0)},
        'GND': {(150.0, 229.5): (150.0, 237.0), (172.0, 229.5): (172.0, 237.0)},
        '+3V3': {(150.0, 229.5): (150.0, 237.0), (172.0, 229.5): (172.0, 237.0)}}
moved = 0
for z in list(b.Zones()):
    mv = MOVE.get(z.GetNetname())
    if not mv: continue
    ol = z.Outline()
    for i in range(ol.TotalVertices()):
        v = ol.CVertex(i); k = (round(mm(v.x), 2), round(mm(v.y), 2))
        if k in mv:
            ol.SetVertex(i, pcbnew.VECTOR2I(MM(mv[k][0]), MM(mv[k][1]))); moved += 1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
print('removed', len(gone), 'items; zone vertices moved', moved)

"""c26: BT1 Keystone 3034 (not stocked at JLCPCB) -> Lianxin XDCR-2032-603 SMD CR2032 holder (C7498148).
Footprint from the maker's drawing: two SMD pads 4.2 x 3.0 mm, 26 mm inside / 32 mm outside (centres +-14.5 mm),
body 16 x 28.6 mm. "+" is the pad marked + on the drawing's layout view. Placed upright where the 3034 was, centre
(58.915, 141.0). All BT1 copper is removed; BT1+ and the GND pad fanout are rerouted afterwards."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
f = b.FindFootprintByReference('BT1')
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
vp, gnd = nets['Net-(BT1-+)'], nets['GND']
# copper of the old holder
T = b.Tracks(); tracks = [T[i] for i in range(T.size())]
gone = [x for x in tracks if x.GetNetname() == 'Net-(BT1-+)']
p2 = [p for p in f.Pads() if p.GetNumber() == '2'][0]
for x in tracks:
    if x.GetNetname() == 'GND' and x.Type() != pcbnew.PCB_VIA_T and (p2.HitTest(x.GetStart()) or p2.HitTest(x.GetEnd())):
        gone.append(x)
        for v in tracks:
            if v.Type() == pcbnew.PCB_VIA_T and v.GetNetname() == 'GND' and (v.GetPosition() == x.GetStart() or v.GetPosition() == x.GetEnd()):
                gone.append(v)
for x in gone: b.Remove(x)
# rebuild the footprint in place (keeps its symbol link, fields and uuid)
f.SetOrientationDegrees(0)
f.SetPosition(pcbnew.VECTOR2I(MM(58.915), MM(141.0)))
o = f.GetPosition()
old_p = list(f.Pads())
for p in old_p: f.Remove(p)
G = f.GraphicalItems(); old_g = [G[i] for i in range(len(G))]
for g in old_g: f.Remove(g)
Z = f.Zones(); old_z = [Z[i] for i in range(len(Z))]
for z in old_z: f.Remove(z)
for num, y, net in (('1', 14.5, vp), ('2', -14.5, gnd)):
    p = pcbnew.PAD(f); p.SetNumber(num); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD); p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    p.SetRoundRectRadiusRatio(0.1); p.SetSize(pcbnew.VECTOR2I(MM(4.2), MM(3.0)))
    p.SetLayerSet(p.SMDMask())
    f.Add(p); p.SetPosition(o + pcbnew.VECTOR2I(0, MM(y))); p.SetNet(net)
def rect(layer, w, h, width):
    for (x1, y1, x2, y2) in ((-w, -h, w, -h), (w, -h, w, h), (w, h, -w, h), (-w, h, -w, -h)):
        s = pcbnew.PCB_SHAPE(f, pcbnew.SHAPE_T_SEGMENT); s.SetLayer(layer); s.SetWidth(MM(width))
        s.SetStart(o + pcbnew.VECTOR2I(MM(x1), MM(y1))); s.SetEnd(o + pcbnew.VECTOR2I(MM(x2), MM(y2))); f.Add(s)
rect(pcbnew.F_Fab, 8.0, 14.3, 0.1)
rect(pcbnew.F_CrtYd, 8.5, 16.5, 0.05)
for (x1, y1, x2, y2) in ((-8.1, -12.4, -8.1, 12.4), (8.1, -12.4, 8.1, 12.4)):
    s = pcbnew.PCB_SHAPE(f, pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.F_SilkS); s.SetWidth(MM(0.12))
    s.SetStart(o + pcbnew.VECTOR2I(MM(x1), MM(y1))); s.SetEnd(o + pcbnew.VECTOR2I(MM(x2), MM(y2))); f.Add(s)
t = pcbnew.PCB_TEXT(f); t.SetText('+'); t.SetLayer(pcbnew.F_SilkS); t.SetPosition(o + pcbnew.VECTOR2I(MM(3.6), MM(11.6)))
t.SetTextSize(pcbnew.VECTOR2I(MM(1.5), MM(1.5))); t.SetTextThickness(MM(0.2)); f.Add(t)
f.SetFPID(pcbnew.LIB_ID('sam_cpu', 'BatteryHolder_Lianxin_XDCR-2032-603'))
f.Models().clear()
f.Reference().SetPosition(o + pcbnew.VECTOR2I(MM(-5.5), MM(-17.3)))
f.Value().SetPosition(o); f.Value().SetLayer(pcbnew.F_Fab)
keep = tracks
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
print('removed', len(gone), 'items')

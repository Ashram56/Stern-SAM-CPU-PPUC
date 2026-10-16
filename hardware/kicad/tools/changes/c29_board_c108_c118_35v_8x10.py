"""c29: C108/C118 (470 uF on +12 V) 16 V 6.3x7.7 -> 35 V 8x10 can (Vincent's card: "35 V, 8x10"; RV35V470M8X10,
LCSC C48935389). C108 / C118 get CP_Elec_8x10 with their tops where they were (they grow down, still clear of the heatsink area
from y 71), packed between C4 and Q4. +12V track ends on the old pads follow to the new pad centres; the old GND pad
stubs and vias go (route/fanout_vias.py gives the new GND pads theirs). The +12V feed under C108 drops to y 68.6
to clear the bigger GND pad, and C4's GND via moves below its pad, away from C108 pad 1."""
import os, sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM
LIB = os.path.join(os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/kicad10/root/usr/share/kicad/footprints'),
                   'Capacitor_SMD.pretty')
T = b.Tracks(); tracks = [T[i] for i in range(T.size()) if T[i].Type() != pcbnew.PCB_VIA_T]
keep = []
def follow(old_pads, new_pos):
    """old_pads: [(PAD, number)], new_pos: {number: VECTOR2I}"""
    for p, num in old_pads:
        for t in tracks:
            if p.HitTest(t.GetStart()): t.SetStart(new_pos[num])
            if p.HitTest(t.GetEnd()): t.SetEnd(new_pos[num])
# C108 / C118: new footprint from the KiCad library, same symbol link and fields
for ref, x in (('C108', 109.05), ('C118', 119.7)):
    f = b.FindFootprintByReference(ref)
    n = pcbnew.FootprintLoad(LIB, 'CP_Elec_8x10')
    n.SetParent(b); n.SetFPID(pcbnew.LIB_ID('Capacitor_SMD', 'CP_Elec_8x10'))
    n.SetReference(ref); n.SetValue(f.GetValue()); n.SetPath(f.GetPath())
    n.Reference().SetVisible(f.Reference().IsVisible())
    n.SetPosition(pcbnew.VECTOR2I(MM(x), MM(61.6 + 4.45)))
    nets = {p.GetNumber(): p.GetNet() for p in f.Pads()}
    for p in n.Pads(): p.SetNet(nets[p.GetNumber()])
    g = [p for p in f.Pads() if p.GetNetname() == 'GND'][0]
    stubs = [t for t in tracks if t.GetNetname() == 'GND' and (g.HitTest(t.GetStart()) or g.HitTest(t.GetEnd()))]
    ends = [e for t in stubs for e in (t.GetStart(), t.GetEnd())]
    vias = [v for v in (T[i] for i in range(T.size())) if v.Type() == pcbnew.PCB_VIA_T and v.GetNetname() == 'GND' and v.GetPosition() in ends]
    for x in stubs + vias: tracks.remove(x) if x in tracks else None; keep.append(x); b.Remove(x)
    follow([(p, p.GetNumber()) for p in f.Pads() if p.GetNetname() != 'GND'], {p.GetNumber(): p.GetPosition() for p in n.Pads()})
    for fld in f.GetFields():
        if fld.GetName() not in ('Reference', 'Value', 'Footprint') and not n.HasField(fld.GetName()):
            c = pcbnew.PCB_FIELD(fld); c.SetParent(n); n.AddField(c)
    n.SetLocked(f.IsLocked())
    keep.append(f); b.Remove(f); b.Add(n)
def at(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
def near(a, x, y): return abs(a.x - MM(x)) < MM(0.02) and abs(a.y - MM(y)) < MM(0.02)
OLD12 = [((105.8, 66.05), (109.4, 67.55)), ((109.4, 67.55), (114.78, 67.55)), ((114.78, 67.55), (116.45, 66.05)),
         ((114.53, 89.14), (114.53, 67.55))]
v12 = b.FindNet('+12V')
for t in list(tracks):
    if t.GetNetname() == '+12V' and any(near(t.GetStart(), *a) and near(t.GetEnd(), *c) for a, c in OLD12):
        tracks.remove(t); keep.append(t); b.Remove(t)
for a, c in (((105.8, 66.05), (108.35, 68.6)), ((108.35, 68.6), (116.45, 68.6)), ((116.45, 68.6), (116.45, 66.05)),
             ((114.53, 89.14), (114.53, 70.52)), ((114.53, 70.52), (116.45, 68.6))):
    t = pcbnew.PCB_TRACK(b); t.SetStart(at(*a)); t.SetEnd(at(*c)); t.SetWidth(MM(0.8)); t.SetLayer(pcbnew.F_Cu)
    t.SetNet(v12); b.Add(t)
T = b.Tracks()
for x in [T[i] for i in range(T.size())]:
    if x.GetNetname() != 'GND': continue
    if x.Type() == pcbnew.PCB_VIA_T and near(x.GetPosition(), 103.94, 64.59): x.SetPosition(at(102.6, 66.8))
    elif x.Type() != pcbnew.PCB_VIA_T and near(x.GetStart(), 101.64, 64.59) and near(x.GetEnd(), 103.94, 64.59): x.SetEnd(at(102.6, 66.8))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
print('done')
# schematic: audio.kicad_sch Footprint fields (pass the sheet path as the third argument)
if len(sys.argv) > 3:
    s = open(sys.argv[3]).read()
    assert s.count('(property "Footprint" "Capacitor_SMD:CP_Elec_6.3x7.7"') == 2
    open(sys.argv[3], 'w').write(s.replace('(property "Footprint" "Capacitor_SMD:CP_Elec_6.3x7.7"',
                                           '(property "Footprint" "Capacitor_SMD:CP_Elec_8x10"'))

"""c32: J19 / J30 to parts JLCPCB stocks (the HRO TYPE-C-31-M-12 and CUI SJ1-3535NG have none).
J19 -> SHOU HAN SH-U262-161N-4BVC11 (C22383468), a TYPE-C-31-M-12 clone: same signal pads and front slots (within
0.05 mm), but its drawing asks for longer rear shell slots (pad 1.8 / drill 1.4 instead of 1.6 / 1.2), so only those
two pads change. Footprint sam_cpu:USB_C_Receptacle_SH_U262-161N-4BVC11.
J30 -> PJ-393-7A SMD 3.5 mm stereo jack with switched tip and ring (C128990). Footprint from the maker's drawing:
pads 1.4 x 2.5, one row at 2.70 / 5.80 / 8.55 / 10.80 mm behind the front face (pins 1, 4, 3, 5), the other at
3.60 / 6.45 / 8.70 (pins 7, 6, 2), rows 6.7 mm apart (centres), two 1.2 mm pegs 2.2 / 9.2 mm behind the front on the
centre line, body 13.2 x 6.0, 1.3 mm nose. Pin use from the drawing's schematic: 1 sleeve, 4 tip with break 7, 3 ring
with break 6; 2 / 5 is a plug-detect switch (unused). The schematic symbol keeps its S / T / TN / R / RN pins, so the
pads are numbered with those names. Front face on the right board edge (x 150.65), same height as before.
All copper on the old J30 pads is removed; its nets are rerouted afterwards. The jack sits 0.2 mm lower than the old
one so its courtyard clears R186. Three nets ran straight through the new pad rows on F.Cu: +12V now drops to B.Cu
under the jack (via at 145.21 / 115.2), and the I2S_DIN / FRAME_SCK runs and the old AUD_AMP_L/R B.Cu stubs there are
cut back and hand-routed: I2S_DIN and FRAME_SCK pass under the jack on B.Cu either side of +12V, AUD_AMP_L/R
come up through vias between the pad rows, AUD_DAC_L crosses +12V on B.Cu above the jack and comes down between
the T and S pads. AUD_DAC_R stays open as before (its U22 end was never routed).
Both footprints go into sam_cpu.pretty and the schematic Footprint fields point at them (pass the project directory
as the third argument). Afterwards: route/fanout_vias.py out out GND J30:S.
Usage: c32_j19_j30_stocked.py in.kicad_pcb out.kicad_pcb [project_dir]"""
import os
import sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM
keep = []
# J19: rear shell slots
j = b.FindFootprintByReference('J19')
for p in j.Pads():
    if p.GetNumber() == 'SH' and p.GetSize().y < MM(1.9) and abs(p.GetSize().y - MM(1.6)) < MM(0.01):
        p.SetSize(pcbnew.VECTOR2I(MM(1.0), MM(1.8))); p.SetDrillSize(pcbnew.VECTOR2I(MM(0.6), MM(1.4)))
j.SetFPID(pcbnew.LIB_ID('sam_cpu', 'USB_C_Receptacle_SH_U262-161N-4BVC11'))
j.SetKeywords('USB C receptacle 16P'); j.SetLibDescription('USB-C 16P receptacle, SHOU HAN SH-U262-161N-4BVC11 (LCSC C22383468); HRO TYPE-C-31-M-12 pattern, rear slots 1.4 mm')
# J30
f = b.FindFootprintByReference('J30')
nets = {p.GetNumber(): p.GetNet() for p in f.Pads()}
T = b.Tracks(); tr = [T[i] for i in range(T.size())]
gone = []
for x in tr:
    pts = [x.GetPosition()] if x.Type() == pcbnew.PCB_VIA_T else [x.GetStart(), x.GetEnd()]
    if any(p.HitTest(q) for p in f.Pads() for q in pts): gone.append(x)
for x in gone: b.Remove(x)
for p in list(f.Pads()): keep.append(p); f.Remove(p)
G = f.GraphicalItems(); g0 = [G[i] for i in range(len(G))]; keep += g0
for g in g0: f.Remove(g)
f.Models().clear()
f.SetOrientationDegrees(0)
FX, FY = 150.65, 121.45
f.SetPosition(pcbnew.VECTOR2I(MM(FX), MM(FY))); o = f.GetPosition()
def at(lx, ly): return o + pcbnew.VECTOR2I(MM(lx), MM(ly))
PADS = [('S', -2.70, -3.35), ('T', -5.80, -3.35), ('R', -8.55, -3.35), ('', -10.80, -3.35),
        ('TN', -3.60, 3.35), ('RN', -6.45, 3.35), ('', -8.70, 3.35)]
for num, x, y in PADS:
    p = pcbnew.PAD(f); p.SetNumber(num); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD); p.SetShape(pcbnew.PAD_SHAPE_RECTANGLE)
    p.SetSize(pcbnew.VECTOR2I(MM(1.4), MM(2.5))); p.SetLayerSet(p.SMDMask()); f.Add(p); p.SetPosition(at(x, y))
    if num: p.SetNet(nets[num])
for x in (-2.2, -9.2):
    p = pcbnew.PAD(f); p.SetNumber(''); p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(pcbnew.VECTOR2I(MM(1.2), MM(1.2))); p.SetDrillSize(pcbnew.VECTOR2I(MM(1.2), MM(1.2)))
    p.SetLayerSet(p.UnplatedHoleMask()); f.Add(p); p.SetPosition(at(x, 0))
def seg(layer, x1, y1, x2, y2, w):
    s = pcbnew.PCB_SHAPE(f, pcbnew.SHAPE_T_SEGMENT); s.SetLayer(layer); s.SetWidth(MM(w))
    s.SetStart(at(x1, y1)); s.SetEnd(at(x2, y2)); f.Add(s)
def rect(layer, x1, y1, x2, y2, w):
    for a in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)): seg(layer, *a, w)
rect(pcbnew.F_Fab, -13.2, -3.0, 0, 3.0, 0.1); rect(pcbnew.F_Fab, 0, -2.75, 1.3, 2.75, 0.1)
rect(pcbnew.F_CrtYd, -13.45, -4.85, 1.55, 4.85, 0.05)
for a in ((-13.3, -1.8, -13.3, 1.8), (-12.0, 3.1, -9.6, 3.1)):
    seg(pcbnew.F_SilkS, *a, 0.12)
f.SetFPID(pcbnew.LIB_ID('sam_cpu', 'Jack_3.5mm_PJ-393-7A_Horizontal'))
f.SetKeywords('audio jack 3.5mm stereo switched'); f.SetLibDescription('3.5 mm stereo jack, SMD, switched tip and ring, PJ-393-7A (LCSC C128990); pads S/T/R/TN/RN = pins 1/4/3/7/6')
f.Reference().SetPosition(at(-7.0, -6.0)); f.Value().SetPosition(at(-7.0, 0)); f.Value().SetLayer(pcbnew.F_Fab)
# tracks through the new pads: cut (segments given by their end points, mm)
def near(a, x, y): return abs(a.x - MM(x)) < MM(0.02) and abs(a.y - MM(y)) < MM(0.02)
def pt(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
CUT = {'+12V': [((145.21, 108.76), (145.21, 121.99)), ((145.21, 121.99), (145.21, 123.85)), ((145.21, 123.85), (142.56, 126.5)),
                ((142.56, 126.5), (142.52, 126.5))],
       'I2S_DIN': [((140.08, 124.45), (140.08, 115.09)), ((141.51, 125.88), (140.08, 124.45))],
       'FRAME_SCK': [((147.91, 121.85), (147.83, 121.77)), ((147.91, 125.26), (147.91, 121.85)), ((147.91, 125.26), (142.08, 131.08))],
       'AUD_AMP_R': [((140.78, 121.59), (141.25, 121.59)), ((139.43, 122.94), (140.78, 121.59))],
       'AUD_AMP_L': [((138.83, 124.9), (141.74, 124.9)), ((141.74, 124.9), (141.76, 124.88)), ((141.76, 124.88), (142.3, 124.88)),
                     ((142.3, 124.88), (142.32, 124.9)), ((142.32, 124.9), (146.75, 124.9))]}
SHORTEN = {'I2S_DIN': ((141.51, 125.88), (141.51, 129.5)), 'FRAME_SCK': ((147.83, 121.77), (147.83, 114.5)),
           'AUD_DAC_L': ((139.07, 118.08), (139.07, 114.2))}
CUT['AUD_DAC_L'] = [((137.56, 119.59), (139.07, 118.08))]
T = b.Tracks(); tr = [T[i] for i in range(T.size())]; cut = 0; via12 = None
for x in tr:
    n = x.GetNetname()
    if x.Type() == pcbnew.PCB_VIA_T:
        if n == '+12V' and near(x.GetPosition(), 142.52, 126.5): x = x.Cast(); via12 = (x.GetWidth(pcbnew.F_Cu), x.GetDrill()); b.Remove(x); cut += 1
        continue
    for a, c in CUT.get(n, []):
        if (near(x.GetStart(), *a) and near(x.GetEnd(), *c)) or (near(x.GetStart(), *c) and near(x.GetEnd(), *a)):
            b.Remove(x); cut += 1; break
    else:
        if n in SHORTEN:
            old, new = SHORTEN[n]
            if near(x.GetStart(), *old): x.SetStart(pt(*new)); cut += 1
            elif near(x.GetEnd(), *old): x.SetEnd(pt(*new)); cut += 1
assert cut == 21 and via12, cut
v12 = b.FindNet('+12V')
for ly, a, c in ((pcbnew.B_Cu, (142.52, 126.5), (145.21, 126.5)), (pcbnew.B_Cu, (145.21, 126.5), (145.21, 115.2)),
                 (pcbnew.F_Cu, (145.21, 115.2), (145.21, 108.76))):
    t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(0.8)); t.SetLayer(ly); t.SetNet(v12); b.Add(t)
v = pcbnew.PCB_VIA(b); v.SetPosition(pt(145.21, 115.2)); v.SetWidth(via12[0]); v.SetDrill(via12[1])
v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(v12); b.Add(v)
F, B = pcbnew.F_Cu, pcbnew.B_Cu
ROUTE = {'I2S_DIN': [(B, [(140.08, 115.09), (143.08, 115.09), (143.08, 122.6)]),
                     (F, [(143.08, 122.6), (143.08, 127.0), (141.51, 128.57), (141.51, 129.5)])],
         'FRAME_SCK': [(B, [(147.83, 114.5), (147.2, 115.13), (147.2, 127.6), (144.5, 127.6)]),
                       (F, [(144.5, 127.6), (144.5, 128.66), (142.08, 131.08)])],
         'AUD_AMP_R': [(B, [(139.43, 122.94), (140.2, 122.17), (140.2, 120.35), (140.6, 119.95)]),
                       (F, [(140.6, 119.95), (141.0, 119.55), (141.0, 118.3), (142.1, 118.3)])],
         'AUD_AMP_L': [(B, [(138.83, 124.9), (143.95, 124.9), (143.95, 120.3)]),
                       (F, [(143.95, 120.3), (144.85, 119.4), (144.85, 118.3)])],
         'AUD_DAC_L': [(B, [(139.07, 114.2), (146.4, 114.2)]),
                       (F, [(146.4, 114.2), (146.4, 123.0), (147.05, 123.65), (147.05, 124.8)])]}
VIAS = {'I2S_DIN': [(140.08, 115.09), (143.08, 122.6)], 'FRAME_SCK': [(147.83, 114.5), (144.5, 127.6)],
        'AUD_AMP_R': [(140.6, 119.95)], 'AUD_AMP_L': [(143.95, 120.3)], 'AUD_DAC_L': [(146.4, 114.2)]}
for n, runs in ROUTE.items():
    net = b.FindNet(n)
    for ly, pts in runs:
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(0.2)); t.SetLayer(ly); t.SetNet(net); b.Add(t)
    for x, y in VIAS[n]:
        v = pcbnew.PCB_VIA(b); v.SetPosition(pt(x, y)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3))
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(F, B); v.SetNet(net); b.Add(v)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
print('J30 copper removed', len(gone))
if len(sys.argv) > 3:
    d = sys.argv[3]; io = pcbnew.PCB_IO_KICAD_SEXPR()
    for ref in ('J19', 'J30'):
        f = pcbnew.FOOTPRINT(b.FindFootprintByReference(ref))
        f.SetOrientationDegrees(0); f.SetPosition(pcbnew.VECTOR2I(0, 0)); f.SetLocked(False)
        for p in f.Pads(): p.SetNetCode(0)
        f.SetReference('REF**'); f.SetValue(f.GetFPID().GetUniStringLibItemName()); f.SetPath(pcbnew.KIID_PATH())
        for fld in list(f.GetFields()):
            if fld.GetName() not in ('Reference', 'Value', 'Footprint', 'Datasheet', 'Description'): f.RemoveField(fld.GetName())
        io.FootprintSave(os.path.join(d, 'sam_cpu.pretty'), f)
    for fn, a, c in (('mcu.kicad_sch', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12', 'sam_cpu:USB_C_Receptacle_SH_U262-161N-4BVC11'),
                     ('rs485_i2s.kicad_sch', 'Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal', 'sam_cpu:Jack_3.5mm_PJ-393-7A_Horizontal')):
        p = os.path.join(d, fn); t = open(p).read()
        assert t.count('(property "Footprint" "%s"' % a) == 1, fn
        open(p, 'w').write(t.replace('(property "Footprint" "%s"' % a, '(property "Footprint" "%s"' % c))

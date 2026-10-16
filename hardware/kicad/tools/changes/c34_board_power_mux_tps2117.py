"""c34 (board): power mux to one TPS2117 (schematic in c33). U2, Q1 and Q2 go; U1 becomes SOT-583-8 in the old
Q1 / Q2 spot, where the external +5 V (from D1), the J11 +5 V (B.Cu, from JP1) and the +5V bus all pass.
U1 at (99.75, 103.85), 270 deg: top row PR1 / VIN1 / VOUT / GND, bottom row MODE / VIN2 / VOUT / ST.
- VIN1: the external +5 V track from D1 comes straight down x 99.5, narrowed to 0.3 mm for the last 0.9 mm.
- MODE: tied to VIN1 under the body. VOUT: both pins bridged, then down to the +5V bus at y 106.6.
- VIN2: stub to a via on the J11 B.Cu track. GND: down the east side to a via (planes).
- PR1: the R1 / R2 divider moves from (101-105, 60) to U1 (PR1 is too long and crowded to route back up there):
  R1 (now 0402, EXT_5V - PR1) stands upright at (97.85, 102.6) between F1 and the EXT_5V track, beside PR1;
  R2 (0603, PR1 - GND) sits east of U1 at (103.2, 104.4), its GND pad tied to the U1 GND track. PR1 crosses under
  U1 on B.Cu (y 104.3, between +4V5 and the J11 / GND vias). The +4V5 via west of U1 moves to (97.7, 103.95).
Nets: Net-(D1-A1) -> /Power/EXT_5V, Net-(JP1-B) -> /Power/J11_5V, Net-(U2-CTL) -> Net-(U1-PR1); the gate nets
go. Copper left dangling by the removed parts (old U1 / U2 / Q1 / Q2 pins) is removed. EXT_5V and J11_5V move from
the Power_HI class (0.25 mm clearance, too wide for the 0.5 mm pitch pins) to Power_5V (0.2 mm, like +5V).
R2 is 33k now.
Usage: c34_board_power_mux_tps2117.py in.kicad_pcb out.kicad_pcb (run where the project files are; it edits
sam_cpu.kicad_pro beside out.kicad_pcb)"""
import os, sys
pro = os.path.join(os.path.dirname(os.path.abspath(sys.argv[2])), 'sam_cpu.kicad_pro')
t = open(pro).read()
for old, new in (('Net-(D1-A1)', '/Power/EXT_5V'), ('Net-(JP1-B)', '/Power/J11_5V')):
    a = '"netclass": "Power_HI",\n        "pattern": "%s"' % old
    if a in t: t = t.replace(a, '"netclass": "Power_5V",\n        "pattern": "%s"' % new)
open(pro, 'w').write(t)
import pcbnew
LIB = os.path.join(os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/kicad10/root/usr/share/kicad/footprints'), 'Package_TO_SOT_SMD.pretty')
U1FP = pcbnew.FootprintLoad(LIB, 'SOT-583-8')       # before the board is loaded (the plugin lookup fails after)
R1FP = pcbnew.FootprintLoad(LIB.replace('Package_TO_SOT_SMD', 'Resistor_SMD'), 'R_0402_1005Metric')
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM
FP = {f.GetReference(): f for f in b.GetFootprints()}; u1old = FP['U1']
def pt(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
def near(a, x, y, tol=0.02): return abs(a.x - MM(x)) < MM(tol) and abs(a.y - MM(y)) < MM(tol)
keep = []       # removed items stay referenced: freeing them from Python corrupts the board's objects
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
def newnet(name):
    if name in nets: return nets[name]
    n = pcbnew.NETINFO_ITEM(b, name); b.Add(n); nets[name] = n; return n
# renames
for old, new in (('Net-(D1-A1)', '/Power/EXT_5V'), ('Net-(JP1-B)', '/Power/J11_5V'), ('Net-(U2-CTL)', 'Net-(U1-PR1)')):
    o = nets[old]; n = newnet(new)
    T = b.Tracks()
    for x in [T[i] for i in range(T.size())] + [p for f in b.GetFootprints() for p in f.Pads()]:
        if x.GetNetCode() == o.GetNetCode(): x.SetNet(n)
EXT, J11, PR1, V5, GND = (nets[n] for n in ('/Power/EXT_5V', '/Power/J11_5V', 'Net-(U1-PR1)', '+5V', 'GND'))
# tracks of the gate nets, all of PR1 (old U2-CTL route and the R1 - R2 link) and the EXT stub into the old Q1 drain
T = b.Tracks()
for x in [T[i] for i in range(T.size())]:
    n = x.GetNetname()
    if n in ('Net-(Q1-G)', 'Net-(Q2-G)'): keep.append(x); b.Remove(x); continue
    if n == 'Net-(U1-PR1)': keep.append(x); b.Remove(x); continue     # all of it, R1 / R2 move to U1
    if n == 'GND' and ((x.Type() == pcbnew.PCB_VIA_T and near(x.GetPosition(), 106.625, 60.065)) or
                       (x.Type() != pcbnew.PCB_VIA_T and near(x.GetStart(), 105.6, 60.06))):    # old R2 GND stub
        keep.append(x); b.Remove(x); continue
    if n == '/Power/EXT_5V' and x.Type() != pcbnew.PCB_VIA_T:
        if near(x.GetStart(), 98.6, 105.39) or near(x.GetEnd(), 98.6, 105.39): keep.append(x); b.Remove(x); continue
        for e, s in ((x.GetEnd(), x.SetEnd), (x.GetStart(), x.SetStart)):     # trunk from D1 now ends at 102.2
            if near(e, 99.5, 104.5): s(pt(99.5, 102.2))
    if n == '/Power/J11_5V' and x.Type() != pcbnew.PCB_VIA_T:
        if near(x.GetStart(), 103.15, 105.39) or near(x.GetEnd(), 103.15, 105.39) or \
           (near(x.GetStart(), 104.45, 104.73) and near(x.GetEnd(), 103.81, 104.73)): keep.append(x); b.Remove(x)
# parts
for ref in ('U2', 'Q1', 'Q2'):
    f = FP[ref]; keep.append(f); b.Remove(f)
u = U1FP; u.SetParent(b); u.SetFPID(pcbnew.LIB_ID('Package_TO_SOT_SMD', 'SOT-583-8'))
u.SetReference('U1'); u.SetValue('TPS2117'); u.SetPath(u1old.GetPath())
u.SetPosition(pt(99.75, 103.85)); u.SetOrientationDegrees(270)
u.Reference().SetPosition(pt(99.75, 105.75)); u.Reference().SetTextAngleDegrees(0)
for name, val in (('Datasheet', 'https://www.ti.com/lit/ds/symlink/tps2117.pdf'),
                  ('Description', '2:1 power mux with priority, 1.6-5.5 V, 4 A, 20 mOhm, TPS2117DRLR (LCSC C22399676)')):
    fld = u.GetField(name) if u.HasField(name) else None
    if fld: fld.SetText(val)
    else:
        fld = pcbnew.PCB_FIELD(u, pcbnew.FIELD_T_USER, name); fld.SetText(val); fld.SetVisible(False); u.AddField(fld)
u.SetLibDescription('TPS2117 power mux, SOT-583-8 (DRL)')
keep.append(u1old); b.Remove(u1old); b.Add(u)
st = newnet('unconnected-(U1-ST-Pad8)')
PADNET = {'1': GND, '2': V5, '3': EXT, '4': PR1, '5': EXT, '6': J11, '7': V5, '8': st}
for p in u.Pads(): p.SetNet(PADNET[p.GetNumber()])
r1old = FP['R1']; r = R1FP; r.SetParent(b); r.SetFPID(pcbnew.LIB_ID('Resistor_SMD', 'R_0402_1005Metric'))
r.SetReference('R1'); r.SetValue(r1old.GetValue()); r.SetPath(r1old.GetPath())
r.SetPosition(pt(97.85, 102.6)); r.SetOrientationDegrees(270)                       # pad 1 (EXT_5V) at the top
r.Reference().SetPosition(pt(96.2, 104.0)); r.Reference().SetTextAngleDegrees(0)
for name in ('Datasheet', 'Description'):
    if r1old.HasField(name) and r1old.GetField(name).GetText():
        if r.HasField(name): r.GetField(name).SetText(r1old.GetField(name).GetText())
        else:
            fld = pcbnew.PCB_FIELD(r, pcbnew.FIELD_T_USER, name); fld.SetText(r1old.GetField(name).GetText())
            fld.SetVisible(False); r.AddField(fld)
keep.append(r1old); b.Remove(r1old); b.Add(r)
for p in r.Pads(): p.SetNet(EXT if p.GetNumber() == '1' else PR1)
r2 = FP['R2']; r2.SetValue('33k'); r2.SetPosition(pt(103.2, 104.4)); r2.SetOrientationDegrees(180)   # pad 1 (PR1) east
r2.Reference().SetPosition(pt(103.2, 105.6)); r2.Reference().SetTextAngleDegrees(0)
# copper at U1
F, B = pcbnew.F_Cu, pcbnew.B_Cu
def track(net, ly, pts, w):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(w)); t.SetLayer(ly); t.SetNet(net); b.Add(t)
def via(net, x, y, d=0.6, h=0.3):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pt(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(h))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(F, B); v.SetNet(net); b.Add(v)
track(EXT, F, [(99.5, 102.2), (99.5, 103.11)], 0.3)                                   # VIN1
track(EXT, F, [(99.5, 103.11), (99.5, 103.55), (99.0, 104.05), (99.0, 104.59)], 0.15)  # MODE
track(V5, F, [(100.0, 103.11), (100.0, 104.59), (100.0, 106.6)], 0.3)                  # VOUT
track(J11, F, [(99.5, 104.59), (99.5, 105.25), (99.15, 105.6)], 0.3)                   # VIN2
via(J11, 99.15, 105.6); track(J11, B, [(99.15, 105.6), (100.15, 106.7)], 0.8)
track(EXT, F, [(97.85, 102.09), (99.5, 102.09)], 0.3)                                # R1 pad 1 to the EXT_5V track
track(PR1, F, [(97.85, 103.11), (99.0, 103.11)], 0.2)                # R1 pad 2 to U1 PR1
track(PR1, F, [(98.3, 103.11), (98.3, 104.6)], 0.2); via(PR1, 98.3, 104.6)
track(PR1, B, [(98.3, 104.6), (98.6, 104.3), (103.2, 104.3), (104.025, 105.125), (104.025, 105.45)], 0.2)
via(PR1, 104.025, 105.45); track(PR1, F, [(104.025, 105.45), (104.025, 104.4)], 0.2)  # up to R2 pad 1
track(GND, F, [(102.375, 104.4), (101.4, 104.4)], 0.3)                              # R2 pad 2 to the U1 GND track
# +4V5 used to pass right beside PR1 (via 98.55 / 102.29 and down x 98.55): its via moves to 97.7 / 103.95
P45 = nets['+4V5']; T = b.Tracks()
for x in [T[i] for i in range(T.size())]:
    if x.GetNetname() != '+4V5': continue
    if x.Type() == pcbnew.PCB_VIA_T:
        if near(x.GetPosition(), 98.55, 102.29): keep.append(x); b.Remove(x)
    elif any((near(x.GetStart(), *a) and near(x.GetEnd(), *c)) or (near(x.GetStart(), *c) and near(x.GetEnd(), *a)) for a, c in
             (((98.55, 102.29), (98.55, 103.96)), ((98.55, 103.96), (97.58, 104.93)), ((98.55, 102.29), (99.93, 103.67)))):
        keep.append(x); b.Remove(x)
via(P45, 97.7, 103.95)
track(P45, F, [(97.7, 103.95), (97.7, 104.81), (97.58, 104.93)], 0.25)
track(P45, B, [(97.7, 103.95), (97.98, 103.67), (99.93, 103.67)], 0.25)
track(GND, F, [(100.5, 103.11), (101.1, 103.11), (101.4, 103.41), (101.4, 105.1)], 0.3); via(GND, 101.4, 105.1)
# dangling copper of the power nets (old pins), repeatedly
def on_seg(q, o):
    a, c = o.GetStart(), o.GetEnd(); d = c - a; L2 = d.x * d.x + d.y * d.y
    if L2 == 0: return (q - a).EuclideanNorm() < MM(0.01)
    t = max(0, min(1, ((q.x - a.x) * d.x + (q.y - a.y) * d.y) / L2))
    return ((q.x - a.x - t * d.x) ** 2 + (q.y - a.y - t * d.y) ** 2) ** 0.5 < MM(0.01)
for net in (EXT, J11, V5, PR1):
    while True:
        T = b.Tracks(); items = [T[i] for i in range(T.size()) if T[i].GetNetCode() == net.GetNetCode()]
        pads = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode() == net.GetNetCode()]
        zones = [z for z in b.Zones() if z.GetNetCode() == net.GetNetCode()]
        def touched(q, me):
            if any(p.HitTest(q) for p in pads): return True
            for o in items:
                if o is me: continue
                if o.Type() == pcbnew.PCB_VIA_T:
                    if (o.GetPosition() - q).EuclideanNorm() <= o.Cast().GetWidth(F) // 2: return True
                elif on_seg(q, o): return True
            return False
        gone = [x for x in items if x.Type() != pcbnew.PCB_VIA_T and x.GetLength() < MM(0.01)
                and not any(p.HitTest(x.GetStart()) for p in pads)]
        if gone:
            for x in gone: keep.append(x); b.Remove(x)
            continue
        for x in items:
            if x.Type() == pcbnew.PCB_VIA_T:
                q = x.GetPosition()
                n = sum(1 for o in items if o is not x and o.Type() != pcbnew.PCB_VIA_T and (o.GetStart() == q or o.GetEnd() == q))
                if n <= 1 and not any(p.HitTest(q) for p in pads) and not zones: gone.append(x)
            elif not (touched(x.GetStart(), x) and touched(x.GetEnd(), x)): gone.append(x)
        if not gone: break
        for x in gone: keep.append(x); b.Remove(x)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
print('ok')

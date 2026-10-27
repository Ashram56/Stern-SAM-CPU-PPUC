"""c43 (board): clean +12 V rail and Pi buck (schematic in c42), all outside the DeepPCB cut except JP3.
- 12 V OR, by J23 (x 124.6-137.3, y 49.5-61.4, F.Cu): Q20 (IO side, 180 deg) and Q19 (EXT side, 0 deg) at y 59.2
  with their sources facing each other, U34 / U33 above them, the U34 CTL divider R213 / R214 in the pocket by C5.
  The old J23 -> F1 copper becomes /Power/12V_OR: its B.Cu diagonal from J23 goes, a via between the FETs drops on
  B.Cu x 131 to the old y 71.73 track. J23 pad 1 (EXT_12V) reaches the Q19 drain on B.Cu y 61, J11 pad 6 (IO_12V)
  the Q20 drain on F.Cu (down x 108.21, along y 46.9, down x 124.9).
  The +5V B.Cu link from the C5 via now runs along y 51.38 before turning down to y 55.4, to free B.Cu under U34;
  two dangling GND stubs and vias by U34 (no pad) go.
- Pi buck, under the Pi (x 126.6-136.4, y 127-157): U35 (90 deg) with Cin C133 below it, the SW node straight down
  between the C133 pads to L2, Cout C135 / C136, JP4 (BUCK), the FB divider R215 / R216 and C134 above. +12V comes
  up from the B.Cu y 132.58 track through two vias, the Vout sense runs up F.Cu x 136.1 to R215.
- JP3 (BOARD) cuts the locked +5V trunk to J21 at y 112 (inside the cut); the trunk below it and J21 pins 2 / 4 are
  PI_5V, which also gets the JP4 output on B.Cu y 155.3 to a via on the trunk at x 109.
Net classes: Power_12V (0.8 mm, 0.2 clearance: the PowerDI3333 gate pad is 0.23 mm from a source pad) for the three
12 V inputs and outputs of the OR, Power_PI (1.2 mm, 0.2) for PI_5V, the buck output and SW.
Usage: c43_board_12v_or_pi_buck.py in.kicad_pcb out.kicad_pcb sam_cpu_dir (run where the project files are; it
edits sam_cpu.kicad_pro beside out.kicad_pcb and reads the symbol uuids from power.kicad_sch)"""
import os, re, sys, json
SCH = os.path.join(sys.argv[3], 'power.kicad_sch')
pro = os.path.join(os.path.dirname(os.path.abspath(sys.argv[2])), 'sam_cpu.kicad_pro')
P = json.load(open(pro)); ns = P['net_settings']
hi = next(c for c in ns['classes'] if c['name'] == 'Power_HI')
for name, w, cl in (('Power_12V', 0.8, 0.2), ('Power_PI', 1.2, 0.2)):
    if not any(c['name'] == name for c in ns['classes']):
        c = dict(hi); c.update(name=name, track_width=w, clearance=cl, via_diameter=0.8, via_drill=0.4); ns['classes'].append(c)
pats = [p for p in ns['netclass_patterns'] if p['pattern'] != 'Net-(J23-Pin_1)']
for cls, pat in (('Power_12V', '/Power/EXT_12V'), ('Power_12V', '/Power/IO_12V'), ('Power_12V', '/Power/12V_OR'),
                 ('Power_PI', 'PI_5V'), ('Power_PI', '/Power/PI_5V_BUCK'), ('Power_PI', 'Net-(U35-SW)')):
    if not any(p['pattern'] == pat for p in pats): pats.append({'netclass': cls, 'pattern': pat})
ns['netclass_patterns'] = pats
open(pro, 'w').write(json.dumps(P, indent=2) + '\n')

import pcbnew
FPD = os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/k10/root/usr/share/kicad/footprints')
PARTS = {   # ref: (lib, footprint, x, y, deg)
    'Q19': ('Package_SON', 'Diodes_PowerDI3333-8', 135.0, 59.2, 0), 'Q20': ('Package_SON', 'Diodes_PowerDI3333-8', 128.0, 59.2, 180),
    'U33': ('Package_TO_SOT_SMD', 'TSOT-23-6', 135.0, 54.9, 180), 'U34': ('Package_TO_SOT_SMD', 'TSOT-23-6', 128.0, 54.9, 0),
    'R213': ('Resistor_SMD', 'R_0603_1608Metric', 134.2, 50.0, 180), 'R214': ('Resistor_SMD', 'R_0603_1608Metric', 134.2, 51.6, 0),
    'U35': ('Package_TO_SOT_SMD', 'SOT-23-6', 132.75, 133.0, 90),
    'C133': ('Capacitor_SMD', 'C_1206_3216Metric', 132.75, 136.9, 180), 'C134': ('Capacitor_SMD', 'C_1206_3216Metric', 129.1, 129.6, 0),
    'C135': ('Capacitor_SMD', 'C_1206_3216Metric', 132.75, 150.0, 0), 'C136': ('Capacitor_SMD', 'C_1206_3216Metric', 132.75, 152.6, 0),
    'C137': ('Capacitor_SMD', 'C_0603_1608Metric', 129.8, 133.0, 270), 'L2': ('Inductor_SMD', 'L_Changjiang_FXL0630', 132.75, 143.2, 270),
    'R215': ('Resistor_SMD', 'R_0603_1608Metric', 135.4, 130.6, 90), 'R216': ('Resistor_SMD', 'R_0603_1608Metric', 133.7, 129.3, 90),
    'JP3': ('Jumper', 'SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm', 106.5, 112.0, 270),
    'JP4': ('Jumper', 'SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm', 132.75, 155.3, 180)}
LOADED = {r: pcbnew.FootprintLoad(os.path.join(FPD, l + '.pretty'), n) for r, (l, n, *_) in PARTS.items()}   # before LoadBoard
sch = open(SCH).read()
def symfields(ref):
    i = sch.index('(reference "%s")' % ref); j = sch.rfind('(lib_id', 0, i); blk = sch[j:i]
    f = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk)); f['uuid'] = re.search(r'\(uuid "([0-9a-f-]+)"\)', blk).group(1)
    return f
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; F, B = pcbnew.F_Cu, pcbnew.B_Cu
SHEET = '/febff99c-25e7-5ff2-ad94-91f07160e16c/'
def pt(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
def near(a, x, y, tol=0.02): return abs(a.x - MM(x)) < MM(tol) and abs(a.y - MM(y)) < MM(tol)
keep = []       # removed items stay referenced: freeing them from Python corrupts the board's objects
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
def net(name):
    if name in nets: return nets[name]
    n = pcbnew.NETINFO_ITEM(b, name); b.Add(n); nets[name] = n; return n
def tracks(): T = b.Tracks(); return [T[i] for i in range(T.size())]
def track(n, ly, pts, w):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(w)); t.SetLayer(ly); t.SetNet(net(n)); b.Add(t)
def via(n, x, y, d=0.6, h=0.3):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pt(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(h))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(F, B); v.SetNet(net(n)); b.Add(v)
FP = {f.GetReference(): f for f in b.GetFootprints()}

# 12V_OR: the old J23 net, without its B.Cu diagonal from J23; the y 71.73 track now starts at x 131
old = nets['Net-(J23-Pin_1)']; OR = net('/Power/12V_OR')
for x in tracks():
    if x.GetNetCode() != old.GetNetCode(): continue
    if x.Type() != pcbnew.PCB_VIA_T and (near(x.GetStart(), 144.5, 60.0) or near(x.GetEnd(), 144.5, 60.0)):
        keep.append(x); b.Remove(x); continue
    x.SetNet(OR)
    if x.Type() != pcbnew.PCB_VIA_T:
        for e, s in ((x.GetStart(), x.SetStart), (x.GetEnd(), x.SetEnd)):
            if near(e, 132.77, 71.73): s(pt(131.0, 71.73))
FP['F1'].FindPadByNumber('1').SetNet(OR)
FP['J23'].FindPadByNumber('1').SetNet(net('/Power/EXT_12V'))
FP['J11'].FindPadByNumber('6').SetNet(net('/Power/IO_12V'))

# +5V B.Cu from the C5 via: along y 51.38, then down to y 55.4 at x 121.3; dangling GND stubs and vias by U34
for x in tracks():
    if x.GetNetname() == '+5V' and x.Type() != pcbnew.PCB_VIA_T and x.GetLayer() == B:
        if near(x.GetStart(), 129.71, 51.38) and near(x.GetEnd(), 125.69, 55.4): keep.append(x); b.Remove(x)
        elif near(x.GetStart(), 125.69, 55.4) and near(x.GetEnd(), 111.25, 55.4): x.SetStart(pt(121.3, 55.4))
    elif x.GetNetname() == 'GND':
        if x.Type() == pcbnew.PCB_VIA_T: hit = near(x.GetPosition(), 127.48, 51.55) or near(x.GetPosition(), 127.48, 52.5)
        else: hit = near(x.GetStart(), 126.43, 50.95) or near(x.GetStart(), 126.43, 51.9)
        if hit: keep.append(x); b.Remove(x)
track('+5V', B, [(129.71, 51.38), (125.3, 51.38), (121.3, 55.4)], 0.5)

# JP3 cuts the +5V trunk at y 112: the trunk below it is PI_5V
for x in tracks():
    if x.GetNetname() == '+5V' and x.Type() != pcbnew.PCB_VIA_T and near(x.GetStart(), 106.5, 106.6) and near(x.GetEnd(), 106.5, 125.0):
        x.SetEnd(pt(106.5, 110.6)); lk = x.IsLocked()
        t = pcbnew.PCB_TRACK(b); t.SetStart(pt(106.5, 113.4)); t.SetEnd(pt(106.5, 125.0)); t.SetWidth(x.GetWidth())
        t.SetLayer(F); t.SetNet(x.GetNet()); t.SetLocked(lk); b.Add(t); break
else: raise SystemExit('trunk not found')
V5 = nets['+5V']; PI = net('PI_5V')
def on_seg(q, o, tol):
    a, c = o.GetStart(), o.GetEnd(); d = c - a; L2 = d.x * d.x + d.y * d.y
    if L2 == 0: return (q - a).EuclideanNorm() < tol
    s = max(0, min(1, ((q.x - a.x) * d.x + (q.y - a.y) * d.y) / L2))
    return ((q.x - a.x - s * d.x) ** 2 + (q.y - a.y - s * d.y) ** 2) ** 0.5 < tol
items = [x for x in tracks() if x.GetNetCode() == V5.GetNetCode()]
pads5 = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode() == V5.GetNetCode()]
grp = [p for p in pads5 if p.GetParentFootprint().GetReference() == 'J21']; new = list(grp)
def touch(a, c):    # a: pad / via / track, c: track or via
    if c.Type() == pcbnew.PCB_VIA_T:
        q = c.GetPosition()
        if a.Type() == pcbnew.PCB_PAD_T: return a.HitTest(q)
        if a.Type() == pcbnew.PCB_VIA_T: return (a.GetPosition() - q).EuclideanNorm() < MM(0.01)
        return on_seg(q, a, a.GetWidth() // 2 + MM(0.01))
    for q in (c.GetStart(), c.GetEnd()):
        if a.Type() == pcbnew.PCB_PAD_T and a.HitTest(q): return True
        if a.Type() == pcbnew.PCB_VIA_T and (a.GetPosition() - q).EuclideanNorm() <= a.GetWidth(F) // 2: return True
        if a.Type() == pcbnew.PCB_TRACE_T and a.GetLayer() == c.GetLayer() and (on_seg(q, a, MM(0.01)) or
                on_seg(a.GetStart(), c, MM(0.01)) or on_seg(a.GetEnd(), c, MM(0.01))): return True
    return False
while new:
    a = new.pop(); add = [c for c in items if c not in grp and touch(a, c)]
    grp += add; new += add
    for p in pads5:
        if p not in grp and any(p.HitTest(c.GetStart()) or p.HitTest(c.GetEnd()) for c in add if c.Type() != pcbnew.PCB_VIA_T):
            grp.append(p); new.append(p)
bad = [p.GetParentFootprint().GetReference() + '.' + p.GetNumber() for p in grp if p.Type() == pcbnew.PCB_PAD_T
       and p.GetParentFootprint().GetReference() != 'J21']
if bad: raise SystemExit('PI_5V trunk reaches ' + ' '.join(bad))
for x in grp: x.SetNet(PI)
print('PI_5V items', len(grp))

# parts
PADNETS = {
    'Q19': {'1': '/Power/12V_OR', '2': '/Power/12V_OR', '3': '/Power/12V_OR', '4': 'Net-(Q19-G)', '5': '/Power/EXT_12V'},
    'Q20': {'1': '/Power/12V_OR', '2': '/Power/12V_OR', '3': '/Power/12V_OR', '4': 'Net-(Q20-G)', '5': '/Power/IO_12V'},
    'U33': {'1': '/Power/EXT_12V', '2': 'GND', '3': 'GND', '4': 'unconnected-(U33-STAT-Pad4)', '5': 'Net-(Q19-G)', '6': '/Power/12V_OR'},
    'U34': {'1': '/Power/IO_12V', '2': 'GND', '3': 'Net-(U34-CTL)', '4': 'unconnected-(U34-STAT-Pad4)', '5': 'Net-(Q20-G)', '6': '/Power/12V_OR'},
    'R213': {'1': '/Power/EXT_12V', '2': 'Net-(U34-CTL)'}, 'R214': {'1': 'Net-(U34-CTL)', '2': 'GND'},
    'U35': {'1': 'GND', '2': 'Net-(U35-SW)', '3': '+12V', '4': 'Net-(U35-FB)', '5': 'unconnected-(U35-EN-Pad5)', '6': 'Net-(U35-BOOT)'},
    'C133': {'1': '+12V', '2': 'GND'}, 'C134': {'1': '+12V', '2': 'GND'},
    'C135': {'1': '/Power/PI_5V_BUCK', '2': 'GND'}, 'C136': {'1': '/Power/PI_5V_BUCK', '2': 'GND'},
    'C137': {'1': 'Net-(U35-BOOT)', '2': 'Net-(U35-SW)'}, 'L2': {'1': 'Net-(U35-SW)', '2': '/Power/PI_5V_BUCK'},
    'R215': {'1': '/Power/PI_5V_BUCK', '2': 'Net-(U35-FB)'}, 'R216': {'1': 'Net-(U35-FB)', '2': 'GND'},
    'JP3': {'1': '+5V', '2': 'PI_5V'}, 'JP4': {'1': 'PI_5V', '2': '/Power/PI_5V_BUCK'}}
for ref, (lib, name, x, y, deg) in PARTS.items():
    if ref in FP: raise SystemExit(ref + ' already on the board')
    s = symfields(ref); f = LOADED[ref]; f.SetParent(b); f.SetFPID(pcbnew.LIB_ID(lib, name))
    f.SetReference(ref); f.SetValue(s['Value']); f.SetPath(pcbnew.KIID_PATH(SHEET + s['uuid']))
    f.SetPosition(pt(x, y)); f.SetOrientationDegrees(deg)
    for fld in ('Datasheet', 'Description'):
        if not s.get(fld): continue
        if f.HasField(fld): f.GetField(fld).SetText(s[fld])
        else:
            g = pcbnew.PCB_FIELD(f, pcbnew.FIELD_T_USER, fld); g.SetText(s[fld]); g.SetVisible(False); f.AddField(g)
    b.Add(f)
    for p in f.Pads():
        if p.GetNumber(): p.SetNet(net(PADNETS[ref][p.GetNumber()]))
# reference texts: beside the part, upright
for ref, (dx, dy) in {'Q19': (0, -2.6), 'Q20': (0, -2.6), 'U33': (2.9, 0), 'U34': (-2.9, -1.4), 'R213': (-2.6, 0), 'R214': (-2.6, 0),
                      'U35': (-2.5, -1.6), 'C133': (0, 1.9), 'C134': (0, -1.9), 'C135': (-3.2, 0), 'C136': (-3.2, 0),
                      'C137': (-1.9, 0), 'L2': (-4.6, 0), 'R215': (1.9, 0), 'R216': (0, -2.2), 'JP3': (-2.6, 0), 'JP4': (-3.0, 0)}.items():
    f = b.FindFootprintByReference(ref); r = f.Reference(); r.SetTextAngleDegrees(0)
    r.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8))); r.SetTextThickness(MM(0.12))
    q = f.GetPosition(); r.SetPosition(pcbnew.VECTOR2I(q.x + MM(dx), q.y + MM(dy)))

# 12 V OR copper (F.Cu unless noted)
track('/Power/12V_OR', F, [(129.5, 58.875), (129.5, 60.175)], 0.4)          # Q20 sources
track('/Power/12V_OR', F, [(133.5, 58.225), (133.5, 59.525)], 0.4)          # Q19 sources
track('/Power/12V_OR', F, [(129.5, 59.2), (133.5, 59.2)], 1.0)
track('/Power/12V_OR', F, [(131.0, 59.2), (131.0, 60.3)], 0.8); via('/Power/12V_OR', 131.0, 60.3, 0.8, 0.4)
track('/Power/12V_OR', B, [(131.0, 60.3), (131.0, 71.73)], 0.8)
track('/Power/12V_OR', F, [(133.6, 55.85), (133.6, 58.225)], 0.3)           # U33 SENSE
track('/Power/12V_OR', F, [(129.137, 53.95), (130.8, 53.95), (130.8, 59.2)], 0.3)   # U34 SENSE
track('/Power/EXT_12V', B, [(144.5, 60.0), (143.5, 61.0), (136.3, 61.0)], 0.8); via('/Power/EXT_12V', 136.3, 61.0, 0.8, 0.4)
track('/Power/EXT_12V', F, [(136.3, 61.0), (136.0, 59.8)], 0.8)              # into the Q19 drain
track('/Power/EXT_12V', F, [(136.137, 55.85), (136.137, 58.3)], 0.4)        # U33 VIN
track('/Power/EXT_12V', F, [(135.025, 50.0), (135.6, 50.0), (136.3, 50.7), (136.3, 51.6)], 0.25); via('/Power/EXT_12V', 136.3, 51.6)
track('/Power/EXT_12V', B, [(136.3, 51.6), (136.3, 61.0)], 0.3)             # R213 top, down to the EXT via
track('/Power/IO_12V', F, [(108.21, 41.18), (108.21, 46.9), (123.9, 46.9), (124.9, 47.9), (124.9, 57.6), (126.4, 59.1),
                           (127.5, 59.2)], 0.8)
track('/Power/IO_12V', F, [(126.863, 53.95), (124.9, 53.95)], 0.4)          # U34 VIN
track('Net-(Q20-G)', F, [(129.137, 54.9), (130.15, 54.9), (130.15, 57.6), (129.5, 58.225)], 0.2)
track('Net-(Q19-G)', F, [(133.863, 54.9), (132.6, 54.9)], 0.25); via('Net-(Q19-G)', 132.6, 54.9)
track('Net-(Q19-G)', B, [(132.6, 54.9), (132.6, 61.0)], 0.25); via('Net-(Q19-G)', 132.6, 61.0)
track('Net-(Q19-G)', F, [(132.6, 61.0), (133.5, 60.175)], 0.25)
track('Net-(U34-CTL)', F, [(133.375, 50.0), (133.375, 51.6), (132.4, 52.3)], 0.25); via('Net-(U34-CTL)', 132.4, 52.3)
track('Net-(U34-CTL)', B, [(132.4, 52.3), (129.2, 52.3), (127.0, 54.5), (127.0, 56.4), (125.85, 56.4)], 0.2)
via('Net-(U34-CTL)', 125.85, 56.4); track('Net-(U34-CTL)', F, [(126.863, 55.85), (125.85, 55.85), (125.85, 56.4)], 0.2)
track('GND', F, [(126.863, 54.9), (125.85, 54.9)], 0.3); via('GND', 125.85, 54.9)                 # U34 GND
track('GND', F, [(136.137, 53.95), (136.137, 54.9)], 0.3)                                         # U33 GND + CTL
track('GND', F, [(136.137, 53.95), (135.6, 53.4), (135.025, 52.825), (135.025, 51.6)], 0.3); via('GND', 135.025, 52.8)

# buck copper
track('Net-(U35-SW)', F, [(132.75, 134.137), (132.75, 136.6)], 0.5)      # 0.5 mm beside the GND / VIN legs
track('Net-(U35-SW)', F, [(132.75, 136.6), (132.75, 140.175)], 1.0)
track('Net-(U35-SW)', F, [(129.8, 133.775), (129.8, 140.175), (131.2, 140.175)], 0.4)            # C137 to L2
track('Net-(U35-BOOT)', F, [(131.8, 131.863), (131.8, 132.225), (129.8, 132.225)], 0.3)
track('+12V', F, [(133.7, 134.137), (133.7, 136.2)], 0.5)
track('+12V', F, [(135.3, 134.4), (134.3, 135.4), (134.3, 136.2)], 0.6); via('+12V', 135.3, 134.4, 0.8, 0.4)
track('+12V', B, [(135.3, 134.4), (135.3, 132.58)], 0.8)
track('+12V', F, [(127.625, 129.6), (127.6, 132.58)], 0.8); via('+12V', 127.6, 132.58, 0.8, 0.4)   # C134
track('GND', F, [(131.8, 134.137), (131.8, 136.2)], 0.5)
track('GND', F, [(131.8, 135.5), (130.5, 135.2)], 0.4); via('GND', 130.5, 135.2)
track('/Power/PI_5V_BUCK', F, [(132.75, 146.6), (132.75, 147.0), (131.275, 148.475), (131.275, 155.3)], 1.2)
track('/Power/PI_5V_BUCK', F, [(131.275, 155.3), (132.1, 155.3)], 0.8)
track('GND', F, [(134.225, 150.0), (134.225, 152.6)], 0.8)
track('GND', F, [(134.225, 151.3), (135.6, 151.3)], 0.6); via('GND', 135.6, 151.3)
track('PI_5V', F, [(133.4, 155.3), (134.8, 155.3)], 1.0); via('PI_5V', 134.8, 155.3, 0.8, 0.4)
track('PI_5V', B, [(134.8, 155.3), (109.0, 155.3)], 1.2); via('PI_5V', 109.0, 155.3, 0.8, 0.4)
track('Net-(U35-FB)', F, [(133.7, 131.863), (133.7, 130.125), (135.4, 129.775)], 0.25)
track('/Power/PI_5V_BUCK', F, [(135.4, 131.425), (136.1, 132.125), (136.1, 146.2), (134.3, 146.2)], 0.25)   # Vout sense
track('GND', F, [(133.7, 128.475), (133.7, 127.4)], 0.3); via('GND', 133.7, 127.4)               # R216
track('GND', F, [(130.575, 129.6), (130.6, 127.8)], 0.5); via('GND', 130.6, 127.8)               # C134
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
print('ok')

"""c50 (board, schematic in c49): power, reset and derating fixes from the 2026-10-31 repairability review.
- R217 (new, 10k 0805, MR_N pull-up) left of U5 at (68.0, 74.6): pad 2 (MR_N) joins the MR_N track on x 70.343 at
  y 74.6, pad 1 (+3V3) drops through a via at (65.9, 74.6) into the In2 +3V3 plane.
- R1 0402 -> 0603, out of the gap between F1, D1 and U1 (0.03 mm) to (96.6, 104.54), rotated 90 (pad 1 EXT_5V below,
  pad 2 PR1 above). PR1 runs from U1 pin 4 along y 103.11 to pad 2; EXT_5V from pad 1 to the existing via at
  (98.33, 104.446). The old EXT_5V stub to the 0402 goes.
- FB1 0805 -> 1206 (L_1206_3216Metric) centred at (103.38, 108.735): pad 1 keeps its J11 via, the JP1-A track runs on
  to pad 2. Pad 2 stays 0.25 mm clear of the 1.5 mm +5V track on x 106.5.
- R211 0603 -> 1206 centred at (148.3, 206.3): pad 1 sits on the D27-A1 track end, JP2-A runs on along y 205.669 to pad 2.
- C4, C8, C112, C114, C133, C134 change part only (same footprint).
Usage: c50_board_power_reset_derating.py in.kicad_pcb out.kicad_pcb sam_cpu_dir"""
import os, re, sys
import pcbnew
FPD = os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/k10/root/usr/share/kicad/footprints')
SCH = sys.argv[3]


def sch_desc(sheet, ref):
    s = open(os.path.join(SCH, sheet)).read()
    i = s.index('(reference "%s")' % ref); j = s.rfind('(lib_id', 0, i); blk = s[j:i]
    P = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk))
    return P, re.search(r'\(uuid "([0-9a-f-]+)"\)', blk).group(1)


NEW = {'R217': ('Resistor_SMD', 'R_0805_2012Metric', 'mcu.kicad_sch'),
       'R1': ('Resistor_SMD', 'R_0603_1608Metric', 'power.kicad_sch'),
       'FB1': ('Inductor_SMD', 'L_1206_3216Metric', 'power.kicad_sch'),
       'R211': ('Resistor_SMD', 'R_1206_3216Metric', 'rs485_i2s.kicad_sch')}
FPS = {}
for ref, (lib, name, sheet) in NEW.items():      # load and set fields before LoadBoard (field access fails after)
    f = pcbnew.FootprintLoad(os.path.join(FPD, lib + '.pretty'), name)
    P, su = sch_desc(sheet, ref)
    f.GetField('Description').SetText(P['Description'])
    r = f.Reference(); r.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
    r.SetTextThickness(pcbnew.FromMM(0.15))
    FPS[ref] = (f, lib, name, P, su)

b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; F = pcbnew.F_Cu
def pt(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
def near(a, x, y, tol=0.02): return abs(a.x - MM(x)) < MM(tol) and abs(a.y - MM(y)) < MM(tol)
def seg(t, a, c): return t.Type() != pcbnew.PCB_VIA_T and ((near(t.GetStart(), *a) and near(t.GetEnd(), *c)) or
                                                          (near(t.GetStart(), *c) and near(t.GetEnd(), *a)))
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
def tracks(): T = b.Tracks(); return [T[i] for i in range(T.size())]
keep = []
def drop(a, c):
    hit = [t for t in tracks() if seg(t, a, c)]; assert len(hit) == 1, (a, c, len(hit))
    keep.append(hit[0]); b.Remove(hit[0])
def track(n, pts, w):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(w)); t.SetLayer(F)
        t.SetNet(nets[n]); b.Add(t)
def via(n, x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pt(x, y)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(nets[n]); b.Add(v)


def place(ref, x, y, rot, padnets, path=None, text=None):
    f, lib, name, P, su = FPS[ref]
    old = b.FindFootprintByReference(ref)
    if old:
        path = old.GetPath(); keep.append(old); b.Remove(old)
    f.SetParent(b); f.SetFPID(pcbnew.LIB_ID(lib, name)); f.SetReference(ref); f.SetValue(P['Value'])
    f.SetPath(path); f.SetAttributes(pcbnew.FP_SMD)
    f.SetOrientationDegrees(rot); f.SetPosition(pt(x, y)); b.Add(f)
    got = {}
    for p in f.Pads():
        p.SetNet(nets[padnets[p.GetNumber()]]); q = p.GetPosition()
        got[p.GetNumber()] = (round(pcbnew.ToMM(q.x), 3), round(pcbnew.ToMM(q.y), 3))
    if text:
        r = f.Reference(); r.SetPosition(pt(*text[:2])); r.SetTextAngleDegrees(text[2])
    print(ref, got)
    return got


# R217: MR_N pull-up beside U5 (mcu sheet path)
r20 = b.FindFootprintByReference('R20'); mcu_sheet = r20.GetPath().AsString().rsplit('/', 1)[0]
p = place('R217', 68.0, 74.6, 0, {'1': '+3V3', '2': '/MCU and Pi/MR_N'},
          path=pcbnew.KIID_PATH(mcu_sheet + '/' + FPS['R217'][4]), text=(67.0, 72.9, 0))
assert p == {'1': (67.088, 74.6), '2': (68.912, 74.6)}, p
drop((70.343, 73.939), (70.343, 78.455))
track('/MCU and Pi/MR_N', [(70.343, 73.939), (70.343, 74.6), (70.343, 78.455)], 0.2)
track('/MCU and Pi/MR_N', [(68.912, 74.6), (70.343, 74.6)], 0.2)
track('+3V3', [(67.088, 74.6), (65.9, 74.6)], 0.3); via('+3V3', 65.9, 74.6)

# R1: 0603, below F1
p = place('R1', 96.6, 104.54, 90, {'1': '/Power/EXT_5V', '2': 'Net-(U1-PR1)'}, text=(97.8, 104.54, 90))
assert p == {'1': (96.6, 105.365), '2': (96.6, 103.715)}, p
drop((97.85, 101.27), (97.85, 102.09))
drop((99.0, 103.11), (97.85, 103.11))
track('Net-(U1-PR1)', [(99.0, 103.11), (97.205, 103.11), (96.6, 103.715)], 0.2)
track('/Power/EXT_5V', [(96.6, 105.365), (97.411, 105.365), (98.33, 104.446)], 0.4)

# FB1: 6 A 1206
p = place('FB1', 103.38, 108.735, 0, {'1': 'Net-(J11-Pin_1)', '2': 'Net-(JP1-A)'}, text=(103.38, 107.0, 0))
assert p == {'1': (101.805, 108.735), '2': (104.955, 108.735)}, p
track('Net-(JP1-A)', [(104.425, 108.735), (104.955, 108.735)], 0.8)

# R211: 1206
p = place('R211', 148.3, 206.3, 0, {'1': 'Net-(D27-A1)', '2': 'Net-(JP2-A)'}, text=(148.3, 208.2, 0))
assert p == {'1': (146.838, 206.3), '2': (149.762, 206.3)}, p
drop((148.55, 205.669), (148.55, 205.955))
track('Net-(JP2-A)', [(148.55, 205.669), (149.762, 205.669), (149.762, 206.3)], 0.2)

# part changes only: copy the schematic Description into the footprint
for ref, sheet in (('C4', 'power.kicad_sch'), ('C8', 'power.kicad_sch'), ('C133', 'power.kicad_sch'),
                   ('C134', 'power.kicad_sch'), ('C112', 'audio.kicad_sch'), ('C114', 'audio.kicad_sch')):
    b.FindFootprintByReference(ref).GetField('Description').SetText(sch_desc(sheet, ref)[0]['Description'])

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
print('ok')

"""c47 (board, after c45; schematic in c46): JP3 becomes a right-angle 1x3 2.54 mm header with a jumper shunt.
- The three-pad solder jumper at (132.75, 155.3) goes, with its two short F.Cu stubs.
- The header lies flat under the Pi (about 2.5 mm high, Pi keep-low limit 3 mm), pads on y 159.5, pins and shunt
  toward +y: pin 1 +5V at x 135.29, pin 2 PI_5V at 132.75, pin 3 PI_5V_BUCK at 130.21.
- PI_5V_BUCK: the buck bus on x 131.275 runs on from y 155.3 into pin 3; PI_5V: F.Cu from the via at (132.75, 157.3)
  into pin 2; +5V: F.Cu from the via at (135.4, 155.3) into pin 1. The B.Cu tracks to the x 109 trunk are unchanged.
Usage: c47_board_pi_5v_header_jumper.py in.kicad_pcb out.kicad_pcb sam_cpu_dir"""
import os, re, sys
import pcbnew
FPD = os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/k10/root/usr/share/kicad/footprints')
LIB, JPNAME = 'Connector_PinHeader_2.54mm', 'PinHeader_1x03_P2.54mm_Horizontal'
JP = pcbnew.FootprintLoad(os.path.join(FPD, LIB + '.pretty'), JPNAME)     # before LoadBoard
sch = open(os.path.join(sys.argv[3], 'power.kicad_sch')).read()
i = sch.index('(reference "JP3")'); j = sch.rfind('(lib_id', 0, i); blk = sch[j:i]
assert '"Jumper:Jumper_3_Open"' in blk
S = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk)); SU = re.search(r'\(uuid "([0-9a-f-]+)"\)', blk).group(1)
JP.GetField('Description').SetText(S['Description'])     # field access fails once a board is loaded
r = JP.Reference(); r.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8))); r.SetTextThickness(pcbnew.FromMM(0.12))
r.SetPosition(pcbnew.VECTOR2I(0, pcbnew.FromMM(-2.51)))     # beside pin 1 once rotated 270
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; F, B = pcbnew.F_Cu, pcbnew.B_Cu
def pt(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
def near(a, x, y, tol=0.02): return abs(a.x - MM(x)) < MM(tol) and abs(a.y - MM(y)) < MM(tol)
def seg(t, a, c): return t.Type() != pcbnew.PCB_VIA_T and ((near(t.GetStart(), *a) and near(t.GetEnd(), *c)) or
                                                          (near(t.GetStart(), *c) and near(t.GetEnd(), *a)))
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
V5, PI, BK = nets['+5V'], nets['PI_5V'], nets['/Power/PI_5V_BUCK']
def tracks(): T = b.Tracks(); return [T[i] for i in range(T.size())]
def track(n, ly, pts, w):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(w)); t.SetLayer(ly); t.SetNet(n); b.Add(t)

old = b.FindFootprintByReference('JP3'); assert old.GetFPID().GetLibItemName() == 'SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm'
keep = [old]; b.Remove(old)                  # keep removed items referenced, or SWIG frees them under the board
gone = 0
for t in tracks():
    if seg(t, (132.75, 155.3), (132.75, 157.3)) or seg(t, (134.05, 155.3), (135.4, 155.3)): keep.append(t); b.Remove(t); gone += 1
assert gone == 2, gone
f = JP; f.SetParent(b); f.SetFPID(pcbnew.LIB_ID(LIB, JPNAME)); f.SetReference('JP3'); f.SetValue(S['Value'])
f.SetPath(pcbnew.KIID_PATH('/febff99c-25e7-5ff2-ad94-91f07160e16c/' + SU))
f.SetOrientationDegrees(270); f.SetPosition(pt(135.29, 159.5))
f.SetAttributes(pcbnew.FP_THROUGH_HOLE)    # a real BOM part, unlike the solder jumpers
b.Add(f)
pos = {}
for p in f.Pads():
    p.SetNet({'1': V5, '2': PI, '3': BK}[p.GetNumber()]); q = p.GetPosition(); pos[p.GetNumber()] = (round(pcbnew.ToMM(q.x), 3), round(pcbnew.ToMM(q.y), 3))
print('pads', pos)
assert pos == {'1': (135.29, 159.5), '2': (132.75, 159.5), '3': (130.21, 159.5)}, pos
track(BK, F, [(131.275, 155.3), (131.275, 158.4), (130.21, 159.5)], 1.2)
track(PI, F, [(132.75, 157.3), (132.75, 159.5)], 1.0)
track(V5, F, [(135.4, 155.3), (135.4, 158.6), (135.29, 159.5)], 0.8)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
print('ok')

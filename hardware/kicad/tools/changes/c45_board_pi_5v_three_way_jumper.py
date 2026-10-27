"""c45 (board, after c43; schematic in c44): one three-pad solder jumper JP3 picks the Pi header 5 V.
- The two-pad JP3 on the +5V trunk at (106.5, 112) and JP4 by the buck go. The trunk is whole again from the +5V bus
  down to y 155.3 (no part left inside the DeepPCB cut).
- The new JP3 sits where JP4 was, at (132.75, 155.3): pad 1 PI_5V_BUCK (the buck output bus ends in it), pad 2 PI_5V,
  pad 3 +5V. The trunk on x 109 is cut between y 155.3 and 157.3: two B.Cu tracks run from there to the jumper,
  +5V along y 155.3 into pad 3, PI_5V along y 157.3 from pad 2. Below y 157.3 the trunk to J21 pins 2 / 4 is PI_5V.
Usage: c45_board_pi_5v_three_way_jumper.py in.kicad_pcb out.kicad_pcb sam_cpu_dir"""
import os, re, sys
import pcbnew
FPD = os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/k10/root/usr/share/kicad/footprints')
JPNAME = 'SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm'
JP = pcbnew.FootprintLoad(os.path.join(FPD, 'Jumper.pretty'), JPNAME)     # before LoadBoard
sch = open(os.path.join(sys.argv[3], 'power.kicad_sch')).read()
i = sch.index('(reference "JP3")'); j = sch.rfind('(lib_id', 0, i); blk = sch[j:i]
assert '"Jumper:SolderJumper_3_Open"' in blk
S = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk)); SU = re.search(r'\(uuid "([0-9a-f-]+)"\)', blk).group(1)
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; F, B = pcbnew.F_Cu, pcbnew.B_Cu
def pt(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
def near(a, x, y, tol=0.02): return abs(a.x - MM(x)) < MM(tol) and abs(a.y - MM(y)) < MM(tol)
def seg(t, a, c): return t.Type() != pcbnew.PCB_VIA_T and ((near(t.GetStart(), *a) and near(t.GetEnd(), *c)) or
                                                          (near(t.GetStart(), *c) and near(t.GetEnd(), *a)))
keep = []
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
V5, PI, BK = nets['+5V'], nets['PI_5V'], nets['/Power/PI_5V_BUCK']
def tracks(): T = b.Tracks(); return [T[i] for i in range(T.size())]
def track(n, ly, pts, w):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(w)); t.SetLayer(ly); t.SetNet(n); b.Add(t)
def via(n, x, y, d=0.8, h=0.4):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pt(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(h))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(F, B); v.SetNet(n); b.Add(v)

for ref in ('JP3', 'JP4'):
    f = b.FindFootprintByReference(ref); keep.append(f); b.Remove(f)
done = set()
for t in tracks():
    if seg(t, (106.5, 106.6), (106.5, 110.6)): t.SetEnd(pt(106.5, 125.0)); done.add('trunk')         # trunk whole again
    elif seg(t, (106.5, 113.4), (106.5, 125.0)): keep.append(t); b.Remove(t)
    elif seg(t, (131.275, 155.3), (132.1, 155.3)) or seg(t, (133.4, 155.3), (134.8, 155.3)) or seg(t, (134.8, 155.3), (109.0, 155.3)):
        keep.append(t); b.Remove(t)                                                                    # old JP4 copper
    elif t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == PI.GetNetCode() and (near(t.GetPosition(), 134.8, 155.3) or
                                                                                 near(t.GetPosition(), 109.0, 155.3)):
        keep.append(t); b.Remove(t)
    elif seg(t, (109.0, 152.2), (109.0, 170.5)):                                                       # cut at y 155.3 / 157.3
        t.SetStart(pt(109.0, 152.2)); t.SetEnd(pt(109.0, 155.3)); lk = t.IsLocked()
        u = pcbnew.PCB_TRACK(b); u.SetStart(pt(109.0, 157.3)); u.SetEnd(pt(109.0, 170.5)); u.SetWidth(t.GetWidth())
        u.SetLayer(F); u.SetNet(PI); u.SetLocked(lk); b.Add(u); done.add('cut')
assert done == {'trunk', 'cut'}, done
# PI_5V = the copper joined to J21 pins 2 / 4 (the trunk below the cut); every other +5V / PI_5V item is +5V
def on_seg(q, o, tol):
    a, c = o.GetStart(), o.GetEnd(); d = c - a; L2 = d.x * d.x + d.y * d.y
    if L2 == 0: return (q - a).EuclideanNorm() < tol
    s = max(0, min(1, ((q.x - a.x) * d.x + (q.y - a.y) * d.y) / L2))
    return ((q.x - a.x - s * d.x) ** 2 + (q.y - a.y - s * d.y) ** 2) ** 0.5 < tol
codes = (V5.GetNetCode(), PI.GetNetCode())
items = [t for t in tracks() if t.GetNetCode() in codes]
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
grp = [p for p in b.FindFootprintByReference('J21').Pads() if p.GetNumber() in ('2', '4')]; new = list(grp)
while new:
    a = new.pop(); add = [c for c in items if c not in grp and touch(a, c)]; grp += add; new += add
other = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode() in codes and p not in grp]
bad = [p.GetParentFootprint().GetReference() + '.' + p.GetNumber() for p in other
       if any(p.HitTest(c.GetStart()) or p.HitTest(c.GetEnd()) for c in grp if c.Type() == pcbnew.PCB_TRACE_T)]
if bad: raise SystemExit('PI_5V reaches ' + ' '.join(bad))
for x in items: x.SetNet(PI if x in grp else V5)
print('PI_5V items', len(grp))
f = JP; f.SetParent(b); f.SetFPID(pcbnew.LIB_ID('Jumper', JPNAME)); f.SetReference('JP3'); f.SetValue(S['Value'])
f.SetPath(pcbnew.KIID_PATH('/febff99c-25e7-5ff2-ad94-91f07160e16c/' + SU))
f.SetPosition(pt(132.75, 155.3)); f.SetOrientationDegrees(0)
f.GetField('Description').SetText(S['Description'])
r = f.Reference(); r.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8))); r.SetTextThickness(MM(0.12)); r.SetPosition(pt(128.9, 155.3))
f.SetAttributes(b.FindFootprintByReference('JP1').GetAttributes())
b.Add(f)
for p in f.Pads(): p.SetNet({'1': BK, '2': PI, '3': V5}[p.GetNumber()])
track(PI, F, [(132.75, 155.3), (132.75, 157.3)], 1.0); via(PI, 132.75, 157.3)
track(PI, B, [(132.75, 157.3), (109.0, 157.3)], 1.2); via(PI, 109.0, 157.3)
track(V5, F, [(134.05, 155.3), (135.4, 155.3)], 0.8); via(V5, 135.4, 155.3)
track(V5, B, [(135.4, 155.3), (109.0, 155.3)], 1.2); via(V5, 109.0, 155.3)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2])
J = b.FindFootprintByReference('J21')
print('J21 pins', [(p.GetNumber(), p.GetNetname()) for p in J.Pads() if p.GetNumber() in ('2', '4')])
print('ok')

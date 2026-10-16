"""c25: board side of c24. U32 pads get the CA-IS2092VW nets, net Net-(U32-VISOIN) becomes Net-(U32-VISO).
Logic side: pads 1 and 2 swap GND / +3V3, so their one-segment fanouts (stub + via to the planes) swap nets too.
Cable side: all copper of A, B and VISO is removed and rerouted afterwards with the iso-only Freerouting flow
(route/mkisoB.py, chunk2.sh, impiso.py)."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
NI = b.GetNetInfo(); mm = pcbnew.ToMM
nets = {n.GetNetname(): n for n in NI.NetsByName().values()}
old = nets['Net-(U32-VISOIN)']
viso = pcbnew.NETINFO_ITEM(b, 'Net-(U32-VISO)'); b.Add(viso)
nets = {n.GetNetname(): n for n in NI.NetsByName().values()}
T = b.Tracks(); tracks = [T[i] for i in range(T.size())]
for x in tracks:
    if x.GetNetCode() == old.GetNetCode(): x.SetNet(viso)
for z in b.Zones():
    if z.GetNetCode() == old.GetNetCode(): z.SetNet(viso)
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetCode() == old.GetNetCode(): p.SetNet(viso)
u = b.FindFootprintByReference('U32')
u.SetValue('CA-IS2092VW')
NEW = {'1': '+3V3', '2': 'GND', '3': 'Net-(U32-RXD)', '4': 'Net-(U32-DE)', '5': 'Net-(U32-DE)', '6': 'Net-(U32-TXD)',
       '7': '+3V3', '8': 'GND', '9': 'GND_ISO', '10': 'unconnected-(U32-SEL-Pad10)', '11': 'unconnected-(U32-NC-Pad11)',
       '12': 'Net-(D27-A1)', '13': 'Net-(D27-A2)', '14': 'Net-(U32-VISO)', '15': 'GND_ISO', '16': 'Net-(U32-VISO)'}
for n in ('unconnected-(U32-SEL-Pad10)', 'unconnected-(U32-NC-Pad11)'):
    if n not in nets:
        ni = pcbnew.NETINFO_ITEM(b, n); b.Add(ni); nets[n] = ni
pads = {p.GetNumber(): p for p in u.Pads()}
# fanout chains of pads 1 / 2 (pad -> segment -> via), found before the pads change net
def chain(p):
    out = []
    for x in tracks:
        if x.GetNetCode() != p.GetNetCode() or x.Type() == pcbnew.PCB_VIA_T: continue
        for e, o in ((x.GetStart(), x.GetEnd()), (x.GetEnd(), x.GetStart())):
            if p.HitTest(e) and x.GetLayer() == pcbnew.F_Cu:
                out.append(x)
                for v in tracks:
                    if v.Type() == pcbnew.PCB_VIA_T and v.GetNetCode() == p.GetNetCode() and (v.GetPosition() - o).EuclideanNorm() < 1000:
                        out.append(v)
    return out
c1, c2 = chain(pads['1']), chain(pads['2'])
assert len(c1) == 2 and len(c2) == 2, (len(c1), len(c2))
for x in c1: x.SetNet(nets['+3V3'])
for x in c2: x.SetNet(nets['GND'])
for k, n in NEW.items(): pads[k].SetNet(nets[n])
# C127 (100n on VCC) sits beside pins 1 / 2 with GND at y 186.55 and +3V3 at 188.1: turn it 180 so its pads follow the
# swapped pins. The via + stub at its top pad become +3V3, its old +3V3 stub and plane via at the bottom go (the pad-2
# fanout via, now GND, already touches that pad).
c = b.FindFootprintByReference('C127')
c.SetOrientationDegrees(270)
def at(x, y, tol=0.05):
    out = []
    for t_ in tracks:
        pts = [t_.GetPosition()] if t_.Type() == pcbnew.PCB_VIA_T else [t_.GetStart(), t_.GetEnd()]
        if any(abs(mm(q.x) - x) < tol and abs(mm(q.y) - y) < tol for q in pts): out.append(t_)
    return out
top = [x for x in at(138.55, 186.55) if x.GetNetname() == 'GND']
assert len(top) == 2, len(top)
for x in top: x.SetNet(nets['+3V3'])
bot = [x for x in at(136.29, 188.43) if x.GetNetname() == '+3V3']
assert len(bot) == 2, len(bot)
for x in bot: b.Remove(x)
# C128's GND via now faces C127's +3V3 pad: slide it 0.3 mm left (its stub shortens with it)
for x in at(136.7, 186.19):
    if x.Type() == pcbnew.PCB_VIA_T: x.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(136.4), pcbnew.FromMM(186.19)))
    elif abs(mm(x.GetEnd().x) - 136.7) < 0.05: x.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(136.4), x.GetEnd().y))
    else: x.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(136.4), x.GetStart().y))
gone = []
for x in tracks:
    if x.GetNetname() in ('Net-(D27-A1)', 'Net-(D27-A2)', 'Net-(U32-VISO)'):
        gone.append(x); b.Remove(x)
keepref = tracks  # keep SWIG objects alive (see sam-cpu-pcb-placement notes)
b.RemoveNative(old) if hasattr(b, 'RemoveNative') else None
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
print('removed', len(gone), 'A/B/VISO items; fanouts swapped', [(round(mm(v.GetPosition().x), 2), round(mm(v.GetPosition().y), 2)) for v in c1 + c2 if v.Type() == pcbnew.PCB_VIA_T])

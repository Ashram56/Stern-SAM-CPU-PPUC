"""c53 (board): reroute the U4 (RP2354B) -> U6/U7 data and address bus after c52 opened escape room under U4.
BUS_D0..D7, BUS_A0..A3 and BUS_IOSTB are ripped and laid again from c53_bus_routes.json, which a grid router (0.05 mm grid,
F.Cu/B.Cu, 0.2 mm tracks, 0.6/0.3 mm vias, every other copper item kept as an obstacle with its net-class clearance)
produced, routing the nets top to bottom and retrying failed ones first. BUS_DIR and BUS_OE_N keep their copper.
BUS_IOSTB is left unrouted here and added by the next change. U6's GND via (pin 11) moves 0.12 mm, to (54.62, 54.37), to keep 0.5 mm hole to hole from the BUS_D0 via.
Result: BUS_D0, D1, D6, A0 and A1 connect (they were open); the other bus nets stay connected.
Usage: c53_bus_reroute.py in.kicad_pcb out.kicad_pcb"""
import json, os, sys
import pcbnew
NETS = ['BUS_D%d' % i for i in range(8)] + ['BUS_A%d' % i for i in range(4)] + ['BUS_IOSTB']
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; M = pcbnew.ToMM
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
keep = []
for t in list(b.GetTracks()):
    if t.GetNetname() in NETS: keep.append(t); b.Remove(t)
def P(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
for t in b.GetTracks():                      # U6 pin 11 GND via and its stub
    if t.GetNetname() != 'GND': continue
    if t.Type() == pcbnew.PCB_VIA_T and abs(M(t.GetPosition().x) - 54.67) < 0.01 and abs(M(t.GetPosition().y) - 54.47) < 0.01:
        t.SetPosition(P(54.62, 54.37))
    elif t.Type() != pcbnew.PCB_VIA_T:
        for get, put in ((t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)):
            if abs(M(get().x) - 54.67) < 0.01 and abs(M(get().y) - 54.47) < 0.01: put(P(54.62, 54.37))
L = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu}
for r in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c53_bus_routes.json'))):
    if not r['ok']: continue
    assert r['net'] in NETS, r['net']
    for s in r['segs']:
        for a, c in zip(s['pts'], s['pts'][1:]):
            if a == c: continue
            t = pcbnew.PCB_TRACK(b); t.SetStart(P(*a)); t.SetEnd(P(*c)); t.SetWidth(MM(0.2)); t.SetLayer(L[s['layer']])
            t.SetNet(nets[r['net']]); b.Add(t)
    for x, y in r['vias']:
        v = pcbnew.PCB_VIA(b); v.SetPosition(P(x, y)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(nets[r['net']]); b.Add(v)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2]); print('ok')

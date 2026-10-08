"""Change 11 (2026-10-08): c11_remove_qwiic_pcb.py <in.kicad_pcb> <out.kicad_pcb>: remove the QWIIC option from a SAM_IO layout.
J2, R96, R97 and C8 are deleted (c11_dangle.py then removes the copper that only served them); the 0 ohm R9 becomes a 0.2 mm F.Cu track
between its pads and Net-(U1-RO) is merged into /485_RX. No other routing is touched."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
rx = b.FindNet('/485_RX'); ro = b.FindNet('Net-(U1-RO)')
fps = {f.GetReference(): f for f in b.GetFootprints()}
r9 = fps['R9']
p1, p2 = [p.GetPosition() for p in sorted(r9.Pads(), key=lambda p: p.GetNumber())]
for ref in ('J2', 'R96', 'R97', 'C8', 'R9'):
    b.Remove(fps[ref])
# the RO net becomes /485_RX
for t in b.GetTracks():
    if t.GetNetCode() == ro.GetNetCode(): t.SetNet(rx)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetCode() == ro.GetNetCode(): p.SetNet(rx)
t = pcbnew.PCB_TRACK(b); t.SetStart(p1); t.SetEnd(p2); t.SetWidth(pcbnew.FromMM(0.2))
t.SetLayer(pcbnew.F_Cu); t.SetNet(rx); b.Add(t)
b.Save(sys.argv[2])

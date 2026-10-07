"""Change 19 (2026-10-07): make the board taller so the lowered MH3 (c18) is a complete keyhole again, not a notch.

    kpython c19_board_taller.py sam_cpu.kicad_pcb

- Bottom edge moves from y 231.76 to 236.76 (+5 mm, across the full width). MH3's 10.4 mm clearance circle (centre
  y 230.01) now ends 1.55 mm above the edge.
- MH3 goes back to the closed keyhole footprint (screw at the slot top, 8.24 / 222.59).
- The GND / +3V3 zones follow the new bottom edge; the GND_ISO zone does not change. No part moves.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pcbnew
import place_pcb as P

W0, W2, YX, H = 120.65, 142.0, 154.0, 236.76
MH3 = (8.24, 222.59)
MAIN = [(0, 0), (W0, 0), (W0, 152.0), (114.0, 152.0), (114.0, 183.4), (120.0, 183.4), (120.0, 199.5), (W2, 199.5),
        (W2, H), (0, H)]
OUTLINE = [(0, 0), (W0, 0), (W0, YX), (W2, YX), (W2, H), (0, H)]


def main(boardfile):
    b = pcbnew.LoadBoard(boardfile)
    keep = []        # removed items stay referenced: once Python frees one, pcbnew's SWIG types break
    d = b.Drawings()
    for x in [d[i] for i in range(d.size())] if hasattr(d, 'size') else list(d):
        if x.GetLayer() == pcbnew.Edge_Cuts:
            keep.append(x)
            b.Remove(x)
    for a, c in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P.pt(*a))
        s.SetEnd(P.pt(*c))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(P.mm(0.1))
        b.Add(s)
    old = [f for f in b.GetFootprints() if f.GetReference() == 'MH3'][0]
    keep.append(old)
    b.Remove(old)
    P.keyhole(b, 'MH3', *MH3).SetLocked(True)
    for z in [b.GetArea(i) for i in range(b.GetAreaCount())]:
        if z.GetNetname() == 'GND_ISO':
            continue
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for p in MAIN:
            o.Append(P.pt(*p))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(boardfile)
    mh = [f for f in b.GetFootprints() if f.GetReference() == 'MH3'][0]
    print('outline %.2f x %.2f; MH3 courtyard' % (W2, H), [round(v, 2) for v in P.box(mh)])


if __name__ == '__main__':
    main(sys.argv[1])

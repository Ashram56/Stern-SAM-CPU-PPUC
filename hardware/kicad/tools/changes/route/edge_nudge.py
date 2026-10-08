"""Keep copper JLCPCB's 0.3 mm from the routed right edge (x 120.65 above the extension): track ends closer than
half their width + 0.3 mm move left. Board in place:

    kpython edge_nudge.py board.kicad_pcb
"""
import sys
import pcbnew

EDGE, Y_EXT, GAP = 120.65, 154.0, 0.31          # mm (board coordinates, origin offset 30 / 30)
OX = OY = 30.0


def main(path):
    b = pcbnew.LoadBoard(path)
    t = b.Tracks()
    n = 0
    for x in [t[i].Cast() for i in range(t.size())]:
        if x.Type() != pcbnew.PCB_TRACE_T:
            continue
        lim = EDGE - pcbnew.ToMM(x.GetWidth()) / 2 - GAP
        for get, put in ((x.GetStart, x.SetStart), (x.GetEnd, x.SetEnd)):
            p = get()
            px, py = pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY
            if py < Y_EXT and px > lim:
                q = pcbnew.VECTOR2I(pcbnew.FromMM(lim + OX), p.y)
                # the other tracks ending here follow
                for y in [t[i].Cast() for i in range(t.size())]:
                    if y.Type() == pcbnew.PCB_TRACE_T and y is not x and y.GetNetCode() == x.GetNetCode():
                        if y.GetStart() == p:
                            y.SetStart(q)
                        if y.GetEnd() == p:
                            y.SetEnd(q)
                put(q)
                n += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(path)
    print('track ends moved in from the edge:', n)


if __name__ == '__main__':
    main(sys.argv[1])

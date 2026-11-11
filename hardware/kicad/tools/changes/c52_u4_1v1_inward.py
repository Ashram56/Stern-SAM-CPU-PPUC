"""c52 (board): open escape room inside U4 (RP2354B) for the nets that could not leave its pads.
The +1V1 link from pin 69 area (75.55, 51.05) to pin 10 ran 0.6 mm inside the pin rows (y 51.9, x 69.6) and left no
room for a via between the pads and itself, so BUS_D0, BUS_D1, BUS_D6, BUS_A0, BUS_A1 and BOOTSEL had no exit.
It now runs 1.6 mm in (y 52.7, x 70.8), still 0.75 mm from the exposed pad, which leaves room for 0.6/0.3 vias
under the package body, between the pin rows and the new +1V1 path. c53 routes the bus through that room.
Usage: c52_u4_1v1_inward.py in.kicad_pcb out.kicad_pcb"""
import sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; F = pcbnew.F_Cu
def pt(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
def near(a, x, y, tol=0.02): return abs(a.x - MM(x)) < MM(tol) and abs(a.y - MM(y)) < MM(tol)
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
keep = []                                   # removed items stay referenced (else SWIG frees them)
def tracks(): T = b.Tracks(); return [T[i] for i in range(T.size())]
def drop(n, a, c):
    hit = [t for t in tracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() == n and
           ((near(t.GetStart(), *a) and near(t.GetEnd(), *c)) or (near(t.GetStart(), *c) and near(t.GetEnd(), *a)))]
    assert len(hit) == 1, (n, a, c, len(hit)); keep.append(hit[0]); b.Remove(hit[0])
def track(n, pts, w, lock=False):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(MM(w)); t.SetLayer(F)
        t.SetNet(nets[n]); t.SetLocked(lock); b.Add(t)

V = '+1V1'
drop(V, (75.55, 51.9), (69.6, 51.9)); drop(V, (69.6, 51.9), (69.6, 55.8))
track(V, [(75.55, 51.9), (74.75, 52.7), (70.8, 52.7), (70.8, 55.8), (69.6, 55.8)], 0.2, lock=True)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2]); print('ok')

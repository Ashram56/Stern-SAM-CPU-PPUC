"""Change 23 (2026-10-08): free the RP2354B escapes the autorouter could not finish (Vincent: "Move parts, reroute").
Run with KiCad 10's Python on the routed board:

    kpython c23_usb_bus_room.py sam_cpu.kicad_pcb

U4's USB pins 66 / 67 were fenced in: the +3V3 fan-out of pin 64 ran right above them to pin 68's via, C12 sat on
top of them, and the hand-routed +1V1 link runs just inside the pin row. R13 / R14 sat above pins 76-80 (BUS_D0-D3,
BOOTSEL, +3V3), which then had no way out.
- C12 moves 1.6 mm left (its GND stub and via with it, pad 1 joins pin 69's +3V3 via); pin 64 gets its own via inside the pin row instead of the
  track over pins 65-67.
- R13 / R14 (USB 27 R) go between J19 and C12 / L1, in line with U4 pins 66 / 67 and J19's D+ / D- pads: R14 (D+)
  left, R13 (D-) right, connector side (pin 1) on top. The pair is hand-routed and locked from pins 66 / 67 straight
  up to them (0.2 mm tracks, 0.2 mm gap).
- U7 moves 1.8 mm right and 1 mm down (clear of C31), so the eight BD lines from U6 to RN1 / RN2 get a 4.6 mm lane
  between J9 and U7. Its locked GND / +3V3 fan-out stubs and vias move with it.
- Unlocked copper on the nets of the moved parts or crossing their new courtyards is ripped (then the stubs left
  dangling); the router redoes it (tools/changes/route/, PCB.md).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pcbnew
import place_pcb as P

P.W = 142.0
P.H = 236.76
TOUCH = 5000                                                # nm
MOVES = {'R14': (43.6, 11.0), 'R13': (45.4, 11.0)}          # courtyard top-left
SHIFT = {'U7': (1.8, 1.0), 'C12': (-1.6, 0.0)}              # mm right, down
# locked +3V3 fan-out of U4 pin 64 running over pins 65-67 (board mm, both ends)
# and C12's +3V3 stub to a via in the gap above pin 66 (C12 joins pin 69's via instead)
DROP = [((45.95, 21.05), (45.95, 20.25)), ((45.95, 20.25), (44.55, 20.25)), ((44.55, 20.25), (44.3, 19.9)),
        ((44.1, 19.4), (45.2, 20.04))]
DROP_VIA = (45.2, 20.04)
C12_LINK = [(42.9, 19.4), (43.95, 19.15)]                   # C12 pad 1 (moved) to pin 69's via
PIN64 = [(45.95, 21.05), (45.95, 22.3), (45.7, 22.6)]       # new stub, via at the end
USB = {'Net-(U4-USB_DP)': [(44.75, 21.05), (44.75, 14.6), (44.4, 14.25), (44.4, 13.4)],
       'Net-(U4-USB_DM)': [(45.15, 21.05), (45.15, 15.0), (46.2, 13.95), (46.2, 13.4)]}


def track(b, net, a, c, w=0.2):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(P.pt(*a))
    t.SetEnd(P.pt(*c))
    t.SetWidth(P.mm(w))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    t.SetLocked(True)
    b.Add(t)
    return t


def main(boardfile):
    b = pcbnew.LoadBoard(boardfile)
    nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
    fps = {f.GetReference(): f for f in list(b.GetFootprints())}
    t = b.Tracks()
    tracks = [t[i].Cast() for i in range(t.size())]
    keep = []

    def near(p, q):
        return abs(pcbnew.ToMM(p.x) - 30 - q[0]) < 0.02 and abs(pcbnew.ToMM(p.y) - 30 - q[1]) < 0.02
    drop = [x for x in tracks if x.Type() == pcbnew.PCB_TRACE_T and x.GetNetname() == '+3V3' and any(
        near(x.GetStart(), a) and near(x.GetEnd(), c) or near(x.GetStart(), c) and near(x.GetEnd(), a) for a, c in DROP)]
    drop += [x for x in tracks if x.Type() == pcbnew.PCB_VIA_T and near(x.GetPosition(), DROP_VIA)]
    assert len(drop) == len(DROP) + 1, len(drop)
    for x in drop:
        b.Remove(x)
        keep.append(x)
    tracks = [x for x in tracks if all(x is not y for y in drop)]

    occ = P.Occupancy()
    for r, f in fps.items():
        if r not in MOVES and r not in SHIFT:
            occ.add(f)
    moved = set()
    for r, (dx, dy) in SHIFT.items():
        pads = list(fps[r].Pads())
        others = [p for f in fps.values() if f is not fps[r] for p in f.Pads()]
        stubs = [x for x in tracks if x.IsLocked() and x.Type() == pcbnew.PCB_TRACE_T and any(
            p.GetNetCode() == x.GetNetCode() and (p.HitTest(x.GetStart()) or p.HitTest(x.GetEnd())) for p in pads)
            and not any(p.GetNetCode() == x.GetNetCode() and (p.HitTest(x.GetStart()) or p.HitTest(x.GetEnd()))
                        for p in others)]       # a stub between two parts stays
        ends = [e for x in stubs for e in (x.GetStart(), x.GetEnd())]
        vias = [v for v in tracks if v.Type() == pcbnew.PCB_VIA_T and v.IsLocked() and any(v.GetPosition() == e for e in ends)]
        d = pcbnew.VECTOR2I(P.mm(dx), P.mm(dy))
        fps[r].Move(d)
        for x in stubs + vias:
            x.Move(d)
            moved.add(id(x))
        assert occ.free(P.box(fps[r])), (r, P.box(fps[r]))
        occ.add(fps[r])
    for r, xy in MOVES.items():
        P.move_box_to(fps[r], *xy)
        assert occ.free(P.box(fps[r])), (r, P.box(fps[r]))
        occ.add(fps[r])

    # rip-up: nets of the moved parts, and unlocked copper under their new courtyards
    rects = []
    for r in list(MOVES) + list(SHIFT):
        x0, y0, x1, y1 = P.box(fps[r], 0.2)
        rects.append(pcbnew.SHAPE_RECT(P.pt(x0, y0), P.mm(x1 - x0), P.mm(y1 - y0)))
    # and the corridor of the hand-routed pair / pin 64 stub
    rects.append(pcbnew.SHAPE_RECT(P.pt(44.2, 12.8), P.mm(2.4), P.mm(10.8)))
    ripnets = {p.GetNetname() for r in list(MOVES) + list(SHIFT) for p in fps[r].Pads()} - {'GND', '+3V3', '+5V', ''}
    rip = [x for x in tracks if id(x) not in moved and not x.IsLocked() and (
        x.GetNetname() in ripnets or any(x.GetEffectiveShape().Collide(rc, 0) for rc in rects))]
    for x in rip:
        b.Remove(x)
    ids = {id(x) for x in rip}
    cut = {x.GetNetCode() for x in rip}
    live = [x for x in tracks if id(x) not in ids and x.GetNetCode() in cut]
    pads = [p for f in fps.values() for p in f.Pads() if p.GetNetCode() in cut]
    n_dead = 0
    while True:
        segs = [x for x in live if x.Type() == pcbnew.PCB_TRACE_T]
        vias = [x for x in live if x.Type() == pcbnew.PCB_VIA_T]

        def touches(tr, q):
            n = tr.GetNetCode()
            return (any(p.GetNetCode() == n and p.IsOnLayer(tr.GetLayer()) and p.HitTest(q) for p in pads)
                    or any(o is not tr and o.GetNetCode() == n and o.GetLayer() == tr.GetLayer()
                           and o.GetLength() > TOUCH and pcbnew.SEG(o.GetStart(), o.GetEnd()).Distance(q) <= TOUCH
                           for o in segs)
                    or any(v.GetNetCode() == n and v.HitTest(q, 0) for v in vias))
        dead = [x for x in segs if not x.IsLocked() and not (touches(x, x.GetStart()) and touches(x, x.GetEnd()))]
        for v in vias:
            if v.IsLocked():
                continue
            q = v.GetPosition()
            on = {x.GetLayer() for x in segs if x.GetNetCode() == v.GetNetCode() and x.HitTest(q, 0)}
            plane = v.GetNetname() in ('GND', '+3V3')
            if not (len(on) >= 2 or on and plane or any(p.GetNetCode() == v.GetNetCode() and p.HitTest(q) for p in pads)):
                dead.append(v)
        if not dead:
            break
        for x in dead:
            b.Remove(x)
        ids = {id(x) for x in dead}
        live = [x for x in live if id(x) not in ids]
        rip += dead
        n_dead += len(dead)

    # hand routes
    for a, c in zip(PIN64, PIN64[1:]):
        track(b, nets['+3V3'], a, c)
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P.pt(*PIN64[-1]))
    v.SetWidth(P.mm(0.6))
    v.SetDrill(P.mm(0.3))
    v.SetNet(nets['+3V3'])
    v.SetLocked(True)
    b.Add(v)
    track(b, nets['+3V3'], *C12_LINK)
    for n, pts in USB.items():
        for a, c in zip(pts, pts[1:]):
            track(b, nets[n], a, c)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(boardfile)
    print('ripped %d tracks / vias on %d nets (%d dangling stubs); %d locked stubs / vias moved' % (
        len(rip), len({x.GetNetname() for x in rip}), n_dead, len(moved)))
    for r in list(MOVES) + list(SHIFT):
        print(' ', r, [round(v, 2) for v in P.box(fps[r])])


if __name__ == '__main__':
    main(sys.argv[1])

"""Change 20 (2026-10-07): move the line-in jack J30 next to the amplifier inputs (Vincent: far from the amps it
picks up noise). Run with KiCad 10's Python:

    kpython c20_line_in_near_amps.py sam_cpu.kicad_pcb

- J30 goes from the bottom of the extension to the right edge just below J24, level with the 470 R inputs R187 /
  R190 and about 10 mm from U22's outputs: opening on the right edge, courtyard x 105.8-124.6, y 86.7-96.0.
- R193 / R200 (subwoofer low-pass, in J30's spot) move into the free row below R197 / R198.
- R193 / R200 keep their locked GND / +3V3 fan-out stubs (moved with them); fan-out stubs under J30 are removed.
- Unlocked tracks and vias crossing the three new courtyards are ripped (with the stubs left dangling); the router
  redoes them.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pcbnew
import place_pcb as P

P.W = 142.0
J30_FRONT_X, J30_Y = 120.65 - 0.3, 86.7     # body front 0.3 mm inside the right edge, courtyard top
MOVES = {'R193': (94.95, 91.4), 'R200': (98.6, 91.4)}       # courtyard top-left
TOUCH = 5000                                                # nm


def main(boardfile):
    b = pcbnew.LoadBoard(boardfile)
    fps = {f.GetReference(): f for f in list(b.GetFootprints())}
    t = b.Tracks()
    tracks = [t[i] for i in range(t.size())]
    occ = P.Occupancy()
    for r, f in fps.items():
        if r not in MOVES and r != 'J30':
            occ.add(f)
    # the plane fan-out stubs (locked, c07 / c09) of the moved resistors travel with them
    moved = set()
    for r, xy in MOVES.items():
        before = fps[r].GetPosition()
        pads = list(fps[r].Pads())
        stubs = [tr for tr in tracks if tr.IsLocked() and any(
            p.GetNetCode() == tr.GetNetCode() and (p.HitTest(tr.GetStart()) or p.HitTest(tr.GetEnd())) for p in pads)]
        vias = [v for v in tracks if v.Type() == pcbnew.PCB_VIA_T and v.IsLocked() and any(
            tr.Type() == pcbnew.PCB_TRACE_T and v.GetNetCode() == tr.GetNetCode()
            and (tr.GetStart() == v.GetPosition() or tr.GetEnd() == v.GetPosition()) for tr in stubs)]
        P.move_box_to(fps[r], *xy)
        d = fps[r].GetPosition() - before
        for x in stubs + vias:
            if id(x) not in moved:
                x.Move(d)
                moved.add(id(x))
        assert occ.free(P.box(fps[r])), (r, P.box(fps[r]))
        occ.add(fps[r])
    j = fps['J30']
    bx = P.box(j)
    P.move_box_to(j, bx[0] + J30_FRONT_X - (bx[2] - 4.55), J30_Y)   # barrel 4.55 mm past the body front
    bx = P.box(j)
    assert not any(P.overlaps(bx, o) for o in occ.boxes), bx

    rects = []
    for r in list(MOVES) + ['J30']:
        x0, y0, x1, y1 = P.box(fps[r], 0.2)
        rects.append(pcbnew.SHAPE_RECT(P.pt(x0, y0), P.mm(x1 - x0), P.mm(y1 - y0)))
    # unlocked copper under the new courtyards, and locked fan-out stubs under J30 (they would take J30's pad nets)
    rip = [tr for tr in tracks if id(tr) not in moved and (not tr.IsLocked() or tr.GetNetname() in ('GND', '+3V3')
           and tr.GetEffectiveShape().Collide(rects[-1], 0))
           and any(tr.GetEffectiveShape().Collide(rc, 0) for rc in rects)]
    for tr in rip:
        b.Remove(tr)
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
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(boardfile)
    print('ripped %d tracks / vias on %d nets (%d of them dangling stubs)' % (
        len(rip), len({x.GetNetname() for x in rip}), n_dead))
    for r in list(MOVES) + ['J30']:
        print(' ', r, [round(v, 2) for v in P.box(fps[r])])


if __name__ == '__main__':
    main(sys.argv[1])

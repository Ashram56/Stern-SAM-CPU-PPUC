"""Change 22 (2026-10-07): RP2354B fan-out fixes (Vincent, "Fix all"). Run with KiCad 10's Python after c21:

    kicad-cli sch export netlist --format kicadsexpr -o net.net sam_cpu.kicad_sch
    kpython c22_board_rp_fanout.py net.net sam_cpu.kicad_pcb

- U6 / U7 (bus buffers) turn 180 degrees in place: their RP2354B side (A pins) now faces U4 and their J9 side faces
  J9 / RN1-RN3. With c21's reversed channel order the bits arrive in the same top-to-bottom order as U4's pins.
  Their GND / +3V3 fan-out stubs and vias turn with them; their +5V copper is ripped.
- R13 / R14 (USB series resistors) swap places: D+ on the left, D- on the right, the order of U4's USB pins and of
  J19's B row (the A / B row join under J19 is the one crossing a USB-C receptacle always needs).
- R205 / R207 / R209 (RP2354B side of the RS485 port) move from the transceiver to a column between U7 and the SWD
  header J20, a few mm from U4's GPIO20-22 corner, so the long run to U32 is behind the 1 k series resistors.
- Pad nets follow the netlist; every track and via of the re-ordered bus nets, the USB nets and the RS485 nets that
  were cut, plus unlocked copper crossing the new courtyards, is ripped (then the stubs left dangling); the router
  redoes them.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pcbnew
import place_pcb as P

TOUCH = 5000                                                # nm
BUFFERS = ('U6', 'U7')
POWER = ('GND', '+3V3')                       # plane fan-outs (stub + via) turn with the buffers
# RS485 resistors upright in the free column between U7 and J20 (left of the SWD lanes, so the RS485 runs from U4's
# GPIO20-22 corner never cross them), RP pin (1) on top: courtyard top-left
RS485 = {'R207': (31.4, 36.7), 'R205': (31.4, 39.95), 'R209': (31.4, 43.2)}


def main(netfile, boardfile):
    comps, nets = P.load_netlist(netfile)
    b = pcbnew.LoadBoard(boardfile)
    netinfo = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}

    def net(name):
        if name not in netinfo:
            n = pcbnew.NETINFO_ITEM(b, name)
            b.Add(n)
            netinfo[name] = n
        return netinfo[name]
    padnet = {(r, p): name for name, nodes in nets for r, p in nodes}
    fps = {f.GetReference(): f for f in list(b.GetFootprints())}
    t = b.Tracks()
    tracks = [t[i] for i in range(t.size())]

    # 1. buffers: turn 180 degrees about their own origin, with their power fan-out
    turned = set()
    five = []                                   # +5V copper on the buffers' pads: ripped, re-routed
    for r in BUFFERS:
        f = fps[r]
        box0 = P.box(f)
        pads = [p for p in f.Pads() if p.GetNetname() in POWER]
        stubs = [x for x in tracks if x.Type() == pcbnew.PCB_TRACE_T and x.GetNetname() in POWER and any(
            p.GetNetCode() == x.GetNetCode() and (p.HitTest(x.GetStart()) or p.HitTest(x.GetEnd())) for p in pads)]
        ends = [e for x in stubs for e in (x.GetStart(), x.GetEnd())]
        vias = [v for v in tracks if v.Type() == pcbnew.PCB_VIA_T and v.GetNetname() in POWER
                and any(v.GetPosition() == e for e in ends)]
        c = f.GetPosition()
        p5 = [p for p in f.Pads() if p.GetNetname() == '+5V']
        five += [x for x in tracks if x.GetNetname() == '+5V' and any(
            p.HitTest(x.GetPosition() if x.Type() == pcbnew.PCB_VIA_T else x.GetStart())
            or x.Type() == pcbnew.PCB_TRACE_T and p.HitTest(x.GetEnd()) for p in p5)]
        f.Rotate(c, pcbnew.EDA_ANGLE(180, pcbnew.DEGREES_T))
        for x in stubs + vias:
            x.Rotate(c, pcbnew.EDA_ANGLE(180, pcbnew.DEGREES_T))
            turned.add(id(x))
        assert all(abs(a - b_) < 0.05 for a, b_ in zip(box0, P.box(f))), (r, box0, P.box(f))

    # 2. USB resistors swap places
    a, c = fps['R13'], fps['R14']
    pa, pc = a.GetPosition(), c.GetPosition()
    a.SetPosition(pc)
    c.SetPosition(pa)

    # 3. pad nets from the netlist (U6 / U7 / RN1-RN3 / R25 channel order)
    changed = []
    for ref, f in fps.items():
        if ref not in comps:
            continue
        for pad in f.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n and n != pad.GetNetname():
                changed.append('%s.%s %s' % (ref, pad.GetNumber(), n))
                pad.SetNet(net(n))

    # 4. RS485 resistors next to U4
    occ = P.Occupancy()
    for r, f in fps.items():
        if r not in RS485:
            occ.add(f)
    for r, xy in RS485.items():
        f = fps[r]
        for deg in (90, 270):
            f.SetOrientationDegrees(deg)
            p1, p2 = [P.pad_xy(p) for p in sorted(f.Pads(), key=lambda p: p.GetNumber())]
            if p1[1] < p2[1]:
                break
        P.move_box_to(f, *xy)
        assert occ.free(P.box(f)), (r, P.box(f))
        occ.add(f)

    # 5. rip-up
    bus = {n for n in netinfo if n.startswith(('BUS_D', 'BUS_A', 'BUS_IOSTB', 'BUS_DIR', 'BUS_OE_N', 'BD', 'BA', 'BSTB'))
           or n.startswith(('Net-(RN', 'Net-(U7-', '/IO bus/B'))}
    usb = {n for n in netinfo if 'USB_D' in n or n.startswith('Net-(J19-D')}
    rs485 = {n for n in netinfo if n.startswith(('RP_RS485', '/RS485 and I2S/RS485_'))}
    rects = []
    for r in list(BUFFERS) + ['R13', 'R14'] + list(RS485):
        x0, y0, x1, y1 = P.box(fps[r], 0.2)
        rects.append(pcbnew.SHAPE_RECT(P.pt(x0, y0), P.mm(x1 - x0), P.mm(y1 - y0)))
    rip = [x for x in tracks if id(x) not in turned and (
        x.GetNetname() in bus | usb | rs485 and x.GetNetname() not in POWER
        or id(x) in {id(y) for y in five}
        or not x.IsLocked() and any(x.GetEffectiveShape().Collide(rc, 0) for rc in rects))]
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
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(boardfile)
    print('pad nets changed:', len(changed))
    print('ripped %d tracks / vias on %d nets (%d dangling stubs); %d power stubs / vias turned with the buffers' % (
        len(rip), len({x.GetNetname() for x in rip}), n_dead, len(turned)))
    for r in list(BUFFERS) + ['R13', 'R14'] + list(RS485):
        print(' ', r, fps[r].GetOrientationDegrees(), [round(v, 2) for v in P.box(fps[r])])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

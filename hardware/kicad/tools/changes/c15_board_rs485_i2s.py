"""Change 15 (2026-10-07): bring the board up to date with c13 / c14 (RS485 port, I2S header), without moving any
existing part. Run with KiCad 10's Python:

    kicad-cli sch export netlist --format kicadsexpr -o net.net sam_cpu.kicad_sch
    kpython c15_board_rs485_i2s.py net.net sam_cpu.kicad_pcb

- Pad nets from the netlist (RP2354B GPIO20-22, J21 pins 7 / 26 / 29, the I2S nets on J28).
- J27 (RJ45) on the right edge where J5 was, opening facing out of the board edge, below MH10.
- J28 (I2S header) on the right edge between J27 and J18; the transceiver group left of J27, in the space the
  J5 driver left.
- Unlocked tracks and vias under the new footprints are ripped up (the router redoes them).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pcbnew
import place_pcb as P

W = P.W
NEW = ['U32', 'R204', 'R205', 'R206', 'R207', 'R208', 'R209', 'R210', 'R211', 'R212', 'C127', 'D27', 'JP2', 'J27',
       'J28']
# J27 courtyard spans x 102.2 .. 121.0 (front 0.35 mm past the edge, like J17 / J22 / J23), y 152.3 .. 168.7
J27_BOX = (102.2, 152.3)
REGIONS = {
    'J28': [(113.0, 170.4, 120.35, 183.3)],
    'rs485': [(84.0, 152.2, 101.8, 169.6), (105.4, 170.4, 112.8, 183.3)],
}


def main(netfile, boardfile):
    comps, nets = P.load_netlist(netfile)
    board = pcbnew.LoadBoard(boardfile)
    netinfo = {n.GetNetname(): n for n in board.GetNetInfo().NetsByName().values()}

    def net(name):
        if name not in netinfo:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            netinfo[name] = n
        return netinfo[name]
    padnet = {(r, p): name for name, nodes in nets for r, p in nodes}
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    changed = []
    for ref, f in fps.items():
        if ref not in comps:
            continue
        for pad in f.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n and n != pad.GetNetname():
                changed.append('%s.%s %s' % (ref, pad.GetNumber(), n))
                pad.SetNet(net(n))
    gone = [r for r in fps if r not in comps and not r.startswith('MH')]
    assert not gone, gone
    added = []
    for ref in NEW:
        c = comps[ref]
        f = P.load_fp(c['fp'])
        f.SetReference(ref)
        f.SetValue(c['value'])
        f.SetFPID(pcbnew.LIB_ID(*c['fp'].split(':')))
        f.SetPath(pcbnew.KIID_PATH(c['path']))
        f.SetSheetname(c['sheetname'] or '')
        f.SetSheetfile(c['sheet'] or '')
        board.Add(f)
        for pad in f.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(net(n))
        fps[ref] = f
        added.append(ref)
    assert not [r for r in comps if r not in fps], [r for r in comps if r not in fps]

    occ = P.Occupancy()
    for ref, f in fps.items():
        if ref not in added:
            occ.add(f)
    # RJ45: rotated so the plug opening (courtyard +y side in the library) faces the right board edge
    j = fps['J27']
    j.SetOrientationDegrees(90)
    P.move_box_to(j, *J27_BOX)
    b = P.box(j)
    assert b[2] > W and not any(P.overlaps(b, o) for o in occ.boxes), b
    occ.add(j)
    j.SetLocked(True)
    left = P.pack([fps['J28']], REGIONS['J28'], occ)
    group = [fps[r] for r in NEW if r not in ('J27', 'J28', 'C127')]
    left += P.pack(group, REGIONS['rs485'], occ, {'U32': 1.6})
    # decoupling capacitor upright just right of U32, level with pin 8 (VCC); slide down if that spot is taken
    c, ub = fps['C127'], P.box(fps['U32'])
    vcc = [p for p in fps['U32'].Pads() if p.GetNetname() == '+3V3'][0]
    c.SetOrientationDegrees(90 if padnet[('C127', '1')] == '+3V3' else 270)
    for k in range(12):
        P.move_box_to(c, ub[2] + 0.2, P.pad_xy(vcc)[1] - 1.0 + 0.5 * k)
        if occ.free(P.box(c)):
            occ.add(c)
            break
    else:
        left.append('C127')
    assert not left, left

    # rip up unlocked copper crossing the new courtyards (+0.2 mm)
    rects = []
    for r in NEW:
        x0, y0, x1, y1 = P.box(fps[r], 0.2)
        rects.append(pcbnew.SHAPE_RECT(P.pt(x0, y0), P.mm(x1 - x0), P.mm(y1 - y0)))
    t = board.Tracks()
    tracks = [t[i] for i in range(t.size())]
    rip = [tr for tr in tracks if not tr.IsLocked()
           and any(tr.GetEffectiveShape().Collide(rc, 0) for rc in rects)]
    for tr in rip:
        board.Remove(tr)
    # then the unlocked stubs those cuts left dangling (pcbnew's Tracks() proxy breaks after removals: keep a list)
    ids = {id(x) for x in rip}
    live = [x for x in tracks if id(x) not in ids]
    pads = [p for f in fps.values() for p in f.Pads()]
    cut = {x.GetNetCode() for x in rip}
    pads = [p for p in pads if p.GetNetCode() in cut]
    live = [x for x in live if x.GetNetCode() in cut]           # only the nets that were cut can dangle
    while True:
        segs = [x for x in live if x.Type() == pcbnew.PCB_TRACE_T]
        vias = [x for x in live if x.Type() == pcbnew.PCB_VIA_T]

        def touches(tr, q):
            n = tr.GetNetCode()
            return (any(p.GetNetCode() == n and p.IsOnLayer(tr.GetLayer()) and p.HitTest(q) for p in pads)
                    or any(o is not tr and o.GetNetCode() == n and o.GetLayer() == tr.GetLayer() and o.HitTest(q, 0)
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
            board.Remove(x)
        ids = {id(x) for x in dead}
        live = [x for x in live if id(x) not in ids]
        rip += dead
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(boardfile)
    print('pad nets changed:', len(changed), '; '.join(changed))
    print('new footprints:', ' '.join(added))
    print('tracks / vias ripped (under them, then dangling):', len(rip), 'on', len({x.GetNetname() for x in rip}), 'nets')
    for r in added:
        print(' ', r, [round(v, 1) for v in P.box(fps[r])])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

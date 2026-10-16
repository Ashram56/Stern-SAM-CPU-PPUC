"""Change 18 (2026-10-07): board side of c16 / c17 (isolated RS485, two top-entry RJ45s, line-in jack), the right-hand
extension back, and the bottom-left keyhole lowered. No existing part moves except MH3. Run with KiCad 10's Python:

    kicad-cli sch export netlist --format kicadsexpr -o net.net sam_cpu.kicad_sch
    kpython c18_board_isolated_rs485.py net.net sam_cpu.kicad_pcb

- Outline: the 142 mm extension below the Pi comes back (right edge at x 142 from y 154 down, as in draft 0.4).
- MH3 (bottom-left keyhole): its screw position moves 7.42 mm down, from y 215.17 to 222.59, where its clearance
  circle used to be. Read off the Stern drawing, the bottom keyholes sat one slide-length higher than the bottom round
  hole MH4 (y 222.86), while the top keyholes sit level with MH5: so with the board slid down onto its screws, MH3 now
  lines up with MH4. The 10.4 mm clearance circle would now cross the bottom edge, so it becomes an open notch in the
  outline (same slot, 4.4 mm wide, screw at its rounded top).
- The 15 parts c15 placed for page 13 are taken off and all 24 page-13 parts are placed again: U32 (ADM2682E) straddles
  the isolation gap at x 114.5, the 1 k / pull resistors and VCC capacitors on its logic side (where c15 had them),
  the isoPower capacitors, TVS and termination on its cable side, J27 / J29 stacked in the extension, J28 below the
  logic group, J30 at the bottom of the extension with its opening on the right edge.
- Copper: the GND / +3V3 zones skip the cable-side area and a new GND_ISO zone (all four layers) fills it, 2 mm apart.
  Every track or via crossing the new courtyards, the cable-side area or the MH3 notch, and the old DAC output nets
  (now split through J30), are ripped up; the router redoes them.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pcbnew
import place_pcb as P

P.W = 142.0                                  # Occupancy.free() bound: the explicit regions below keep parts on board
W0, W2, YX, H = 120.65, 142.0, 154.0, 231.76
PAGE13 = ['U32', 'R204', 'R205', 'R206', 'R207', 'R208', 'R209', 'R210', 'R211', 'R212', 'C127', 'C128', 'C129',
          'C130', 'C131', 'C132', 'D27', 'JP2', 'J27', 'J28', 'J29', 'J30']
ISO_NETS = {'RS485_A', 'RS485_B', 'RS485_TERM', 'VISO', 'GND_ISO'}
# cable side (GND_ISO copper) and the hole cut in the GND / +3V3 zones for it (2 mm wider)
ISO = [(116.0, 154.0), (W2, 154.0), (W2, 197.5), (122.0, 197.5), (122.0, 181.4), (116.0, 181.4)]
MAIN = [(0, 0), (W0, 0), (W0, 152.0), (114.0, 152.0), (114.0, 183.4), (120.0, 183.4), (120.0, 199.5), (W2, 199.5),
        (W2, H), (0, H)]
U32_AT = (114.5, 161.0)                      # centre; pins 1-8 (logic) left, 9-16 (cable) right
J27_BOX, J29_BOX = (124.9, 155.0), (124.9, 173.6)
# decoupling capacitors upright beside U32's supply pins (VCC 2 / 7 at y 157.8 / 164.2, VISOIN 15 / VISOOUT 10 at the
# same heights on the cable side): courtyard top-left and orientation
CAPS = {'C128': (104.4, 155.4, 90), 'C127': (106.75, 155.8, 90), 'C129': (106.75, 162.6, 90),
        'C132': (120.8, 155.8, 90), 'C130': (120.8, 162.6, 90), 'C131': (122.5, 162.2, 90)}
REGIONS = {
    'logic': [(90.0, 152.2, 104.0, 169.6)],
    'iso': [(116.2, 168.4, 124.6, 181.1), (120.75, 154.3, 124.6, 162.0)],
    'J28': [(105.4, 170.4, 113.6, 183.3)],
}
J30_FRONT_X, J30_Y = W2 - 0.3, 201.0        # body front 0.3 mm inside the right edge (pad clearance), top at y 201
# MH3: screw at the slot top; open keyhole notch from the bottom edge
MH3 = (8.24, 222.59)
SLOT_R, CIRC_R, DROP = 2.2, 5.2, 7.42
TOUCH = 5000                                 # nm


def pt(x, y):
    return P.pt(x, y)


def seg(b, a, c):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(*a))
    s.SetEnd(pt(*c))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(P.mm(0.1))
    b.Add(s)


def arc(b, a, m, c):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(pt(*a), pt(*m), pt(*c))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(P.mm(0.1))
    b.Add(s)


def outline(b):
    """outline with the extension and the MH3 notch: segments and arcs, clockwise on screen"""
    x, y = MH3
    cy = y + DROP                                       # clearance circle centre (below the board edge's reach)
    dx = math.sqrt(CIRC_R ** 2 - (H - cy) ** 2)         # circle meets the bottom edge
    dy = math.sqrt(CIRC_R ** 2 - SLOT_R ** 2)           # circle meets the slot sides
    on = lambda deg, r=CIRC_R, c=(x, cy): (c[0] + r * math.cos(math.radians(deg)), c[1] + r * math.sin(math.radians(deg)))
    a1 = math.degrees(math.atan2(H - cy, dx))
    a2 = math.degrees(math.atan2(-dy, SLOT_R))
    pts = [(0, 0), (W0, 0), (W0, YX), (W2, YX), (W2, H), (x + dx, H)]
    for a, c in zip(pts, pts[1:]):
        seg(b, a, c)
    arc(b, (x + dx, H), on((a1 + a2) / 2), (x + SLOT_R, cy - dy))
    seg(b, (x + SLOT_R, cy - dy), (x + SLOT_R, y))
    arc(b, (x + SLOT_R, y), (x, y - SLOT_R), (x - SLOT_R, y))
    seg(b, (x - SLOT_R, y), (x - SLOT_R, cy - dy))
    arc(b, (x - SLOT_R, cy - dy), on(180 - (a1 + a2) / 2), (x - dx, H))
    seg(b, (x - dx, H), (0, H))
    seg(b, (0, H), (0, 0))


def mh3(b):
    """MH3 as a pad-less footprint marking the notch (the hole itself is in the outline)"""
    fp = pcbnew.FOOTPRINT(b)
    fp.SetReference('MH3')
    fp.SetValue('Keyhole (open)')
    fp.SetFPID(pcbnew.LIB_ID('sam_cpu', 'Keyhole_SAM_Open'))
    b.Add(fp)
    x, y = MH3
    fp.SetPosition(pt(x, y))
    r = pcbnew.PCB_SHAPE(fp)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetLayer(pcbnew.F_CrtYd)
    r.SetWidth(P.mm(0.05))
    fp.Add(r)
    r.SetStart(pt(x - CIRC_R - 0.5, y - SLOT_R - 0.5))
    r.SetEnd(pt(x + CIRC_R + 0.5, H))
    P.board_only(fp)
    fp.Reference().SetPosition(pt(x + 7, y - 3))
    fp.Value().SetVisible(False)
    fp.SetLocked(True)
    return fp


def poly(points):
    s = pcbnew.SHAPE_POLY_SET()
    s.NewOutline()
    for p in points:
        s.Append(pt(*p))
    return s


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
    # pcbnew's collection proxies break after Remove(): take every list up front
    fps = {f.GetReference(): f for f in list(b.GetFootprints())}
    t = b.Tracks()
    tracks = [t[i] for i in range(t.size())]
    zones = [b.GetArea(i) for i in range(b.GetAreaCount())]
    d = b.Drawings()
    edges = [d[i] for i in range(d.size()) if d[i].GetLayer() == pcbnew.Edge_Cuts] if hasattr(d, 'size') else \
        [x for x in d if x.GetLayer() == pcbnew.Edge_Cuts]
    old_dac = {'Net-(U22-OUTL)', 'Net-(U22-OUTR)'}

    # 1. page-13 footprints off, MH3 replaced
    removed = [r for r in PAGE13 if r in fps]
    keep = []        # removed footprints must stay referenced: once Python frees one, pcbnew's SWIG types break
    for r in removed + ['MH3']:
        keep.append(fps.pop(r))
        b.Remove(keep[-1])
    fps['MH3'] = mh3(b)

    # 2. pad nets of the remaining parts (U22 / R187 / R190 / TP19 / TP20 now split through J30)
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

    # 3. page-13 footprints back from the library
    for ref in PAGE13:
        c = comps[ref]
        f = P.load_fp(c['fp'])
        f.SetReference(ref)
        f.SetValue(c['value'])
        f.SetFPID(pcbnew.LIB_ID(*c['fp'].split(':')))
        f.SetPath(pcbnew.KIID_PATH(c['path']))
        f.SetSheetname(c['sheetname'] or '')
        f.SetSheetfile(c['sheet'] or '')
        b.Add(f)
        for pad in f.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(net(n))
        fps[ref] = f
    missing = [r for r in comps if r not in fps]
    assert not missing, missing

    # 4. outline and zones
    for d in edges:
        b.Remove(d)
    outline(b)
    tmpl = None
    for z in zones:
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for p in MAIN:
            o.Append(pt(*p))
        if z.GetNetname() == 'GND' and tmpl is None:
            tmpl = z
    iso = pcbnew.ZONE(tmpl)                      # copy of a GND zone: same clearance / thermal settings
    iso.SetNet(net('GND_ISO'))
    ls = pcbnew.LSET()
    for L in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(L)
    iso.SetLayerSet(ls)
    o = iso.Outline()
    o.RemoveAllContours()
    o.NewOutline()
    for p in ISO:
        o.Append(pt(*p))
    iso.SetZoneName('GND_ISO')
    b.Add(iso)

    # 5. placement
    occ = P.Occupancy()
    for ref, f in fps.items():
        if ref not in PAGE13:
            occ.add(f)
    u = fps['U32']
    u.SetPosition(pt(*U32_AT))
    assert occ.free(P.box(u)), P.box(u)
    occ.add(u)
    for ref, xy in (('J27', J27_BOX), ('J29', J29_BOX)):
        P.move_box_to(fps[ref], *xy)
        bx = P.box(fps[ref])
        assert occ.free(bx) and bx[2] < W2 - 0.3, (ref, bx)
        occ.add(fps[ref])
    # J30 (CUI SJ1-3535NG): plug opening at footprint -y (body front at local y -1.2, barrel 4.55 mm past it to the
    # courtyard), turned to face the right edge
    j = fps['J30']
    j.SetOrientationDegrees(270)
    pad = {p.GetNumber(): P.pad_xy(p) for p in j.Pads()}
    assert pad['TN'][0] < pad['S'][0], pad            # switch contacts at the back: opening faces +x
    bx = P.box(j)
    front = bx[2] - 4.55
    P.move_box_to(j, bx[0] + J30_FRONT_X - front, J30_Y)
    bx = P.box(j)
    assert not any(P.overlaps(bx, o) for o in occ.boxes), bx
    occ.add(j)
    for r in ('J27', 'J29', 'J30', 'U32'):
        fps[r].SetLocked(True)
    left = P.pack([fps['J28']], REGIONS['J28'], occ)
    for r, (x0, y0, deg) in CAPS.items():
        fps[r].SetOrientationDegrees(deg)
        P.move_box_to(fps[r], x0, y0)
        assert occ.free(P.box(fps[r])), (r, P.box(fps[r]))
        occ.add(fps[r])
    left += P.pack([fps[r] for r in ('D27', 'R211', 'JP2')], REGIONS['iso'], occ)
    left += P.pack([fps[r] for r in ('R204', 'R205', 'R206', 'R207', 'R208', 'R209', 'R210', 'R212')],
                   REGIONS['logic'], occ)
    assert not left, left

    # 6. rip-up: new courtyards, the MH3 notch, the cable-side area (anything not on a cable-side net), old DAC nets
    rects = []
    for r in PAGE13 + ['MH3']:
        x0, y0, x1, y1 = P.box(fps[r], 0.2)
        rects.append(pcbnew.SHAPE_RECT(pt(x0, y0), P.mm(x1 - x0), P.mm(y1 - y0)))
    gap = poly([(114.0, 152.0), (W2, 152.0), (W2, 199.5), (120.0, 199.5), (120.0, 183.4), (114.0, 183.4)])
    iso_names = {n for n in netinfo if n.split('/')[-1] in ISO_NETS}

    def inside(p):
        return gap.Contains(p)

    def hit(tr):
        if tr.GetNetname() in old_dac:
            return True
        if any(tr.GetEffectiveShape().Collide(rc, 0) for rc in rects):
            return True
        if tr.GetNetname() in iso_names:
            return False
        if tr.Type() == pcbnew.PCB_VIA_T:
            return inside(tr.GetPosition())
        a, c = tr.GetStart(), tr.GetEnd()
        n = max(2, int(pcbnew.ToMM((c - a).EuclideanNorm()) / 0.25))
        return any(inside(pcbnew.VECTOR2I(int(a.x + (c.x - a.x) * k / n), int(a.y + (c.y - a.y) * k / n)))
                   for k in range(n + 1))
    rip = [tr for tr in tracks if hit(tr)]
    locked = [tr for tr in rip if tr.IsLocked()]
    for tr in rip:
        b.Remove(tr)
    # stubs left dangling on the nets that were cut (as in c15, but a track end must sit on the other track's centre
    # line: within its width is not enough, or a chain of tiny router leftovers holds itself up)
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
                           and o.GetLength() > TOUCH and pcbnew.SEG(o.GetStart(), o.GetEnd()).Distance(q) <= TOUCH for o in segs)
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
        n_dead += len(dead)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(boardfile)
    print('page-13 footprints replaced:', len(removed), 'removed,', len(PAGE13), 'placed')
    print('pad nets changed:', len(changed), '; '.join(changed))
    print('ripped: %d tracks / vias (%d locked) on %d nets, then %d dangling' % (
        len(rip), len(locked), len({x.GetNetname() for x in rip}), n_dead))
    for r in PAGE13 + ['MH3']:
        print(' ', r, fps[r].GetValue(), [round(v, 2) for v in P.box(fps[r])])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

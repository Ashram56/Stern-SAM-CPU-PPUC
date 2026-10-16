"""Push apart vias of different nets whose drilled holes are closer than JLCPCB's 0.5 mm (hole to hole, different
nets). Moves the unlocked via (or a GND / +3V3 plane fan-out via) of each pair (with the track ends on it) straight away from the other, if the moved
via and tracks still clear every other copper item by the net clearance. Board in place:

    kpython via_spacing.py board.kicad_pcb
"""
import math
import sys
import pcbnew

MIN_H2H = 0.5
CLR = 0.16                       # mm, a little over the 0.15 netclass clearance
MM, TO = pcbnew.FromMM, pcbnew.ToMM


def main(path):
    b = pcbnew.LoadBoard(path)
    t = b.Tracks()
    items = [t[i].Cast() for i in range(t.size())]
    vias = [v for v in items if v.Type() == pcbnew.PCB_VIA_T]
    segs = [x for x in items if x.Type() == pcbnew.PCB_TRACE_T]
    pads = [p for f in b.GetFootprints() for p in f.Pads()]
    fixed, failed = 0, []

    def clear(shape, net, layer, skip):
        for x in items:
            if x.GetNetCode() == net or id(x) in skip:
                continue
            if x.Type() == pcbnew.PCB_TRACE_T and layer is not None and x.GetLayer() != layer:
                continue
            if x.GetEffectiveShape().Collide(shape, MM(CLR)):
                return False
        for p in pads:
            if p.GetNetCode() == net and net > 0:
                continue
            for ly in ((layer,) if layer is not None else (pcbnew.F_Cu, pcbnew.B_Cu)):
                if p.IsOnLayer(ly) and p.GetEffectiveShape(ly).Collide(shape, MM(CLR)):
                    return False
        return True

    for i, a in enumerate(vias):
        for c in vias[i + 1:]:
            if a.GetNetCode() == c.GetNetCode():
                continue
            d = TO((a.GetPosition() - c.GetPosition()).EuclideanNorm())
            need = (a.GetDrillValue() + c.GetDrillValue()) / 2e6 + MIN_H2H + 0.02
            if d >= need:
                continue
            done = False
            for v, o in ((a, c), (c, a)):
                plane = v.GetNetname() in ('GND', '+3V3')     # locked plane fan-out vias may move with their stub
                if v.IsLocked() and not plane:
                    continue
                p0 = v.GetPosition()
                ends = [(s, 'S') for s in segs if s.GetNetCode() == v.GetNetCode() and s.GetStart() == p0] + \
                       [(s, 'E') for s in segs if s.GetNetCode() == v.GetNetCode() and s.GetEnd() == p0]
                if any(s.IsLocked() for s, _ in ends) and not plane:
                    continue
                skip = {id(v)} | {id(s) for s, _ in ends}
                ox, oy = TO(o.GetPosition().x), TO(o.GetPosition().y)
                base = math.atan2(TO(p0.y) - oy, TO(p0.x) - ox)
                for da in (0, 30, -30, 60, -60, 90, -90):        # straight away first, then sideways
                    ang = base + math.radians(da)
                    # land on the circle of radius `need` around the other via
                    p1 = pcbnew.VECTOR2I(MM(ox + need * math.cos(ang)), MM(oy + need * math.sin(ang)))
                    if TO((p1 - p0).EuclideanNorm()) > 0.4:
                        continue
                    ok = clear(pcbnew.SHAPE_CIRCLE(p1, v.GetWidth(pcbnew.F_Cu) // 2), v.GetNetCode(), None, skip)
                    for s, w in ends:
                        q = s.GetEnd() if w == 'S' else s.GetStart()
                        ok = ok and clear(pcbnew.SHAPE_SEGMENT(p1, q, s.GetWidth()), s.GetNetCode(), s.GetLayer(), skip)
                    ok = ok and all(TO((p1 - x.GetPosition()).EuclideanNorm()) >= need - 0.01 for x in vias
                                    if x is not v and x.GetNetCode() != v.GetNetCode())
                    if ok:
                        v.SetPosition(p1)
                        for s, w in ends:
                            (s.SetStart if w == 'S' else s.SetEnd)(p1)
                        done = True
                        break
                if done:
                    break
            if done:
                fixed += 1
            else:
                failed.append('%s / %s at (%.2f, %.2f)' % (a.GetNetname(), c.GetNetname(),
                              TO(a.GetPosition().x) - 30, TO(a.GetPosition().y) - 30))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(path)
    print('via pairs pushed apart:', fixed, ' not fixed:', len(failed))
    for f in failed:
        print('  ', f)


if __name__ == '__main__':
    main(sys.argv[1])

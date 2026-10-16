"""Plane fan-out (c09 search) only for SMD pads of the net that have no copper on them yet:

    kpython fanout_missing.py board.kicad_pcb +3V3   (new parts placed after c07 / c09)

Same search as c07_gnd_fanout.py (first free spot around the pad, short locked stub, locked via), with the stub
no wider than the pad so it can leave a 0.4 mm-pitch QFN pin. Original c07 notes follow.

GND is not autorouted: both copper layers carry a GND pour. So that every SMD ground pad reaches the bottom
pour even where the top pour is cut up by tracks, each one gets its own via on a short 0.3 mm stub, placed in
the first free spot around the pad. The RP2354B exposed pad gets a 3 x 3 via array (RP2350 hardware design
guide: the exposed pad is the chip's only ground). Everything added here is locked, and the autorouter sees it
as fixed copper.
"""
import math
import sys
import pcbnew

MM = pcbnew.FromMM
OX, OY = 30.0, 30.0
VIA, DRILL = 0.6, 0.3
CLR = 0.2           # via / stub clearance to other copper
STUB = 0.3


def V(x, y):
    return pcbnew.VECTOR2I(int(x), int(y))


def main(path, netname):
    b = pcbnew.LoadBoard(path)
    gnd = b.GetNetsByName()[netname]
    gcode = gnd.GetNetCode()
    layers = (pcbnew.F_Cu, pcbnew.B_Cu)

    pads = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            pads.append((fp, p))
    tl = b.Tracks()
    tracks = [tl[i] for i in range(tl.size())]
    holes = [p for _, p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
    edge = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(edge, False)
    inner = pcbnew.SHAPE_POLY_SET(edge)
    inner.Deflate(MM(VIA / 2 + 0.5), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    placed = []         # (x, y) of new vias

    def via_ok(x, y):
        c = pcbnew.SHAPE_CIRCLE(V(x, y), MM(VIA / 2))
        if not inner.Contains(V(x, y)):
            return False
        for fp, p in pads:
            if p.GetNetCode() == gcode and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                continue
            clr = 0.5 if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else CLR
            for ly in layers:
                if p.IsOnLayer(ly) and p.GetEffectiveShape(ly).Collide(c, MM(clr)):
                    return False
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and p.GetEffectiveHoleShape().Collide(c, MM(clr)):
                return False
        for t in tracks:
            if t.GetNetCode() != gcode and t.GetEffectiveShape().Collide(c, MM(CLR)):
                return False
        for (px, py) in placed:
            if math.hypot(px - x, py - y) < MM(VIA + 0.25):
                return False
        return True

    def stub_ok(pad, x, y):
        s = pcbnew.SHAPE_SEGMENT(pad.GetPosition(), V(x, y), stub_w(pad))
        for fp, p in pads:
            if p.GetNetCode() == gcode or not p.IsOnLayer(pcbnew.F_Cu):
                continue
            if p.GetEffectiveShape(pcbnew.F_Cu).Collide(s, MM(CLR)):
                return False
        for t in tracks:
            if t.GetNetCode() != gcode and t.GetLayer() == pcbnew.F_Cu and t.GetEffectiveShape().Collide(s, MM(CLR)):
                return False
        return True

    def stub_w(pad):
        sz = pad.GetSize()
        return min(MM(STUB), min(sz.x, sz.y))

    def add_via(x, y):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(V(x, y))
        v.SetWidth(MM(VIA))
        v.SetDrill(MM(DRILL))
        v.SetNet(gnd)
        v.SetLocked(True)
        b.Add(v)
        placed.append((x, y))

    ep = None
    n_ok, missing = 0, []
    for fp, p in pads:
        if p.GetNetCode() != gcode or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or not p.IsOnLayer(pcbnew.F_Cu):
            continue
        if p is ep:
            continue
        if any(t.GetNetCode() == gcode and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()) if t.Type() == pcbnew.PCB_TRACE_T
                                           else p.HitTest(t.GetPosition())) for t in tracks):
            continue            # already has copper on it (fan-out stub or route)
        pc = p.GetPosition()
        bb = p.GetBoundingBox()
        r0 = max(bb.GetWidth(), bb.GetHeight()) / 2
        done = False
        for extra in (0.55, 0.8, 1.1, 1.5, 2.0, 2.6):
            r = r0 + MM(extra)
            for k in range(24):
                a = 2 * math.pi * k / 24
                x, y = pc.x + r * math.cos(a), pc.y + r * math.sin(a)
                if via_ok(x, y) and stub_ok(p, x, y):
                    add_via(x, y)
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(pc)
                    t.SetEnd(V(x, y))
                    t.SetWidth(stub_w(p))
                    t.SetLayer(pcbnew.F_Cu)
                    t.SetNet(gnd)
                    t.SetLocked(True)
                    b.Add(t)
                    tracks.append(t)
                    done = True
                    break
            if done:
                break
        if done:
            n_ok += 1
        else:
            missing.append('%s.%s' % (fp.GetReference(), p.GetNumber()))
    b.Save(path)
    print(netname, 'pads with a via:', n_ok, ' without:', len(missing), ' '.join(missing))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

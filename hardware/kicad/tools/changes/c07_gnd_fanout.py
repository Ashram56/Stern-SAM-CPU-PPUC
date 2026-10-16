"""Layout step 2: ground vias before autorouting.

    kpython c07_gnd_fanout.py ../../sam_cpu/sam_cpu.kicad_pcb

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


def main(path):
    b = pcbnew.LoadBoard(path)
    gnd = b.GetNetsByName()['GND']
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
        s = pcbnew.SHAPE_SEGMENT(pad.GetPosition(), V(x, y), MM(STUB))
        for fp, p in pads:
            if p.GetNetCode() == gcode or not p.IsOnLayer(pcbnew.F_Cu):
                continue
            if p.GetEffectiveShape(pcbnew.F_Cu).Collide(s, MM(CLR)):
                return False
        for t in tracks:
            if t.GetNetCode() != gcode and t.GetLayer() == pcbnew.F_Cu and t.GetEffectiveShape().Collide(s, MM(CLR)):
                return False
        return True

    def add_via(x, y):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(V(x, y))
        v.SetWidth(MM(VIA))
        v.SetDrill(MM(DRILL))
        v.SetNet(gnd)
        v.SetLocked(True)
        b.Add(v)
        placed.append((x, y))

    # RP2354B exposed pad: 3 x 3 array on the 1.13 mm grid of its paste windows
    u4 = b.FindFootprintByReference('U4')
    ep = [p for p in u4.Pads() if p.GetNumber() == '81'][0]
    c = ep.GetPosition()
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            add_via(c.x + i * MM(1.13), c.y + j * MM(1.13))

    n_ok, missing = 0, []
    for fp, p in pads:
        if p.GetNetCode() != gcode or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or not p.IsOnLayer(pcbnew.F_Cu):
            continue
        if p is ep:
            continue
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
                    t.SetWidth(MM(STUB))
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
    print('GND pads with a via:', n_ok, ' without:', len(missing), ' '.join(missing))


if __name__ == '__main__':
    main(sys.argv[1])

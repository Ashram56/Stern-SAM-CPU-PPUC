"""Layout step 2: import the Freerouting session, stitch the two GND pours, fill zones.

    kpython c06_route_import.py ../../sam_cpu/sam_cpu.kicad_pcb routed.ses

The session comes from Freerouting 2.5 run headless on the DSN KiCad exports
(ExportSpecctraDSN), with GND exported as a plane on both layers.
Stitching vias go on a 5 mm grid wherever both GND pours have room for them.
"""
import math
import sys
import pcbnew

MM = pcbnew.FromMM
PITCH = 5.0
VIA, DRILL = 0.6, 0.3


def fill(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())


def gnd_fills(b):
    out = {}
    for z in b.Zones():
        if z.GetNetname() == 'GND':
            out[z.GetLayer()] = z.GetFilledPolysList(z.GetLayer())
    return out


def fits(polys, x, y, r):
    for layer, poly in polys.items():
        for k in range(12):
            a = 2 * math.pi * k / 12
            p = pcbnew.VECTOR2I(int(x + r * math.cos(a)), int(y + r * math.sin(a)))
            if not poly.Contains(p):
                return False
        if not poly.Contains(pcbnew.VECTOR2I(int(x), int(y))):
            return False
    return True


def main(path, ses):
    b = pcbnew.LoadBoard(path)
    if ses != '-':
        if not pcbnew.ImportSpecctraSES(b, ses):
            raise SystemExit('SES import failed')
    fill(b)
    polys = gnd_fills(b)
    bb = b.GetBoardEdgesBoundingBox()
    gnd = b.GetNetsByName()['GND']
    n = 0
    y = bb.GetTop() + MM(PITCH / 2)
    while y < bb.GetBottom():
        x = bb.GetLeft() + MM(PITCH / 2)
        while x < bb.GetRight():
            # the via must sit wholly inside both fills, 0.3 mm in from their edges
            if fits(polys, x, y, MM(VIA / 2 + 0.3)):
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
                v.SetWidth(MM(VIA))
                v.SetDrill(MM(DRILL))
                v.SetNet(gnd)
                b.Add(v)
                n += 1
            x += MM(PITCH)
        y += MM(PITCH)
    fill(b)
    b.Save(path)
    print('stitching vias', n)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

"""Layout step 3: go to 4 copper layers (F.Cu signal / In1.Cu GND plane / In2.Cu +3V3 plane / B.Cu signal).

    kpython c08_four_layers.py ../../sam_cpu/sam_cpu.kicad_pcb

Five 2-layer autoroutes stalled with 39-170 open connections, so the board gets solid inner planes
(RP2350 hardware design guide: unbroken ground under the chip). The outer GND pours stay and are filled
after routing; the ground vias from c07 now land on the In1 plane.
"""
import sys
import pcbnew

MM = pcbnew.FromMM


def zone(b, layer, net, name, prio):
    outline = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline, False)
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(b.GetNetsByName()[net])
    z.SetZoneName(name)
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(MM(0.25))
    z.SetMinThickness(MM(0.2))
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.4))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = outline.Outline(0)
    # keep planes 0.5 mm in from the board edge
    z.Outline().AddOutline(o)
    b.Add(z)


def main(path):
    b = pcbnew.LoadBoard(path)
    b.SetCopperLayerCount(4)
    b.SetLayerName(pcbnew.In1_Cu, 'In1.Cu')
    b.SetLayerName(pcbnew.In2_Cu, 'In2.Cu')
    b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    zone(b, pcbnew.In1_Cu, 'GND', 'GND_PLANE', 0)
    zone(b, pcbnew.In2_Cu, '+3V3', '3V3_PLANE', 0)
    b.Save(path)
    print('layers', b.GetCopperLayerCount())


if __name__ == '__main__':
    main(sys.argv[1])

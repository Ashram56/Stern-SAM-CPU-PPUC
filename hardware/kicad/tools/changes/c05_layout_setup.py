"""Layout step 1: net classes, design rules, hand-routed RP2354B regulator, ground zones.

Run with KiCad 10's Python on the placed board (in place):
    kpython c05_layout_setup.py ../../sam_cpu/sam_cpu.kicad_pcb

- Rules for JLCPCB 2-layer, 1 oz: 0.2 mm tracks, 0.15 mm clearance, 0.6 / 0.3 mm vias.
- Net classes: Power (0.25 mm logic rails, a few hundred mA at most), Power_5V (0.5 mm branches),
  Power_HI (0.8 mm +12 V and the input paths), Speaker (1.0 mm amplifier outputs).
- +5 V trunk routed by hand, 1.5 mm, from the power-mux output (D4, Q1, Q2, TP1) down the free strip
  under the Pi to J21 pins 2 / 4, which feed the Pi (up to 3 A).
- RP2354B core regulator routed by hand on the top layer, as the RP2350 hardware design guide asks
  (short LX loop, VIN cap on VREG_VIN, PGND into the exposed pad, FB sensed on the 1.1 V rail), locked.
- GND zones on both layers over the whole outline (filled after routing).
"""
import sys
import pcbnew

OX, OY = 30.0, 30.0
MM = pcbnew.FromMM

POWER = ['+3V3', '+4V5', '+1V1', 'VREF', 'Net-(J19-VBUS-PadA4)', 'Net-(U22-AVDD)']
POWER_5V = ['+5V']
POWER_HI = ['+12V', 'Net-(D1-A1)', 'Net-(J11-Pin_1)', 'Net-(JP1-A)', 'Net-(JP1-B)',
            'Net-(J23-Pin_1)']
SPEAKER = ['Net-(J10-Pin_%d)' % i for i in range(1, 5)] + ['Net-(J24-Pin_%d)' % i for i in range(1, 5)]

# (net, width mm, [points in board mm]) on F.Cu
REG_TRACKS = [
    ('Net-(U4-VREG_LX)', 0.25, [(46.35, 21.05), (46.35, 19.3)]),            # pin 63 -> L1.1
    ('+3V3', 0.2, [(45.95, 21.05), (45.95, 20.25), (44.55, 20.25), (44.3, 19.9)]),  # pin 64 VREG_VIN -> C12.1
    ('+1V1', 0.6, [(46.7, 17.9), (49.45, 17.6)]),                           # L1.2 -> C24.1
    ('GND', 0.25, [(46.75, 21.05), (46.75, 22.4), (44.7, 24.45)]),          # pin 62 PGND -> EP
    ('+1V1', 0.2, [(45.55, 21.05), (45.55, 21.9), (39.6, 21.9), (39.6, 25.8), (38.4, 25.8)]),  # FB -> DVDD pin 10
    ('Net-(U4-VREG_AVDD)', 0.25, [(47.15, 21.05), (47.15, 20.45), (53.75, 20.45), (53.75, 19.42)]),
    ('Net-(U4-VREG_AVDD)', 0.25, [(53.75, 19.42), (52.8, 18.45), (51.75, 17.5)]),  # R8.2 -> C11.1
]

# +5 V trunk to the Pi header (F.Cu)
TRUNK_5V = [
    ('+5V', 1.0, [(63.55, 75.44), (63.55, 76.6), (76.09, 76.6), (76.09, 74.95)]),   # D4.2, Q1.2, Q2.2, TP1
    ('+5V', 1.5, [(76.09, 76.6), (76.5, 76.6), (76.5, 95.0), (74.8, 96.7), (74.8, 118.0),
                  (79.0, 122.2), (79.0, 140.5), (62.3, 140.5)]),
    ('+5V', 1.2, [(62.3, 140.5), (62.3, 149.77), (64.52, 149.77), (67.06, 149.77)]),  # round MH9, J21.2 -> J21.4
]


def pt(x, y):
    return pcbnew.VECTOR2I(MM(x + OX), MM(y + OY))


def add_class(ns, name, width, clearance, via=0.6, drill=0.3):
    nc = pcbnew.NETCLASS(name)
    nc.SetTrackWidth(MM(width))
    nc.SetClearance(MM(clearance))
    nc.SetViaDiameter(MM(via))
    nc.SetViaDrill(MM(drill))
    ns.SetNetclass(name, nc)


def main(path):
    b = pcbnew.LoadBoard(path)
    ds = b.GetDesignSettings()
    ds.m_TrackMinWidth = MM(0.15)
    ds.m_MinClearance = MM(0.15)
    ds.m_ViasMinSize = MM(0.6)
    ds.m_CopperEdgeClearance = MM(0.3)
    ns = ds.m_NetSettings
    dc = ns.GetDefaultNetclass()
    dc.SetTrackWidth(MM(0.2))
    dc.SetClearance(MM(0.15))
    dc.SetViaDiameter(MM(0.6))
    dc.SetViaDrill(MM(0.3))
    add_class(ns, 'Power', 0.25, 0.15)
    add_class(ns, 'Power_5V', 0.5, 0.2)
    add_class(ns, 'Power_HI', 0.8, 0.25, 0.8, 0.4)
    add_class(ns, 'Speaker', 1.0, 0.3, 0.8, 0.4)
    ns.ClearNetclassPatternAssignments()
    for cls, nets in (('Power', POWER), ('Power_5V', POWER_5V), ('Power_HI', POWER_HI), ('Speaker', SPEAKER)):
        for n in nets:
            ns.SetNetclassPatternAssignment(n, cls)
    ns.RecomputeEffectiveNetclasses() if hasattr(ns, 'RecomputeEffectiveNetclasses') else None
    b.SynchronizeNetsAndNetClasses(True)

    nets = b.GetNetsByName()
    for net, w, pts in REG_TRACKS + TRUNK_5V:
        ni = nets[net]
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pt(*a))
            t.SetEnd(pt(*c))
            t.SetWidth(MM(w))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(ni)
            t.SetLocked(True)
            b.Add(t)

    # GND zones on both layers, following the board outline
    outline = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline, False)
    gnd = nets['GND']
    for layer, prio in ((pcbnew.F_Cu, 0), (pcbnew.B_Cu, 0)):
        z = pcbnew.ZONE(b)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetZoneName('GND_' + ('TOP' if layer == pcbnew.F_Cu else 'BOT'))
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(MM(0.25))
        z.SetMinThickness(MM(0.2))
        z.SetThermalReliefGap(MM(0.3))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.Outline().AddOutline(outline.Outline(0))
        b.Add(z)

    b.Save(path)
    print('tracks added', sum(len(p) - 1 for _, _, p in REG_TRACKS + TRUNK_5V))


if __name__ == '__main__':
    main(sys.argv[1])

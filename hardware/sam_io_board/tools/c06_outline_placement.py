"""Change 06 (2026-10-07): Vincent chose the smaller Opto_16 size and asked for the bus to be routed
on two layers. Shrinks the board to 100 x 70 mm (Opto_16 is 99.7 x 67.3; the address DIP SW3 needs
the extra 2.7 mm), moves the bottom mounting holes, the logo and the board name up, and places the
SAM bus parts for routing: both buffers turned so their 3.3 V side faces the RP2040 and their 5 V
side faces J9. Existing parts and their routing do not move.
Run with KiCad 10's Python: c06_outline_placement.py <board.kicad_pcb> [place]
("place" only moves the SAM bus parts, for a board that already had the outline change)"""
import os, sys
import pcbnew

MM = pcbnew.FromMM
X0, Y0, X1, Y1 = 75.0, 39.0, 175.0, 109.0
PLACE = {
    # J9 on the left edge; U7 turned so its 3.3 V pins face down towards the RP2040's GPIO3-10 and its
    # 5 V pins face up towards RN1 / RN2; U8 turned so its 3.3 V pins face the RP2040's GPIO11-15
    # coming down from the right (c08_bus_fanout.py routes those lines).
    'J9': (80.5, 68.0, 0),
    'RN1': (88.5, 70.5, 0), 'RN2': (88.5, 75.0, 0),
    'U7': (98.5, 76.0, 90),
    'C30': (93.2, 79.4, 90), 'C31': (93.2, 72.6, 90),
    'R27': (91.6, 96.2, 0), 'R28': (93.6, 86.0, 90),
    'RN3': (88.5, 87.0, 0), 'R29': (88.5, 90.5, 0),
    'U8': (97.0, 94.6, 180),
    'C32': (91.6, 98.4, 0), 'C33': (86.0, 99.0, 0),
    'Q1': (104.3, 100.8, 0), 'R30': (104.3, 103.4, 0),
    'TP3': (87.0, 102.5, 0), 'TP4': (90.5, 102.5, 0), 'TP5': (94.0, 102.5, 0), 'TP6': (97.5, 102.5, 0),
}
b = pcbnew.LoadBoard(sys.argv[1])
ONLY_PLACE = sys.argv[2:] == ['place']
for f in b.GetFootprints():
    r = f.GetReference()
    if r in PLACE:
        x, y, rot = PLACE[r]
        f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); f.SetOrientationDegrees(rot)
    elif r == 'REF**' and not ONLY_PLACE and f.GetY() > MM(120):       # bottom mounting holes: 5 mm from the new edge
        f.SetPosition(pcbnew.VECTOR2I(f.GetX(), MM(Y1 - 5)))
D = b.Drawings()
for i in range(0 if ONLY_PLACE else len(D)):
    d = D[i].Cast()
    if d.GetLayerName() == 'Edge.Cuts':
        d.SetStart(pcbnew.VECTOR2I(MM(X0), MM(Y0))); d.SetEnd(pcbnew.VECTOR2I(MM(X1), MM(Y1)))
    elif d.GetLayerName() == 'F.Silkscreen' and d.GetY() > MM(95) and d.GetX() < MM(120):  # logo, name
        dy = MM(-8) if d.GetClass() != 'PCB_TEXT' else MM(104 - 135.255)
        d.Move(pcbnew.VECTOR2I(MM(48), dy))
for z in ([] if ONLY_PLACE else b.Zones()):
    if z.GetNetname() == 'GND':
        o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
        for x, y in ((X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)):
            o.Append(MM(x), MM(y))
b.Save(sys.argv[1])
print('done'); sys.stdout.flush(); os._exit(0)

# Original SAM CPU/Sound board: connector and mounting-hole positions

Mechanical reference for laying out the replacement board so it drops into
the original position in the backbox, reuses the original mounting screws,
and lets the existing harness plugs reach their headers.

Source: the component-layout page of the Stern manual
(`docs/reference/Stern_SAM_Manual-CPU_Sound_Board_Schematic.pdf`, page 11,
board 520-5246-00 **Rev G**). That page is a vector drawing, so positions
were read from its path data, not from a scan. `tools/sam_cpu_mechanical.py`
regenerates every file here.

| File | What it is |
|---|---|
| `sam_cpu_520-5246-00_positions.csv` | Every pin, connector body and hole, in mm |
| `sam_cpu_520-5246-00_outline.dxf` | Board edge, holes, connector bodies, pins (layers EDGE, HOLES, CONN, PINS) for import into KiCad |
| `sam_cpu_520-5246-00_annotated.png` | The layout page with the computed coordinates marked |

## Coordinate system

Millimetres, origin at the **top-left corner of the board**, X to the right,
Y down (KiCad convention), seen from the component side with the board as it
hangs in the backbox: J11 power at the top, switch connectors on the left
and bottom edges, USB/serial/display on the right. The DXF uses the same
origin with Y negated (DXF Y points up); import it with the origin at the
top-left corner.

## Scale and confidence

The drawing is uniformly scaled (round holes are round). The scale comes
from connector bodies whose length is fixed by their standard, and six
independent ones agree to within 0.05 %: J1, J2, J3 (n x 3.96 mm KK-396
bodies), J9 (2x10 box header, 33.02 mm), J5 (2x7 box header, 25.40 mm) and
J7 (2x10 pin field, 25.40 mm).

The result lands on round inch values, which is a good sign the scale is
right: the board comes out at **219.06 x 231.76 mm = 8.625 x 9.125 in**,
J9 pins sit at X = 10.16 / 12.70 mm (0.4 / 0.5 in), and every switch
connector pin falls on a 0.025 in grid.

| Quantity | Confidence |
|---|---|
| Board size, hole centres, pin positions **along** each connector | High, about ±0.3 mm (assuming your board matches Rev G) |
| Pin row **across** a KK-396 connector (X of J12/J6/J13, Y of J1/J2/J3) | Medium, ±0.8 mm: the drawing shows the housing, not the pins. I took the centre of the housing without its friction-ramp strip; the row is probably exactly 10.16 mm (0.4 in) from the board edge |
| Hole diameters | Low: the drawing shows the pad/keep-out shapes, not necessarily the drill |

## Mounting holes

Four keyhole slots in the corners plus four round holes. The keyholes open
**upward**: the board is hung on screws through the large circle and drops
down, so the screw shank ends at the top of the slot. That top-of-slot
centre is the screw position to match.

| Hole | Type | Screw X | Screw Y | Notes |
|---|---|---|---|---|
| MH6 | keyhole, top-left | 8.24 | 6.27 | clearance circle centre (8.24, 13.69), Ø10.4; slot 4.4 wide |
| MH1 | keyhole, top-right | 210.16 | 6.27 | circle centre (210.16, 13.69) |
| MH3 | keyhole, bottom-left | 8.24 | 215.17 | circle centre (8.24, 222.59) |
| MH2 | keyhole, bottom-right | 210.16 | 215.17 | circle centre (210.16, 222.59) |
| MH5 | round, top centre | 109.20 | 6.98 | Ø6.3 circle in a 10.2 mm square pad |
| MH4 | round, bottom centre | 97.14 | 222.86 | same |
| MH7 | round, left middle | 8.25 | 116.84 | same |
| MH8 | round, right middle | 210.17 | 116.84 | same |

Keyhole screw spacing: 201.92 mm horizontally, 208.90 mm vertically.

## Left edge (switch matrix and bus)

Pin 1 is at the **bottom** of each connector, numbering upward. Pitch 3.96 mm.

| Conn | Function | Pins | Pin X | Pin 1 Y | Last pin Y | Housing (x0, y0)-(x1, y1) |
|---|---|---|---|---|---|---|
| J9 | Bus to I/O board, 2x10 IDC | 20 | 12.70 odd / 10.16 even | 52.07 (pin 1, 2) | 29.21 (pin 19, 20) | (6.98, 24.13)-(15.87, 57.15) |
| J12 | Upper switch return (columns 9-16) | 10 | 10.03 | 103.51 | 67.87 | (6.73, 65.87)-(14.85, 105.49) |
| J6 | Lower switch return (columns 1-8) | 10 | 10.03 | 163.83 | 128.19 | (6.73, 126.19)-(14.85, 165.81) |
| J13 | Dedicated switches (SW D17-24) | 10 | 10.03 | 208.28 | 172.64 | (6.73, 170.63)-(14.85, 210.26) |

J9 pin 1 is the inner (board-centre side) column, bottom row.

## Bottom edge (dedicated switches and strobes)

Pin 1 is at the **right** end of each connector. Pitch 3.96 mm. Pin row
Y = 221.73 for all three (10.03 mm above the bottom edge).

| Conn | Function | Pins | Pin 1 X | Last pin X | Housing (x0, y0)-(x1, y1) |
|---|---|---|---|---|---|
| J3 | Upper dedicated switch in | 10 | 85.09 | 49.45 | (47.45, 216.91)-(87.07, 225.03) |
| J2 | Lower dedicated switch in | 12 | 151.77 | 108.21 | (106.18, 216.91)-(153.75, 225.03) |
| J1 | Switch drive (row strobes) | 9 | 194.94 | 163.26 | (161.26, 216.91)-(196.92, 225.03) |

## Top and right edges

| Conn | Function | Position |
|---|---|---|
| J11 | Power in, KK-396 1x6, pin 1 at left | pins Y 11.18, X 58.41 to 78.21 |
| J10 | Audio out, KK-396 1x4, pin 1 at left | pins Y 8.76, X 156.19 to 168.07 |
| J15 | USB-B, opens at the right edge | housing (204.22, 60.41)-(219.06, 75.67) |
| J7 | Processor JTAG 2x10 | pin 1 (212.08, 105.40), bottom-right |
| J8 | Xilinx JTAG | outline (205.09, 123.82)-(212.71, 139.06) |
| J5 | DMD display 2x7 IDC | pin 1 (211.44, 164.46), bottom-right; pins 13/14 at Y 149.22 |
| J14 | Serial header | outline (186.17, 157.03)-(202.93, 170.64) |
| J4 | DB9, overhangs the right edge by 6.3 mm | outline (206.78, 173.18)-(225.32, 204.37) |

Every individual pin is in the CSV.

## Finding for the KiCad schematic

The switch connectors J1, J2, J3, J6, J12 and J13 are **KK-396 (3.96 mm,
0.156 in)** headers on the original board, not 2.54 mm. Their drawn bodies
are exactly n x 3.96 mm long, and J12 is 1.2x the length of the 2x10 box
header J9, which only works at 3.96 mm. The existing harness plugs are
0.156 in housings, so the draft 0.1 schematic's
`Molex_KK-254_AE-6410-xxA` footprints for those six connectors need to
become `Molex_KK-396_A-41791-00xx` (J10 and J11 already use KK-396).

## What to measure on the real board

One ruler session confirms everything above:

1. Board width x height. Expected 219.1 x 231.8 mm (8 5/8 x 9 1/8 in).
   If this matches, the scale is confirmed.
2. Board revision printed near the Stern copyright (this data is Rev G).
3. Pin pitch on J12 or J3: pin 1 to pin 10 should be 35.6 mm (3.96 mm pitch).
4. Left edge to the J12 pin centres, and bottom edge to the J1/J2/J3 pin
   centres: expected about 10.0 to 10.2 mm. This settles the medium-confidence
   row position.
5. Screw positions: board corner to the top of each keyhole slot (expected
   8.2 mm in, 6.3 mm down), and what sits in the round holes MH4, MH5, MH7,
   MH8 (screw, plastic standoff or nothing) with its diameter.
6. Optionally, one straight-on photo of the board with a ruler along the
   left and bottom edges, as a record.

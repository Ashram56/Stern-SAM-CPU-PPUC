"""Change 08 (2026-10-07), after c06 / c07: routes the RP2040 side of the SAM bus by hand.
The RP2040 (U3) numbers its pins anticlockwise and so do both buffers, so a bus that runs from one
to the other in the same bit order cannot be drawn on one layer: the order has to flip. Here every
line flips through two vias: the lines leave U3 on F.Cu as in IO_16_8_1 (its GPIO3-18 fanout is
reused near U3), spread to the 0.65 mm pin pitch, and each one drops a via under its own buffer pin
and reaches it on B.Cu, crossing under the lines that are still running on F.Cu.
  D0-D7 (GPIO3-10)  -> U7 pins 3-10, U7 above the lines, B.Cu verticals
  A0-A3, IOSTB      -> U8 pins 2-6, U8 left of the lines, B.Cu horizontals
  DIR (GPIO16)      -> U7 pin 2 (via B.Cu), OE_N (GPIO17) -> U8 pin 1, NBRESET_DRV (GPIO18) -> Q1 gate
The rest (5 V side, J9, pull-ups, power) is routed after this.
Usage: c08_bus_fanout.py <board.kicad_pcb>"""
import re, sys, uuid
import sx

W, VIA, DRILL = 0.2, 0.5, 0.3
P = 0.65                                   # buffer pin pitch
segs, vias = [], []


def path(net, pts, layer='F.Cu'):
    for a, b in zip(pts, pts[1:]):
        segs.append((net, layer, a, b))


def via(net, x, y):
    vias.append((net, x, y))


# ---- D0-D7 to U7 (rot 90 at 98.5, 76.0: pins 3-10 on its lower row at y 78.8625, x 96.225 + 0.65 i)
U7_ROW = 78.8625
WROW = (80.1, 80.7)                        # vias next to the pins, two staggered rows
xs = [96.225 + P * i for i in range(8)]
ys = [81.296 + P * i for i in range(8)]    # the lines after spreading to the pin pitch
# from U3 (pins 5-9, 11-13 at x 113.9105): D0-D4 straight out, D5-D7 under C13 as in IO_16_8_1,
# then each one steps down to its row, the lowest line first, 45 degree steps 0.65 mm apart
start = {0: [(113.9105, 81.296)], 1: [(113.9105, 81.696)], 2: [(113.9105, 82.096)],
         3: [(113.9105, 82.496)], 4: [(113.9105, 82.896)],
         5: [(113.9105, 83.696), (112.646, 83.696), (112.039, 84.303)],
         6: [(113.9105, 84.096), (112.82694, 84.096), (112.21994, 84.703)],
         7: [(113.9105, 84.496), (112.992626, 84.496), (112.385626, 85.103)]}
xj, prev_y = 107.0, None
for i in range(7, -1, -1):
    y0 = start[i][-1][1]
    if prev_y is not None:
        xj = xj + (prev_y - y0) - P * 2 ** 0.5
    d = ys[i] - y0
    pts = list(start[i])
    if d > 1e-6:
        pts += [(xj, y0), (xj - d, ys[i])]
    pts.append((xs[i], ys[i]))
    net = 'BUS_D%d' % i
    path(net, pts)
    via(net, xs[i], ys[i])
    wy = WROW[i % 2]
    path(net, [(xs[i], ys[i]), (xs[i], wy)], 'B.Cu')
    via(net, xs[i], wy)
    path(net, [(xs[i], wy), (xs[i], U7_ROW)])
    prev_y = y0
# U7 pin 1 (VCCA) and 2 (DIR) sit left of D0, 11 and 12 (GND) right of D7
path('GND', [(101.425, U7_ROW), (102.075, U7_ROW), (102.075, WROW[0])])
via('GND', 102.075, WROW[0])

# ---- A0-A3, IOSTB to U8 (rot 180 at 97.0, 94.6: pins 2-6 on its right column at x 99.8625)
U8_COL = 99.8625
WCOL = (101.15, 101.75)
ty = [94.6 + 2.275 - P * i for i in range(5)]          # pin 2 (A0) lowest ... pin 6 (IOSTB)
X0 = 97.0 + 5.35
vx = [X0 + P * i for i in range(5)]
# from U3 as in IO_16_8_1: A0 (pin 14) and A1-IOSTB (pins 15-18) leave down and left, then run
# south-west at 45 degrees; each one turns south onto its own column and stops level with its pin
astart = [[(113.9105, 84.896), (113.158312, 84.896), (112.551311, 85.503), (110.204, 85.503)],
          [(114.748, 85.7335), (112.958, 85.7335), (112.7885, 85.903), (110.369686, 85.903)],
          [(115.148, 85.7335), (115.148, 86.274), (114.935, 86.487), (114.046, 86.487),
           (114.027, 86.468), (110.763, 86.468)],
          [(115.548, 85.7335), (115.548, 86.439686), (115.100686, 86.887), (113.303, 86.887),
           (113.284, 86.868), (110.928686, 86.868)],
          [(115.948, 85.7335), (115.948, 86.605372), (115.266371, 87.287), (111.075372, 87.287)]]
anames = ['BUS_A0', 'BUS_A1', 'BUS_A2', 'BUS_A3', 'BUS_IOSTB']
for i, net in enumerate(anames):
    pts = list(astart[i])
    s = pts[-1][0] + pts[-1][1]                          # the 45 degree line x + y = s
    pts += [(vx[i], s - vx[i]), (vx[i], ty[i])]
    path(net, pts)
    via(net, vx[i], ty[i])
    wx = WCOL[i % 2]
    path(net, [(vx[i], ty[i]), (wx, ty[i])], 'B.Cu')
    via(net, wx, ty[i])
    path(net, [(wx, ty[i]), (U8_COL, ty[i])])
# U8 pins 7-10 (unused inputs and GND) to one via
path('GND', [(U8_COL, 93.625), (U8_COL, 91.675)])
path('GND', [(U8_COL, 92.325), (101.15, 92.325)])
via('GND', 101.15, 92.325)

# ---- DIR, OE_N, NBRESET_DRV: IO_16_8_1's GPIO16-18 fanout (down the right of U3 on B.Cu, back on
# F.Cu at y 95.1-95.9) is reused up to x 108.5
path('BUS_DIR', [(119.548, 85.7335), (119.548, 86.265975), (119.769025, 86.487), (122.174, 86.487),
                 (122.555, 86.106)])
via('BUS_DIR', 122.555, 86.106)
path('BUS_DIR', [(122.555, 86.106), (121.52, 87.141), (121.52, 93.491), (121.285, 93.726)], 'B.Cu')
via('BUS_DIR', 121.285, 93.726)
path('BUS_DIR', [(121.285, 93.726), (121.158, 93.853), (120.015, 93.853), (118.783, 95.085),
                 (108.4, 95.085), (107.9, 94.585)])
via('BUS_DIR', 107.9, 94.585)
# DIR crosses under everything on B.Cu to U7 pin 2
path('BUS_DIR', [(107.9, 94.585), (107.9, 88.5), (95.575, 88.5), (95.575, WROW[1])], 'B.Cu')
via('BUS_DIR', 95.575, WROW[1])
path('BUS_DIR', [(95.575, WROW[1]), (95.575, U7_ROW)])

path('BUS_OE_N', [(119.948, 85.7335), (121.2765, 85.7335), (121.285, 85.725)])
via('BUS_OE_N', 121.285, 85.725)
path('BUS_OE_N', [(121.285, 85.725), (121.12, 85.89), (121.12, 93.070756), (120.523, 93.667756),
                  (120.523, 94.742)], 'B.Cu')
via('BUS_OE_N', 120.523, 94.742)
path('BUS_OE_N', [(120.523, 94.742), (119.78, 95.485), (107.530315, 95.485),
                  (107.530315 - 2.04, 97.525), (U8_COL, 97.525)])

path('NBRESET_DRV', [(120.7855, 84.896), (121.298942, 84.896), (121.866942, 85.464), (123.31, 85.464),
                     (123.698, 85.852)])
via('NBRESET_DRV', 123.698, 85.852)
path('NBRESET_DRV', [(123.698, 85.852), (121.92, 87.63), (121.92, 94.919), (121.485, 95.354)], 'B.Cu')
via('NBRESET_DRV', 121.485, 95.354)
path('NBRESET_DRV', [(121.485, 95.354), (120.954, 95.885), (107.696, 95.885),
                     (107.696 - 3.965, 95.885 + 3.965), (103.3625, 99.85)])

# GND stitching vias in the way (no track on them; the GND pour stays tied by the others)
REMOVE_VIAS = [(108.204, 84.582)]

t = open(sys.argv[1]).read()
for h, a, b in sorted(sx.items(t), key=lambda x: -x[1]):
    if h == 'via' and any(abs(sx.at(t[a:b])[0] - x) < 1e-3 and abs(sx.at(t[a:b])[1] - y) < 1e-3
                          for x, y in REMOVE_VIAS):
        assert '(net "GND")' in t[a:b]
        while t[a - 1] in '\t':
            a -= 1
        t = t[:a - 1] + t[b:]
f = lambda v: ('%.6f' % v).rstrip('0').rstrip('.')
out = []
for net, layer, (x1, y1), (x2, y2) in segs:
    if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
        continue
    out.append('\t(segment\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(width %s)\n\t\t(layer "%s")\n'
               '\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n' % (f(x1), f(y1), f(x2), f(y2), f(W), layer, net,
                                                         uuid.uuid4()))
for net, x, y in vias:
    out.append('\t(via\n\t\t(at %s %s)\n\t\t(size %s)\n\t\t(drill %s)\n\t\t(layers "F.Cu" "B.Cu")\n'
               '\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n' % (f(x), f(y), f(VIA), f(DRILL), net, uuid.uuid4()))
k = t.index('\n\t(segment') + 1
t = t[:k] + ''.join(out) + t[k:]
open(sys.argv[1], 'w').write(t)
print(len(out), 'tracks and vias added')

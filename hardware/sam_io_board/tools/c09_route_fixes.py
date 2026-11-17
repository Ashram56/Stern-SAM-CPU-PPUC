"""Change 09 (2026-10-07), after the Freerouting passes (route_mkdsn.py / route_import.py): the few
things the router left.
- +3V3 to the pull-ups and U7 VCCA: the router joined C30, U7 pin 1, R27 and R30 to each other but not
  to the RP2040's 3.3 V; one B.Cu track from the 3.3 V ring around U3 down to R30 does it.
- C31 (U7 5 V decoupling) had no room for a GND via next to it: a via in its GND pad.
- Q1's source pad had no room for pour spokes: a short track to a GND via and a solid pour connection.
- The F.Cu GND pour under U8 / Q1 was cut off by the new tracks: one via ties it to B.Cu.
- One BUS_OE_N piece under U8 the router had necked to 0.15 mm: back at 0.2 mm it came 3 um too
  close to a via of the U8 pin 18 line, so that via moves up 0.04 mm.
Usage: c09_route_fixes.py <board.kicad_pcb>"""
import sys, uuid

t = open(sys.argv[1]).read()
n = t.count('96.43 96.42)')
assert n == 3, n
t = t.replace('96.43 96.42)', '96.43 96.38)')

out = []


def seg(net, layer, pts):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        out.append('\t(segment\n\t\t(start %g %g)\n\t\t(end %g %g)\n\t\t(width 0.2)\n\t\t(layer "%s")\n'
                   '\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n' % (x1, y1, x2, y2, layer, net, uuid.uuid4()))


def via(net, x, y):
    out.append('\t(via\n\t\t(at %g %g)\n\t\t(size 0.5)\n\t\t(drill 0.3)\n\t\t(layers "F.Cu" "B.Cu")\n'
               '\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n' % (x, y, net, uuid.uuid4()))


seg('+3V3', 'B.Cu', [(112.395, 85.3), (109.0, 88.7), (108.6, 89.1), (108.6, 95.4), (104.0, 100.0),
                     (104.0, 101.9), (102.5, 103.4)])
via('+3V3', 102.5, 103.4)
seg('+3V3', 'F.Cu', [(102.5, 103.4), (103.475, 103.4)])
via('GND', 93.2, 71.9)
seg('GND', 'F.Cu', [(103.3625, 101.75), (104.4, 102.35)])
via('GND', 104.4, 102.35)
via('GND', 96.4, 99.0)
# Q1 source: solid pour connection (its thermal spokes are blocked by the tracks around it)
q = t.index('(property "Reference" "Q1"')
q = t.index('(pad "2"', q)
q = t.index('(net "GND")', q)
t = t[:q] + '(zone_connect 2)\n\t\t\t' + t[q:]
k = t.index('\n\t(segment') + 1
t = t[:k] + ''.join(out) + t[k:]
open(sys.argv[1], 'w').write(t)
print(len(out), 'tracks and vias added')

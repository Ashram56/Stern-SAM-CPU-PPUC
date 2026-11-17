"""Routing step 1: from KiCad's Specctra DSN, make the Freerouting input. Every existing track and
via is protected, so only the new SAM bus connections get routed. GND stays with the pour: its net is
dropped, its tracks and vias become keepouts (vias as zero-length paths, which Freerouting honours),
and the pour itself is left out (a full-board plane on both layers would block everything).
The router keeps <clearance> um (default 200) between copper of different nets; 250 on the first
pass keeps it off the existing tracks' rounded corners, 210 on the second pass lets it into tight spots.
Usage: route_mkdsn.py <in.dsn> <out.dsn> [clearance]"""
import re, sys
CLR = 200   # um kept around GND copper
s = open(sys.argv[1]).read()
s = re.sub(r'\n\s*\(plane GND \(polygon [^()]*\)\)', '', s)
i = s.index('(net GND'); d = 0
for j in range(i, len(s)):
    d += {'(': 1, ')': -1}.get(s[j], 0)
    if d == 0:
        break
s = s[:i] + s[j + 1:]
s = re.sub(r'(\(class kicad_default[^()]*?)\sGND(\s)', r'\1\2', s)
ko, lines = [], []
for l in s.split('\n'):
    if '(net GND)' not in l:
        lines.append(l.replace('(type route)', '(type protect)')); continue
    m = re.search(r'\(wire \(path (\S+) (\d+)\s+(.*?)\)\(net GND\)', l)
    if m:
        ko.append('    (keepout "" (path %s %d %s))' % (m.group(1), int(m.group(2)) + 2 * CLR, m.group(3))); continue
    m = re.search(r'\(via "Via\[0-1\]_(\d+):\d+_um" +(\S+) (\S+)', l)
    if m:
        for ly in ('F.Cu', 'B.Cu'):
            ko.append('    (keepout "" (path %s %d %s %s %s %s))' % (ly, int(m.group(1)) + 2 * CLR,
                                                                     m.group(2), m.group(3), m.group(2), m.group(3)))
        continue
    raise SystemExit('unhandled GND line: ' + l)
s = '\n'.join(lines)
k = s.index('    (via "Via')
s = s[:k] + '\n'.join(ko) + '\n' + s[k:]
assert '(plane' not in s
if len(sys.argv) > 3:
    s = re.sub(r'\(clearance 200\)$', '(clearance %d)' % int(sys.argv[3]), s, flags=re.M)
open(sys.argv[2], 'w').write(s)
print(len(ko), 'GND keepouts,', s.count('(type protect)'), 'protected tracks / vias')

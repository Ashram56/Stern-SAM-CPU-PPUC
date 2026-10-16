"""Generalised mkisoB: DSN that routes only the given nets. Other nets are dropped from the network, their copper
inside the box (mm, board coordinates) becomes keepouts. Planes: only the inner GND_ISO plane is kept (as in mkisoB).
Usage: mkonly.py in.dsn out.dsn "net1,net2" x0 y0 x1 y1 ["x,y x,y ...|x,y ..."]
The optional last argument lists polygons (mm) the routed nets must stay out of, e.g. the non-isolated side."""
import re, sys
ISO = set(sys.argv[3].split(','))
CLR = 200
bx0, by0, bx1, by1 = (float(v) * 1000 for v in sys.argv[4:8])
X0, X1, Y0, Y1 = bx0, bx1, -by1, -by0
s = open(sys.argv[1]).read()
def block_end(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == '(': d += 1
        elif s[j] == ')':
            d -= 1
            if d == 0: return j + 1
def nm(t): return t[1:-1] if t.startswith('"') else t
# planes: keep only inner GND_ISO
s = re.sub(r'\n    \(plane (?!GND_ISO \(polygon In)[^\n]*(\n {12}[^\n]*)*', '', s)
s = re.sub(r'\n    \(plane GND_ISO \(polygon [FB]\.Cu[^\n]*(\n {12}[^\n]*)*', '', s)
# network: keep ISO nets, one class
i = s.index('  (network'); e = block_end(s, i)
net = s[i:e]
keep = []
for m in re.finditer(r'\n    \(net ', net):
    k = m.start() + 1; ke = block_end(net, k + 4)
    if nm(net[k + 9:].split('\n')[0].strip()) in ISO: keep.append(net[k - 1 + 1:ke])
cls = '    (class ONLY %s\n      (rule\n        (width 200)\n        (clearance 150)\n      )\n    )' % ' '.join(
    '"%s"' % n if '(' in n else n for n in sorted(ISO))
s = s[:i] + '  (network\n    ' + '\n    '.join(x.strip() for x in keep) + '\n' + cls + '\n  )' + s[e:]
# wiring: ISO copper stays, other copper near the area becomes keepouts
i = s.index('  (wiring'); e = block_end(s, i)
out, ko = [], []
body = s[i:e]
items, j = [], body.index('(wiring') + 7
while True:
    j = body.find('(', j)
    if j < 0 or j >= len(body) - 2: break
    je = block_end(body, j); items.append(' '.join(body[j:je].split())); j = je
for l in items:
    m = re.search(r'\(net ("[^"]*"|\S+?)\)', l)
    if not m: continue
    if nm(m.group(1)) in ISO: out.append('    ' + l); continue
    w = re.search(r'\(wire \(path (\S+) ([\d.]+)\s+([-\d.\s]+)\)', l)
    if w:
        c = [float(v) for v in w.group(3).split()]
        if not any(X0 < c[k] < X1 and Y0 < c[k + 1] < Y1 for k in range(0, len(c), 2)): continue
        ko.append('    (keepout "" (path %s %d %s))' % (w.group(1), float(w.group(2)) + 2 * CLR, w.group(3).strip()))
        continue
    v = re.search(r'\(via "Via\[[^]]*\]_(\d+):\d+_um"\s+(\S+) (\S+)', l)
    if v:
        x, y = float(v.group(2)), float(v.group(3))
        if not (X0 < x < X1 and Y0 < y < Y1): continue
        for ly in ('F.Cu', 'B.Cu'):
            ko.append('    (keepout "" (circle %s %d %s %s))' % (ly, int(v.group(1)) + 2 * CLR, v.group(2), v.group(3)))
        continue
    raise SystemExit('unhandled: ' + l)
s = s[:i] + '  (wiring\n' + '\n'.join(out) + '\n  )' + s[e:]
if len(sys.argv) > 8:
    for poly in sys.argv[8].split('|'):
        pts = ' '.join('%d %d' % (float(x) * 1000, -float(y) * 1000) for x, y in (q.split(',') for q in poly.split()))
        for ly in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
            ko.append('    (keepout "" (polygon %s 0 %s))' % (ly, pts))
k = s.index('\n    (plane ')
s = s[:k] + '\n' + '\n'.join(ko) + s[k:]
open(sys.argv[2], 'w').write(s)
print(len(keep), 'nets', len(out), 'iso wires', len(ko), 'keepouts')

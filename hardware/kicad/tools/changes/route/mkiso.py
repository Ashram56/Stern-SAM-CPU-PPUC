"""DSN for routing around the isolated RS485 area. args: in.dsn out.dsn A|B
A: the isolated area is a keepout on F/B (its inner GND_ISO planes already block vias); iso nets go to class ISO
   (route with ignore_net_classes=ISO).  B: no keepout, iso nets in class ISO (route with every other class ignored)."""
import re, sys
ISO = ['GND_ISO', '"Net-(D27-A1)"', '"Net-(D27-A2)"', '"Net-(JP2-A)"', '"Net-(U32-VISOIN)"']
src, dst, mode = sys.argv[1:4]
s = open(src).read()
# drop the outer GND_ISO planes (poured after routing)
s, n = re.subn(r'\n    \(plane GND_ISO \(polygon [FB]\.Cu [^)]*\)\)', '', s)
assert n == 2, n
if mode == 'A':
    m = 300     # um margin on the open (left) side
    poly = [(146000 - m, -184000 + m), (172000, -184000 + m), (172000, -227500 - m), (152000 - m, -227500 - m),
            (152000 - m, -211400 - m), (146000 - m, -211400 - m)]
    pts = ' '.join('%d %d' % p for p in poly + poly[:1])
    ko = ''.join('\n    (keepout "" (polygon %s 0 %s))' % (ly, pts) for ly in ('F.Cu', 'B.Cu'))
    i = s.index('\n    (plane ')
    s = s[:i] + ko + s[i:]
# move the iso nets into their own class
k = s.index('    (class kicad_default')
e = s.index('\n    )', k) + 6
for name in ISO:
    s2 = re.sub(r'(?<=[\s(])%s(?=[\s)])' % re.escape(name), '', s[k:e], count=1)
    assert s2 != s[k:e], name
    s = s[:k] + s2 + s[e:]
    e = s.index('\n    )', k) + 6
rule = s[k:e]
rule = re.sub(r'\(class kicad_default.*?\n      \)', '(class ISO ' + ' '.join(ISO) + '\n      )', rule, flags=re.S)
if not rule.startswith('    (class ISO'):
    rule = re.sub(r'\(class kicad_default[^\n]*(\n      [^(\n][^\n]*)*', '(class ISO ' + ' '.join(ISO), rule)
s = s[:e] + '\n' + rule + s[e:]
open(dst, 'w').write(s)
print('ok', mode)

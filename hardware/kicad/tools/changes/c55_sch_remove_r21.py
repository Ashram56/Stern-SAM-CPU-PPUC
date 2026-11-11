"""c55 (schematic, 2026-11-01): R21 (1k, Pi GPIO27 to BOOTSEL) is removed (Vincent: the Pi already flashes and
recovers the RP2354B over SWD, and the link hung a ~130 mm trace on the flash chip select). J21 GPIO27 gets a
no-connect flag. Usage: c55_sch_remove_r21.py sam_cpu_dir"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import no_connect


def block_end(s, i):
    n = 0
    for j in range(i, len(s)):
        if s[j] == '(': n += 1
        elif s[j] == ')':
            n -= 1
            if n == 0: return j + 1


def cut(s, start):
    return s[:start] + s[block_end(s, start + 2):]


p = os.path.join(sys.argv[1], 'mcu.kicad_sch'); s = open(p).read()
i = s.index('(property "Reference" "R21"'); j = s.rfind('\n\t(symbol\n', 0, i); s = cut(s, j)
m = re.search(r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy 345\.44 185\.42\) \(xy 370\.84 185\.42\)', s); s = cut(s, m.start())
m = re.search(r'\n\t\(label "BOOTSEL"\n\t\t\(at 378\.46 185\.42 0\)', s); s = cut(s, m.start())
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + no_connect((345.44, 185.42)) + '\n' + s[k:]
old = 'and drives RUN and BOOTSEL.'
assert s.count(old) == 1
s = s.replace(old, 'and drives RUN (BOOTSEL only from SW2: R21 removed, GPIO27 free).')
open(p, 'w').write(s)
print('ok')

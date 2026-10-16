"""c30: the DIP switch block is not loaded (Vincent, 2026-10-16): SW3, its pull-ups R168-R175, the 74HC165 U14 that
reads it and U14's decoupling cap C93 get KiCad's DNP flag in sw_dedicated_2.kicad_sch and on the board footprints
(left out of the BOM / position files, crossed out on the schematic). Copper stays, so it can be fitted later.
With U14 absent, U15 pin 10 (serial in) is left open; the firmware ignores that byte.
Usage: c30_dip_switch_dnp.py sam_cpu_dir"""
import os, re, sys
import pcbnew
d = sys.argv[1]
REFS = {'SW3', 'U14', 'C93'} | {'R%d' % i for i in range(168, 176)}
p = os.path.join(d, 'sw_dedicated_2.kicad_sch'); s = open(p).read(); n = 0
def fix(m):
    global n
    r = re.search(r'\(property "Reference" "([^"]+)"', m.group(0))
    if r and r.group(1) in REFS:
        n += 1; return m.group(0).replace('\t\t(dnp no)', '\t\t(dnp yes)', 1)
    return m.group(0)
s = re.sub(r'\n\t\(symbol\n.*?\n\t\)', fix, s, flags=re.S)
open(p, 'w').write(s)
b = pcbnew.LoadBoard(os.path.join(d, 'sam_cpu.kicad_pcb'))
for r in sorted(REFS):
    b.FindFootprintByReference(r).SetDNP(True)
b.Save(os.path.join(d, 'sam_cpu.kicad_pcb'))
print('schematic symbols', n, 'footprints', len(REFS))

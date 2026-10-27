"""c46 (schematic, after c44): JP3 becomes a 3-pin header with a jumper shunt (Vincent, 2026-10-27: one shunt can only
sit on one pair), a right-angle 2.54 mm header (PZ254R-11-03P, LCSC C492411; shunt C100114) so it stays low under the
Pi. Pin 2 (middle) PI_5V, pin 1 now the board +5V, pin 3 PI_5V_BUCK (the board puts pin 3 next to the buck output).
Usage: c46_sch_pi_5v_header_jumper.py project_dir"""
import os, re, sys
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c42_sch_12v_or_pi_buck.py')).read()
exec(src[:src.index('# ---------------------------------------------------------------- power sheet')])   # c42 helpers
pw[0] = 1130
p = os.path.join(d, 'power.kicad_sch'); s = open(p).read()
a, b = find_symbol(s, 'JP3'); blk = s[a:b]
assert '(lib_id "Jumper:SolderJumper_3_Open")' in blk
blk = blk.replace('(lib_id "Jumper:SolderJumper_3_Open")', '(lib_id "Jumper:Jumper_3_Open")')
blk = blk.replace('"Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm"', '"Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Horizontal"')
old = 'Pi header 5 V: bridge 1-2 for the buck, 2-3 for the board +5 V, none for a Jetson (open by default)'
assert old in blk
blk = blk.replace(old, 'Pi header 5 V jumper, right-angle 1x3 2.54 mm PZ254R-11-03P (LCSC C492411) + shunt C100114: '
                       '1-2 board +5 V, 2-3 buck, no shunt for a Jetson')
s = s[:a] + blk + s[b:]
s = embed(s, 'Jumper', 'Jumper_3_Open')
# swap the sources: +5V on pin 1 (386.08), PI_5V_BUCK on pin 3 (396.24)
m = re.search(r'\n\t\(label "PI_5V_BUCK"\n\t\t\(at 381 220.98 180\)', s); assert m
s = s[:m.start()] + s[block(s, m.start() + 2):]
for mm in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "power:\+5V"\)\n\t\t\(at 401.32 220.98 ', s):
    s = s[:mm.start()] + s[block(s, mm.start() + 2):]; break
else: raise SystemExit('no +5V at the jumper')
add = PWR('power:+5V', 381.0, 220.98) + label('PI_5V_BUCK', 401.32, 220.98, 0, 'left')
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + add + s[k:]
s = replace_once(s, 'JP3 (open by default) feeds J21 pins 2 / 4 (PI_5V) from one source:\\n1-2: the buck (Pi 4 / Pi 5, 5.18 V 3 A)\\n'
                 '2-3: the board +5 V\\nopen: Jetson, or a Pi on its own USB-C.',
                 'JP3 (3-pin header, one shunt) feeds J21 pins 2 / 4 (PI_5V) from one source:\\n1-2: the board +5 V\\n'
                 '2-3: the buck (Pi 4 / Pi 5, 5.18 V 3 A)\\nno shunt: Jetson, or a Pi on its own USB-C.')
open(p, 'w').write(s)
print('ok')

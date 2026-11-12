"""c66 (schematic): AMP_PDN also driven by the RP2354B (Vincent's card, 2026-11-12: I2C + PDN, 3 wires).

A clean corridor exists from U4 pin 44 (GPIO35): F stub to a via east of the pin, In2 under slow lines only, then
B / F to the AMP_PDN via (c66b board). LINE_DET stays on the 74HC157 only.
- mcu sheet: U4 pin 44 (GPIO35) no-connect -> AMP_PDN.
- audio sheet: R190 10k pull-up kept (amplifiers leave shutdown by themselves while GPIO35 is an input); C158 becomes
  100 nF (1 ms) so the GPIO drives a small load. Firmware: GPIO35 low = shutdown / hard reset, input = run.
Usage: c66_sch_pdn_gpio35.py project_dir"""
import os, re, sys
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c62_sch_audio_tas5805m.py')).read()
exec(src[:src.index('# capacitor references')])     # helpers only

p = os.path.join(d, 'mcu.kicad_sch'); s = open(p).read()
m = re.search(r'\n\t\(no_connect\n\t\t\(at 208.28 187.96\)', s); assert m
s = s[:m.start()] + s[block(s, m.start() + 2):]
add = wire((208.28, 187.96), (213.36, 187.96)) + glabel('AMP_PDN', 213.36, 187.96, 0, 'output')
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + add + s[k:]
open(p, 'w').write(s)

p = os.path.join(d, 'audio.kicad_sch'); s = open(p).read()
s = replace_once(s, '(text "Amplifier control: RP2354B I2C1 (GPIO38 SDA / GPIO39 SCL), PDN by RC"',
                 '(text "Amplifier control: RP2354B I2C1 (GPIO38 SDA / GPIO39 SCL), PDN (GPIO35 + RC)"')
s = replace_once(s, '(text "AMP_PDN rises 10 ms after +3V3 (10k / 1 uF). The RP2354B resets both amplifiers\\nover I2C (0x01),',
                 '(text "AMP_PDN rises 1 ms after +3V3 (10k / 100 nF) while GPIO35 is an input. GPIO35 low = hard reset /\\nshutdown; the RP2354B also resets over I2C (0x01),')
i = s.index('(property "Reference" "C158"'); j = s.rindex('\n\t(symbol', 0, i); e = block(s, j + 2)
r = s[j:e]
r = replace_once(r, '(property "Value" "1uF"', '(property "Value" "100nF"')
r = replace_once(r, '"%s"' % D_1U, '"%s"' % D_100N)
s = s[:j] + r + s[e:]
open(p, 'w').write(s)
print('ok')

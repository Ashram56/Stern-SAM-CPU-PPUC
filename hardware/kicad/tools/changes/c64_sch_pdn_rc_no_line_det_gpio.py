"""c64 (schematic): only I2C from the RP2354B to the amplifiers.

Around U4 only two tracks fit out of the corner between pins 40 and 41 (0.15 mm), so:
- AMP_PDN: R190 becomes a 10k pull-up to +3V3 and new C158 1 uF to GND (about 10 ms after +3V3). The RP2354B
  resets the TAS5805M over I2C (register 0x01) and holds them in deep sleep / Hi-Z (0x03) until configured.
- LINE_DET only drives the 74HC157 select; the TAS5805M mutes by itself on the I2S clock change (clock error).
- mcu sheet: U4 pins 45 (GPIO36) and 44 (GPIO35) back to no-connect.
Usage: c64_sch_pdn_rc_no_line_det_gpio.py project_dir"""
import os, re, sys
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c62_sch_audio_tas5805m.py')).read()
exec(src[:src.index('# capacitor references')])     # helpers only (no file is written above this line)


def cut(s, start_pat):
    """remove the top-level block whose text starts with start_pat (must be unique)."""
    m = [x for x in re.finditer(r'\n\t\(', s) if s.startswith(start_pat, x.start() + 1)]
    assert len(m) == 1, (len(m), start_pat[:60])
    i = m[0].start() + 2
    return s[:m[0].start()] + s[block(s, i):]


def find_block(s, head, at):
    for x in re.finditer(r'\n\t' + re.escape(head), s):
        e = block(s, x.start() + 2)
        if '(at %s' % at in s[x.start():e]: return x.start(), e
    raise AssertionError((head, at))


p = os.path.join(d, 'audio.kicad_sch'); s = open(p).read()
s = replace_once(s, '(text "Amplifier control: RP2354B I2C1 (GPIO38 SDA / GPIO39 SCL), PDN (GPIO36)"',
                 '(text "Amplifier control: RP2354B I2C1 (GPIO38 SDA / GPIO39 SCL), PDN by RC"')
s = replace_once(s, '(text "AMP_PDN low (100k pull-down, RP2354B at reset): both amplifiers off.\\nThe RP2354B raises AMP_PDN, then loads',
                 '(text "AMP_PDN rises 10 ms after +3V3 (10k / 1 uF). The RP2354B resets both amplifiers\\nover I2C (0x01), keeps them in deep sleep until configured, then loads')
i = s.index('(property "Reference" "R190"'); j = s.rindex('\n\t(symbol', 0, i); e = block(s, j + 2)
r = s[j:e]
r = replace_once(r, '(property "Value" "100k"', '(property "Value" "10k"')
r = replace_once(r, '"%s"' % D_R['100k'], '"%s"' % D_R['10k'])
s = s[:j] + r + s[e:]
a, b = find_block(s, '(global_label "AMP_PDN"', '137.16 173.99 90'); s = s[:a] + s[b:]
a, b = find_block(s, '(symbol\n\t\t(lib_id "power:GND")', '137.16 184.15 0'); s = s[:a] + s[b:]
pw[0] = 10900
add = PWR('+3V3', 137.16, 173.99)
add += wire((137.16, 184.15), (137.16, 186.69)) + glabel('AMP_PDN', 137.16, 186.69, 270, 'input')
add += two('Device', 'C', 'C158', '1uF', FP['0805'], 129.54, 182.88, 'AMP_PDN', 'GND', D_1U)
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + add + s[k:]
open(p, 'w').write(s)

p = os.path.join(d, 'mcu.kicad_sch'); s = open(p).read()
add = ''
for y, net in ((190.5, 'AMP_PDN'), (187.96, 'LINE_DET')):
    a, b = find_block(s, '(global_label "%s"' % net, '213.36 %s 0' % fmt(y)); s = s[:a] + s[b:]
    m = re.search(r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy 208.28 %s\) \(xy 213.36 %s\)' % (re.escape(fmt(y)), re.escape(fmt(y))), s)
    assert m, y
    s = s[:m.start()] + s[block(s, m.start() + 2):]
    add += no_connect(208.28, y)
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + add + s[k:]
open(p, 'w').write(s)
print('ok')

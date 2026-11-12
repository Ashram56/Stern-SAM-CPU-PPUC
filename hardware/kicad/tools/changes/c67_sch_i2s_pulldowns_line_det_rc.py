"""c67 (schematic): parts for use without a Raspberry Pi (Vincent, 2026-11-12).
- R199 / R200 / R201 100k from I2S_BCK / I2S_LRCK / I2S_DIN to GND: the A inputs of U26 no longer float
  when neither the Pi nor J28 drives them.
- R202 10k in series between LINE_DET (J30 plug switch, R198 pull-up) and the select pin of U26 (new net
  MUX_SEL), C160 100 nF from MUX_SEL to GND: 1 ms debounce and ESD current limit for the jack contact.
Usage: c67_sch_i2s_pulldowns_line_det_rc.py project_dir"""
import os, re, sys
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c62_sch_audio_tas5805m.py')).read()
exec(src[:src.index('# capacitor references')])     # helpers only (no file is written above this line)
p = os.path.join(d, 'audio.kicad_sch'); s = open(p).read()
i = s.index('\t(global_label "LINE_DET"\n\t\t(shape input)\n\t\t(at 43.18 104.14 180)'); e = block(s, i + 1)
s = s[:i] + label('MUX_SEL', 43.18, 104.14, 180).rstrip('\n') + s[e:]
pw[0] = 11000
D100K = 'Resistor 100k 1% 0805, 0805W8F1003T5E (LCSC C17407)'
add = text('Without a Pi: 100k pull-downs on the I2S inputs; LINE_DET through 10k / 100 nF (1 ms, ESD)', 93.98, 113.03)
add += two('Device', 'R', 'R199', '100k', FP['R'], 96.52, 125.73, 'I2S_BCK', 'GND', D100K)
add += two('Device', 'R', 'R200', '100k', FP['R'], 109.22, 125.73, 'I2S_LRCK', 'GND', D100K)
add += two('Device', 'R', 'R201', '100k', FP['R'], 121.92, 125.73, 'I2S_DIN', 'GND', D100K)
add += two('Device', 'R', 'R202', '10k', FP['R'], 134.62, 125.73, 'LINE_DET', 'MUX_SEL', D_R['10k'])
add += two('Device', 'C', 'C160', '100n', FP['0805'], 147.32, 125.73, 'MUX_SEL', 'GND', D_100N)
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + add + s[k:]
open(p, 'w').write(s)
print('ok')

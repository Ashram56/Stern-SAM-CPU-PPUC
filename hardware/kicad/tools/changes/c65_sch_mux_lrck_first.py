"""c65 (schematic): 74HC157 channel 1 carries LRCK and channel 2 BCK (was the reverse).

On the board the PCM1808 has LRCK on its top pin row and BCK on its bottom row; with LRCK on U26 pins 2-4 and BCK on
pins 5-7 both ADC clocks reach the mux on the top layer without crossing. Labels renamed in place at the U26 pin ends.
Usage: c65_sch_mux_lrck_first.py project_dir"""
import os, re, sys
d = sys.argv[1]
SWAP = {  # (name, y) of the labels on the U26 pin rows (x 40-100 on the audio sheet): new name
    ('I2S_BCK', '73.66'): 'I2S_LRCK', ('ADC_BCK', '76.2'): 'ADC_LRCK', ('I2S_LRCK', '81.28'): 'I2S_BCK',
    ('ADC_LRCK', '83.82'): 'ADC_BCK', ('MUX_BCK', '73.66'): 'MUX_LRCK', ('MUX_LRCK', '81.28'): 'MUX_BCK'}
p = os.path.join(d, 'audio.kicad_sch'); s = open(p).read()
done = 0
def sub(m):
    global done
    kind, name, x, y = m.group(1), m.group(2), m.group(3), m.group(4)
    k = (name, y)
    if k in SWAP and 40 <= float(x) <= 100:
        done += 1
        return m.group(0).replace('(%s "%s"' % (kind, name), '(%s "%s"' % (kind, SWAP[k]), 1)
    return m.group(0)
s = re.sub(r'\((global_label|label) "([^"]+)"\n(?:\t\t[^\n]*\n)*?\t\t\(at ([\d.]+) ([\d.]+) [\d.]+\)', sub, s)
assert done == 6, done
open(p, 'w').write(s); print('ok')

"""c62 (schematic): digital audio chain. Two TAS5805M (I2S in, DSP, class D) replace PCM5102A + OPA1678 + 2x TDA7297.

Audio sheet rebuilt:
- U23 TAS5805M (I2C 0x2C, ADR 4.7k to DVDD): left (OUT_A) / right (OUT_B) bridged, J10 + J22 as before.
- U24 TAS5805M (I2C 0x2D, ADR 15k): both channels carry the subwoofer mix from its DSP, J24 as before.
  Both: PVDD = +12V (bulk C108 / C118 470 uF 35 V kept, 2 x 22 uF 35 V 1206 + 2 x 100 nF per amp), DVDD = +3V3,
  LC filter 10 uH FXL0630 + 680 nF per output (datasheet table 8-2: run 768 kHz, or BD at 384 kHz, since PVDD can
  exceed 12 V), bootstrap 220 nF, AVDD / VR_DIG 1 uF. One AMP_PDN for both (100k pull-down: off until the RP2354B
  has configured them), I2C AMP_SDA / AMP_SCL (4.7k pull-ups) from RP2354B I2C1 (GPIO38 / GPIO39).
- U26 74HC157 picks the I2S source: Pi / J28 (I2S_BCK, I2S_LRCK, I2S_DIN) when J30 is empty, the line-in ADC when a
  plug is in (LINE_DET from the J30 TN switch, 220k pull-up: low through the input divider when T touches TN).
  33 R series resistors feed AMP_SCLK / AMP_LRCLK / AMP_SDIN.
- U22 PCM1808 ADC, master 256 fs (MD0 = MD1 = high), I2S (FMT low), SCKI from Y2 12.288 MHz: 48 kHz, BCK 64 fs.
  Inputs: 10k / 10k divider (2 Vrms line level -> 0.92 Vrms, full scale 1.06 Vrms), 470 pF, 4.7 uF coupling.
rs485_i2s sheet: J30 T / R -> LINEIN_L / LINEIN_R, TN -> LINE_DET, RN unused.
mcu sheet: U4 pin 48 (GPIO39) AMP_MUTE -> AMP_SCL, pin 47 (GPIO38) AMP_SDA, pin 45 (GPIO36) AMP_PDN, pin 44 (GPIO35) LINE_DET.
Usage: c62_sch_audio_tas5805m.py project_dir"""
import os, re, sys, uuid
d = sys.argv[1]
SYM = os.environ.get('KICAD10_SYMBOL_DIR', '/opt/k10/root/usr/share/kicad/symbols')
PATH = '/2aea4fdf-a573-57d0-a5af-7bd6ce737647/a37597f6-5aec-507d-b794-5c4f395391ec'   # audio sheet instance


def U(): return str(uuid.uuid4())
def fmt(v): return ('%.2f' % v).rstrip('0').rstrip('.')


def block(s, i):
    n = 0
    for j in range(i, len(s)):
        if s[j] == '(': n += 1
        elif s[j] == ')':
            n -= 1
            if n == 0: return j + 1


def replace_once(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:80])
    return s.replace(old, new)


# ---------------------------------------------------------------- PCM1808 project symbol
PCM_PINS = [  # number, name, type, x, y, angle
    ('13', 'VINL', 'input', -12.7, 5.08, 0), ('14', 'VINR', 'input', -12.7, 2.54, 0),
    ('1', 'VREF', 'passive', -12.7, -5.08, 0),
    ('6', 'SCKI', 'input', 12.7, 7.62, 180), ('8', 'BCK', 'bidirectional', 12.7, 5.08, 180),
    ('7', 'LRCK', 'bidirectional', 12.7, 2.54, 180), ('9', 'DOUT', 'output', 12.7, 0, 180),
    ('12', 'FMT', 'input', 12.7, -5.08, 180), ('10', 'MD0', 'input', 12.7, -7.62, 180),
    ('11', 'MD1', 'input', 12.7, -10.16, 180),
    ('3', 'VCC', 'power_in', -2.54, 15.24, 270), ('4', 'VDD', 'power_in', 2.54, 15.24, 270),
    ('2', 'AGND', 'power_in', -2.54, -15.24, 90), ('5', 'DGND', 'power_in', 2.54, -15.24, 90)]


def lib_prop(name, val, x, y, hide):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n%s'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n') % (
        name, val, fmt(x), fmt(y), '\t\t\t(hide yes)\n' if hide else '')


def pcm1808_symbol():
    t = ('\t(symbol "PCM1808"\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
         '\t\t(duplicate_pin_numbers_are_jumpers no)\n')
    t += lib_prop('Reference', 'U', -10.16, 13.97, False) + lib_prop('Value', 'PCM1808', 5.08, 13.97, False)
    t += lib_prop('Footprint', 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm', 0, -17.78, True)
    t += lib_prop('Datasheet', 'https://www.ti.com/lit/ds/symlink/pcm1808.pdf', 0, -20.32, True)
    t += lib_prop('Description', 'Stereo audio ADC 24 bit 96 kHz, single-ended inputs, I2S / left-justified, '
                  'master or slave, VCC 5 V analog, VDD 3.3 V digital, TSSOP-14', 0, 0, True)
    t += lib_prop('ki_keywords', 'audio ADC I2S', 0, 0, True)
    t += lib_prop('ki_fp_filters', 'TSSOP*4.4x5mm*P0.65mm*', 0, 0, True)
    t += ('\t\t(symbol "PCM1808_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start -10.16 12.7)\n\t\t\t\t(end 10.16 -12.7)\n'
          '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n'
          '\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t\t(symbol "PCM1808_1_1"\n')
    for num, name, typ, x, y, a in PCM_PINS:
        t += ('\t\t\t(pin %s line\n\t\t\t\t(at %s %s %d)\n\t\t\t\t(length 2.54)\n\t\t\t\t(name "%s"\n'
              '\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n'
              '\t\t\t\t)\n\t\t\t\t(number "%s"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n'
              '\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n') % (typ, fmt(x), fmt(y), a, name, num)
    t += '\t\t)\n\t\t(embedded_fonts no)\n\t)\n'
    return t


p = os.path.join(d, 'sam_cpu.kicad_sym'); L = open(p).read()
if '(symbol "PCM1808"' not in L:
    k = L.rstrip().rindex('\n)')
    L = L[:k] + '\n' + pcm1808_symbol().rstrip('\n') + L[k:]
    open(p, 'w').write(L)


# ---------------------------------------------------------------- library pins
def lib_text(lib, name):
    if lib == 'sam_cpu':
        src = open(os.path.join(d, 'sam_cpu.kicad_sym')).read()
    else:
        src = open(os.path.join(SYM, lib + '.kicad_sym')).read()
    i = src.index('\t(symbol "%s"' % name); j = block(src, i + 1)
    return src[i:j]


def lib_pins(lib, name):
    b = lib_text(lib, name)
    m = re.search(r'\(extends "([^"]+)"\)', b)
    if m: return lib_pins(lib, m.group(1))
    out = {}
    for m in re.finditer(r'\(pin (\w+) \w+\s*\(at ([-\d. ]+)\)\s*\(length [\d.]+\).*?\(name "([^"]*)".*?\(number "([^"]*)"',
                         b, re.S):
        x, y, a = m.group(2).split()
        out[m.group(4)] = (float(x), float(y), int(a))
    return out


def embed_text(lib, name):
    b = lib_text(lib, name)
    m = re.search(r'\(extends "([^"]+)"\)', b)
    assert not m, 'extends not handled: ' + name
    full = '%s:%s' % (lib, name)
    sym = b.replace('(symbol "%s"' % name, '(symbol "%s"' % full, 1)
    sym = re.sub(r'\(size 1\.27 1\.27\)', '(size 1.5 1.5)', sym)
    return '\n'.join('\t' + l for l in sym.split('\n'))


# ---------------------------------------------------------------- sheet primitives (style of c42)
def prop(name, val, x, y, hide=False, just=None, ang=0):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s %d)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.6 1.6)\n\t\t\t\t)\n%s\t\t\t)\n\t\t)\n') % (
        name, val, fmt(x), fmt(y), ang, '\t\t\t(hide yes)\n' if hide else '',
        '\t\t\t\t(justify %s)\n' % just if just else '')


def symbol(lib_id, ref, val, fp, x, y, pins, desc='', ds='', rpos=None, vpos=None, power=False, just='left'):
    rx, ry = rpos or (x + 2.54, y - 1.27)
    vx, vy = vpos or (x + 2.54, y + 1.27)
    t = ('\t(symbol\n\t\t(lib_id "%s")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
         '\t\t(in_bom %s)\n\t\t(on_board %s)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n') % (
        lib_id, fmt(x), fmt(y), 'no' if power else 'yes', 'no' if power else 'yes', U())
    t += prop('Reference', ref, rx, ry, hide=power, just=None if power else just)
    t += prop('Value', val, vx, vy, just=None if power else just)
    t += prop('Footprint', fp, x, y, True) + prop('Datasheet', ds, x, y, True) + prop('Description', desc, x, y, True)
    for n in pins: t += '\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (n, U())
    t += ('\t\t(instances\n\t\t\t(project "sam_cpu"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n'
          '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n') % (PATH, ref)
    return t


def wire(*pts):
    t = ''
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t += ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n'
              '\t\t)\n\t\t(uuid "%s")\n\t)\n') % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), U())
    return t


def label(name, x, y, ang):
    just = 'right' if ang in (180, 270) else 'left'
    return ('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.6 1.6)\n\t\t\t)\n'
            '\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (name, fmt(x), fmt(y), ang, just, U())


def glabel(name, x, y, ang, shape='passive'):
    just = 'right' if ang in (180, 270) else 'left'
    w = len(name) * 1.25 + 4.5
    rx, ry = {0: (x + w, y), 180: (x - w, y), 90: (x, y - w), 270: (x, y + w)}[ang]
    return ('\t(global_label "%s"\n\t\t(shape %s)\n\t\t(at %s %s %d)\n\t\t(fields_autoplaced yes)\n\t\t(effects\n'
            '\t\t\t(font\n\t\t\t\t(size 1.6 1.6)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n\t\t(uuid "%s")\n'
            '\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %s %s 0)\n\t\t\t(hide yes)\n'
            '\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.6 1.6)\n'
            '\t\t\t\t)\n\t\t\t\t(justify %s)\n\t\t\t)\n\t\t)\n\t)\n') % (name, shape, fmt(x), fmt(y), ang, just, U(),
                                                                    fmt(rx), fmt(ry), just)


def junction(x, y):
    return ('\t(junction\n\t\t(at %s %s)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "%s")\n\t)\n'
            % (fmt(x), fmt(y), U()))


def no_connect(x, y):
    return '\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid "%s")\n\t)\n' % (fmt(x), fmt(y), U())


def text(t, x, y, size=1.8):
    return ('\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %s %s)\n'
            '\t\t\t)\n\t\t\t(justify left top)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (t, fmt(x), fmt(y), size, size, U())


def rect(x1, y1, x2, y2):
    return ('\t(rectangle\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width 0.2)\n\t\t\t(type dash)\n'
            '\t\t\t(color 120 120 120 1)\n\t\t)\n\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid "%s")\n\t)\n'
            % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), U()))


pw = [10000]
POWER = ('GND', '+12V', '+3V3', '+5V')


def PWR(name, x, y):
    pw[0] += 1
    desc = 'Power symbol creates a global label with name \\"%s\\"' % name
    vy = y + 2.54 if name == 'GND' else y - 3.81
    return symbol('power:' + name, '#PWR%d' % pw[0], name, '', x, y, ['1'], desc, rpos=(x, y), vpos=(x, vy), power=True)


def flag(x, y):
    pw[0] += 1
    return symbol('power:PWR_FLAG', '#FLG%d' % pw[0], 'PWR_FLAG', '', x, y, ['1'],
                  'Special symbol for telling ERC where power comes from', rpos=(x, y), vpos=(x, y - 3.81), power=True)


# ---------------------------------------------------------------- placement helpers
used_libs = set()
out = []
GLOBAL = {'I2S_BCK', 'I2S_LRCK', 'I2S_DIN', 'LINE_DET', 'LINEIN_L', 'LINEIN_R', 'AMP_SDA', 'AMP_SCL', 'AMP_PDN'}


def net_end(net, x, y, direction):
    """Terminate a wire end at (x, y) going `direction` (L, R, U, D) with a label or power symbol."""
    t = ''
    if net == 'NC':
        return no_connect(x, y)
    if net in POWER:
        return PWR(net, x, y)       # the symbol body points away from the pin row (down for GND, up otherwise)
    ang = {'L': 180, 'R': 0, 'U': 90, 'D': 270}[direction]
    if net in GLOBAL:
        shape = 'input' if net in ('I2S_BCK', 'I2S_LRCK', 'I2S_DIN', 'LINEIN_L', 'LINEIN_R', 'LINE_DET') else 'bidirectional'
        if net == 'AMP_PDN': shape = 'input'
        return glabel(net, x, y, ang, shape)
    return label(net, x, y, ang)


def ic(lib, name, ref, val, fp, x, y, nets, desc, ds='', stub=2.54, rpos=None, vpos=None, stubs=None):
    """Place an IC; nets: pin number -> net. Pins get a stub and a label / power symbol."""
    used_libs.add((lib, name))
    pins = lib_pins(lib, name)
    t = symbol('%s:%s' % (lib, name), ref, val, fp, x, y, list(pins), desc, ds, rpos=rpos, vpos=vpos)
    done = set(); gnd = {}
    for num, net in nets.items():
        px, py, a = pins[num]
        sx, sy = x + px, y - py
        if (sx, sy) in done: continue
        done.add((sx, sy))
        if net == 'NC':
            t += no_connect(sx, sy); continue
        st = (stubs or {}).get(num, stub)
        dx, dy, dr = {0: (-st, 0, 'L'), 180: (st, 0, 'R'), 90: (0, st, 'D'), 270: (0, -st, 'U')}[a]
        t += wire((sx, sy), (sx + dx, sy + dy))
        if net == 'GND' and a == 90:
            gnd.setdefault(a, []).append((sx + dx, sy + dy)); continue
        t += net_end(net, sx + dx, sy + dy, dr)
    for pts in gnd.values():          # bottom ground pins: one bar, one symbol
        pts.sort()
        if len(pts) > 1:
            t += wire(pts[0], pts[-1]) + ''.join(junction(*q) for q in pts[1:-1])
        t += PWR('GND', *pts[0])
    missing = set(pins) - set(nets)
    assert not missing, (ref, missing)
    return t


def two(lib, name, ref, val, fp, x, y, top, bot, desc):
    """Vertical two-pin part at (x, y): pin 1 top (y - 3.81, or 2.54 for small symbols), pin 2 bottom."""
    used_libs.add((lib, name))
    pins = lib_pins(lib, name)
    h = pins['1'][1]
    t = symbol('%s:%s' % (lib, name), ref, val, fp, x, y, ['1', '2'], desc, rpos=(x + 2.54, y - 1.27),
               vpos=(x + 2.54, y + 1.27))
    for net, py, dr in ((top, y - h, 'U'), (bot, y + h, 'D')):
        if net in POWER and ((net == 'GND') == (dr == 'D')):
            t += net_end(net, x, py, dr)
        else:
            t += wire((x, py), (x, py - 2.54 if dr == 'U' else py + 2.54)) + net_end(
                net, x, py - 2.54 if dr == 'U' else py + 2.54, dr)
    return t


FP = {'0805': 'Capacitor_SMD:C_0805_2012Metric', '1206': 'Capacitor_SMD:C_1206_3216Metric',
      'R': 'Resistor_SMD:R_0805_2012Metric', 'L': 'Inductor_SMD:L_Changjiang_FXL0630',
      'CP': 'Capacitor_SMD:CP_Elec_8x10', 'FB': 'Inductor_SMD:L_0805_2012Metric'}
D_100N = 'Capacitor 100 nF 50 V X7R 0805, CC0805KRX7R9BB104 (LCSC C49678)'
D_22U = 'Capacitor 22 uF 35 V X5R 1206, TDK C3216X5R1V226MTJ00E (LCSC C342620)'
D_1U = 'Capacitor 1 uF 50 V X7R 0805, CL21B105KBFNNNE (LCSC C28323)'
D_4U7 = 'Capacitor 4.7 uF 25 V X5R 0805, CL21A475KAQNNNE (LCSC C1779)'
D_10U = 'Capacitor 10 uF 25 V X5R 0805, CL21A106KAYNNNE (LCSC C15850)'
D_220N = 'Capacitor 220 nF 50 V X7R 0805, CL21B224KBFNNNE (LCSC C5378)'
D_680N = 'Capacitor 680 nF 50 V X7R 0805, CC0805KKX7R9BB684 (LCSC C107133)'
D_470P = 'Capacitor 470 pF 50 V X7R 0805, 0805B471K500NT (LCSC C1743)'
D_470U = 'Polarized capacitor 470 uF 35 V 8 x 10 mm, RV35V470M8X10 (LCSC C48935389)'
D_L = 'Inductor 10 uH 4.5 A (Isat 5.5 A) 68 mOhm, FXL0630-100-M 7 x 6.6 x 3 mm (LCSC C167223)'
D_R = {'4.7k': 'Resistor 4.7k 1% 0805, 0805W8F4701T5E (LCSC C17673)',
       '15k': 'Resistor 15k 1% 0805, 0805W8F1502T5E (LCSC C17475)',
       '10k': 'Resistor 10k 1% 0805, 0805W8F1002T5E (LCSC C17414)',
       '100k': 'Resistor 100k 1% 0805, 0805W8F1003T5E (LCSC C17407)',
       '220k': 'Resistor 220k 1% 0805, 0805W8F2203T5E (LCSC C17556)',
       '33': 'Resistor 33 R 1% 0805, 0805W8F330JT5E (LCSC C17634)'}
TAS_FP = 'Package_SO:Texas_PWP0028V_TSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.4x9.7mm_Mask2.94x5.62mm_ThermalVias'
TAS_DS = 'https://www.ti.com/lit/ds/symlink/tas5805m.pdf'

# capacitor references: freed C96-C121 (C108 / C118 kept as bulk), then C138 onwards
cref = [c for c in range(96, 122) if c not in (108, 118)] + list(range(138, 200))
rref = list(range(186, 204))
def C(): return 'C%d' % cref.pop(0)
def R(): return 'R%d' % rref.pop(0)


add = ''
# ---------------------------------------------------------------- amplifiers
amps = (
    ('U23', 'AMP1', 30.48, 'C108', '4.7k', 'I2C address 0x2C (ADR 4.7k)', 'Stereo amplifier: left = OUT_A, right = OUT_B (bridged)',
     (('A', 'SPK_L_P', 'SPK_L_N'), ('B', 'SPK_R_P', 'SPK_R_N'))),
    ('U24', 'AMP2', 160.02, 'C118', '15k', 'I2C address 0x2D (ADR 15k)', 'Subwoofer amplifier: both channels carry the DSP subwoofer mix',
     (('A', 'SUB1_P', 'SUB1_N'), ('B', 'SUB2_P', 'SUB2_N'))))
lref = iter(range(3, 11))
for ref, A, y0, cbulk, radr, addr, title, chans in amps:
    X, Y = 220.98, y0 + 55.88
    add += rect(149.86, y0, 411.48, y0 + 119.38) + text(title + ' (' + ref + ', ' + addr + ')', 151.13, y0 + 1.27)
    nets = {'1': 'GND', '5': 'GND', '14': 'GND', '19': 'GND', '24': 'GND', '29': 'GND',
            '2': '+3V3', '15': '+12V', '16': '+12V', '27': '+12V', '28': '+12V',
            '3': A + '_ADR', '4': A + '_VRDIG', '13': A + '_AVDD', '6': 'AMP_LRCLK', '7': 'AMP_SCLK', '8': 'AMP_SDIN',
            '9': 'NC', '10': 'AMP_SDA', '11': 'AMP_SCL', '12': 'AMP_PDN'}
    for ch, _, _ in chans:
        nets.update({{'A': '26', 'B': '17'}[ch]: '%s_OUT%s_P' % (A, ch), {'A': '23', 'B': '20'}[ch]: '%s_OUT%s_N' % (A, ch),
                     {'A': '25', 'B': '18'}[ch]: '%s_BST%s_P' % (A, ch), {'A': '22', 'B': '21'}[ch]: '%s_BST%s_N' % (A, ch)})
    add += ic('Amplifier_Audio', 'TAS5805MPWP', ref, 'TAS5805M', TAS_FP, X, Y, nets,
              '23 W stereo / 45 W mono digital-input class-D amplifier with DSP, 4.5-26.4 V, TAS5805MPWPR (LCSC C478472)',
              TAS_DS, stub=5.08, rpos=(X + 7.62, Y - 33.02), vpos=(X + 7.62, Y + 33.02),
              stubs={'12': 15.24, '11': 15.24, '2': 10.16})
    # supply decoupling (left block)
    xs = 157.48
    add += text('PVDD (+12V): bulk + 22 uF + 100 nF at each PVDD pin pair', xs, y0 + 7.62, 1.5)
    add += two('Device', 'C_Polarized', cbulk, '470u', FP['CP'], xs + 2.54, y0 + 20.32, '+12V', 'GND', D_470U)
    for i in range(2):
        add += two('Device', 'C', C(), '22u', FP['1206'], xs + 12.7 + 10.16 * i, y0 + 20.32, '+12V', 'GND', D_22U)
        add += two('Device', 'C', C(), '100n', FP['0805'], xs + 33.02 + 10.16 * i, y0 + 20.32, '+12V', 'GND', D_100N)
    add += text('DVDD (+3V3), AVDD, VR_DIG', xs, y0 + 33.02, 1.5)
    add += two('Device', 'C', C(), '4.7u', FP['0805'], xs + 2.54, y0 + 45.72, '+3V3', 'GND', D_4U7)
    add += two('Device', 'C', C(), '100n', FP['0805'], xs + 12.7, y0 + 45.72, '+3V3', 'GND', D_100N)
    add += two('Device', 'C', C(), '1u', FP['0805'], xs + 2.54, y0 + 66.04, A + '_AVDD', 'GND', D_1U)
    add += two('Device', 'C', C(), '1u', FP['0805'], xs + 12.7, y0 + 66.04, A + '_VRDIG', 'GND', D_1U)
    add += text('ADR: ' + addr, xs, y0 + 78.74, 1.5)
    add += two('Device', 'R', R(), radr, FP['R'], xs + 2.54, y0 + 91.44, '+3V3', A + '_ADR', D_R[radr])
    # outputs: bootstrap caps, LC filter, connectors (right block)
    xo = 264.16
    add += text('Bootstrap 220 nF, LC filter 10 uH + 680 nF (4 or 8 ohm),\\nswitching 768 kHz (or BD 384 kHz)',
                190.5, y0 + 101.6, 1.5)
    for k, (ch, pnet, nnet) in enumerate(chans):
        for j, (pol, spk) in enumerate((('P', pnet), ('N', nnet))):
            col = xo + 2.54 + (k * 2 + j) * 35.56
            outn, bstn = '%s_OUT%s_%s' % (A, ch, pol), '%s_BST%s_%s' % (A, ch, pol)
            add += two('Device', 'C', C(), '220n', FP['0805'], col, y0 + 27.94, bstn, outn, D_220N)
            lr = 'L%d' % next(lref)
            yl = y0 + 55.88      # inductor drawn horizontally with wires: OUT label - L - SPK label
            used_libs.add(('Device', 'L'))
            add += symbol('Device:L', lr, '10u', FP['L'], col + 10.16, yl, ['1', '2'], D_L,
                          rpos=(col + 12.7, yl - 1.27), vpos=(col + 12.7, yl + 1.27))
            add += wire((col + 10.16, yl - 3.81), (col + 10.16, yl - 6.35)) + label(outn, col + 10.16, yl - 6.35, 90)
            add += wire((col + 10.16, yl + 3.81), (col + 10.16, yl + 6.35)) + label(spk, col + 10.16, yl + 6.35, 270)
            add += two('Device', 'C', C(), '680n', FP['0805'], col + 20.32, y0 + 81.28, spk, 'GND', D_680N)
    # connectors
    if ref == 'U23':
        conns = (('J10', 'J10 SPEAKERS', ('SPK_L_P', 'SPK_R_P', 'SPK_L_N', 'SPK_R_N'), 'Original connector: pins 3 / 4 = minus'),
                 ('J22', 'J22 STEREO', ('SPK_L_P', 'SPK_L_N', 'SPK_R_P', 'SPK_R_N'), 'Same channels as pairs'))
    else:
        conns = (('J24', 'J24 SUBWOOFER', ('SUB1_P', 'SUB1_N', 'SUB2_P', 'SUB2_N'), 'Dual voice coil or two subwoofers'),)
    for i, (jr, jv, jn, note) in enumerate(conns):
        cx, cy = (299.72 + i * 66.04) if ref == 'U23' else 279.4, y0 + 104.14
        used_libs.add(('Connector_Generic', 'Conn_01x04'))
        pins = lib_pins('Connector_Generic', 'Conn_01x04')
        add += symbol('Connector_Generic:Conn_01x04', jr, jv,
                      'Connector_Molex:Molex_KK-396_A-41791-0004_1x04_P3.96mm_Vertical', cx, cy, list(pins),
                      'KK-396 4-pin header, Molex 41791-0004 (LCSC C10379)', rpos=(cx - 2.54, cy - 6.35),
                      vpos=(cx - 2.54, cy + 8.89))
        for n, net in zip(('1', '2', '3', '4'), jn):
            px, py, a = pins[n]
            sx, sy = cx + px, cy - py
            add += wire((sx, sy), (sx - 7.62, sy)) + label(net, sx - 7.62, sy, 180)
        add += text(note, cx - 20.32, cy + 10.16, 1.4)

# PDN, I2C pull-ups (shared)
x0, y0 = 20.32, 30.48
add += rect(15.24, 152.4, 144.78, 195.58) + text('Amplifier control: RP2354B I2C1 (GPIO38 SDA / GPIO39 SCL), PDN (GPIO36)', 16.51, 153.67)
add += text('AMP_PDN low (100k pull-down, RP2354B at reset): both amplifiers off.\\nThe RP2354B raises AMP_PDN, '
            'then loads the PPC3 configuration over I2C\\n(mode, 768 kHz switching, crossover, limiter): '
            'no sound without firmware.', 16.51, 160.02, 1.4)
add += two('Device', 'R', R(), '4.7k', FP['R'], 106.68, 170.18, '+3V3', 'AMP_SDA', D_R['4.7k'])
add += two('Device', 'R', R(), '4.7k', FP['R'], 121.92, 170.18, '+3V3', 'AMP_SCL', D_R['4.7k'])
add += two('Device', 'R', R(), '100k', FP['R'], 137.16, 180.34, 'AMP_PDN', 'GND', D_R['100k'])

# ---------------------------------------------------------------- I2S source select
add += rect(15.24, 30.48, 144.78, 149.86) + text('I2S source: Pi / J28 when J30 is empty, line-in ADC when a plug is in', 16.51, 31.75)
MX, MY = 76.2, 88.9
add += ic('74xx', '74LS157', 'U26', '74HC157', 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm', MX, MY,
          {'1': 'LINE_DET', '15': 'GND', '2': 'I2S_BCK', '3': 'ADC_BCK', '5': 'I2S_LRCK', '6': 'ADC_LRCK',
           '11': 'I2S_DIN', '10': 'ADC_DOUT', '14': 'GND', '13': 'GND', '4': 'MUX_BCK', '7': 'MUX_LRCK',
           '9': 'MUX_DIN', '12': 'NC', '8': 'GND', '16': '+3V3'},
          'Quad 2:1 multiplexer 2-6 V, 74HC157D,653 SOIC-16 (LCSC C5609)',
          'https://assets.nexperia.com/documents/data-sheet/74HC_HCT157.pdf', stub=5.08,
          rpos=(MX + 5.08, MY - 26.67), vpos=(MX + 5.08, MY + 29.21),
          stubs={'2': 20.32, '5': 20.32, '11': 20.32, '1': 20.32})
add += two('Device', 'C', C(), '100n', FP['0805'], 104.14, 50.8, '+3V3', 'GND', D_100N)
for i, (a, b) in enumerate((('MUX_BCK', 'AMP_SCLK'), ('MUX_LRCK', 'AMP_LRCLK'), ('MUX_DIN', 'AMP_SDIN'))):
    add += two('Device', 'R', R(), '33', FP['R'], 109.22 + i * 10.16, 99.06, a, b, D_R['33'])
add += text('S low (A inputs): Pi.  S high: ADC.  33 R series at the outputs.', 16.51, 139.7, 1.4)

# ---------------------------------------------------------------- line-in ADC
AX, AY = 63.5, 233.68
add += rect(15.24, 198.12, 144.78, 279.4)
add += text('Line-in ADC: PCM1808 master 256 fs (12.288 MHz -> 48 kHz, BCK 64 fs), I2S', 16.51, 199.39)
add += ic('sam_cpu', 'PCM1808', 'U22', 'PCM1808', 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm', AX, AY,
          {'13': 'ADC_INL', '14': 'ADC_INR', '1': 'ADC_VREF', '6': 'ADC_SCKI', '8': 'ADC_BCK', '7': 'ADC_LRCK',
           '9': 'ADC_DOUT', '12': 'GND', '10': '+3V3', '11': '+3V3', '3': 'ADC_VCC', '4': '+3V3', '2': 'GND', '5': 'GND'},
          'Stereo audio ADC 24 bit, PCM1808PWR TSSOP-14 (LCSC C55513)', 'https://www.ti.com/lit/ds/symlink/pcm1808.pdf',
          stub=5.08, rpos=(AX + 5.08, AY - 21.59), vpos=(AX + 5.08, AY + 24.13), stubs={'10': 10.16, '11': 15.24, '4': 10.16})
used_libs.add(('sam_cpu', 'PCM1808'))
# supplies: +5V -> FB4 -> ADC_VCC; decoupling row at the bottom
used_libs.add(('Device', 'FerriteBead_Small'))
add += two('Device', 'FerriteBead_Small', 'FB4', '600R', FP['FB'], 22.86, 213.36, '+5V', 'ADC_VCC',
           'Ferrite bead 600 R at 100 MHz 500 mA 0805, GZ2012D601TF (LCSC C1017)')
add += wire((45.72, 213.36), (40.64, 213.36)) + label('ADC_VCC', 40.64, 213.36, 180) + flag(45.72, 213.36)
for k, (val, top, d_) in enumerate((('10u', 'ADC_VCC', D_10U), ('100n', 'ADC_VCC', D_100N), ('10u', '+3V3', D_10U),
                                    ('100n', '+3V3', D_100N), ('10u', 'ADC_VREF', D_10U), ('100n', 'ADC_VREF', D_100N))):
    xy = (20.32 + 10.16 * k, 264.16) if k < 4 else (20.32 + 10.16 * (k - 4), 241.3)
    add += two('Device', 'C', C(), val, FP['0805'], xy[0], xy[1], top, 'GND', d_)
# oscillator
used_libs.add(('Oscillator', 'ASE-xxxMHz'))
add += ic('Oscillator', 'ASE-xxxMHz', 'Y2', '12.288MHz', 'Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm',
          104.14, 213.36, {'1': '+3V3', '2': 'GND', '3': 'ADC_SCKI', '4': '+3V3'},
          'Oscillator 12.288 MHz CMOS 1.8-3.3 V 3225, YXC OT2EL4C4JI-111OLP-12.288M (LCSC C5203546)', stub=2.54,
          rpos=(109.22, 205.74), vpos=(109.22, 222.25))
add += two('Device', 'C', C(), '100n', FP['0805'], 129.54, 213.36, '+3V3', 'GND', D_100N)
# inputs: J30 tip / ring -> 10k -> node (10k to GND, 470 pF) -> 4.7 uF -> VINL / VINR
for i, (src, node, pin) in enumerate((('LINEIN_L', 'LIN_L_DIV', 'ADC_INL'), ('LINEIN_R', 'LIN_R_DIV', 'ADC_INR'))):
    bx = 99.06 + i * 22.86
    add += two('Device', 'R', R(), '10k', FP['R'], bx, 241.3, src, node, D_R['10k'])
    add += two('Device', 'C', C(), '4.7u', FP['0805'], bx + 6.35, 241.3, node, pin, D_4U7)
    add += two('Device', 'R', R(), '10k', FP['R'], bx + 12.7, 264.16, node, 'GND', D_R['10k'])
    add += two('Device', 'C', C(), '470p', FP['0805'], bx + 19.05, 264.16, node, 'GND', D_470P)
add += two('Device', 'R', R(), '220k', FP['R'], 142.24, 213.36, '+3V3', 'LINE_DET', D_R['220k'])
add += text('Divider 10k / 10k: 2 Vrms in -> 0.92 Vrms (full scale 1.06 Vrms).  J30 TN = LINE_DET:\\n'
            'low through 20k without a plug, high (220k) with a plug.', 16.51, 274.32, 1.3)

# ---------------------------------------------------------------- write the sheet
p = os.path.join(d, 'audio.kicad_sch'); s = open(p).read()
head_end = s.index('\t(lib_symbols')
head = s[:head_end]
head = head.replace('(title "Audio: PCM5102A, TDA7297 stereo + subwoofer (+12 V)")',
                    '(title "Audio: TAS5805M stereo + subwoofer (I2S + DSP), line-in ADC (+12 V)")')
libs = sorted(used_libs) + [('power', n) for n in ('GND', '+12V', '+3V3', '+5V', 'PWR_FLAG')]
lib_section = '\t(lib_symbols\n' + '\n'.join(embed_text(l, n) for l, n in libs) + '\n\t)\n'
tail_i = s.rindex('\t(sheet_instances') if '\t(sheet_instances' in s else None
tail = s[tail_i:] if tail_i else ')\n'
body = add
body += text('Digital audio chain: I2S (Pi on J21 / J28, or the PCM1808 line-in ADC) -> 74HC157 source select -> '
             'two TAS5805M with DSP (EQ, subwoofer crossover, limiter), +12 V, no heatsink.\\n'
             'TAS5805M speaker outputs are bridged: no speaker wire may go to ground.', 15.24, 20.32, 1.6)
s = head + lib_section + body + tail
open(p, 'w').write(s)

# ---------------------------------------------------------------- rs485_i2s sheet: J30
p = os.path.join(d, 'rs485_i2s.kicad_sch'); s = open(p).read()
s = replace_once(s, '(global_label "AUD_AMP_L"', '(global_label "LINEIN_L"')
s = replace_once(s, '(global_label "AUD_AMP_R"', '(global_label "LINEIN_R"')
s = replace_once(s, '(global_label "AUD_DAC_L"', '(global_label "LINE_DET"')
m = re.search(r'\n\t\(global_label "AUD_DAC_R"\n\t\t\(shape \w+\)\n\t\t\(at ([-\d.]+) ([-\d.]+) \d+\)', s)
gx, gy = float(m.group(1)), float(m.group(2))
s = s[:m.start()] + s[block(s, m.start() + 2):]
# the wire that ends on that label: remove it and put a no-connect on the J30 RN pin end
wm = None
for w in re.finditer(r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)', s):
    a = (float(w.group(1)), float(w.group(2))); b = (float(w.group(3)), float(w.group(4)))
    if (gx, gy) in (a, b): wm = (w, a if b == (gx, gy) else b)
assert wm, 'RN wire'
w, other = wm
s = s[:w.start()] + s[block(s, w.start() + 2):]
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + no_connect(*other) + s[k:]
s = s.replace('J30: line-in (e.g. Pi 4 headphone out). No plug: DAC -> amplifiers through the jack contacts. Plug in: DAC cut off.',
              'J30: line-in for a host without I2S (mini PC). Tip / ring -> PCM1808 ADC (audio sheet); TN = LINE_DET: '
              'a plug selects the ADC as I2S source.')
open(p, 'w').write(s)

# ---------------------------------------------------------------- mcu sheet: U4 pins 44 / 45 / 47 / 48
p = os.path.join(d, 'mcu.kicad_sch'); s = open(p).read()
s = replace_once(s, '(global_label "AMP_MUTE"', '(global_label "AMP_SCL"')
add = ''
for y, net, shape in ((195.58, 'AMP_SDA', 'bidirectional'), (190.5, 'AMP_PDN', 'output'), (187.96, 'LINE_DET', 'input')):
    m = re.search(r'\n\t\(no_connect\n\t\t\(at 208.28 %s\)' % re.escape(fmt(y)), s)
    assert m, y
    s = s[:m.start()] + s[block(s, m.start() + 2):]
    add += wire((208.28, y), (213.36, y)) + glabel(net, 213.36, y, 0, shape)
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + add + s[k:]
open(p, 'w').write(s)

# ---------------------------------------------------------------- root sheet text
p = os.path.join(d, 'sam_cpu.kicad_sch'); s = open(p).read()
s = s.replace('(text "Audio: PCM5102A, TDA7297 stereo + subwoofer (+12 V)"',
              '(text "Audio: TAS5805M stereo + subwoofer, line-in ADC (+12 V)"')
open(p, 'w').write(s)
print('ok, caps left from', cref[0], 'resistors left', rref)

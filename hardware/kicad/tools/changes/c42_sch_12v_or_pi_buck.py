"""c42 (schematic): +12 V rail from two sources, a 5.1 V buck for the Pi, and a 5 V jumper on the Pi header.
+12 V rail: J23 (external, EXT_12V) and J11 pin 6 (IO board J16, unregulated, IO_12V) feed 12V_OR through two LTC4412
ideal-diode controllers U33 / U34 with DMP3013SFV P-FETs Q19 / Q20 (30 V, 9.5 mOhm, PowerDI3333-8), then F1 (4 A hold, now
the rail fuse) feeds +12V with the D5 clamp as before. The FETs block J23 reverse polarity. External has priority: R213 / R214 (47k / 10k) drive the CTL of the IO controller U34 above 0.9 V whenever
EXT_12V is above about 5 V, which turns Q20 off. U33 CTL is grounded (always on). STAT pins are not used.
Pi buck: U35 TPS54302 (4.5-28 V, 3 A, 400 kHz) from +12V, R215 / R216 (100k / 13k) set 5.18 V on PI_5V_BUCK,
L2 10 uH FXL0630, C133 / C134 10 uF 25 V in, C135 / C136 22 uF 16 V out, C137 boot. EN is left open (internal pull-up).
Solder jumpers (open by default) feed PI_5V (J21 pins 2 / 4): JP4 from the buck, JP3 from the board +5 V (JP3 sits on the
+5 V trunk to J21), both open for a Jetson or a Pi powered by its own USB-C. The +5V power symbol on J21 (mcu sheet) becomes a PI_5V global label.
Usage: c42_sch_12v_or_pi_buck.py project_dir"""
import os, re, sys, uuid
d = sys.argv[1]
SYM = os.environ.get('KICAD10_SYMBOL_DIR', '/opt/k10/root/usr/share/kicad/symbols')
PATH_POWER = '/2aea4fdf-a573-57d0-a5af-7bd6ce737647/febff99c-25e7-5ff2-ad94-91f07160e16c'


def U(): return str(uuid.uuid4())
def fmt(v): return ('%.2f' % v).rstrip('0').rstrip('.')


def block(s, i):
    n = 0
    for j in range(i, len(s)):
        if s[j] == '(': n += 1
        elif s[j] == ')':
            n -= 1
            if n == 0: return j + 1


def find_symbol(s, ref):
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]+"\)', s):
        j = block(s, m.start() + 2)
        if '(reference "%s")' % ref in s[m.start():j]:
            return m.start(), j
    raise SystemExit('no ' + ref)


def drop_symbol(s, ref):
    a, b = find_symbol(s, ref)
    return s[:a] + s[b:]


def drop_item(s, kind, x, y):
    m = re.search(r'\n\t\(%s\n\t\t\(at %s %s\)' % (kind, re.escape(fmt(x)), re.escape(fmt(y))), s)
    assert m, (kind, x, y)
    return s[:m.start()] + s[block(s, m.start() + 2):]


def embed(s, lib, name):
    full = '%s:%s' % (lib, name)
    if '(symbol "%s"' % full in s: return s
    L = open(os.path.join(SYM, lib + '.kicad_sym')).read()
    i = L.index('\t(symbol "%s"' % name); j = block(L, i + 1)
    sym = L[i:j].replace('(symbol "%s"' % name, '(symbol "%s"' % full, 1)
    sym = re.sub(r'\(size 1\.27 1\.27\)', '(size 1.5 1.5)', sym)
    sym = '\n'.join('\t' + l for l in sym.split('\n'))
    k = s.index('\t(lib_symbols') + len('\t(lib_symbols')
    return s[:k] + '\n' + sym + s[k:]


def prop(name, val, x, y, hide=False, just=None, ang=0):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s %d)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.6 1.6)\n\t\t\t\t)\n%s\t\t\t)\n\t\t)\n') % (
        name, val, fmt(x), fmt(y), ang, '\t\t\t(hide yes)\n' if hide else '',
        '\t\t\t\t(justify %s)\n' % just if just else '')


def symbol(lib_id, ref, val, fp, x, y, rot=0, npins=2, desc='', ds='', rpos=None, vpos=None, power=False,
           path=PATH_POWER, fang=0, just='left'):
    rx, ry = rpos or (x + 2.54, y - 1.27)
    vx, vy = vpos or (x + 2.54, y + 1.27)
    t = ('\t(symbol\n\t\t(lib_id "%s")\n\t\t(at %s %s %d)\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
         '\t\t(in_bom %s)\n\t\t(on_board %s)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n') % (
        lib_id, fmt(x), fmt(y), rot, 'no' if power else 'yes', 'no' if power else 'yes', U())
    t += prop('Reference', ref, rx, ry, hide=power, just=None if power else just, ang=fang)
    t += prop('Value', val, vx, vy, just=None if power else just, ang=fang)
    t += prop('Footprint', fp, x, y, True) + prop('Datasheet', ds, x, y, True) + prop('Description', desc, x, y, True)
    for n in range(1, npins + 1): t += '\t\t(pin "%d"\n\t\t\t(uuid "%s")\n\t\t)\n' % (n, U())
    t += ('\t\t(instances\n\t\t\t(project "sam_cpu"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n'
          '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n') % (path, ref)
    return t


def wire(*pts):
    t = ''
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t += ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n'
              '\t\t)\n\t\t(uuid "%s")\n\t)\n') % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), U())
    return t


def label(name, x, y, ang, just):
    return ('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.6 1.6)\n\t\t\t)\n'
            '\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (name, fmt(x), fmt(y), ang, just, U())


def glabel(name, x, y, ang):
    just = 'right' if ang in (180, 270) else 'left'
    return ('\t(global_label "%s"\n\t\t(shape passive)\n\t\t(at %s %s %d)\n\t\t(fields_autoplaced yes)\n\t\t(effects\n'
            '\t\t\t(font\n\t\t\t\t(size 1.6 1.6)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n\t\t(uuid "%s")\n'
            '\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %s %s 0)\n\t\t\t(hide yes)\n'
            '\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.6 1.6)\n'
            '\t\t\t\t)\n\t\t\t\t(justify %s)\n\t\t\t)\n\t\t)\n\t)\n') % (name, fmt(x), fmt(y), ang, just, U(), fmt(x),
                                                                    fmt(y), just)


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


def replace_once(s, old, new):
    assert s.count(old) == 1, old[:80]
    return s.replace(old, new)


pw = [1100]
def PWR(lib_id, x, y, rot=0):
    pw[0] += 1
    name = lib_id.split(':')[1]
    desc = ('Special symbol for telling ERC where power comes from' if name == 'PWR_FLAG'
            else 'Power symbol creates a global label with name \\"%s\\"' % name)
    ref = ('#FLG%d' if name == 'PWR_FLAG' else '#PWR0%d') % pw[0]
    vy = y + (2.54 if (name in ('GND', 'PWR_FLAG')) != (rot == 180) else -3.81)
    if name == 'PWR_FLAG': vy = y - 3.81 if rot == 0 else y + 3.81
    return symbol(lib_id, ref, name, '', x, y, rot, 1, desc, rpos=(x, y), vpos=(x, vy), power=True)


C_FP, R_FP = 'Capacitor_SMD:C_%s', 'Resistor_SMD:R_0603_1608Metric'

# ---------------------------------------------------------------- power sheet
p = os.path.join(d, 'power.kicad_sch'); s = open(p).read()
for w in ((30.48, 177.8, 50.8, 177.8), (50.8, 177.8, 50.8, 175.26), (50.8, 175.26, 52.07, 175.26)):   # J23 - F1
    m = re.search(r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s %s\) \(xy %s %s\)' % tuple(re.escape(fmt(v)) for v in w), s)
    assert m, w
    s = s[:m.start()] + s[block(s, m.start() + 2):]
s = drop_item(s, 'no_connect', 30.48, 149.86)    # J11 pin 6 (+12 V from the IO board) is now used
for lib, name in (('Power_Management', 'LTC4412xS6'), ('Transistor_FET', 'DMP3013SFV'),
                  ('Regulator_Switching', 'TPS54302'), ('Jumper', 'SolderJumper_2_Open'), ('Device', 'L')):
    s = embed(s, lib, name)

add = wire((30.48, 177.8), (40.64, 177.8)) + label('EXT_12V', 40.64, 177.8, 0, 'left')         # J23 pin 1
add += wire((52.07, 175.26), (46.99, 175.26)) + label('12V_OR', 46.99, 175.26, 180, 'right')    # F1 input
add += wire((30.48, 149.86), (30.48, 156.21), (40.64, 156.21)) + label('IO_12V', 40.64, 156.21, 0, 'left')

# +12 V OR: external path (U33 / Q19) at x 325, IO path (U34 / Q20) at x 376
add += rect(292.1, 116.84, 406.4, 165.1)
add += text("+12 V OR (12V_OR to F1): J23 external (priority) or J11 pin 6 (IO board)", 293.37, 118.11)
LT = 'https://www.analog.com/media/en/technical-documentation/data-sheets/4412fb.pdf'
for (x, inp, u, q, ctl_gnd) in ((325.12, 'EXT_12V', 'U33', 'Q19', True), (375.92, 'IO_12V', 'U34', 'Q20', False)):
    y = 132.08                              # FET, rotated 90: D left (x - 5.08), S right (x + 5.08), G below
    add += symbol('Transistor_FET:DMP3013SFV', q, 'DMP3013SFV', 'Package_SON:Diodes_PowerDI3333-8', x, y, 90, 5,
                  'P-MOSFET -30 V -12 A 9.5 mOhm, DMP3013SFV-TP (LCSC C49452326) or DMP3013SFV-7 (C264098)',
                  'https://www.diodes.com/assets/Datasheets/DMP3013SFV.pdf', rpos=(x, y - 8.89),
                  vpos=(x, y - 6.35), fang=90, just=None)
    uy = 147.32                             # LTC4412: GATE (top) lands on the FET gate
    add += symbol('Power_Management:LTC4412xS6', u, 'LTC4412', 'Package_TO_SOT_SMD:TSOT-23-6', x, uy, 0, 6,
                  'Ideal diode controller 2.5-28 V, LTC4412ES6#TRPBF (LCSC C514442)', LT,
                  rpos=(x + 2.54, uy - 7.62), vpos=(x + 2.54, uy + 7.62))
    add += wire((x - 20.32, 129.54), (x - 15.24, 129.54), (x - 5.08, 129.54)) + label(inp, x - 20.32, 129.54, 180, 'right')
    add += PWR('power:PWR_FLAG', x - 15.24, 129.54, 0)
    add += wire((x - 10.16, 144.78), (x - 10.16, 129.54)) + junction(x - 10.16, 129.54)        # VIN
    add += wire((x + 10.16, 144.78), (x + 10.16, 129.54)) + junction(x + 10.16, 129.54)        # SENSE
    add += wire((x + 5.08, 129.54), (x + 12.7, 129.54)) + label('12V_OR', x + 12.7, 129.54, 0, 'left')
    add += no_connect(x + 10.16, 149.86) + PWR('power:GND', x, 157.48)                         # STAT, GND
    if ctl_gnd:
        add += wire((x - 10.16, 149.86), (x - 12.7, 149.86), (x - 12.7, 152.4)) + PWR('power:GND', x - 12.7, 152.4)
    else:                                   # CTL = EXT_12V x 10k / 57k: IO path off while J23 is powered
        cx = x - 20.32
        add += wire((x - 10.16, 149.86), (cx, 149.86)) + junction(cx, 149.86)
        add += symbol('Device:R', 'R213', '47k', R_FP, cx, 146.05, 0, 2, 'Resistor', rpos=(cx + 1.27, 144.78),
                      vpos=(cx + 1.27, 147.32))
        add += symbol('Device:R', 'R214', '10k', R_FP, cx, 153.67, 0, 2, 'Resistor', rpos=(cx + 1.27, 152.4),
                      vpos=(cx + 1.27, 154.94))
        add += wire((cx, 142.24), (cx, 139.7), (cx - 2.54, 139.7)) + label('EXT_12V', cx - 2.54, 139.7, 180, 'right')
        add += PWR('power:GND', cx, 157.48)

# Pi buck and JP3
add += rect(292.1, 170.18, 406.4, 248.92)
add += text('Pi 5.1 V buck (3 A) and Pi header 5 V jumpers JP3 / JP4', 293.37, 171.45)
add += text('JP3 / JP4 (open by default) feed J21 pins 2 / 4 (PI_5V):\\nJP4: from the buck (Pi 4 / Pi 5, 5.18 V 3 A)\\n'
            'JP3: from the board +5 V\\nboth open: Jetson, or a Pi on its own USB-C. Never bridge both.', 293.37, 222.25, 1.5)
X, Y = 330.2, 203.2                         # U35: VIN (320.04, 200.66), EN (320.04, 205.74), GND (330.2, 210.82),
add += symbol('Regulator_Switching:TPS54302', 'U35', 'TPS54302', 'Package_TO_SOT_SMD:SOT-23-6', X, Y, 0, 6,
              # SW (340.36, 203.2), FB (340.36, 205.74), BOOT (340.36, 200.66)
              'Buck 4.5-28 V 3 A 400 kHz, TPS54302DDCR (LCSC C311983)',
              'https://www.ti.com/lit/ds/symlink/tps54302.pdf', rpos=(X - 2.54, Y - 8.89), vpos=(X + 2.54, Y + 8.89))
add += PWR('power:+12V', 297.18, 200.66) + wire((297.18, 200.66), (320.04, 200.66))
for i, cx in enumerate((302.26, 312.42)):
    add += junction(cx, 200.66)
    add += symbol('Device:C', 'C%d' % (133 + i), '10u', C_FP % '1206_3216Metric', cx, 204.47, 0, 2,
                  'Unpolarized capacitor, 25 V X7R 1206 (LCSC C14860)', rpos=(cx + 1.27, 203.2), vpos=(cx + 1.27, 205.74))
    add += PWR('power:GND', cx, 208.28)
add += no_connect(320.04, 205.74) + PWR('power:GND', 330.2, 210.82)
add += symbol('Device:C', 'C137', '100n', C_FP % '0603_1608Metric', 347.98, 196.85, 0, 2,
              'Unpolarized capacitor, 50 V', rpos=(349.25, 195.58), vpos=(349.25, 198.12))
add += wire((340.36, 200.66), (342.9, 200.66), (342.9, 193.04), (347.98, 193.04))       # BOOT
add += wire((347.98, 200.66), (347.98, 203.2)) + junction(347.98, 203.2)
add += wire((340.36, 203.2), (355.6, 203.2))                                              # SW
add += symbol('Device:L', 'L2', '10u', 'Inductor_SMD:L_Changjiang_FXL0630', 359.41, 203.2, 90, 2,
              'Inductor 10 uH, FXL0630-100-M 7 x 6.6 x 3 mm (LCSC C167223)', rpos=(359.41, 198.12),
              vpos=(359.41, 200.66), fang=90, just=None)
add += wire((363.22, 203.2), (401.32, 203.2)) + label('PI_5V_BUCK', 383.54, 203.2, 0, 'left')
add += symbol('Device:R', 'R215', '100k', R_FP, 368.3, 207.01, 0, 2, 'Resistor', rpos=(369.57, 205.74),
              vpos=(369.57, 208.28))
add += symbol('Device:R', 'R216', '13k', R_FP, 368.3, 214.63, 0, 2, 'Resistor', rpos=(369.57, 213.36),
              vpos=(369.57, 215.9))
add += junction(368.3, 203.2) + junction(368.3, 210.82) + PWR('power:GND', 368.3, 218.44)
add += wire((340.36, 205.74), (342.9, 205.74), (342.9, 210.82), (368.3, 210.82))         # FB
for i, cx in enumerate((378.46, 388.62)):
    add += junction(cx, 203.2)
    add += symbol('Device:C', 'C%d' % (135 + i), '22u', C_FP % '1206_3216Metric', cx, 207.01, 0, 2,
                  'Unpolarized capacitor, 16 V X5R 1206 (LCSC C77088)', rpos=(cx + 1.27, 205.74), vpos=(cx + 1.27, 208.28))
    add += PWR('power:GND', cx, 210.82)
JPFP = 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm'
add += symbol('Jumper:SolderJumper_2_Open', 'JP4', 'BUCK', JPFP, 401.32, 220.98, 90, 2,
              'Pi header 5 V from the buck (open by default)', rpos=(395.0, 215.9), vpos=(395.0, 218.44),
              fang=90, just=None)
add += wire((401.32, 203.2), (401.32, 215.9))                                             # JP4 B: buck
add += wire((401.32, 226.06), (401.32, 231.14), (396.24, 231.14)) + junction(396.24, 231.14)
add += symbol('Jumper:SolderJumper_2_Open', 'JP3', 'BOARD', JPFP, 391.16, 228.6, 0, 2,
              'Pi header 5 V from the board +5 V (open by default)', rpos=(391.16, 222.25), vpos=(391.16, 224.79),
              just=None)
add += wire((386.08, 228.6), (381.0, 228.6)) + PWR('power:+5V', 381.0, 228.6)           # JP3 A: board +5 V
add += wire((396.24, 228.6), (396.24, 238.76)) + glabel('PI_5V', 396.24, 238.76, 270)     # PI_5V: J21 pins 2 / 4
add += wire((396.24, 236.22), (386.08, 236.22)) + junction(396.24, 236.22) + PWR('power:PWR_FLAG', 386.08, 236.22, 180)

k = s.rstrip().rindex('\n)') + 1
s = s[:k] + add + s[k:]

s = replace_once(s, 'J11 keeps the original CPU board connector (IO board J16 harness) for +5 V and ground only: its +-12 V pins are not used.\\n'
                 'The audio amplifiers run from an external +12 V supply on J23 (about 3 A at full volume). F1 + D5 blow the fuse on reverse polarity.',
                 'J11 keeps the original CPU board connector (IO board J16 harness): +5 V, ground and +12 V (pin 6, unregulated); -12 V (pin 3) is not used.\\n'
                 'The +12 V rail (audio amplifiers, Pi buck) comes from J23 (external, priority) or J11 pin 6 through ideal diodes U33 / U34 (they block reverse polarity), then F1 (4 A hold) and the D5 clamp.')
s = replace_once(s, '(text "External +12 V for audio (J23)"', '(text "External +12 V (J23) and rail fuse F1"')
s = replace_once(s, '(text "IO board power (J11, +5 V only)"', '(text "IO board power (J11: +5 V, +12 V on pin 6)"')
s = replace_once(s, 'Power: +5 V mux, external +12 V, 3.3 V, 4.5 V, monitors', 'Power: +5 V mux, +12 V OR, Pi buck, 3.3 V, 4.5 V, monitors')
open(p, 'w').write(s)

# ---------------------------------------------------------------- mcu sheet: J21 pins 2 / 4 on PI_5V
p = os.path.join(d, 'mcu.kicad_sch'); s = open(p).read()
a, b = find_symbol(s, '#PWR02056')
assert '(lib_id "power:+5V")' in s[a:b] and '(at 330.2 132.08 0)' in s[a:b]
s = s[:a] + s[b:]
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + glabel('PI_5V', 330.2, 132.08, 90) + s[k:]
open(p, 'w').write(s)
print('ok')

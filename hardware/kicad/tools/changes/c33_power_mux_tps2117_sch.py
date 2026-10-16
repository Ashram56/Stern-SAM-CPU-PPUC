"""c33 (schematic): power mux U1/U2 + Q1/Q2 (two LTC4412 ideal-diode controllers with AO3401A; the only stocked
LTC4412 is a TOKMAS clone, 77 pcs) -> one TI TPS2117DRLR (C22399676), Vincent's card choice "TPS2117".
TPS2117: 2:1 power mux, 1.6-5.5 V, 4 A, 20 mOhm, SOT-583-8 (KiCad symbol TPS2116DRL: same pinout, 2.5 A part).
Priority mode: MODE tied to VIN1, VIN1 = external +5 V (J17, net EXT_5V), VIN2 = J11 +5 V after JP1 (net J11_5V).
PR1 = R1/R2 divider of VIN1 (100k / 33k): VIN1 is used while it is above about 4 V (PR1 reference 1 V), else VIN2.
ST (open drain) is not used. The +5V PWR_FLAG goes (VOUT is a power output). U1 takes the old U1 place; U2, Q1, Q2 and their wiring go.
Usage: c33_power_mux_tps2117_sch.py project_dir"""
import os, re, sys, uuid
d = sys.argv[1]
p = os.path.join(d, 'power.kicad_sch'); s = open(p).read()
LIB = os.path.join(os.environ.get('KICAD10_SYMBOL_DIR', '/opt/kicad10/root/usr/share/kicad/symbols'), 'Power_Management.kicad_sym')

def U(): return str(uuid.uuid4())

def block(s, i):
    n = 0
    for j in range(i, len(s)):
        if s[j] == '(': n += 1
        elif s[j] == ')':
            n -= 1
            if n == 0: return j + 1

def drop(s, i):
    """remove the top-level item starting at i (a tab-indented line) including its line break"""
    j = block(s, i)
    return s[:i - 1] + s[j:]          # i - 1: the tab before '('

def drop_symbol(s, ref):
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]+"\)', s):
        j = block(s, m.start() + 2)
        if '(property "Reference" "%s"' % ref in s[m.start():j]:
            return s[:m.start()] + s[j:]
    raise SystemExit('no ' + ref)

for ref in ('U1', 'U2', 'Q1', 'Q2', '#PWR01004', '#PWR01010', '#PWR01006', '#PWR01011', '#PWR01012',
            '#FLG3', '#PWR01045'):        # +5V PWR_FLAG stub: U1 VOUT now drives +5V
    s = drop_symbol(s, ref)

WIRES = [(111.76, 53.34, 116.84, 53.34), (127.0, 53.34, 129.54, 53.34), (111.76, 76.2, 111.76, 53.34),
         (121.92, 60.96, 121.92, 68.58), (111.76, 81.28, 109.22, 81.28), (121.92, 88.9, 121.92, 91.44),
         (121.92, 132.08, 121.92, 139.7), (111.76, 147.32, 111.76, 124.46), (111.76, 124.46, 116.84, 124.46),
         (127.0, 124.46, 129.54, 124.46), (132.08, 147.32, 134.62, 147.32), (121.92, 160.02, 121.92, 162.56),
         (111.76, 152.4, 101.6, 152.4), (101.6, 152.4, 101.6, 99.06), (177.8, 203.2, 177.8, 200.66)]
def fmt(v): return ('%.2f' % v).rstrip('0').rstrip('.')
for w in WIRES:
    m = re.search(r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s %s\) \(xy %s %s\)' % tuple(re.escape(fmt(v)) for v in w), s)
    assert m, w
    s = s[:m.start()] + s[block(s, m.start() + 2):]
for kind, x, y in (('junction', 111.76, 76.2), ('junction', 111.76, 147.32), ('no_connect', 132.08, 152.4),
                   ('no_connect', 132.08, 81.28)):
    m = re.search(r'\n\t\(%s\n\t\t\(at %s %s\)' % (kind, re.escape(fmt(x)), re.escape(fmt(y))), s)
    assert m, (kind, x, y)
    s = s[:m.start()] + s[block(s, m.start() + 2):]
assert '(lib_id "Power_Management:LTC4412xS6")' not in s and '(lib_id "Transistor_FET:AO3401A")' not in s

# library symbol
L = open(LIB).read()
i = L.index('\t(symbol "TPS2116DRL"'); j = block(L, i + 1)
sym = L[i:j].replace('(symbol "TPS2116DRL"', '(symbol "Power_Management:TPS2116DRL"', 1)
sym = re.sub(r'\(size 1\.27 1\.27\)', '(size 1.5 1.5)', sym)
sym = '\n'.join('\t' + l for l in sym.split('\n'))
for name in ('Power_Management:LTC4412xS6', 'Transistor_FET:AO3401A'):
    m = re.search(r'\n\t\t\(symbol "%s"' % re.escape(name), s)
    s = s[:m.start()] + s[block(s, m.start() + 3):]
k = s.index('\t(lib_symbols') + len('\t(lib_symbols')
s = s[:k] + '\n' + sym + s[k:]

# new U1 (VIN1 pin lands on the old U1 VIN pin, VOUT on the old SENSE pin)
X, Y = 121.92, 81.28
def prop(name, val, x, y, hide=False):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.6 1.6)\n\t\t\t\t)\n%s\t\t\t)\n\t\t)\n') % (
        name, val, fmt(x), fmt(y), '\t\t\t(hide yes)\n' if hide else '', '' if hide else '')
u1 = ('\t(symbol\n\t\t(lib_id "Power_Management:TPS2116DRL")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n'
      '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n'
      '\t\t(uuid "7a70cda5-241d-51f4-879c-205266f69d32")\n' % (fmt(X), fmt(Y)))
u1 += prop('Reference', 'U1', X - 7.62, Y - 10.16) + prop('Value', 'TPS2117', X + 3.81, Y - 10.16)
u1 += prop('Footprint', 'Package_TO_SOT_SMD:SOT-583-8', X, Y + 15.24, True)
u1 += prop('Datasheet', 'https://www.ti.com/lit/ds/symlink/tps2117.pdf', X, Y + 17.78, True)
u1 += prop('Description', '2:1 power mux with priority, 1.6-5.5 V, 4 A, 20 mOhm, TPS2117DRLR (LCSC C22399676)', X, Y, True)
for n in range(1, 9): u1 += '\t\t(pin "%d"\n\t\t\t(uuid "%s")\n\t\t)\n' % (n, U())
u1 += ('\t\t(instances\n\t\t\t(project "sam_cpu"\n\t\t\t\t(path "/2aea4fdf-a573-57d0-a5af-7bd6ce737647/febff99c-25e7-5ff2-ad94-'
       '91f07160e16c"\n\t\t\t\t\t(reference "U1")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')

def wire(x1, y1, x2, y2):
    return ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n'
            '\t\t)\n\t\t(uuid "%s")\n\t)\n') % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), U())
def label(name, x, y, ang, just):
    return ('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.6 1.6)\n\t\t\t)\n'
            '\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (name, fmt(x), fmt(y), ang, just, U())
add = wire(101.6, 99.06, 101.6, 78.74) + wire(101.6, 78.74, 111.76, 78.74)          # PR1 from R1 / R2
add += wire(111.76, 83.82, 106.68, 83.82) + label('EXT_5V', 106.68, 83.82, 180, 'right')  # MODE = VIN1
add += label('EXT_5V', 83.82, 68.58, 0, 'left')
add += wire(111.76, 86.36, 106.68, 86.36) + label('J11_5V', 106.68, 86.36, 180, 'right')
add += label('J11_5V', 111.76, 147.32, 0, 'left')
add += '\t(no_connect\n\t\t(at 132.08 86.36)\n\t\t(uuid "%s")\n\t)\n' % U()
k = s.rstrip().rindex('\n)') + 1                    # before the file's closing parenthesis
s = s[:k] + add + u1 + s[k:]
# R2 100k -> 33k: VIN1 is dropped below about 4 V
m = re.search(r'\(property "Reference" "R2"', s); a = s.rfind('\n\t(symbol\n', 0, m.start()); b = block(s, a + 2)
r2 = s[a:b]; assert r2.count('(property "Value" "100k"') == 1
s = s[:a] + r2.replace('(property "Value" "100k"', '(property "Value" "33k"') + s[b:]
# R1 is 0402 on the board (it fits between F1 and the EXT_5V track beside U1, c34)
m = re.search(r'\(property "Reference" "R1"', s); a = s.rfind('\n\t(symbol\n', 0, m.start()); b = block(s, a + 2)
r1 = s[a:b]; assert r1.count('"Resistor_SMD:R_0603_1608Metric"') == 1
s = s[:a] + r1.replace('"Resistor_SMD:R_0603_1608Metric"', '"Resistor_SMD:R_0402_1005Metric"') + s[b:]
# sheet note
OLD = 'External +5 V on J17 has priority: U2 turns the J11 path off whenever +5V_EXT is present (EXT_PRESENT high).\\nLTC4412 + AO3401A ideal diodes stand in for the TPS2121 of ARCHITECTURE.md 9.3 (library part, about 4 A per path).'
NEW = 'External +5 V on J17 has priority: U1 TPS2117 (2:1 mux, 4 A) takes VIN1 while R1 / R2 hold PR1 above 1 V (VIN1 above about 4 V), else J11 on VIN2.\\nThe TPS2117 replaces the TPS2121 of ARCHITECTURE.md 9.3 (JLCPCB stock); the KiCad TPS2116DRL symbol has the same pinout.'
assert s.count(OLD) == 1; s = s.replace(OLD, NEW)
open(p, 'w').write(s)
print('ok')

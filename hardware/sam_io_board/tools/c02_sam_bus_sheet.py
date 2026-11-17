"""Change 02 (2026-10-07): create sam_bus.kicad_sch from the CPU board's IO bus sheet
(hardware/kicad/sam_cpu/io_bus.kicad_sch, PR #4 branch), so both ends of the SAM bus use the
same circuit: SN74LVC8T245 on D0-D7, 74AHCT541 on A0-A3 and IOSTB, 2N7002 open-drain NBRESET,
33 R series resistors, J9 2x10 header with the IO board J1 pinout. Only references, the J9
value, the notes and the instance paths change. Also numbers the root sheet's power symbols.
Usage: c02_sam_bus_sheet.py <io_bus.kicad_sch> <sam_io dir>"""
import re, sys, uuid
import sx

src, d = sys.argv[1], sys.argv[2]
root_path = f'{d}/sam_io.kicad_sch'
root = open(root_path).read()
ROOT = re.search(r'\(uuid "([^"]+)"\)', root).group(1)
SHEET = next(re.search(r'\(uuid "([^"]+)"\)', root[a:b]).group(1)
             for h, a, b in sx.items(root) if h == 'sheet' and sx.prop(root[a:b], 'Sheetname') == 'SAM bus')

# CPU board reference -> SAM_IO reference (U6, R23-R26 are taken on the root sheet)
REF = {'U6': 'U7', 'U7': 'U8', 'R23': 'R27', 'R24': 'R28', 'R25': 'R29', 'R26': 'R30', 'Q3': 'Q1',
       'TP10': 'TP3', 'TP11': 'TP4', 'TP12': 'TP5', 'TP13': 'TP6'}
t = open(src).read()
pwr = iter(range(301, 400))
def fix_symbol(s):
    ref = sx.prop(s, 'Reference')
    new = f'#PWR0{next(pwr)}' if ref.startswith('#PWR') else REF.get(ref, ref)
    s = s.replace(f'(property "Reference" "{ref}"', f'(property "Reference" "{new}"')
    s = s.replace(f'(reference "{ref}")', f'(reference "{new}")')
    s = re.sub(r'\(project "sam_cpu"\s*\(path "[^"]+"', f'(project "sam_io"\n\t\t\t\t(path "/{ROOT}/{SHEET}"', s)
    if new == 'J9':
        s = s.replace('(property "Value" "J9 IO BUS"', '(property "Value" "SAM BUS"')
    return s
out = []; last = 0
for h, a, b in sx.items(t):
    if h == 'symbol':
        out.append(t[last:a]); out.append(fix_symbol(t[a:b])); last = b
out.append(t[last:]); t = ''.join(out)
t = re.sub(r'\(uuid "[^"]+"\)', f'(uuid "{uuid.uuid4()}")', t, count=1)
t = re.sub(r'\(title_block.*?\n\t\)', '''(title_block
		(title "SAM bus: J9 to the SAM IO power driver board J1")
		(date "2026-10-07")
		(rev "0.1")
	)''', t, count=1, flags=re.S)
old_note = re.search(r'\(text "ARCHITECTURE\.md[^"]*"', t).group(0)
t = t.replace(old_note, '(text "Copy of the SAM CPU replacement board IO bus sheet (Stern-SAM-CPU-PPUC hardware/kicad, ARCHITECTURE.md 3.1-3.2).\\n'
              'J9 has the SAM IO board J1 pinout, pin for pin: a straight 20-way ribbon connects the two.\\n'
              'GPIOs from io-boards src/IODevices/SamBus/SamBusPins.h: D0-D7 GPIO3-10, A0-A3 GPIO11-14, IOSTB 15, DIR 16, OE_N 17, NBRESET_DRV 18.\\n'
              'Both buffers are off at power-up (BUS_OE_N pulled high) and NBRESET is held low until the firmware releases it.\\n'
              '33 R series resistors on the J9 side for the ribbon cable. Unused 74AHCT541 inputs tied low."')
open(f'{d}/sam_bus.kicad_sch', 'w').write(t)

# number the root sheet's power symbols (the KiCad 6 file kept their numbers in symbol_instances)
n = iter(range(101, 300)); out = []; last = 0
for h, a, b in sx.items(root):
    s = root[a:b]
    if h == 'symbol' and (sx.prop(s, 'Reference') or '').startswith('#PWR'):
        ref = sx.prop(s, 'Reference'); new = f'#PWR0{next(n)}'
        s = s.replace(f'(property "Reference" "{ref}"', f'(property "Reference" "{new}"').replace(
            f'(reference "{ref}")', f'(reference "{new}")')
    out.append(root[last:a]); out.append(s); last = b
out.append(root[last:]); open(root_path, 'w').write(''.join(out))

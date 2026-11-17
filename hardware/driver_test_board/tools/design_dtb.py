"""SAM driver output test board (banc de test des sorties driver), schematic draft 0.1.

Plugs onto the output connectors of the Stern I/O Power Driver board 520-5249-00 (J6-J10, J12, J13, J2, J3)
instead of the playfield harness, and onto the switch inputs of the CPU board (J1, J2, J3, J6, J12, J13).
Every output sees a light load (47 k / 22 k + LED) to its own rail, is divided down and sampled by
7 x 74HC165 read by an RP2354B PIO; the CPU board switch inputs are driven by 2N7002 from 5 x 74HCT595.
USB to the PC is isolated (ADuM3160 + 1 W DC/DC).

Pinouts: IO board schematic 520-5249-00 Rev A (Indiana Jones manual p.106-113), coil table of the same
manual, CPU board PR #12 (Ashram56/Stern-SAM-CPU-PPUC). Run build_dtb.py.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from kigen import Part, Design

D = Design('driver_test_board', 'SAM driver output test board', '0.1', 'Stern SAM CPU PPUC (CERN-OHL-S v2)', '2026-11-17')
SHEETS = []

_cnt = collections.Counter({'U': 9})   # U1-U5 are given by hand
def nref(p):
    _cnt[p] += 1
    return f'{p}{_cnt[p]}'

FP = {
    'R': 'Resistor_SMD:R_0805_2012Metric', 'C': 'Capacitor_SMD:C_0805_2012Metric',
    'C1206': 'Capacitor_SMD:C_1206_3216Metric', 'LED': 'LED_SMD:LED_0805_2012Metric',
    'SOT23': 'Package_TO_SOT_SMD:SOT-23', 'SO16': 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    'BTN': 'Button_Switch_SMD:SW_SPST_TL3342',
}
def kk396(n): return f'Connector_Molex:Molex_KK-396_A-41791-{n:04d}_1x{n:02d}_P3.96mm_Vertical'

def R(v, a, b, rot=0, mpn=None):
    return Part(nref('R'), 'Device:R', v, {'1': a, '2': b}, FP['R'], rotation=rot)
def C(v, a, b='GND', fp=None):
    return Part(nref('C'), 'Device:C', v, {'1': a, '2': b}, fp or FP['C'])
def LED(a, k, color='red'):
    return Part(nref('D'), 'Device:LED', color, {'2': a, '1': k}, FP['LED'], rotation=90)
def conn(ref, n, nets, value):
    full = {str(i): nets.get(i, 'NC') for i in range(1, n + 1)}
    return Part(ref, f'Connector_Generic:Conn_01x{n:02d}', value, full, kk396(n))
def flag(net):
    return Part(nref('#FLG'), 'power:PWR_FLAG', 'PWR_FLAG', {'1': net}, '')
def TP(net):
    return Part(nref('TP'), 'Connector:TestPoint', net, {'1': net}, 'TestPoint:TestPoint_Pad_D1.5mm')

def sheet(name, fn, title, comments=()):
    s = D.sheet(name, fn, title, comments=comments)
    SHEETS.append(s)
    return s

def row(sheet, title, parts, dx=12.7):
    """one block, parts side by side"""
    b = sheet.block(title)
    for i, p in enumerate(parts):
        b.place(p, i * dx, 0)
    return b

def stack(sheet, title, part, extras=(), ex=30.48):
    """big part at origin, extras in a column to its right"""
    b = sheet.block(title)
    b.place(part, 0, 0)
    for i, p in enumerate(extras):
        b.place(p, ex + (i % 2) * 12.7, -20 + (i // 2) * 12.7)
    return b

# ---------------------------------------------------------------------------------------------------------
# Channel definitions
# ---------------------------------------------------------------------------------------------------------
# IO board connectors (driver side). Coil numbers and pins: IJ manual coil table; TIP122 for 17-32.
J8_PINS = {1: 1, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9}            # coil -> pin (key 2)
J9_PINS = {9: 1, 10: 2, 11: 4, 12: 5, 13: 6, 14: 7, 15: 8, 16: 9}     # key 3
J7_PINS = {17: 2, 18: 3, 19: 4, 20: 6, 21: 7, 22: 8, 23: 9, 24: 10}   # +20 V on 1, key 5
J6_PINS = {25 + i: 1 + i for i in range(8)}                             # +20 V on 10, key 9
J12_STB = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11]                              # Q33-Q42, key 7, GND 12
J13_COL = [1, 3, 4, 5, 6, 7, 8]                                         # + pin 10 (via JP2), +18 V on 9, key 2

coil_rail = {**{c: ('V50', '47k') for c in range(1, 17)},
             **{c: ('V20S', '22k') for c in range(17, 25)},
             **{c: ('V20F', '22k') for c in range(25, 33)}}

# 74HC165 chains: chain k -> 8 sense nets D0..D7 (None = spare, tied to GND)
CH = []
CH.append([f'S_COIL{c}' for c in range(1, 9)])
CH.append([f'S_COIL{c}' for c in range(9, 17)])
CH.append([f'S_COIL{c}' for c in range(17, 25)])
CH.append([f'S_COIL{c}' for c in range(25, 33)])
CH.append([f'S_LSTB{p}' for p in J12_STB[:8]])
CH.append([f'S_LSTB{p}' for p in J12_STB[8:]] + [f'S_LCOL{p}' for p in J13_COL[:6]])
CH.append([f'S_LCOL{J13_COL[6]}', 'S_LCOLX'] + [None] * 6)

# CPU board switch inputs
CPU_J1_STB = [1, 3, 4, 5, 6, 7, 8, 9]                    # strobes, key 2
CPU_J6_RET = [9, 8, 7, 6, 5, 3, 2, 1]                    # Return 1..8 (pin 9 = Return 1), key 4, GND 10
CPU_J12_RET = [9, 8, 7, 6, 4, 3, 2, 1]                   # Return 9..16, key 5, GND 10
CPU_J2_DED = [2, 3, 4, 6, 7, 8, 9, 10]                   # D-1..D-8, GND 1/11, key 5, 12 TAMPIN (NC)
CPU_J3_DED = [1, 2, 4, 5, 6, 7, 8, 9]                    # D-9..D-16, key 3, GND 10
CPU_J13_DED = [1, 3, 4, 5, 6, 7, 8, 9]                   # D-17..D-24, key 2, GND 10

# RP2354B GPIO map
GP = {}
for k in range(7): GP[k] = f'SR_Q{k}'
GP.update({7: 'SR_CLK_MCU', 8: 'SR_PL_N'})
AUX = ['AUXO_P1', 'AUXO_P2', 'AUXO_P3', 'AUXO_P5', 'AUXO_P6', 'AUXO_P7', 'AUXO_P8', 'AUXO_P9', 'AUXO_P10',
       'AUXS_P9', 'AUXS_P10', 'AUXS_P11', 'AUXS_P12']
for i, n in enumerate(AUX): GP[9 + i] = 'G_' + n
for i, p in enumerate(CPU_J1_STB): GP[22 + i] = f'G_CSTB{i + 1}'
GP.update({30: 'SER_RET', 31: 'SER_DED', 32: 'SRCLK', 33: 'RCLK', 34: 'SR_OE_N', 35: 'SR_CLR_N', 36: 'LED_STATUS',
           40: 'ADC_V50', 41: 'ADC_V20S', 42: 'ADC_V20F', 43: 'ADC_V18L'})
SPARE_GP = [37, 38, 39, 44, 45, 46, 47]
for g in SPARE_GP: GP[g] = f'GP{g}'

ROOT_NOTES = ('SAM driver output test board, schematic draft 0.1 (2026-11-17). Licence: CERN-OHL-S v2.\n'
              'Replaces the playfield harness on the I/O Power Driver board 520-5249-00 (J6-J10, J12, J13, J2, J3) and the switch\n'
              'harness on the CPU board (J1, J2, J3, J6, J12, J13). Every output sees < 1 mA: a stuck-on output cannot burn anything.\n'
              'The 50 V and 20 V rails MUST be on during tests: each output has a 1N4004 flyback diode to its rail on the driver board.\n'
              'Board ground = pinball ground (J10 pins 2-5, IO J12 pin 12, CPU connectors). USB to the PC is isolated (ADuM3160).\n'
              'IO J10 pin 1 carries 24 VAC: it is not connected on this board.')

# ---------------------------------------------------------------------------------------------------------
# Sheet: power and isolated USB
# ---------------------------------------------------------------------------------------------------------
S = sheet('Power and USB', 'power_usb.kicad_sch', 'Isolated USB (ADuM3160), 1 W isolated 5 V, 3.3 V', comments=(
    'PC side: USB-C J1 (device, CC 5.1 k), ESD U2, ADuM3160 upstream side powered from VBUS_USB. GND_USB is the PC ground.',
    'Pinball side: PS1 B0505S-1WR3 (1.5 kV) makes +5V; U4 NCP1117-3.3 makes +3V3. GND is the pinball ground.',
    'R3 330 R loads +3V3 permanently (10 mA) to absorb the current injected by the input dividers when 50 V is applied.',
    'ADuM3160: SPU = VDD1 and SPD = VDD2 select full speed (12 Mbit/s, as the RP2354B); PIN = VDD2 enables the upstream pull-up.',
))
row(S, 'USB-C to PC', [
    Part('J1', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C',
         {'S1': 'GND_USB', 'A1': 'GND_USB', 'A12': 'GND_USB', 'B1': 'GND_USB', 'B12': 'GND_USB',
          'A4': 'VBUS_USB', 'A9': 'VBUS_USB', 'B4': 'VBUS_USB', 'B9': 'VBUS_USB', 'A5': 'CC1', 'B5': 'CC2',
          'A7': 'UDM', 'B7': 'UDM', 'A6': 'UDP', 'B6': 'UDP', 'A8': 'NC', 'B8': 'NC'},
         'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12'),
], dx=0)
row(S, 'CC, ESD', [R('5.1k', 'CC1', 'GND_USB'), R('5.1k', 'CC2', 'GND_USB'),
                   Part('U2', 'Power_Protection:USBLC6-2SC6', 'USBLC6-2SC6',
                        {'1': 'UDP', '6': 'UDP', '3': 'UDM', '4': 'UDM', '5': 'VBUS_USB', '2': 'GND_USB'},
                        'Package_TO_SOT_SMD:SOT-23-6'),
                   C('10u', 'VBUS_USB', 'GND_USB'), flag('VBUS_USB'), flag('GND_USB')], dx=17.78)
row(S, 'USB isolator', [
    Part('U3', 'Interface_USB:ADUM3160', 'ADuM3160BRWZ',
         {'1': 'VBUS_USB', '2': 'GND_USB', '8': 'GND_USB', '3': 'VDD1', '4': 'VDD1', '5': 'VDD1', '7': 'UDP', '6': 'UDM',
          '16': '+5V', '9': 'GND', '15': 'GND', '14': 'VDD2', '12': 'VDD2', '13': 'VDD2', '10': 'DDP', '11': 'DDM'},
         'Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm'),
    C('100n', 'VBUS_USB', 'GND_USB'), C('1u', 'VDD1', 'GND_USB'), C('100n', 'VDD1', 'GND_USB'),
    C('100n', '+5V'), C('1u', 'VDD2'), C('100n', 'VDD2'),
    R('27', 'DDP', 'USB_DP_MCU', rot=90), R('27', 'DDM', 'USB_DM_MCU', rot=90), flag('VDD1'), flag('VDD2')], dx=15.24)
row(S, 'Isolated 5 V and 3.3 V', [
    Part('PS1', 'dtb:B0505S', 'B0505S-1WR3', {'2': 'VBUS_USB', '1': 'GND_USB', '4': '+5V', '3': 'GND'}),
    C('10u', '+5V'), C('10u', '+5V'),
    Part('U4', 'Regulator_Linear:NCP1117-3.3_SOT223', 'NCP1117-3.3', {'3': '+5V', '1': 'GND', '2': '+3V3'}),
    C('10u', '+3V3'), C('100n', '+3V3'), R('330', '+3V3', 'GND'),
    R('1k', '+3V3', 'LED_PWR_A'), LED('LED_PWR_A', 'GND', 'green')], dx=17.78)
row(S, 'Ground lug, mounting holes, test points', [
    Part('H1', 'Mechanical:MountingHole_Pad', 'GND lug M3', {'1': 'GND'}, 'MountingHole:MountingHole_3.2mm_M3_Pad_Via'),
    Part('H2', 'Mechanical:MountingHole', 'M3', {}, 'MountingHole:MountingHole_3.2mm_M3'),
    Part('H3', 'Mechanical:MountingHole', 'M3', {}, 'MountingHole:MountingHole_3.2mm_M3'),
    Part('H4', 'Mechanical:MountingHole', 'M3', {}, 'MountingHole:MountingHole_3.2mm_M3'),
    TP('+5V'), TP('+3V3'), TP('GND'), TP('GND_USB')], dx=12.7)

# ---------------------------------------------------------------------------------------------------------
# Sheet: MCU
# ---------------------------------------------------------------------------------------------------------
S = sheet('MCU', 'mcu.kicad_sch', 'RP2354B (2 MB flash in package), crystal, core regulator, SWD', comments=(
    'Same RP2354B block as the CPU board (mcu.kicad_sch, PR #12). PIO0: 74HC165 capture (GPIO0-8) + aux capture (GPIO9-21).',
    'PIO1: CPU strobe watch (GPIO22-29) + 74HCT595 switch outputs (GPIO30-35). ADC: rail monitors GPIO40-43.',
))
fixed = {'VREG_AVDD': 'VREG_AVDD', 'DVDD': '+1V1', 'VREG_FB': '+1V1', 'VREG_LX': 'VREG_LX', 'GND': 'GND',
         'VREG_PGND': 'GND', 'RUN': 'RUN', 'USB_DM': 'USB_DM_MCU', 'USB_DP': 'USB_DP_MCU', '~{QSPI_SS}': 'BOOTSEL',
         'XIN': 'XIN', 'XOUT': 'XOUT', 'SWCLK': 'SWCLK', 'SWDIO': 'SWDIO'}
mcu = Part('U5', 'dtb:RP2354B', 'RP2354B', {}, 'Package_DFN_QFN:QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm')
for p in mcu.sd.pins:
    nm = p['name']
    if nm.startswith('GPIO'): mcu.nets[p['number']] = GP.get(int(nm.split('/')[0][4:]), 'NC')
    elif nm in ('IOVDD', 'QSPI_IOVDD', 'USB_OTP_VDD', 'ADC_AVDD', 'VREG_VIN'): mcu.nets[p['number']] = '+3V3'
    elif nm in fixed: mcu.nets[p['number']] = fixed[nm]
    elif nm.startswith('QSPI'): mcu.nets[p['number']] = 'NC'
    else: raise ValueError(nm)
b = S.block('RP2354B'); b.place(mcu, 0, 0)
row(S, 'Core regulator', [
    Part('L1', 'Device:L', '3.3u', {'1': 'VREG_LX', '2': '+1V1'}, 'Inductor_SMD:L_Cenker_CKCS201610'),
    R('33', '+3V3', 'VREG_AVDD'), C('4.7u', 'VREG_AVDD'), flag('VREG_AVDD'), flag('+1V1'),
    C('4.7u', '+1V1'), C('100n', '+1V1'), C('100n', '+1V1'), C('100n', '+1V1')])
row(S, '3.3 V decoupling', [C('4.7u', '+3V3')] + [C('100n', '+3V3') for _ in range(10)], dx=7.62)
row(S, 'Reset, BOOTSEL, crystal', [
    R('10k', '+3V3', 'RUN'), Part('SW1', 'Switch:SW_Push', 'RESET', {'1': 'RUN', '2': 'GND'}, FP['BTN'], rotation=90),
    R('1k', 'BOOTSEL_BTN', 'BOOTSEL'),
    Part('SW2', 'Switch:SW_Push', 'BOOTSEL', {'1': 'BOOTSEL_BTN', '2': 'GND'}, FP['BTN'], rotation=90),
    Part('Y1', 'Device:Crystal_GND24', '12MHz', {'1': 'XIN', '3': 'XTAL_OUT', '2': 'GND', '4': 'GND'},
         'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', rotation=270),
    R('1k', 'XTAL_OUT', 'XOUT'), C('15p', 'XIN'), C('15p', 'XTAL_OUT')], dx=12.7)
row(S, 'SWD, status LED, spare GPIO', [
    Part('J2', 'Connector_Generic:Conn_01x03', 'SWD', {'1': 'SWCLK', '2': 'GND', '3': 'SWDIO'},
         'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical'),
    R('1k', 'LED_STATUS', 'LED_ST_A'), LED('LED_ST_A', 'GND', 'yellow')] + [TP(f'GP{g}') for g in SPARE_GP], dx=10.16)

# ---------------------------------------------------------------------------------------------------------
# Sheet: coil outputs (IO J8, J9, J7, J6, J10)
# ---------------------------------------------------------------------------------------------------------
S = sheet('Coil outputs', 'coils.kicad_sch', 'Coil and flasher outputs 1-32: light load + LED to the rail, divider to the 74HC165', comments=(
    'Per output: rail -> pull-up (47 k at 50 V: 1 mA, 48 mW; 22 k at 20 V: 0.8 mA) -> LED -> output. LED on = transistor on.',
    'Sense: 220 k / 47 k divider -> 74HC165 (3.3 V). Reads 0 below 5.6 V, 1 above 13 V at the output: TIP122 on (0.8 V) reads 0.',
    'At 60 V the 220 k limits the clamp current to 0.25 mA. Coils 1-16: STP22NE10L MOSFET, 17-32: TIP122 Darlington.',
    'J10 pin 1 = 24 VAC: NOT connected. J10 pins 2-5 = ground reference of the board. J10 pin 6 = +50 V (unfused).',
))
def coil_conn(ref, pins, extra, n, value):
    nets = {p: f'COIL{c}' for c, p in pins.items()}
    nets.update(extra)
    return conn(ref, n, nets, value)
row(S, 'IO board connectors', [
    coil_conn('J3', J8_PINS, {}, 9, 'IO J8 coils 1-8'),
    coil_conn('J4', J9_PINS, {}, 9, 'IO J9 coils 9-16'),
    coil_conn('J5', J7_PINS, {1: 'V20S'}, 10, 'IO J7 coils 17-24'),
    coil_conn('J6', J6_PINS, {10: 'V20F'}, 10, 'IO J6 coils 25-32'),
    conn('J7', 10, {2: 'GND', 3: 'GND', 4: 'GND', 5: 'GND', 6: 'V50'}, 'IO J10 +50 V, GND'),
], dx=20.32)
for c in range(1, 33):
    rail, rv = coil_rail[c]
    row(S, f'Coil {c}', [R(rv, rail, f'LA_COIL{c}'), LED(f'LA_COIL{c}', f'COIL{c}'),
                         R('220k', f'COIL{c}', f'S_COIL{c}'), R('47k', f'S_COIL{c}', 'GND')], dx=20.32)
row(S, 'Rail monitors (100 k / 4.7 k: 73 V full scale)', sum([[R('100k', r, f'ADC_{r}'), R('4.7k', f'ADC_{r}', 'GND'),
    C('100n', f'ADC_{r}')] for r in ('V50', 'V20S', 'V20F')], []) + [TP('V50'), TP('V20S'), TP('V20F')], dx=17.78)

# ---------------------------------------------------------------------------------------------------------
# Sheet: lamp matrix (IO J12, J13)
# ---------------------------------------------------------------------------------------------------------
S = sheet('Lamp matrix', 'lamps.kicad_sch', 'Lamp strobes (IO J12) and lamp columns (IO J13)', comments=(
    'Strobes (STP19NE06L, low side): +18 V -> 22 k -> LED -> strobe, sensed like the coils.',
    'Columns (VN02N high side, 18 V): column -> 10 k -> LED -> GND (1.6 mA, keeps the VN02N out of open-load) + divider.',
    'J13 per the SAM schematic: +18 V on pin 9, columns on 1, 3-8 and 10. JP1/JP2 (bridged 1-2 by default) swap pins 9 and 10',
    'if a board turns out to be wired the other way (Vincent\'s Databus-Analysis table, see ARCHITECTURE.md Q16).',
))
row(S, 'IO board connectors and J13 pin 9/10 swap', [
    conn('J8', 12, {**{p: f'LSTB{p}' for p in J12_STB}, 12: 'GND'}, 'IO J12 lamp strobes'),
    conn('J9', 10, {**{p: f'LCOL{p}' for p in J13_COL}, 9: 'J13P9', 10: 'J13P10'}, 'IO J13 lamp columns'),
    Part('JP1', 'Jumper:SolderJumper_3_Bridged12', '+18V = pin 9', {'1': 'J13P9', '2': 'V18L', '3': 'J13P10'},
         'Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm'),
    Part('JP2', 'Jumper:SolderJumper_3_Bridged12', 'col = pin 10', {'1': 'J13P10', '2': 'LCOLX', '3': 'J13P9'},
         'Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm'),
], dx=20.32)
for p in J12_STB:
    row(S, f'Strobe J12-{p}', [R('22k', 'V18L', f'LA_LSTB{p}'), LED(f'LA_LSTB{p}', f'LSTB{p}'),
                               R('220k', f'LSTB{p}', f'S_LSTB{p}'), R('47k', f'S_LSTB{p}', 'GND')], dx=20.32)
for p in J13_COL + ['X']:
    n = f'LCOL{p}'
    row(S, f'Column J13-{p if p != "X" else "10 (JP2)"}', [R('10k', n, f'LA_{n}'), LED(f'LA_{n}', 'GND', 'yellow'),
                               R('220k', n, f'S_{n}'), R('47k', f'S_{n}', 'GND')], dx=20.32)
row(S, '+18 V monitor', [R('100k', 'V18L', 'ADC_V18L'), R('4.7k', 'ADC_V18L', 'GND'), C('100n', 'ADC_V18L'), TP('V18L')], dx=17.78)

# ---------------------------------------------------------------------------------------------------------
# Sheet: capture (74HC165 x 7)
# ---------------------------------------------------------------------------------------------------------
S = sheet('Capture', 'capture.kicad_sch', '74HC165 x 7: 56 inputs sampled in parallel, 1 sample per microsecond', comments=(
    'All seven 74HC165 share SR_PL_N and SR_CLK; each Q7 goes to its own GPIO (SR_Q0-6), so the PIO reads 7 bits per clock.',
    'Chain 0-3: coils 1-32. Chain 4: J12 strobes 1-6, 8, 9. Chain 5: J12 10, 11 + J13 columns 1, 3-7. Chain 6: J13 8, 10 (JP2) + 6 spares.',
))
DPINS = ['11', '12', '13', '14', '3', '4', '5', '6']
for k, nets in enumerate(CH):
    pn = {'10': 'GND', '1': 'SR_PL_N', '2': 'SR_CLK', '15': 'GND', '16': '+3V3', '8': 'GND', '9': f'SR_Q{k}', '7': 'NC'}
    for i, n in enumerate(nets):
        pn[DPINS[i]] = n if n else 'GND'
    row(S, f'Chain {k}', [Part(nref('U'), '74xx:74HC165', '74HC165', pn, FP['SO16']), C('100n', '+3V3')], dx=20.32)
row(S, 'Clock and load', [R('33', 'SR_CLK_MCU', 'SR_CLK', rot=90), TP('SR_CLK'), TP('SR_PL_N')], dx=15.24)

# ---------------------------------------------------------------------------------------------------------
# Sheet: aux port (IO J2, J3)
# ---------------------------------------------------------------------------------------------------------
S = sheet('Aux port', 'aux.kicad_sch', 'Aux port (IO J2 data + ASTB, IO J3 strobes): 5 V logic, read directly by the PIO', comments=(
    'IO J2: 8 data bits + ASTB on pins 1-3, 5-10 (key 4), 100 R + 470 pF on the IO board. IO J3: strobes on 9-12 (12-pin, key 4).',
    'IO J3 pins 1-8 are AUX_IN inputs of the IO board: left open here. Strobes last 300 ns: GPIO direct, 4.7 k series (5 V tolerant).',
))
row(S, 'IO board connectors', [
    conn('J10', 10, {p: f'AUXO_P{p}' for p in (1, 2, 3, 5, 6, 7, 8, 9, 10)}, 'IO J2 aux out'),
    conn('J11', 12, {p: f'AUXS_P{p}' for p in (9, 10, 11, 12)}, 'IO J3 aux strobes'),
], dx=20.32)
for n in AUX:
    row(S, n, [R('4.7k', n, 'G_' + n, rot=90)], dx=0)

# ---------------------------------------------------------------------------------------------------------
# Sheet: switch simulation (CPU board inputs)
# ---------------------------------------------------------------------------------------------------------
S = sheet('Switch simulation', 'switches.kicad_sch', 'Switch simulation on the CPU board inputs: 8 strobes read, 16 returns + 24 dedicated driven', comments=(
    'Matrix: the PIO watches the 8 strobes of CPU J1 (open collector, pulled up on the CPU board) and, for the active strobe,',
    'pulls the returns of the closed switches to ground (2N7002), within 2 us; the CPU board waits about 125 us per strobe.',
    'Dedicated: 24 x 2N7002 to ground on CPU J2, J3, J13 (switch closed = drain on). TAMPIN (J2 pin 12) left open.',
    '74HCT595 at 5 V (3.3 V inputs are fine for HCT). SR_OE_N is pulled high and every gate has 100 k to ground: all switches',
    'open until the firmware has loaded the registers and pulled SR_OE_N low.',
))
row(S, 'CPU board connectors', [
    conn('J12', 9, {p: f'CSTB_P{p}' for p in CPU_J1_STB}, 'CPU J1 strobes'),
    conn('J13', 10, {**{p: f'RET{i + 1}' for i, p in enumerate(CPU_J6_RET)}, 10: 'GND'}, 'CPU J6 returns 1-8'),
    conn('J14', 10, {**{p: f'RET{i + 9}' for i, p in enumerate(CPU_J12_RET)}, 10: 'GND'}, 'CPU J12 returns 9-16'),
    conn('J15', 12, {**{p: f'DED{i + 1}' for i, p in enumerate(CPU_J2_DED)}, 1: 'GND', 11: 'GND'}, 'CPU J2 D-1..D-8'),
    conn('J16', 10, {**{p: f'DED{i + 9}' for i, p in enumerate(CPU_J3_DED)}, 10: 'GND'}, 'CPU J3 D-9..D-16'),
    conn('J17', 10, {**{p: f'DED{i + 17}' for i, p in enumerate(CPU_J13_DED)}, 10: 'GND'}, 'CPU J13 D-17..D-24'),
], dx=20.32)
for i, p in enumerate(CPU_J1_STB):
    row(S, f'Strobe sense J1-{p}', [R('4.7k', f'CSTB_P{p}', f'G_CSTB{i + 1}', rot=90)], dx=0)
QP = ['15', '1', '2', '3', '4', '5', '6', '7']
def sr595(outs, ser_in, ser_out):
    pn = {'14': ser_in, '11': 'SRCLK', '10': 'SR_CLR_N', '12': 'RCLK', '13': 'SR_OE_N', '16': '+5V', '8': 'GND', '9': ser_out}
    for q, n in zip(QP, outs): pn[q] = n
    return Part(nref('U'), '74xx:74HCT595', '74HCT595', pn, FP['SO16'])
ret = [f'G_RET{i}' for i in range(1, 17)]
ded = [f'G_DED{i}' for i in range(1, 25)]
row(S, 'Return registers (SER_RET)', [sr595(ret[0:8], 'SER_RET', 'SR_RET_1'), C('100n', '+5V'),
                                      sr595(ret[8:16], 'SR_RET_1', 'NC'), C('100n', '+5V')], dx=22.86)
row(S, 'Dedicated registers (SER_DED)', [sr595(ded[0:8], 'SER_DED', 'SR_DED_1'), C('100n', '+5V'),
                                         sr595(ded[8:16], 'SR_DED_1', 'SR_DED_2'), C('100n', '+5V'),
                                         sr595(ded[16:24], 'SR_DED_2', 'NC'), C('100n', '+5V')], dx=22.86)
row(S, 'Register control', [R('10k', '+3V3', 'SR_OE_N'), R('10k', 'SR_CLR_N', 'GND')], dx=10.16)
def sw(gate, drain):
    return [Part(nref('Q'), 'Transistor_FET:2N7002', '2N7002', {'1': gate, '3': drain, '2': 'GND'}, FP['SOT23']),
            R('100k', gate, 'GND')]
for i in range(16):
    row(S, f'Return {i + 1}', sw(f'G_RET{i + 1}', f'RET{i + 1}'), dx=17.78)
for i in range(24):
    row(S, f'D-{i + 1}', sw(f'G_DED{i + 1}', f'DED{i + 1}'), dx=17.78)

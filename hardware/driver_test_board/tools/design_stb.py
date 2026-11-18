"""SAM universal test board (carte de test universelle), 48 channels, schematic draft 0.1 (2026-11-18).

One board design, four copies: coils (IO J8, J9, J7, J6), lamps + aux (IO J12, J13, J2, J3), switch matrix
(CPU J1 strobes, J6 + J12 returns, J2), dedicated switches (CPU J3, J13). Four KK-396 12-pin headers A-D, each pin is a
universal channel:
  - sense: series resistor + pull-down to a 74HC165 input (its input clamp limits the node to 3.3 V); header A also goes
    straight to a GPIO (22 k / 47 k, fast enough for the 300 ns aux strobes);
  - load: 33 k + two antiparallel LEDs to the header common COMx, which a 3-pad solder jumper ties to RAILx (power
    connector J5), to GND, or leaves open (red = output pulls low, green = output drives high);
  - drive: BSS123 (100 V) to ground from a 74HCT595, to simulate a closed switch.
USB to the PC is isolated (ADuM3160 + 1 W DC/DC). Run build_dtb.py design_stb <outdir>.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from kigen import Part, Design

D = Design('sam_test_board', 'SAM universal test board (48 channels)', '0.1', 'Stern SAM CPU PPUC (CERN-OHL-S v2)', '2026-11-18')
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

HEADERS = 'ABCD'
def ch(h, p): return f'{h}{p}'            # channel net = connector pin, e.g. A1 .. D12
CHANNELS = [(h, p) for h in HEADERS for p in range(1, 13)]

# RP2354B GPIO map
GP = {}
for k in range(6): GP[k] = f'SR_Q{k}'
GP.update({6: 'SR_CLK_MCU', 7: 'SR_PL_N'})
for p in range(1, 13): GP[7 + p] = f'S_A{p}'                     # header A direct: GPIO8-19
GP.update({20: 'SER', 21: 'SRCLK', 22: 'RCLK', 23: 'SR_OE_N', 24: 'SR_CLR_N', 25: 'LED_STATUS', 26: 'SYNC_IO',
           27: 'ID0', 28: 'ID1', 40: 'ADC_RA', 41: 'ADC_RB', 42: 'ADC_RC', 43: 'ADC_RD'})
SPARE_GP = [29, 30, 31, 32]
for g in SPARE_GP: GP[g] = f'GP{g}'

ROOT_NOTES = ('SAM universal test board, 48 channels, schematic draft 0.1 (2026-11-18). Licence: CERN-OHL-S v2.\n'
              'Same board x 4: coils / lamps + aux / switch matrix / dedicated switches. Role = ID0/ID1 solder jumpers.\n'
              'Each header pin: sense (to 74HC165, header A also direct to GPIO), 33 k + LEDs to the header common\n'
              '(solder jumper: RAILx from J5, GND or open), BSS123 to ground for switch simulation.\n'
              'Rails on J5 are only the light-load supply: plug the USB first so the 3.3 V rail absorbs the clamp current.\n'
              'Board ground = pinball ground (J5 pins 5-6, H1 lug). USB to the PC is isolated (ADuM3160).')

# ---------------------------------------------------------------------------------------------------------
# Sheet: power and isolated USB
# ---------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------
# Sheet: power and isolated USB
# ---------------------------------------------------------------------------------------------------------
S = sheet('Power and USB', 'power_usb.kicad_sch', 'Isolated USB (ADuM3160), 1 W isolated 5 V, 3.3 V', comments=(
    'PC side: USB-C J1 (device, CC 5.1 k), ESD U2, ADuM3160 upstream side powered from VBUS_USB. GND_USB is the PC ground.',
    'Pinball side: PS1 B0505S-1WR3 (1.5 kV) makes +5V; U4 NCP1117-3.3 makes +3V3. GND is the pinball ground.',
    '3 x 220 R load +3V3 permanently (45 mA) to absorb the current the input dividers inject through the 74HC165 clamps (42 mA max at 50 V).',
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
    R('27', 'DDP', 'USB_DP_MCU', rot=90), R('27', 'DDM', 'USB_DM_MCU', rot=90), flag('VDD1'), flag('VDD2')], dx=20.32)
row(S, 'Isolated 5 V and 3.3 V', [
    Part('PS1', 'dtb:B0505S', 'B0505S-1WR3', {'2': 'VBUS_USB', '1': 'GND_USB', '4': '+5V', '3': 'GND'}),
    C('10u', '+5V'), C('10u', '+5V'),
    Part('U4', 'Regulator_Linear:NCP1117-3.3_SOT223', 'NCP1117-3.3', {'3': '+5V', '1': 'GND', '2': '+3V3'}),
    C('10u', '+3V3'), C('100n', '+3V3'), R('220', '+3V3', 'GND'), R('220', '+3V3', 'GND'), R('220', '+3V3', 'GND'),
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
# ---------------------------------------------------------------------------------------------------------
# Sheet: MCU
# ---------------------------------------------------------------------------------------------------------
S = sheet('MCU', 'mcu.kicad_sch', 'RP2354B (2 MB flash in package), crystal, core regulator, SWD', comments=(
    'Same RP2354B block as the CPU board (mcu.kicad_sch, PR #12). PIO0: 74HC165 capture (GPIO0-7), header A direct (GPIO8-19).',
    'PIO1: 74HCT595 outputs (GPIO20-24). Board role: ID0/ID1 solder jumpers (GPIO27/28). SYNC GPIO26. ADC: rails GPIO40-43.',
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

row(S, 'Board role, sync', [
    Part('JP9', 'Jumper:SolderJumper_2_Open', 'ID0', {'1': 'ID0', '2': 'GND'}, 'Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm'),
    Part('JP10', 'Jumper:SolderJumper_2_Open', 'ID1', {'1': 'ID1', '2': 'GND'}, 'Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm'),
    R('330', 'SYNC_IO', 'SYNC', rot=90), R('10k', '+3V3', 'SYNC', rot=90),
    Part('J11', 'Connector_Generic:Conn_01x02', 'SYNC', {'1': 'SYNC', '2': 'GND'},
         'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical')], dx=20.32)

# ---------------------------------------------------------------------------------------------------------
# Sheets: headers A-D (12 universal channels each)
# ---------------------------------------------------------------------------------------------------------
for h in HEADERS:
    fast = h == 'A'
    S = sheet(f'Header {h}', f'header_{h.lower()}.kicad_sch', f'Header {h}: 12 universal channels' + (' (also direct to GPIO)' if fast else ''), comments=(
        f'Sense: {"22 k / 47 k (5 V -> 3.4 V, 50 V clamps at 2.1 mA)" if fast else "100 k / 220 k (5 V -> 3.4 V, 50 V clamps at 0.46 mA)"} into the 74HC165, whose input clamp holds the node at 3.3 V.',
        f'Load: COM{h} -- 33 k -- red LED -- pin (output pulls low, COM on a rail); green LED back (output drives high, COM on GND).',
        f'JP{HEADERS.index(h) + 1}: COM{h} to RAIL{h} (pads 1-2), to GND (pads 2-3), or open (switch simulation, sense only).',
        'Drive: BSS123 drain on the pin (100 V), gate from the 74HCT595 chain, 100 k pull-down: off until the firmware enables it.',
    ))
    row(S, 'Connector, common', [
        conn(f'J{HEADERS.index(h) + 7}', 12, {p: ch(h, p) for p in range(1, 13)}, f'Header {h}'),
        Part(f'JP{HEADERS.index(h) + 1}', 'Jumper:SolderJumper_3_Open', f'COM{h}', {'1': f'RAIL{h}', '2': f'COM{h}', '3': 'GND'},
             'Jumper:SolderJumper-3_P1.3mm_Open_Pad1.0x1.5mm', rotation=90)], dx=25.4)
    for p in range(1, 13):
        n = ch(h, p)
        row(S, f'{h}{p}', [
            R('33k', f'COM{h}', f'LA_{n}', rot=90),
            LED(f'LA_{n}', n, 'red'), LED(n, f'LA_{n}', 'green'),
            R('22k' if fast else '100k', n, f'S_{n}', rot=90), R('47k' if fast else '220k', f'S_{n}', 'GND', rot=90),
            Part(nref('Q'), 'Transistor_FET:BSS123', 'BSS123', {'1': f'G_{n}', '2': 'GND', '3': n}, FP['SOT23']),
            R('100k', f'G_{n}', 'GND', rot=90)], dx=17.78)

# ---------------------------------------------------------------------------------------------------------
# Sheet: rails, capture and drive registers
# ---------------------------------------------------------------------------------------------------------
S = sheet('Registers', 'registers.kicad_sch', '6 x 74HC165 (capture, 1 sample/us) + 6 x 74HCT595 (BSS123 gates), rail inputs', comments=(
    'Chain k of the 74HC165 reads channels 8k+1 .. 8k+8 in the order A1..A12, B1..B12, C1..C12, D1..D12 (D0 = first).',
    'All 74HC165 share SR_PL_N and SR_CLK, each Q7 has its own GPIO (SR_Q0-5): the PIO reads 6 bits per clock.',
    'The 74HCT595 chain (SER -> U..) drives the gates in the same channel order, first register = channels 1-8.',
    'J5 brings the light-load rails (RAILA-D, up to 50 V) and the pinball ground. Rail monitors: 100 k / 4.7 k to the ADC.',
))
row(S, 'Rail input', [conn('J5', 6, {1: 'RAILA', 2: 'RAILB', 3: 'RAILC', 4: 'RAILD', 5: 'GND', 6: 'GND'}, 'Rails + GND')], dx=0)
for x in HEADERS:
    row(S, f'Rail {x} monitor', [R('100k', f'RAIL{x}', f'ADC_R{x}', rot=90), R('4.7k', f'ADC_R{x}', 'GND', rot=90),
                                 C('100n', f'ADC_R{x}'), TP(f'RAIL{x}')], dx=12.7)
DPINS = ['11', '12', '13', '14', '3', '4', '5', '6']
for k in range(6):
    pn = {'10': 'GND', '1': 'SR_PL_N', '2': 'SR_CLK', '15': 'GND', '16': '+3V3', '8': 'GND', '9': f'SR_Q{k}', '7': 'NC'}
    for i in range(8):
        h, p = CHANNELS[8 * k + i]; pn[DPINS[i]] = f'S_{ch(h, p)}'
    row(S, f'Capture {k}', [Part(nref('U'), '74xx:74HC165', '74HC165', pn, FP['SO16']), C('100n', '+3V3')], dx=33.02)
row(S, 'Capture clock', [R('33', 'SR_CLK_MCU', 'SR_CLK', rot=90), TP('SR_CLK'), TP('SR_PL_N')], dx=12.7)
QP = ['15', '1', '2', '3', '4', '5', '6', '7']
for k in range(6):
    sin = 'SER' if k == 0 else f'SER_{k}'
    pn = {'14': sin, '11': 'SRCLK', '10': 'SR_CLR_N', '12': 'RCLK', '13': 'SR_OE_N', '16': '+5V', '8': 'GND',
          '9': f'SER_{k + 1}' if k < 5 else 'NC'}
    for i in range(8):
        h, p = CHANNELS[8 * k + i]; pn[QP[i]] = f'G_{ch(h, p)}'
    row(S, f'Drive {k}', [Part(nref('U'), '74xx:74HCT595', '74HCT595', pn, FP['SO16']), C('100n', '+5V')], dx=33.02)
row(S, 'Drive control', [R('10k', '+3V3', 'SR_OE_N', rot=90), R('10k', 'SR_CLR_N', 'GND', rot=90)], dx=20.32)

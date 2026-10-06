"""SAM CPU replacement board: first schematic draft, generated from docs/ARCHITECTURE.md.

Run through build.py. After the first commit the .kicad_sch files are the source of truth;
this script only documents how the draft was produced.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from kigen import *

D = Design('sam_cpu', 'SAM CPU replacement board', '0.1', 'Stern SAM CPU PPUC (CERN-OHL-S v2)', '2026-10-06')

# ---------------------------------------------------------------- helpers
_cnt = collections.Counter({'D': 10, 'Q': 10})
def nref(prefix):
    _cnt[prefix] += 1
    return f'{prefix}{_cnt[prefix]}'

FP = {
    'R': 'Resistor_SMD:R_0603_1608Metric',
    'RN': 'Resistor_SMD:R_Array_Convex_4x0603',
    'C': 'Capacitor_SMD:C_0603_1608Metric',
    'C0805': 'Capacitor_SMD:C_0805_2012Metric',
    'CP6': 'Capacitor_SMD:CP_Elec_6.3x7.7',
    'CP8': 'Capacitor_SMD:CP_Elec_8x10',
    'SOD123': 'Diode_SMD:D_SOD-123',
    'SMA': 'Diode_SMD:D_SMA',
    'SMB': 'Diode_SMD:D_SMB',
    'SO14': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    'SO16': 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    'TSSOP20': 'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',
    'TSSOP24': 'Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm',
    'LED': 'LED_SMD:LED_0603_1608Metric',
    'FB': 'Inductor_SMD:L_0805_2012Metric',
    'BTN': 'Button_Switch_SMD:SW_SPST_TL3342',
}
SMALL_C = ('100n', '10n', '1u', '15p', '47p', '2.2n', '220n')
def kk254(n): return f'Connector_Molex:Molex_KK-254_AE-6410-{n:02d}A_1x{n:02d}_P2.54mm_Vertical'
def kk396(n): return f'Connector_Molex:Molex_KK-396_A-41791-{n:04d}_1x{n:02d}_P3.96mm_Vertical'

def R(value, n1, n2, ref=None, fp=None, rot=0):
    return Part(ref or nref('R'), 'Device:R', value, {'1': n1, '2': n2}, fp or FP['R'], rotation=rot)
def C(value, n1, n2, ref=None, fp=None, rot=0, pol=False):
    lib = 'Device:C_Polarized' if pol else 'Device:C'
    if fp is None: fp = FP['C'] if value in SMALL_C else FP['C0805']
    return Part(ref or nref('C'), lib, value, {'1': n1, '2': n2}, fp, rotation=rot)

def hres(b, value, left, right, x, y, fp=None):
    """horizontal resistor, left net / right net."""
    return b.place(R(value, left, right, fp=fp, rot=90), x, y)
def bank(b, rows, x, y, pitch=7.62, fp=None):
    for i, (v, l, r) in enumerate(rows):
        hres(b, v, l, r, x, y + i * pitch, fp=fp)
def vcap(b, value, top, x, y, bot='GND', pol=False, fp=None):
    return b.place(C(value, top, bot, pol=pol, fp=fp), x, y)
def decaps(b, net, values, x, y, dx=7.62):
    for i, v in enumerate(values):
        vcap(b, v, net, x + i * dx, y)
def divider(b, rt, rb, top, mid, bot, x, y, cap=None):
    """vertical divider; the mid node goes right to a label (and an optional cap to GND)."""
    r1 = R(rt, top, mid); b.place(r1, x, y, auto=False)
    b.terminate(r1.pin_pos('1'), 'U', top)
    r2 = R(rb, mid, bot); b.place(r2, x, y + 10.16, auto=False)
    b.terminate(r2.pin_pos('2'), 'D', bot)
    node = (x, round(y + 5.08, 4))
    b.wire(r1.pin_pos('2'), node); b.wire(node, r2.pin_pos('1'))
    end = (x + 10.16, node[1])
    if cap:
        cx = x + 5.08
        b.wire(node, (cx, node[1])); b.wire((cx, node[1]), end)
        c = C(cap, mid, 'GND'); b.place(c, cx, node[1] + 3.81, auto=False)
        b.terminate(c.pin_pos('2'), 'D', 'GND', stub=0)
        b.junction((cx, node[1]))
    else:
        b.wire(node, end)
    b.label(end, mid, 'R'); b.junction(node)
def flag(b, net, x, y):
    return b.place(Part(nref('#FLG'), 'power:PWR_FLAG', 'PWR_FLAG', {'1': net}, ''), x, y)
def generic_conn(ref, n, nets, fp, value=None):
    return Part(ref, f'Connector_Generic:Conn_01x{n:02d}', value or f'Conn_01x{n:02d}',
                {str(k): v for k, v in nets.items()}, fp)

def series_r(b, ic, pin, out, value='33', dx=2.54):
    """horizontal resistor wired straight onto a right-hand IC pin."""
    px, py = ic.pin_pos(pin)
    r = R(value, ic.nets[pin], out, rot=90)
    b.place(r, px + dx + 3.81, py, auto=False)
    b.wire((px, py), r.pin_pos('1'))
    b.terminate(r.pin_pos('2'), 'R', out)
    return r
def series_pack(b, ic, pins, outs, value='33', dx=2.54):
    """4-resistor array on four consecutive right-hand IC pins (top to bottom)."""
    pos = [ic.pin_pos(p) for p in pins]
    x0, y0 = pos[0]
    rn = Part(nref('RN'), 'Device:R_Pack04', value, {}, FP['RN'], rotation=90)
    left, right = ['5', '6', '7', '8'], ['4', '3', '2', '1']
    for k in range(4):
        if k < len(pins) and outs[k] != 'NC':
            rn.nets[left[k]] = ic.nets[pins[k]]; rn.nets[right[k]] = outs[k]
        else:
            rn.nets[left[k]] = 'NC'; rn.nets[right[k]] = 'NC'
    b.place(rn, x0 + dx + 5.08, y0 + 2.54, auto=False)
    for k in range(4):
        if rn.nets[left[k]] == 'NC':
            b.terminate(rn.pin_pos(left[k]), 'L', 'NC'); b.terminate(rn.pin_pos(right[k]), 'R', 'NC')
            if k < len(pins): b.terminate(pos[k], 'R', 'NC')
            continue
        b.wire(pos[k], rn.pin_pos(left[k]))
        b.terminate(rn.pin_pos(right[k]), 'R', outs[k])
    return rn
def led(b, color, src, mid, x, y, ref):
    """src -> 1k -> LED -> GND, horizontal."""
    r = R('1k', src, mid, rot=90); b.place(r, x, y, auto=False)
    b.terminate(r.pin_pos('1'), 'L', src)
    d = Part(ref, 'Device:LED', color, {'2': mid, '1': 'GND'}, FP['LED'], rotation=180)
    b.place(d, x + 12.7, y, auto=False)
    b.wire(r.pin_pos('2'), d.pin_pos('2'))
    b.terminate(d.pin_pos('1'), 'R', 'GND')

# =====================================================================
# Sheet: power
# =====================================================================
S = D.sheet('Power', 'power.kicad_sch', 'Power: +5 V mux (external / J11), 3.3 V, supply monitors', comments=(
    'J11 keeps the original CPU board pinout (IO board J16 harness): +5 V, +-12 V and ground.',
    'External +5 V on J17 has priority: U2 turns the J11 path off whenever +5V_EXT is present (EXT_PRESENT high).',
    'LTC4412 + AO3401A ideal diodes stand in for the TPS2121 of ARCHITECTURE.md 9.3 (library part, about 4 A per path).',
    'JP1 (bridged by default) disconnects the J11 +5 V completely; leaving J17 unplugged forces J11.',
))
b = S.block('J11: power from the IO board (J16 harness)')
b.place(generic_conn('J11', 6, {1: '+5V_J11_IN', 2: 'GND', 3: '-12V_IN', 4: 'GND', 5: 'GND', 6: '+12V_IN'}, kk396(6), 'J11 POWER'), 0, 0)
for i, (v, l, r) in enumerate([('FB 3A', '+5V_J11_IN', '+5V_J11_F'), ('FB 1A', '+12V_IN', '+12V'), ('FB 1A', '-12V_IN', '-12V')]):
    b.place(Part(f'FB{i + 1}', 'Device:FerriteBead_Small', v, {'1': l, '2': r}, FP['FB'], rotation=90), 22.86, -5.08 + i * 7.62)
b.place(Part('JP1', 'Jumper:SolderJumper_2_Bridged', 'J11 5V', {'1': '+5V_J11_F', '2': '+5V_J11'},
             'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm'), 22.86, 17.78)
vcap(b, '47u', '+12V', 50.8, 0, pol=True, fp=FP['CP6'])
vcap(b, '47u', 'GND', 60.96, 0, bot='-12V', pol=True, fp=FP['CP6'])
for i, n in enumerate(['+12V', '-12V', 'GND', '+5V_J11_IN', '+12V_IN', '-12V_IN']):
    flag(b, n, 50.8 + (i % 3) * 12.7, 17.78 + (i // 3) * 12.7)

b = S.block('J17: external +5 V (priority)')
b.place(Part('J17', 'Connector:Screw_Terminal_01x02', 'EXT 5V', {'1': '+5V_EXT', '2': 'GND'},
             'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'), 0, 0)
b.place(Part('D1', 'Device:D_TVS', 'SMBJ5.0CA', {'1': '+5V_EXT', '2': 'GND'}, FP['SMB']), 25.4, 0)
vcap(b, '100u', '+5V_EXT', 22.86, 12.7, pol=True, fp=FP['CP8'])
flag(b, '+5V_EXT', 38.1, 12.7)

b = S.block('Ideal-diode power mux')
b.place(Part('U1', 'Power_Management:LTC4412xS6', 'LTC4412', {'1': '+5V_EXT', '3': 'GND', '5': 'GATE_EXT', '2': 'GND', '6': '+5V', '4': 'NC'}), 0, 0)
b.place(Part('Q1', 'Transistor_FET:AO3401A', 'AO3401A', {'1': 'GATE_EXT', '3': '+5V_EXT', '2': '+5V'}), 38.1, 0)
b.place(Part('U2', 'Power_Management:LTC4412xS6', 'LTC4412', {'1': '+5V_J11', '3': 'EXT_PRESENT', '5': 'GATE_J11', '2': 'GND', '6': '+5V', '4': 'NC'}), 0, 35.56)
b.place(Part('Q2', 'Transistor_FET:AO3401A', 'AO3401A', {'1': 'GATE_J11', '3': '+5V_J11', '2': '+5V'}), 38.1, 35.56)
divider(b, '100k', '100k', '+5V_EXT', 'EXT_PRESENT', 'GND', 63.5, 25.4)
vcap(b, '100u', '+5V', 63.5, 0, pol=True, fp=FP['CP8'])
vcap(b, '10u', '+5V', 73.66, 0)
flag(b, '+5V', 83.82, 0); flag(b, '+5V_J11', 83.82, 12.7)

b = S.block('3.3 V regulator')
b.place(Part('U3', 'Regulator_Linear:AMS1117-3.3', 'AMS1117-3.3', {'3': '+5V', '1': 'GND', '2': '+3V3'}), 0, 0)
vcap(b, '10u', '+5V', -20.32, 12.7)
vcap(b, '22u', '+3V3', 20.32, 12.7)
led(b, 'green', '+3V3', 'LED_PWR', -10.16, 30.48, 'D2')
b = S.block('Supply monitors (RP2354B ADC)')
divider(b, '10k', '10k', '+5V', 'VMON_5V', 'GND', 0, 0, cap='100n')
divider(b, '33k', '10k', '+12V', 'VMON_12V', 'GND', 33.02, 0, cap='100n')

# =====================================================================
# Sheet: MCU
# =====================================================================
S = D.sheet('MCU', 'mcu.kicad_sch', 'RP2354B SAM IO controller', comments=(
    'GPIO map follows ARCHITECTURE.md 9.2: PIO0 bus on GPIO0-15, PIO1 switch chain on GPIO16-20, PIO2 DMD on GPIO21-27.',
    'GPIO31 reads the coin door memory protect input (J2 pin 10), which the doc does not list yet.',
    'Core supply from the internal switching regulator: VREG_LX -> L1 -> DVDD (1.1 V), VREG_AVDD through 33 R / 4.7 uF.',
    'Check these values against the RP2350 hardware design guide before layout.',
))
gp = {i: f'BUS_D{i}' for i in range(8)}
gp.update({8 + i: f'BUS_A{i}' for i in range(4)})
gp.update({12: 'BUS_IOSTB', 13: 'BUS_DIR', 14: 'NBRESET_DRV', 15: 'BUS_OE_N',
           16: 'SW_CLK', 17: 'SW_LOAD_N', 18: 'SW_DATA', 19: 'STB_DATA', 20: 'STB_LATCH',
           21: 'DMD_DE', 22: 'DMD_ROWDATA', 23: 'DMD_ROWCLK', 24: 'DMD_COLLATCH_A', 25: 'DMD_PIXCLK',
           26: 'DMD_SDATA', 27: 'DMD_COLLATCH_B', 28: 'FRAME_MOSI', 29: 'FRAME_CS_N', 30: 'FRAME_SCK',
           31: 'MEM_PROTECT', 32: 'RP_UART_TX', 33: 'RP_UART_RX', 34: 'RP_IRQ_N', 35: 'GI_PWM', 36: 'GI_SPARE',
           40: 'VMON_5V', 41: 'VMON_12V', 42: 'LED_STATUS'})
sd = SymDef.get('MCU_RaspberryPi:RP2354B')
nets = {}
fixed = {'VREG_AVDD': 'VREG_AVDD', 'DVDD': '+1V1', 'VREG_FB': '+1V1', 'VREG_LX': 'VREG_LX', 'GND': 'GND',
         'VREG_PGND': 'GND', 'RUN': 'RUN', 'USB_DM': 'USB_DM_MCU', 'USB_DP': 'USB_DP_MCU', '~{QSPI_SS}': 'BOOTSEL',
         'XIN': 'XIN', 'XOUT': 'XOUT', 'SWCLK': 'SWCLK', 'SWDIO': 'SWDIO'}
for p in sd.pins:
    nm = p['name']
    if nm.startswith('GPIO'): nets[p['number']] = gp.get(int(nm.split('/')[0][4:]), 'NC')
    elif nm in ('IOVDD', 'QSPI_IOVDD', 'USB_OTP_VDD', 'ADC_AVDD', 'VREG_VIN'): nets[p['number']] = '+3V3'
    elif nm in fixed: nets[p['number']] = fixed[nm]
    elif nm.startswith('QSPI'): nets[p['number']] = 'NC'
    else: raise ValueError(nm)
b = S.block('RP2354B (2 MB flash in the package)')
b.place(Part('U4', 'MCU_RaspberryPi:RP2354B', 'RP2354B', nets), 0, 0)

b = S.block('Decoupling and core regulator')
decaps(b, '+3V3', ['100n'] * 8, 0, 0)
decaps(b, '+3V3', ['4.7u', '100n', '100n', '100n'], 0, 22.86)
hres(b, '33', '+3V3', 'VREG_AVDD', 38.1, 22.86)
vcap(b, '4.7u', 'VREG_AVDD', 55.88, 30.48)
b.place(Part('L1', 'Device:L', '3.3u', {'1': 'VREG_LX', '2': '+1V1'}, 'Inductor_SMD:L_Cenker_CKCS201610', rotation=90), 43.18, 45.72)
decaps(b, '+1V1', ['4.7u', '100n', '100n', '100n'], 0, 45.72)
flag(b, '+1V1', 63.5, 45.72); flag(b, 'VREG_AVDD', 71.12, 30.48)

b = S.block('12 MHz crystal')
b.place(Part('Y1', 'Device:Crystal_GND24', '12MHz', {'1': 'XIN', '3': 'XTAL_OUT', '2': 'GND', '4': 'GND'},
             'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm'), 0, 0)
hres(b, '1k', 'XOUT', 'XTAL_OUT', 30.48, 0)
vcap(b, '15p', 'XIN', 0, 15.24)
vcap(b, '15p', 'XTAL_OUT', 22.86, 15.24)

b = S.block('Reset supervisor, RESET and BOOTSEL')
b.place(Part('U5', 'Power_Supervisor:TPS3808DBV', 'TPS3808G33', {'5': '+3V3', '3': 'MR_N', '4': 'NC', '6': '+3V3', '2': 'GND', '1': 'RUN'}), 0, 0)
hres(b, '10k', 'RUN', '+3V3', 30.48, 10.16)
b.place(Part('SW1', 'Switch:SW_Push', 'RESET', {'1': 'MR_N', '2': 'GND'}, FP['BTN']), 0, 22.86)
b.place(Part('SW2', 'Switch:SW_Push', 'BOOTSEL', {'1': 'BOOTSEL_BTN', '2': 'GND'}, FP['BTN']), 0, 33.02)
hres(b, '1k', 'BOOTSEL', 'BOOTSEL_BTN', 30.48, 33.02)

b = S.block('USB to the Pi (CDC link + firmware update)')
b.place(Part('J19', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C (to Pi)',
             {'S1': 'GND', 'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'A4': 'VBUS_PI', 'A9': 'VBUS_PI',
              'B4': 'VBUS_PI', 'B9': 'VBUS_PI', 'A5': 'CC1', 'B5': 'CC2', 'A7': 'USB_DM', 'B7': 'USB_DM',
              'A6': 'USB_DP', 'B6': 'USB_DP', 'A8': 'NC', 'B8': 'NC'},
             'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12'), 0, 0)
bank(b, [('100k', 'VBUS_PI', 'GND'), ('5.1k', 'CC1', 'GND'), ('5.1k', 'CC2', 'GND'),
         ('27', 'USB_DM', 'USB_DM_MCU'), ('27', 'USB_DP', 'USB_DP_MCU')], 50.8, -12.7)

b = S.block('SWD header and status LED')
b.place(generic_conn('J20', 3, {1: 'SWCLK', 2: 'GND', 3: 'SWDIO'}, 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical', 'SWD'), 0, 0)
led(b, 'yellow', 'LED_STATUS', 'LED_STATUS_A', -5.08, 15.24, 'D3')

# =====================================================================
# Sheet: Raspberry Pi
# =====================================================================
S = D.sheet('Raspberry Pi', 'pi.kicad_sch', 'Raspberry Pi 4 / CM4 40-pin header', comments=(
    'Only GPIOs a CM4 has on the same numbers (ARCHITECTURE.md 9.1). The Pi 3V3 pins stay unconnected.',
    'The Pi is powered from the board +5 V through pins 2 and 4: never plug the Pi USB-C supply at the same time.',
    'Link: UART0 (GPIO14/15), SPI0 for DMD frames, I2S to the DAC, RUN / BOOTSEL / SWD to the RP2354B, IRQ back.',
))
pi = Part('J21', 'Connector:Raspberry_Pi_2_3', 'Raspberry Pi 40-pin', {}, 'Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical')
pimap = {'8': 'PI_TXD', '10': 'PI_RXD', '19': 'FRAME_MOSI', '23': 'FRAME_SCK', '24': 'FRAME_CS_N',
         '12': 'I2S_BCK', '35': 'I2S_LRCK', '40': 'I2S_DIN', '15': 'PI_RUN', '13': 'PI_BOOTSEL',
         '18': 'SWCLK', '22': 'SWDIO', '16': 'RP_IRQ_N'}
for p in pi.sd.pins:
    n = p['number']
    pi.nets[n] = {'5V': '+5V', 'GND': 'GND', '3V3': 'NC'}.get(p['name'], pimap.get(n, 'NC'))
b = S.block('Pi header')
b.place(pi, 0, 0)
b = S.block('Pi to RP2354B link')
bank(b, [('33', 'PI_TXD', 'RP_UART_RX'), ('33', 'PI_RXD', 'RP_UART_TX'), ('1k', 'PI_RUN', 'MR_N'),
         ('1k', 'PI_BOOTSEL', 'BOOTSEL'), ('10k', 'RP_IRQ_N', '+3V3')], 0, 0)

# =====================================================================
# Sheet: IO bus (J9 to the IO power driver board J1)
# =====================================================================
S = D.sheet('IO bus', 'io_bus.kicad_sch', 'J9: bus to the IO power driver board (IO board J1)', comments=(
    'ARCHITECTURE.md 3.1-3.2. The doc calls this connector J1 (its name on the IO board); on the CPU board it is J9.',
    'Both buffers are disabled at power-up (BUS_OE_N pulled high) and NBRESET is held low until firmware releases it.',
    'Series resistors on the J9 side for the ribbon cable. Unused 74AHCT541 inputs tied low.',
))
b = S.block('Data: SN74LVC8T245 (A = 3.3 V side, B = 5 V side)')
n8 = {'1': '+3V3', '23': '+5V', '24': '+5V', '11': 'GND', '12': 'GND', '13': 'GND', '22': 'BUS_OE_N', '2': 'BUS_DIR'}
for i in range(8):
    n8[str(3 + i)] = f'BUS_D{i}'; n8[str(21 - i)] = f'BD{i}'
u6 = Part('U6', 'Logic_LevelTranslator:SN74LVC8T245', 'SN74LVC8T245', n8, FP['TSSOP24'])
b.place(u6, 0, 0, auto=False)
for i in range(8):
    series_r(b, u6, str(21 - i), f'J9_D{i}')
b.autoconnect(u6, skip=[str(21 - i) for i in range(8)])
bank(b, [('10k', 'BUS_OE_N', '+3V3'), ('10k', 'BUS_DIR', 'GND')], -7.62, 38.1)

b = S.block('Address and IOSTB: 74AHCT541 at 5 V')
n5 = {'20': '+5V', '10': 'GND', '1': 'BUS_OE_N', '19': 'BUS_OE_N', '6': 'BUS_IOSTB', '7': 'GND', '8': 'GND', '9': 'GND',
      '14': 'BSTB', '13': 'NC', '12': 'NC', '11': 'NC'}
for i in range(4):
    n5[str(2 + i)] = f'BUS_A{i}'; n5[str(18 - i)] = f'BA{i}'
u7 = Part('U7', '74xx:74AHCT541', '74AHCT541', n5, FP['TSSOP20'])
b.place(u7, 0, 0, auto=False)
series_pack(b, u7, ['18', '17', '16', '15'], [f'J9_A{i}' for i in range(4)])
series_r(b, u7, '14', 'J9_IOSTB', dx=12.7)
b.autoconnect(u7, skip=['18', '17', '16', '15', '14'])

b = S.block('NBRESET: open drain, IO board held in reset until released')
b.place(Part('Q3', 'Transistor_FET:2N7002', '2N7002', {'1': 'NBRESET_DRV', '3': 'J9_NBRESET', '2': 'GND'}), 0, 0)
hres(b, '10k', 'NBRESET_DRV', '+3V3', -7.62, 15.24)

b = S.block('J9: 2x10 to IO board J1')
j9n = {'7': 'J9_D0', '5': 'J9_D1', '3': 'J9_D2', '1': 'J9_D3', '2': 'J9_D4', '4': 'J9_D5', '6': 'J9_D6', '8': 'J9_D7',
       '12': 'J9_A0', '14': 'J9_A1', '16': 'J9_A2', '18': 'J9_A3', '15': 'J9_IOSTB', '13': 'J9_NBRESET',
       '19': 'GND', '20': 'GND', '9': 'NC', '10': 'NC', '11': 'NC', '17': 'NC'}
b.place(Part('J9', 'Connector_Generic:Conn_02x10_Odd_Even', 'J9 IO BUS', j9n, 'Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical'), 0, 0)
b = S.block('Decoupling')
decaps(b, '+3V3', ['100n'], 0, 0); decaps(b, '+5V', ['100n', '100n', '10u'], 7.62, 0)

# =====================================================================
# Sheet: switch returns (J6, J12)
# =====================================================================
S = D.sheet('Switch returns', 'sw_returns.kicad_sch', 'Switch matrix returns: LM339 front end (copy of the original)', comments=(
    'Per return (ARCHITECTURE.md 5.2-5.3): series diode from the connector, 1 k pull-up to +4.5 V, 220 R + 100 nF, LM339 against',
    'VREF (2.25 V). Output 1 = open, 0 = closed, as the ROM expects. Connector pin to return order follows the original drawing:',
    'verify with a meter before relying on it.',
))
def return_channel(b, i, x, y):
    """RETn_F (to comparator) <- 100n node <- 220R <- 1k pull-up node <- diode <- RETn_IN (connector)"""
    rin, rf = f'RET{i}_IN', f'RET{i}_F'
    xY = x + 5.08
    b.label((x, y), rf, 'L'); b.wire((x, y), (xY, y))
    c = C('100n', rf, 'GND'); b.place(c, xY, y + 3.81, auto=False)
    b.terminate(c.pin_pos('2'), 'D', 'GND', stub=0)
    r = R('220', rf, f'RET{i}_X', rot=90); b.place(r, xY + 7.62 + 3.81, y, auto=False)
    b.wire((xY, y), r.pin_pos('1'))
    xX = r.pin_pos('2')[0] + 5.08
    b.wire(r.pin_pos('2'), (xX, y))
    pu = R('1k', '+4V5', f'RET{i}_X'); b.place(pu, xX, y - 3.81, auto=False)
    b.terminate(pu.pin_pos('1'), 'U', '+4V5', elbow='L')
    d = Part(nref('D'), 'Diode:1N4148W', '1N4148W', {'1': rin, '2': f'RET{i}_X'}, FP['SOD123'], rotation=180)
    b.place(d, xX + 7.62 + 3.81, y, auto=False)
    b.wire((xX, y), d.pin_pos('2'))
    b.terminate(d.pin_pos('1'), 'R', rin)
    b.junction((xY, y)); b.junction((xX, y))
b1 = S.block('Returns 1-8 (J6)'); b2 = S.block('Returns 9-16 (J12)')
for i in range(1, 17):
    return_channel(b1 if i <= 8 else b2, i, 0, ((i - 1) % 8) * 20.32)
b = S.block('LM339 comparators (outputs to the shift chain)')
for k in range(4):
    ref = f'U{8 + k}'
    for u in range(1, 5):
        i = k * 4 + u
        on, inn, out = {1: ('5', '4', '2'), 2: ('7', '6', '1'), 3: ('11', '10', '13'), 4: ('9', '8', '14')}[u]
        b.place(Part(ref, 'Comparator:LM339', 'LM339', {on: f'RET{i}_F', inn: 'VREF', out: f'RET{i}'}, FP['SO14'], unit=u),
                k * 38.1, (u - 1) * 17.78)
    b.place(Part(ref, 'Comparator:LM339', 'LM339', {'3': '+4V5', '12': 'GND'}, FP['SO14'], unit=5), k * 38.1, 4 * 17.78)
b = S.block('Comparator pull-ups (3.3 V logic)')
bank(b, [('10k', f'RET{i}', '+3V3') for i in range(1, 9)], 0, 0)
bank(b, [('10k', f'RET{i}', '+3V3') for i in range(9, 17)], 33.02, 0)
b = S.block('+4.5 V switch supply and VREF')
b.place(Part('D4', 'Device:D', 'S1M', {'2': '+5V', '1': '+4V5'}, FP['SMA'], rotation=180), 0, 0)
vcap(b, '100u', '+4V5', 0, 12.7, pol=True, fp=FP['CP6'])
flag(b, '+4V5', 12.7, 12.7)
divider(b, '3.3k', '3.3k', '+4V5', 'VREF', 'GND', 33.02, 0, cap='22u')
decaps(b, '+4V5', ['100n'] * 4, 0, 35.56)
b = S.block('J6 and J12: switch rows (returns)')
j6 = {p: f'RET{i + 1}_IN' for i, p in enumerate([1, 2, 3, 5, 6, 7, 8, 9])}; j6.update({4: 'NC', 10: 'GND'})
j12 = {p: f'RET{i + 9}_IN' for i, p in enumerate([1, 2, 3, 4, 6, 7, 8, 9])}; j12.update({5: 'NC', 10: 'GND'})
b.place(generic_conn('J6', 10, j6, kk254(10), 'J6 SWITCH ROWS'), 0, 0)
b.place(generic_conn('J12', 10, j12, kk254(10), 'J12 SWITCH ROWS'), 33.02, 0)

# =====================================================================
# Sheet: dedicated switches (J2, J3, J13) + DIP
# =====================================================================
S = D.sheet('Dedicated switches', 'sw_dedicated.kicad_sch', 'Dedicated switches D1-D24, memory protect, DIP switches', comments=(
    'Per input: 1.5 k pull-up to +4.5 V (switch wetting current) and the original 39 k + 47 pF filter, plus 68 k to ground so',
    'the 3.3 V 74HC165 sees 2.8 V (open) or 0 V (closed). Connector pin to D-number order follows the original drawing: verify it.',
    'Memory protect (J2 pin 10) uses the same filter with the original 4.7 k pull-up and goes to RP2354B GPIO31.',
))
def ded_channel(b, name, x, y, pull='1.5k'):
    nin = f'{name}_IN'
    b.label((x, y), name, 'L')
    xB = x + 5.08; xB2 = xB + 7.62
    b.wire((x, y), (xB, y)); b.wire((xB, y), (xB2, y))
    c = C('47p', name, 'GND'); b.place(c, xB, y + 3.81, auto=False)
    b.terminate(c.pin_pos('2'), 'D', 'GND', stub=0)
    rd = R('68k', name, 'GND'); b.place(rd, xB2, y + 3.81, auto=False)
    b.terminate(rd.pin_pos('2'), 'D', 'GND', stub=0)
    r = R('39k', name, nin, rot=90); b.place(r, xB2 + 10.16 + 3.81, y, auto=False)
    b.wire((xB2, y), r.pin_pos('1'))
    xA = r.pin_pos('2')[0] + 5.08
    b.wire(r.pin_pos('2'), (xA, y))
    pu = R(pull, '+4V5', nin); b.place(pu, xA, y - 3.81, auto=False)
    b.terminate(pu.pin_pos('1'), 'U', '+4V5', elbow='L')
    b.wire((xA, y), (xA + 5.08, y)); b.label((xA + 5.08, y), nin, 'R')
    b.junction((xB, y)); b.junction((xB2, y)); b.junction((xA, y))
blocks = [S.block('D1-D8 (J2)'), S.block('D9-D16 (J3)'), S.block('D17-D24 (J13)')]
for i in range(1, 25):
    ded_channel(blocks[(i - 1) // 8], f'DED{i}', 0, ((i - 1) % 8) * 20.32)
b = S.block('Memory protect (J2 pin 10)')
ded_channel(b, 'MEM_PROTECT', 0, 0, pull='4.7k')
b = S.block('Connectors J2, J3, J13')
j2 = {p: f'DED{i + 1}_IN' for i, p in enumerate([1, 2, 3, 4, 6, 7, 8, 9])}; j2.update({5: 'NC', 10: 'MEM_PROTECT_IN', 11: 'GND', 12: 'GND'})
j3 = {p: f'DED{i + 9}_IN' for i, p in enumerate([1, 2, 4, 5, 6, 7, 8, 9])}; j3.update({3: 'NC', 10: 'GND'})
j13 = {p: f'DED{i + 17}_IN' for i, p in enumerate([1, 3, 4, 5, 6, 7, 8, 9])}; j13.update({2: 'NC', 10: 'GND'})
b.place(generic_conn('J2', 12, j2, kk254(12), 'J2 DEDICATED'), 0, 0)
b.place(generic_conn('J3', 10, j3, kk254(10), 'J3 DEDICATED'), 33.02, 0)
b.place(generic_conn('J13', 10, j13, kk254(10), 'J13 DEDICATED'), 66.04, 0)
b = S.block('DIP switches (D25-D32)')
dn = {str(i): f'DIP{i}' for i in range(1, 9)}; dn.update({str(9 + i): 'GND' for i in range(8)})
b.place(Part('SW3', 'Switch:SW_DIP_x08', 'DIP x8', dn, 'Button_Switch_THT:SW_DIP_SPSTx08_Slide_9.78x22.5mm_W7.62mm_P2.54mm'), 0, 0)
bank(b, [('10k', f'DIP{i}', '+3V3') for i in range(1, 9)], 0, 25.4)

# =====================================================================
# Sheet: switch scan chain + strobes
# =====================================================================
S = D.sheet('Switch scan', 'sw_scan.kicad_sch', 'Switch scan: 6 x 74HC165, 74HC595 strobes, J1 switch columns', comments=(
    'One shift clock for both registers: PIO1 shifts 48 inputs in while the next strobe pattern shifts into the 595 (ARCHITECTURE.md 5.3-5.4).',
    'First bits out of SW_DATA: U19 RET1-8, U18 RET9-16, U17 D1-8, U16 D9-16, U15 D17-24, U14 DIP1-8.',
    'Strobes: 595 high -> MMBT3904 on -> strobe pulled low (active), with the original 1 k pull-up to +4.5 V and 100 nF.',
))
chips = [('U14', [f'DIP{i}' for i in range(1, 9)]), ('U15', [f'DED{i}' for i in range(17, 25)]),
         ('U16', [f'DED{i}' for i in range(9, 17)]), ('U17', [f'DED{i}' for i in range(1, 9)]),
         ('U18', [f'RET{i}' for i in range(9, 17)]), ('U19', [f'RET{i}' for i in range(1, 9)])]
b = S.block('74HC165 input chain (3.3 V)')
for k, (ref, ins) in enumerate(chips):
    n = {'16': '+3V3', '8': 'GND', '1': 'SW_LOAD_N', '2': 'SW_CLK', '15': 'GND', '7': 'NC',
         '10': 'GND' if k == 0 else f'CHAIN{k}', '9': f'CHAIN{k + 1}' if k < 5 else 'SW_DATA'}
    for pin, net in zip(['11', '12', '13', '14', '3', '4', '5', '6'], ins): n[pin] = net
    b.place(Part(ref, '74xx:74HC165', '74HC165', n, FP['SO16']), (k % 3) * 55.88, (k // 3) * 66.04)
b = S.block('74HC595 strobe register')
n = {'16': '+3V3', '8': 'GND', '14': 'STB_DATA', '11': 'SW_CLK', '10': '+3V3', '12': 'STB_LATCH', '13': 'GND', '9': 'NC'}
for i, pin in enumerate(['15', '1', '2', '3', '4', '5', '6', '7']): n[pin] = f'STB_Q{i + 1}'
b.place(Part('U20', '74xx:74HC595', '74HC595', n, FP['SO16']), 0, 0)
decaps(b, '+3V3', ['100n'] * 7, -15.24, 35.56)
def strobe_channel(b, i, x, y):
    q = f'STB_Q{i}'
    b.label((x, y), q, 'L')
    r = R('1k', q, f'STB{i}_B', rot=90); b.place(r, x + 2.54 + 3.81, y, auto=False)
    b.wire((x, y), r.pin_pos('1'))
    t = Part(nref('Q'), 'Transistor_BJT:MMBT3904', 'MMBT3904', {'1': f'STB{i}_B', '3': f'STB{i}', '2': 'GND'})
    b.place(t, r.pin_pos('2')[0] + 7.62, y, auto=False)
    b.wire(r.pin_pos('2'), t.pin_pos('1'))
    b.terminate(t.pin_pos('2'), 'D', 'GND', stub=0)
    cpos = t.pin_pos('3'); node = (cpos[0], cpos[1] - 2.54)
    b.wire(cpos, node)
    n2 = (node[0] + 7.62, node[1])
    b.wire(node, n2)
    pu = R('1k', '+4V5', f'STB{i}'); b.place(pu, node[0], node[1] - 3.81, auto=False)
    b.terminate(pu.pin_pos('1'), 'U', '+4V5', elbow='L')
    c = C('100n', f'STB{i}', 'GND'); b.place(c, n2[0], n2[1] + 3.81, auto=False)
    b.terminate(c.pin_pos('2'), 'D', 'GND', stub=0)
    b.wire(n2, (n2[0] + 5.08, n2[1])); b.label((n2[0] + 5.08, n2[1]), f'STB{i}', 'R')
    b.junction(node); b.junction(n2)
bs = [S.block('Strobe drivers 1-4'), S.block('Strobe drivers 5-8')]
for i in range(1, 9):
    strobe_channel(bs[(i - 1) // 4], i, 0, ((i - 1) % 4) * 27.94)
b = S.block('J1: switch columns (strobes), key pin 2')
j1 = {p: f'STB{i + 1}' for i, p in enumerate([1, 3, 4, 5, 6, 7, 8, 9])}; j1[2] = 'NC'
b.place(generic_conn('J1', 9, j1, kk254(9), 'J1 SWITCH COLUMNS'), 0, 0)

# =====================================================================
# Sheet: display (J5) and GI dimmer header
# =====================================================================
S = D.sheet('Display and GI', 'display_gi.kicad_sch', 'J5 original DMD driver and GI dimmer header', comments=(
    'J5 pinout read from the original drawing (ARCHITECTURE.md 8): signals on odd pins, ground on even pins. Confirm with a meter (Q18).',
    'The 100 k pull-downs keep the DMD lines low while the RP2354B boots.',
    'J18 is the default GI dimmer link of ARCHITECTURE.md 10.2: +5 V, GND, GI_PWM, GI_SPARE.',
))
dmd = ['DMD_DE', 'DMD_ROWDATA', 'DMD_ROWCLK', 'DMD_COLLATCH_A', 'DMD_PIXCLK', 'DMD_SDATA', 'DMD_COLLATCH_B']
b = S.block('74HCT245 at 5 V (A to B only)')
n = {'20': '+5V', '10': 'GND', '1': '+5V', '19': 'GND', '9': 'GND', '11': 'NC'}
for i, s in enumerate(dmd):
    n[str(2 + i)] = s; n[str(18 - i)] = f'J5B{i}'
u21 = Part('U21', '74xx:74HC245', '74HCT245', n, FP['TSSOP20'])
b.place(u21, 0, 0, auto=False)
series_pack(b, u21, ['18', '17', '16', '15'], [f'J5_{s[4:]}' for s in dmd[:4]])
series_pack(b, u21, ['14', '13', '12', '11'], [f'J5_{s[4:]}' for s in dmd[4:]] + ['NC'])
b.autoconnect(u21, skip=['18', '17', '16', '15', '14', '13', '12', '11'])
decaps(b, '+5V', ['100n'], 10.16, 33.02)
b = S.block('Pull-downs')
bank(b, [('100k', s, 'GND') for s in dmd], 0, 0)
b = S.block('J5: DMD (2x7)')
j5 = {str(2 * i + 1): f'J5_{s[4:]}' for i, s in enumerate(dmd)}
j5.update({str(2 * i + 2): 'GND' for i in range(7)})
b.place(Part('J5', 'Connector_Generic:Conn_02x07_Odd_Even', 'J5 DMD', j5, 'Connector_IDC:IDC-Header_2x07_P2.54mm_Vertical'), 0, 0)
b = S.block('J18: GI dimmer board link')
b.place(generic_conn('J18', 4, {1: '+5V', 2: 'GND', 3: 'J18_GI_PWM', 4: 'J18_GI_SPARE'}, kk254(4), 'J18 GI DIMMER'), 0, 0)
bank(b, [('100', 'GI_PWM', 'J18_GI_PWM'), ('100', 'GI_SPARE', 'J18_GI_SPARE'), ('100k', 'GI_PWM', 'GND')], -45.72, -2.54)

# =====================================================================
# Sheet: audio
# =====================================================================
S = D.sheet('Audio', 'audio.kicad_sch', 'Audio: Pi I2S -> PCM5102A -> 2 x TDA2030A on +-12 V -> J10', comments=(
    'Same structure as the original (DAC + two TDA2030A on +-12 V, speakers on J10). Volume stays digital (ROM / PinMAME).',
    'Gain: 22k / 4.7k input divider x (1 + 22k / 1k) = about 4 overall. Starting values, to check on the bench.',
))
b = S.block('PCM5102A DAC (PLL from BCK, I2S format)')
b.place(Part('U22', 'Audio:PCM5102A', 'PCM5102A',
             {'15': 'I2S_LRCK', '14': 'I2S_DIN', '13': 'I2S_BCK', '12': 'GND', '11': 'GND', '10': 'GND', '17': 'DAC_XSMT',
              '16': 'GND', '1': '+3V3', '3': 'GND', '20': '+3V3', '19': 'GND', '8': '+3V3_A', '9': 'GND',
              '6': 'DAC_OUTL', '7': 'DAC_OUTR', '2': 'DAC_CAPP', '4': 'DAC_CAPM', '18': 'DAC_LDOO', '5': 'DAC_VNEG'}), 0, 0)
hres(b, '10k', 'DAC_XSMT', '+3V3', -38.1, 25.4)
b.place(C('2.2u', 'DAC_CAPP', 'DAC_CAPM', rot=90), 43.18, -12.7)
vcap(b, '2.2u', 'DAC_LDOO', 40.64, 5.08)
vcap(b, '2.2u', 'DAC_VNEG', 58.42, 5.08)
b.place(Part('FB4', 'Device:FerriteBead_Small', 'FB', {'1': '+3V3', '2': '+3V3_A'}, FP['FB'], rotation=90), 0, 35.56)
vcap(b, '10u', '+3V3_A', 22.86, 40.64)
flag(b, '+3V3_A', 33.02, 40.64)
decaps(b, '+3V3', ['100n', '100n', '10u'], 45.72, 40.64)
for ch, side in (('L', 0), ('R', 1)):
    b = S.block(f'{"Left" if ch == "L" else "Right"} amplifier')
    hres(b, '470', f'DAC_OUT{ch}', f'AF{ch}', 0, 0)
    vcap(b, '2.2n', f'AF{ch}', 0, 12.7)
    b.place(C('1u', f'AF{ch}', f'AC{ch}', rot=90), 25.4, 0)
    hres(b, '22k', f'AC{ch}', f'AIN{ch}', 50.8, 0)
    b.place(R('4.7k', f'AIN{ch}', 'GND'), 30.48, 15.24)
    b.place(Part(f'U{23 + side}', 'Amplifier_Audio:TDA2030', 'TDA2030A',
                 {'1': f'AIN{ch}', '2': f'AFB{ch}', '5': '+12V', '3': '-12V', '4': f'SPK_{ch}'}), 91.44, 0)
    hres(b, '22k', f'AFB{ch}', f'SPK_{ch}', 91.44, 22.86)
    b.place(R('1k', f'AFB{ch}', f'AFC{ch}'), 63.5, 22.86)
    vcap(b, '22u', f'AFC{ch}', 63.5, 40.64, pol=True, fp=FP['CP6'])
    b.place(R('1', f'SPK_{ch}', f'ZB{ch}', fp='Resistor_SMD:R_1206_3216Metric'), 124.46, 7.62)
    vcap(b, '220n', f'ZB{ch}', 124.46, 27.94)
    b.place(Part(nref('D'), 'Device:D', 'S1M', {'2': f'SPK_{ch}', '1': '+12V'}, FP['SMA'], rotation=90), 142.24, -10.16)
    b.place(Part(nref('D'), 'Device:D', 'S1M', {'2': '-12V', '1': f'SPK_{ch}'}, FP['SMA'], rotation=90), 142.24, 15.24)
    decaps(b, '+12V', ['100n'], 160.02, -10.16)
    vcap(b, '100u', '+12V', 170.18, -10.16, pol=True, fp=FP['CP8'])
    vcap(b, '100n', 'GND', 160.02, 15.24, bot='-12V')
    vcap(b, '100u', 'GND', 170.18, 15.24, bot='-12V', pol=True, fp=FP['CP8'])
b = S.block('J10: speakers (original pinout)')
b.place(generic_conn('J10', 4, {1: 'SPK_L', 2: 'SPK_R', 3: 'GND', 4: 'GND'}, kk396(4), 'J10 SPEAKERS'), 0, 0)

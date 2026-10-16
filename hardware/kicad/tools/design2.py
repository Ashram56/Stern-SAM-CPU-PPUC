"""SAM CPU replacement board schematic, drawn with wires (draft 0.2).

Every page keeps a connector next to the circuit that drives or reads it. Coordinates
are in units of 2.54 mm (0.1 in). Run through build2.py.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from kigen import Part, SymDef, Design
from sch import Page

D = Design('sam_cpu', 'SAM CPU replacement board', '0.2', 'Stern SAM CPU PPUC (CERN-OHL-S v2)', '2026-10-06')
PAGES = []
ROOT_NOTES = ('SAM CPU replacement board, draft 0.2, drawn from docs/ARCHITECTURE.md. Licence: CERN-OHL-S v2.\n'
              'A Raspberry Pi 4 on the 40-pin header J21 runs PinMAME + ppuc (HDMI stays on the Pi). The RP2354B drives the\n'
              'original IO power driver board on J9 and scans the switches. Connector names and pinouts follow the original\n'
              'CPU/Sound board 520-5246-00. Each connector sits on the same page as the circuit that drives or reads it.\n'
              'Signals between pages use global labels; the numbers in brackets next to a label list the other pages it goes to.')
U = 2.54

_cnt = collections.Counter({'D': 10, 'Q': 10})
EXPLICIT = {'C119'}          # refs given by hand; the counters skip them
def nref(prefix):
    _cnt[prefix] += 1
    while f'{prefix}{_cnt[prefix]}' in EXPLICIT:
        _cnt[prefix] += 1
    return f'{prefix}{_cnt[prefix]}'

FP = {
    'R': 'Resistor_SMD:R_0603_1608Metric', 'RN': 'Resistor_SMD:R_Array_Convex_4x0603',
    'C': 'Capacitor_SMD:C_0603_1608Metric', 'C0805': 'Capacitor_SMD:C_0805_2012Metric', 'C1206': 'Capacitor_SMD:C_1206_3216Metric',
    'CP6': 'Capacitor_SMD:CP_Elec_6.3x7.7', 'CP8': 'Capacitor_SMD:CP_Elec_8x10',
    'SOD123': 'Diode_SMD:D_SOD-123', 'SMA': 'Diode_SMD:D_SMA', 'SMB': 'Diode_SMD:D_SMB',
    'SO8': 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', 'SO14': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm', 'SO16': 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    'TSSOP20': 'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm', 'TSSOP24': 'Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm',
    'LED': 'LED_SMD:LED_0603_1608Metric', 'FB': 'Inductor_SMD:L_0805_2012Metric',
    'BTN': 'Button_Switch_SMD:SW_SPST_TL3342',
}
SMALL_C = ('100n', '10n', '1u', '15p', '47p', '2.2n', '220n')
def kk254(n): return f'Connector_Molex:Molex_KK-254_AE-6410-{n:02d}A_1x{n:02d}_P2.54mm_Vertical'
def kk396(n): return f'Connector_Molex:Molex_KK-396_A-41791-{n:04d}_1x{n:02d}_P3.96mm_Vertical'

def R(value, n1, n2, rot=0, fp=None, ref=None):
    return Part(ref or nref('R'), 'Device:R', value, {'1': n1, '2': n2}, fp or FP['R'], rotation=rot)
def C(value, n1, n2, rot=0, pol=False, fp=None):
    if fp is None: fp = FP['C'] if value in SMALL_C else FP['C0805']
    return Part(nref('C'), 'Device:C_Polarized' if pol else 'Device:C', value, {'1': n1, '2': n2}, fp, rotation=rot)
def conn(ref, n, nets, fp, value):
    return Part(ref, f'Connector_Generic:Conn_01x{n:02d}', value, {str(k): v for k, v in nets.items()}, fp)
def TP(net):
    return Part(nref('TP'), 'Connector:TestPoint', net, {'1': net}, 'TestPoint:TestPoint_Pad_D1.5mm')
def flag(net, up=None):
    """PWR_FLAG; for +V rails it hangs below its pin so the rail symbol can point up."""
    from sch import POWER
    if up is None: up = net in POWER and not POWER[net][1]
    return Part(nref('#FLG'), 'power:PWR_FLAG', 'PWR_FLAG', {'1': net}, '', rotation=180 if up else 0)

class P(Page):
    """Page with unit-based placement helpers."""
    def at(self, part, x, y):
        return self.add(part, x * U, y * U)
    def hr(self, value, n1, n2, x, y, **k):      # horizontal resistor, pin 1 left at (x, y)
        return self.at(R(value, n1, n2, rot=90, **k), x + 1.5, y)
    def vr(self, value, n1, n2, x, y, **k):      # vertical resistor, pin 1 top at (x, y)
        return self.at(R(value, n1, n2, **k), x, y + 1.5)
    def vc(self, value, n1, x, y, n2='GND', **k):  # vertical capacitor, pin 1 top at (x, y)
        return self.at(C(value, n1, n2, **k), x, y + 1.5)
    def hc(self, value, n1, n2, x, y, **k):
        return self.at(C(value, n1, n2, rot=90, **k), x + 1.5, y)
    def tps(self, nets, x, y, dx=4):
        """a row of test points, pins at y"""
        for i, n in enumerate(nets):
            self.at(TP(n), x + i * dx, y)
    def decaps(self, net, values, x, y, dx=3, n2='GND'):
        for i, v in enumerate(values):
            k = {}
            if v.endswith('u') and float(v[:-1]) >= 47: k = dict(pol=True, fp=FP['CP6'])
            self.vc(v, net, x + i * dx, y, n2=n2, **k)
    def pack(self, ic, pins, outs, x, value='33'):
        """4 x resistor array, rotated so its left pins face the IC; pins/outs top to bottom.
        Left-hand pins sit at x, from y_top to y_top + 3."""
        rn = Part(nref('RN'), 'Device:R_Pack04', value, {}, FP['RN'], rotation=90)
        ys = [ic.pin_pos(p)[1] / U for p in pins]
        ytop = round(min(ys))
        # rot 90: left pins R4.2, R3.2, R2.2, R1.2 at y-1 .. y+2 ; right pins R4.1 .. R1.1
        left = ['5', '6', '7', '8']; right = ['4', '3', '2', '1']
        for k in range(4):
            if k < len(pins) and outs[k] != 'NC':
                rn.nets[left[k]] = ic.nets[pins[k]]; rn.nets[right[k]] = outs[k]
            else:
                rn.nets[left[k]] = 'NC'; rn.nets[right[k]] = 'NC'
        return self.at(rn, x + 2, ytop + 1)

    def fan(self, net, src, x, dst):
        """hand-drawn dogleg: src -> (x, src_y) -> (x, dst_y) -> dst, in units"""
        pts = [src, (x, src[1]), (x, dst[1]), dst]
        out = [pts[0]]
        for p in pts[1:]:
            if p != out[-1]: out.append(p)
        self.wire(net, [(a * U, b * U) for a, b in out])

    def fan_in(self, items, xmin):
        """connector pins -> rows: items = [(net, (px, py), (dx, dy))]; non-crossing doglegs between xmin and dst x"""
        up = sorted([it for it in items if it[2][1] < it[1][1]], key=lambda it: it[2][1])
        down = sorted([it for it in items if it[2][1] >= it[1][1]], key=lambda it: -it[2][1])
        for grp in (up, down):
            for k, (net, src, dst) in enumerate(grp):
                self.fan(net, src, xmin + k, dst)

def page(*a, **k):
    p = P(*a, **k); PAGES.append(p); return p


# =====================================================================
# Power
# =====================================================================
S = page('Power', 'power.kicad_sch', 'Power: +5 V mux, external +12 V, 3.3 V, 4.5 V, monitors', notes=(
    'J11 keeps the original CPU board connector (IO board J16 harness) for +5 V and ground only: its +-12 V pins are not used.',
    'The audio amplifiers run from an external +12 V supply on J23 (about 3 A at full volume). F1 + D5 blow the fuse on reverse polarity.',
    'U3 NCP1117 (as in the RP2350 hardware guide) is stable with ceramic capacitors. All regulator capacitors are 0805 or larger for low DC-bias derating.',
    'External +5 V on J17 has priority: U2 turns the J11 path off whenever +5V_EXT is present (EXT_PRESENT high).',
    'LTC4412 + AO3401A ideal diodes stand in for the TPS2121 of ARCHITECTURE.md 9.3 (library part, about 4 A per path).',
    'JP1 (bridged by default) disconnects the J11 +5 V completely; leaving J17 unplugged forces J11.',
))
# external input (row 1)
S.at(Part('J17', 'Connector:Screw_Terminal_01x02', 'EXT 5V', {'1': '+5V_EXT', '2': 'GND'},
          'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', mirror='y'), 10, 26)
S.at(Part('D1', 'Device:D_TVS', 'SMBJ5.0CA', {'1': '+5V_EXT', '2': 'GND'}, FP['SMB'], rotation=270), 20, 29.5)
S.vc('100u', '+5V_EXT', 25, 28, pol=True, fp=FP['CP8'])
S.at(flag('+5V_EXT'), 30, 24)
S.at(Part('Q1', 'Transistor_FET:AO3401A', 'AO3401A', {'1': 'GATE_EXT', '3': '+5V_EXT', '2': '+5V'}, rotation=90), 48, 22)
S.at(Part('U1', 'Power_Management:LTC4412xS6', 'LTC4412', {'1': '+5V_EXT', '3': 'GND', '5': 'GATE_EXT', '2': 'GND', '6': '+5V', '4': 'NC'}), 48, 31)
# J11 input (row 2)
S.at(Part('J11', 'Connector_Generic:Conn_01x06', 'J11 POWER',
          {'1': '+5V_J11_IN', '2': 'GND', '3': 'NC', '4': 'GND', '5': 'GND', '6': 'NC'}, kk396(6), mirror='y'), 10, 56)
S.at(Part('FB1', 'Device:FerriteBead_Small', '3A', {'1': '+5V_J11_IN', '2': '+5V_J11_F'}, FP['FB'], rotation=90), 19, 54)
S.at(Part('JP1', 'Jumper:SolderJumper_2_Bridged', 'J11 5V', {'1': '+5V_J11_F', '2': '+5V_J11'},
          'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm'), 27, 54)
S.at(flag('+5V_J11'), 33, 50)
S.at(Part('Q2', 'Transistor_FET:AO3401A', 'AO3401A', {'1': 'GATE_J11', '3': '+5V_J11', '2': '+5V'}, rotation=90), 48, 50)
S.at(Part('U2', 'Power_Management:LTC4412xS6', 'LTC4412', {'1': '+5V_J11', '3': 'EXT_PRESENT', '5': 'GATE_J11', '2': 'GND', '6': '+5V', '4': 'NC'}), 48, 59)
S.vr('100k', '+5V_EXT', 'EXT_PRESENT', 36, 36)
S.vr('100k', 'EXT_PRESENT', 'GND', 36, 42)
# external +12 V for the audio amplifiers
S.at(Part('J23', 'Connector:Screw_Terminal_01x02', 'EXT 12V', {'1': '+12V_IN', '2': 'GND'},
          'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', mirror='y'), 10, 70)
S.at(Part('F1', 'Device:Polyfuse', '4A hold', {'1': '+12V_IN', '2': '+12V'}, 'Fuse:Fuse_2920_7451Metric', rotation=90), 22, 69)
S.at(Part('D5', 'Device:D_Zener', 'SMBJ15A', {'1': '+12V', '2': 'GND'}, FP['SMB'], rotation=270), 30, 73)
S.vc('100u', '+12V', 38, 70, pol=True, fp=FP['CP8'])
S.vc('100n', '+12V', 44, 70)
S.stub_len['+3V3'] = 6
# +5 V output
S.decaps('+5V', ['100u', '10u'], 62, 36)
# 3.3 V
S.at(Part('U3', 'Regulator_Linear:NCP1117-3.3_SOT223', 'NCP1117-3.3', {'3': '+5V', '1': 'GND', '2': '+3V3'}), 90, 28)
S.vc('10u', '+5V', 82, 30, fp=FP['C1206'])
S.vc('10u', '+3V3', 98, 30, fp=FP['C1206'])
S.vr('1k', '+3V3', 'LED_PWR', 104, 28)
S.at(Part('D2', 'Device:LED', 'green', {'2': 'LED_PWR', '1': 'GND'}, FP['LED'], rotation=90), 104, 35.5)
# 4.5 V switch supply
S.at(Part('D4', 'Device:D', 'S1M', {'2': '+5V', '1': '+4V5'}, FP['SMA'], rotation=180), 89.5, 52)
S.vc('100u', '+4V5', 98, 54, pol=True, fp=FP['CP6'])
# supply monitors
S.vr('10k', '+5V', 'VMON_5V', 120, 28)
S.vr('10k', 'VMON_5V', 'GND', 120, 34)
S.vc('100n', 'VMON_5V', 125, 34)
S.vr('33k', '+12V', 'VMON_12V', 140, 28)
S.vr('10k', 'VMON_12V', 'GND', 140, 34)
S.vc('100n', 'VMON_12V', 145, 34)
S.port('VMON_5V', 132 * U, 32 * U, 'R')
S.port('VMON_12V', 152 * U, 32 * U, 'R')
# power flags for the rails
for i, n in enumerate(['+5V', '+4V5', '+12V', 'GND']):
    S.at(flag(n), 70 + i * 6, 80)
S.tps(['+5V', '+3V3', '+4V5', '+12V', 'GND', 'GND'], 70, 92, dx=6)
S.frame('Test points', 64 * U, 84 * U, 112 * U, 98 * U)
S.frame('External +5 V (J17, priority)', 5 * U, 16 * U, 58 * U, 44 * U)
S.frame('IO board power (J11, +5 V only)', 5 * U, 46 * U, 58 * U, 64 * U)
S.frame('External +12 V for audio (J23)', 5 * U, 66 * U, 58 * U, 92 * U)
S.frame('3.3 V', 76 * U, 16 * U, 112 * U, 44 * U)
S.frame('4.5 V for the switch matrix', 76 * U, 46 * U, 112 * U, 66 * U)
S.frame('Supply monitors (RP2354B ADC)', 114 * U, 16 * U, 160 * U, 44 * U)

# =====================================================================
# MCU and Raspberry Pi
# =====================================================================
S = page('MCU and Pi', 'mcu.kicad_sch', 'RP2354B SAM IO controller and Raspberry Pi 4 header', paper='A3', notes=(
    'GPIO map: ARCHITECTURE.md 9.2. PIO0 bus on GPIO0-15, PIO1 switch chain on GPIO16-20, PIO2 DMD on GPIO21-27, GPIO31 coin door memory protect.',
    'Core supply from the internal switching regulator: VREG_LX -> L1 -> DVDD (1.1 V); VREG_AVDD through 33 R / 4.7 uF. Check against the RP2350 hardware guide.',
    'Raspberry Pi 4 on the 40-pin header J21 (HDMI stays on the Pi). The Pi is powered from the board +5 V: never plug the Pi USB-C supply at the same time.',
    'U25 DS3231MZ real-time clock on the Pi I2C1 bus (Linux: dtoverlay=i2c-rtc,ds3231), backed by a CR2032 in BT1.',
))
gp = {i: f'BUS_D{i}' for i in range(8)}
gp.update({8 + i: f'BUS_A{i}' for i in range(4)})
gp.update({12: 'BUS_IOSTB', 13: 'BUS_DIR', 14: 'NBRESET_DRV', 15: 'BUS_OE_N',
           16: 'SW_CLK', 17: 'SW_LOAD_N', 18: 'SW_DATA', 19: 'STB_DATA', 20: 'STB_LATCH',
           21: 'DMD_DE', 22: 'DMD_ROWDATA', 23: 'DMD_ROWCLK', 24: 'DMD_COLLATCH_A', 25: 'DMD_PIXCLK',
           26: 'DMD_SDATA', 27: 'DMD_COLLATCH_B', 28: 'FRAME_MOSI', 29: 'FRAME_CS_N', 30: 'FRAME_SCK',
           31: 'MEM_PROTECT', 32: 'RP_UART_TX', 33: 'RP_UART_RX', 34: 'RP_IRQ_N', 35: 'GI_PWM', 36: 'GI_SPARE',
           37: 'AMP_MUTE', 40: 'VMON_5V', 41: 'VMON_12V', 42: 'LED_STATUS'})
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
MX, MY = 72, 58
u4 = S.at(Part('U4', 'MCU_RaspberryPi:RP2354B', 'RP2354B', nets), MX, MY)
S.label_nets |= {'MR_N', 'BOOTSEL', 'SWCLK', 'SWDIO'}
# core regulator parts (above the chip)
S.at(Part('L1', 'Device:L', '3.3u', {'1': 'VREG_LX', '2': '+1V1'}, 'Inductor_SMD:L_Cenker_CKCS201610', rotation=180,
          props={'MPN': 'Abracon AOTA-B201610S3R3-101-T (polarity dot as on Pico 2)'}), 74, 28.5)
S.vr('33', '+3V3', 'VREG_AVDD', 65, 26)
S.vc('4.7u', 'VREG_AVDD', 61, 30)
S.at(flag('VREG_AVDD', up=True), 57, 33)
S.at(flag('+1V1'), 80, 26)
S.decaps('+3V3', ['4.7u'] + ['100n'] * 11, 84, 17)
S.decaps('+1V1', ['4.7u', '100n', '100n', '100n'], 126, 17)
# reset supervisor and RESET button
S.at(Part('U5', 'Power_Supervisor:TPS3808DBV', 'TPS3808G33', {'5': '+3V3', '3': 'MR_N', '4': 'NC', '6': '+3V3', '2': 'GND', '1': 'RUN'}), 42, 30)
S.vr('10k', '+3V3', 'RUN', 52, 33)
S.at(Part('SW1', 'Switch:SW_Push', 'RESET', {'1': 'MR_N', '2': 'GND'}, FP['BTN'], rotation=270), 32, 33)
# USB-C to the Pi
S.at(Part('J19', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C (to Pi)',
          {'S1': 'GND', 'SH': 'GND', 'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'A4': 'VBUS_PI', 'A9': 'VBUS_PI',
           'B4': 'VBUS_PI', 'B9': 'VBUS_PI', 'A5': 'CC1', 'B5': 'CC2', 'A7': 'USB_DM', 'B7': 'USB_DM',
           'A6': 'USB_DP', 'B6': 'USB_DP', 'A8': 'NC', 'B8': 'NC'},
          'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12'), 10, 52)
S.vr('100k', 'VBUS_PI', 'GND', 20, 62)
S.vr('5.1k', 'CC1', 'GND', 24, 62)
S.vr('5.1k', 'CC2', 'GND', 28, 62)
S.hr('27', 'USB_DM', 'USB_DM_MCU', 38, 46)
S.hr('27', 'USB_DP', 'USB_DP_MCU', 38, 50)
# BOOTSEL button
S.hr('1k', 'BOOTSEL_BTN', 'BOOTSEL', 48, 54)
S.at(Part('SW2', 'Switch:SW_Push', 'BOOTSEL', {'1': 'BOOTSEL_BTN', '2': 'GND'}, FP['BTN'], mirror='y'), 43, 54)
# crystal
S.at(Part('Y1', 'Device:Crystal_GND24', '12MHz', {'1': 'XIN', '3': 'XTAL_OUT', '2': 'GND', '4': 'GND'},
          'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', rotation=270, props={'MPN': 'Abracon ABM8-272-T3'}), 44, 62.5)
S.hr('1k', 'XTAL_OUT', 'XOUT', 52, 66)
S.vc('15p', 'XIN', 36, 60)
S.vc('15p', 'XTAL_OUT', 48, 66)
# SWD header, status LED
S.at(Part('J20', 'Connector_Generic:Conn_01x03', 'SWD', {'1': 'SWCLK', '2': 'GND', '3': 'SWDIO'},
          'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical', mirror='y'), 28, 74)
S.hr('1k', 'LED_STATUS_A', 'LED_STATUS', 50, 77)
S.at(Part('D3', 'Device:LED', 'yellow', {'2': 'LED_STATUS_A', '1': 'GND'}, FP['LED']), 44.5, 77)
# Raspberry Pi header (mirrored: GPIO0-13 face the RP2354B)
pi = Part('J21', 'Connector:Raspberry_Pi_2_3', 'Raspberry Pi 40-pin', {}, 'Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical', mirror='y')
pimap = {'8': 'PI_TXD', '10': 'PI_RXD', '19': 'FRAME_MOSI', '23': 'FRAME_SCK', '24': 'FRAME_CS_N',
         '12': 'I2S_BCK', '35': 'I2S_LRCK', '40': 'I2S_DIN', '15': 'PI_RUN', '13': 'PI_BOOTSEL',
         '18': 'SWCLK', '22': 'SWDIO', '16': 'RP_IRQ_N', '3': 'PI_SDA', '5': 'PI_SCL'}
for p in pi.sd.pins:
    n = p['number']
    pi.nets[n] = {'5V': '+5V', 'GND': 'GND', '3V3': 'NC'}.get(p['name'], pimap.get(n, 'NC'))
S.at(pi, 128, 66)
S.hr('33', 'PI_TXD', 'RP_UART_RX', 142, 57)
S.hr('33', 'PI_RXD', 'RP_UART_TX', 148, 58)
S.hr('1k', 'PI_RUN', 'MR_N', 146, 68)
S.hr('1k', 'PI_BOOTSEL', 'BOOTSEL', 146, 73)
S.vr('10k', '+3V3', 'RP_IRQ_N', 150, 76)
S.frame('Raspberry Pi 4 (40-pin header J21)', 104 * U, 44 * U, 160 * U, 86 * U)
# real-time clock for the Pi (I2C1, GPIO2/3; the Pi has 1.8 k pull-ups), kept running by a CR2032
S.label_nets |= {'PI_SDA', 'PI_SCL'}
S.at(Part('U25', 'Timer_RTC:DS3231MZ', 'DS3231MZ', {'2': '+3V3', '5': 'GND', '6': 'RTC_VBAT', '7': 'PI_SDA', '8': 'PI_SCL',
                                                    '1': 'NC', '3': 'NC', '4': 'NC'}, 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'), 34, 100)
S.at(Part('BT1', 'Device:Battery_Cell', 'CR2032', {'1': 'RTC_VBAT', '2': 'GND'}, 'Battery:BatteryHolder_Keystone_3034_1x20mm'), 18, 102)
S.at(Part('C119', 'Device:C', '100n', {'1': '+3V3', '2': 'GND'}, FP['C']), 46, 96.5)
S.at(Part('#FLG99', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'RTC_VBAT'}, '', rotation=180), 24, 94)
S.frame('Real-time clock (Pi I2C1, CR2032 backup)', 8 * U, 86 * U, 60 * U, 112 * U)
S.tps(['+1V1', 'RUN', 'GND'], 72, 100)
S.frame('Test points', 66 * U, 92 * U, 86 * U, 106 * U)

# =====================================================================
# IO bus: J9 to the IO power driver board
# =====================================================================
S = page('IO bus', 'io_bus.kicad_sch', 'J9: bus to the IO power driver board (IO board J1)', notes=(
    'ARCHITECTURE.md 3.1-3.2. The doc calls this connector J1 (its name on the IO board); on the CPU board it is J9.',
    'Both buffers are off at power-up (BUS_OE_N pulled high) and NBRESET is held low until the firmware releases it.',
    '33 R series resistors on the J9 side for the ribbon cable. Unused 74AHCT541 inputs tied low.',
))
n8 = {'1': '+3V3', '23': '+5V', '24': '+5V', '11': 'GND', '12': 'GND', '13': 'GND', '22': 'BUS_OE_N', '2': 'BUS_DIR'}
for i in range(8):
    n8[str(3 + i)] = f'BUS_D{i}'; n8[str(21 - i)] = f'BD{i}'
u6 = S.at(Part('U6', 'Logic_LevelTranslator:SN74LVC8T245', 'SN74LVC8T245', n8, FP['TSSOP24']), 40, 36)
S.pack(u6, ['21', '20', '19', '18'], [f'J9_D{i}' for i in range(4)], 52)
S.pack(u6, ['17', '16', '15', '14'], [f'J9_D{i}' for i in range(4, 8)], 52)
S.vr('10k', '+3V3', 'BUS_OE_N', 24, 52)
S.vr('10k', 'BUS_DIR', 'GND', 30, 52)
S.port('BUS_OE_N', 14 * U, 56 * U, 'L')
S.port('BUS_DIR', 14 * U, 50 * U, 'L')
n5 = {'20': '+5V', '10': 'GND', '1': 'BUS_OE_N', '19': 'BUS_OE_N', '6': 'BUS_IOSTB', '7': 'GND', '8': 'GND', '9': 'GND',
      '14': 'BSTB', '13': 'NC', '12': 'NC', '11': 'NC'}
for i in range(4):
    n5[str(2 + i)] = f'BUS_A{i}'; n5[str(18 - i)] = f'BA{i}'
u7 = S.at(Part('U7', '74xx:74AHCT541', '74AHCT541', n5, FP['TSSOP20']), 40, 78)
S.pack(u7, ['18', '17', '16', '15'], [f'J9_A{i}' for i in range(4)], 52)
S.wire('BUS_OE_N', [(35 * U, 82 * U), (33 * U, 82 * U), (33 * U, 83 * U), (35 * U, 83 * U)])
S.hr('33', 'BSTB', 'J9_IOSTB', 52, 80)
S.at(Part('Q3', 'Transistor_FET:2N7002', '2N7002', {'1': 'NBRESET_DRV', '3': 'J9_NBRESET', '2': 'GND'}), 92, 84)
S.vr('10k', '+3V3', 'NBRESET_DRV', 84, 79)
S.port('NBRESET_DRV', 76 * U, 84 * U, 'L')
j9n = {'7': 'J9_D0', '5': 'J9_D1', '3': 'J9_D2', '1': 'J9_D3', '2': 'J9_D4', '4': 'J9_D5', '6': 'J9_D6', '8': 'J9_D7',
       '12': 'J9_A0', '14': 'J9_A1', '16': 'J9_A2', '18': 'J9_A3', '15': 'J9_IOSTB', '13': 'J9_NBRESET',
       '19': 'GND', '20': 'GND', '9': 'NC', '10': 'NC', '11': 'NC', '17': 'NC'}
S.at(Part('J9', 'Connector_Generic:Conn_02x10_Odd_Even', 'J9 IO BUS', j9n, 'Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical'), 110, 56)
S.decaps('+3V3', ['100n'], 14, 98)
S.decaps('+5V', ['100n', '100n', '10u'], 20, 98)
S.tps(['J9_IOSTB', 'J9_NBRESET', 'J9_D0', 'J9_A0'], 132, 30, dx=6)

# =====================================================================
# Switch columns: 74HC595 + strobe drivers + J1
# =====================================================================
S = page('Switch columns', 'sw_columns.kicad_sch', 'Switch matrix columns: 74HC595, strobe drivers, J1', notes=(
    'One shift clock for both registers: PIO1 shifts the next strobe pattern into the 595 while the 74HC165 chain shifts in (ARCHITECTURE.md 5.3-5.4).',
    'Strobes: 595 output high -> MMBT3904 on -> strobe pulled low (active), with the original 1 k pull-up to +4.5 V and 100 nF.',
    'J1 keeps the original pinout (key on pin 2). Strobes 5-8 are driven even where a game does not use them (Q15).',
))
n = {'16': '+3V3', '8': 'GND', '14': 'STB_DATA', '11': 'SW_CLK', '10': '+3V3', '12': 'STB_LATCH', '13': 'GND', '9': 'NC'}
for i, pin in enumerate(['15', '1', '2', '3', '4', '5', '6', '7']): n[pin] = f'STB_Q{i + 1}'
S.at(Part('U20', '74xx:74HC595', '74HC595', n, FP['SO16']), 26, 60)
S.decaps('+3V3', ['100n'], 14, 90)
def strobe_channel(S, i, x0, y0):
    q, b, s = f'STB_Q{i}', f'STB{i}_B', f'STB{i}'
    S.hr('1k', q, b, x0, y0)
    S.at(Part(nref('Q'), 'Transistor_BJT:MMBT3904', 'MMBT3904', {'1': b, '3': s, '2': 'GND'}), x0 + 7, y0)
    S.vr('1k', '+4V5', s, x0 + 12, y0 - 7)
    S.vc('100n', s, x0 + 16, y0 - 3)
for i in range(1, 9):
    strobe_channel(S, i, 50, 22 + (i - 1) * 11)
    S.fan(f'STB_Q{i}', (30, 55 + i), {1: 33, 2: 34, 3: 35, 4: 36, 5: 36, 6: 35, 7: 34, 8: 33}[i], (50, 22 + (i - 1) * 11))
j1 = {p: f'STB{i + 1}' for i, p in enumerate([1, 3, 4, 5, 6, 7, 8, 9])}; j1[2] = 'NC'
S.at(conn('J1', 9, j1, kk396(9), 'J1 SWITCH COLUMNS'), 92, 60)
S.tps(['STB1', 'STB2', 'SW_CLK', 'SW_DATA'], 120, 30, dx=6)

# =====================================================================
# Switch rows: J6 / J12, LM339 front end, 74HC165
# =====================================================================
def return_channel(S, i, u, unit, y):
    rin, x, f, ret = f'RET{i}_IN', f'RET{i}_X', f'RET{i}_F', f'RET{i}'
    S.at(Part(nref('D'), 'Diode:1N4148W', '1N4148W', {'1': rin, '2': x}, FP['SOD123']), 21.5, y)
    S.vr('1k', '+4V5', x, 26, y - 4)
    S.hr('220', x, f, 29, y)
    S.vc('100n', f, 34, y + 1)
    on, inn, out = {1: ('5', '4', '2'), 2: ('7', '6', '1'), 3: ('11', '10', '13'), 4: ('9', '8', '14')}[unit]
    S.at(Part(u, 'Comparator:LM339', 'LM339', {on: f, inn: 'VREF', out: ret}, FP['SO14'], unit=unit), 40, y + 1)
    S.vr('10k', '+3V3', ret, 47, y - 3)

def rows_page(first, jref, jpins, keypin, uref, cmp_refs, chain_in, chain_out, extra=None):
    S = page(f'Switch rows {first}-{first + 7}', f'sw_rows_{first}.kicad_sch',
             f'Switch matrix returns {first}-{first + 7}: {jref}, LM339 front end, 74HC165', notes=(
        'Per return (ARCHITECTURE.md 5.2-5.3): series diode from the connector, 1 k pull-up to +4.5 V, 220 R + 100 nF, LM339 against',
        'VREF (2.25 V). Output 1 = open, 0 = closed, as the ROM expects. Connector pin order follows the original drawing: check it with a meter.',
    ))
    jn = {p: f'RET{first + k}_IN' for k, p in enumerate(jpins)}; jn.update({keypin: 'NC', 10: 'GND'})
    S.at(Part(jref, 'Connector_Generic:Conn_01x10', f'{jref} SWITCH ROWS', {str(k): v for k, v in jn.items()}, kk396(10), mirror='y'), 8, 58)
    S.fan_in([(f'RET{first + k}_IN', (10, 54 + p - 1), (20, 18 + k * 11)) for k, p in enumerate(jpins)], 15)
    for k in range(8):
        y = 18 + k * 11
        return_channel(S, first + k, cmp_refs[k // 4], k % 4 + 1, y)
        S.fan(f'RET{first + k}', (43, y + 1), 56 - k if k < 4 else 53 + k - 4, (65, 53 + k))
    for j, u in enumerate(cmp_refs):
        S.at(Part(u, 'Comparator:LM339', 'LM339', {'3': '+4V5', '12': 'GND'}, FP['SO14'], unit=5), 100 + j * 10, 30)
    S.decaps('+4V5', ['100n', '100n'], 98, 44)
    S.decaps('+3V3', ['100n'], 106, 44)
    nn = {'16': '+3V3', '8': 'GND', '1': 'SW_LOAD_N', '2': 'SW_CLK', '15': 'GND', '7': 'NC', '10': chain_in, '9': chain_out}
    for pin, k in zip(['11', '12', '13', '14', '3', '4', '5', '6'], range(8)): nn[pin] = f'RET{first + k}'
    S.at(Part(uref, '74xx:74HC165', '74HC165', nn, FP['SO16']), 70, 58)
    S.port('SW_LOAD_N', 80 * U, 72 * U, 'R')
    S.port('SW_CLK', 80 * U, 74 * U, 'R')
    if extra: extra(S)
    return S

def vref(S):
    S.vr('3.3k', '+4V5', 'VREF', 70, 86)
    S.vr('3.3k', 'VREF', 'GND', 70, 92)
    S.vc('22u', 'VREF', 76, 92)
    S.port('VREF', 84 * U, 90 * U, 'R')
    S.tps(['VREF'], 92, 84)
    S.frame('Comparator reference (2.25 V)', 64 * U, 78 * U, 100 * U, 102 * U)
rows_page(1, 'J6', [1, 2, 3, 5, 6, 7, 8, 9], 4, 'U19', ['U8', 'U9'], 'CHAIN5', 'SW_DATA', extra=vref)
rows_page(9, 'J12', [1, 2, 3, 4, 6, 7, 8, 9], 5, 'U18', ['U10', 'U11'], 'CHAIN4', 'CHAIN5',
          extra=lambda S: S.port('VREF', 60 * U, 100 * U, 'R'))

# =====================================================================
# Dedicated switches
# =====================================================================
def ded_channel(S, name, cx, y, pull='1.5k'):
    nin = f'{name}_IN'
    S.vr(pull, '+4V5', nin, cx + 13, y - 4)
    S.hr('39k', nin, name, cx + 15, y)
    S.vc('47p', name, cx + 21, y + 1)
    S.vr('68k', name, 'GND', cx + 25, y + 1)

def ded_column(S, jref, npins, pinmap, extra_nets, first, uref, chain_in, chain_out, cx, title):
    jn = {p: f'DED{first + k}_IN' for k, p in enumerate(pinmap)}; jn.update(extra_nets)
    S.at(Part(jref, f'Connector_Generic:Conn_01x{npins:02d}', title, {str(k): v for k, v in jn.items()}, kk396(npins), mirror='y'), cx, 54)
    pin_y = lambda p: 54 - (5 if npins == 12 else 4) + p - 1
    items = [(f'DED{first + k}_IN', (cx + 2, pin_y(p)), (cx + 15, 18 + k * 10)) for k, p in enumerate(pinmap)]
    if npins == 12: items.append(('MEM_PROTECT_IN', (cx + 2, pin_y(10)), (cx + 15, 100)))
    S.fan_in(items, cx + 7)
    for k in range(8):
        y = 18 + k * 10
        ded_channel(S, f'DED{first + k}', cx, y)
        S.fan(f'DED{first + k}', (cx + 18, y), cx + (32 - k if k < 4 else 29 + k - 4), (cx + 44, 49 + k))
    nn = {'16': '+3V3', '8': 'GND', '1': 'SW_LOAD_N', '2': 'SW_CLK', '15': 'GND', '7': 'NC', '10': chain_in, '9': chain_out}
    for pin, k in zip(['11', '12', '13', '14', '3', '4', '5', '6'], range(8)): nn[pin] = f'DED{first + k}'
    S.at(Part(uref, '74xx:74HC165', '74HC165', nn, FP['SO16']), cx + 49, 54)
    S.decaps('+3V3', ['100n'], cx + 45, 74)

DED_NOTES = (
    'Per input (ARCHITECTURE.md 5.2-5.3): 1.5 k pull-up to +4.5 V (switch wetting current) and the original 39 k + 47 pF filter, plus 68 k to',
    'ground so the 3.3 V 74HC165 sees 2.8 V (open) or 0 V (closed). Connector pin to D-number order follows the original drawing: check it with a meter.',
)
S = page('Dedicated switches 1-16', 'sw_dedicated_1.kicad_sch', 'Dedicated switches D1-D16 (J2, J3) and coin door memory protect', notes=DED_NOTES + (
    'Memory protect (J2 pin 10) uses the same filter with the original 4.7 k pull-up and goes straight to RP2354B GPIO31.',))
ded_column(S, 'J2', 12, [1, 2, 3, 4, 6, 7, 8, 9], {5: 'NC', 10: 'MEM_PROTECT_IN', 11: 'GND', 12: 'GND'}, 1, 'U17', 'CHAIN3', 'CHAIN4', 6, 'J2 DEDICATED')
ded_channel(S, 'MEM_PROTECT', 6, 100, pull='4.7k')
S.port('MEM_PROTECT', 40 * U, 100 * U, 'R')
ded_column(S, 'J3', 10, [1, 2, 4, 5, 6, 7, 8, 9], {3: 'NC', 10: 'GND'}, 9, 'U16', 'CHAIN2', 'CHAIN3', 82, 'J3 DEDICATED')

S = page('Dedicated switches 17-24', 'sw_dedicated_2.kicad_sch', 'Dedicated switches D17-D24 (J13) and DIP switches', notes=DED_NOTES + (
    'The 8 DIP switches are read through the last 74HC165 of the chain (U14), whose serial input is tied low.',))
ded_column(S, 'J13', 10, [1, 3, 4, 5, 6, 7, 8, 9], {2: 'NC', 10: 'GND'}, 17, 'U15', 'CHAIN1', 'CHAIN2', 6, 'J13 DEDICATED')
dn = {str(i): f'DIP{i}' for i in range(1, 9)}; dn.update({str(9 + i): 'GND' for i in range(8)})
S.at(Part('SW3', 'Switch:SW_DIP_x08', 'DIP x8', dn, 'Button_Switch_THT:SW_DIP_SPSTx08_Slide_9.78x22.5mm_W7.62mm_P2.54mm', mirror='y'), 96, 52)
for i in range(8):
    S.vr('10k', '+3V3', f'DIP{i + 1}', 102 + 4 * i, 32)
nn = {'16': '+3V3', '8': 'GND', '1': 'SW_LOAD_N', '2': 'SW_CLK', '15': 'GND', '7': 'NC', '10': 'GND', '9': 'CHAIN1'}
for pin, k in zip(['11', '12', '13', '14', '3', '4', '5', '6'], range(8)): nn[pin] = f'DIP{k + 1}'
S.at(Part('U14', '74xx:74HC165', '74HC165', nn, FP['SO16']), 140, 58)
S.decaps('+3V3', ['100n'], 132, 80)

# =====================================================================
# Display (J5) and GI dimmer header (J18)
# =====================================================================
S = page('Display and GI', 'display_gi.kicad_sch', 'J5 original DMD driver and J18 GI dimmer header', notes=(
    'J5 pinout read from the original drawing (ARCHITECTURE.md 8): signals on odd pins, ground on even pins. Confirm with a meter (Q18).',
    'The 100 k pull-downs keep the DMD lines low while the RP2354B boots.',
    'J18 is the default GI dimmer link of ARCHITECTURE.md 10.2: +5 V, GND, GI_PWM, GI_SPARE.',
))
dmd = ['DMD_DE', 'DMD_ROWDATA', 'DMD_ROWCLK', 'DMD_COLLATCH_A', 'DMD_PIXCLK', 'DMD_SDATA', 'DMD_COLLATCH_B']
n = {'20': '+5V', '10': 'GND', '1': '+5V', '19': 'GND', '9': 'GND', '11': 'NC'}
for i, s_ in enumerate(dmd):
    n[str(2 + i)] = s_; n[str(18 - i)] = f'J5B{i}'
u21 = S.at(Part('U21', '74xx:74HC245', '74HCT245', n, FP['TSSOP20']), 60, 50)
S.pack(u21, ['18', '17', '16', '15'], [f'J5_{s_[4:]}' for s_ in dmd[:4]], 74)
S.pack(u21, ['14', '13', '12', '11'], [f'J5_{s_[4:]}' for s_ in dmd[4:]] + ['NC'], 74)
for i, s_ in enumerate(dmd):
    S.port(s_, 22 * U, (45 + i) * U, 'L')
    S.vr('100k', s_, 'GND', 26 + 4 * i, 55)
S.decaps('+5V', ['100n'], 70, 68)
j5 = {str(2 * i + 1): f'J5_{s_[4:]}' for i, s_ in enumerate(dmd)}
j5.update({str(2 * i + 2): 'GND' for i in range(7)})
S.at(Part('J5', 'Connector_Generic:Conn_02x07_Odd_Even', 'J5 DMD', j5, 'Connector_IDC:IDC-Header_2x07_P2.54mm_Vertical'), 100, 46)
S.at(conn('J18', 4, {1: '+5V', 2: 'GND', 3: 'J18_GI_PWM', 4: 'J18_GI_SPARE'}, kk254(4), 'J18 GI DIMMER'), 100, 88)
S.port('GI_PWM', 30 * U, 85 * U, 'L')
S.port('GI_SPARE', 30 * U, 92 * U, 'L')
S.hr('100', 'GI_PWM', 'J18_GI_PWM', 60, 85)
S.hr('100', 'GI_SPARE', 'J18_GI_SPARE', 60, 92)
S.vr('100k', 'GI_PWM', 'GND', 44, 87)
S.frame('Original DMD (J5)', 12 * U, 28 * U, 112 * U, 76 * U)
S.frame('GI dimmer board link (J18)', 12 * U, 78 * U, 112 * U, 100 * U)

# =====================================================================
# Audio
# =====================================================================
S = page('Audio', 'audio.kicad_sch', 'Audio: PCM5102A, TDA7297 stereo + subwoofer (+12 V)', notes=(
    'Single +12 V supply (J23). U23 drives left / right in bridge (BTL): no output capacitor, but no speaker wire may go to ground.',
    'J10 keeps the original connector: pins 1 / 2 = left + / right +, pins 3 / 4 (ground on the original) = left - / right -. Check the harness keeps the two speaker returns separate.',
    'J22 = the same two channels as pairs (L+ L- R+ R-). Subwoofer: (L + R) / 2 through a 110 Hz 2nd-order low-pass (U26), U24 drives two bridged outputs on J24 (dual voice coil or two subwoofers).',
    'TDA7297 gain is fixed at 32 dB: 22k / 1.8k input dividers give full output at DAC full scale. AMP_MUTE (RP2354B GPIO37) high mutes all outputs. U23 / U24 need a heatsink.',
))
S.at(Part('U22', 'Audio:PCM5102A', 'PCM5102A',
          {'15': 'I2S_LRCK', '14': 'I2S_DIN', '13': 'I2S_BCK', '12': 'GND', '11': 'GND', '10': 'GND', '17': 'DAC_XSMT',
           '16': 'GND', '1': '+3V3', '3': 'GND', '20': '+3V3', '19': 'GND', '8': '+3V3_A', '9': 'GND',
           '6': 'DAC_OUTL', '7': 'DAC_OUTR', '2': 'DAC_CAPP', '4': 'DAC_CAPM', '18': 'DAC_LDOO', '5': 'DAC_VNEG'}), 30, 56)
S.hr('10k', '+3V3', 'DAC_XSMT', 15, 59)
for n_, y_ in (('I2S_LRCK', 52), ('I2S_DIN', 53), ('I2S_BCK', 54)):
    S.port(n_, 14 * U, y_ * U, 'L')
S.vc('2.2u', 'DAC_CAPP', 40, 55, n2='DAC_CAPM')
S.vc('2.2u', 'DAC_LDOO', 44, 60)
S.vc('2.2u', 'DAC_VNEG', 48, 61)
S.at(Part('FB4', 'Device:FerriteBead_Small', 'FB', {'1': '+3V3', '2': '+3V3_A'}, FP['FB']), 40, 41)
S.vc('10u', '+3V3_A', 44, 43)
S.at(flag('+3V3_A'), 48, 42)
S.decaps('+3V3', ['100n', '100n', '10u'], 10, 70)
S.label_nets |= {'AFL', 'AFR', 'SUB_OUT', 'AMP_STBY', 'AMP_PLAY'}

def amp_in(S, src, tag, x, y, flt=True):
    """DAC output -> (470 R / 2.2 nF filter) -> 22k / 1.8k divider -> 1 uF -> TDA7297 input"""
    if flt:
        S.hr('470', src, f'AF{tag}', x, y)
        S.vc('2.2n', f'AF{tag}', x + 5, y + 1)
        src = f'AF{tag}'
    S.hr('22k', src, f'AD{tag}', x + 7, y)
    S.vr('1.8k', f'AD{tag}', 'GND', x + 12, y + 1)
    S.hc('1u', f'AD{tag}', f'AIN{tag}', x + 14, y)

def tda7297(S, uref, ins, outs, x, y, dy=14):
    """both bridge channels of one TDA7297 (units 1 and 2) plus its supply unit"""
    (i1, i2), (o1p, o1n, o2p, o2n) = ins, outs
    S.at(Part(uref, 'Amplifier_Audio:TDA7297', 'TDA7297', {'4': i1, '1': o1p, '2': o1n, '6': 'AMP_PLAY', '7': 'AMP_STBY',
                                                           '5': 'NC', '10': 'NC', '11': 'NC'},
              'Package_TO_SOT_THT:TO-220-15_P2.54x5.08mm_StaggerOdd_Lead4.58mm_Vertical', unit=1), x, y)
    S.at(Part(uref, 'Amplifier_Audio:TDA7297', 'TDA7297', {'12': i2, '15': o2p, '14': o2n},
              'Package_TO_SOT_THT:TO-220-15_P2.54x5.08mm_StaggerOdd_Lead4.58mm_Vertical', unit=2), x, y + dy)
    S.at(Part(uref, 'Amplifier_Audio:TDA7297', 'TDA7297', {'3': '+12V', '13': '+12V', '8': 'GND', '9': 'GND'},
              'Package_TO_SOT_THT:TO-220-15_P2.54x5.08mm_StaggerOdd_Lead4.58mm_Vertical', unit=3), x + 14, y + dy // 2)
    S.decaps('+12V', ['100n', '470u'], x + 22, y + 2, dx=5)

# stereo amplifier
amp_in(S, 'DAC_OUTL', 'L', 54, 22)
amp_in(S, 'DAC_OUTR', 'R', 54, 36)
tda7297(S, 'U23', ('AINL', 'AINR'), ('SPK_LP', 'SPK_LN', 'SPK_RP', 'SPK_RN'), 82, 22)
# subwoofer: (L + R) / 2, 2nd-order Sallen-Key low-pass about 110 Hz, Q about 0.74, on a 6 V bias
S.hc('1u', 'AFL', 'SUB_CL', 54, 60)
S.hc('1u', 'AFR', 'SUB_CR', 54, 64)
S.hr('20k', 'SUB_CL', 'SUB_SUM', 58, 60)
S.hr('20k', 'SUB_CR', 'SUB_SUM', 58, 64)
S.vr('100k', 'SUB_SUM', 'SUB_BIAS', 63, 66)
S.hr('10k', 'SUB_SUM', 'SUB_P', 64, 60)
S.vc('100n', 'SUB_P', 69, 62)
S.hc('220n', 'SUB_SUM', 'SUB_OUT', 64, 55)
S.at(Part('U26', 'Amplifier_Operational:OPA1678', 'OPA1678', {'3': 'SUB_P', '2': 'SUB_OUT', '1': 'SUB_OUT'}, FP['SO8'], unit=1), 76, 60)
S.at(Part('U26', 'Amplifier_Operational:OPA1678', 'OPA1678', {'5': 'SUB_BIAS', '6': 'SUB_SPARE', '7': 'SUB_SPARE'}, FP['SO8'], unit=2), 76, 72)
S.at(Part('U26', 'Amplifier_Operational:OPA1678', 'OPA1678', {'8': '+12V', '4': 'GND'}, FP['SO8'], unit=3), 88, 60)
S.decaps('+12V', ['100n'], 92, 58)
S.vr('10k', '+12V', 'SUB_BIAS', 58, 72)
S.vr('10k', 'SUB_BIAS', 'GND', 58, 78)
S.vc('10u', 'SUB_BIAS', 63, 78)
S.hc('1u', 'SUB_OUT', 'SUB_AC', 54, 88)
amp_in(S, 'SUB_AC', 'S', 54, 88, flt=False)
tda7297(S, 'U24', ('AINS', 'AINS'), ('SUB1P', 'SUB1N', 'SUB2P', 'SUB2N'), 100, 80, dy=12)
# standby (soft start) and mute, shared by both amplifiers
S.vr('10k', '+5V', 'AMP_STBY', 112, 56)
S.vc('10u', 'AMP_STBY', 116, 62)
S.vr('10k', '+5V', 'AMP_PLAY', 120, 56)
S.vc('10u', 'AMP_PLAY', 124, 62)
S.at(Part('Q4', 'Transistor_FET:2N7002', '2N7002', {'1': 'AMP_MUTE', '3': 'AMP_PLAY', '2': 'GND'}), 128, 68)
S.vr('100k', 'AMP_MUTE', 'GND', 120, 70)
S.port('AMP_MUTE', 112 * U, 69 * U, 'L')
S.at(conn('J10', 4, {1: 'SPK_LP', 2: 'SPK_RP', 3: 'SPK_LN', 4: 'SPK_RN'}, kk396(4), 'J10 SPEAKERS'), 140, 24)
S.at(conn('J22', 4, {1: 'SPK_LP', 2: 'SPK_LN', 3: 'SPK_RP', 4: 'SPK_RN'}, kk396(4), 'J22 STEREO'), 140, 40)
S.at(conn('J24', 4, {1: 'SUB1P', 2: 'SUB1N', 3: 'SUB2P', 4: 'SUB2N'}, kk396(4), 'J24 SUBWOOFER'), 140, 84)
S.tps(['DAC_OUTL', 'DAC_OUTR', 'SUB_OUT', 'GND'], 12, 90)
S.frame('Stereo amplifier (bridge)', 52 * U, 14 * U, 132 * U, 50 * U)
S.frame('Subwoofer low-pass', 52 * U, 52 * U, 94 * U, 98 * U)
S.frame('Subwoofer amplifier', 96 * U, 76 * U, 132 * U, 98 * U)
S.frame('Standby / mute', 108 * U, 52 * U, 132 * U, 74 * U)

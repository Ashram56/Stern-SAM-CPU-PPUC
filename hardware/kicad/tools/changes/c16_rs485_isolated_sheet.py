"""Change 16 (2026-10-07): rewrite page 13 ('RS485 and I2S', created by c13) for Vincent's review of draft 0.6:

- U32 is now an isolated transceiver, ADM2682E (isoPower, 5 kV, 16 Mbps): everything on the cable side (TVS,
  termination, both RJ45 GND pins) sits on its own ground GND_ISO, like Stern's node boards.
- Two top-entry RJ45s in parallel (J27 in, J29 out), OST PJ012 vertical.
- J30: switched 3.5 mm stereo jack for the Pi 4's analog output. With no plug the DAC drives the amplifiers through
  the jack's normally-closed contacts; a plug disconnects the DAC (c17 splits the two DAC output wires on the audio
  sheet into AUD_DAC_L / R and AUD_AMP_L / R).
- J28 (I2S header) unchanged.

Only this sheet file is rewritten (same generator as c13, so U32 / R204-R212 / C127 / D27 / JP2 / J27 / J28 keep their
UUIDs). New refs: C128-C132, J29, J30.
"""
import collections
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLS)
import design2
from design2 import P, Part, FP, U, R
from kigen import uid, write

SCH = os.path.join(TOOLS, '..', 'sam_cpu')
FN = 'rs485_i2s.kicad_sch'
NAME = 'RS485 and I2S'
PAGE = 13
CLI = os.environ.get('KICAD_CLI', 'kicad-cli')

S = P(NAME, FN, 'Isolated RS485 port (2x RJ45), I2S input header, analog line-in', notes=(
    'Half-duplex RS485 on J27 / J29 (in parallel, top-entry RJ45: pin 1 A, pin 2 B, pins 7 / 8 GND_ISO). ADM2682E isolated',
    'transceiver: the cable side (A / B, SM712 TVS, 120 R termination on JP2, RJ45 ground) is on GND_ISO, powered by the',
    'chip\'s own isoPower converter (VISO). Keep GND and GND_ISO copper apart under U32. DE / RE tied: receive by default.',
    'Pi on J21: Pi UART3 (GPIO4 TX, GPIO5 RX, GPIO7 RTS = driver enable). Pi remote: RP2354B UART1 (GPIO20 TX, GPIO21 RX,',
    'GPIO22 driver enable). Both reach the transceiver through 1 k: only the configured side drives.',
    'J28: I2S from a remote Pi to the PCM5102A (in parallel with J21 pins 12 / 35 / 40); keep that cable short.',
    'J30: line-in (e.g. Pi 4 headphone out). No plug: DAC -> amplifiers through the jack contacts. Plug in: DAC cut off.',
))

SOT23 = 'Package_TO_SOT_SMD:SOT-23'
RJ45 = 'Connector_RJ:RJ45_OST_PJ012-8P8CX_Vertical'

# isolated transceiver; logic side on +3V3 / GND, cable side on VISO / GND_ISO; half duplex (Y-A, Z-B)
S.at(Part('U32', 'Interface_UART:ADM2682E', 'ADM2682E', {
    '1': 'GND', '2': '+3V3', '3': 'RS485_RO', '4': 'RS485_DE', '5': 'RS485_DE', '6': 'RS485_DI', '7': '+3V3',
    '8': 'GND', '9': 'GND_ISO', '10': 'VISO', '11': 'RS485_A', '12': 'RS485_B', '13': 'RS485_B', '14': 'RS485_A',
    '15': 'VISO', '16': 'GND_ISO'}, 'Package_SO:SOIC-16W_7.5x12.8mm_P1.27mm'), 50, 40)
S.hr('1k', 'PI_RS485_RX', 'RS485_RO', 14, 28, ref='R204')
S.hr('1k', 'RP_RS485_RX', 'RS485_RO', 14, 32, ref='R205')
S.hr('1k', 'PI_RS485_TX', 'RS485_DI', 14, 40, ref='R206')
S.hr('1k', 'RP_RS485_TX', 'RS485_DI', 14, 44, ref='R207')
S.hr('1k', 'PI_RS485_DE', 'RS485_DE', 14, 52, ref='R208')
S.hr('1k', 'RP_RS485_DE', 'RS485_DE', 14, 56, ref='R209')
S.vr('10k', 'RS485_DE', 'GND', 30, 60, ref='R210')
S.vr('10k', '+3V3', 'RS485_RO', 30, 18, ref='R212')
# decoupling per the ADM2682E data sheet: VCC 100n + 10u (pin 2), 100n (pin 7); VISOOUT 100n + 10u, VISOIN 100n
S.at(Part('C127', 'Device:C', '100n', {'1': '+3V3', '2': 'GND'}, FP['C']), 36, 21.5)
S.at(Part('C128', 'Device:C', '10u', {'1': '+3V3', '2': 'GND'}, FP['C0805']), 40, 21.5)
S.at(Part('C129', 'Device:C', '100n', {'1': '+3V3', '2': 'GND'}, FP['C']), 44, 21.5)
S.at(Part('C130', 'Device:C', '100n', {'1': 'VISO', '2': 'GND_ISO'}, FP['C']), 60, 21.5)
S.at(Part('C131', 'Device:C', '10u', {'1': 'VISO', '2': 'GND_ISO'}, FP['C0805']), 64, 21.5)
S.at(Part('C132', 'Device:C', '100n', {'1': 'VISO', '2': 'GND_ISO'}, FP['C']), 68, 21.5)
S.at(Part('#FLG1301', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'VISO'}, '', rotation=180), 72, 21)
S.at(Part('#FLG1302', 'power:PWR_FLAG', 'PWR_FLAG', {'1': 'GND_ISO'}, ''), 72, 66)
# cable side: TVS, switchable termination, two RJ45 in parallel (in / out)
S.at(Part('D27', 'Diode:SM712_SOT23', 'SM712', {'1': 'RS485_A', '2': 'RS485_B', '3': 'GND_ISO'}, SOT23), 70, 58)
S.vr('120', 'RS485_A', 'RS485_TERM', 78, 30, ref='R211')
S.at(Part('JP2', 'Jumper:Jumper_2_Open', 'TERM', {'1': 'RS485_TERM', '2': 'RS485_B'},
          'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'), 82, 44)
RJ = {'1': 'RS485_A', '2': 'RS485_B', '3': 'NC', '4': 'NC', '5': 'NC', '6': 'NC', '7': 'GND_ISO', '8': 'GND_ISO'}
S.at(Part('J27', 'Connector:RJ45', 'J27 RS485 IN', RJ, RJ45), 98, 30)
S.at(Part('J29', 'Connector:RJ45', 'J29 RS485 OUT', RJ, RJ45), 98, 56)
# I2S input for a remote Pi
S.at(Part('J28', 'Connector_Generic:Conn_02x03_Odd_Even', 'J28 I2S IN', {
    '1': 'I2S_BCK', '2': 'GND', '3': 'I2S_LRCK', '4': 'GND', '5': 'I2S_DIN', '6': 'GND'},
    'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical'), 30, 96)
# analog line-in: normally-closed tip / ring contacts pass the DAC through
S.at(Part('J30', 'Connector_Audio:AudioJack3_SwitchTR', 'J30 LINE IN', {
    'T': 'AUD_AMP_L', 'TN': 'AUD_DAC_L', 'R': 'AUD_AMP_R', 'RN': 'AUD_DAC_R', 'S': 'GND'},
    'Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'), 80, 96)
S.frame('Isolated RS485 port (J27 in, J29 out)', 6 * U, 15 * U, 112 * U, 72 * U)
S.frame('I2S input header (J28)', 6 * U, 80 * U, 56 * U, 110 * U)
S.frame('Analog line-in (J30)', 60 * U, 80 * U, 112 * U, 110 * U)

LOCAL = {'RS485_RO', 'RS485_DI', 'RS485_DE', 'RS485_A', 'RS485_B', 'RS485_TERM', 'VISO'}
glob = {n for part in S.parts for n in part.nets.values()} - LOCAL - {'NC'}
from sch import POWER
POWER['GND_ISO'] = ('power:GNDPWR', True)          # cable-side ground: its own ground symbol
glob -= set(POWER)
OUTS = {'output', 'tri_state', 'open_collector', 'open_emitter', 'power_out'}
types = collections.defaultdict(set)
for part in S.parts:
    for q in part.unit_pins():
        nn = part.nets.get(q['number'])
        if nn in glob:
            types[nn].add(q['type'])
shapes = {}
for nn, ts in types.items():
    if ts & OUTS and 'input' not in ts and 'bidirectional' not in ts:
        s = 'output'
    elif ts <= {'input'} or ts <= {'input', 'passive'} and 'input' in ts:
        s = 'input'
    elif 'bidirectional' in ts:
        s = 'bidirectional'
    else:
        s = 'passive'
    shapes[(S.name, nn)] = s
D = design2.D
S.pwr_base = PAGE * 1000
path = f'/{D.root_uuid}/{uid("sheet", FN)}'
S.build(D, glob, path, shapes)
if S.failed:
    print('label fallbacks:', S.failed)
write(os.path.join(SCH, FN), S.emit(D, path, shapes))
subprocess.run([CLI, 'sch', 'upgrade', '--force', os.path.join(SCH, FN)], check=True, capture_output=True)


# the root sheet symbol and the .kicad_pro entry exist since c13; refresh the page description on the root sheet
root = os.path.join(SCH, 'sam_cpu.kicad_sch')
t = open(root).read()
t2 = t.replace('(text "RS485 port (RJ45) and I2S input header"', '(text "%s"' % S.title)
if t2 != t:
    open(root, 'w').write(t2)
print('wrote', FN, len(S.parts), 'symbols')

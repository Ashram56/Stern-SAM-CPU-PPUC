"""Change 13 (2026-10-07): add the 'RS485 and I2S' sheet (new file, page 13) and its sheet symbol on the root.

Existing sheets are not regenerated; c14 adds the matching labels on the MCU sheet. New refs are explicit:
U32, R204-R212, C127, D27, JP2, J27, J28.

Vincent's two set-ups share one RS485 port (RJ45, J27):
1. Pi on J21: the port is the Pi's UART3 (GPIO4 TXD3, GPIO5 RXD3, GPIO7 RTS3 as driver enable).
2. Pi remote: the port is the RP2354B's UART1 (GPIO20 TX, GPIO21 RX, GPIO22 driver enable), and the remote Pi's
   I2S reaches the DAC through J28.
Both sides are wired to the transceiver through 1 k resistors; only the side that is configured drives, the other
leaves its pins as inputs (both boot that way). A wrong configuration costs about 1.6 mA, nothing breaks.
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
import schlib as L

SCH = os.path.join(TOOLS, '..', 'sam_cpu')
FN = 'rs485_i2s.kicad_sch'
NAME = 'RS485 and I2S'
PAGE = 13
CLI = os.environ.get('KICAD_CLI', 'kicad-cli')

S = P(NAME, FN, 'RS485 port (RJ45) and I2S input header', notes=(
    'One half-duplex RS485 port on J27 (RJ45: pin 1 A, pin 2 B, pins 7 / 8 GND, DMX-over-RJ45 order). THVD1450: 3.3 V,',
    'bus fail-safe, +-18 kV ESD; SM712 TVS for the cable; 120 R termination fitted with the JP2 jumper (end of line only).',
    'Pi on J21: Pi UART3 (GPIO4 TX, GPIO5 RX, GPIO7 RTS = driver enable, Linux RS485 mode). Pi remote: RP2354B UART1',
    '(GPIO20 TX, GPIO21 RX, GPIO22 driver enable). Both reach the transceiver through 1 k: only the configured side drives.',
    'J28: I2S from a remote Pi to the PCM5102A (in parallel with J21 pins 12 / 35 / 40). Keep that cable short: I2S is clocked',
    'logic and has the same long-wire limits as the DMD links that were removed.',
))

SOT23 = 'Package_TO_SOT_SMD:SOT-23'

# transceiver, receive by default (DE / RE pulled low), RO pulled up while the receiver is off
u = S.at(Part('U32', 'Interface_UART:THVD1450D', 'THVD1450', {
    '1': 'RS485_RO', '2': 'RS485_DE', '3': 'RS485_DE', '4': 'RS485_DI', '5': 'GND', '6': 'RS485_A', '7': 'RS485_B',
    '8': '+3V3'}, FP['SO8']), 50, 40)
S.hr('1k', 'PI_RS485_RX', 'RS485_RO', 16, 30, ref='R204')
S.hr('1k', 'RP_RS485_RX', 'RS485_RO', 16, 34, ref='R205')
S.hr('1k', 'PI_RS485_TX', 'RS485_DI', 16, 42, ref='R206')
S.hr('1k', 'RP_RS485_TX', 'RS485_DI', 16, 46, ref='R207')
S.hr('1k', 'PI_RS485_DE', 'RS485_DE', 16, 52, ref='R208')
S.hr('1k', 'RP_RS485_DE', 'RS485_DE', 16, 56, ref='R209')
S.vr('10k', 'RS485_DE', 'GND', 32, 60, ref='R210')
S.vr('10k', '+3V3', 'RS485_RO', 32, 20, ref='R212')
S.at(Part('C127', 'Device:C', '100n', {'1': '+3V3', '2': 'GND'}, FP['C']), 60, 21.5)
# line side: TVS, switchable termination, RJ45
S.at(Part('D27', 'Diode:SM712_SOT23', 'SM712', {'1': 'RS485_A', '2': 'RS485_B', '3': 'GND'}, SOT23), 70, 58)
S.vr('120', 'RS485_A', 'RS485_TERM', 76, 30, ref='R211')
S.at(Part('JP2', 'Jumper:Jumper_2_Open', 'TERM', {'1': 'RS485_TERM', '2': 'RS485_B'},
          'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'), 80, 44)
S.at(Part('J27', 'Connector:RJ45', 'J27 RS485', {'1': 'RS485_A', '2': 'RS485_B', '3': 'NC', '4': 'NC', '5': 'NC',
                                                 '6': 'NC', '7': 'GND', '8': 'GND'},
          'Connector_RJ:RJ45_Amphenol_54602-x08_Horizontal'), 96, 40)
# I2S input for a remote Pi
S.at(Part('J28', 'Connector_Generic:Conn_02x03_Odd_Even', 'J28 I2S IN', {
    '1': 'I2S_BCK', '2': 'GND', '3': 'I2S_LRCK', '4': 'GND', '5': 'I2S_DIN', '6': 'GND'},
    'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical'), 40, 96)
S.frame('RS485 port (J27)', 6 * U, 14 * U, 108 * U, 72 * U)
S.frame('I2S input header (J28)', 6 * U, 80 * U, 108 * U, 108 * U)

LOCAL = {'RS485_RO', 'RS485_DI', 'RS485_DE', 'RS485_A', 'RS485_B', 'RS485_TERM'}
glob = {n for part in S.parts for n in part.nets.values()} - LOCAL - {'NC'}
from sch import POWER
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

# root sheet symbol (page 13) on the 3-column grid, copied from the audio sheet symbol
root = os.path.join(SCH, 'sam_cpu.kicad_sch')
s = open(root).read()
suid = uid('sheet', FN)
if suid not in s:
    head, blocks, foot = L.split(s)
    sheets = [b for b in blocks if L.kind(b) == 'sheet']
    tmpl = [b for b in sheets if '"audio.kicad_sch"' in b][0]
    ax, ay, _ = L.at(tmpl)
    k = PAGE - 1
    nx, ny = 25.4 + (k % 3) * 127.0, 63.5 + (k // 3) * 45.72
    dx, dy = nx - ax, ny - ay

    def shift(m):
        return '(at %s %s' % (L.fmt(float(m.group(1)) + dx), L.fmt(float(m.group(2)) + dy))
    nb = re.sub(r'\(at ([-\d.]+) ([-\d.]+)', shift, tmpl)
    nb = nb.replace('"audio.kicad_sch"', '"%s"' % FN).replace('"Audio"', '"%s"' % NAME)
    nb = re.sub(r'\(page "11"\)', '(page "%d")' % PAGE, nb)
    old_uuid = re.search(r'\(uuid "([^"]+)"\)', tmpl).group(1)
    nb = nb.replace(old_uuid, suid)
    texts = [b for b in blocks if L.kind(b) == 'text' and L.at(b) and abs(L.at(b)[0] - ax - 2.54) < 0.01
             and abs(L.at(b)[1] - ay - 5.08) < 0.01]
    nt = re.sub(r'\(at ([-\d.]+) ([-\d.]+)', shift, texts[0])
    nt = re.sub(r'\(text "[^"]*"', '(text "%s"' % S.title, nt)
    nt = re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % uid('rootdesc', FN), nt)
    i = blocks.index(texts[0])
    blocks[i + 1:i + 1] = [nb, nt]
    open(root, 'w').write(L.join(head, blocks, foot))
pro = os.path.join(SCH, 'sam_cpu.kicad_pro')
pj = json.load(open(pro))
if [suid, NAME] not in pj['sheets']:
    pj['sheets'].append([suid, NAME])
    json.dump(pj, open(pro, 'w'), indent=2)
print('wrote', FN, len(S.parts), 'symbols')

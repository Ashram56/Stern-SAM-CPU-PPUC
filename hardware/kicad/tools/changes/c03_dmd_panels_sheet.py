"""Change 03 (2026-10-06): add the 'DMD panels' sheet (new file, page 12) and its sheet symbol on the root.
Existing sheets are not touched by this script. New refs are explicit: U27-U31, RN6-RN11, C122-C126, J25, J26, TP23-TP24."""
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, TOOLS)
import design2
from design2 import P, Part, FP, U, conn, R
from kigen import uid, write
import schlib as L

SCH = os.path.join(TOOLS, '..', 'sam_cpu')
FN = 'dmd_panels.kicad_sch'
NAME = 'DMD panels'
CLI = os.environ.get('KICAD_CLI', 'kicad-cli')

S = P(NAME, FN, 'HD DMD panels (HUB75) and switch-chain extensions', notes=(
    'Two HUB75 panels (J25 = panel A, J26 = panel B) on 17 RP2354B lines (PIO2): 6 colour bits per panel (R1 G1 B1 R2 G2 B2),',
    'shared CLK, LAT, OE and 2 row-address lines (A, B). 74AHCT245 buffers on +5 V (HUB75 is 5 V logic), 33 R series resistors.',
    'Panel A data = DMD_D0-D5 (GPIO20-25), panel B = DMD_D6-D11 (GPIO26-31). DMD_D0-D6 also drive the original DMD buffer (J5):',
    'only one display path runs at a time. HUB75 C, D, E (pins 11, 12, 8) are not connected: panels with 4-5 row lines need 3 more GPIOs.',
    'U31: first 74HC595 of the strobe chain (status LED, GI_SPARE, 6 spare outputs). U30: last 74HC165 of the switch chain',
    '(coin door memory protect + 7 spare inputs). Both share SW_CLK and SW_LOAD_N (165 load / 595 latch on one pulse).',
))

TSSOP = FP['TSSOP20']


def buf(ref, ins, outs, x, y):
    n = {'20': '+5V', '10': 'GND', '1': '+5V', '19': 'GND'}
    for i in range(8):
        n[str(2 + i)] = ins[i]
        n[str(18 - i)] = outs[i]
    return S.at(Part(ref, '74xx:74HC245', '74AHCT245', n, TSSOP), x, y)


def rpack(ref, ic, pins, outs, x):
    rn = S.pack(ic, pins, outs, x)
    rn.ref = ref
    return rn


A = ['R1', 'G1', 'B1', 'R2', 'G2', 'B2', 'CLK', 'LAT']
ua = buf('U27', [f'DMD_D{i}' for i in range(6)] + ['DMD_CLK', 'DMD_LAT'], [f'PA_{s}_B' for s in A], 34, 26)
ub = buf('U28', [f'DMD_D{i}' for i in range(6, 12)] + ['DMD_CLK', 'DMD_LAT'], [f'PB_{s}_B' for s in A], 34, 56)
C3 = ['PA_OE', 'PB_OE', 'PA_ROWA', 'PB_ROWA', 'PA_ROWB', 'PB_ROWB']
uc = buf('U29', ['DMD_OE', 'DMD_OE', 'DMD_A', 'DMD_A', 'DMD_B', 'DMD_B', 'GND', 'GND'],
         [f'{s}_B' for s in C3] + ['NC', 'NC'], 34, 86)
rpack('RN6', ua, ['18', '17', '16', '15'], [f'PA_{s}' for s in A[:4]], 48)
rpack('RN7', ua, ['14', '13', '12', '11'], [f'PA_{s}' for s in A[4:]], 48)
rpack('RN8', ub, ['18', '17', '16', '15'], [f'PB_{s}' for s in A[:4]], 48)
rpack('RN9', ub, ['14', '13', '12', '11'], [f'PB_{s}' for s in A[4:]], 48)
rpack('RN10', uc, ['18', '17', '16', '15'], C3[:4], 48)
rpack('RN11', uc, ['14', '13', '12', '11'], C3[4:] + ['NC', 'NC'], 48)
for k, (ref, x) in enumerate([('C122', 22), ('C123', 26), ('C124', 30)]):
    S.at(Part(ref, 'Device:C', '100n', {'1': '+5V', '2': 'GND'}, FP['C']), x, 106.5)


def hub75(ref, p, x, y, title):
    n = {'1': f'{p}_R1', '2': f'{p}_G1', '3': f'{p}_B1', '4': 'GND', '5': f'{p}_R2', '6': f'{p}_G2', '7': f'{p}_B2',
         '8': 'NC', '9': f'{p}_ROWA', '10': f'{p}_ROWB', '11': 'NC', '12': 'NC', '13': f'{p}_CLK', '14': f'{p}_LAT',
         '15': f'{p}_OE', '16': 'GND'}
    S.at(Part(ref, 'Connector_Generic:Conn_02x08_Odd_Even', title, n, 'Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical'), x, y)


hub75('J25', 'PA', 84, 34, 'J25 HUB75 PANEL A')
hub75('J26', 'PB', 84, 66, 'J26 HUB75 PANEL B')
# first 595 of the strobe chain
n = {'16': '+3V3', '8': 'GND', '14': 'STB_DATA', '11': 'SW_CLK', '10': '+3V3', '12': 'SW_LOAD_N', '13': 'GND',
     '9': 'STB_CHAIN', '15': 'LED_STATUS', '1': 'GI_SPARE'}
for pin in ['2', '3', '4', '5', '6', '7']: n[pin] = 'NC'
S.at(Part('U31', '74xx:74HC595', '74HC595', n, FP['SO16']), 128, 30)
S.at(Part('C125', 'Device:C', '100n', {'1': '+3V3', '2': 'GND'}, FP['C']), 118, 46.5)
# last 165 of the switch chain
n = {'16': '+3V3', '8': 'GND', '1': 'SW_LOAD_N', '2': 'SW_CLK', '15': 'GND', '7': 'NC', '10': 'CHAIN6', '9': 'SW_DATA',
     '11': 'MEM_PROTECT'}
for pin in ['12', '13', '14', '3', '4', '5', '6']: n[pin] = 'GND'
S.at(Part('U30', '74xx:74HC165', '74HC165', n, FP['SO16']), 128, 72)
S.at(Part('C126', 'Device:C', '100n', {'1': '+3V3', '2': 'GND'}, FP['C']), 118, 88.5)
S.at(Part('TP23', 'Connector:TestPoint', 'DMD_CLK', {'1': 'DMD_CLK'}, 'TestPoint:TestPoint_Pad_D1.5mm'), 12, 100)
S.at(Part('TP24', 'Connector:TestPoint', 'DMD_LAT', {'1': 'DMD_LAT'}, 'TestPoint:TestPoint_Pad_D1.5mm'), 16, 100)
S.frame('HD panel buffers and HUB75 connectors', 6 * U, 14 * U, 104 * U, 112 * U)
S.frame('Switch chain extensions', 108 * U, 14 * U, 156 * U, 100 * U)

LOCAL = {n for part in S.parts for n in part.nets.values() if n.startswith(('PA_', 'PB_'))}
glob = {n for part in S.parts for n in part.nets.values()} - LOCAL - {'NC'}
from sch import POWER
glob -= set(POWER)
OUTS = {'output', 'tri_state', 'open_collector', 'open_emitter', 'power_out'}
import collections
types = collections.defaultdict(set)
for part in S.parts:
    for q in part.unit_pins():
        nn = part.nets.get(q['number'])
        if nn in glob: types[nn].add(q['type'])
shapes = {}
for nn, ts in types.items():
    if ts & OUTS and 'input' not in ts and 'bidirectional' not in ts: s = 'output'
    elif ts <= {'input'} or ts <= {'input', 'passive'} and 'input' in ts: s = 'input'
    elif 'bidirectional' in ts: s = 'bidirectional'
    else: s = 'passive'
    shapes[(S.name, nn)] = s
D = design2.D
S.pwr_base = 12000
path = f'/{D.root_uuid}/{uid("sheet", FN)}'
S.build(D, glob, path, shapes)
if S.failed:
    print('label fallbacks:', S.failed)
write(os.path.join(SCH, FN), S.emit(D, path, shapes))
subprocess.run([CLI, 'sch', 'upgrade', '--force', os.path.join(SCH, FN)], check=True, capture_output=True)

# root sheet symbol (page 12), next to the others on the 3-column grid
root = os.path.join(SCH, 'sam_cpu.kicad_sch')
s = open(root).read()
suid = uid('sheet', FN)
if suid not in s:
    head, blocks, foot = L.split(s)
    sheets = [b for b in blocks if L.kind(b) == 'sheet']
    tmpl = [b for b in sheets if '"audio.kicad_sch"' in b][0]
    ax, ay, _ = L.at(tmpl)
    nx, ny = 25.4 + (11 % 3) * 127.0, 63.5 + (11 // 3) * 45.72
    dx, dy = nx - ax, ny - ay
    import re
    def shift(m):
        return '(at %s %s' % (L.fmt(float(m.group(1)) + dx), L.fmt(float(m.group(2)) + dy))
    nb = re.sub(r'\(at ([-\d.]+) ([-\d.]+)', shift, tmpl)
    nb = nb.replace('"audio.kicad_sch"', '"%s"' % FN).replace('"Audio"', '"%s"' % NAME)
    nb = re.sub(r'\(page "11"\)', '(page "12")', nb)
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

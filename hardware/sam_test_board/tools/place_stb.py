"""Create sam_test_board.kicad_pcb from the KiCad netlist and place every part.

kpy place_stb.py <netlist> <out.kicad_pcb>
Board W x H, 2 layers, all parts on the top side (single-sided JLCPCB assembly).
Headers A and B on the top edge, C and D on the bottom edge (KK-396 ramps inward), one column of 7 parts per
channel facing its pin, the 74HC165 / 74HCT595 in a middle strip under the channels they serve, MCU, rails
connector J5 and the isolated USB corner on the right.
"""
import sys, os, re, math, collections
import pcbnew
FPDIR = os.environ.get('KICAD9_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
NET, OUT = sys.argv[1], sys.argv[2]
W, H = float(os.environ.get('STB_W', 165)), float(os.environ.get('STB_H', 133))
BAR_X, BAR_Y = W - 36.0, H - 22.0          # isolated USB corner: x > BAR_X, y > BAR_Y

# ---------------- netlist ----------------
s = open(NET).read()
comps = {m.group(1): dict(value=m.group(2), fp=m.group(3)) for m in
         re.finditer(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)', s)}
sheet_of = {m.group(1): m.group(2) for m in re.finditer(r'\(comp \(ref "([^"]+)"\)(?:(?!\(comp ).)*?\(sheetpath \(names "([^"]*)"\)', s, re.S)}
nets = {}
for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)(?=\n\s*\(net \(code|\Z)', s[s.index('(nets'):], re.S):
    nets[m.group(1)] = re.findall(r'\(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2))
pinnet = {}
for n, nodes in nets.items():
    for r, p in nodes: pinnet[(r, p)] = n
def short(n): return n.split('/')[-1]
bynet = collections.defaultdict(set)
for (r, p), n in pinnet.items(): bynet[short(n)].add(r)
def netsof(r): return {short(pinnet[k]) for k in pinnet if k[0] == r}
NETS_OF = collections.defaultdict(set)
for (r, p), n in pinnet.items(): NETS_OF[r].add(short(n))

board = pcbnew.BOARD()
board.SetCopperLayerCount(2)
mm = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I(mm(x), mm(y))
netinfo = {}
for n in nets:
    ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); netinfo[n] = ni
FP = {}
def load(ref):
    lib, name = comps[ref]['fp'].split(':')
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name)
    if fp is None: raise SystemExit(f'missing footprint {comps[ref]["fp"]}')
    fp.SetReference(ref); fp.SetValue(comps[ref]['value'])
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    board.Add(fp)
    for pad in fp.Pads():
        n = pinnet.get((ref, pad.GetNumber()))
        if n: pad.SetNet(netinfo[n])
    FP[ref] = fp
for ref in comps:
    if not ref.startswith('#'): load(ref)

placed = set()
OCC = []
def cbox(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    return (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
def put(ref, x, y, rot=0, gap=0.75):
    fp = FP[ref]; fp.SetOrientationDegrees(rot); fp.SetPosition(V(x, y))
    placed.add(ref)
    b = cbox(fp)
    OCC.append((b[0] - gap, b[1] - gap, b[2] + gap, b[3] + gap, ref))
    return fp
def collides(ref, x, y, rot, gap=0.75):
    fp = FP[ref]; fp.SetOrientationDegrees(rot); fp.SetPosition(V(x, y))
    b = cbox(fp)
    b = (b[0] - gap, b[1] - gap, b[2] + gap, b[3] + gap)
    if b[0] < 1.0 or b[1] < 1.0 or b[2] > W - 1.0 or b[3] > H - 1.0: return True
    for o in OCC:
        if b[0] < o[2] and b[2] > o[0] and b[1] < o[3] and b[3] > o[1]: return True
    return False
def near(ref, x, y, rot=0, step=0.5, rmax=60):
    for r in range(0, int(rmax / step)):
        cands = [(0, 0)] if r == 0 else [(dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if max(abs(dx), abs(dy)) == r]
        cands.sort(key=lambda d: d[0] ** 2 + d[1] ** 2)
        for dx, dy in cands:
            if not collides(ref, x + dx * step, y + dy * step, rot):
                return put(ref, x + dx * step, y + dy * step, rot)
    FAIL.append(ref); print(f"no room for {ref} near {x:.1f},{y:.1f}")
    return put(ref, x, y, rot)
FAIL = []
def pos(ref): return pcbnew.ToMM(FP[ref].GetPosition().x), pcbnew.ToMM(FP[ref].GetPosition().y)
def padpos(ref, num):
    p = FP[ref].FindPadByNumber(str(num)); return pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)

# ---------------- outline, holes ----------------
def edge(x0, y0, x1, y1):
    sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
    sh.SetStart(V(x0, y0)); sh.SetEnd(V(x1, y1)); sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(mm(0.1)); board.Add(sh)
for a, b in [((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))]:
    edge(*a, *b)
put('H1', 5, 5, gap=1.5); put('H2', W - 5, 5, gap=1.5); put('H3', W - 5, H - 5, gap=1.5); put('H4', 5, H - 5, gap=1.5)

# ---------------- connectors ----------------
# KK-396 A-41791: the friction ramp is on the footprint's local +y side; Vincent's convention: ramp faces inward.
ROT = {'top': 0, 'bottom': 180, 'left': 90, 'right': 270}
CGAP = 3.25
def put_conn(ref, side, along, across):
    fp = FP[ref]; rot = ROT[side]
    fp.SetOrientationDegrees(rot); fp.SetPosition(V(0, 0))
    b = cbox(fp)
    if side in ('top', 'bottom'): put(ref, along - b[0], across, rot, gap=CGAP)
    else: put(ref, across, along - b[1], rot, gap=CGAP)
    b = cbox(fp)
    return b[2] if side in ('top', 'bottom') else b[3]
HDR = {'A': 'J7', 'B': 'J8', 'C': 'J9', 'D': 'J10'}
SIDE = {'A': 'top', 'B': 'top', 'C': 'bottom', 'D': 'bottom'}
X0 = 10.5
e = put_conn('J7', 'top', X0, 7.5); put_conn('J8', 'top', e + 5.5, 7.5)
e = put_conn('J9', 'bottom', X0, H - 7.5); XR = put_conn('J10', 'bottom', e + 5.5, H - 7.5)
put_conn('J5', 'top', XR + 7.0, 7.5)          # rails + GND, top edge, right of header B

# ---------------- channel columns ----------------
SLOT, START = 5.0, 11.5
def chparts(n):
    la = f'LA_{n}'
    leds = sorted(r for r in bynet[la] if r.startswith('D'))
    red = [r for r in leds if comps[r]['value'] == 'red'][0]; green = [r for r in leds if comps[r]['value'] == 'green'][0]
    r33 = [r for r in bynet[la] if r.startswith('R')][0]
    rs1 = [r for r in bynet[f'S_{n}'] if r.startswith('R') and n in NETS_OF[r]][0]
    rs2 = [r for r in bynet[f'S_{n}'] if r.startswith('R') and 'GND' in NETS_OF[r]][0]
    q = [r for r in bynet[n] if r.startswith('Q')][0]
    rg = [r for r in bynet[f'G_{n}'] if r.startswith('R')][0]
    return red, green, r33, q, rg, rs1, rs2
COL = {}
for h in 'ABCD':
    J = HDR[h]; down = SIDE[h] == 'top'
    for p in range(1, 13):
        n = f'{h}{p}'
        x, y = padpos(J, p)
        red, green, r33, q, rg, rs1, rs2 = chparts(n)
        slots = [red, green, r33, q, None, rg, rs1, rs2] if p % 2 else [red, green, r33, None, q, rg, rs1, rs2]
        for i, r in enumerate(slots):
            if r is None: continue
            yy = y + (1 if down else -1) * (START + i * SLOT)
            rot = 0 if r.startswith('Q') else 90
            if r.startswith('Q') and not down: rot = 180
            if not collides(r, x, yy, rot): put(r, x, yy, rot)
            else: near(r, x, yy, rot, step=0.25, rmax=6)
        COL[n] = (x, y)
    # common solder jumper at the start of the header, outside the columns
JP_OF = {'A': 'JP1', 'B': 'JP2', 'C': 'JP3', 'D': 'JP4'}
for h in 'ABCD':
    x, y = padpos(HDR[h], 1)
    near(JP_OF[h], x - 6.0 if h in 'AC' else padpos(HDR[h], 12)[0] + 6.0, y + (16 if SIDE[h] == 'top' else -16), 0, rmax=20)

# ---------------- registers: middle strip ----------------
def centroid(refs):
    pts = [pos(r) for r in refs]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
YT = START + 7 * SLOT + 7.5 + 2.5 + 6.0       # centre of the strip row under the top bank
YB = H - YT                                   # row above the bottom bank
regs = sorted((r for r in comps if comps[r]['value'] in ('74HC165', '74HCT595')), key=lambda r: int(r[1:]))
for r in regs:
    chs = [short(pinnet[(r, p)]) for p in ['11', '12', '13', '14', '3', '4', '5', '6', '15', '1', '2', '7']
           if (r, p) in pinnet]
    chs = [c.split('_', 1)[1] for c in chs if c.startswith(('S_', 'G_'))]
    tops = [c for c in chs if c[0] in 'AB']
    use = tops if len(tops) * 2 >= len(chs) else [c for c in chs if c[0] in 'CD']
    x = sum(COL[c][0] for c in use) / len(use)
    if comps[r]['value'] == '74HCT595': x += 5.5
    else: x -= 5.5
    y = YT if use[0][0] in 'AB' else YB
    near(r, x, y, 90, step=0.5, rmax=30)
    cap = [c for c in comps if c.startswith('C') and sheet_of.get(c) == '/Registers/' and c not in placed
           and ('+3V3' if comps[r]['value'] == '74HC165' else '+5V') in NETS_OF[c]][0]
    px, py = padpos(r, 16)
    near(cap, px, py + (-4 if y == YT else 4), 0, step=0.25, rmax=30)

# ---------------- MCU (right region) ----------------
MX, MY = XR + 20.0 if XR + 20.0 < W - 22 else W - 22, (BAR_Y + 30) / 2 + 4
MX = W - 25.0
put('U5', MX, MY, 0, gap=1.0)
gnd = FP['U5'].FindPadByNumber('81').GetNet()
for i in (-1, 0, 1):
    for j in (-1, 0, 1):
        v = pcbnew.PCB_VIA(board); v.SetPosition(V(MX + i * 1.1, MY + j * 1.1)); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
        v.SetNet(gnd); board.Add(v)
def u5pins(names=None, nums=None):
    return [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in FP['U5'].Pads()
            if (names and short(p.GetNetname()) in names) or (nums and p.GetNumber() in nums)]
def near_u5(ref, pts, d):
    x = sum(p[0] for p in pts) / len(pts); y = sum(p[1] for p in pts) / len(pts)
    dx, dy = x - MX, y - MY
    if abs(dx) > abs(dy): tx, ty, rot = MX + math.copysign(5.0 + d, dx), y, 0
    else: tx, ty, rot = x, MY + math.copysign(5.0 + d, dy), 90
    if ref.startswith(('Y', 'L', 'SW', 'D')): rot = 0
    near(ref, tx, ty, rot, step=0.25, rmax=14)
mcu = lambda r: sheet_of.get(r) == '/MCU/'
L1 = [r for r in comps if r.startswith('L')][0]
near_u5(L1, u5pins({'VREG_LX'}), 2.5)
cav = [r for r in bynet['VREG_AVDD'] if r.startswith('C')][0]; rav = [r for r in bynet['VREG_AVDD'] if r.startswith('R')][0]
near_u5(cav, u5pins({'VREG_AVDD'}), 2.2); near_u5(rav, u5pins({'VREG_AVDD'}), 5.5)
c11 = sorted((r for r in bynet['+1V1'] if r.startswith('C')), key=lambda r: int(r[1:]))
for c, pin in zip(c11, ['65', '51', '32', '10']): near_u5(c, u5pins(nums={pin}), 2.2)
c33 = sorted((r for r in comps if mcu(r) and r.startswith('C') and r not in placed and '+3V3' in NETS_OF[r]
              and comps[r]['value'] == '100n'), key=lambda r: int(r[1:]))
for c, pins in zip(c33, [['5'], ['15'], ['24'], ['29'], ['41'], ['50'], ['59', '60'], ['64'], ['68', '69'], ['76']]):
    near_u5(c, u5pins(nums=set(pins)), 3.5)
near_u5('Y1', u5pins({'XIN', 'XOUT'}), 5.0)
for r in [x for x in comps if mcu(x) and NETS_OF[x] & {'XTAL_OUT', 'XIN'} and x not in ('Y1', 'U5')]: near_u5(r, u5pins({'XIN', 'XOUT'}), 8.5)
for n in ['RUN', 'BOOTSEL', 'LED_STATUS', 'SR_CLK_MCU', 'SYNC_IO']:
    for r in sorted(x for x in bynet[n] if x[0] == 'R' and x not in placed): near_u5(r, u5pins({n}), 2.5)
for n in ['USB_DP_MCU', 'USB_DM_MCU']:
    for r in sorted(x for x in bynet[n] if x[0] == 'R' and x not in placed): near_u5(r, u5pins({n}), 2.5)
for r in [x for x in comps if mcu(x) and x.startswith('C') and x not in placed]: near(r, MX + 9, MY - 9, 0)

# ---------------- isolated USB corner ----------------
put('J1', W - 16.0, H - 3.65, 0)
put('U3', BAR_X + 11.0, BAR_Y, 90)
put('PS1', BAR_X + 2.6, BAR_Y + 3.81, 180)
OCC.append((BAR_X - 0.25, BAR_Y - 0.25, W, BAR_Y + 0.25, 'barrier'))
OCC.append((BAR_X - 0.25, BAR_Y, BAR_X + 0.25, H, 'barrier'))
def parts_on(netnames, prefix='C'):
    return sorted({r for n in netnames for r in bynet[n] if r.startswith(prefix) and r not in placed})
def cluster(refs, x, y, rot=0, step=0.5, rmax=60):
    for r in refs:
        if r not in placed: near(r, x, y, rot, step=step, rmax=rmax)
fence = (0, 0, W, BAR_Y + 0.25, 'fence'); fence2 = (0, 0, BAR_X + 0.25, H, 'fence')
OCC += [fence, fence2]
cluster(['U2'], W - 7.0, H - 13.0, 0, rmax=10)
cluster(parts_on(['CC1', 'CC2'], 'R'), W - 4.0, H - 13.0, 90, rmax=30)
cluster(parts_on(['VBUS_USB', 'VDD1'], 'C'), BAR_X + 20.0, H - 13.0, 0, rmax=30)
cluster([r for r in comps if r.startswith('TP') and 'GND_USB' in NETS_OF[r]], BAR_X + 26.0, H - 8.0, 0, rmax=30)
OCC.remove(fence); OCC.remove(fence2)
cluster(parts_on(['VDD2'], 'C'), BAR_X + 11.0, BAR_Y - 10.0)
U4 = [r for r in comps if comps[r]['value'].startswith('NCP1117')][0]
near(U4, BAR_X - 4.0, BAR_Y - 12.0, 0)
cluster(parts_on(['+5V'], 'C'), BAR_X - 4.0, BAR_Y - 4.0)
cluster([r for r in comps if sheet_of.get(r) == '/Power and USB/' and r.startswith('C') and '+3V3' in NETS_OF[r]], BAR_X - 6.0, BAR_Y - 20.0)
cluster(parts_on(['+3V3', 'LED_PWR_A'], 'R') and [r for r in comps if sheet_of.get(r) == '/Power and USB/' and r.startswith('R') and r not in placed and NETS_OF[r] & {'+3V3', 'LED_PWR_A'}]
        + parts_on(['LED_PWR_A'], 'D'), BAR_X - 14.0, BAR_Y - 6.0)
# MCU extras
cluster(['SW1', 'SW2'], MX - 12, MY + 18)
cluster(['J2'], MX + 14, MY + 16, 90)
cluster(['J11'], MX + 16, MY - 16, 90)
cluster([r for r in comps if r.startswith('JP') and r not in placed], MX - 12, MY - 16)
cluster(parts_on(['LED_ST_A'], 'D'), MX + 8, MY + 16)
cluster(parts_on(['SR_OE_N', 'SR_CLR_N', 'SR_CLK'], 'R'), MX - 18, MY)
# rail monitors under J5
for h in 'ABCD':
    cluster(sorted(x for x in bynet[f'ADC_R{h}'] | bynet[f'RAIL{h}'] if x[0] in 'RCT' and x not in placed), padpos('J5', 'ABCD'.index(h) + 1)[0], 22)
rest = [r for r in comps if not r.startswith('#') and r not in placed]
for r in rest:
    pts = [pos(x) for n in NETS_OF[r] - {'GND', '+3V3', '+5V'} for x in bynet[n] if x != r and x in placed and not x.startswith('J')]
    c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else (MX - 15, MY)
    near(r, c[0], c[1], 0, rmax=120)

def keepout(pts):
    z = pcbnew.ZONE(board); z.SetIsRuleArea(True)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts: ol.Append(mm(x), mm(y))
    board.Add(z)
keepout([(W, BAR_Y - 0.25), (BAR_X - 0.25, BAR_Y - 0.25), (BAR_X - 0.25, H), (BAR_X + 0.25, H), (BAR_X + 0.25, BAR_Y + 0.25), (W, BAR_Y + 0.25)])
print('FAILED', FAIL)
print('board', W, 'x', H, 'placed', len(placed), 'of', len([r for r in comps if not r.startswith('#')]), 'XR', round(XR, 1), 'YT', YT)
pcbnew.SaveBoard(OUT, board)

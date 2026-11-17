"""Create driver_test_board.kicad_pcb from the KiCad netlist and place every part.

kpy place_pcb.py <netlist> <out.kicad_pcb>
Board 250 x 150 mm, 2 layers. Driver-side connectors on the bottom and right edges, CPU-side connectors on the
top and left edges, every channel (load resistor, LED, divider) in a column/row facing its connector pin.
"""
import sys, os, re, math, collections
import pcbnew
sys.path.insert(0, os.path.dirname(__file__))
FPDIR = os.environ.get('KICAD9_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
NET, OUT = sys.argv[1], sys.argv[2]

# ---------------- netlist ----------------
s = open(NET).read()
comps = {m.group(1): dict(value=m.group(2), fp=m.group(3)) for m in
         re.finditer(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)', s)}
nets = {}
for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)(?=\n\s*\(net \(code|\Z)', s[s.index('(nets'):], re.S):
    nets[m.group(1)] = re.findall(r'\(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2))
pinnet = {}
for n, nodes in nets.items():
    for r, p in nodes: pinnet[(r, p)] = n
def short(n): return n.split('/')[-1]
bynet = collections.defaultdict(set)
for (r, p), n in pinnet.items(): bynet[short(n)].add(r)

W, H = 250.0, 150.0
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
    return fp
for ref in comps:
    if not ref.startswith('#'): load(ref)

placed = set()
OCC = []   # placed courtyard boxes (x0, y0, x1, y1) incl. clearance
def cbox(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    return (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
def put(ref, x, y, rot=0, gap=0.75):
    """fix ref at (x, y); its courtyard plus `gap` becomes occupied"""
    fp = FP[ref]
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(V(x, y))
    placed.add(ref)
    b = cbox(fp)
    OCC.append((b[0] - gap, b[1] - gap, b[2] + gap, b[3] + gap, ref))
    return fp
def collides(ref, x, y, rot, gap=0.75):
    fp = FP[ref]; fp.SetOrientationDegrees(rot); fp.SetPosition(V(x, y))
    b = cbox(fp)
    b = (b[0] - gap, b[1] - gap, b[2] + gap, b[3] + gap)
    if b[0] < 1.5 or b[1] < 1.5 or b[2] > W - 1.5 or b[3] > H - 1.5: return True
    for o in OCC:
        if b[0] < o[2] and b[2] > o[0] and b[1] < o[3] and b[3] > o[1]: return True
    return False
def near(ref, x, y, rot=0, step=1.0, rmax=60):
    """place ref at the free spot closest to (x, y)"""
    for r in range(0, int(rmax / step)):
        cands = [(0, 0)] if r == 0 else [(dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if max(abs(dx), abs(dy)) == r]
        cands.sort(key=lambda d: d[0] ** 2 + d[1] ** 2)
        for dx, dy in cands:
            if not collides(ref, x + dx * step, y + dy * step, rot):
                return put(ref, x + dx * step, y + dy * step, rot)
    print("OCC", [o for o in OCC if o[0]<x+8 and o[2]>x-8 and o[1]<y+8 and o[3]>y-8]); raise SystemExit(f"no room for {ref} near {x},{y}")
def padpos(ref, num):
    for p in FP[ref].Pads():
        if p.GetNumber() == str(num): return pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)

# ---------------- outline, holes ----------------
def edge(x0, y0, x1, y1):
    sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
    sh.SetStart(V(x0, y0)); sh.SetEnd(V(x1, y1)); sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(mm(0.1)); board.Add(sh)
for a, b in [((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))]:
    edge(*a, *b)
put('H1', 5, 5); put('H2', W - 5, 5); put('H3', W - 5, H - 5); put('H4', 5, H - 5)

# ---------------- connectors ----------------
# KK-396 A-41791: the friction ramp is on the footprint's local +y side. Vincent's convention: ramp faces inward.
# local +y on screen: rot 0 -> down, 90 -> right, 180 -> up, 270 -> left.
ROT = {'top': 0, 'bottom': 180, 'left': 90, 'right': 270}
CGAP = 3.25            # connector courtyard clearance (+0.75 of the neighbour = 4 mm)
def put_conn(ref, side, along, across):
    """place ref with its courtyard starting at `along` on the edge axis and its pin row at `across`"""
    fp = FP[ref]; rot = ROT[side]
    fp.SetOrientationDegrees(rot); fp.SetPosition(V(0, 0))
    b = cbox(fp)
    if side in ('top', 'bottom'): put(ref, along - b[0], across, rot, gap=CGAP)
    else: put(ref, across, along - b[1], rot, gap=CGAP)
    b = cbox(fp)
    return b[2] if side in ('top', 'bottom') else b[3]
def conn_row(refs, side, start, gap=5.5, across=None):
    if across is None: across = {'top': 7.5, 'bottom': H - 7.5, 'left': 7.5, 'right': W - 7.5}[side]
    pos = start
    for ref in refs:
        pos = put_conn(ref, side, pos, across) + gap
    return pos
SIDE = {}
for refs, side, start in [(['J12', 'J13', 'J14', 'J15', 'J10'], 'top', 11.0),
                          (['J16', 'J17'], 'left', 30.0),
                          (['J8', 'J9'], 'right', 26.0),
                          (['J3', 'J4', 'J5', 'J6'], 'bottom', 36.0)]:
    conn_row(refs, side, start)
    for r in refs: SIDE[r] = side
# aux J3 (IO side, only pins 9-12 used) inside the board, under the lamp connectors' reach, ramp towards its parts
put_conn('J11', 'top', 148.0, 37.0); SIDE['J11'] = 'top'
# power input (IO J10: GND, +50 V) has no channel parts: inside the board, under J11
put_conn('J7', 'top', 148.0, 64.0)
# USB-C on the bottom edge, bottom-left corner, receptacle front flush with the edge (front at local y +3.65)
put('J1', 16.0, H - 3.65, 0)
# isolation barrier at y = BAR_Y for x < BAR_X: USB side (GND_USB) below, board side (GND) above.
# ADuM3160 side 1 (pins 1-8) faces down, side 2 up; B0505S input pins 1-2 below the barrier, outputs 3-4 above.
BAR_X, BAR_Y = 35.5, 128.0
put('U3', 25.0, BAR_Y, 90)
put('PS1', 33.0, BAR_Y + 3.81, 180)

# ---------------- channel columns ----------------
def channel(conn_ref, pin, net, side):
    """stack the parts of the channel whose connector pin is (conn_ref, pin) inward from the pin"""
    x, y = padpos(conn_ref, pin)
    seq = []
    frontier = [net]; seen = set()
    while frontier:
        n = frontier.pop(0)
        if n in seen or n in ('GND', '+3V3', '+5V') or (n.startswith('V') and n != net): continue
        seen.add(n)
        for r in sorted(bynet[n]):
            if r in placed or r in seq or r[0] not in 'RDQ': continue
            seq.append(r)
            for pad in FP[r].Pads():
                frontier.append(short(pad.GetNetname()))
    d = {'bottom': (0, -1), 'top': (0, 1), 'right': (-1, 0), 'left': (1, 0)}[side]
    vertical = side in ('bottom', 'top')
    start = 11.5
    for i, r in enumerate(seq):
        rot = 90 if vertical else 0
        if r.startswith('Q'): rot = 0 if vertical else 90
        dist = start + i * 5.0
        near(r, x + d[0] * dist, y + d[1] * dist, rot, step=0.5, rmax=12)
    return seq

for ref in ['J3', 'J4', 'J5', 'J6', 'J8', 'J9', 'J10', 'J11', 'J12', 'J13', 'J14', 'J15', 'J16', 'J17']:
    for pad in sorted(FP[ref].Pads(), key=lambda p: int(p.GetNumber())):
        n = short(pad.GetNetname())
        if not n or n == 'GND' or n.startswith('unconnected') or n.startswith('V') or n.startswith('J13P'): continue
        channel(ref, pad.GetNumber(), n, SIDE[ref])
# J13 pins 9/10 via the solder jumpers, then the LCOLX channel
x9, y9 = padpos('J9', 9)
near('JP1', x9 - 12, y9, 90, step=0.5)
near('JP2', x9 - 12, y9 + 4, 90, step=0.5)
channel('J9', 10, 'LCOLX', 'right')

# ---------------- clusters ----------------
def cluster(refs, x, y, rot=0, step=1.0, rmax=60):
    for r in refs:
        if r in placed: continue
        near(r, x, y, rot, step=step, rmax=rmax)
def parts_on(netnames, prefix='C'):
    return sorted({r for n in netnames for r in bynet[n] if r.startswith(prefix) and r not in placed})
def centroid(ref, skip=('GND', '+3V3', '+5V')):
    pts = []
    for pad in FP[ref].Pads():
        n = short(pad.GetNetname())
        if not n or n in skip: continue
        for r in bynet[n]:
            if r != ref and r in placed and not r.startswith('J'):
                pts.append((pcbnew.ToMM(FP[r].GetPosition().x), pcbnew.ToMM(FP[r].GetPosition().y)))
    if not pts: return None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

# MCU in the centre, its support parts around it
MX, MY = 112.0, 78.0
put('U5', MX, MY, 0)
cluster(['Y1'], MX - 10, MY + 10)
cluster(['L1'], MX + 9, MY + 10)
for c in parts_on(['+1V1', 'VREG_AVDD', 'XIN', 'XTAL_OUT', 'XOUT'], 'C') + parts_on(['VREG_AVDD', 'XOUT', 'RUN', 'BOOTSEL', 'BOOTSEL_BTN', 'LED_ST_A', 'LED_STATUS'], 'R'):
    near(c, MX, MY + 13, 0, step=0.5)
caps_3v3 = parts_on(['+3V3'], 'C')
for c in caps_3v3[:11]:
    near(c, MX, MY - 11, 0, step=0.5)
caps_3v3 = caps_3v3[11:]
cluster(['SW1', 'SW2'], MX - 22, MY + 20)
cluster(['J2'], MX + 24, MY + 20, 90)
cluster(parts_on(['LED_ST_A'], 'D'), MX + 14, MY + 18)

# shift registers: each one at the centroid of the channel parts it serves, pulled 6 mm towards the MCU
for r in sorted(r for r in comps if comps[r]['value'] in ('74HC165', '74HCT595')):
    c = centroid(r)
    if c is None: c = (MX, MY)
    x, y = c
    x, y = x + (MX - x) * 0.18, y + (MY - y) * 0.18
    near(r, x, y, 0, step=0.5, rmax=80)
    if caps_3v3 and comps[r]['value'] == '74HC165': near(caps_3v3.pop(0), x + 7, y, 90, step=0.5)
for r in sorted(r for r in comps if comps[r]['value'] == '74HCT595'):
    x, y = pcbnew.ToMM(FP[r].GetPosition().x), pcbnew.ToMM(FP[r].GetPosition().y)
    c5 = parts_on(['+5V'], 'C')
    if c5: near(c5[0], x + 7, y, 90, step=0.5)

# isolated USB and power: USB side parts below the barrier, regulator and decoupling above it
cluster(['U2'], 9.0, 134.0, 0, step=0.5, rmax=10)
cluster(parts_on(['CC1', 'CC2'], 'R'), 4.0, 134.0, 90, step=0.5, rmax=10)
cluster(parts_on(['VBUS_USB', 'VDD1'], 'C'), 20.0, 136.0, 0, step=0.5, rmax=12)
cluster(parts_on(['VDD2'], 'C'), 30.0, 120.0, 0, step=0.5)
cluster(parts_on(['DDP', 'DDM'], 'R'), 24.0, 118.0, 0, step=0.5)
near('U4', 52, 104, 0)
cluster(parts_on(['+5V'], 'C'), 52, 96)
cluster(caps_3v3, 62, 100)
cluster(parts_on(['+3V3', 'LED_PWR_A'], 'R') + parts_on(['LED_PWR_A'], 'D'), 62, 110)
cluster(parts_on(['SR_OE_N', 'SR_CLR_N', 'SR_CLK'], 'R'), MX, MY - 22)
# everything else (rail monitors, test points, ...) next to what it connects to
rest = [r for r in comps if not r.startswith('#') and r not in placed]
for r in rest:
    c = centroid(r, skip=('GND',)) or (MX + 30, MY)
    near(r, c[0], c[1], 0, step=0.5, rmax=120)

# isolation barrier: 0.5 mm strip with no track and no via on both layers, so nothing crosses between GND_USB and GND
def keepout(pts):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts: ol.Append(mm(x), mm(y))
    board.Add(z)
keepout([(0, BAR_Y - 0.25), (BAR_X + 0.25, BAR_Y - 0.25), (BAR_X + 0.25, H), (BAR_X - 0.25, H), (BAR_X - 0.25, BAR_Y + 0.25), (0, BAR_Y + 0.25)])
print('placed', len(placed), 'of', len([r for r in comps if not r.startswith('#')]))
pcbnew.SaveBoard(OUT, board)

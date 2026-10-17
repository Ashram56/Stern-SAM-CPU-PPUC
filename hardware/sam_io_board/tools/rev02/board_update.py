"""Rev 0.2 PCB update: board from rev 0.1, footprints from the rev 0.2 netlist, MCU area cleared and
re-placed, board grown to 100 x 100 mm, harness connectors and input stages added. KiCad 10 Python.
Usage: board_update.py <netlist.xml> <board.kicad_pcb>"""
import os, sys, math
import xml.etree.ElementTree as ET
import pcbnew
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
def _hook(kind, value, tb):
    while tb: print(f'  line {tb.tb_lineno}'); tb = tb.tb_next
    print(f'{kind.__name__}: {value}'); sys.stdout.flush(); os._exit(1)
sys.excepthook = _hook
MM = pcbnew.FromMM; TOMM = pcbnew.ToMM
FPDIR = os.environ['KICAD10_FOOTPRINT_DIR']
netfile, boardfile = sys.argv[1:3]
QFN = 'Package_DFN_QFN:QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm'

CX, CY = 114.5, 81.5
PLACE = {   # ref: (x, y, rot)
    'U3': (CX, CY, 0),
    'R10': (116.8, 71.0, 90), 'R11': (115.8, 71.0, 90), 'C40': (113.8, 73.6, 90), 'C19': (112.2, 73.6, 90),
    'C37': (110.6, 73.6, 90), 'C12': (108.2, 75.2, 0), 'C4': (113.4, 70.4, 0),
    'C35': (118.6, 72.4, 90), 'L1': (121.2, 72.6, 90), 'C36': (124.0, 72.6, 90), 'C16': (126.6, 74.4, 0),
    'C34': (122.0, 76.8, 0), 'R31': (124.6, 75.4, 90),
    'C17': (121.2, 78.6, 0), 'C20': (121.8, 80.2, 0), 'C41': (123.2, 81.9, 90), 'R15': (124.8, 82.4, 90),
    'C15': (121.4, 86.6, 0), 'C39': (121.4, 88.0, 0),
    'C9': (108.4, 88.0, 0), 'C13': (110.4, 89.4, 0), 'C38': (108.4, 89.6, 0), 'C14': (112.8, 88.6, 0),
    'C10': (116.6, 88.6, 90), 'Y1': (114.5, 91.4, 0), 'C6': (111.4, 91.4, 90), 'C7': (117.6, 91.4, 90),
    'R12': (119.4, 91.4, 90), 'J20': (136.0, 92.0, 0),
    'C21': (109.4, 71.4, 0),
}
# harness connectors and input stages
J3X, J13X, JY = 84.0, 125.0, 123.5
PLACE['J3'] = (J3X, JY, 0); PLACE['J13'] = (J13X, JY, 0); PLACE['J2'] = (168.0, 58.0, 270)
for i, p in enumerate((1, 2, 4, 5, 6, 7, 8, 9)):            # J3 -> stage 1..8
    x = J3X + 3.96 * (p - 1)
    PLACE['R%d' % (101 + i)] = (x, 115.2, 90); PLACE['R%d' % (121 + i)] = (x, 111.9, 90); PLACE['C%d' % (101 + i)] = (x, 108.6, 90)
for i, p in enumerate((1, 3, 4, 5, 6, 7, 8, 9)):            # J13 -> stage 10..17
    x = J13X + 3.96 * (p - 1)
    PLACE['R%d' % (110 + i)] = (x, 115.2, 90); PLACE['R%d' % (130 + i)] = (x, 111.9, 90); PLACE['C%d' % (110 + i)] = (x, 108.6, 90)
PLACE['C110'] = (126.8, 109.0, 90)
y10 = 58.0 + 3.96 * 9                                          # J2 pin 10 -> stage 9
PLACE['R109'] = (160.0, y10 - 3.0, 0); PLACE['R129'] = (160.0, y10, 0); PLACE['C109'] = (156.5, y10, 90)

t = ET.parse(netfile); comps = {}
for c in t.iter('comp'):
    sp = c.find('sheetpath'); props = {p.get('name'): p.get('value') for p in c.iter('property')}
    comps[c.get('ref')] = dict(value=c.findtext('value'), fp=c.findtext('footprint'), path=sp.get('tstamps') + c.findtext('tstamps'),
                               sheetname=props.get('Sheetname', ''), sheetfile=props.get('Sheetfile', ''))
comps['U3']['fp'] = QFN
padnet = {(n.get('ref'), n.get('pin')): net.get('name') for net in t.iter('net') for n in net.iter('node')}

b = pcbnew.LoadBoard(boardfile)
keep_alive = []
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name); b.Add(n); nets[name] = n
    return nets[name]

# 1. footprints: rename J3 -> J20, drop U2 and the RP2040
have = {}
for f in list(b.GetFootprints()):
    r = f.GetReference()
    if r == 'J3' and 'PinSocket' in str(f.GetFPID().GetLibItemName()): f.SetReference('J20'); r = 'J20'
    if r in ('U2', 'U3'):
        keep_alive.append(f); b.Remove(f); continue
    have[r] = f

# 2. clear tracks / vias in the MCU box, then dangling ends
BOX = (104.0, 66.8, 126.2, 94.8)
def inbox(p): return BOX[0] <= TOMM(p.x) <= BOX[2] and BOX[1] <= TOMM(p.y) <= BOX[3]
for tr in list(b.GetTracks()):
    pts = [tr.GetStart(), tr.GetEnd()] if tr.GetClass() != 'PCB_VIA' else [tr.GetPosition()]
    if any(inbox(p) for p in pts): keep_alive.append(tr); b.Remove(tr)

# 3. board outline 100 x 100, holes back to y = 134, GND zone over the board on both layers
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts and d.GetClass() == 'PCB_SHAPE':
        for get, set_ in ((d.GetStart, d.SetStart), (d.GetEnd, d.SetEnd)):
            p = get()
            if abs(TOMM(p.y) - 109.0) < 0.2: set_(pcbnew.VECTOR2I(p.x, MM(139.0)))
for f in b.GetFootprints():
    if 'MountingHole' in str(f.GetFPID().GetLibItemName()) and TOMM(f.GetPosition().y) > 100:
        f.SetPosition(pcbnew.VECTOR2I(f.GetPosition().x, MM(134.0)))
for z in b.Zones():
    if z.GetNetname() == 'GND':
        o = z.Outline()
        for i in range(o.TotalVertices()):
            v = o.CVertex(i)
            if abs(TOMM(v.y) - 109.0) < 0.2: o.SetVertex(i, pcbnew.VECTOR2I(v.x, MM(139.0)))
        ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls)

# 4. add missing footprints, place PLACE parts
io = pcbnew.PCB_IO_KICAD_SEXPR()
for ref, c in sorted(comps.items()):
    if ref in have: continue
    lib, name = c['fp'].split(':')
    f = io.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name)
    assert f, c['fp']
    f.SetReference(ref); f.SetValue(c['value']); f.SetFPID(pcbnew.LIB_ID(lib, name))
    f.SetPath(pcbnew.KIID_PATH(c['path'])); f.SetSheetname(c['sheetname']); f.SetSheetfile(c['sheetfile'])
    b.Add(f); have[ref] = f
    assert ref in PLACE, ref
for ref, (x, y, rot) in PLACE.items():
    f = have[ref]
    f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
# 4b. 2 x 2 GND vias in the exposed pad
gnd = net('GND')
for dx in (-0.85, 0.85):
    for dy in (-0.85, 0.85):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(CX + dx), MM(CY + dy)))
        v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(gnd); b.Add(v)
# 5. nets and paths for every footprint
for ref, f in have.items():
    if ref not in comps: continue
    f.SetPath(pcbnew.KIID_PATH(comps[ref]['path']))
    for pad in f.Pads():
        n = padnet.get((ref, pad.GetNumber()))
        if n: pad.SetNet(net(n))
        elif pad.GetNumber(): pad.SetNet(b.GetNetInfo().OrphanedItem())
extra = set(have) - set(comps) - {''}
print('board-only footprints:', sorted(r for r in extra))
missing = set(comps) - set(have); assert not missing, missing
b.Save(boardfile)
print('saved')
sys.stdout.flush(); os._exit(0)

"""c36 (board): footprints of the parts c35 removed from the schematic go, with every track and via on the nets they
leave behind; pad nets follow the new netlist (J21 pins 18 / 22 SWDIO / SWCLK, U15 pin 10 to GND, no-connects on
U4 pins 47 / 66 / 67 and U31 pin 1). The +3V3 / GND plane vias of the removed pads go too.
Usage: c36_board_trim_usb_gi_dip_swd.py in.kicad_pcb out.kicad_pcb"""
import sys
import pcbnew

REMOVED = ['C93', 'J18', 'J19', 'J20', 'R10', 'R11', 'R12', 'R13', 'R14', 'R183', 'R184', 'R185', 'SW3', 'U14'] + \
          ['R%d' % i for i in range(168, 176)]
PADS = {('J21', '18'): '/MCU and Pi/SWDIO', ('J21', '22'): '/MCU and Pi/SWCLK', ('U15', '10'): 'GND',
        ('U4', '47'): 'unconnected-(U4-GPIO38-Pad47)', ('U4', '66'): 'unconnected-(U4-USB_DM-Pad66)',
        ('U4', '67'): 'unconnected-(U4-USB_DP-Pad67)', ('U31', '1'): 'unconnected-(U31-QB-Pad1)'}

b = pcbnew.LoadBoard(sys.argv[1])
keep = []        # removed items stay referenced: freeing them from Python corrupts the board's objects
FP = {f.GetReference(): f for f in b.GetFootprints()}
nets = {str(k): v for k, v in b.GetNetInfo().NetsByName().items()}


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name); b.Add(n); nets[name] = n
    return nets[name]


# vias and tracks touching a removed pad: plane vias of GND / +3V3 pads, and the stubs to them
gone_pads = [p for r in REMOVED for p in FP[r].Pads()]
for r in REMOVED:
    keep.append(FP[r]); b.Remove(FP[r])
changed = set()
for (r, n), name in PADS.items():
    p = FP[r].FindPadByNumber(n)
    changed.add(p.GetNetname()); p.SetNet(net(name))

# nets with fewer than two pads left, plus the nets whose pads changed, lose all their copper
count = {}
for f in b.GetFootprints():
    for p in f.Pads():
        count[p.GetNetname()] = count.get(p.GetNetname(), 0) + 1
dead = {n for n in nets if count.get(n, 0) < 2} | changed
dead -= {'GND', '+3V3', '+5V'}
rm = 0
for t in list(b.Tracks()):
    if t.GetNetname() in dead:
        keep.append(t); b.Remove(t); rm += 1
# GND / +3V3 / +5V copper that sat on a removed pad (fan-out stubs and their vias)
for t in list(b.Tracks()):
    if t.GetNetname() in ('GND', '+3V3', '+5V') and any(p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()) for p in gone_pads
                                                       if p.GetNetname() == t.GetNetname()):
        keep.append(t); b.Remove(t); rm += 1
b.Save(sys.argv[2])
print('removed footprints', len(REMOVED), 'tracks/vias', rm)

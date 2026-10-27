"""c39 (board): J19 and R10-R14 come back for c38, placed only (no routing). J19, R13 and R14 go where they were at
e6c37a8 (J19 on the top edge above U4, R13 / R14 in line with U4 pins 66 / 67); R10-R12 (VBUS / CC pull-downs), whose
old spot D3 / SW2 now use, sit in a column left of J19 with 1 mm between courtyards. Pad nets follow the c38 netlist
(USB_D+ / USB_D- on the U4 side, USB_C_D+ / USB_C_D- on the connector side, a diff pair). Tracks and vias of other
nets that touch the new pads are removed, so the board has no shorts; the router re-does them.
Usage: kpython c39_board_restore_usb.py in.kicad_pcb old.kicad_pcb (sam_cpu.kicad_pcb at e6c37a8) out.kicad_pcb"""
import sys
import pcbnew

b = pcbnew.LoadBoard(sys.argv[1]); o = pcbnew.LoadBoard(sys.argv[2])
M = pcbnew.FromMM
keep = []        # removed items stay referenced (see c36)
NETS = {'Net-(J19-D+-PadA6)': '/MCU and Pi/USB_C_D+', 'Net-(J19-D--PadA7)': '/MCU and Pi/USB_C_D-',
        'Net-(U4-USB_DP)': '/MCU and Pi/USB_D+', 'Net-(U4-USB_DM)': '/MCU and Pi/USB_D-'}
PLACE = {'R10': (66.5, 32.6), 'R11': (66.5, 35.4), 'R12': (66.5, 38.2)}     # board file coordinates, 0 deg
nets = {str(k): v for k, v in b.GetNetInfo().NetsByName().items()}


def net(name):
    name = NETS.get(name, name)
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name); b.Add(n); nets[name] = n
    return nets[name]


new = []
for r in ['J19', 'R10', 'R11', 'R12', 'R13', 'R14']:
    f = o.FindFootprintByReference(r)
    names = [p.GetNetname() for p in f.Pads()]
    o.Remove(f); keep.append(f); b.Add(f)
    for p, n in zip(f.Pads(), names):
        p.SetNet(net(n) if n else b.GetNetInfo().GetNetItem(0))
    if r in PLACE:
        f.SetPosition(pcbnew.VECTOR2I(M(PLACE[r][0]), M(PLACE[r][1]))); f.SetOrientationDegrees(0)
    new.append(f)
u4 = b.FindFootprintByReference('U4')
for n, name in (('66', '/MCU and Pi/USB_D-'), ('67', '/MCU and Pi/USB_D+')):
    u4.FindPadByNumber(n).SetNet(net(name))

# copper of other nets on the new pads goes
rm = 0
pads = [p for f in new for p in f.Pads()]
for t in list(b.Tracks()):
    for p in pads:
        if p.GetNetname() != t.GetNetname() and p.GetEffectiveShape(t.GetLayer() if t.Type() != pcbnew.PCB_VIA_T else pcbnew.F_Cu).Collide(
                t.GetEffectiveShape(), M(0.1)):
            keep.append(t); b.Remove(t); rm += 1
            break

# 1 mm between courtyards
def cy(f):
    c = f.GetCourtyard(pcbnew.F_CrtYd)
    return c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
for f in new:
    bb = cy(f); bb.Inflate(M(0.99))
    near = [g.GetReference() for g in b.GetFootprints() if g.GetReference() != f.GetReference() and cy(g).Intersects(bb)]
    print(f.GetReference(), 'neighbours within 1 mm:', near)
b.Save(sys.argv[3])
print('placed', len(new), 'removed tracks/vias', rm)

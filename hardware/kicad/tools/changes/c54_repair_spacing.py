"""c54 (board, 2026-11-01): repairability spacing pass around U4 and BOOTSEL (Vincent's review request).
- BOOTSEL: R15 (1k, QSPI_SS to the button) goes next to U4 pin 75 so the long trace to the button sits behind
  1k instead of hanging on the flash chip select; SW2 moves to the free area above U4, near R15. The old copper of
  /MCU and Pi/BOOTSEL and Net-(R15-Pad1) is deleted: both are left for hand routing.
- Spacing: parts listed in MOVES move by (dx, dy) with their private GND / +3V3 via stubs; other attached tracks get
  an axis-aligned jog (c54_movelib), so no odd angle appears.
- R21 removed with its copper (c55 removes it from the schematic).
- Pins 68/69 (+3V3): pin 68 loses its own via and joins pin 69's track: vertical, then horizontal.
Usage: kpython c54_repair_spacing.py in.kicad_pcb out.kicad_pcb   (needs in.kicad_pro / .kicad_dru beside in)
Then c51_0603_to_0805.py apply out out sam_cpu_dir c54_0805_refs.txt for the 0603 -> 0805 swaps."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from c54_movelib import move, delete_net_copper, keep, P

# ref: absolute target (x, y[, rot]) for parts whose nets are rerouted by hand, else relative (dx, dy)
PLACE = {'R15': (68.97, 45.60, -90), 'SW2': (55.25, 41.00, 0)}
MOVES = {
    'C12': (0, -1.35),
    'C22': (65.49 - 68.05, 43.60 - 46.73),
    'C23': (62.03 - 65.85, 43.60 - 46.73),
    'C13': (64.60 - 66.08, 47.85 - 49.30),
    'C21': (0.80, 0),        # J11 pin 1 track at x 88.7 limits it
    'R8': (0.60, 0),
    'C11': (0.20, 0),
}
# second pass: small moves of tight passives elsewhere on the board, found by search and kept only when DRC adds no
# error (c54_moves.json, ref: [dx, dy])
_J = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c54_moves.json')
if os.environ.get('C54_MOVES'): _J = os.environ['C54_MOVES']
if os.path.exists(_J):
    import json
    MOVES.update({k: tuple(v) for k, v in json.load(open(_J)).items()})
DELETE_NETS = ['/MCU and Pi/BOOTSEL', 'Net-(R15-Pad1)', 'Net-(J21-GPIO27)']


def pins_68_69(b):
    mm = pcbnew.ToMM
    for t in list(b.GetTracks()):
        if t.GetNetname() != '+3V3': continue
        if t.GetClass() == 'PCB_VIA' and abs(mm(t.GetPosition().x) - 74.10) < .01 and abs(mm(t.GetPosition().y) - 50.13) < .01:
            keep.append(t); b.Remove(t)
        elif t.GetClass() != 'PCB_VIA':
            e = {(round(mm(t.GetStart().x), 2), round(mm(t.GetStart().y), 2)), (round(mm(t.GetEnd().x), 2), round(mm(t.GetEnd().y), 2))}
            if e == {(74.35, 51.05), (74.1, 50.13)}: keep.append(t); b.Remove(t)
    for a, c in (((74.35, 51.05), (74.35, 50.30)), ((74.35, 50.30), (73.95, 50.30))):
        n = pcbnew.PCB_TRACK(b); n.SetStart(P(*a)); n.SetEnd(P(*c)); n.SetWidth(pcbnew.FromMM(0.2)); n.SetLayer(pcbnew.F_Cu)
        n.SetNet(b.FindNet('+3V3')); n.SetLocked(True); b.Add(n); keep.append(n)


def track(b, pts, net, w=0.2):
    for a, c in zip(pts, pts[1:]):
        n = pcbnew.PCB_TRACK(b); n.SetStart(P(*a)); n.SetEnd(P(*c)); n.SetWidth(pcbnew.FromMM(w)); n.SetLayer(pcbnew.F_Cu)
        n.SetNet(b.FindNet(net)); b.Add(n); keep.append(n)


def main(inp, out):
    b = pcbnew.LoadBoard(inp)
    for n in DELETE_NETS: print('deleted', n, delete_net_copper(b, n))
    # c55: R21 (Pi GPIO27 to BOOTSEL) is gone; J21 pad 13 becomes a no-connect net like the other unused Pi pins
    r21 = b.FindFootprintByReference('R21'); keep.append(r21); b.Remove(r21)
    nc = pcbnew.NETINFO_ITEM(b, 'unconnected-(J21-GPIO27-Pad13)'); b.Add(nc); keep.append(nc)
    for p in b.FindFootprintByReference('J21').Pads():
        if p.GetNumber() == '13': p.SetNet(nc)
    for ref, (x, y, r) in PLACE.items():
        f = b.FindFootprintByReference(ref)
        f.SetOrientationDegrees(r)
        dx = x - pcbnew.ToMM(f.GetPosition().x); dy = y - pcbnew.ToMM(f.GetPosition().y)
        move(b, ref, dx, dy)
    for ref, (dx, dy) in MOVES.items(): move(b, ref, dx, dy)
    pins_68_69(b)
    # SW2 pin 1 pair, then SW2 to R15 pad 1 (90 degree path at y 41, below the CC2 track, above C22/C23)
    track(b, [(52.10, 39.10), (58.40, 39.10)], 'Net-(R15-Pad1)')
    track(b, [(58.40, 39.10), (58.40, 41.00), (68.97, 41.00), (68.97, 44.69)], 'Net-(R15-Pad1)')
    b.Save(out)


if __name__ == '__main__':
    main(*sys.argv[1:3])

"""c40 (board): free the escape of U4 pins 66 / 67 (USB_D- / USB_D+) for the router. The re-route after c36 ran an
unlocked +1V1 stub from pin 65 up to L1 pin 2 right beside pin 66 (0.25 mm track at x 75.37, about 0.02 mm from the
pin's straight exit), so DeepPCB found the pins blocked. Pin 65 also reaches +1V1 through the locked inner ring, so the
stub goes and nothing opens. Netclass USB clearance goes 0.2 -> 0.15 mm (in sam_cpu.kicad_pro): the QFN-80 pads are
0.2 mm apart edge to edge, so a 0.2 mm class clearance left no room to leave the pads.
Usage: kpython c40_board_usb_pin_escape.py in.kicad_pcb out.kicad_pcb"""
import sys
import pcbnew

b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM
keep = []
box = (74.9, 47.8, 76.8, 51.1)      # board file mm: column above pins 65-66 up to L1 pin 2
rm = 0
for t in list(b.Tracks()):
    if t.GetNetname() != '+1V1' or t.IsLocked() or t.Type() == pcbnew.PCB_VIA_T:
        continue
    if all(box[0] <= M(p.x) <= box[2] and box[1] <= M(p.y) <= box[3] for p in (t.GetStart(), t.GetEnd())):
        keep.append(t); b.Remove(t); rm += 1
b.Save(sys.argv[2]); print('removed +1V1 stub segments', rm)

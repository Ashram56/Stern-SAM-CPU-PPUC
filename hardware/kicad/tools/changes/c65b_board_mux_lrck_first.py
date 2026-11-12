# c65b: board side of c65 + audio re-placement for hand routing. Run with KiCad 10 python from hardware/kicad:
#   kpython tools/changes/c65b_board_mux_lrck_first.py sam_cpu <netlist from the c65 schematic>
# Sets every pad net from the netlist (U26 channels 1 / 2 swapped) and moves:
#   R192 / R191 / R193 (33 R) level with U26 pins 4 / 7 and under pin 8, turned so the mux side faces U26,
#   FB4 turned (+5V at the top), C146 turned (+3V3 next to U26 pin 16).
import pcbnew, os, sys, re
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
D = sys.argv[1]; NETF = sys.argv[2]; PCB = os.path.join(D, 'sam_cpu.kicad_pcb'); MM = 1e6
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c63_board_audio_tas5805m.py')).read()
exec(src[src.index('def parse_netlist'):src.index('COMPS, PADNET')])
COMPS, PADNET = parse_netlist(NETF)
PLACE = {'R192': (126.0, 109.365, 180), 'R191': (126.0, 113.175, 180), 'R193': (126.0, 116.9, 180),
         'FB4': (138.55, 106.3, 270), 'C146': (131.0, 103.3, 180)}
b = pcbnew.LoadBoard(PCB)
def netinfo(name):
    n = b.FindNet(name)
    if n is None: n = pcbnew.NETINFO_ITEM(b, name); b.Add(n)
    return n
for fp in b.GetFootprints():
    r = fp.GetReference()
    if r in PLACE:
        x, y, rot = PLACE[r]
        fp.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM))); fp.SetOrientationDegrees(rot)
n = 0
for fp in b.GetFootprints():
    for p in fp.Pads():
        net = PADNET.get((fp.GetReference(), p.GetNumber()))
        if net is not None and net != p.GetNetname(): p.SetNet(netinfo(net)); n += 1
pcbnew.SaveBoard(PCB, b); print('pads renetted', n)

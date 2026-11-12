# c64b: board side of c64. Run with KiCad 10 python from hardware/kicad:
#   kpython tools/changes/c64b_board_pdn_rc.py sam_cpu <netlist from the c64 schematic>
# Sets every pad net from the netlist (U4 pins 44 / 45 unconnected, R190 pad 1 +3V3 / pad 2 AMP_PDN) and adds C158
# (AMP_PDN 1 uF to GND) east of R190, on the pull-up row between the two amplifiers.
import pcbnew, os, sys, re
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
D = sys.argv[1]; NETF = sys.argv[2]; PCB = os.path.join(D, 'sam_cpu.kicad_pcb'); MM = 1e6
FPDIR = os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/k10dl/root/usr/share/kicad/footprints')
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c63_board_audio_tas5805m.py')).read()
exec(src[src.index('def parse_netlist'):src.index('COMPS, PADNET')])
COMPS, PADNET = parse_netlist(NETF)
PLACE = {'C158': (131.0, 82.9, 0)}
b = pcbnew.LoadBoard(PCB)
def netinfo(name):
    n = b.FindNet(name)
    if n is None: n = pcbnew.NETINFO_ITEM(b, name); b.Add(n)
    return n
have = {fp.GetReference(): fp for fp in b.GetFootprints()}
for ref, (x, y, r) in PLACE.items():
    if ref in have: continue
    c = COMPS[ref]; lib, name = c['footprint'].split(':', 1)
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name); fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref); fp.SetValue(c['value']); b.Add(fp)
    fp.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM))); fp.SetOrientationDegrees(r)
    fp.SetPath(pcbnew.KIID_PATH(c['sheet'] + c['uuid'])); fp.SetSheetname(c['sheetnames'].strip('/'))
    fp.SetSheetfile('audio.kicad_sch'); fp.SetField('Description', c['description'])
    have[ref] = fp
have['R190'].SetValue(COMPS['R190']['value']); have['R190'].SetField('Description', COMPS['R190']['description'])
n = 0
for fp in b.GetFootprints():
    for p in fp.Pads():
        net = PADNET.get((fp.GetReference(), p.GetNumber()))
        if net is not None and net != p.GetNetname(): p.SetNet(netinfo(net)); n += 1
pcbnew.SaveBoard(PCB, b); print('pads renetted', n)

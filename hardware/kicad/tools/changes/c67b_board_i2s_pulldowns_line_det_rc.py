# c67b: board side of c67. Run with KiCad 10 python from hardware/kicad:
#   kpython tools/changes/c67b_board_i2s_pulldowns_line_det_rc.py sam_cpu <netlist from the c67 schematic>
# Adds R199 / R200 / R201 (100k I2S pull-downs), R202 (10k) and C160 (100 nF) for LINE_DET -> MUX_SEL, and sets
# every pad net from the netlist (U26 pin 1 becomes MUX_SEL). Positions here are the first drop; the parts were
# then placed and routed by hand (see the README).
import pcbnew, os, sys, re
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
D = sys.argv[1]; NETF = sys.argv[2]; PCB = os.path.join(D, 'sam_cpu.kicad_pcb'); MM = 1e6
FPDIR = os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/k10/root/usr/share/kicad/footprints')
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c63_board_audio_tas5805m.py')).read()
exec(src[src.index('def parse_netlist'):src.index('COMPS, PADNET')])
COMPS, PADNET = parse_netlist(NETF)
PLACE = {'R199': (100.0, 20.0, 0), 'R200': (105.0, 20.0, 0), 'R201': (110.0, 20.0, 0), 'R202': (115.0, 20.0, 0),
         'C160': (120.0, 20.0, 0)}
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
n = 0
for fp in b.GetFootprints():
    for p in fp.Pads():
        net = PADNET.get((fp.GetReference(), p.GetNumber()))
        if net is not None and net != p.GetNetname(): p.SetNet(netinfo(net)); n += 1
pcbnew.SaveBoard(PCB, b); print('pads renetted', n)

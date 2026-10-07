"""Change 03 (2026-10-07): bring the IO_16_8_1 board up to date with the SAM_IO schematic.
Every part that stays keeps its position and its routing. Removes the IN16 / OUT8 footprints,
the tracks and zones of nets that no longer exist and the dangling track ends they leave,
the terminal-number silkscreen of J6-J11, and the GNDPWR zone; extends the GND zone over the
freed area; adds the SAM bus parts with a first rough placement on the left edge (not routed).
Run with KiCad 10's Python, one process per phase:
  c03_board_update.py <netlist.xml> <board.kicad_pcb> remove|add
(c04_board_clean.py runs between the two)"""
import json, os, sys
import xml.etree.ElementTree as ET
import pcbnew
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__   # SWIG iterators under Python 3.14


def _hook(kind, value, tb):         # importing traceback crashes next to pcbnew here
    while tb:
        print(f'  line {tb.tb_lineno}'); tb = tb.tb_next
    print(f'{kind.__name__}: {value}')
    sys.stdout.flush(); os._exit(1)
sys.excepthook = _hook

MM = pcbnew.FromMM
FPDIR = os.environ['KICAD10_FOOTPRINT_DIR']

# rough placement of the new parts: ref -> (x, y, rotation, side). J9 on the left edge where the
# J6-J8 terminals were, with its key facing the board edge; buffers between J9 and the RP2040.
PLACE = {
    'J9': (80.5, 62.0, 0, 'F'),
    'RN1': (90.5, 64.5, 90, 'F'), 'RN2': (90.5, 70.0, 90, 'F'),
    'U7': (97.5, 67.5, 0, 'F'),
    'R27': (97.5, 59.5, 0, 'F'), 'R28': (97.5, 76.5, 0, 'F'),
    'C30': (104.0, 61.0, 90, 'F'), 'C31': (104.0, 65.0, 90, 'F'),
    'RN3': (90.5, 84.5, 90, 'F'), 'R29': (90.5, 89.0, 0, 'F'),
    'U8': (97.5, 86.5, 0, 'F'),
    'C32': (104.0, 82.0, 90, 'F'), 'C33': (104.0, 92.5, 90, 'F'),
    'Q1': (92.5, 96.5, 0, 'F'), 'R30': (97.5, 96.5, 0, 'F'),
    'TP3': (84.0, 101.0, 0, 'F'), 'TP4': (87.5, 101.0, 0, 'F'),
    'TP5': (91.0, 101.0, 0, 'F'), 'TP6': (94.5, 101.0, 0, 'F'),
}
BOARD = (75.0, 39.0, 175.0, 139.0)


def load_netlist(path):
    t = ET.parse(path)
    comps = {}
    for c in t.iter('comp'):
        sp = c.find('sheetpath')
        props = {p.get('name'): p.get('value') for p in c.iter('property')}
        comps[c.get('ref')] = dict(value=c.findtext('value'), fp=c.findtext('footprint'),
                                   path=sp.get('tstamps') + c.findtext('tstamps'),
                                   sheetname=props.get('Sheetname', ''), sheetfile=props.get('Sheetfile', ''))
    pads = {(n.get('ref'), n.get('pin')): net.get('name') for net in t.iter('net') for n in net.iter('node')}
    return comps, pads


def main(netfile, boardfile, phase):
    """phase 'clean': footprints, nets, tracks, zones, silkscreen. phase 'add': the new parts.
    Two processes, because the SWIG proxies of a board stop working once footprints were removed."""
    comps, padnet = load_netlist(netfile)
    netnames = set(padnet.values())
    io = pcbnew.PCB_IO_KICAD_SEXPR()
    lib_fps = {}
    if phase == 'add':
        for ref in PLACE:
            lib, name = comps[ref]['fp'].split(':')
            lib_fps[ref] = io.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name)
    board = pcbnew.LoadBoard(boardfile)
    info = board.GetNetInfo()
    nets = {n.GetNetname(): n for n in info.NetsByName().values()}

    def net(name):
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); nets[name] = n
        return nets[name]

    if phase == 'add':
        have = {f.GetReference() for f in board.GetFootprints()}
        for ref in sorted(PLACE):
            if ref in have:
                continue
            c = comps[ref]; f = lib_fps[ref]
            lib, name = c['fp'].split(':')
            f.SetReference(ref); f.SetValue(c['value'])
            f.SetFPID(pcbnew.LIB_ID(lib, name))
            f.SetPath(pcbnew.KIID_PATH(c['path']))
            f.SetSheetname(c['sheetname']); f.SetSheetfile(c['sheetfile'])
            board.Add(f)
            x, y, rot, side = PLACE[ref]
            f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            f.SetOrientationDegrees(rot)
            for pad in f.Pads():
                n = padnet.get((ref, pad.GetNumber()))
                if n:
                    pad.SetNet(net(n))
        missing = set(comps) - {f.GetReference() for f in board.GetFootprints()}
        assert not missing, missing
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        board.Save(boardfile)
        print('added footprints:', sorted(set(PLACE) - have))
        return

    bypath = {c['path']: r for r, c in comps.items()}
    # 1. footprints: drop the ones whose symbol is gone, renumber pads of the ones that stay
    removed, dead_pads, kept_pads = [], [], []
    for f in list(board.GetFootprints()):
        p = f.GetPath().AsString()
        if not p:                       # mounting holes and logo: board-only
            continue
        ref = bypath.get(p)
        if ref is None:
            for pad in f.Pads():
                bb = pad.GetBoundingBox()
                dead_pads.append((pad.GetNetname(), bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
            removed.append(f.GetReference()); board.Remove(f); continue
        assert ref == f.GetReference(), (ref, f.GetReference())
        for pad in f.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n and n != pad.GetNetname():
                pad.SetNet(net(n))
            elif not n and pad.GetNumber() and pad.GetNetname():
                pad.SetNet(info.OrphanedItem())
            bb = pad.GetBoundingBox()
            kept_pads.append((n or '', [l for l in ('F.Cu', 'B.Cu') if pad.IsOnLayer(board.GetLayerID(l))],
                              bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
    board.Save(boardfile)
    json.dump({'removed': dead_pads, 'kept': kept_pads}, open(boardfile + '.pads.json', 'w'))
    print('removed footprints:', len(removed), sorted(removed))


if __name__ == '__main__':
    netfile, boardfile = sys.argv[1:3]
    phase = sys.argv[3]
    main(netfile, boardfile, phase)
    sys.stdout.flush(); os._exit(0)     # pcbnew can crash while Python tears down

"""Change 04 (2026-10-06): bring the board up to date with the schematic after changes 01-03, without moving any
existing part. Updates pad nets, adds the new footprints, and widens the board below the Pi for the two HUB75
headers. Run with KiCad 10's Python: c04_board_update.py <netlist> <board>"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pcbnew
import place_pcb as P

W, H = P.W, P.H
W2, YX = 142.0, 154.0          # extension: right edge at x 142 from y 154 down (clear of the Pi above)
EXT = (120.9, YX + 31.5, W2 - 0.4, H - 0.4)       # below the two headers
NEW_REGIONS = {
    'buffers': [EXT, (100, 208, 120.4, H - 0.4)],
    'U31': [(84, 168, 108.5, 196), EXT, (100, 208, 120.4, H - 0.4)],
    'U30': [(17, 128, 55, 168), (120.9, H - 9.5, W2 - 0.4, H - 0.4), EXT],
}
# both HUB75 headers side by side at the top of the extension, cables leave to the right
FIXED = {'J25': (W2 - 17.4, YX + 6.0, 0), 'J26': (W2 - 6.6, YX + 6.0, 0)}


def inside(b):
    x0, y0, x1, y1 = b
    if x0 < 0.3 or y0 < 0.3 or y1 > H - 0.3:
        return False
    if x1 <= W - 0.3:
        return True
    return y0 >= YX + 0.3 and x1 <= W2 - 0.3


class Occ(P.Occupancy):
    def free(self, b, reserved=False):
        if not inside(b):
            return False
        if any(P.overlaps(b, o) for o in self.boxes):
            return False
        return not (reserved and any(P.overlaps(b, o) for o in self.rings))


def main(netfile, boardfile):
    comps, nets = P.load_netlist(netfile)
    board = pcbnew.LoadBoard(boardfile)
    netinfo = {n.GetNetname(): n for n in board.GetNetInfo().NetsByName().values()}

    def net(name):
        if name not in netinfo:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            netinfo[name] = n
        return netinfo[name]
    padnet = {(r, p): name for name, nodes in nets for r, p in nodes}
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    changed = 0
    for ref, f in fps.items():
        if ref not in comps:
            continue
        for pad in f.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            old = pad.GetNetname()
            if n and n != old:
                pad.SetNet(net(n)); changed += 1
            elif not n and old:
                pad.SetNet(netinfo.get('', board.GetNetInfo().OrphanedItem())); changed += 1
    gone = [r for r in fps if r not in comps and not r.startswith('MH')]
    assert not gone, gone
    added = []
    for ref, c in sorted(comps.items()):
        if ref in fps:
            continue
        f = P.load_fp(c['fp'])
        f.SetReference(ref); f.SetValue(c['value'])
        f.SetFPID(pcbnew.LIB_ID(*c['fp'].split(':')))
        f.SetPath(pcbnew.KIID_PATH(c['path']))
        f.SetSheetname(c['sheetname'] or ''); f.SetSheetfile(c['sheet'] or '')
        board.Add(f)
        for pad in f.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(net(n))
        fps[ref] = f
        added.append(ref)
    print('pad nets changed:', changed, ' new footprints:', ' '.join(added))

    # outline: replace the rectangle with the widened polygon
    dr = board.Drawings()
    for d in [dr[i] for i in range(len(dr))]:
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(d)
    poly = [(0, 0), (W, 0), (W, YX), (W2, YX), (W2, H), (0, H)]
    for a, b in zip(poly, poly[1:] + poly[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P.pt(*a)); s.SetEnd(P.pt(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(P.mm(0.1))
        board.Add(s)

    occ = Occ()
    for ref, f in fps.items():
        if ref not in added:
            occ.add(f)
    for ref, (x, y, rot) in FIXED.items():
        f = fps[ref]
        f.SetOrientationDegrees(rot)
        p1 = [p for p in f.Pads() if p.GetNumber() == '1'][0]
        f.SetPosition(P.pt(x, y) - (p1.GetPosition() - f.GetPosition()))
        assert occ.free(P.box(f)), ref
        occ.add(f); f.SetLocked(True)
    caps = {'C122': 'U27', 'C123': 'U28', 'C124': 'U29', 'C125': 'U31', 'C126': 'U30'}
    groups = {'buffers': [r for r in added if r in ('U27', 'U28', 'U29', 'TP23', 'TP24') or r.startswith('RN')],
              'U31': ['U31'], 'U30': ['U30']}
    fps['U30'].SetOrientationDegrees(90)     # lies along the bottom edge of the extension
    for g, refs in groups.items():
        left = P.pack([fps[r] for r in refs], NEW_REGIONS[g], occ, {r: 1.6 for r in refs if r.startswith('U') and r != 'U30'})
        if left:
            print('did not fit', g, left)
    for c, u in caps.items():
        vcc = [p for p in fps[u].Pads() if p.GetNetname() in ('+5V', '+3V3')][0]
        toward = '1' if padnet[(c, '1')] == vcc.GetNetname() else '2'
        if not P.place_satellite(fps[c], fps[u], vcc, occ, toward):
            print('no room for', c)
    board.Save(boardfile)
    for r in added:
        print(r, [round(v, 1) for v in P.box(fps[r])])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

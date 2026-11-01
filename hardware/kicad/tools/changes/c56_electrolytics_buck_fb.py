"""c56 (board, 2026-11-01): electrolytics C4 / C108 / C118 spread in their row, and the buck feedback divider.
- The row is boxed in: R3-R7 / C9 / D2 above, the U23 / U24 heatsink keep-out (y 70.9-84.1, "NO PARTS") below.
  Vincent chose the simple spread (no rotation, Q4 stays): C4 3.9 mm left, C108 2.45 mm left, C118 0.65 mm left;
  gaps C4-C108 1.55 mm, C108-C118 1.85 mm, C118-Q4 0.85 mm (C4 cannot go further left: the J11 pin 1 and EXT_5V
  power tracks run there).
  Their attached tracks and the foreign copper under their new pads are ripped: Vincent reroutes them by hand
  (+5V / +12V / GND stubs, VMON_5V, RP_UART_TX).
- R216 (FB to GND, 13k) moves 1 mm up and 0.5 mm left, away from U35 and R215; its GND via goes to the left of the
  pad (STB_DATA runs on B.Cu at y 126.49 just above). The buck input loop (C133, C134, C137) is not touched.
Usage: kpython c56_electrolytics_buck_fb.py in.kicad_pcb out.kicad_pcb   (needs in.kicad_pro / .kicad_dru beside)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from c54_movelib import move, keep, P
MM = pcbnew.FromMM; mm = pcbnew.ToMM

ENDS = []
PLACE = {'C4': (95.0, 64.6, 0), 'C108': (106.6, 66.05, 0), 'C118': (119.05, 66.05, 0)}


def place_and_rip(b, ref, x, y, rot, log):
    f = b.FindFootprintByReference(ref)
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_VIA': continue
        if any(p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(t.GetLayer()) and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()))
               for p in f.Pads()):
            ENDS.extend([t.GetStart(), t.GetEnd()]); keep.append(t); b.Remove(t); log.append((ref, t.GetNetname()))
    f.SetOrientationDegrees(rot); f.SetPosition(P(x, y))


def rip_foreign(b, ref, log):
    for p in b.FindFootprintByReference(ref).Pads():
        bb = p.GetBoundingBox(); bb.Inflate(MM(0.3))
        for t in list(b.GetTracks()):
            if t.GetNetCode() == p.GetNetCode(): continue
            if t.GetClass() == 'PCB_VIA':
                hit = bb.Intersects(t.GetBoundingBox())
            else:
                hit = t.GetLayer() in list(p.GetLayerSet().Seq()) and bb.Intersects(t.GetBoundingBox()) and t.HitTest(bb, False)
            if hit: keep.append(t); b.Remove(t); log.append((ref, 'under pad: ' + t.GetNetname()))


def drop_floating_vias(b, log):
    for t in list(b.GetTracks()):
        if t.GetClass() != 'PCB_VIA': continue
        if t.GetNetname() in ('GND', '+3V3') and not any(t.GetPosition() == e for e in ENDS): continue
        con = [s for s in b.GetTracks() if s.GetClass() != 'PCB_VIA' and s.GetNetCode() == t.GetNetCode()
               and (s.GetStart() == t.GetPosition() or s.GetEnd() == t.GetPosition())]
        pads = [p for g in b.GetFootprints() for p in g.Pads() if p.GetNetCode() == t.GetNetCode() and p.HitTest(t.GetPosition())]
        if not con and not pads: keep.append(t); b.Remove(t); log.append(('', 'floating via ' + t.GetNetname()))


def r216(b):
    move(b, 'R216', 0, -1.0); move(b, 'R216', -0.5, 0)
    f = b.FindFootprintByReference('R216'); g = [p for p in f.Pads() if p.GetNetname() == 'GND'][0]
    gx, gy = mm(g.GetPosition().x), mm(g.GetPosition().y)
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND' and abs(mm(t.GetPosition().x) - gx) < .05 and abs(mm(t.GetPosition().y) - (gy - 1.075)) < .05:
            via = t
    for t in b.GetTracks():
        if t.GetClass() != 'PCB_VIA' and t.GetNetname() == 'GND' and (t.GetStart() == via.GetPosition() or t.GetEnd() == via.GetPosition()):
            stub = t
    nv = P(gx - 1.0, gy); via.SetPosition(nv); stub.SetStart(g.GetPosition()); stub.SetEnd(nv)


def main(inp, out):
    b = pcbnew.LoadBoard(inp); log = []
    for ref, (x, y, r) in PLACE.items(): place_and_rip(b, ref, x, y, r, log)
    for ref in PLACE: rip_foreign(b, ref, log)
    drop_floating_vias(b, log)
    r216(b)
    from collections import Counter
    for k, v in sorted(Counter(log).items()): print(k, v)
    b.Save(out)


if __name__ == '__main__':
    main(*sys.argv[1:3])

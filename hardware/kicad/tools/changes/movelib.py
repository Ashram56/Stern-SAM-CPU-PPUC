"""Move named footprints on an existing board (never a full re-placement). The locked GND / +3V3 plane fan-out of a
moved part (stub on its pad and the via at the stub end) is deleted; run route/fanout_missing.py for GND and +3V3
afterwards to give the pads new vias. Coordinates are board mm from the top-left corner (KiCad + 30 mm)."""
import pcbnew

OX, OY = 30.0, 30.0
MM = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(MM(x + OX), MM(y + OY))


class Board:
    def __init__(self, path):
        self.b = pcbnew.LoadBoard(path)
        self.keep = []      # removed items stay referenced: freeing them from Python corrupts the board's objects
        self.fp = {f.GetReference(): f for f in self.b.GetFootprints()}
        self.moved = []

    def strip_fanout(self, f):
        b = self.b
        tracks = list(b.Tracks())
        pads = [p for p in f.Pads()]
        ends = []
        for t in tracks:
            if t.Type() != pcbnew.PCB_TRACE_T or t.GetNetname() not in ('GND', '+3V3'):
                continue
            for p in pads:
                if p.GetNetname() != t.GetNetname():
                    continue
                if p.HitTest(t.GetStart()):
                    ends.append((t.GetNetname(), t.GetEnd())); self.keep.append(t); b.Remove(t); break
                if p.HitTest(t.GetEnd()):
                    ends.append((t.GetNetname(), t.GetStart())); self.keep.append(t); b.Remove(t); break
        for t in tracks:
            if t.Type() == pcbnew.PCB_VIA_T and any(n == t.GetNetname() and (t.GetPosition() - e).EuclideanNorm() < MM(0.05)
                                                    for n, e in ends):
                self.keep.append(t); b.Remove(t)
        # vias sitting inside a pad (exposed pads)
        for t in list(b.Tracks()):
            if t.Type() == pcbnew.PCB_VIA_T and any(p.GetNetname() == t.GetNetname() and p.HitTest(t.GetPosition()) for p in pads):
                self.keep.append(t); b.Remove(t)

    def move(self, ref, x, y, rot=None, side=None):
        f = self.fp[ref]
        self.strip_fanout(f)
        if side is not None and (side == 'B') != f.IsFlipped():
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetPosition(V(x, y))
        if rot is not None:
            f.SetOrientationDegrees(rot)
        self.moved.append(ref)

    def save(self, path):
        self.b.Save(path)
        print('moved', len(self.moved), ' '.join(self.moved))

"""c58 (board, 2026-11-01): board widened to the right, x 150.65 -> 172, from the top edge down to y 126.5.
- Vincent chose to widen the board for routing room. The band x 150.65-172, y 126.5-184 stays open: the face-down
  Pi 4's USB / Ethernet jacks hang there off the board (User.Drawings "PI USB / ETHERNET (OFF BOARD)", y 126-182).
- Edge.Cuts: (30,30)-(172,30)-(172,126.5)-(150.65,126.5)-(150.65,184)-(172,184)-(172,266.76)-(30,266.76).
- GND F/B, GND In1 and +3V3 In2 zones follow the new outline.
- J17, J23, J22, J24 move +21.35 mm in x with axis-aligned jogs (c54_movelib); J30 moves +21.35 mm with its copper
  ripped; the 12 V OR stage (U33 U34 Q19 Q20 R213 R214 C5 Q4 TP19 TP20 C102) moves +10 mm as a rigid block with
  its internal copper; C108 +6 mm, C118 +9 mm. Ripped nets go to <out>.ripped.json and are rerouted by c58_krt/.
Usage: kpython c58_widen_right.py in.kicad_pcb out.kicad_pcb   (needs in.kicad_pro / .kicad_dru beside)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from c54_movelib import move, keep, P
MM = pcbnew.FromMM; mm = pcbnew.ToMM
DX = 172 - 150.65
OUT = [(30, 30), (172, 30), (172, 126.5), (150.65, 126.5), (150.65, 184), (172, 184), (172, 266.76), (30, 266.76)]

b = pcbnew.LoadBoard(sys.argv[1])
for d in list(b.GetDrawings()):
    if d.GetLayer() == pcbnew.Edge_Cuts: keep.append(d); b.Remove(d)
for i in range(len(OUT)):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
    s.SetStart(P(*OUT[i])); s.SetEnd(P(*OUT[(i + 1) % len(OUT)])); b.Add(s); keep.append(s)
for z in b.Zones():
    if z.GetZoneName() not in ('GND_TOP', 'GND_BOT', 'GND_PLANE', '3V3_PLANE'): continue
    o = z.Outline(); pts = [(round(mm(o.CVertex(i).x), 2), round(mm(o.CVertex(i).y), 2)) for i in range(o.TotalVertices())]
    k = pts.index((150.65, 30.0))
    pts[k:k + 1] = [(172, 30), (172, 126.5), (150.65, 126.5)]
    o.RemoveAllContours(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    print(z.GetZoneName(), pts)
RIPPED = {}


def rip_chains(b, ref):
    """Remove the copper from each pad of ref up to the first junction (pad, via or branch); private GND / +3V3
    via stubs are kept and travel with the part."""
    f = b.FindFootprintByReference(ref); mine = {U(p) for p in f.Pads()}; stubs = []
    for p in f.Pads():
        for t in list(b.GetTracks()):
            if t.GetClass() == 'PCB_VIA' or t.GetNetCode() != p.GetNetCode() or not p.IsOnLayer(t.GetLayer()): continue
            if not (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())): continue
            far = t.GetEnd() if p.HitTest(t.GetStart()) else t.GetStart()
            vias = [v for v in b.GetTracks() if v.GetClass() == 'PCB_VIA' and v.GetNetCode() == t.GetNetCode() and v.GetPosition() == far]
            if t.GetNetname() in ('GND', '+3V3') and vias and len([s for s in b.GetTracks() if s.GetClass() != 'PCB_VIA'
                    and s.GetNetCode() == t.GetNetCode() and far in (s.GetStart(), s.GetEnd())]) == 1:
                stubs += [t, vias[0]]; continue
            cur = t
            while True:
                RIPPED[cur.GetNetname()] = max(RIPPED.get(cur.GetNetname(), 0), mm(cur.GetWidth()))
                keep.append(cur); b.Remove(cur)
                if any(q.GetNetCode() == cur.GetNetCode() and q.HitTest(far) for g in b.GetFootprints() for q in g.Pads()): break
                if any(v.GetClass() == 'PCB_VIA' and v.GetNetCode() == cur.GetNetCode() and v.GetPosition() == far for v in b.GetTracks()): break
                nx = [s for s in b.GetTracks() if s.GetClass() != 'PCB_VIA' and s.GetNetCode() == cur.GetNetCode() and far in (s.GetStart(), s.GetEnd())]
                if len(nx) != 1: break
                cur = nx[0]; far = cur.GetEnd() if cur.GetStart() == far else cur.GetStart()
    return stubs


def U(i): return i.m_Uuid.AsString()


JOGS = ['J17', 'J23', 'J22', 'J24']
MOVES = {'J30': (DX, 0),
         # the electrolytic row opens up
         'C118': (9, 0), 'C108': (6, 0)}
# 12 V / 5 V OR stage and its neighbours move 10 mm right as a rigid block, with the copper between their own pads
BLOCK = ['U33', 'U34', 'Q19', 'Q20', 'R213', 'R214', 'C5', 'Q4', 'TP19', 'TP20', 'C102']
BDX = 10


def move_block(b):
    fps = [b.FindFootprintByReference(r) for r in BLOCK]
    bb = fps[0].GetBoundingBox(False, False)
    for f in fps[1:]: bb.Merge(f.GetBoundingBox(False, False))
    bb.Inflate(MM(0.5))
    nets = {p.GetNetCode() for f in fps for p in f.Pads()}
    inside = lambda pt: bb.Contains(pt)
    moved = 0
    for t in list(b.GetTracks()):
        if t.GetNetCode() not in nets: continue
        if t.GetClass() == 'PCB_VIA': ok = inside(t.GetPosition())
        else: ok = inside(t.GetStart()) and inside(t.GetEnd())
        if ok: t.Move(P(BDX, 0)); moved += 1
    for f in fps: f.Move(P(BDX, 0))
    # block copper that now reaches out of the block: cut at the block border (rerouted later)
    nb = pcbnew.BOX2I(bb.GetOrigin() + P(BDX, 0), bb.GetSize())
    cut = 0
    for t in list(b.GetTracks()):
        if t.GetNetCode() not in nets or t.GetClass() == 'PCB_VIA': continue
        a_, c_ = nb.Contains(t.GetStart()), nb.Contains(t.GetEnd())
        o_ = bb.Contains(t.GetStart()) or bb.Contains(t.GetEnd())
        if (a_ != c_) or (o_ and not (a_ and c_)):
            RIPPED[t.GetNetname()] = max(RIPPED.get(t.GetNetname(), 0), mm(t.GetWidth())); keep.append(t); b.Remove(t); cut += 1
    print('block: moved', moved, 'cut', cut)


for r in JOGS: move(b, r, DX, 0)
move_block(b)
for r, (dx, dy) in MOVES.items():
    stubs = rip_chains(b, r)
    for s in stubs: s.Move(P(dx, dy))
    b.FindFootprintByReference(r).Move(P(dx, dy))
from c56_electrolytics_buck_fb import rip_foreign, drop_floating_vias
log = []
for r in list(MOVES) + BLOCK: rip_foreign(b, r, log)
for _, n in log: RIPPED.setdefault(n.replace('under pad: ', ''), 0.2)
drop_floating_vias(b, log)


def strip_dangling(b, nets):
    """Iteratively remove the tails the rip left: tracks with a free end and vias with at most one track."""
    pads = {}
    for g in b.GetFootprints():
        for q in g.Pads(): pads.setdefault(q.GetNetCode(), []).append(q)
    n = 0
    while True:
        tr = [t for t in b.GetTracks() if t.GetNetname() in nets]
        segs = [t for t in tr if t.GetClass() != 'PCB_VIA']; vias = [t for t in tr if t.GetClass() == 'PCB_VIA']
        def on_pad(t, pt, layer=None):
            return any(q.HitTest(pt) and (layer is None or q.IsOnLayer(layer)) for q in pads.get(t.GetNetCode(), []))
        dead = []
        for t in segs:
            for pt in (t.GetStart(), t.GetEnd()):
                if on_pad(t, pt, t.GetLayer()): continue
                if any(v.GetNetCode() == t.GetNetCode() and v.GetPosition() == pt for v in vias): continue
                if any(U(o) != U(t) and o.GetNetCode() == t.GetNetCode() and o.GetLayer() == t.GetLayer() and (pt in (o.GetStart(), o.GetEnd()) or o.HitTest(pt, 0)) for o in segs): continue
                dead.append(t); break
        for v in vias:
            if on_pad(v, v.GetPosition()): continue
            if len([t for t in segs if t.GetNetCode() == v.GetNetCode() and v.GetPosition() in (t.GetStart(), t.GetEnd())]) <= 1: dead.append(v)
        if not dead: return n
        for t in dead: keep.append(t); b.Remove(t); n += 1


print('stripped', strip_dangling(b, set(RIPPED) - {'GND', '+3V3'}))
import json
json.dump(RIPPED, open(sys.argv[2] + '.ripped.json', 'w'), indent=1)
print(RIPPED)
b.Save(sys.argv[2])

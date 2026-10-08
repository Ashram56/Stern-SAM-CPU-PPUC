"""keep_escape.py <orig.kicad_pcb> <out.kicad_pcb> <half_box_mm> [whole_net_regex]
Keep only the original copper that is part of U3's hand-routed escape: tracks and vias reached from a U3 pad
through connected copper whose every point stays inside a square of +-half_box mm around U3. Everything else
(tracks, vias, zone fills) is deleted. Kept copper is left unlocked."""
import sys, pcbnew
import re
src, dst, H = sys.argv[1], sys.argv[2], float(sys.argv[3])
WHOLE = re.compile(sys.argv[4]) if len(sys.argv) > 4 else None  # nets whose copper is kept whole
b = pcbnew.LoadBoard(src)
u3 = b.FindFootprintByReference('U3'); c = u3.GetPosition()
mm = pcbnew.FromMM; tol = mm(0.01)
def inside(p): return abs(p.x - c.x) <= mm(H) and abs(p.y - c.y) <= mm(H)
tracks = list(b.GetTracks())
# copper items inside the box, grouped by net
cand = []
for t in tracks:
    if t.GetClass() == 'PCB_VIA':
        if inside(t.GetPosition()): cand.append(t)
    elif inside(t.GetStart()) and inside(t.GetEnd()): cand.append(t)
def pts(t):
    return [t.GetPosition()] if t.GetClass() == 'PCB_VIA' else [t.GetStart(), t.GetEnd()]
def layers(t):
    return {pcbnew.F_Cu, pcbnew.B_Cu} if t.GetClass() == 'PCB_VIA' else {t.GetLayer()}
def near(a, b2): return abs(a.x - b2.x) <= tol and abs(a.y - b2.y) <= tol
# seeds: anything touching a U3 pad
keep = set(); frontier = []
for t in cand:
    for p in u3.Pads():
        if p.GetNetCode() != t.GetNetCode() or p.GetNetCode() <= 0: continue
        if not (layers(t) & {pcbnew.F_Cu} if True else False): continue
        if any(p.HitTest(q) for q in pts(t)):
            keep.add(id(t)); frontier.append(t); break
byid = {id(t): t for t in cand}
while frontier:
    t = frontier.pop()
    for o in cand:
        if id(o) in keep or o.GetNetCode() != t.GetNetCode(): continue
        if not (layers(o) & layers(t)): continue
        if any(near(a, q) for a in pts(t) for q in pts(o)) or \
           (o.GetClass() != 'PCB_VIA' and t.GetClass() == 'PCB_VIA' and False):
            keep.add(id(o)); frontier.append(o)
        elif o.GetClass() == 'PCB_VIA' and t.GetClass() != 'PCB_VIA' and \
                t.HitTest(o.GetPosition()):
            keep.add(id(o)); frontier.append(o)
        elif t.GetClass() == 'PCB_VIA' and o.GetClass() != 'PCB_VIA' and \
                o.HitTest(t.GetPosition()):
            keep.add(id(o)); frontier.append(o)
n_k = {}
if WHOLE:
    for t in tracks:
        if WHOLE.fullmatch(t.GetNetname()): keep.add(id(t))
for t in tracks:
    if id(t) not in keep: b.Remove(t)
    else:
        k = b.GetNetInfo().GetNetItem(t.GetNetCode()).GetNetname() if False else t.GetNetname()
        n_k[k] = n_k.get(k, 0) + 1
for z in b.Zones(): z.UnFill()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(dst)
print(f"kept {len(keep)} items on {len(n_k)} nets inside +-{H} mm of U3 at {pcbnew.ToMM(c.x):.3f},{pcbnew.ToMM(c.y):.3f}, rot {u3.GetOrientationDegrees()}")
print(sorted(n_k.items()))

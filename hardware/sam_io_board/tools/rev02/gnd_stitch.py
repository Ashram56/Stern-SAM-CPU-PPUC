"""GND vias: one next to each listed GND pad (with a short track), and a stitching grid.
Usage: gnd_stitch.py <board> <drc.json> [grid_mm]"""
import os, sys, json, math, pcbnew
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
MM = pcbnew.FromMM
b = pcbnew.LoadBoard(sys.argv[1]); d = json.load(open(sys.argv[2])); grid = float(sys.argv[3]) if len(sys.argv) > 3 else 0
gnd = b.FindNet('GND'); CL = MM(float(os.environ.get("CL","0.2"))); VD = MM(float(os.environ.get("VD","0.6"))); VH = MM(float(os.environ.get("VH","0.3")))
edge = b.GetBoardEdgesBoundingBox()
items = []
for t in b.GetTracks(): items.append(t)
for f in b.GetFootprints():
    for p in f.Pads(): items.append(p)
def free(x, y, layers=(pcbnew.F_Cu, pcbnew.B_Cu), ignore=None, gnd_ok=False):
    if not (edge.GetLeft() + MM(0.8) < x < edge.GetRight() - MM(0.8) and edge.GetTop() + MM(0.8) < y < edge.GetBottom() - MM(0.8)): return False
    c = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(x), int(y)), VD // 2)
    for it in items:
        if it is ignore: continue
        if gnd_ok and it.GetNetCode() == gnd.GetNetCode() and it.GetClass() != 'PAD': continue
        bb = it.GetBoundingBox()
        if bb.GetLeft() - VD > x or bb.GetRight() + VD < x or bb.GetTop() - VD > y or bb.GetBottom() + VD < y: continue
        for l in layers:
            if it.IsOnLayer(l):
                cl = CL if it.GetNetCode() != gnd.GetNetCode() else MM(0.1)
                if it.GetClass() == 'PAD' and it.GetNetCode() == gnd.GetNetCode() and it is ignore: continue
                if it.GetEffectiveShape(l).Collide(c, cl): return False
        if it.GetClass() == 'PAD' and it.HasHole():
            if math.hypot(it.GetPosition().x - x, it.GetPosition().y - y) < VD + it.GetDrillSize().x / 2 + MM(0.3): return False
    for f in b.GetFootprints():   # keep out of mounting holes
        if 'MountingHole' in str(f.GetFPID().GetLibItemName()) and math.hypot(f.GetPosition().x - x, f.GetPosition().y - y) < MM(5.2): return False
    return True
def via(x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(int(x), int(y))); v.SetWidth(VD); v.SetDrill(VH); v.SetNet(gnd); b.Add(v); items.append(v); return v
# pads named in the DRC report (unconnected or starved)
want = set()
for v in d.get('unconnected_items', []) + [v for v in d['violations'] if v['type'] == 'starved_thermal']:
    for i in v['items']:
        if '[GND]' in i['description'] and i['description'].startswith('Pad'):
            want.add((round(i['pos']['x'], 3), round(i['pos']['y'], 3)))
n_pad = 0
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetCode() != gnd.GetNetCode() or p.HasHole(): continue
        pos = p.GetPosition()
        if (round(pcbnew.ToMM(pos.x), 3), round(pcbnew.ToMM(pos.y), 3)) not in want: continue
        done = False
        for r in (0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2, 2.6, 3.0):
            for k in range(32):
                a = k * math.pi / 16
                x = pos.x + MM(r) * math.cos(a) + (p.GetSize().x // 2) * math.cos(a)
                y = pos.y + MM(r) * math.sin(a) + (p.GetSize().y // 2) * math.sin(a)
                if not free(x, y, ignore=p): continue
                tr = pcbnew.PCB_TRACK(b); tr.SetStart(pos); tr.SetEnd(pcbnew.VECTOR2I(int(x), int(y))); tr.SetWidth(MM(0.25))
                tr.SetLayer(pcbnew.F_Cu); tr.SetNet(gnd)
                # the track itself must clear other nets
                ok = True
                for it in items:
                    if it.GetNetCode() == gnd.GetNetCode() or not it.IsOnLayer(pcbnew.F_Cu): continue
                    if it.GetEffectiveShape(pcbnew.F_Cu).Collide(tr.GetEffectiveShape(pcbnew.F_Cu), CL): ok = False; break
                if not ok: continue
                b.Add(tr); items.append(tr); via(x, y); done = True; n_pad += 1; break
            if done: break
        if not done: print('no via for', f.GetReference(), p.GetNumber())
n_grid = 0
if grid:
    x0, y0 = edge.GetLeft(), edge.GetTop()
    g = MM(grid)
    yy = y0 + g // 2
    while yy < edge.GetBottom():
        xx = x0 + g // 2
        while xx < edge.GetRight():
            if free(xx, yy): via(xx, yy); n_grid += 1
            xx += g
        yy += g
print('pad vias', n_pad, 'grid vias', n_grid)
b.Save(sys.argv[1]); sys.stdout.flush(); os._exit(0)

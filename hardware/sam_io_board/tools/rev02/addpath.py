"""Add the polylines/vias of a pathchk spec to the board. Usage: addpath.py <board> <spec.json>"""
import pcbnew, os, sys, json
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM
def P(q): return pcbnew.VECTOR2I(MM(q[0]), MM(q[1]))
for s in json.load(open(sys.argv[2])):
    n = b.FindNet(s['net'])
    if 'via' in s:
        v = pcbnew.PCB_VIA(b); v.SetPosition(P(s['via'])); v.SetWidth(MM(0.5)); v.SetDrill(MM(0.3)); v.SetNet(n); b.Add(v); continue
    for a, c in zip(s['pts'], s['pts'][1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(P(a)); t.SetEnd(P(c)); t.SetWidth(MM(0.2)); t.SetLayer(b.GetLayerID(s['layer'])); t.SetNet(n); b.Add(t)
b.Save(sys.argv[1]); os._exit(0)

"""c60 (board, 2026-11-11): bottom edge back to the original 231.76 mm.
Draft 0.7 made the board 5 mm taller (236.76) only to fit the lowered MH3; c59 put MH3 back at the Stern position,
so Vincent chose the original height. Nothing (pads, courtyards, tracks, vias) sits in the removed band.
Edge.Cuts and the GND / +3V3 zone outlines move from y 236.76 to y 231.76 (board frame, origin at the aux origin).
Usage: kpython c60_height_original.py in.kicad_pcb out.kicad_pcb   (needs in.kicad_pro / .kicad_dru beside)"""
import sys, pcbnew
MM = pcbnew.FromMM; mm = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1]); o = b.GetDesignSettings().GetAuxOrigin()
OLD, NEW = o.y + MM(236.76), o.y + MM(231.76)
n = 0
for d in b.GetDrawings():
    if d.GetLayer() != pcbnew.Edge_Cuts: continue
    s, e = d.GetStart(), d.GetEnd()
    if s.y == OLD: d.SetStart(pcbnew.VECTOR2I(s.x, NEW)); n += 1
    if e.y == OLD: d.SetEnd(pcbnew.VECTOR2I(e.x, NEW)); n += 1
for z in b.Zones():
    ol = z.Outline()
    for i in range(ol.TotalVertices()):
        v = ol.CVertex(i)
        if v.y == OLD: ol.SetVertex(i, pcbnew.VECTOR2I(v.x, NEW)); n += 1
print('moved points', n)
b.Save(sys.argv[2])

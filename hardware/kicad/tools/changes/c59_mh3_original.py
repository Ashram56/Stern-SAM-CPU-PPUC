"""c59 (board, 2026-11-11): MH3 back to the Stern 520-5246-00 position.
Vincent's Stern-compatible mounting plate (scanned 2026-11-11) has its bottom keyholes exactly where the original
drawing puts them: screw at the slot top, y 215.17, clearance circle y 222.59. Draft 0.7 had moved MH3 7.42 mm down
(screw 222.59), which would put the backbox screw on solid board. Vincent chose the original position.
Usage: kpython c59_mh3_original.py in.kicad_pcb out.kicad_pcb   (needs in.kicad_pro / .kicad_dru beside)"""
import sys, pcbnew
MM = pcbnew.FromMM; mm = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1])
f = [g for g in b.GetFootprints() if g.GetReference() == 'MH3'][0]
o = b.GetDesignSettings().GetAuxOrigin()
f.SetPosition(pcbnew.VECTOR2I(o.x + MM(8.24), o.y + MM(215.17)))
f.Reference().SetPosition(pcbnew.VECTOR2I(o.x + MM(8.24), o.y + MM(229.6)))  # below the circle, clear of R138
p = f.GetPosition(); print('MH3', round(mm(p.x - o.x), 2), round(mm(p.y - o.y), 2))
b.Save(sys.argv[2])

# move footprints: python3 move.py in.kicad_pcb out.kicad_pcb REF=dx,dy ...  (mm, KiCad coordinates)
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
for a in sys.argv[3:]:
    ref, d = a.split('='); dx, dy = map(float, d.split(','))
    fp = b.FindFootprintByReference(ref)
    p = fp.GetPosition(); fp.SetPosition(pcbnew.VECTOR2I(p.x + pcbnew.FromMM(dx), p.y + pcbnew.FromMM(dy)))
pcbnew.SaveBoard(sys.argv[2], b)

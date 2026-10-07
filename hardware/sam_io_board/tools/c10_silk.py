"""Change 10 (2026-10-07): silkscreen.
- Moves the reference designators that ended up over a pad or another part's outline after the SAM
  bus placement.
- c06 had been run twice on the outline, which moved the board name and one piece of the PPUC logo a
  second time, off the board: puts them back where c06 meant them (logo piece with the rest of the
  logo, name below it at y 104).
KiCad 10 Python: c10_silk.py <board.kicad_pcb>"""
import os, sys
import pcbnew

MM = pcbnew.FromMM
REF_AT = {'R29': (88.5, 91.9), 'C32': (88.8, 98.4), 'R30': (104.3, 104.8), 'RN2': (88.5, 77.7)}
b = pcbnew.LoadBoard(sys.argv[1])
for f in b.GetFootprints():
    if f.GetReference() in REF_AT:
        x, y = REF_AT[f.GetReference()]
        f.Reference().SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
D = b.Drawings()
for i in range(len(D)):
    d = D[i].Cast()
    if d.GetLayerName() == 'F.Silkscreen' and d.GetBoundingBox().GetLeft() > MM(175):
        if d.GetClass() == 'PCB_TEXT':
            d.SetPosition(pcbnew.VECTOR2I(MM(144.774), MM(104)))
        else:
            d.Move(pcbnew.VECTOR2I(MM(-48), MM(8)))
b.Save(sys.argv[1])
print('done'); sys.stdout.flush(); os._exit(0)

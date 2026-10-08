# Candidate placement: move the RP2040 block rigidly into the empty right half (all relative spacing
# kept, so decaps and the crystal stay where they were relative to U3), and the reset / boot buttons
# and LED block further right to make room. usage: shift.py in out DXA DXB
import pcbnew, sys
A = 'U3 U2 C13 C5 C6 C12 Y1 C10 C19 C4 C7 R12 R10 C14 R11 C9 C16 C21 C20 C17 R15 C15'.split()
B = 'R6 R21 R7 TP1 D3 SW1 R1 SW2'.split()
dxa, dxb = float(sys.argv[3]), float(sys.argv[4])
b = pcbnew.LoadBoard(sys.argv[1])
for fp in b.GetFootprints():
    r = fp.GetReference(); dx = dxa if r in A else dxb if r in B else None
    if dx is not None: fp.Move(pcbnew.VECTOR2I(int(dx * 1e6), 0))
pcbnew.SaveBoard(sys.argv[2], b); print('moved', len(A) + len(B))

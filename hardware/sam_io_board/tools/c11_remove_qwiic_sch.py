"""Change 11 (2026-10-08): Remove the QWIIC option from sam_io.kicad_sch: J2, its pull-ups R96/R97, its decoupling C8 and their wires,
labels, junctions and power symbols; replace the 0 ohm R9 with a wire; drop the 'remove when using QWIIC' note."""
import re, sys, uuid
src = open(sys.argv[1]).read()
X0, X1, Y0, Y1 = 110.0, 152.0, 15.0, 48.0          # the QWIIC block
def block_end(s, i):
    d = 0; q = False
    while True:
        c = s[i]
        if q:
            if c == '\\': i += 1
            elif c == '"': q = False
        elif c == '"': q = True
        elif c == '(': d += 1
        elif c == ')':
            d -= 1
            if d == 0: return i + 1
        i += 1
def inbox(x, y): return X0 <= x <= X1 and Y0 <= y <= Y1
out = []; i = 0; removed = []
while True:
    j = src.find('\n\t(', i)
    if j < 0: out.append(src[i:]); break
    out.append(src[i:j]); k = j + 2; e = block_end(src, k); blk = src[k:e]
    head = blk[1:].split(None, 1)[0].strip('()\n')
    drop = False
    if head in ('wire', 'junction', 'label', 'no_connect', 'symbol', 'text'):
        if head == 'wire':
            pts = [tuple(map(float, p)) for p in re.findall(r'\(xy ([\d.\-]+) ([\d.\-]+)\)', blk)]
            drop = all(inbox(*p) for p in pts)
        else:
            m = re.search(r'\(at ([\d.\-]+) ([\d.\-]+)', blk)
            drop = bool(m) and inbox(float(m.group(1)), float(m.group(2)))
        if head == 'symbol':
            ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
            ref = ref.group(1) if ref else '?'
            if ref == 'R9': drop = True
            if drop: removed.append(ref)
        if head == 'text' and 'using QWIIC' in blk: drop = True
        if drop and head != 'symbol': removed.append(head)
    if not drop: out.append('\n\t' + blk)
    else: pass
    i = e
s = ''.join(out)
wire = ('\n\t(wire\n\t\t(pts\n\t\t\t(xy 105.41 55.88) (xy 113.03 55.88)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n'
        '\t\t)\n\t\t(uuid "%s")\n\t)' % uuid.uuid4())
p = s.find('\n\t(wire'); assert p > 0; s = s[:p] + wire + s[p:]
open(sys.argv[2], 'w').write(s)
from collections import Counter; print(Counter(removed))

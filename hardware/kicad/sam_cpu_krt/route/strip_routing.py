"""Strip all tracks, vias, arcs and zone fills from a .kicad_pcb, keeping everything else."""
import sys

def block_end(s, i):
    depth = 0; q = False
    while True:
        c = s[i]
        if q:
            if c == '\\': i += 1
            elif c == '"': q = False
        elif c == '"': q = True
        elif c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0: return i + 1
        i += 1

src = open(sys.argv[1]).read()
out = []; i = 0; counts = {}
drop_top = ('(segment', '(via', '(arc')
while i < len(src):
    # line-start tokens at depth 1 are indented with exactly one tab
    j = src.find('\n\t(', i)
    if j < 0: out.append(src[i:]); break
    out.append(src[i:j + 1]); k = j + 2
    end = block_end(src, k)
    blk = src[k:end]
    head = blk.split(None, 1)[0].rstrip(')')
    if head in drop_top:
        counts[head] = counts.get(head, 0) + 1
        i = end
        if src.startswith('\n', i): pass
        out[-1] = out[-1][:-1]  # drop the newline before the block
        continue
    if head == '(zone':
        while True:
            p = blk.find('(filled_polygon')
            if p < 0: break
            ls = blk.rfind('\n', 0, p)
            blk = blk[:ls] + blk[block_end(blk, p):]
            counts['fill'] = counts.get('fill', 0) + 1
    out.append('\t' + blk); i = end
open(sys.argv[2], 'w').write(''.join(out))
print(counts)

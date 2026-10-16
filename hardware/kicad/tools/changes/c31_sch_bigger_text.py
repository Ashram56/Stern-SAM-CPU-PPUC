"""c31: bigger schematic text (Vincent: "barely visible"). On every sheet the 1.27 mm text becomes 1.6 mm for
references, values, labels and notes, and 1.5 mm for pin names / numbers inside the embedded symbols (lib_symbols),
which keeps them inside a 2.54 mm pin pitch. Larger existing sizes (titles, notes) are left alone. Global-label
intersheet references move out by the same ratio so they clear the longer label.
Usage: c31_sch_bigger_text.py sam_cpu_dir"""
import glob, os, re, sys
K = 1.6 / 1.27
def refs(m):
    """move a global label's intersheet reference out with the longer label text"""
    g = m.group(0)
    a = re.search(r'^\t\(global_label "[^"]*"\n\t\t\(shape \w+\)\n\t\t\(at ([-\d.]+) ([-\d.]+)', g)
    r = re.search(r'(\(property "Intersheetrefs" "[^"]*"\n\t\t\t\(at )([-\d.]+) ([-\d.]+)', g)
    if not a or not r: return g
    lx, ly, rx, ry = (float(v) for v in (a.group(1), a.group(2), r.group(2), r.group(3)))
    nx, ny = lx + (rx - lx) * K, ly + (ry - ly) * K
    return g[:r.start(2)] + '%g %g' % (round(nx, 2), round(ny, 2)) + g[r.end(3):]
for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.kicad_sch'))):
    s = open(p).read()
    i = s.find('\n\t(lib_symbols')
    if i >= 0:
        e = s.index('\n\t)', i)
        s = s[:i] + s[i:e].replace('(size 1.27 1.27)', '(size 1.5 1.5)') + s[e:].replace('(size 1.27 1.27)', '(size 1.6 1.6)')
        s = s[:i].replace('(size 1.27 1.27)', '(size 1.6 1.6)') + s[i:]
    else:
        s = s.replace('(size 1.27 1.27)', '(size 1.6 1.6)')
    s = re.sub(r'\t\(global_label .*?\n\t\)', refs, s, flags=re.S)
    open(p, 'w').write(s)
    print(os.path.basename(p))

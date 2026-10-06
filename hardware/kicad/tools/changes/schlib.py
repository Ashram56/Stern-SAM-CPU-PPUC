"""Small helpers to edit existing .kicad_sch files in place (top-level items as text blocks).
Used by the change scripts in this folder; nothing here regenerates a sheet."""
import re
import uuid as _uuid

STUB = 5.08


def split(text):
    """-> header, [blocks], footer; a block is one top-level '\t(...' item with its lines."""
    lines = text.split('\n')
    head, blocks, cur, i = [], [], None, 0
    # header ends at the first top-level item after lib_symbols
    out_blocks, footer = [], []
    depth_items = []
    k = 0
    while k < len(lines):
        ln = lines[k]
        if ln.startswith('\t(') and not ln.startswith('\t\t'):
            j = k
            # find the matching '\t)' (or a one-line item)
            if ln.rstrip().endswith(')') and ln.count('(') == ln.count(')'):
                depth_items.append('\n'.join(lines[k:k + 1])); k += 1; continue
            while not lines[j] == '\t)':
                j += 1
            depth_items.append('\n'.join(lines[k:j + 1]))
            k = j + 1
        else:
            if depth_items:
                footer.append(ln)
            else:
                head.append(ln)
            k += 1
    return head, depth_items, footer


def join(head, blocks, footer):
    return '\n'.join(head + blocks + footer)


def kind(b):
    return b.split('\n', 1)[0].strip()[1:].split(' ')[0]


def at(b):
    m = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3) or 0)) if m else None


def wire_pts(b):
    m = re.search(r'\(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)', b)
    return (float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4)))


def label_text(b):
    m = re.match(r'\s*\((?:global_label|label|hierarchical_label) "([^"]*)"', b)
    return m.group(1) if m else None


def same(a, b):
    return abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01


def on_seg(p, a, b):
    if abs(a[0] - b[0]) < 0.01:
        return abs(p[0] - a[0]) < 0.01 and min(a[1], b[1]) - 0.01 <= p[1] <= max(a[1], b[1]) + 0.01
    if abs(a[1] - b[1]) < 0.01:
        return abs(p[1] - a[1]) < 0.01 and min(a[0], b[0]) - 0.01 <= p[0] <= max(a[0], b[0]) + 0.01
    return False


def new_uuid():
    return str(_uuid.uuid4())


def fmt(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return s if s != '-0' else '0'


def wire(a, b):
    return ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n'
            '\t\t)\n\t\t(uuid "%s")\n\t)') % (fmt(a[0]), fmt(a[1]), fmt(b[0]), fmt(b[1]), new_uuid())


def glabel(net, p, d, shape='bidirectional'):
    """global label at p; d = direction the label body extends ('R' or 'L', 'U', 'D')."""
    ang = {'R': 0, 'L': 180, 'U': 90, 'D': 270}[d]
    just = 'left' if d in ('R', 'U') else 'right'
    off = 1.15 * len(net) + 4.4                 # where KiCad autoplaces the page references
    r = (p[0] + DV[d][0] * off, p[1] + DV[d][1] * off)
    return ('\t(global_label "%s"\n\t\t(shape %s)\n\t\t(at %s %s %d)\n\t\t(fields_autoplaced yes)\n\t\t(effects\n'
            '\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n\t\t(uuid "%s")\n'
            '\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %s %s %d)\n\t\t\t(show_name no)\n'
            '\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
            '\t\t\t\t(justify %s)\n\t\t\t)\n\t\t)\n\t)') % (
        net, shape, fmt(p[0]), fmt(p[1]), ang, just, new_uuid(), fmt(r[0]), fmt(r[1]), ang, just)


def no_connect(p):
    return '\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid "%s")\n\t)' % (fmt(p[0]), fmt(p[1]), new_uuid())


DV = {'R': (1, 0), 'L': (-1, 0), 'U': (0, -1), 'D': (0, 1)}


def stub_label(blocks, p, d, net):
    q = (p[0] + DV[d][0] * STUB, p[1] + DV[d][1] * STUB)
    blocks.append(wire(p, q))
    blocks.append(glabel(net, q, d))


def wire_component(blocks, p):
    """indices of wire / junction blocks electrically connected to point p (endpoints and T-joins)."""
    wires = {i: wire_pts(b) for i, b in enumerate(blocks) if kind(b) == 'wire'}
    seen, pts, todo = set(), [p], [p]
    while todo:
        q = todo.pop()
        for i, (a, b) in wires.items():
            if i in seen:
                continue
            if same(q, a) or same(q, b) or on_seg(q, a, b) or on_seg(a, (q[0], q[1]), (q[0], q[1])):
                seen.add(i)
                for e in (a, b):
                    todo.append(e); pts.append(e)
        # wire endpoints lying on a wire already in the set (T joins from the other side)
        for i, (a, b) in wires.items():
            if i in seen:
                continue
            for j in list(seen):
                c, e = wires[j]
                if on_seg(a, c, e) or on_seg(b, c, e):
                    seen.add(i); todo += [a, b]; pts += [a, b]
                    break
    juncs = {i for i, b in enumerate(blocks) if kind(b) == 'junction' and any(same(at(b)[:2], x) for x in pts)}
    labels = {i for i, b in enumerate(blocks) if kind(b) in ('label', 'global_label')
              and any(same(at(b)[:2], x) for x in pts)}
    return seen, juncs, labels, pts

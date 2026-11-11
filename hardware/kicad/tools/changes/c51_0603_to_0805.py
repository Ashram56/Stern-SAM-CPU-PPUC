"""c51 (board + schematic, 2026-10-31): the targeted repairability pass Vincent chose ("Ciblé"): every 0603 resistor
and capacitor whose 0805 footprint fits in place becomes 0805, without moving parts or copper.
The swap keeps each part's centre, rotation, reference text, fields and nets, and rewrites its footprint from the
KiCad 10 library 0805 (pads, courtyard, silk, fab, 3D model). The 0805 pads contain the 0603 pads' centres, so every
track end stays connected.
Which parts fit is decided by DRC (unconnected items are compared by count: their pairing moves with the geometry): swap all candidates, run DRC with zone refill, put back every part named in a new
copper, courtyard or mask error, and repeat until no new error appears (search mode). The kept list is written to
c51_0805_refs.txt and applied again in apply mode, which also changes the symbols' Footprint field.
Usage: c51_0603_to_0805.py search in.kicad_pcb work_dir      (needs in.kicad_pro / .kicad_dru beside in.kicad_pcb)
       c51_0603_to_0805.py apply in.kicad_pcb out.kicad_pcb sam_cpu_dir refs.txt"""
import json, os, re, subprocess, sys
from collections import Counter

R = {'from': 'Resistor_SMD:R_0603_1608Metric', 'to': 'Resistor_SMD:R_0805_2012Metric',
     'descr': ('Resistor SMD 0603 (1608 Metric)', 'Resistor SMD 0805 (2012 Metric)'),
     'model': ('R_0603_1608Metric.step', 'R_0805_2012Metric.step'),
     'sub': [('(start -0.237258 -0.5225)', '(start -0.227064 -0.735)'), ('(end 0.237258 -0.5225)', '(end 0.227064 -0.735)'),
             ('(start -0.237258 0.5225)', '(start -0.227064 0.735)'), ('(end 0.237258 0.5225)', '(end 0.227064 0.735)'),
             ('(start -1.48 -0.73)', '(start -1.68 -0.95)'), ('(end 1.48 0.73)', '(end 1.68 0.95)'),
             ('(start -0.8 -0.4125)', '(start -1 -0.625)'), ('(end 0.8 0.4125)', '(end 1 0.625)')],
     'pad': (0.825, 0.9125, '(size 0.8 0.95)', '(size 1.025 1.4)', '(roundrect_rratio 0.25)', '(roundrect_rratio 0.243902)')}
C = {'from': 'Capacitor_SMD:C_0603_1608Metric', 'to': 'Capacitor_SMD:C_0805_2012Metric',
     'descr': ('Capacitor SMD 0603 (1608 Metric)', 'Capacitor SMD 0805 (2012 Metric)'),
     'model': ('C_0603_1608Metric.step', 'C_0805_2012Metric.step'),
     'sub': [('(start -0.14058 -0.51)', '(start -0.261252 -0.735)'), ('(end 0.14058 -0.51)', '(end 0.261252 -0.735)'),
             ('(start -0.14058 0.51)', '(start -0.261252 0.735)'), ('(end 0.14058 0.51)', '(end 0.261252 0.735)'),
             ('(start -1.48 -0.73)', '(start -1.7 -0.98)'), ('(end 1.48 0.73)', '(end 1.7 0.98)'),
             ('(start -0.8 -0.4)', '(start -1 -0.625)'), ('(end 0.8 0.4)', '(end 1 0.625)')],
     'pad': (0.775, 0.95, '(size 0.9 0.95)', '(size 1 1.45)', '(roundrect_rratio 0.25)', '(roundrect_rratio 0.25)')}
KINDS = (R, C)
BLOCKING = {'clearance', 'courtyards_overlap', 'solder_mask_bridge', 'shorting_items', 'copper_edge_clearance',
            'hole_clearance', 'tracks_crossing', 'starved_thermal', 'unconnected_items', 'items_not_allowed',
            'edge_clearance', 'malformed_courtyard'}


def block_end(s, i):
    n = 0
    for j in range(i, len(s)):
        if s[j] == '(': n += 1
        elif s[j] == ')':
            n -= 1
            if n == 0: return j + 1


def footprints(s):
    """(start, end, ref, kind) of every 0603 R / C footprint."""
    out = []
    for k in KINDS:
        for m in re.finditer(r'\t\(footprint "%s"' % re.escape(k['from']), s):
            e = block_end(s, m.start() + 1)
            ref = re.search(r'\(property "Reference" "([^"]+)"', s[m.start():e]).group(1)
            out.append((m.start(), e, ref, k))
    return out


def swap_block(b, k):
    b = b.replace('"%s"' % k['from'], '"%s"' % k['to'], 1)
    b = b.replace(k['descr'][0], k['descr'][1], 1).replace(k['model'][0], k['model'][1], 1)
    for a, c in k['sub']:
        if b.count(a) != 1: return None
        b = b.replace(a, c)
    old, new, s0, s1, r0, r1 = k['pad']
    for sign in ('-', ''):
        b, n = re.subn(r'\(at %s%s 0( [-\d.]+)?\)' % (sign, re.escape('%g' % old)),
                       lambda m: '(at %s%g 0%s)' % (sign, new, m.group(1) or ''), b)
        if n != 1: return None
    if b.count(s0) != 2: return None
    b = b.replace(s0, s1).replace(r0, r1)
    return b


def swap(s, refs):
    done = []
    for a, e, ref, k in sorted(footprints(s), reverse=True):
        if ref not in refs: continue
        nb = swap_block(s[a:e], k)
        if nb is None: print('skip (non-library geometry)', ref); continue
        s = s[:a] + nb + s[e:]; done.append(ref)
    return s, done


def drc(pcb):
    js = pcb[:-len('.kicad_pcb')] + '.json'
    subprocess.run(['/opt/k10/kicad-cli', 'pcb', 'drc', '--refill-zones', '--format', 'json', '-o', js, pcb],
                   capture_output=True)
    j = json.load(open(js))
    v = [x for x in j['violations'] if x['type'] in BLOCKING]
    v += [{'type': 'unconnected_items', 'items': [{'description': 'count'}]}] * len(j['unconnected_items'])
    return v


def key(v): return (v['type'], tuple(sorted(i['description'] for i in v['items'])))


def search(inp, work):
    base = open(inp).read(); stem = inp[:-len('.kicad_pcb')]
    for ext in ('.kicad_pro', '.kicad_dru'):
        open(os.path.join(work, 'try' + ext), 'w').write(open(stem + ext).read())
    b0 = Counter(key(v) for v in drc(inp))
    refs = {r for _, _, r, _ in footprints(base)}
    print('candidates', len(refs))
    for it in range(40):
        s, done = swap(base, refs); refs &= set(done)
        p = os.path.join(work, 'try.kicad_pcb'); open(p, 'w').write(s)
        new = Counter(key(v) for v in drc(p)) - b0
        bad = set()
        for (t, items) in new:          # put back one swapped part per error, so its neighbour may keep its 0805
            hit = [m.group(1) for d in items for m in [re.search(r'(?: of |^Footprint )([RC]\d+)\b', d)]
                   if m and m.group(1) in refs]
            if hit and not bad & set(hit): bad.add(hit[-1])
        print('pass', it, 'swapped', len(refs), 'new errors', sum(new.values()), 'put back', len(bad))
        if not new: break
        if not bad: raise SystemExit('new errors not tied to a swapped part: %s' % list(new)[:5])
        refs -= bad
    open(os.path.join(work, 'c51_0805_refs.txt'), 'w').write('\n'.join(sorted(refs, key=lambda r: (r[0], int(r[1:])))) + '\n')
    print('kept', len(refs))


def apply(inp, out, sch, refsfile):
    refs = set(open(refsfile).read().split())
    s, done = swap(open(inp).read(), refs)
    assert set(done) == refs, refs - set(done)
    open(out, 'w').write(s)
    n = 0
    for f in sorted(os.listdir(sch)):
        if not f.endswith('.kicad_sch'): continue
        p = os.path.join(sch, f); t = open(p).read(); changed = False
        for m in list(re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "Device:[RC]"\)', t))[::-1]:
            e = block_end(t, m.start() + 2); b = t[m.start():e]
            ref = re.search(r'\(reference "([^"]+)"\)', b).group(1)
            if ref not in refs: continue
            for k in KINDS:
                if '"%s"' % k['from'] in b:
                    b = b.replace('"%s"' % k['from'], '"%s"' % k['to'], 1); n += 1; changed = True
            t = t[:m.start()] + b + t[e:]
        if changed: open(p, 'w').write(t)
    print('swapped', len(done), 'symbols', n)


if __name__ == '__main__':
    if sys.argv[1] == 'search': search(sys.argv[2], sys.argv[3])
    else: apply(*sys.argv[2:6])

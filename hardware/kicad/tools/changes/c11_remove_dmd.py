"""Change 11 (2026-10-07): remove every DMD interface from the schematic.

    python3 c11_remove_dmd.py ../../sam_cpu

Vincent's decision: DMD links over long wires will not work reliably (signal integrity), so both display paths go.
- Page 10: the original DMD driver (J5, U21 74HCT245, RN4 / RN5, R176-R182 pull-downs, C95). J18 GI dimmer stays.
- Page 12: the HD panel bus (J25 / J26 HUB75, U27-U29, RN6-RN11, C122-C124, TP23 / TP24). U30 (7th 74HC165,
  coin door memory protect) and U31 (first 74HC595, LED_STATUS / GI_SPARE) stay: they are switch-chain parts.
- MCU page: the DMD_* labels on GPIO20-36 become no-connect flags. The pins are left unassigned.
Everything inside the two DMD frames is deleted (symbols, wires, labels, junctions, flags, frame and its title).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import schlib as L

# (sheet file, frame rectangle start / end) whose whole content goes
FRAMES = {
    'display_gi.kicad_sch': ((30.48, 71.12), (284.48, 193.04)),
    'dmd_panels.kicad_sch': ((15.24, 35.56), (264.16, 284.48)),
}
RENAME = {'Display and GI': 'GI dimmer', 'DMD panels': 'Switch chain extensions'}
ROOT_TEXT = {
    'J5 original DMD driver and J18 GI dimmer header': 'J18 GI dimmer header',
    'HD DMD panels (HUB75) and switch-chain extensions': 'Switch-chain extensions: 7th 74HC165, first 74HC595',
}
NOTES = {
    'display_gi.kicad_sch': 'J18 is the default GI dimmer link of ARCHITECTURE.md 10.2: +5 V, GND, GI_PWM, GI_SPARE '
                            '(GI_SPARE is an on/off output of U31).\\nThe DMD interfaces were removed (2026-10-07): '
                            'DMD signals do not survive the long cabinet wires.',
    'dmd_panels.kicad_sch': 'U31: first 74HC595 of the strobe chain (status LED, GI_SPARE, 6 spare outputs). U30: last '
                            '74HC165 of the switch chain\\n(coin door memory protect + 7 spare inputs). Both share SW_CLK '
                            'and SW_LOAD_N (165 load / 595 latch on one pulse).\\nThe HD DMD panel outputs that shared '
                            'this page were removed (2026-10-07).',
}
MCU_NOTE_OLD = ('PIO2 drives two HD DMD panels on GPIO20-36 (data 20-31, CLK, LAT, OE, A, B); '
                'the original DMD (J5) shares GPIO20-26.')
MCU_NOTE_NEW = 'GPIO20-36 are unassigned (no-connect flags; the DMD outputs were removed).'


def inside(p, frame):
    (x0, y0), (x1, y1) = frame
    return x0 - 0.01 <= p[0] <= x1 + 0.01 and y0 - 0.01 <= p[1] <= y1 + 0.01


def rect_of(b):
    m = re.search(r'\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)', b)
    return (float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4)))


def ref_of(b):
    m = re.search(r'\(property "Reference" "([^"]+)"', b)
    return m.group(1) if m else None


def clear_frame(path, frame, note):
    head, blocks, foot = L.split(open(path).read())
    keep, refs = [], []
    for b in blocks:
        k = L.kind(b)
        if k == 'wire':
            a, c = L.wire_pts(b)
            gone = inside(a, frame) and inside(c, frame)
        elif k == 'rectangle':
            gone = rect_of(b) == frame
        elif k in ('symbol', 'junction', 'no_connect', 'global_label', 'label', 'text'):
            p = L.at(b)
            gone = p is not None and inside(p[:2], frame)
        else:
            gone = False
        if gone and k == 'symbol' and not ref_of(b).startswith('#'):
            refs.append(ref_of(b))
        if not gone:
            keep.append(b)
    # sheet note (top left, outside the frames)
    for i, b in enumerate(keep):
        if L.kind(b) == 'text' and L.at(b)[:2] == (15.24, 15.24):
            keep[i] = re.sub(r'\(text "(?:[^"\\]|\\.)*"', lambda m: '(text "%s"' % note, b, count=1)
    open(path, 'w').write(L.join(head, keep, foot))
    return sorted(refs, key=lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r))))


def mcu_no_connects(path):
    head, blocks, foot = L.split(open(path).read())
    dmd = [i for i, b in enumerate(blocks) if L.kind(b) == 'global_label' and L.label_text(b).startswith('DMD_')]
    drop, flags, names = set(), [], []
    for i in dmd:
        p = L.at(blocks[i])[:2]
        wires, juncs, labels, pts = L.wire_component(blocks, p)
        assert len(wires) == 1 and not juncs and labels == {i}, (L.label_text(blocks[i]), wires, juncs, labels)
        a, c = L.wire_pts(blocks[next(iter(wires))])
        pin = c if L.same(a, p) else a
        drop |= wires | {i}
        flags.append(L.no_connect(pin))
        names.append(L.label_text(blocks[i]))
    blocks = [b for j, b in enumerate(blocks) if j not in drop] + flags
    for j, b in enumerate(blocks):
        if L.kind(b) == 'text' and MCU_NOTE_OLD in b:
            blocks[j] = b.replace(MCU_NOTE_OLD, MCU_NOTE_NEW)
    open(path, 'w').write(L.join(head, blocks, foot))
    return names


def root(sch):
    path = os.path.join(sch, 'sam_cpu.kicad_sch')
    s = open(path).read()
    for old, new in RENAME.items():
        s = s.replace('(property "Sheetname" "%s"' % old, '(property "Sheetname" "%s"' % new)
    for old, new in ROOT_TEXT.items():
        s = s.replace('(text "%s"' % old, '(text "%s"' % new)
    open(path, 'w').write(s)
    pro = os.path.join(sch, 'sam_cpu.kicad_pro')
    pj = json.load(open(pro))
    pj['sheets'] = [[u, RENAME.get(n, n)] for u, n in pj['sheets']]
    json.dump(pj, open(pro, 'w'), indent=2)


def main(sch):
    for fn, frame in FRAMES.items():
        print(fn, 'removed:', ' '.join(clear_frame(os.path.join(sch, fn), frame, NOTES[fn])))
    print('mcu.kicad_sch no-connect flags for:', ' '.join(mcu_no_connects(os.path.join(sch, 'mcu.kicad_sch'))))
    root(sch)


if __name__ == '__main__':
    main(sys.argv[1])

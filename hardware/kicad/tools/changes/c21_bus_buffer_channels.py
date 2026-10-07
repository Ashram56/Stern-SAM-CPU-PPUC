"""Change 21 (2026-10-07): reverse the channel order of the bus buffers U6 (SN74LVC8T245) and U7 (74AHCT541) on the
IO bus sheet, so that c22 can turn both parts 180 degrees on the board with their RP2354B side facing U4 and the bit
order still matching U4's pins and J9.

    python3 c21_bus_buffer_channels.py ../../sam_cpu/io_bus.kicad_sch

Every channel of each buffer is identical, so only which channel carries which bit changes; the RP2354B GPIOs and
the J9 pinout do not.
- U6: BUS_Dk moves from channel k+1 to channel 8-k (A side: label text swapped; B side: the wires from the B pins
  to RN1 / RN2 become local label pairs BD0-BD7).
- U7: BUS_A0-A3 / BUS_IOSTB move from channels 0-4 to channels 4-0 (inputs: label text swapped; outputs: the wires
  from Y0-Y4 to RN3 / R25 become label pairs BA0-BA3 / BSTB). Y2 (BUS_A2) keeps its channel and its wire.
"""
import sys
import schlib as L

U6, U7 = (101.6, 91.44), (101.6, 198.12)
# U6 B pins (B1 pin 21 ... B8 pin 14) at x +10.16, y offsets from the library symbol
U6_B = {21: 17.78, 20: 12.7, 19: 7.62, 18: 2.54, 17: -2.54, 16: -7.62, 15: -12.7, 14: -17.78}
# U7 Y pins carrying something: pin -> (old signal, new signal)
U7_Y = {18: (12.7, 'BA0', 'BSTB'), 17: (10.16, 'BA1', 'BA3'), 15: (5.08, 'BA3', 'BA1'), 14: (2.54, 'BSTB', 'BA0')}
U6_A = {'BUS_D%d' % k: 'BUS_D%d' % (7 - k) for k in range(8)}
U7_A = {'BUS_A0': 'BUS_IOSTB', 'BUS_A1': 'BUS_A3', 'BUS_A3': 'BUS_A1', 'BUS_IOSTB': 'BUS_A0'}


def label(net, p, d):
    """local label at p, text running away from the wire end ('R' or 'L')"""
    ang, just = (0, 'left') if d == 'R' else (180, 'right')
    return ('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            '\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)') % (
        net, L.fmt(p[0]), L.fmt(p[1]), ang, just, L.new_uuid())


def pin(sym, dx, dy):
    return (round(sym[0] + dx, 4), round(sym[1] - dy, 4))


def relabel(blocks, x, table):
    n = 0
    for i, b in enumerate(blocks):
        if L.kind(b) == 'global_label' and abs(L.at(b)[0] - x) < 0.01 and L.label_text(b) in table:
            t = L.label_text(b)
            blocks[i] = b.replace('(global_label "%s"' % t, '(global_label "%s"' % table[t], 1)
            n += 1
    assert n == len(table), (x, n)


def rewire(blocks, p, new_here, old_there):
    """drop the wires from pin p to the part it drove; label p with new_here and the far end with old_there"""
    wires, juncs, labels, pts = L.wire_component(blocks, p)
    assert wires and not labels, (p, labels)
    ends = [q for q in pts if sum(1 for e in pts if L.same(e, q)) == 1 and not L.same(q, p)]
    assert len(ends) == 1, (p, ends)
    for i in sorted(wires | juncs, reverse=True):
        del blocks[i]
    blocks.append(label(new_here, p, 'R'))
    blocks.append(label(old_there, ends[0], 'L'))


def main(path):
    s = open(path).read()
    if '"BD0"' in s:
        sys.exit('already applied')
    head, blocks, foot = L.split(s)
    relabel(blocks, U6[0] - 10.16 - 5.08, U6_A)
    relabel(blocks, U7[0] - 12.7 - 5.08, U7_A)
    for k, (pn, dy) in enumerate(U6_B.items()):          # channel k+1 carried BUS_Dk, now carries BUS_D(7-k)
        rewire(blocks, pin(U6, 10.16, dy), 'BD%d' % (7 - k), 'BD%d' % k)
    for pn, (dy, old, new) in U7_Y.items():
        rewire(blocks, pin(U7, 12.7, dy), new, old)
    open(path, 'w').write(L.join(head, blocks, foot))
    print('U6: 8 channels reversed; U7: 4 outputs re-labelled')


if __name__ == '__main__':
    main(sys.argv[1])

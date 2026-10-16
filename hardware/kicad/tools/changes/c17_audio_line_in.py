"""Change 17 (2026-10-07): route the DAC outputs through the line-in jack J30 (page 13, c16).

The two long wires from the PCM5102A outputs (U22 OUTL / OUTR) up to the 470 R series resistors (R187 / R190) are
removed past the TP19 / TP20 branches: the DAC ends get global labels AUD_DAC_L / AUD_DAC_R at x 101.6 and the
resistor ends get AUD_AMP_L / AUD_AMP_R. J30's normally-closed contacts join them while no plug is in. Nothing else moves.

    python3 c17_audio_line_in.py ../../sam_cpu/audio.kicad_sch
"""
import sys
import schlib as L

# (horizontal wire from the DAC pin, vertical wire up to the resistor, DAC-end label, resistor-end label)
CUTS = [(((88.9, 132.08), (134.62, 132.08)), ((134.62, 132.08), (134.62, 55.88)), 'AUD_DAC_L', (134.62, 55.88),
         'AUD_AMP_L'),
        (((88.9, 134.62), (137.16, 134.62)), ((137.16, 134.62), (137.16, 91.44)), 'AUD_DAC_R', (137.16, 91.44),
         'AUD_AMP_R')]
XL = 101.6          # new end of the DAC wires, clear of the TP branches (x 93.98 / 91.44) and of the frames


def main(path):
    s = open(path).read()
    if 'AUD_DAC_L' in s:
        sys.exit('already applied')
    head, blocks, foot = L.split(s)
    for hor, ver, dac, amp_pt, amp in CUTS:
        for a, b in (hor, ver):
            i = [k for k, x in enumerate(blocks) if L.kind(x) == 'wire'
                 and {L.wire_pts(x)[0], L.wire_pts(x)[1]} == {a, b}]
            assert len(i) == 1, (a, b, i)
            del blocks[i[0]]
        end = (XL, hor[0][1])
        blocks.append(L.wire(hor[0], end))
        blocks.append(L.glabel(dac, end, 'R', 'passive'))
        # resistor end: the short wire to R187 / R190 pin 1 starts here (or the pin itself)
        blocks.append(L.glabel(amp, amp_pt, 'L', 'passive'))
    open(path, 'w').write(L.join(head, blocks, foot))
    print('split', ', '.join(c[2] + ' / ' + c[4] for c in CUTS))


if __name__ == '__main__':
    main(sys.argv[1])

"""Change 14 (2026-10-07): connect the RS485 port of page 13 on the MCU sheet.

    python3 c14_mcu_rs485_labels.py ../../sam_cpu

- RP2354B GPIO20 / 21 / 22 (pads 20-22, freed by c11): the no-connect flag becomes a 5.08 mm stub and a global
  label RP_RS485_TX / RX / DE, where the DMD_D0-D2 labels were.
- Pi header J21 pins 7 (GPIO4 TXD3), 29 (GPIO5 RXD3), 26 (GPIO7 RTS3): same, labels PI_RS485_TX / RX / DE,
  stubs to the left like FRAME_MOSI / CS / SCK below them.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import schlib as L

# pin end (sheet mm), label direction, net
PINS = [
    ((304.8, 160.02), 'L', 'PI_RS485_TX'),     # J21.7
    ((304.8, 162.56), 'L', 'PI_RS485_RX'),     # J21.29
    ((304.8, 170.18), 'L', 'PI_RS485_DE'),     # J21.26
]
RP = {'DMD_D0': 'RP_RS485_TX', 'DMD_D1': 'RP_RS485_RX', 'DMD_D2': 'RP_RS485_DE'}   # GPIO20-22
NOTE_OLD = 'GPIO20-36 are unassigned (no-connect flags; the DMD outputs were removed).'
NOTE_NEW = ('GPIO20-22: RS485 port (UART1 TX / RX, driver enable, page 13); GPIO23-36 unassigned. Pi UART3 '
            '(GPIO4 / 5, RTS on GPIO7) reaches the same port.')


def old_rp_pins():
    """pin end and label direction of the DMD_D0-D2 labels before c11 (from git)."""
    import subprocess
    old = subprocess.run(['git', 'show', 'd8a858f~1:hardware/kicad/sam_cpu/mcu.kicad_sch'], capture_output=True,
                         text=True, check=True, cwd=HERE).stdout
    head, blocks, foot = L.split(old)
    out = []
    for b in blocks:
        if L.kind(b) == 'global_label' and L.label_text(b) in RP:
            p = L.at(b)
            wires, _, _, _ = L.wire_component(blocks, p[:2])
            a, c = L.wire_pts(blocks[next(iter(wires))])
            pin = c if L.same(a, p[:2]) else a
            d = 'R' if p[0] > pin[0] else 'L' if p[0] < pin[0] else 'D' if p[1] > pin[1] else 'U'
            out.append((pin, d, RP[L.label_text(b)]))
    return out


TITLES = {  # title blocks c11 left behind on the two pages it emptied
    'display_gi.kicad_sch': ('J5 original DMD driver and J18 GI dimmer header', 'J18 GI dimmer header'),
    'dmd_panels.kicad_sch': ('HD DMD panels (HUB75) and switch-chain extensions',
                             'Switch-chain extensions: 7th 74HC165, first 74HC595'),
}


def titles(sch):
    for fn, (old, new) in TITLES.items():
        path = os.path.join(sch, fn)
        s = open(path).read()
        open(path, 'w').write(s.replace('(title "%s")' % old, '(title "%s")' % new))


def main(sch):
    path = os.path.join(sch, 'mcu.kicad_sch')
    head, blocks, foot = L.split(open(path).read())
    todo = PINS + old_rp_pins()
    assert len(todo) == 6
    for pin, d, net in todo:
        nc = [i for i, b in enumerate(blocks) if L.kind(b) == 'no_connect' and L.same(L.at(b)[:2], pin)]
        assert len(nc) == 1, (net, pin)
        del blocks[nc[0]]
        L.stub_label(blocks, pin, d, net)
    for i, b in enumerate(blocks):
        if L.kind(b) == 'text' and NOTE_OLD in b:
            blocks[i] = b.replace(NOTE_OLD, NOTE_NEW)
    open(path, 'w').write(L.join(head, blocks, foot))
    print('labels added:', ' '.join(n for _, _, n in todo))
    titles(sch)


if __name__ == '__main__':
    main(sys.argv[1])

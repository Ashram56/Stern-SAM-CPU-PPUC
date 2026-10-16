"""Change 01 (2026-10-06): two HD DMD panels. Re-assign RP2354B GPIOs on the MCU sheet, in place.
Pin map: /mnt/project-files/hardware/dmd_two_panel_pin_proposal.md (17-signal variant)."""
import sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import schlib as L
import design2
from kigen import pin_outward

F = os.path.join(HERE, '..', '..', 'sam_cpu', 'mcu.kicad_sch')
NEW = {20: 'DMD_D0', 21: 'DMD_D1', 22: 'DMD_D2', 23: 'DMD_D3', 24: 'DMD_D4', 25: 'DMD_D5', 26: 'DMD_D6',
       27: 'DMD_D7', 28: 'DMD_D8', 29: 'DMD_D9', 30: 'DMD_D10', 31: 'DMD_D11',
       32: 'DMD_CLK', 33: 'DMD_LAT', 34: 'DMD_OE', 35: 'DMD_A', 36: 'DMD_B',
       37: 'RP_IRQ_N', 38: 'GI_PWM', 39: 'AMP_MUTE', 40: 'FRAME_MOSI', 41: 'FRAME_CS_N', 42: 'FRAME_SCK',
       44: 'RP_UART_TX', 45: 'RP_UART_RX', 46: 'VMON_5V', 47: 'VMON_12V'}

page = [p for p in design2.PAGES if p.filename == 'mcu.kicad_sch'][0]
u4 = [q for q in page.parts if q.ref == 'U4'][0]
gpio_pin = {int(p['name'].split('/')[0][4:]): p['number'] for p in u4.sd.pins if p['name'].startswith('GPIO')}


def outward(part, num):
    p = part.pin(num)
    d = pin_outward(p['angle'], part.rot)
    if part.mirror == 'y':
        d = {'L': 'R', 'R': 'L'}.get(d, d)
    return d


# every pin end on the sheet, to find what a removed wire used to connect
ends = []
for part in page.parts:
    for p in part.unit_pins():
        if part.lib_id.startswith('power:'):
            continue
        ends.append((part, p['number'], part.pin_pos(p['number'])))

text = open(F).read()
head, blocks, foot = L.split(text)
drop, add = set(), []
for g, new in sorted(NEW.items()):
    num = gpio_pin[g]
    P = u4.pin_pos(num)
    d = outward(u4, num)
    old = u4.nets[num]
    if old == new:
        continue
    nc = [i for i, b in enumerate(blocks) if L.kind(b) == 'no_connect' and L.same(L.at(b)[:2], P)]
    if nc:
        drop |= set(nc)
        L.stub_label(add, P, d, new)
        continue
    q = (P[0] + L.DV[d][0] * L.STUB, P[1] + L.DV[d][1] * L.STUB)
    lab = [i for i, b in enumerate(blocks) if L.kind(b) == 'global_label' and L.same(L.at(b)[:2], q)]
    if lab:
        i = lab[0]
        blocks[i] = blocks[i].replace('(global_label "%s"' % old, '(global_label "%s"' % new, 1)
        continue
    # routed with wires on this sheet: remove the run, label both ends
    ws, js, ls, pts = L.wire_component(blocks, P)
    assert ws, (g, old)
    drop |= ws | js | ls
    L.stub_label(add, P, d, new)
    for part, n2, e in ends:
        if part is u4 and n2 == num:
            continue
        if any(L.same(e, x) for x in pts):
            d2 = outward(part, n2)
            if part.ref == 'R17':      # keep LED_STATUS clear of the GPIO46 label on the same row
                k = (e[0] + 2.54, e[1]); m = (k[0], k[1] + 5.08)
                add += [L.wire(e, k), L.wire(k, m), L.glabel(old, m, 'D')]
            elif part.ref == 'R18':    # step up so the label clears R19 next to it
                k = (e[0], e[1] - 2.54)
                add += [L.wire(e, k), L.glabel(old, k, 'R')]
            else:
                L.stub_label(add, e, d2, old)
            print('GPIO%d: %s moved off, %s.%s keeps %s by label' % (g, old, part.ref, n2, old))
# GPIO43 becomes free; old users of 43 none. Pins left without a net get a no-connect
blocks = [b for i, b in enumerate(blocks) if i not in drop] + add
s = L.join(head, blocks, foot)
s = s.replace('PIO2 DMD on GPIO21-27, GPIO31 coin door memory protect.',
              'PIO2 drives two HD DMD panels on GPIO20-36 (data 20-31, CLK, LAT, OE, A, B); the original DMD (J5) shares GPIO20-26.'
              '\\nFrames from the Pi on SPI1 (GPIO40-42), UART0 on GPIO44-45, ADC monitors on GPIO46-47, GPIO43 spare.'
              ' Coin door, status LED and GI_SPARE moved onto the switch chain.')
open(F, 'w').write(s)
print('mcu: removed', len(drop), 'items, added', len(add))

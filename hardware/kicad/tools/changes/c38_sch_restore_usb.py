"""c38 (schematic): USB-C J19 comes back on the MCU sheet as it was at e6c37a8 (VBUS pull-down R10, CC pull-downs
R11 / R12, USB series resistors R13 / R14, their wires and ground symbols); the no-connects c35 put on U4 USB_DP /
USB_DM go. Labels USB_D+ / USB_D- (U4 side) and USB_C_D+ / USB_C_D- (connector side) name the pair so the
board sees it as a differential pair (netclass USB). J20, the GI dimmer and the DIP block stay removed, SWD stays on J21 pins 18 / 22.
Usage: c38_sch_restore_usb.py old_mcu.kicad_sch (mcu.kicad_sch at e6c37a8) mcu.kicad_sch"""
import re
import sys
import uuid

import schlib

old, cur = sys.argv[1], sys.argv[2]
o = schlib.split(open(old).read())[1]
h, n, f = schlib.split(open(cur).read())
have = set(n)


def pts(b):
    return [(float(x), float(y)) for x, y in re.findall(r'\(xy ([\d.-]+) ([\d.-]+)\)', b)]


def usb_area(x, y):       # J19 block: left of U4, above J20 (J20 sits at y 185-191)
    return x <= 157.5 and 110 <= y <= 170


back = []
for b in o:
    if b in have:
        continue
    k = schlib.kind(b)
    if k == 'wire':
        ok = all(usb_area(*p) for p in pts(b))
    elif k in ('symbol', 'no_connect', 'junction', 'label'):
        ok = usb_area(*schlib.at(b)[:2])
    else:
        ok = False
    if ok:
        back.append(b)
refs = sorted(re.search(r'"Reference" "([^"]+)"', b).group(1) for b in back if schlib.kind(b) == 'symbol')
assert [r for r in refs if not r.startswith('#')] == ['J19', 'R10', 'R11', 'R12', 'R13', 'R14'], refs
# the no-connects on U4 USB_DM / USB_DP (pins at x 157.48, y 121.92 / 124.46)
nc = [b for b in n if schlib.kind(b) == 'no_connect' and abs(schlib.at(b)[0] - 157.48) < 0.01
      and min(abs(schlib.at(b)[1] - y) for y in (121.92, 124.46)) < 0.01]
assert len(nc) == 2
n = [b for b in n if b not in nc] + back
n = [b.replace('No USB: the Pi flashes the RP2354B over SWD on J21',
               'USB-C J19 (backup flashing path); the Pi also flashes the RP2354B over SWD on J21') for b in n]
tpl = next(b for b in n if schlib.kind(b) == 'label' and schlib.label_text(b) == 'SWCLK')


def label(text, x, y):
    b = re.sub(r'\(label "[^"]*"', '(label "%s"' % text, tpl, count=1)
    b = re.sub(r'\(at [-\d.]+ [-\d.]+ [-\d.]+\)', '(at %s %s 0)' % (schlib.fmt(x), schlib.fmt(y)), b, count=1)
    return re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % uuid.uuid4(), b, count=1)


# on the wires U4 pin 66 / 67 -> R13 / R14 and R13 / R14 -> J19 D- / D+
n += [label('USB_D-', 127, 121.92), label('USB_D+', 127, 124.46), label('USB_C_D-', 91.44, 116.84), label('USB_C_D+', 93.98, 127)]
open(cur, 'w').write(schlib.join(h, n, f))
print('restored', len(back), 'blocks:', refs)

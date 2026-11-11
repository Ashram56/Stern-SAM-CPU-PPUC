"""c35 (schematic): parts removed to free routing space (Vincent, 2026-10-17, second CPU board alternative), and the Pi
SWD lines matched to Raspberry Pi's stock OpenOCD config.
- USB-C J19 and its parts go (VBUS pull-down R10, CC pull-downs R11 / R12, USB series resistors R13 / R14); U4 USB_DP / USB_DM get no-connects.
  The Pi reaches the RP2354B over UART0 and flashes it over SWD (blank flash works over SWD).
- GI dimmer sheet (J18, R183-R185) goes; GI_PWM (U4) and GI_SPARE (U31 QB) become no-connects.
- J20 SWD header goes: the Pi's own SWD lines (J21) are the programming path.
- DIP block goes: SW3 (already not loaded), its pull-ups R168-R175, C93 and U14, the 74HC165 that read only SW3; U15's
  serial input (was U14 Q7) goes to GND, so the switch chain is 8 bits shorter.
- J21: SWDIO on pin 18 (GPIO24) and SWCLK on pin 22 (GPIO25), as interface/raspberrypi-swd.cfg (Raspberry Pi OpenOCD).
Dangling wires, labels and power symbols left by the removals are deleted by running ERC until it is clean.
Usage: c35_sch_trim_usb_gi_dip_swd.py project_dir kicad-cli"""
import json, os, re, subprocess, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schlib

d, cli = sys.argv[1], sys.argv[2]
P = lambda f: os.path.join(d, f)
REMOVE = {'mcu.kicad_sch': ['J19', 'R10', 'R11', 'R12', 'R13', 'R14', 'J20'],
          'sw_dedicated_2.kicad_sch': ['SW3', 'U14', 'C93'] + ['R%d' % i for i in range(168, 176)]}


def ref_of(b):
    m = re.search(r'\(property "Reference" "([^"]+)"', b)
    return m.group(1) if m else None


def no_connect(x, y):
    return ('\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid "%s")\n\t)' % (schlib.fmt(x), schlib.fmt(y), uuid.uuid4()))


def edit(fn, fun):
    h, bl, f = schlib.split(open(P(fn)).read())
    bl = fun(bl)
    open(P(fn), 'w').write(schlib.join(h, bl, f))


# 1. symbols
for fn, refs in REMOVE.items():
    def f(bl, refs=refs):
        out = [b for b in bl if not (schlib.kind(b) == 'symbol' and ref_of(b) in refs)]
        assert len(bl) - len(out) == len(refs), (fn, len(bl) - len(out))
        return out
    edit(fn, f)

# 2. SWD swap on the J21 side (labels at x 345.44)
def swd(bl):
    n = 0
    for i, b in enumerate(bl):
        if schlib.kind(b) == 'label' and abs(schlib.at(b)[0] - 345.44) < 0.01 and schlib.label_text(b) in ('SWCLK', 'SWDIO'):
            new = 'SWDIO' if schlib.label_text(b) == 'SWCLK' else 'SWCLK'
            bl[i] = b.replace('(label "%s"' % schlib.label_text(b), '(label "%s"' % new, 1); n += 1
    assert n == 2
    return bl
edit('mcu.kicad_sch', swd)

# 3. GI labels go (the dangling wire behind them is cleaned up below, then the pin gets a no-connect)
for fn, name in (('mcu.kicad_sch', 'GI_PWM'), ('dmd_panels.kicad_sch', 'GI_SPARE')):
    edit(fn, lambda bl, name=name: [b for b in bl if not (schlib.kind(b) == 'global_label' and schlib.label_text(b) == name)])

# 4. GI dimmer sheet and its note on the root sheet
s = open(P('sam_cpu.kicad_sch')).read()
h, bl, f = schlib.split(s)
bl = [b for b in bl if not (schlib.kind(b) == 'sheet' and '"display_gi.kicad_sch"' in b)
      and not (schlib.kind(b) == 'text' and b.split('\n')[0].strip().startswith('(text "J18 GI dimmer'))]
open(P('sam_cpu.kicad_sch'), 'w').write(schlib.join(h, bl, f))
if os.path.exists(P('display_gi.kicad_sch')):
    os.remove(P('display_gi.kicad_sch'))

# 5. ERC loop: remove what the removals left dangling, found by item uuid (ERC sheet paths are not reliable here)
FILES = [f for f in os.listdir(d) if f.endswith('.kicad_sch')]

def erc():
    out = '/tmp/c35_erc.json'
    subprocess.run([cli, 'sch', 'erc', '--format', 'json', '-o', out, P('sam_cpu.kicad_sch')], check=True, capture_output=True)
    return [x for sh in json.load(open(out))['sheets'] for x in sh['violations']]

DANGLING = ('wire_dangling', 'label_dangling', 'global_label_dangling', 'no_connect_dangling', 'unconnected_wire_endpoint')
for rnd in range(40):
    v = erc()
    kill = set()
    for x in v:
        for it in x['items']:
            if x['type'] in DANGLING or (x['type'] == 'pin_not_connected' and it['description'].startswith('Symbol #PWR')):
                kill.add(it['uuid'])
    if not kill:
        break
    for fn in FILES:
        h, bl, f = schlib.split(open(P(fn)).read())
        out = [b for b in bl if not any('"%s"' % u in b for u in kill)]
        if len(out) != len(bl):
            open(P(fn), 'w').write(schlib.join(h, out, f))

# 6. pins left open on purpose: no-connects; U15's serial input to GND
OPEN_NC = {'U4': ('66', '67', '47'), 'U31': ('1',)}
for x in erc():
    for it in x['items']:
        m = re.match(r'Symbol (\S+) Pin (\S+) ', it['description'])
        if x['type'] != 'pin_not_connected' or not m:
            continue
        ref, pin = m.groups()
        px, py = it['pos']['x'] * 100, it['pos']['y'] * 100
        fn = [f for f in FILES if '"%s"' % it['uuid'] in open(P(f)).read()][0]
        h, bl, f = schlib.split(open(P(fn)).read())
        if pin in OPEN_NC.get(ref, ()):
            bl.append(no_connect(px, py))
        elif (ref, pin) == ('U15', '10'):
            g = next(b for b in bl if schlib.kind(b) == 'symbol' and '(lib_id "power:GND")' in b)
            gx, gy, _ = schlib.at(g)
            ng = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', lambda m: str(uuid.uuid4()), g)
            ng = re.sub(r'\(at ([-\d.]+) ([-\d.]+)', lambda m: '(at %s %s' % (schlib.fmt(float(m.group(1)) - gx + px),
                        schlib.fmt(float(m.group(2)) - gy + py)), ng)
            ng = re.sub(r'#PWR\d+', '#PWR03501', ng)
            bl.append(ng)
        else:
            raise SystemExit('unexpected open pin %s %s' % (ref, pin))
        open(P(fn), 'w').write(schlib.join(h, bl, f))
left = erc()
for x in left:
    print('ERC', x['type'], [it['description'] for it in x['items']])
print('rounds', rnd, 'ERC left', len(left))

# 7. sheet notes
NOTES = [('mcu.kicad_sch', 'Coin door, status LED and GI_SPARE moved onto the switch chain.',
          'Coin door and status LED moved onto the switch chain. No USB: the Pi flashes the RP2354B over SWD on J21 '
          '(pin 18 GPIO24 = SWDIO, pin 22 GPIO25 = SWCLK, as raspberrypi-swd.cfg) and drives RUN and BOOTSEL.'),
         ('sw_dedicated_2.kicad_sch', 'The 8 DIP switches are read through the last 74HC165 of the chain (U14), whose serial input is tied low.',
          'The DIP switch block was removed (c35): U15 is now the last 74HC165 of the chain, its serial input tied low.'),
         ('sam_cpu.kicad_sch', '(text "Dedicated switches D17-D24 (J13) and DIP switches"', '(text "Dedicated switches D17-D24 (J13)"')]
for fn, a, b in NOTES:
    s = open(P(fn)).read()
    if a in s:
        open(P(fn), 'w').write(s.replace(a, b, 1))

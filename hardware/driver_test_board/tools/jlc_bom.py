"""JLCPCB BOM + CPL for the driver test board.

kpy jlc_bom.py <board.kicad_pcb> <outdir>
Parts with no LCSC code (connectors, test points, solder jumpers, holes) are left out of the BOM and CPL:
the KK-396 headers are through-hole, soldered by hand (Molex 26-60-4090/4100/4120, i.e. A-41791-0009/0010/0012).
LCSC codes checked on the JLC parts search, 2026-11-17 (stock in the README).
"""
import sys, os, csv, collections
import pcbnew
LCSC = {
    # (value, footprint name) -> LCSC
    ('47k', 'R_0805_2012Metric'): 'C17713', ('220k', 'R_0805_2012Metric'): 'C17556',
    ('100k', 'R_0805_2012Metric'): 'C149504', ('22k', 'R_0805_2012Metric'): 'C17560',
    ('4.7k', 'R_0805_2012Metric'): 'C17673', ('10k', 'R_0805_2012Metric'): 'C17414',
    ('1k', 'R_0805_2012Metric'): 'C17513', ('5.1k', 'R_0805_2012Metric'): 'C27834',
    ('33', 'R_0805_2012Metric'): 'C17634', ('27', 'R_0805_2012Metric'): 'C17594',
    ('330', 'R_0805_2012Metric'): 'C17630',
    ('100n', 'C_0805_2012Metric'): 'C49678', ('10u', 'C_0805_2012Metric'): 'C15850',
    ('4.7u', 'C_0805_2012Metric'): 'C1779', ('1u', 'C_0805_2012Metric'): 'C28323',
    ('15p', 'C_0805_2012Metric'): 'C63339',
    ('red', 'LED_0805_2012Metric'): 'C84256', ('yellow', 'LED_0805_2012Metric'): 'C2296',
    ('green', 'LED_0805_2012Metric'): 'C2297',
    ('2N7002', 'SOT-23'): 'C8545',
    ('74HC165', 'SOIC-16_3.9x9.9mm_P1.27mm'): 'C5613',
    ('74HCT595', 'SOIC-16_3.9x9.9mm_P1.27mm'): 'C282339',
    ('USBLC6-2SC6', 'SOT-23-6'): 'C7519',
    ('ADuM3160BRWZ', 'SOIC-16W_7.5x10.3mm_P1.27mm'): 'C284149',
    ('B0505S-1WR3', 'PinHeader_1x04_P2.54mm_Vertical'): 'C2992394',
    ('NCP1117-3.3', 'SOT-223-3_TabPin2'): 'C26537',
    ('RP2354B', 'QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm'): 'C39843328',
    ('3.3u', 'L_Cenker_CKCS201610'): 'C167673',
    ('12MHz', 'Crystal_SMD_3225-4Pin_3.2x2.5mm'): 'C133337',
    ('USB-C', 'USB_C_Receptacle_HRO_TYPE-C-31-M-12'): 'C165948',
    ('BOOTSEL', 'SW_SPST_TL3342'): 'C29780122', ('RESET', 'SW_SPST_TL3342'): 'C29780122',
}
# rotation / origin offsets of the JLC (EasyEDA) footprints against KiCad, from the pad comparison (jlc_rotcheck.py)
# (checked 2026-11-17 with jlc_rotcheck.py; LEDs compared by K/A name: C84256, C2296, C2297 need no offset;
#  C29780122 contacts 1-2 / 3-4 are the KiCad pads 1 / 2 rows, no offset)
JLC_ROT = {'C8545': 180, 'C5613': 270, 'C282339': 270, 'C284149': 270, 'C7519': 270, 'C26537': 180, 'C2992394': 270}
# origin of the JLC footprint minus the KiCad origin, in KiCad footprint axes at rotation 0, CPL convention (y up)
JLC_POS = {'C165948': (0.0, 1.575), 'C2992394': (0.0, -3.81)}
b = pcbnew.LoadBoard(sys.argv[1]); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
groups = collections.defaultdict(list); cpl = []; missing = collections.Counter()
for fp in b.GetFootprints():
    ref, val, name = fp.GetReference(), fp.GetValue(), fp.GetFPID().GetLibItemName().wx_str()
    code = LCSC.get((val, name))
    if not code:
        missing[(ref[:2].rstrip('0123456789'), val, name)] += 1; continue
    groups[(val, name, code)].append(ref)
    x, y = pcbnew.ToMM(fp.GetPosition().x), -pcbnew.ToMM(fp.GetPosition().y)
    rot = fp.GetOrientationDegrees()
    dx, dy = JLC_POS.get(code, (0, 0))
    if dx or dy:
        import math
        a = math.radians(rot); x += dx * math.cos(a) - dy * math.sin(a); y += dx * math.sin(a) + dy * math.cos(a)
    rot = (rot + JLC_ROT.get(code, 0)) % 360
    cpl.append((ref, f'{x:.3f}mm', f'{y:.3f}mm', 'Top' if fp.GetLayer() == pcbnew.F_Cu else 'Bottom', f'{rot:.1f}'))
key = lambda r: (r.rstrip('0123456789'), int(''.join(c for c in r if c.isdigit()) or 0))
with open(os.path.join(out, 'driver_test_board-bom-jlcpcb.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
    for (val, name, code), refs in sorted(groups.items(), key=lambda g: key(sorted(g[1], key=key)[0])):
        w.writerow([val, ','.join(sorted(refs, key=key)), name, code])
with open(os.path.join(out, 'driver_test_board-cpl-jlcpcb.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    for row in sorted(cpl, key=lambda r: key(r[0])): w.writerow(row)
print('BOM lines', len(groups), 'placed parts', len(cpl))
print('not assembled:', dict(missing))

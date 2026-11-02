"""c49 (schematic): power, reset and derating fixes from the 2026-10-31 repairability review (Vincent: "Tout appliquer").
- R217 10k 0805 (LCSC C17414) pulls MR_N (U5 TPS3808 pin 3) up to +3V3. Without it the Pi's default pull-down on GPIO22,
  through R20 1k, holds MR_N near 1.2 V (TPS3808 VIL 0.3 VDD, VIH 0.7 VDD) while the Pi boots.
- C133 / C134 (+12V, buck input): 10 uF 50 V X7R 1206 CGA1206X7R106K500NT (LCSC C6119989) instead of 25 V; the SMBJ15A
  clamp lets transients reach about 24 V. C114 (+12V / 2 audio bias): 10 uF 50 V X5R 0805 GRM21BR61H106KE43L (C440198).
- C112 (SUB_OUT): 220 nF 50 V X7R 0603 CL10B224KB8NNNC (C64705) instead of 25 V.
- R1 (TPS2117 PR1 divider): 0402 -> 0603, 100k 0603WAF1003T5E (C25803).
- FB1 (J11 5 V path): 3 A 0805 -> 6 A 1206 ferrite, Vishay ILHB1206ER121V (C124704, 120 R at 100 MHz, 20 mOhm max).
- C4 / C8 (+5V / +4V5 bulk): 100 uF 35 V solid polymer APAQ 350AVEP101M0608 (C3035877), same 6.3 mm can,
  3000 h at 105 C as a polymer (about 10x the life of the 2000 h wet part at 65 C).
- R211 (RS485 120 R termination): 0603 -> 1206, 1206W4F1200T5E (C17909), 250 mW for a shorted line.
Usage: c49_sch_power_reset_derating.py project_dir"""
import os, re, sys
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c42_sch_12v_or_pi_buck.py')).read()
exec(src[:src.index('# ---------------------------------------------------------------- power sheet')])   # c42 helpers
pw[0] = 1140
PATH_MCU = '/2aea4fdf-a573-57d0-a5af-7bd6ce737647/d360c6c3-40d3-5528-aec0-e616a30a2847'


def edit(s, ref, fp=None, val=None, desc=None):
    a, b = find_symbol(s, ref); blk = s[a:b]
    if fp:
        blk, n = re.subn(r'(\(property "Footprint" )"[^"]*"', r'\1"%s"' % fp, blk); assert n == 1, ref
    if val:
        blk, n = re.subn(r'(\(property "Value" )"[^"]*"', r'\1"%s"' % val, blk); assert n == 1, ref
    if desc:
        blk, n = re.subn(r'(\(property "Description" )"[^"]*"', r'\1"%s"' % desc, blk); assert n == 1, ref
    return s[:a] + blk + s[b:]


def sheet(name, fn):
    p = os.path.join(d, name); s = open(p).read(); s = fn(s); open(p, 'w').write(s)


def mcu(s):
    # R217 vertical above the MR_N wire end at (91.44, 76.2): pin 1 (91.44, 66.04) +3V3, pin 2 (91.44, 73.66)
    add = symbol('Device:R', 'R217', '10k', 'Resistor_SMD:R_0805_2012Metric', 91.44, 69.85, 0, 2,
                 'Resistor, MR_N pull-up (TPS3808 MR), 0805W8F1002T5E (LCSC C17414)', path=PATH_MCU,
                 rpos=(88.9, 68.58), vpos=(88.9, 71.12), just='right')
    add += PWR('power:+3V3', 91.44, 66.04) + wire((91.44, 73.66), (91.44, 76.2))
    k = s.rstrip().rindex('\n)') + 1
    return s[:k] + add + s[k:]


def power(s):
    s = edit(s, 'C133', desc='Unpolarized capacitor, 50 V X7R 1206 CGA1206X7R106K500NT (LCSC C6119989)')
    s = edit(s, 'C134', desc='Unpolarized capacitor, 50 V X7R 1206 CGA1206X7R106K500NT (LCSC C6119989)')
    s = edit(s, 'R1', fp='Resistor_SMD:R_0603_1608Metric', desc='Resistor, 0603WAF1003T5E (LCSC C25803)')
    s = edit(s, 'FB1', fp='Inductor_SMD:L_1206_3216Metric', val='6A',
             desc='Ferrite bead 120 R at 100 MHz, 6 A, 20 mOhm max, Vishay ILHB1206ER121V (LCSC C124704)')
    for r in ('C4', 'C8'):
        s = edit(s, r, desc='Polarized capacitor, 100 uF 35 V solid polymer 6.3 x 7.5 mm, APAQ 350AVEP101M0608 '
                            '(LCSC C3035877)')
    return s


def audio(s):
    s = edit(s, 'C114', desc='Unpolarized capacitor, 50 V X5R 0805 GRM21BR61H106KE43L (LCSC C440198)')
    return edit(s, 'C112', desc='Unpolarized capacitor, 50 V X7R 0603 CL10B224KB8NNNC (LCSC C64705)')


def rs485(s):
    return edit(s, 'R211', fp='Resistor_SMD:R_1206_3216Metric',
                desc='Resistor, 250 mW 1206W4F1200T5E (LCSC C17909): survives a shorted RS485 line')


sheet('mcu.kicad_sch', mcu)
sheet('power.kicad_sch', power)
sheet('audio.kicad_sch', audio)
sheet('rs485_i2s.kicad_sch', rs485)
print('ok')

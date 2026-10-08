"""Change 02 (2026-10-06): two HD DMD panels. Net renames on existing sheets, in place.
- display_gi: the J5 buffer inputs become the shared panel data lines DMD_D0-DMD_D6 (GPIO20-26)
- sw_columns: 595 latch shares the 165 load line (SW_LOAD_N); the 595 now follows the new first 595 (STB_CHAIN)
- sw_rows_1: the last 165 (U19) feeds the new 7th 165 (CHAIN6) instead of the RP2354B"""
import os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'sam_cpu')
EDITS = {
    'display_gi.kicad_sch': [('"DMD_DE"', '"DMD_D0"'), ('"DMD_ROWDATA"', '"DMD_D1"'), ('"DMD_ROWCLK"', '"DMD_D2"'),
                             ('"DMD_COLLATCH_A"', '"DMD_D3"'), ('"DMD_PIXCLK"', '"DMD_D4"'), ('"DMD_SDATA"', '"DMD_D5"'),
                             ('"DMD_COLLATCH_B"', '"DMD_D6"'),
                             ('The 100 k pull-downs keep the DMD lines low while the RP2354B boots.',
                              'The 100 k pull-downs keep the DMD lines low while the RP2354B boots. J5 shares GPIO20-26 (DMD_D0-D6) with the'
                              ' HD panel bus: J5 order DE, ROWDATA, ROWCLK, COLLATCH_A, PIXCLK, SDATA, COLLATCH_B = DMD_D0-D6.'
                              ' Only one display path runs at a time (PIO2 program chosen at boot).'),
                             ('J18 is the default GI dimmer link of ARCHITECTURE.md 10.2: +5 V, GND, GI_PWM, GI_SPARE.',
                              'J18 is the default GI dimmer link of ARCHITECTURE.md 10.2: +5 V, GND, GI_PWM, GI_SPARE (GI_SPARE is now an on/off output of U31).')],
    'sw_columns.kicad_sch': [('"STB_LATCH"', '"SW_LOAD_N"'), ('"STB_DATA"', '"STB_CHAIN"'),
                             ('One shift clock for both registers:',
                              'U20 latch shares SW_LOAD_N with the 74HC165 load (one pulse: 165 loads while low, 595 latches on the rising edge).'
                              ' U20 now follows U31 (DMD panels sheet), which carries the status LED and GI_SPARE.\\nOne shift clock for both registers:')],
    'sw_rows_1.kicad_sch': [('"SW_DATA"', '"CHAIN6"')],
    'sw_dedicated_1.kicad_sch': [('goes straight to RP2354B GPIO31.', 'goes to input D0 of the 7th 74HC165 (U30, DMD panels sheet).')],
}
for f, reps in EDITS.items():
    p = os.path.join(D, f)
    s = open(p).read()
    for a, b in reps:
        n = s.count(a)
        assert n >= 1, (f, a)
        s = s.replace(a, b)
        print(f, a, '->', b[:40], n)
    open(p, 'w').write(s)

"""c44 (schematic, after c42): the Pi header 5 V picks its source with one three-pad solder jumper JP3 instead of the two
separate jumpers JP3 / JP4 (Vincent, 2026-10-27: two jumpers can both be bridged by mistake). JP3 pin 2 (middle) is
PI_5V (J21 pins 2 / 4), pin 1 PI_5V_BUCK, pin 3 the board +5V: bridge 1-2 for the buck, 2-3 for the board, none for a
Jetson or a Pi on its own USB-C. JP4 goes.
Usage: c44_sch_pi_5v_three_way_jumper.py project_dir"""
import os, re, sys
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c42_sch_12v_or_pi_buck.py')).read()
exec(src[:src.index('# ---------------------------------------------------------------- power sheet')])   # c42 helpers
pw[0] = 1120


def drop_wire(s, x1, y1, x2, y2):
    m = re.search(r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s %s\) \(xy %s %s\)' % tuple(re.escape(fmt(v)) for v in (x1, y1, x2, y2)), s)
    assert m, (x1, y1, x2, y2)
    return s[:m.start()] + s[block(s, m.start() + 2):]


def drop_sym_at(s, lib_id, x, y):
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "%s"\)\n\t\t\(at %s %s ' % (re.escape(lib_id), re.escape(fmt(x)), re.escape(fmt(y))), s):
        return s[:m.start()] + s[block(s, m.start() + 2):]
    raise SystemExit('no %s at %s %s' % (lib_id, x, y))


p = os.path.join(d, 'power.kicad_sch'); s = open(p).read()
for ref in ('JP3', 'JP4'):
    a, b = find_symbol(s, ref); s = s[:a] + s[b:]
for w in ((363.22, 203.2, 401.32, 203.2), (401.32, 203.2, 401.32, 215.9), (401.32, 226.06, 401.32, 231.14),
          (401.32, 231.14, 396.24, 231.14), (386.08, 228.6, 381.0, 228.6), (396.24, 228.6, 396.24, 238.76),
          (396.24, 236.22, 386.08, 236.22)):
    s = drop_wire(s, *w)
for x, y in ((396.24, 231.14), (396.24, 236.22)): s = drop_item(s, 'junction', x, y)
m = re.search(r'\n\t\(global_label "PI_5V"\n\t\t\(shape passive\)\n\t\t\(at 396.24 238.76 270\)', s); assert m
s = s[:m.start()] + s[block(s, m.start() + 2):]
s = drop_sym_at(s, 'power:+5V', 381.0, 228.6)
s = drop_sym_at(s, 'power:PWR_FLAG', 386.08, 236.22)
s = embed(s, 'Jumper', 'SolderJumper_3_Open')

X, Y = 391.16, 220.98                        # pin 1 (386.08, Y), pin 3 (396.24, Y), pin 2 (X, 224.79)
add = wire((363.22, 203.2), (388.62, 203.2))  # PI_5V_BUCK now ends at C136
add += symbol('Jumper:SolderJumper_3_Open', 'JP3', 'PI 5V', 'Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm', X, Y, 0, 3,
              'Pi header 5 V: bridge 1-2 for the buck, 2-3 for the board +5 V, none for a Jetson (open by default)',
              rpos=(X, Y - 5.08), vpos=(X, Y - 2.54), just=None)
add += wire((386.08, Y), (381.0, Y)) + label('PI_5V_BUCK', 381.0, Y, 180, 'right')
add += wire((396.24, Y), (401.32, Y)) + PWR('power:+5V', 401.32, Y)
add += wire((X, 224.79), (X, 238.76)) + glabel('PI_5V', X, 238.76, 270)
add += wire((X, 233.68), (386.08, 233.68)) + junction(X, 233.68) + PWR('power:PWR_FLAG', 386.08, 233.68, 180)
k = s.rstrip().rindex('\n)') + 1
s = s[:k] + add + s[k:]
s = replace_once(s, 'Pi 5.1 V buck (3 A) and Pi header 5 V jumpers JP3 / JP4', 'Pi 5.1 V buck (3 A) and Pi header 5 V jumper JP3')
s = replace_once(s, 'JP3 / JP4 (open by default) feed J21 pins 2 / 4 (PI_5V):\\nJP4: from the buck (Pi 4 / Pi 5, 5.18 V 3 A)\\n'
                 'JP3: from the board +5 V\\nboth open: Jetson, or a Pi on its own USB-C. Never bridge both.',
                 'JP3 (open by default) feeds J21 pins 2 / 4 (PI_5V) from one source:\\n1-2: the buck (Pi 4 / Pi 5, 5.18 V 3 A)\\n'
                 '2-3: the board +5 V\\nopen: Jetson, or a Pi on its own USB-C.')
open(p, 'w').write(s)
print('ok')

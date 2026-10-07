"""Change 01 (2026-10-07): turn the IO_16_8_1 root sheet into the SAM_IO root sheet.
Removes the IN16 and OUT8 sheets with their labels, renames the GPIO3-18 labels to the
SAM bus global labels (pin map of io-boards src/IODevices/SamBus/SamBusPins.h), puts
no-connect flags on the eight freed output GPIOs, adds the 'SAM bus' sheet and the
symbol instance data KiCad 10 expects. Usage: c01_root_sheet.py <sam_io.kicad_sch>"""
import re, sys, uuid
import sx

path = sys.argv[1]
t = open(path).read()
ROOT = re.search(r'\(uuid "([^"]+)"\)', t).group(1)
U = lambda: str(uuid.uuid4())

BUS = {**{f'In_{i + 1}': (f'BUS_D{i}', 'bidirectional') for i in range(8)},
       **{f'In_{i + 9}': (f'BUS_A{i}', 'output') for i in range(4)},
       'In_13': ('BUS_IOSTB', 'output'), 'In_14': ('BUS_DIR', 'output'),
       'In_15': ('BUS_OE_N', 'output'), 'In_16': ('NBRESET_DRV', 'output')}
GPIO_X, LABEL_X = 220.98, 227.33

def glabel(name, shape, x, y):
    return f'''(global_label "{name}"
		(shape {shape})
		(at {x} {y} 0)
		(fields_autoplaced yes)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify left)
		)
		(uuid "{U()}")
		(property "Intersheetrefs" "${{INTERSHEET_REFS}}"
			(at {x} {y} 0)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left)
				(hide yes)
			)
		)
	)'''

def noconnect(x, y):
    return f'(no_connect\n\t\t(at {x} {y})\n\t\t(uuid "{U()}")\n\t)'

edits = []          # (start, end, replacement)
dead_pts = set()
nc = []
for h, a, b in sx.items(t):
    s = t[a:b]
    if h == 'sheet' and sx.prop(s, 'Sheetname') in ('IN16', 'OUT8'):
        edits.append((a, b, None))
    elif h == 'label':
        n, (x, y, r) = sx.name(s), sx.at(s)
        if not re.fullmatch(r'(In|Out)_\d+', n):
            continue
        if x != LABEL_X:                       # the copies beside the removed sheet symbols
            edits.append((a, b, None)); dead_pts.add((x, y))
        elif n in BUS:
            edits.append((a, b, glabel(*BUS[n], x, y)))
        else:                                  # Out_1..Out_8: GPIO left unconnected
            edits.append((a, b, None)); dead_pts.add((x, y)); nc.append((GPIO_X, y))
for h, a, b in sx.items(t):
    if h == 'wire' and dead_pts & set(sx.pts(t[a:b])):
        edits.append((a, b, None))
assert len(nc) == 8, nc

# instance data for every root symbol (the KiCad 6 file kept it in symbol_instances, which the upgrade drops)
for h, a, b in sx.items(t):
    s = t[a:b]
    if h != 'symbol' or '(instances' in s:
        continue
    ref = sx.prop(s, 'Reference'); unit = re.search(r'\(unit (\d+)\)', s).group(1)
    inst = (f'\t(instances\n\t\t\t(project "sam_io"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n'
            f'\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
    edits.append((a, b, s[:s.rstrip().rfind(')')].rstrip() + '\n\t' + inst))

SHEET = f'''(sheet
		(at 66.04 203.2)
		(size 40.64 20.32)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(stroke
			(width 0.1524)
			(type solid)
		)
		(fill
			(color 0 0 0 0)
		)
		(uuid "{U()}")
		(property "Sheetname" "SAM bus"
			(at 66.04 202.4884 0)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left bottom)
			)
		)
		(property "Sheetfile" "sam_bus.kicad_sch"
			(at 66.04 224.1046 0)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left top)
			)
		)
		(instances
			(project "sam_io"
				(path "/{ROOT}"
					(page "2")
				)
			)
		)
	)'''
NOTE = f'''(text "SAM_IO, derived from PPUC IO_16_8_1 v1.1.1 (TAPR OHL 1.0, see ../README.md):\\n- IN16 (16 inputs, J6-J8) and OUT8 (8 high-power outputs, J9-J11, F2, C56) removed.\\n- GPIO3-18 drive the SAM bus through level shifters on sheet 'SAM bus' (J9 to the SAM IO board J1).\\n- GPIO19-24, 26, 27 (former Out_1-Out_8) unused.\\n- GPIO25 LED, GPIO28 board id and GPIO29 special output unchanged."
		(exclude_from_sim no)
		(at 297.18 195.58 0)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify left bottom)
		)
		(uuid "{U()}")
	)'''

edits.sort(reverse=True)
for a, b, rep in edits:
    if rep is None:
        # drop the item and its leading indentation
        while a > 0 and t[a - 1] in '\t ':
            a -= 1
        if t[a - 1] == '\n':
            a -= 1
        t = t[:a] + t[b:]
    else:
        t = t[:a] + rep + t[b:]

extra = '\n\t'.join([noconnect(*p) for p in nc] + [SHEET, NOTE,
                     '(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)'])
end = t.rstrip().rfind(')')
t = t[:end].rstrip() + '\n\t' + extra + '\n)\n'
t = re.sub(r'\(title_block.*?\n\t\)', '''(title_block
		(title "SAM_IO")
		(date "2026-10-07")
		(rev "0.1")
	)''', t, count=1, flags=re.S)
open(path, 'w').write(t)
print('removed', sum(1 for e in edits if e[2] is None), 'items;', len(nc), 'no-connects')

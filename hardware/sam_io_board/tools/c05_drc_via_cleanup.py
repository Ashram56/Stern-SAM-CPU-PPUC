"""Change 05 (2026-10-07): after the new parts are on the board, remove the vias DRC reports as
dangling (left over from the removed input / output stages) and the stitching vias that the new
parts now sit on. Reads a kicad-cli JSON DRC report. Usage: c05_drc_via_cleanup.py <drc.json> <board>"""
import json, re, sys
import sx

NEW = {'J9', 'RN1', 'RN2', 'RN3', 'U7', 'U8', 'R27', 'R28', 'R29', 'R30', 'C30', 'C31', 'C32', 'C33',
       'Q1', 'TP3', 'TP4', 'TP5', 'TP6'}
rep, boardfile = json.load(open(sys.argv[1])), sys.argv[2]
kill = set()
for v in rep['violations']:
    vias = [i for i in v['items'] if i['description'].startswith('Via ')]
    if not vias:
        continue
    others = [i for i in v['items'] if not i['description'].startswith('Via ')]
    if v['type'] == 'via_dangling' or any(re.search(r' of (\w+)', i['description']) and
                                          re.search(r' of (\w+)', i['description']).group(1) in NEW for i in others):
        for i in vias:
            kill.add((round(i['pos']['x'], 3), round(i['pos']['y'], 3)))
t = open(boardfile).read()
drop = []
for h, a, b in sx.items(t):
    if h == 'via':
        x, y, _ = sx.at(t[a:b])
        if (round(x, 3), round(y, 3)) in kill:
            drop.append((a, b))
for a, b in reversed(drop):
    while t[a - 1] in '\t ':
        a -= 1
    t = t[:a - 1] + t[b:] if t[a - 1] == '\n' else t[:a] + t[b:]
open(boardfile, 'w').write(t)
print('vias removed:', len(drop), 'of', len(kill), 'reported')

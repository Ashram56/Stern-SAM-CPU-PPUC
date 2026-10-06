"""Build the KiCad project from design2.py: python3 build2.py <outdir>"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
OUT = sys.argv[1]
import design2
from kigen import uid, effects, write
from sexp import Sym
from sch import POWER

D, PAGES = design2.D, design2.PAGES
os.makedirs(OUT, exist_ok=True)

# nets used on more than one page get global labels
use = collections.defaultdict(set)
for p in PAGES:
    for part in p.parts:
        for n in part.nets.values():
            if n != 'NC' and n not in POWER: use[n].add(p.name)
glob = {n for n, s in use.items() if len(s) > 1}
# label shapes from the pin types on each page
OUTS = {'output', 'tri_state', 'open_collector', 'open_emitter', 'power_out'}
shapes = {}
for p in PAGES:
    types = collections.defaultdict(set)
    for part in p.parts:
        for q in part.unit_pins():
            n = part.nets.get(q['number'])
            if n in glob: types[n].add(q['type'])
    for n, ts in types.items():
        if ts & OUTS and 'input' not in ts and 'bidirectional' not in ts: s = 'output'
        elif ts <= {'input'} or ts <= {'input', 'passive'} and 'input' in ts: s = 'input'
        elif 'bidirectional' in ts: s = 'bidirectional'
        else: s = 'passive'
        shapes[(p.name, n)] = s

root_uuid = D.root_uuid
problems = 0
sheets = []
ONLY = os.environ.get('ONLY')
def build_page(i):
    p = PAGES[i]
    p.pwr_base = (i + 1) * 1000
    path = f'/{root_uuid}/{uid("sheet", p.filename)}'
    p.build(D, glob, path, shapes)
    doc = p.emit(D, path, shapes)
    write(os.path.join(OUT, p.filename), doc)
    return i, p.failed
todo = [i for i, p in enumerate(PAGES) if not ONLY or p.name in ONLY.split(',')]
import multiprocessing
with multiprocessing.get_context('fork').Pool(min(len(todo), os.cpu_count() or 4)) as pool:
    for i, failed in pool.imap_unordered(build_page, todo):
        if failed:
            problems += len(failed)
            print(f'{PAGES[i].name}: {len(failed)} connections fell back to labels:', failed[:12])
sheets = [(p, uid('sheet', p.filename), i + 2) for i, p in enumerate(PAGES)]

# root: sheet symbols only (signals cross pages through global labels)
items = []
cols, w, h = 3, 88.9, 25.4
for k, (p, suid, page) in enumerate(sheets):
    sx = 25.4 + (k % cols) * 127.0
    sy = 63.5 + (k // cols) * 45.72
    items.append([Sym('sheet'), [Sym('at'), sx, sy], [Sym('size'), w, h], [Sym('exclude_from_sim'), Sym('no')],
                  [Sym('in_bom'), Sym('yes')], [Sym('on_board'), Sym('yes')], [Sym('dnp'), Sym('no')],
                  [Sym('fields_autoplaced'), Sym('yes')],
                  [Sym('stroke'), [Sym('width'), 0.1524], [Sym('type'), Sym('solid')]],
                  [Sym('fill'), [Sym('color'), 0, 0, 0, 0.0]], [Sym('uuid'), suid],
                  [Sym('property'), 'Sheetname', p.name, [Sym('at'), sx, round(sy - 0.7116, 4), 0], effects(size=2.0, justify='left bottom')],
                  [Sym('property'), 'Sheetfile', p.filename, [Sym('at'), sx, round(sy + h + 0.5884, 4), 0], effects(justify='left top')],
                  [Sym('instances'), [Sym('project'), D.project, [Sym('path'), f'/{root_uuid}', [Sym('page'), str(page)]]]]])
    items.append([Sym('text'), p.title, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), sx + 2.54, sy + 5.08, 0],
                  effects(size=1.6, justify='left top'), [Sym('uuid'), uid('rootdesc', p.filename)]])
notes = design2.ROOT_NOTES
items.append([Sym('text'), notes, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), 25.4, 15.24, 0],
              effects(size=2.0, justify='left top'), [Sym('uuid'), uid('rootnote')]])
root = [Sym('kicad_sch'), [Sym('version'), 20250114], [Sym('generator'), 'eeschema'], [Sym('generator_version'), '9.0'],
        [Sym('uuid'), root_uuid], [Sym('paper'), 'A3'],
        [Sym('title_block'), [Sym('title'), D.title], [Sym('date'), D.date], [Sym('rev'), D.rev], [Sym('company'), D.company]],
        [Sym('lib_symbols')]] + items + [
        [Sym('sheet_instances'), [Sym('path'), '/', [Sym('page'), '1']]], [Sym('embedded_fonts'), Sym('no')]]
write(os.path.join(OUT, D.project + '.kicad_sch'), root)

pro = {"meta": {"filename": D.project + ".kicad_pro", "version": 3},
       "schematic": {"drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0,
                                 "intersheets_ref_show": True, "intersheets_ref_own_page": False,
                                 "intersheets_ref_short": False, "intersheets_ref_prefix": "[",
                                 "intersheets_ref_suffix": "]"},
                     "legacy_lib_dir": "", "legacy_lib_list": []},
       "sheets": [[root_uuid, "Root"]] + [[suid, p.name] for p, suid, _ in sheets],
       "text_variables": {}}
json.dump(pro, open(os.path.join(OUT, D.project + '.kicad_pro'), 'w'), indent=2)
print('global nets:', len(glob), ' label fallbacks:', problems)

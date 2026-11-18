"""Build the KiCad 9 project: python3 build_dtb.py [design_module] <outdir> (default design_dtb)"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
import importlib
MOD = sys.argv[1] if len(sys.argv) > 2 else 'design_dtb'
OUT = sys.argv[-1]
dd = importlib.import_module(MOD)
from kigen import uid, effects, write, POWER_NETS
from sexp import Sym
D = dd.D
os.makedirs(OUT, exist_ok=True)
use = collections.defaultdict(set)
for s in dd.SHEETS:
    for b in s.blocks:
        for p in b.parts:
            for n in p.nets.values():
                if n != 'NC' and n not in POWER_NETS: use[n].add(s.name)
D.global_nets = {n for n, ss in use.items() if len(ss) > 1}
root = D.root_uuid
items = []
for k, s in enumerate(dd.SHEETS):
    path = f'/{root}/{uid("sheet", s.filename)}'
    doc = D.write_sheet(s, None, path, k + 2)
    write(os.path.join(OUT, s.filename), doc)
    sx, sy, w, h = 25.4 + (k % 3) * 127.0, 63.5 + (k // 3) * 45.72, 88.9, 25.4
    items.append([Sym('sheet'), [Sym('at'), sx, sy], [Sym('size'), w, h], [Sym('exclude_from_sim'), Sym('no')],
                  [Sym('in_bom'), Sym('yes')], [Sym('on_board'), Sym('yes')], [Sym('dnp'), Sym('no')],
                  [Sym('fields_autoplaced'), Sym('yes')],
                  [Sym('stroke'), [Sym('width'), 0.1524], [Sym('type'), Sym('solid')]],
                  [Sym('fill'), [Sym('color'), 0, 0, 0, 0.0]], [Sym('uuid'), uid('sheet', s.filename)],
                  [Sym('property'), 'Sheetname', s.name, [Sym('at'), sx, round(sy - 0.7116, 4), 0], effects(size=2.0, justify='left bottom')],
                  [Sym('property'), 'Sheetfile', s.filename, [Sym('at'), sx, round(sy + h + 0.5884, 4), 0], effects(justify='left top')],
                  [Sym('instances'), [Sym('project'), D.project, [Sym('path'), f'/{root}', [Sym('page'), str(k + 2)]]]]])
    items.append([Sym('text'), s.title, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), sx + 2.54, sy + 5.08, 0],
                  effects(size=1.6, justify='left top'), [Sym('uuid'), uid('rootdesc', s.filename)]])
items.append([Sym('text'), dd.ROOT_NOTES, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), 25.4, 15.24, 0],
              effects(size=2.0, justify='left top'), [Sym('uuid'), uid('rootnote')]])
doc = [Sym('kicad_sch'), [Sym('version'), 20250114], [Sym('generator'), 'eeschema'], [Sym('generator_version'), '9.0'],
       [Sym('uuid'), root], [Sym('paper'), 'A3'],
       [Sym('title_block'), [Sym('title'), D.title], [Sym('date'), D.date], [Sym('rev'), D.rev], [Sym('company'), D.company]],
       [Sym('lib_symbols')]] + items + [[Sym('sheet_instances'), [Sym('path'), '/', [Sym('page'), '1']]], [Sym('embedded_fonts'), Sym('no')]]
write(os.path.join(OUT, D.project + '.kicad_sch'), doc)
pro = {"meta": {"filename": D.project + ".kicad_pro", "version": 3},
       "sheets": [[root, "Root"]] + [[uid('sheet', s.filename), s.name] for s in dd.SHEETS], "text_variables": {}}
json.dump(pro, open(os.path.join(OUT, D.project + '.kicad_pro'), 'w'), indent=2)
open(os.path.join(OUT, 'sym-lib-table'), 'w').write('(sym_lib_table\n  (version 7)\n  (lib (name "dtb")(type "KiCad")(uri "${KIPRJMOD}/dtb.kicad_sym")(options "")(descr "Project symbols"))\n)\n')
import shutil; shutil.copy(os.path.join(os.path.dirname(__file__), '..', 'dtb.kicad_sym'), OUT)
print('sheets', len(dd.SHEETS), 'global nets', len(D.global_nets))

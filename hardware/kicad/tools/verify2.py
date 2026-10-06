"""Compare the netlist KiCad exports with the nets design2.py intended.
python3 verify2.py <netlist.net>"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
netfile = sys.argv[1]
import design2
from sch import POWER
from sexp import parse, find, find1

use = collections.defaultdict(set)
for p in design2.PAGES:
    for part in p.parts:
        for n in part.nets.values(): use[n].add(p.name)
glob = {n for n, s in use.items() if len(s) > 1} | set(POWER)
intended = {}
for p in design2.PAGES:
    for part in p.parts:
        if part.ref.startswith('#'): continue
        for q in part.unit_pins():
            n = part.nets.get(q['number'])
            if n is None or n == 'NC': continue
            intended[(part.ref, q['number'])] = n if n in glob else (p.name, n)
t = parse(open(netfile).read())[0]
actual, names = {}, {}
for net in find(find1(t, 'nets'), 'net'):
    code = find1(net, 'code')[1]; names[code] = find1(net, 'name')[1]
    for node in find(net, 'node'):
        actual[(find1(node, 'ref')[1], find1(node, 'pin')[1])] = code
errors = 0
k2c, c2k = collections.defaultdict(set), collections.defaultdict(set)
for pin, key in intended.items():
    c = actual.get(pin)
    if c is None:
        print('MISSING in netlist:', pin, key); errors += 1; continue
    k2c[key].add(c); c2k[c].add(key)
for k, cs in k2c.items():
    if len(cs) > 1: print('SPLIT net', k, [names[c] for c in cs]); errors += 1
for c, ks in c2k.items():
    if len(ks) > 1: print('MERGED nets', names[c], ks); errors += 1
for pin, c in actual.items():
    if pin not in intended and not names[c].startswith('unconnected-'):
        print('UNEXPECTED connection', pin, names[c]); errors += 1
# power rails must carry their own names
for k, cs in k2c.items():
    if k in POWER:
        nm = names[next(iter(cs))].lstrip('/')
        if nm != k: print('POWER net named', nm, 'expected', k); errors += 1
print(f'{len(intended)} pins checked, {len(k2c)} nets, {errors} problems')
sys.exit(1 if errors else 0)

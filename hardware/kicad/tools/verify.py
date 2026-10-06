"""Compare the netlist KiCad exports with the nets the generator intended.
python3 verify.py <netlist.net>"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
netfile = sys.argv[1]
sys.argv = [sys.argv[0], '/tmp/unused']
import design
from kigen import POWER_NETS
from sexp import parse, find, find1

D = design.D
use = collections.defaultdict(set)
for s in D.sheets:
    for b in s.blocks:
        for _, net, _ in b.labels: use[net].add(s.name)
glob = {n for n, ss in use.items() if len(ss) > 1} | set(POWER_NETS)
intended = {}
for s in D.sheets:
    for b in s.blocks:
        for p in b.parts:
            for q in p.unit_pins():
                n = p.nets.get(q['number'])
                if n is None or n == 'NC': continue
                if p.ref.startswith('#'): continue
                intended[(p.ref, q['number'])] = n if n in glob else (s.name, n)

t = parse(open(netfile).read())[0]
actual = {}
names = {}
for net in find(find1(t, 'nets'), 'net'):
    code = find1(net, 'code')[1]; names[code] = find1(net, 'name')[1]
    for node in find(net, 'node'):
        actual[(find1(node, 'ref')[1], find1(node, 'pin')[1])] = code
errors = 0
k2c = collections.defaultdict(set); c2k = collections.defaultdict(set)
for pin, key in intended.items():
    c = actual.get(pin)
    if c is None:
        print('MISSING in netlist:', pin, key); errors += 1; continue
    k2c[key].add(c); c2k[c].add(key)
for k, cs in k2c.items():
    if len(cs) > 1: print('SPLIT net', k, [names[c] for c in cs]); errors += 1
for c, ks in c2k.items():
    if len(ks) > 1: print('MERGED nets', names[c], ks); errors += 1
# pins connected in KiCad that we meant to leave unconnected
for pin, c in actual.items():
    if pin not in intended and not names[c].startswith('unconnected-'):
        print('UNEXPECTED connection', pin, names[c]); errors += 1
print(f'{len(intended)} pins checked, {len(k2c)} nets, {errors} problems')
sys.exit(1 if errors else 0)

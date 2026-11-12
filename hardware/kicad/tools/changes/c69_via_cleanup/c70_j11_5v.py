from fx import *
import math,sys
n='/Power/J11_5V'
old=[t['uuid'] for t in b.g['tracks'] if t['net']==n and not (abs(t['x1']-99.5)<1e-3 and abs(t['x2']-99.5)<1e-3 and t['layer']=='F')]
oldv=[v['uuid'] for v in b.g['vias'] if v['net']==n and not (abs(v['x']-99.5)<1e-3)]
print(len(old),len(oldv))
dl=old+oldv+[full(x) for x in ('857ba024','8bfb07f4','402fdb04')]
b.commit(delete=dl)
a=P('+4V5',0.25).at(98.3639,107.336,'B').to(99.5029,108.475).to(100.6,108.475).to(101.739,107.336).to(111.369,107.336)
c=P('Net-(J11-Pin_1)',0.8).at(96.5575,108.165,'B').to(97.9,108.165).to(98.935,109.2).to(100.841,109.2).to(101.281,109.64)
j=P(n,0.8,0.8,0.4).at(99.5,105.444,'B').to(99.5,107.33).to(99.92,107.75); j.vias.append((99.92,107.75))
k=P(n,0.8).at(99.92,107.75,'F').to(99.92,109.135)
bad=[]
for p in (a,c,j,k): bad+=b.check(p)
if not bad and len(sys.argv)>1: b.commit(a,c,j,k); print('committed')

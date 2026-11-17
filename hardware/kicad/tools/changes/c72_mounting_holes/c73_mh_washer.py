# c73: keep copper 5.5 mm away from the centre of the M4 hole MH5 on both sides (9 mm washer + margin).
# Replaces the c72 detours of the four speaker tracks with wider ones.
import sys,math; sys.path.insert(0,'/tmp/claude-0/hr')
import hr
b=hr.Board(); b.redump()
P=lambda n: hr.Path(n,w=1.0,vd=0.8,drill=0.4)
old={'/Audio/SPK_L_N':[(118.96,41.18),(118.96,31.5),(169.3,31.5),(169.3,33.3)],
 '/Audio/SPK_R_P':[(122.92,33.3),(133.4,33.3),(133.9,33.8),(133.9,39.2),(136.9,42.2),(141.5,42.2),(144.5,39.2),(144.5,33.8),(145.0,33.3),(167.6,33.3)],
 '/Audio/SPK_L_P':[(115.0,35.5),(133.4,35.5),(133.9,36.0),(133.9,39.2),(136.9,42.2),(141.5,42.2),(144.5,39.2),(144.5,36.0),(145.0,35.5),(150.0,35.5)],
 '/Audio/SPK_R_N':[(126.88,36.8),(132.1,36.8),(132.6,37.3),(132.6,39.74),(136.36,43.5),(142.04,43.5),(145.8,39.74),(145.8,37.3),(146.3,36.8),(170.6,36.8)]}
dele=[]
for n,pts in old.items():
    want={frozenset((a,c)) for a,c in zip(pts,pts[1:])}
    for t in b.g['tracks']:
        if t['net']==n and frozenset(((round(t['x1'],3),round(t['y1'],3)),(round(t['x2'],3),round(t['y2'],3)))) in want: dele.append(t['uuid'])
assert len(dele)==3+9+9+9,len(dele)
def path(n,l,pts):
    p=P(n).at(*pts[0],l)
    for q in pts[1:]: p.to(*q)
    return p
LN=path('/Audio/SPK_L_N','F',[(118.96,41.18),(118.96,31.5),(133.0,31.5),(133.6,30.9),(144.8,30.9),(145.4,31.5),(169.3,31.5),(169.3,33.3)])
RP=path('/Audio/SPK_R_P','F',[(122.92,33.3),(132.6,33.3),(133.1,33.8),(133.1,39.44),(136.76,43.1),(141.64,43.1),(145.3,39.44),(145.3,33.8),(145.8,33.3),(167.6,33.3)])
LP=path('/Audio/SPK_L_P','B',[(115.0,35.5),(132.6,35.5),(133.1,36.0),(133.1,39.44),(136.76,43.1),(141.64,43.1),(145.3,39.44),(145.3,36.0),(145.8,35.5),(150.0,35.5)])
RN=path('/Audio/SPK_R_N','B',[(126.88,36.8),(131.3,36.8),(131.8,37.3),(131.8,39.98),(136.22,44.4),(142.18,44.4),(146.6,39.98),(146.6,37.3),(147.1,36.8),(170.6,36.8)])
b.g['tracks']=[x for x in b.g['tracks'] if x['uuid'] not in dele]
import json; json.dump(b.g,open(hr.GEO,'w')); b.load()
paths=(LN,RP,LP,RN); bad=[]
for p in paths: bad+=b.check(p)
from shapely.geometry import Point
for name,(cx,cy) in {'MH5':(139.2,36.98),'MH7':(38.25,146.84),'MH4':(127.14,252.86)}.items():
    c=Point(cx,cy); best={}
    for L in 'FB':
        for g,n,k,o in b.items[L]:
            if k=='pad' and o['ref']==name: continue
            d=c.distance(g)
            if d<6.0: best.setdefault((L,n,k),[]).append(round(d,2))
    for p in paths:
        for kind,l,shape,info in p.shapes():
            d=c.distance(shape)
            if d<6.0: best.setdefault((l,p.net,'new'),[]).append(round(d,2))
    print(name,{k:min(v) for k,v in best.items()})
b.view('mh5w.png',(128,29,152,47),size=15,hl=tuple(old),paths=paths)
if not bad and 'go' in sys.argv: b.commit(*paths,delete=dele); hr.drc('c73')
else: b.redump()

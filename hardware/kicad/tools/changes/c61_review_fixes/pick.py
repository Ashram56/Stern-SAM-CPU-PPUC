import json,math,sys
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
I=json.load(open(sys.argv[1])); D=json.load(open(sys.argv[2]))
other={'F':[], 'B':[]}; smd={'F':[],'B':[]}
for t in D['tracks']:
    if t['net']!='GND': other[t['layer']].append(LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['w']/2))
for v in D['vias']:
    g=Point(v['x'],v['y']).buffer(v['d']/2)
    for L in 'FB':
        if v['net']!='GND': other[L].append(g)
allv=[Point(v['x'],v['y']) for v in D['vias']]
for p in D['pads']:
    for L,pl in p['polys'].items():
        g=Polygon(pl)
        if p['net']!='GND': other[L].append(g)
        smd[L].append(g)
    if p['drill'][0]>0: allv.append(Point(p['x'],p['y']))
T={L:STRtree(other[L]) for L in 'FB'}; S={L:STRtree(smd[L]) for L in 'FB'}; V=STRtree(allv)
def ok(pt,L):
    o='B' if L=='F' else 'F'
    for LL in (L,o):
        for j in T[LL].query(pt.buffer(0.6)):
            if other[LL][j].distance(pt)<0.55: return False
        for j in S[LL].query(pt.buffer(0.6)):
            if smd[LL][j].distance(pt)<0.45: return False
    for j in V.query(pt.buffer(1.0)):
        if allv[j].distance(pt)<0.9: return False
    return True
prefer={(131.8,135.5):'buck_in',(131.1,137.6):'buck_in2'}
new=[]
for isl in I:
    if isl['anch']>=2 or isl['area']<4: continue
    P=Polygon(isl['outline'],isl['holes']).buffer(-0.4)
    if P.is_empty: continue
    want=min(4,max(2,int(isl['area']/40)+1))-isl['anch']
    minx,miny,maxx,maxy=P.bounds; cands=[]
    x=minx
    while x<=maxx:
        y=miny
        while y<=maxy:
            pt=Point(x,y)
            if P.contains(pt) and ok(pt,isl['layer']): cands.append(pt)
            y+=0.25
        x+=0.25
    chosen=[]
    anchors=[p for p in allv if Polygon(isl['outline']).contains(p)]
    for _ in range(want):
        if not cands: break
        ref=anchors+chosen
        c=max(cands,key=lambda p:min([p.distance(r) for r in ref] or [1e9]) if ref else -p.distance(P.centroid))
        chosen.append(c); cands=[p for p in cands if p.distance(c)>=1.5]
    for c in chosen:
        new.append((round(c.x,3),round(c.y,3),isl['layer'],round(isl['area'],1)))
        allv.append(c); V=STRtree(allv)
json.dump(new,open(sys.argv[3],'w')); print(len(new),"vias")
import collections; print(collections.Counter(n[2] for n in new))

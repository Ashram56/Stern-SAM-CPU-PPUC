import json,math,collections
from shapely.geometry import Point,Polygon
g=json.load(open('/tmp/claude-0/hr/geo.json'))
R=lambda v: round(v,3)
adj=collections.defaultdict(list)
for t in g['tracks']:
    a=(R(t['x1']),R(t['y1'])); c=(R(t['x2']),R(t['y2']))
    if math.dist(a,c)<1e-4: continue
    adj[(t['net'],t['layer'],a)].append((c,t)); adj[(t['net'],t['layer'],c)].append((a,t))
vias=collections.defaultdict(list)
for v in g['vias']: vias[v['net']].append(v)
pads=collections.defaultdict(list)
for p in g['pads']:
    for l,pts in p['polys'].items():
        if len(pts)>=3: pads[(p['net'],l)].append((Polygon(pts),p))
def term(net,layer,pt):
    for v in vias[net]:
        if math.dist(pt,(v['x'],v['y']))<v['d']/2: return 'via'
    for poly,p in pads[(net,layer)]:
        if poly.distance(Point(pt))<1e-3: return 'pad %s.%s'%(p['ref'],p['pad'])
    return None
def octile(a,c):
    dx=abs(a[0]-c[0]);dy=abs(a[1]-c[1]); return max(dx,dy)+(math.sqrt(2)-1)*min(dx,dy)
seen=set(); chains=[]
for (net,layer,pt),lst in adj.items():
    if len(lst)==2 and not term(net,layer,pt): continue   # interior
    for (nx,t) in lst:
        if t['uuid'] in seen: continue
        path=[pt,nx]; seen.add(t['uuid']); cur=nx; ts=[t]
        while len(adj[(net,layer,cur)])==2 and not term(net,layer,cur):
            (n1,t1),(n2,t2)=adj[(net,layer,cur)]
            n,tt=(n1,t1) if t1['uuid'] not in seen else (n2,t2)
            if tt['uuid'] in seen: break
            seen.add(tt['uuid']); path.append(n); ts.append(tt); cur=n
        chains.append((net,layer,path,ts))
out=[]
for net,layer,path,ts in chains:
    L=sum(math.dist(path[i],path[i+1]) for i in range(len(path)-1)); o=octile(path[0],path[-1])
    turns=0
    for i in range(1,len(path)-1):
        a1=math.atan2(path[i][1]-path[i-1][1],path[i][0]-path[i-1][0]); a2=math.atan2(path[i+1][1]-path[i][1],path[i+1][0]-path[i][0])
        d=abs((a2-a1+math.pi)%(2*math.pi)-math.pi)
        if d>0.2: turns+=1
    e0=term(net,layer,path[0]); e1=term(net,layer,path[-1])
    kind=None
    if L-o>1.5 and L/max(o,0.01)>1.3: kind='detour'
    elif turns>=4 and L<8 and L-o>0.3: kind='zigzag'
    elif e0=='via' and e1=='via' and L<2.5: kind='shorthop'
    elif (e0 is None and len(adj[(net,layer,path[0])])==1) or (e1 is None and len(adj[(net,layer,path[-1])])==1): kind='stub'
    if kind: out.append((kind,net,layer,round(L,1),round(o,1),turns,path[0],path[-1],e0,e1,[t['uuid'] for t in ts]))
import sys
c=collections.Counter(o[0] for o in out); print(c)
for o in sorted(out,key=lambda o:(o[0],-(o[3]-o[4]))): print(o[:10])
json.dump(out,open('/tmp/claude-0/hr/det2.json','w'))

import json,heapq,sys
from shapely.geometry import LineString,Point,Polygon
from shapely.strtree import STRtree
D=json.load(open("dump.json"))
def objs(net):
    O=[]
    for t in D['tracks']:
        if t['net']==net: O.append(dict(k='T',L={t['layer']},g=LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['w']/2),w=t['w'],d=t))
    for v in D['vias']:
        if v['net']==net: O.append(dict(k='V',L={'F','B','I1','I2'},g=Point(v['x'],v['y']).buffer(v['d']/2),w=v['drill'],d=v))
    for p in D['pads']:
        if p['net']==net:
            for l,poly in p['polys'].items():
                L={l} if p['drill'][0]==0 else {'F','B','I1','I2'}
                O.append(dict(k='P',L=L,g=Polygon(poly),w=99,d=p,name=f"{p['ref']}.{p['pad']}"))
    return O
def widest(net,src,dst):
    O=objs(net);n=len(O)
    adj=[[] for _ in O]
    tree=STRtree([o['g'] for o in O])
    for i,o in enumerate(O):
        for j in tree.query(o['g']):
            if j!=i and (o['L']&O[j]['L']) and o['g'].intersects(O[j]['g']): adj[i].append(j)
    S=[i for i,o in enumerate(O) if o.get('name')==src]; T=set(i for i,o in enumerate(O) if o.get('name')==dst)
    if not S or not T: return None
    best=[-1]*n; prev=[None]*n; h=[]
    for s in S: best[s]=99; heapq.heappush(h,(-99,s))
    while h:
        b,i=heapq.heappop(h); b=-b
        if b<best[i]: continue
        for j in adj[i]:
            nb=min(b,O[j]['w'] if O[j]['k']=='T' else 99)
            if nb>best[j]: best[j]=nb; prev[j]=i; heapq.heappush(h,(-nb,j))
    t=max(T,key=lambda x:best[x])
    if best[t]<0: return (net,src,dst,"NOT CONNECTED (tracks only)")
    path=[];i=t
    while i is not None: path.append(i); i=prev[i]
    vias=[O[i]['d'] for i in path if O[i]['k']=='V']
    lay=[]; 
    for i in path:
        if O[i]['k']=='T' and (not lay or lay[-1]!=O[i]['d']['layer']): lay.append(O[i]['d']['layer'])
    nw=[(O[i]['w'],O[i]['d']['layer'],round(O[i]['g'].length/2,1)) for i in path if O[i]['k']=='T' and O[i]['w']==best[t]]
    return (net,src,dst,"bottleneck %.2f mm"%best[t],"vias %d"%len(vias),"layers "+"-".join(lay),"len %.1f"%sum(O[i]['g'].length/2 for i in path if O[i]['k']=='T'))
Q=[l.split() for l in sys.stdin if l.strip()]
for net,s,d in Q: print(widest(net,s,d))

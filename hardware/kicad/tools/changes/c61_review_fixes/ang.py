import json,math
from shapely.geometry import LineString,Point,Polygon
from shapely.strtree import STRtree
D=json.load(open('dump6.json'))
G={'F':[],'B':[]}
for t in D['tracks']: G[t['layer']].append((t['net'],LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['w']/2),t['uuid']))
for v in D['vias']:
    for L in 'FB': G[L].append((v['net'],Point(v['x'],v['y']).buffer(v['d']/2),v['uuid']))
for p in D['pads']:
    for L,pl in p['polys'].items(): G[L].append((p['net'],Polygon(pl),None))
holes=[(v['net'],Point(v['x'],v['y']).buffer(v['drill']/2)) for v in D['vias']]+[(p['net'],Point(p['x'],p['y']).buffer(max(p['drill'])/2)) for p in D['pads'] if p['drill'][0]>0]
T={L:STRtree([g[1] for g in G[L]]) for L in 'FB'}; H=STRtree([h[1] for h in holes])
def clear(net,L,geom,w,uid):
    for j in T[L].query(geom.buffer(w/2+0.5)):
        n,g,u=G[L][j]
        if n==net or n=='': continue
        if g.distance(geom)<w/2+0.2: return False
    for j in H.query(geom.buffer(w/2+0.5)):
        n,g=holes[j]
        if n!=net and g.distance(geom)<w/2+0.33: return False
    return True
fix=[]
for t in D['tracks']:
    dx=t['x2']-t['x1'];dy=t['y2']-t['y1'];l=math.hypot(dx,dy)
    if l<0.1: continue
    a=math.degrees(math.atan2(dy,dx))%45
    if min(a,45-a)<=0.5: continue
    ax,ay=abs(dx),abs(dy);sx=math.copysign(1,dx);sy=math.copysign(1,dy)
    m=min(ax,ay)
    cands=[(t['x1']+sx*m,t['y1']+sy*m),(t['x2']-sx*m,t['y2']-sy*m)]  # diagonal first, or straight first
    done=False
    for K in cands:
        g=LineString([(t['x1'],t['y1']),K,(t['x2'],t['y2'])])
        if clear(t['net'],t['layer'],g,t['w'],t['uuid']):
            fix.append(dict(uuid=t['uuid'],K=[round(K[0],4),round(K[1],4)],net=t['net'],layer=t['layer'],w=t['w'],p1=[t['x1'],t['y1']],p2=[t['x2'],t['y2']])); done=True; break
print(len(fix),"fixable")
json.dump(fix,open('angfix.json','w'))

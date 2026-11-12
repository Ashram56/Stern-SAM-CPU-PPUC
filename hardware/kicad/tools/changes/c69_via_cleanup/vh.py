import hr,det3,math,re,sys,json
from shapely.geometry import Point,Polygon
b=hr.Board(); P=hr.Path
APPLY=len(sys.argv)>1 and sys.argv[1]=='a'
def ang(c,p,q):
    v1=(p[0]-c[0],p[1]-c[1]); v2=(q[0]-c[0],q[1]-c[1]); n1=math.hypot(*v1); n2=math.hypot(*v2)
    if n1<1e-6 or n2<1e-6: return 180
    return math.degrees(math.acos(max(-1,min(1,(v1[0]*v2[0]+v1[1]*v2[1])/(n1*n2)))))
def octs(a,c):
    dx=c[0]-a[0]; dy=c[1]-a[1]; adx,ady=abs(dx),abs(dy)
    if adx<1e-4 or ady<1e-4 or abs(adx-ady)<1e-4: return [[a,c]]
    d=min(adx,ady); sx=math.copysign(1,dx); sy=math.copysign(1,dy)
    m1=(round(a[0]+sx*d,4),round(a[1]+sy*d,4))            # diag first
    m2=(round(c[0]-sx*d,4),round(c[1]-sy*d,4))            # straight first
    return [[a,m1,c],[a,m2,c]]
def padpolys(net):
    out=[]
    for p in b.g['pads']:
        if p['net']==net:
            for L,pts in p['polys'].items():
                if len(pts)>=3: out.append(Polygon(pts))
    return out
failed=set(); done=[]
while True:
    o=det3.run(b.g); adj=o['_adj']; hooks=sorted(o['viahook'],key=lambda x:x[2])
    todo=[h for h in hooks if (h[0],tuple(h[1])) not in failed]
    if not todo: break
    h=todo[0]; net=h[0]; c=tuple(h[1]); key=(net,c); node=('via',net,c[0],c[1])
    lst=adj[node]
    via=[v for v in b.g['vias'] if v['net']==net and abs(v['x']-c[0])<2e-3 and abs(v['y']-c[1])<2e-3][0]
    # all tracks touching the via incl. micro ones
    alltr=[t for t in b.g['tracks'] if t['net']==net and (math.dist((t['x1'],t['y1']),c)<via['d']/2 or math.dist((t['x2'],t['y2']),c)<via['d']/2)]
    if len(alltr)!=len(lst) or len(lst)>3: failed.add(key); continue
    pp=padpolys(net); best=None
    oldlen=sum(math.dist(x[2],x[3]) for x in lst)
    for i,(m,t,e,o1) in enumerate(lst):
        L=math.dist(e,o1)
        if L<0.5: continue
        s=0.1
        while s<=L-0.3:
            V=(round(e[0]+(o1[0]-e[0])*s/L,3),round(e[1]+(o1[1]-e[1])*s/L,3)); s+=0.1
            pv=P(net,t['w'],via['d'],via.get('drill',0.3)); pv.vias.append(V)
            if any(Point(V).buffer(via['d']/2).intersects(q) for q in pp): continue
            combos=[[]]
            ok=True
            for j,(m2,t2,e2,o2) in enumerate(lst):
                if j==i: opts=[[o1,V]]
                else: opts=octs(o2,V)
                good=[]
                for pts in opts:
                    q=P(net,t2['w']).at(pts[0][0],pts[0][1],t2['layer'])
                    for p in pts[1:]: q.to(p[0],p[1])
                    if any(math.dist(a,c_)<0.15 for a,c_,l in q.segs) and len(pts)>2: continue
                    if b.check(q,quiet=True): continue
                    # angle at far node
                    far=m2
                    if far[0]=='pt':
                        if any(ang(pts[0],pts[1],x[3])<89 for x in adj[far] if x[1]['uuid']!=t2['uuid']): continue
                    good.append((q,pts))
                if not good: ok=False; break
                combos=[cb+[g] for cb in combos for g in good]
            if not ok: continue
            for cb in combos:
                dirs=[pts[-2] for q,pts in cb]
                if any(ang(V,dirs[a],dirs[b_])<89 for a in range(len(dirs)) for b_ in range(a+1,len(dirs))): continue
                bad=[x for x in b.check(pv,quiet=True) if not ('hole-hole' in x and f"via ({via['x']},{via['y']})" in x)]
                if bad: break
                nl=sum(q.length() for q,pts in cb)
                if nl<oldlen-0.15 and (best is None or nl<best[0]): best=(nl,V,cb,pv)
    if not best: failed.add(key); print('skip',net,c,h[2]); continue
    nl,V,cb,pv=best
    print('FIX',net,c,'->',V,'len %.1f -> %.1f'%(oldlen,nl))
    done.append((net,c,V,round(oldlen,2),round(nl,2)))
    if not APPLY: failed.add(key); continue
    b.commit(pv,*[q for q,pts in cb],delete=[via['uuid']]+[x[1]['uuid'] for x in lst])
json.dump(done,open('/tmp/claude-0/hr/vh_done.json','w'))
print(len(done),'fixed',len(failed),'left')

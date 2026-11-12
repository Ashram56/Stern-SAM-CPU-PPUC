import json,math,collections,sys
sys.path.insert(0,'/tmp/claude-0/hr/t')
import hr
from shapely.geometry import Point,Polygon
R=lambda v: round(v,3)
def build(g):
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
            if poly.distance(Point(pt))<1e-3: return 'pad'
        return None
    seen=set(); chains=[]
    for (net,layer,pt),lst in list(adj.items()):
        if len(lst)==2 and not term(net,layer,pt): continue
        for (nx,t) in lst:
            if t['uuid'] in seen: continue
            path=[pt,nx]; seen.add(t['uuid']); cur=nx; ts=[t]
            while len(adj[(net,layer,cur)])==2 and not term(net,layer,cur):
                (n1,t1),(n2,t2)=adj[(net,layer,cur)]
                n,tt=(n1,t1) if t1['uuid'] not in seen else (n2,t2)
                if tt['uuid'] in seen: break
                seen.add(tt['uuid']); path.append(n); ts.append(tt); cur=n
            chains.append((net,layer,path,ts,term(net,layer,path[0]),term(net,layer,path[-1])))
    return adj,chains
def turns(path):
    n=0
    for i in range(1,len(path)-1):
        a1=math.atan2(path[i][1]-path[i-1][1],path[i][0]-path[i-1][0]); a2=math.atan2(path[i+1][1]-path[i][1],path[i+1][0]-path[i][0])
        if abs((a2-a1+math.pi)%(2*math.pi)-math.pi)>0.05: n+=1
    return n
def plen(path): return sum(math.dist(path[i],path[i+1]) for i in range(len(path)-1))
def dirn(a,c):
    L=math.dist(a,c); return ((c[0]-a[0])/L,(c[1]-a[1])/L)
def firstdir(path):
    for i in range(len(path)-1):
        if math.dist(path[i],path[i+1])>=0.15: return dirn(path[i],path[i+1])
    return None
def cands(A,B):
    dx=B[0]-A[0]; dy=B[1]-A[1]; sx=1 if dx>=0 else -1; sy=1 if dy>=0 else -1
    d=min(abs(dx),abs(dy)); out=[]
    if d<1e-3 or abs(abs(dx)-abs(dy))<1e-3: return [[A,B]]
    horiz=abs(dx)>abs(dy); rem=abs(abs(dx)-abs(dy))
    st=(sx*rem,0) if horiz else (0,sy*rem)
    out.append([A,(A[0]+sx*d,A[1]+sy*d),B])
    out.append([A,(A[0]+st[0],A[1]+st[1]),B])
    for f in (0.5,0.25,0.75,0.1,0.9):
        k=(st[0]*f,st[1]*f); m1=(A[0]+k[0],A[1]+k[1]); m2=(m1[0]+sx*d,m1[1]+sy*d); out.append([A,m1,m2,B])
    for f in (0.5,0.25,0.75):
        m1=(A[0]+sx*d*f,A[1]+sy*d*f); m2=(m1[0]+st[0],m1[1]+st[1]); out.append([A,m1,m2,B])
    return [[(round(x,4),round(y,4)) for x,y in p] for p in out]
def angle_ok(v1,v2,minang=89):
    cos=v1[0]*v2[0]+v1[1]*v2[1]; return math.degrees(math.acos(max(-1,min(1,cos))))>=minang
KO=Polygon(json.load(open('/tmp/claude-0/hr/keepout.json')))
def run(sel,apply=False,log=True):
    from shapely.geometry import LineString
    b=hr.Board(); g=b.g; adj,chains=build(g); done=[]; add=[]; dele=[]
    ends=collections.defaultdict(list)
    for t in g['tracks']:
        for e in ((t['x1'],t['y1']),(t['x2'],t['y2'])): ends[(t['net'],t['layer'])].append((e,t['uuid']))
    vv=collections.defaultdict(list)
    for v in g['vias']: vv[v['net']].append((v['x'],v['y']))
    pp=collections.defaultdict(list)
    for p in g['pads']:
        for l,pts in p['polys'].items():
            if len(pts)>=3: pp[(p['net'],l)].append(Polygon(pts))
    def touched(net,layer,path,ids):
        ls=LineString(path); A=Point(path[0]); B=Point(path[-1])
        for e,u in ends[(net,layer)]:
            if u in ids: continue
            P=Point(e)
            if ls.distance(P)<0.3 and P.distance(A)>0.02 and P.distance(B)>0.02: return True
        for x,y in vv[net]:
            P=Point(x,y)
            if ls.distance(P)<0.45 and P.distance(A)>0.45 and P.distance(B)>0.45: return True
        inner=LineString(path[1:-1]) if len(path)>3 else None
        if inner is not None:
            for poly in pp[(net,layer)]:
                if poly.distance(inner)<0.05 and poly.distance(A)>1e-3 and poly.distance(B)>1e-3: return True
        return False
    for net,layer,path,ts,e0,e1 in chains:
        if layer not in 'FB': continue
        if not sel(net,layer,path,ts,e0,e1): continue
        A,B=path[0],path[-1]
        if math.dist(A,B)<0.3: continue
        ws=collections.Counter(round(t['w'],3) for t in ts); w=max(ws,key=lambda k:sum(math.dist((t['x1'],t['y1']),(t['x2'],t['y2'])) for t in ts if round(t['w'],3)==k))
        if len(ws)>1 and min(ws)<w-1e-6: continue   # necked chains left alone
        d0=firstdir(path); d1=firstdir(path[::-1]); oldT=turns(path); oldL=plen(path)
        ids={t['uuid'] for t in ts}
        if touched(net,layer,path,ids): continue
        oth0=[dirn(A,n) for n,t in adj[(net,layer,A)] if t['uuid'] not in ids and math.dist(A,n)>=0.15]
        oth1=[dirn(B,n) for n,t in adj[(net,layer,B)] if t['uuid'] not in ids and math.dist(B,n)>=0.15]
        best=None
        for c in cands(A,B):
            c=[p for i,p in enumerate(c) if i==0 or math.dist(p,c[i-1])>1e-3]
            if any(math.dist(c[i],c[i+1])<0.2 for i in range(len(c)-1)) and len(c)>2: continue
            nT=turns(c); nL=plen(c)
            if not (nT<oldT or (nT==oldT and nL<oldL-0.5)) or nL>oldL+0.02: continue
            f0=dirn(c[0],c[1]); f1=dirn(c[-1],c[-2])
            if e0=='pad' and d0 and not angle_ok(f0,d0,0) : pass
            if e0=='pad' and d0 and (f0[0]*d0[0]+f0[1]*d0[1])<0.99: continue
            if e1=='pad' and d1 and (f1[0]*d1[0]+f1[1]*d1[1])<0.99: continue
            if any(not angle_ok(f0,o) for o in oth0) or any(not angle_ok(f1,o) for o in oth1): continue
            p=hr.Path(net,w=w)
            for i in range(len(c)-1): p.segs.append((c[i],c[i+1],layer))
            if b.check(p,quiet=True): continue
            if LineString(c).buffer(w/2).intersects(KO): continue
            key=(nT,nL)
            if best is None or key<best[0]: best=(key,p,c)
        if best:
            add.append(best[1]); dele+= [t['uuid'] for t in ts]; done.append((net,layer,A,B,oldT,best[0][0],round(oldL,1),round(best[0][1],1)))
            if log: print('simplify',net,layer,A,B,'turns',oldT,'->',best[0][0],'len',round(oldL,1),'->',round(best[0][1],1))
    print(len(done),'chains simplified')
    if apply and add: b.commit(*add,delete=dele)
    return done
if __name__=='__main__':
    sel=lambda net,layer,path,ts,e0,e1: turns(path)>=3
    run(sel,apply=len(sys.argv)>1)

import sys,math,collections,json
sys.path.insert(0,'/tmp/claude-0/hr/t')
import hr,simp
from simp import *
from shapely.geometry import LineString,Point,Polygon
def run(apply=False,minturns=4):
    b=hr.Board(); g=b.g; adj,chains=build(g); add=[]; dele=[]; n=0
    ends=collections.defaultdict(list)
    for t in g['tracks']:
        for e in ((t['x1'],t['y1']),(t['x2'],t['y2'])): ends[(t['net'],t['layer'])].append((e,t['uuid']))
    vv=collections.defaultdict(list)
    for v in g['vias']: vv[v['net']].append((v['x'],v['y']))
    for net,layer,path,ts,e0,e1 in chains:
        if layer not in 'FB' or turns(path)<minturns: continue
        ws={round(t['w'],3) for t in ts}
        if len(ws)>1: continue
        w=ws.pop(); ids={t['uuid'] for t in ts}
        ls=LineString(path); A=Point(path[0]); B=Point(path[-1]); bad=False
        for e,u in ends[(net,layer)]:
            P=Point(e)
            if u not in ids and ls.distance(P)<0.3 and P.distance(A)>0.02 and P.distance(B)>0.02: bad=True;break
        for x,y in vv[net]:
            P=Point(x,y)
            if ls.distance(P)<0.45 and P.distance(A)>0.45 and P.distance(B)>0.45: bad=True;break
        if bad: continue
        d0=firstdir(path); d1=firstdir(path[::-1])
        oth0=[dirn(path[0],q) for q,t in adj[(net,layer,path[0])] if t['uuid'] not in ids and math.dist(path[0],q)>=0.15]
        oth1=[dirn(path[-1],q) for q,t in adj[(net,layer,path[-1])] if t['uuid'] not in ids and math.dist(path[-1],q)>=0.15]
        new=[path[0]]; i=0; last=len(path)-1
        while i<last:
            found=None
            for j in range(last,i+1,-1):
                sub=path[i:j+1]; st=turns(sub)
                if st<2 or math.dist(path[i],path[j])<0.3: continue
                for c in cands(path[i],path[j]):
                    c=[p for k,p in enumerate(c) if k==0 or math.dist(p,c[k-1])>1e-3]
                    if len(c)<2 or any(math.dist(c[k],c[k+1])<0.2 for k in range(len(c)-1)): continue
                    if turns(c)>=st or plen(c)>plen(sub)+0.02: continue
                    f0=dirn(c[0],c[1]); f1=dirn(c[-1],c[-2])
                    if i==0:
                        if e0=='pad' and d0 and (f0[0]*d0[0]+f0[1]*d0[1])<0.99: continue
                        if any(not angle_ok(f0,o) for o in oth0): continue
                    else:
                        k=len(new)-1
                        while k>0 and math.dist(new[k-1],new[-1])<0.15: k-=1
                        if k>0:
                            inc=dirn(new[k-1],new[-1])
                            if inc[0]*f0[0]+inc[1]*f0[1]<-0.01: continue
                    if j==last:
                        if e1=='pad' and d1 and (f1[0]*d1[0]+f1[1]*d1[1])<0.99: continue
                        if any(not angle_ok(f1,o) for o in oth1): continue
                    else:
                        k=j+1
                        while k<last and math.dist(path[j],path[k])<0.15: k+=1
                        out=dirn(path[j],path[k]); l1=dirn(c[-2],c[-1])
                        if out[0]*l1[0]+out[1]*l1[1]<-0.01: continue
                    p=hr.Path(net,w=w)
                    for k in range(len(c)-1): p.segs.append((c[k],c[k+1],layer))
                    if b.check(p,quiet=True): continue
                    if LineString(c).buffer(w/2).intersects(simp.KO): continue
                    found=(j,c); break
                if found: break
            if found: new+=found[1][1:]; i=found[0]
            else: new.append(path[i+1]); i+=1
        if turns(new)<turns(path):
            p=hr.Path(net,w=w)
            for k in range(len(new)-1):
                if math.dist(new[k],new[k+1])>1e-4: p.segs.append((new[k],new[k+1],layer))
            add.append(p); dele+=list(ids); n+=1
            print('partial',net,layer,path[0],path[-1],'turns',turns(path),'->',turns(new),'len',round(plen(path),1),'->',round(plen(new),1))
    print(n,'chains')
    if apply and add: b.commit(*add,delete=dele)
if __name__=='__main__': run(len(sys.argv)>1, int(sys.argv[2]) if len(sys.argv)>2 else 4)

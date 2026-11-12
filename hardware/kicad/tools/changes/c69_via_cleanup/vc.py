import hr,det3,math,sys,json,collections
from geomh import ang,octs
b=hr.Board(); P=hr.Path
from shapely.geometry import Polygon,LineString
KO=Polygon(json.load(open('/tmp/claude-0/hr/keepout.json')))
APPLY=len(sys.argv)>1 and sys.argv[1]=='a'
def npos(n,fallback):
    return (n[2],n[3]) if n[0]=='via' else fallback
def chains(adj):
    seen=set(); out=[]
    for n,lst in adj.items():
        if len(lst)==2 and n[0]!='pad': continue
        for (m,t,a,c) in lst:
            if t['uuid'] in seen: continue
            nodes=[n]; pos=[npos(n,a)]; trs=[]; cur=m; prev=t; seen.add(t['uuid']); trs.append(t); pos.append(npos(m,c)); nodes.append(m)
            while len(adj[cur])==2 and cur[0]!='pad':
                nx=[x for x in adj[cur] if x[1]['uuid']!=prev['uuid']]
                if not nx: break
                (m2,t2,a2,c2)=nx[0]
                if t2['uuid'] in seen: break
                seen.add(t2['uuid']); trs.append(t2); nodes.append(m2); pos.append(npos(m2,c2)); prev=t2; cur=m2
            out.append((nodes,pos,trs))
    return out

def touched(net,trs_rm,endpos,vianodes,endpads):
    from shapely.geometry import Point
    rm={t['uuid'] for t in trs_rm}
    lines=[(LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]),t['layer'],t['w']) for t in trs_rm]
    vset={(n[2],n[3]) for n in vianodes}
    for t in b.g['tracks']:
        if t['net']!=net or t['uuid'] in rm: continue
        for p in ((t['x1'],t['y1']),(t['x2'],t['y2'])):
            if any(math.dist(p,e)<0.45 for e in endpos): continue
            for ln,L,w in lines:
                if L==t['layer'] and ln.distance(Point(p))<w/2+t['w']/2: return True
    ipts=[]
    for t in trs_rm:
        for p in ((t['x1'],t['y1']),(t['x2'],t['y2'])):
            if not any(math.dist(p,e)<0.45 for e in endpos): ipts.append((p,t['layer']))
    isvia=lambda p: any(math.dist(p,x)<0.45 for x in vset)
    for t in b.g['tracks']:
        if t['net']!=net or t['uuid'] in rm: continue
        ln=LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])])
        for p,L in ipts:
            if (L==t['layer'] or isvia(p)) and ln.distance(Point(p))<t['w']/2+0.05: return True
    for v in b.g['vias']:
        if v['net']!=net: continue
        c=(v['x'],v['y'])
        if any(math.dist(c,e)<0.45 for e in endpos) or any(math.dist(c,x)<0.01 for x in vset): continue
        if any(ln.distance(Point(c))<v['d']/2+w/2 for ln,L,w in lines): return True
    for p in b.g['pads']:
        if p['net']!=net or (p['ref'],p['pad']) in endpads: continue
        for L,pts in p['polys'].items():
            if len(pts)>=3:
                pg=Polygon(pts)
                if any(L2==L and ln.distance(pg)<w/2 for ln,L2,w in lines): return True
                if any(pg.distance(Point(x))<0.45 for x in vset): return True
    return False
failed=set(); done=[]
while True:
    o=det3.run(b.g); adj=o['_adj']; found=None
    padl={}
    for p in b.g['pads']: padl[(p['net'],p['ref'],p['pad'])]=[L for L in p['polys'] if L in 'FB']
    for nodes,pos,trs in chains(adj):
        k=len(trs)
        if not any(n[0]=='via' for n in nodes[1:-1]): continue
        net=trs[0]['net']
        if net in ('GND','+3V3','GND_ISO'): continue
        cum=[0]
        for t in trs: cum.append(cum[-1]+math.dist((t['x1'],t['y1']),(t['x2'],t['y2'])))
        cands=[]
        for i in range(k):
            for j in range(i+2,k+1):
                if not any(n[0]=='via' for n in nodes[i+1:j]): continue
                cands.append((cum[j]-cum[i],i,j))
        for L0,i,j in sorted(cands,reverse=True):
            key=(net,pos[i],pos[j])
            if key in failed: continue
            if math.dist(pos[i],pos[j])<0.5 or nodes[i]==nodes[j]: failed.add(key); continue
            failed.add(key)
            def layers(idx,inner_tr,outer_tr):
                n=nodes[idx]
                if n[0]=='via': return 'FB'
                if n[0]=='pad': return ''.join(padl.get((net,n[2],n[3]),[]))
                return n[2]
            Ls=set(layers(i,None,None))&set(layers(j,None,None))
            w=max(trs[i:j],key=lambda t:math.dist((t['x1'],t['y1']),(t['x2'],t['y2'])))['w']
            w=max(w,max(t['w'] for t in trs[i:j]) if net.startswith('/Power') or net in('+5V','+12V','+3V3','GND','PI_5V') else w)
            if touched(net,trs[i:j],[pos[i],pos[j]],[n for n in nodes[i+1:j] if n[0]=='via'],{(n[2],n[3]) for n in (nodes[i],nodes[j]) if n[0]=='pad'}): continue
            best=None
            for L in Ls:
                for pts in octs(pos[i],pos[j]):
                    q=P(net,w).at(pts[0][0],pts[0][1],L)
                    for p in pts[1:]: q.to(p[0],p[1])
                    if q.length()>L0-0.5: continue
                    if b.check(q,quiet=True): continue
                    if LineString(pts).buffer(w/2).intersects(KO): continue
                    ok=True
                    for idx,near in ((i,pts[1]),(j,pts[-2])):
                        n=nodes[idx]
                        if n[0]=='pad': continue
                        inner={t['uuid'] for t in trs[i:j]}
                        for x in adj[n]:
                            if x[1]['uuid'] in inner: continue
                            if math.dist(x[2],x[3])<0.3: continue
                            if ang(pos[idx],near,x[3])<89: ok=False
                    if not ok: continue
                    if best is None or q.length()<best[0].length(): best=(q,L)
            if best:
                found=(net,i,j,best,L0,[t['uuid'] for t in trs[i:j]],[n for n in nodes[i+1:j] if n[0]=='via'],pos[i],pos[j]); break
        if found: break
    if not found: break
    net,i,j,(q,L),L0,dl,vs,pi,pj=found
    vu=[v['uuid'] for n in vs for v in b.g['vias'] if v['net']==net and abs(v['x']-n[2])<2e-3 and abs(v['y']-n[3])<2e-3]
    print('FIX',net,pi,'->',pj,L,'len %.1f -> %.1f'%(L0,q.length()),'vias removed',len(vu))
    done.append((net,pi,pj,L,round(L0,1),round(q.length(),1),len(vu)))
    if APPLY: b.commit(q,delete=dl+vu)
json.dump(done,open('/tmp/claude-0/hr/vc_done.json','w'))
print(len(done),'fixed')

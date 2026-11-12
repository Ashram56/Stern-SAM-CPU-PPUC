import json,math,collections,sys
from shapely.geometry import Point,Polygon
def run(g):
    R=lambda v: round(v,3)
    vias=collections.defaultdict(list)
    for v in g['vias']: vias[v['net']].append(v)
    pads=collections.defaultdict(list)
    for p in g['pads']:
        for L,pts in p['polys'].items():
            if len(pts)>=3: pads[(p['net'],L)].append((Polygon(pts),p))
    def node(net,layer,pt):
        for v in vias[net]:
            if math.dist(pt,(v['x'],v['y']))<v['d']/2: return ('via',net,R(v['x']),R(v['y']))
        for poly,p in pads[(net,layer)]:
            if poly.distance(Point(pt))<1e-3: return ('pad',net,p['ref'],p['pad'])
        return ('pt',net,layer,pt)
    adj=collections.defaultdict(list)
    for t in g['tracks']:
        a=(R(t['x1']),R(t['y1'])); c=(R(t['x2']),R(t['y2']))
        if math.dist(a,c)<0.05: continue
        na=node(t['net'],t['layer'],a); nc=node(t['net'],t['layer'],c)
        if na==nc: continue
        adj[na].append((nc,t,a,c)); adj[nc].append((na,t,c,a))
    out=collections.defaultdict(list)
    # via hooks
    for n,lst in adj.items():
        if n[0]!='via': continue
        c=(n[2],n[3])
        for i in range(len(lst)):
            for j in range(i+1,len(lst)):
                o1=lst[i][3]; o2=lst[j][3]
                v1=(o1[0]-c[0],o1[1]-c[1]); v2=(o2[0]-c[0],o2[1]-c[1])
                n1=math.hypot(*v1); n2=math.hypot(*v2)
                if n1<0.3 or n2<0.3: continue
                ang=math.degrees(math.acos(max(-1,min(1,(v1[0]*v2[0]+v1[1]*v2[1])/(n1*n2)))))
                if ang<80: out['viahook'].append((n[1],c,round(ang),lst[i][1]['layer'],o1,lst[j][1]['layer'],o2,len(lst)))
    # chains & overshoot
    seen=set()
    for n,lst in adj.items():
        if len(lst)==2 and n[0]!='pad': continue
        for (m,t,a,c) in lst:
            if t['uuid'] in seen: continue
            pts=[a,c]; cur=m; prev=t; seen.add(t['uuid']); nv=0; L=math.dist(a,c)
            while len(adj[cur])==2 and cur[0]!='pad':
                if cur[0]=='via': nv+=1
                nx=[x for x in adj[cur] if x[1]['uuid']!=prev['uuid']]
                if not nx: break
                (m2,t2,a2,c2)=nx[0]
                if t2['uuid'] in seen: break
                seen.add(t2['uuid']); pts.append(c2); L+=math.dist(a2,c2); prev=t2; cur=m2
            s,e=pts[0],pts[-1]
            x0,x1=sorted((s[0],e[0])); y0,y1=sorted((s[1],e[1]))
            ov=max(max(0,x0-min(p[0] for p in pts)),max(0,max(p[0] for p in pts)-x1),max(0,y0-min(p[1] for p in pts)),max(0,max(p[1] for p in pts)-y1))
            oct_=max(abs(s[0]-e[0]),abs(s[1]-e[1]))+0.414*min(abs(s[0]-e[0]),abs(s[1]-e[1]))
            if ov>=0.6: out['overshoot'].append((t['net'],round(ov,2),round(L,1),round(oct_,1),nv,s,e,len(pts)-1))
    out['_adj']=adj
    return out
if __name__=='__main__':
    g=json.load(open(sys.argv[1] if len(sys.argv)>1 else '/tmp/claude-0/hr/geo.json'))
    o=run(g)
    o.pop('_adj')
    for k,v in o.items(): print(k,len(v))
    for x in sorted(o['viahook'],key=lambda x:x[2]): print('VH',x)
    for x in sorted(o['overshoot'],key=lambda x:-x[1]): print('OV',x)
    json.dump(o,open('/tmp/claude-0/hr/det3.json','w'))

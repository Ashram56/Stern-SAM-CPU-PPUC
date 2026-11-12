import json,math,collections,sys
g=json.load(open('/tmp/claude-0/hr/geo.json'))
R=lambda v: round(v,3)
def run(g,verbose=True):
    out=collections.defaultdict(list)
    nodes=collections.defaultdict(list)   # (net,layer,x,y)->[(track, otherend)]
    for t in g['tracks']:
        a=(R(t['x1']),R(t['y1'])); c=(R(t['x2']),R(t['y2']))
        L=math.dist(a,c)
        if L<0.1: out['micro'].append((t['net'],t['layer'],a,c,t['uuid']))
        dx=abs(a[0]-c[0]);dy=abs(a[1]-c[1])
        if L>=0.1 and not(dx<2e-3 or dy<2e-3 or abs(dx-dy)<4e-3): out['non45'].append((t['net'],t['layer'],a,c,t['uuid']))
        nodes[(t['net'],t['layer'],a)].append((t,c)); nodes[(t['net'],t['layer'],c)].append((t,a))
    vias=collections.defaultdict(list)
    for v in g['vias']: vias[v['net']].append(v)
    pads=collections.defaultdict(list)
    for p in g['pads']: pads[p['net']].append(p)
    def at_via(net,pt): return any(math.dist(pt,(v['x'],v['y']))<v['d']/2 for v in vias[net])
    from shapely.geometry import Point,Polygon
    padpoly={}
    def at_pad(net,layer,pt):
        for p in pads[net]:
            pts=p['polys'].get(layer)
            if pts and len(pts)>=3:
                k=(p['ref'],p['pad'],layer,p['x'],p['y'])
                if k not in padpoly: padpoly[k]=Polygon(pts)
                if padpoly[k].distance(Point(pt))<1e-3: return True
        return False
    for (net,layer,pt),lst in nodes.items():
        if len(lst)>=2:
            for i in range(len(lst)):
                for j in range(i+1,len(lst)):
                    (t1,o1),(t2,o2)=lst[i],lst[j]
                    v1=(o1[0]-pt[0],o1[1]-pt[1]); v2=(o2[0]-pt[0],o2[1]-pt[1])
                    n1=math.hypot(*v1); n2=math.hypot(*v2)
                    if n1<0.1 or n2<0.1: continue
                    cos=(v1[0]*v2[0]+v1[1]*v2[1])/(n1*n2); ang=math.degrees(math.acos(max(-1,min(1,cos))))
                    inpad=at_pad(net,layer,pt) or at_via(net,pt)
                    if ang<1 : out['doubleback'].append((net,layer,pt,o1,o2))
                    elif ang<89 and not inpad: out['acute'].append((net,layer,pt,round(ang),o1,o2))
                    elif abs(ang-90)<1 and len(lst)==2 and not inpad and min(n1,n2)>=0.5: out['right'].append((net,layer,pt))
    return out
if __name__=='__main__':
    o=run(g)
    for k,v in o.items(): print(k,len(v))
    json.dump({k:v for k,v in o.items()},open('/tmp/claude-0/hr/det.json','w'))
    for k in ('acute','doubleback','non45'):
        for x in o[k][:80]: print(k,x[:6])

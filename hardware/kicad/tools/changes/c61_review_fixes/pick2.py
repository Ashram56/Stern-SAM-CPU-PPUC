import json,sys
exec(open('pick.py').read().split("prefer=")[0].replace("I=json.load(open(sys.argv[1])); D=json.load(open(sys.argv[2]))","I=json.load(open('isl4.json')); D=json.load(open('dump4.json'))"))
targets=[(131.275,136.9,'F',2),(131.8,134.14,'F',1),(134.225,149.5,'F',2),(134.225,152.6,'F',1),(99.6,179.77,'F',1),(99.6,179.77,'B',1)]
new=[]
for tx,ty,L,k in targets:
    tp=Point(tx,ty)
    isl=[i for i in I if i['layer']==L and Polygon(i['outline'],i['holes']).buffer(0.8).contains(tp)]
    if not isl: print("no island",tx,ty,L); continue
    P=Polygon(isl[0]['outline'],isl[0]['holes']).buffer(-0.4)
    c=[]
    for dx in [i*0.25 for i in range(-16,17)]:
        for dy in [i*0.25 for i in range(-16,17)]:
            pt=Point(tx+dx,ty+dy)
            if P.contains(pt) and ok(pt,L): c.append(pt)
    c.sort(key=lambda p:p.distance(tp))
    got=0
    for p in c:
        if got>=k: break
        if all(p.distance(Point(n[0],n[1]))>=1.0 for n in new):
            new.append((round(p.x,3),round(p.y,3),L,0)); got+=1; allv.append(p); 
    print(tx,ty,L,"island anch",isl[0]['anch'],"placed",got)
json.dump(new,open('newvias2.json','w'))

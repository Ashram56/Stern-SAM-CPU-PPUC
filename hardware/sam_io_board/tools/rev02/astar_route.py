"""Grid A* router for one net on 2 layers (0.1 mm grid, 0.2 mm track, 0.5/0.3 via).
usage: astar_route.py board net x0 y0 x1 y1 sx sy slayer gx0 gy0 gx1 gy1 [save]
env: GL goal layer (0 F.Cu, 1 B.Cu), SOFT=1 report the tracks it would have to cross, MAINGOAL=1 goal = main GND pour, W track width"""
import pcbnew, sys, heapq, math, os
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
MM=pcbnew.FromMM
a=sys.argv; b=pcbnew.LoadBoard(a[1]); net=a[2]
X0,Y0,X1,Y1=map(float,a[3:7]); sx,sy=float(a[7]),float(a[8]); sl=int(a[9]); GX0,GY0,GX1,GY1=map(float,a[10:14])
GLY=int(os.environ.get('GL','0'))
G=0.1; NX=int((X1-X0)/G)+1; NY=int((Y1-Y0)/G)+1
L=[pcbnew.F_Cu,pcbnew.B_Cu]
blk=[bytearray(NX*NY) for _ in L]; vblk=bytearray(NX*NY); goal=bytearray(NX*NY)
soft=[{} for _ in L]; vsoft={}
SOFT=os.environ.get('SOFT')=='1'
CL=MM(0.165); TR=MM(0.1); VR=MM(0.25)
items=list(b.GetTracks()); fps=list(b.GetFootprints())
for f in fps: items+=list(f.Pads())
nc=b.FindNet(net).GetNetCode()
def cells(bb,m):
    i0=max(0,int((pcbnew.ToMM(bb.GetLeft()-m)-X0)/G)); i1=min(NX-1,int((pcbnew.ToMM(bb.GetRight()+m)-X0)/G)+1)
    j0=max(0,int((pcbnew.ToMM(bb.GetTop()-m)-Y0)/G)); j1=min(NY-1,int((pcbnew.ToMM(bb.GetBottom()+m)-Y0)/G)+1)
    for j in range(j0,j1+1):
        for i in range(i0,i1+1): yield i,j
def P(i,j): return pcbnew.VECTOR2I(MM(X0+i*G),MM(Y0+j*G))
for it in items:
    bb=it.GetBoundingBox()
    if bb.GetRight()<MM(X0-1) or bb.GetLeft()>MM(X1+1) or bb.GetBottom()<MM(Y0-1) or bb.GetTop()>MM(Y1+1): continue
    same = it.GetNetCode()==nc
    for k,l in enumerate(L):
        if not it.IsOnLayer(l): continue
        sh=it.GetEffectiveShape(l)
        for i,j in cells(bb,VR+CL):
            idx=j*NX+i; p=P(i,j)
            if same and it.GetClass()=='PAD' and not it.HasHole() and sh.Collide(pcbnew.SHAPE_CIRCLE(p,VR),MM(0.05)): vblk[idx]=1
            if same and it.GetClass()=='PCB_VIA' and math.hypot(it.GetPosition().x-p.x,it.GetPosition().y-p.y)<MM(0.6): vblk[idx]=1
            if same:
                if not os.environ.get('MAINGOAL') and k==GLY and GX0<=X0+i*G<=GX1 and GY0<=Y0+j*G<=GY1 and sh.Collide(pcbnew.SHAPE_CIRCLE(p,1),0): goal[idx]=1
                continue
            hard = not SOFT or it.GetClass()=='PAD'
            if not blk[k][idx] and sh.Collide(pcbnew.SHAPE_CIRCLE(p,TR),CL):
                if hard: blk[k][idx]=1
                else: soft[k].setdefault(idx,set()).add(id(it))
            if not vblk[idx] and sh.Collide(pcbnew.SHAPE_CIRCLE(p,VR),CL):
                if hard: vblk[idx]=1
                else: vsoft.setdefault(idx,set()).add(id(it))
    if not same and it.GetClass()=='PAD' and it.HasHole():
        c=it.GetPosition(); r=it.GetDrillSize().x/2
        for i,j in cells(bb,VR+CL):
            if math.hypot(c.x-MM(X0+i*G),c.y-MM(Y0+j*G))<r+MM(0.15)+MM(0.25)+MM(0.01): vblk[j*NX+i]=1
# board edge
for i in range(NX):
    for j in range(NY):
        if not (75.5<X0+i*G<174.5 and 39.5<Y0+j*G<138.5): blk[0][j*NX+i]=blk[1][j*NX+i]=vblk[j*NX+i]=1
if os.environ.get('MAINGOAL'):
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import clusters  # clusters.py next to this script
    mp=clusters.main_polys(b); gk=L[GLY]
    for poly in mp[gk]:
        bb=poly.BBox()
        for i,j in cells(bb,0):
            x,y=X0+i*G,Y0+j*G
            if GX0<=x<=GX1 and GY0<=y<=GY1 and poly.Contains(P(i,j)): goal[j*NX+i]=1
si=round((sx-X0)/G); sj=round((sy-Y0)/G)
gl=[(i%NX,i//NX) for i in range(NX*NY) if goal[i]]
print('goal cells',len(gl), 'start blocked', blk[sl][sj*NX+si])
gc=(sum(x for x,_ in gl)/len(gl), sum(y for _,y in gl)/len(gl))
def h(i,j): return math.hypot(i-gc[0],j-gc[1])*0.9
VC=30
start=(si,sj,sl); dist={start:0}; prev={}; pq=[(h(si,sj),0,start)]
D=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]
end=None
while pq:
    f,g,s=heapq.heappop(pq)
    if g>dist.get(s,1e9): continue
    i,j,k=s
    if k==GLY and goal[j*NX+i]: end=s; break
    nb=[]
    for di,dj,c in D:
        ni,nj=i+di,j+dj
        if 0<=ni<NX and 0<=nj<NY and not blk[k][nj*NX+ni]:
            pk=prev.get(s); turn=0
            if pk and (pk[0]-i,pk[1]-j)!=(-di,-dj) and pk[2]==k: turn=0.3
            nb.append(((ni,nj,k),c+turn+(150*len(soft[k].get(nj*NX+ni,set()) - soft[k].get(j*NX+i,set())))))
    if not vblk[j*NX+i]: nb.append(((i,j,1-k),VC+150*len(vsoft.get(j*NX+i,()))))
    for t,c in nb:
        ng=g+c
        if ng<dist.get(t,1e9): dist[t]=ng; prev[t]=s; heapq.heappush(pq,(ng+h(t[0],t[1]),ng,t))
if not end:
    print('NO PATH visited',len(dist)); import collections; c=collections.Counter(s[2] for s in dist); print(c)
    xs=[s for s in dist]; print('bbox',min(X0+s[0]*G for s in xs),max(X0+s[0]*G for s in xs),min(Y0+s[1]*G for s in xs),max(Y0+s[1]*G for s in xs)); os._exit(1)
path=[end]
while path[-1]!=start: path.append(prev[path[-1]])
path.reverse()
byid={id(it):it for it in items}
hit=set()
for p in path:
    hit|=soft[p[2]].get(p[1]*NX+p[0],set())
for p,q in zip(path,path[1:]):
    if p[2]!=q[2]: hit|=vsoft.get(p[1]*NX+p[0],set())
for x in hit:
    it=byid[x]; print('CROSS',it.GetClass(),it.GetNetname(),pcbnew.ToMM(it.GetStart()) if it.GetClass()!='PCB_VIA' else '', pcbnew.ToMM(it.GetEnd()) if it.GetClass()!='PCB_VIA' else pcbnew.ToMM(it.GetPosition()), it.GetLayerName())
print('len',len(path),'vias',sum(1 for p,q in zip(path,path[1:]) if p[2]!=q[2]))
# compress
pts=[path[0]]
for idx in range(1,len(path)-1):
    p,q,r=pts[-1],path[idx],path[idx+1]
    if q[2]!=r[2] or q[2]!=p[2]: pts.append(q); continue
    d1=(q[0]-path[idx-1][0],q[1]-path[idx-1][1]); d2=(r[0]-q[0],r[1]-q[1])
    if d1!=d2: pts.append(q)
pts.append(path[-1])
for p in pts: print('%.2f %.2f %d'%(X0+p[0]*G,Y0+p[1]*G,p[2]))
if len(a)>14:
    n=b.FindNet(net)
    t=pcbnew.PCB_TRACK(b); t.SetStart(V0:=pcbnew.VECTOR2I(MM(sx),MM(sy))); t.SetEnd(P(pts[0][0],pts[0][1])); t.SetWidth(MM(float(os.environ.get('W','0.2')))); t.SetLayer(L[sl]); t.SetNet(n); b.Add(t); t.thisown=0
    for p,q in zip(pts,pts[1:]):
        if p[2]!=q[2]:
            v=pcbnew.PCB_VIA(b); v.SetPosition(P(p[0],p[1])); v.SetWidth(MM(0.5)); v.SetDrill(MM(0.3)); v.SetNet(n); b.Add(v); v.thisown=0
        elif (p[0],p[1])!=(q[0],q[1]):
            t=pcbnew.PCB_TRACK(b); t.SetStart(P(p[0],p[1])); t.SetEnd(P(q[0],q[1])); t.SetWidth(MM(float(os.environ.get('W','0.2')))); t.SetLayer(L[p[2]]); t.SetNet(n); b.Add(t); t.thisown=0
    b.Save(a[14])
os._exit(0)

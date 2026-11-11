import sys,json; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
b=load(sys.argv[1]); f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
mm=pcbnew.ToMM
out=[]
def poly(sh):
    return [[mm(sh.CPoint(i).x),mm(sh.CPoint(i).y)] for i in range(sh.PointCount())]
for zn,L,ln in [('GND_TOP',pcbnew.F_Cu,'F'),('GND_BOT',pcbnew.B_Cu,'B')]:
    z=[z for z in b.Zones() if z.GetZoneName()==zn][0]; ps=z.GetFilledPolysList(L)
    vias=[t for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=='GND']
    th=[p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname()=='GND' and p.HasHole()]
    for i in range(ps.OutlineCount()):
        a=sum(1 for v in vias if ps.Contains(v.GetPosition(),i,v.GetWidth(L)//2))+sum(1 for p in th if ps.Contains(p.GetPosition(),i,p.GetSizeX()//2))
        holes=[poly(ps.Hole(i,j)) for j in range(ps.HoleCount(i))]
        out.append(dict(layer=ln,idx=i,anch=a,outline=poly(ps.Outline(i)),holes=holes,area=abs(ps.Outline(i).Area())/1e12))
json.dump(out,open(sys.argv[2],'w'))
print(len(out))

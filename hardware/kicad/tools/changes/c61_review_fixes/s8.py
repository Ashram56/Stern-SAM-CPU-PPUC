import sys,json; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
b=load('/tmp/rv/s7/sam_cpu.kicad_pcb')
d=json.load(open('/tmp/rv/d7.json'))
bad=set()
for x in d['violations']:
    if x['type'].startswith(('silk','text_')):
        for i in x['items']:
            if i['description'].startswith('Reference field of '): bad.add(i['description'].split()[-1])
fps={f.GetReference():f for f in b.GetFootprints()}
EB=b.GetBoardEdgesBoundingBox(); edge=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(edge,False); edge.Deflate(M(0.4),pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,5000)
def poly_of(item,layer,inf=0):
    s=pcbnew.SHAPE_POLY_SET(); item.TransformShapeToPolygon(s,layer,M(inf),5000,pcbnew.ERROR_OUTSIDE); return s
obst=pcbnew.SHAPE_POLY_SET()
texts={}
for f in b.GetFootprints():
    for p in f.Pads():
        if p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.F_Mask): obst.Append(poly_of(p,pcbnew.F_Mask if p.IsOnLayer(pcbnew.F_Mask) else pcbnew.F_Cu,0.16))
    for g in f.GraphicalItems():
        if g.GetLayer()==pcbnew.F_SilkS and g.IsVisible() if hasattr(g,'IsVisible') else g.GetLayer()==pcbnew.F_SilkS:
            obst.Append(poly_of(g,pcbnew.F_SilkS,0.1))
    for fld in [f.Value()]+[x for x in f.GetFields() if x.IsVisible() and x.GetLayer()==pcbnew.F_SilkS and not x.IsReference()]:
        if fld.IsVisible() and fld.GetLayer()==pcbnew.F_SilkS: obst.Append(poly_of(fld,pcbnew.F_SilkS,0.1))
for dr in b.GetDrawings():
    if dr.GetLayer()==pcbnew.F_SilkS: obst.Append(poly_of(dr,pcbnew.F_SilkS,0.1))
for f in b.GetFootprints():
    r=f.Reference()
    if r.IsVisible() and r.GetLayer()==pcbnew.F_SilkS and f.GetReference() not in bad: obst.Append(poly_of(r,pcbnew.F_SilkS,0.1))
obst.Simplify()
def collides(s):
    t=pcbnew.SHAPE_POLY_SET(s); t.BooleanIntersection(obst)
    a=sum(abs(t.Outline(i).Area()) for i in range(t.OutlineCount()))
    inside=pcbnew.SHAPE_POLY_SET(s); inside.BooleanSubtract(edge)
    a+=10*sum(abs(inside.Outline(i).Area()) for i in range(inside.OutlineCount()))
    return a
moved=0;fail=[]
for ref in sorted(bad):
    f=fps.get(ref)
    if not f: continue
    r=f.Reference()
    if r.GetTextHeight()<M(1.0) or r.GetTextThickness()<M(0.15):
        r.SetTextSize(pcbnew.VECTOR2I(M(1.0),M(1.0))); r.SetTextThickness(M(0.15))
    cy=f.GetCourtyard(pcbnew.F_CrtYd); bb=cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
    cx=bb.GetCenter().x; c_y=bb.GetCenter().y
    best=None
    for ang in (0,90):
        r.SetTextAngleDegrees(ang); r.SetPosition(pcbnew.VECTOR2I(cx,c_y))
        tb=r.GetBoundingBox(); hw=tb.GetWidth()//2; hh=tb.GetHeight()//2
        cands=[(cx,bb.GetTop()-hh-M(0.25)),(cx,bb.GetBottom()+hh+M(0.25)),(bb.GetLeft()-hw-M(0.25),c_y),(bb.GetRight()+hw+M(0.25),c_y),(cx,c_y)]
        for step in (1,2,3):
            cands+= [(cx+dx*M(1.0)*step,y) for (x,y) in cands[:2] for dx in (-1,1)]
        for (x,y) in cands:
            r.SetPosition(pcbnew.VECTOR2I(int(x),int(y)))
            sc=collides(poly_of(r,pcbnew.F_SilkS,0.05))
            dist=((x-cx)**2+(y-c_y)**2)**0.5
            k=(sc>0.001,sc,dist)
            if best is None or k<best[0]: best=(k,ang,x,y)
    k,ang,x,y=best
    r.SetTextAngleDegrees(ang); r.SetPosition(pcbnew.VECTOR2I(int(x),int(y)))
    obst.Append(poly_of(r,pcbnew.F_SilkS,0.1))
    if k[0]: fail.append(ref)
    moved+=1
print("refs processed",moved,"still colliding",len(fail),fail[:40])
pcbnew.SaveBoard('/tmp/rv/s8/sam_cpu.kicad_pcb',b)

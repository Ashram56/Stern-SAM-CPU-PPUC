import pcbnew,json,sys
b=pcbnew.LoadBoard(sys.argv[1]); O=30.0
def mm(v): return pcbnew.ToMM(v)
out=[]
for f in b.GetFootprints():
    try: bb=f.GetCourtyard(pcbnew.F_CrtYd).BBox()
    except Exception: bb=f.GetBoundingBox(False)
    if bb.GetWidth()==0: bb=f.GetBoundingBox(False)
    pads=[]
    for p in f.Pads():
        q=p.GetPosition(); s=p.GetBoundingBox()
        pads.append([mm(q.x)-O,mm(q.y)-O,mm(s.GetWidth()),mm(s.GetHeight()),p.GetNumber(),p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH])
    out.append(dict(ref=f.GetReference(),x0=mm(bb.GetX())-O,y0=mm(bb.GetY())-O,x1=mm(bb.GetRight())-O,y1=mm(bb.GetBottom())-O,pads=pads))
json.dump(out,open(sys.argv[2],'w'))

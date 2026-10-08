import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
for d in b.GetDrawings():
    if d.GetLayerName()=="Edge.Cuts":
        s=d.GetStart();e=d.GetEnd(); print(d.GetShapeStr(), round(s.x/1e6,2),round(s.y/1e6,2),round(e.x/1e6,2),round(e.y/1e6,2))
for r in ['J17','J22','J23','J24','J30','J21','MH9','MH10','MH11','MH12','MH5','J10','J11','U23','U24']:
    f=b.FindFootprintByReference(r); bb=f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f else None
    p=f.GetPosition(); print(r, round(p.x/1e6,2), round(p.y/1e6,2), f.GetOrientationDegrees(), [round(v/1e6,1) for v in (bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom())] if bb else '')

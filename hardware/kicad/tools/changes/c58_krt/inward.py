import pcbnew,sys,math
MM=pcbnew.FromMM; mm=pcbnew.ToMM
b=pcbnew.LoadBoard(sys.argv[1]); K=[]
u4=b.FindFootprintByReference('U4'); c=u4.GetPosition(); cx,cy=mm(c.x),mm(c.y)
D=float(sys.argv[3]) if len(sys.argv)>3 else 4.0
segs=[t for t in b.GetTracks() if t.GetClass()!='PCB_VIA']
moved=0
for v in [t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='+3V3']:
    x,y=mm(v.GetPosition().x),mm(v.GetPosition().y)
    if max(abs(x-cx),abs(y-cy))<5.5 or max(abs(x-cx),abs(y-cy))>7.0: continue
    con=[s for s in segs if s.GetNetCode()==v.GetNetCode() and v.GetPosition() in (s.GetStart(),s.GetEnd())]
    if len(con)!=1: print('skip',x,y,len(con)); continue
    s=con[0]; far=s.GetEnd() if s.GetStart()==v.GetPosition() else s.GetStart()
    pad=[p for p in u4.Pads() if p.GetNetCode()==v.GetNetCode() and p.HitTest(far)]
    if not pad: print('skip nopad',x,y); continue
    p=pad[0]; px,py=mm(p.GetPosition().x),mm(p.GetPosition().y)
    if px>cx+4: print("keep right",p.GetNumber()); continue
    if abs(px-cx)>abs(py-cy): nx,ny=cx+math.copysign(D,px-cx),py
    else: nx,ny=px,cy+math.copysign(D,py-cy)
    v.SetPosition(pcbnew.VECTOR2I(MM(nx),MM(ny)))
    if s.GetStart()==far: s.SetEnd(v.GetPosition())
    else: s.SetStart(v.GetPosition())
    # stub from the pad centre
    if s.GetStart()==far: s.SetStart(p.GetPosition())
    else: s.SetEnd(p.GetPosition())
    moved+=1; print('pin',p.GetNumber(),'via',(x,y),'->',(round(nx,2),round(ny,2)))
b.Save(sys.argv[2]); print('moved',moved)

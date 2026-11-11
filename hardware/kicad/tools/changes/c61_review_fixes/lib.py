import pcbnew
pcbnew.SwigPyIterator.next=pcbnew.SwigPyIterator.__next__
M=pcbnew.FromMM
def load(p): return pcbnew.LoadBoard(p)
def byuuid(b,pref):
    r=[t for t in b.GetTracks() if t.m_Uuid.AsString().startswith(pref)]
    assert len(r)==1,(pref,len(r)); return r[0]
def seg(b,net,layer,x1,y1,x2,y2,w):
    t=pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(M(x1),M(y1))); t.SetEnd(pcbnew.VECTOR2I(M(x2),M(y2)))
    t.SetWidth(M(w)); t.SetLayer(layer); t.SetNet(b.FindNet(net)); b.Add(t); return t
def via(b,net,x,y,d=0.6,dr=0.3):
    v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(M(x),M(y))); v.SetWidth(M(d)); v.SetDrill(M(dr)); v.SetNet(b.FindNet(net)); v.SetViaType(pcbnew.VIATYPE_THROUGH); b.Add(v); return v

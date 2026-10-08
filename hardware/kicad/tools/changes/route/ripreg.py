import pcbnew,sys
# board in, board out, x0 y0 x1 y1 (board mm): rip every net with unlocked copper in the box (all its unlocked copper)
b=pcbnew.LoadBoard(sys.argv[1]); x0,y0,x1,y1=map(float,sys.argv[3:7])
M=pcbnew.FromMM
box=pcbnew.SHAPE_RECT(pcbnew.VECTOR2I(M(x0+30),M(y0+30)),M(x1-x0),M(y1-y0))
t=b.Tracks(); tr=[t[i].Cast() for i in range(t.size())]
nets={x.GetNetname() for x in tr if not x.IsLocked() and x.GetEffectiveShape().Collide(box,0) and x.GetNetname() not in ('GND',)}
rip=[x for x in tr if not x.IsLocked() and x.GetNetname() in nets]
for x in rip: b.Remove(x)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[2]); print(len(nets),'nets',len(rip),'items ripped'); print(sorted(nets))

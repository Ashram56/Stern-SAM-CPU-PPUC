# take r2 board, replace copper of NETS with the original copper from v2
import pcbnew,sys
src,orig,out=sys.argv[1:4]; nets=set(sys.argv[4:])
b=pcbnew.LoadBoard(src); o=pcbnew.LoadBoard(orig); K=[]
for t in list(b.GetTracks()):
    if t.GetNetname() in nets: K.append(t); b.Remove(t)
n=0
for t in o.GetTracks():
    if t.GetNetname() in nets:
        c=t.Duplicate(); c.SetNet(b.FindNet(t.GetNetname())); b.Add(c); K.append(c); n+=1
b.Save(out); print('grafted',n)

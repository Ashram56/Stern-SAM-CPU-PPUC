import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]);K=[]
nets=set(open(sys.argv[3]).read().split('\n'))-{''}
for t in list(b.GetTracks()):
    if t.GetNetname() in nets: K.append(t); b.Remove(t)
    else: t.SetLocked(True)
for d in list(b.GetDrawings()):
    if d.GetLayer()==pcbnew.User_2: K.append(d); b.Remove(d)
b.Save(sys.argv[2]); print('ripped',len(K))

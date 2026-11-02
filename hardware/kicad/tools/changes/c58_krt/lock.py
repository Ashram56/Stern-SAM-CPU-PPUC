import pcbnew,sys
N=set(sys.argv[3].split('|'))
b=pcbnew.LoadBoard(sys.argv[1]);n=0
for t in b.GetTracks():
    if t.GetNetname() not in N: t.SetLocked(True); n+=1
b.Save(sys.argv[2]);print('locked',n)

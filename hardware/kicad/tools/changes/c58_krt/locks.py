import pcbnew,sys
ref=pcbnew.LoadBoard(sys.argv[1]); b=pcbnew.LoadBoard(sys.argv[2])
L={t.m_Uuid.AsString() for t in ref.GetTracks() if t.IsLocked()}
print('ref locked',len(L),'of',len(list(ref.GetTracks())))
n=0
for t in b.GetTracks():
    lk=t.m_Uuid.AsString() in L; t.SetLocked(lk); n+=lk
print('locked now',n,'of',len(list(b.GetTracks())))
print('user2',sum(1 for d in b.GetDrawings() if d.GetLayer()==pcbnew.User_2))
b.Save(sys.argv[3])

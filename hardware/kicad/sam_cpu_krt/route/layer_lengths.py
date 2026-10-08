import pcbnew,sys,collections
b=pcbnew.LoadBoard(sys.argv[1]); L=collections.Counter()
for t in b.GetTracks():
    if t.GetClass()!="PCB_VIA": L[t.GetLayerName()]+=t.GetLength()/1e6
print({k:round(v) for k,v in L.items()})

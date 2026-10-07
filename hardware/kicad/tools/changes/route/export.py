import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
for z in list(b.Zones()): b.Remove(z)
print(pcbnew.ExportSpecctraDSN(b, sys.argv[2]))

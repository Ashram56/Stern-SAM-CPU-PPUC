import pcbnew,sys
# board, ses, out board: import an autorouted session (zones dropped)
b=pcbnew.LoadBoard(sys.argv[1])
for z in list(b.Zones()): b.Remove(z)
assert pcbnew.ImportSpecctraSES(b, sys.argv[2])
b.Save(sys.argv[3])

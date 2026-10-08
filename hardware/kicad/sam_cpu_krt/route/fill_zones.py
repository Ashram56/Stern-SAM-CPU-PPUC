import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
zs = [b.GetArea(i) for i in range(b.GetAreaCount())]
pcbnew.ZONE_FILLER(b).Fill(zs)
pcbnew.SaveBoard(sys.argv[2], b)
print("filled", len(zs))

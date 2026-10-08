import pcbnew, sys
# board, ses, out board: import an autorouted session, keep the zones (removed during import, put back, refilled)
b = pcbnew.LoadBoard(sys.argv[1])
zones = [b.GetArea(i) for i in range(b.GetAreaCount())]
for z in zones:
    b.Remove(z)
assert pcbnew.ImportSpecctraSES(b, sys.argv[2])
for z in zones:
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[3])
t = b.Tracks()
print('tracks+vias', t.size(), 'zones', b.GetAreaCount())

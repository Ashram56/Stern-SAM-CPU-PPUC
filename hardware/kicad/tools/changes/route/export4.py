import pcbnew,sys
# export with only the inner planes (outer GND pours are filled after routing)
b=pcbnew.LoadBoard(sys.argv[1])
for z in list(b.Zones()):
    if z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu): b.Remove(z)
print(pcbnew.ExportSpecctraDSN(b, sys.argv[2]))

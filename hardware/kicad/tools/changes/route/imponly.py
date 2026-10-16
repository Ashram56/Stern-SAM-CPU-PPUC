import pcbnew, sys
# board, ses, out, nets: add the copper of the given nets (comma-separated) from the session to the board
ISO = set(sys.argv[4].split(','))
tmp = pcbnew.LoadBoard(sys.argv[1])
keep = [z for z in tmp.Zones()]
for z in keep: tmp.Remove(z)
assert pcbnew.ImportSpecctraSES(tmp, sys.argv[2])
b = pcbnew.LoadBoard(sys.argv[1])
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
t = tmp.Tracks(); n = 0
for x in [t[i] for i in range(t.size())]:
    x = x.Cast()
    if x.GetNetname() in ISO:
        if x.Type() == pcbnew.PCB_VIA_T:
            y = pcbnew.PCB_VIA(b); y.SetPosition(x.GetPosition()); y.SetDrill(x.GetDrill()); y.SetWidth(x.GetWidth(pcbnew.F_Cu))
            y.SetViaType(x.GetViaType()); y.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        else:
            y = pcbnew.PCB_TRACK(b); y.SetStart(x.GetStart()); y.SetEnd(x.GetEnd()); y.SetWidth(x.GetWidth()); y.SetLayer(x.GetLayer())
        y.SetNet(nets[x.GetNetname()]); b.Add(y); n += 1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[3]); print('added', n, keep and '')

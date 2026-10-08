import pcbnew, sys
# board, iso ses, out: add the iso-net copper from the session to the board
ISO = {'GND_ISO', 'Net-(D27-A1)', 'Net-(D27-A2)', 'Net-(JP2-A)', 'Net-(U32-VISOIN)'}
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

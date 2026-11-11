import pcbnew, sys
NETS = set(sys.argv[4].split(','))
tmp = pcbnew.LoadBoard(sys.argv[1]); kz=[z for z in tmp.Zones()]
for z in kz: tmp.Remove(z)
assert pcbnew.ImportSpecctraSES(tmp, sys.argv[2])
b = pcbnew.LoadBoard(sys.argv[1]); keep=[]
def key(t):
    if t.GetClass()=='PCB_VIA': return ('v', t.GetPosition().x//1000, t.GetPosition().y//1000)
    a=(t.GetStart().x//1000,t.GetStart().y//1000); c=(t.GetEnd().x//1000,t.GetEnd().y//1000)
    return ('t', t.GetLayer(), min(a,c), max(a,c))
old = {key(t) for t in b.GetTracks() if t.GetNetname() in NETS}
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
n=0; import collections; c=collections.Counter()
for x in list(tmp.GetTracks()):
    if x.GetNetname() not in NETS or key(x) in old: continue
    if x.GetClass()!='PCB_VIA' and x.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu): c['skip inner']+=1; continue
    if x.GetClass()=='PCB_VIA':
        y=pcbnew.PCB_VIA(b); y.SetPosition(x.GetPosition()); y.SetDrill(x.GetDrill()); y.SetWidth(x.GetWidth(pcbnew.F_Cu)); y.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
    else:
        y=pcbnew.PCB_TRACK(b); y.SetStart(x.GetStart()); y.SetEnd(x.GetEnd()); y.SetWidth(x.GetWidth()); y.SetLayer(x.GetLayer())
    y.SetNet(nets[x.GetNetname()]); b.Add(y); keep.append(y); n+=1; c[x.GetNetname()]+=1
b.Save(sys.argv[3]); print('added',n,c)

import pcbnew,sys,json
inp,drc,out=sys.argv[1:4]; nets=set(sys.argv[4:])
b=pcbnew.LoadBoard(inp); K=[]
items={t.m_Uuid.AsString():t for t in b.GetTracks()}
kill=set()
for v in json.load(open(drc))['violations']:
    if v['type'] not in ('shorting_items','clearance','tracks_crossing','hole_to_hole','hole_clearance'): continue
    us=[i['uuid'] for i in v['items']]
    g=[u for u in us if u in items and items[u].GetNetname() in nets]
    o=[u for u in us if not(u in items and items[u].GetNetname() in nets)]
    if g and o: kill.update(g)
for u in kill: print('cut',items[u].GetNetname(),items[u].GetClass()); K.append(items[u]); b.Remove(items[u])
b.Save(out)

import hr,math,json
b=hr.Board(); d=json.load(open('/tmp/claude-0/hr/drc/s8.json')); dl=[]
for v0 in d['violations']:
    if v0['type']!='via_dangling': continue
    p=(v0['items'][0]['pos']['x'],v0['items'][0]['pos']['y'])
    v=[v for v in b.g['vias'] if math.dist((v['x'],v['y']),p)<0.01][0]
    ends=[]
    for t in b.g['tracks']:
        if t['net']==v['net']:
            for e in ((t['x1'],t['y1']),(t['x2'],t['y2'])):
                if math.dist(e,p)<v['d']/2: ends.append((e,t['layer']))
    ok=len(ends)>=2 and all(math.dist(e,ends[0][0])<0.005 for e,l in ends) and len({l for e,l in ends})==1
    print(v['net'],p,ends,ok)
    if ok: dl.append(v['uuid'])
b.commit(delete=dl)

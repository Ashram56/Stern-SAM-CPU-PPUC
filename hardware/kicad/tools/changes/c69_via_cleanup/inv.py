import hr,math
b=hr.Board()
dl=[]
for t in b.g['tracks']:
    a=(t['x1'],t['y1']); c=(t['x2'],t['y2'])
    for v in b.g['vias']:
        if v['net']==t['net'] and math.dist(a,(v['x'],v['y']))<v['d']/2-0.01 and math.dist(c,(v['x'],v['y']))<v['d']/2-0.01 and t['w']<=v['d']:
            dl.append(t['uuid']); break
print(len(dl),'in-via tracks')
b.commit(delete=dl)

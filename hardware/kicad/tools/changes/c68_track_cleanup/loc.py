import json,math,sys
g=json.load(open('/tmp/claude-0/hr/geo.json'))
def loc(net,x,y,r=2.5):
    print('==',net,x,y)
    for t in g['tracks']:
        if t['net']==net and (math.dist((t['x1'],t['y1']),(x,y))<r or math.dist((t['x2'],t['y2']),(x,y))<r):
            print(' T',t['layer'],(round(t['x1'],3),round(t['y1'],3)),(round(t['x2'],3),round(t['y2'],3)),t['w'],t['uuid'][:8])
    for v in g['vias']:
        if v['net']==net and math.dist((v['x'],v['y']),(x,y))<r: print(' V',(v['x'],v['y']),v['d'])
    for p in g['pads']:
        if p['net']==net and math.dist((p['x'],p['y']),(x,y))<r: print(' P',p['ref'],p['pad'],(round(p['x'],3),round(p['y'],3)),list(p['polys'].keys()))
if __name__=='__main__':
    a=sys.argv[1:]
    for i in range(0,len(a),3): loc(a[i],float(a[i+1]),float(a[i+2]))

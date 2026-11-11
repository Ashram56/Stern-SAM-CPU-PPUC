import sys; sys.path.insert(0,'/tmp/claude-0/hr/t'); import hr, json
b=hr.Board(); g=b.g
def inbox(x,y,bx): return bx[0]<=x<=bx[2] and bx[1]<=y<=bx[3]
dele=[]
# I2S copper north of y 123.5 in the audio area (rerouted to the mux by hand)
for t in g['tracks']:
    if t['net'] in ('I2S_BCK','I2S_LRCK','I2S_DIN') and (inbox(t['x1'],t['y1'],(110,95,148,123.6)) or inbox(t['x2'],t['y2'],(110,95,148,123.6))): dele.append(t['uuid'])
for v in g['vias']:
    if v['net'] in ('I2S_BCK','I2S_LRCK','I2S_DIN') and inbox(v['x'],v['y'],(110,95,148,123.6)): dele.append(v['uuid'])
# +12V: west vertical + branch to the trunk (rerouted on B)
for t in g['tracks']:
    if t['net']=='+12V' and (inbox(t['x1'],t['y1'],(112.5,61.0,141,99.5)) or inbox(t['x2'],t['y2'],(112.5,61.0,141,99.5))):
        dele.append(t['uuid'])
for v in g['vias']:
    if v['net']=='+12V' and inbox(v['x'],v['y'],(112.5,63,141,99.5)): dele.append(v['uuid'])
# +5V dead stub, orphan GND vias + stubs of the old DAC area
for t in g['tracks']:
    if t['net']=='+5V' and inbox(t['x1'],t['y1'],(114,121,119,124)): dele.append(t['uuid'])
    if t['net']=='GND' and t['layer']=='F' and (inbox(t['x1'],t['y1'],(112,99,140,123)) and inbox(t['x2'],t['y2'],(112,99,140,123))): dele.append(t['uuid'])
for v in g['vias']:
    if v['net']=='GND' and inbox(v['x'],v['y'],(112,99,140,123)): dele.append(v['uuid'])
dele=list(dict.fromkeys(dele)); print(len(dele))
json.dump(dele,open('/tmp/claude-0/k/pl/dele.json','w'))

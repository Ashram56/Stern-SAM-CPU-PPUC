import sys,json; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
b=load('/tmp/rv/s6/sam_cpu.kicad_pcb'); L={'F':pcbnew.F_Cu,'B':pcbnew.B_Cu}
skip=set(json.load(open('/tmp/rv/angskip.json')))
for f in json.load(open('/tmp/rv/angfix.json')):
    if f['uuid'][:8] in skip: continue
    t=byuuid(b,f['uuid'][:8]); t.SetEnd(pcbnew.VECTOR2I(M(f['K'][0]),M(f['K'][1])))
    seg(b,f['net'],L[f['layer']],f['K'][0],f['K'][1],f['p2'][0],f['p2'][1],f['w'])
pcbnew.SaveBoard('/tmp/rv/s7/sam_cpu.kicad_pcb',b)

import sys,json; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
b=load('/tmp/rv/s4/sam_cpu.kicad_pcb')
for x,y,L,a in json.load(open('/tmp/rv/newvias2.json')): via(b,'GND',x,y)
pcbnew.SaveBoard('/tmp/rv/s5/sam_cpu.kicad_pcb',b)

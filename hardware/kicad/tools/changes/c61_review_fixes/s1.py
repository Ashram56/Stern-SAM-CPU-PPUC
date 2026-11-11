import sys; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
b=load('/tmp/rv/w/sam_cpu.kicad_pcb')
keep=[]
# 12V_OR: replace 0.3 mm vertical by a 1.0 mm leg at x 141.0
t=byuuid(b,'8b0a3dcc'); keep.append(t); b.Remove(t)
seg(b,'/Power/12V_OR',pcbnew.F_Cu,140.5,54.0,141.0,54.5,0.8)
seg(b,'/Power/12V_OR',pcbnew.F_Cu,141.0,54.5,141.0,59.2,1.0)
# IO_12V: widen tapered B segments to 0.8
for u in ['0b1d9f95','55bc501c','6729e87a','73103642','ad19a7a5','e890700c']:
    byuuid(b,u).SetWidth(M(0.8))
pcbnew.SaveBoard('/tmp/rv/s1/sam_cpu.kicad_pcb',b)

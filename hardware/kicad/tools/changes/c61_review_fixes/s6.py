import sys,json; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
b=load('/tmp/rv/s5/sam_cpu.kicad_pcb'); keep=[]
for u in ['a6323f77','0d557cb8','ee133357','aec647fc','eb1c8f7e']:
    t=byuuid(b,u); keep.append(t); b.Remove(t)
t=byuuid(b,'dc627b63'); t.SetEnd(pcbnew.VECTOR2I(M(69.7),M(58.5702)))
pcbnew.SaveBoard('/tmp/rv/s6/sam_cpu.kicad_pcb',b)
b=load('/tmp/rv/s6/sam_cpu.kicad_pcb')
for u in ['500b1bad','a8b512e1','b8ecec3c','e553b61d','730b99fc','92d56758','48785f56']:
    t=byuuid(b,u); keep.append(t); b.Remove(t)
seg(b,'+5V',pcbnew.F_Cu,98.016,63.3988,98.8,63.3988,0.375)
seg(b,'+5V',pcbnew.F_Cu,98.8,63.3988,98.8,63.1,0.375)
pcbnew.SaveBoard('/tmp/rv/s6/sam_cpu.kicad_pcb',b)

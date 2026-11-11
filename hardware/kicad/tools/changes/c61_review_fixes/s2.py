import sys,json; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
b=load('/tmp/rv/s1/sam_cpu.kicad_pcb')
nets=['/Power/IO_12V','/Power/12V_OR','/Power/EXT_12V','+12V','/Power/EXT_5V','/Power/J11_5V','Net-(J11-Pin_1)','Net-(JP1-A)','+5V','PI_5V']
skip=set(json.load(open('/tmp/rv/skipvias.json'))) if len(sys.argv)>1 else set()
n=0
for t in b.GetTracks():
    if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname() in nets and t.GetWidth(pcbnew.F_Cu)<M(0.79):
        k="%s@%.3f,%.3f"%(t.GetNetname(),pcbnew.ToMM(t.GetX()),pcbnew.ToMM(t.GetY()))
        if k in skip: continue
        t.SetWidth(M(0.8)); t.SetDrill(M(0.4)); n+=1
print("upgraded",n)
pcbnew.SaveBoard('/tmp/rv/s2/sam_cpu.kicad_pcb',b)

import sys,json; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
import xml.etree.ElementTree as ET
b=load('/tmp/rv/s8/sam_cpu.kicad_pcb')
t=ET.parse('/tmp/rv/net.xml').getroot(); n=0
for c in t.iter('comp'):
    f=b.FindFootprintByReference(c.get('ref'))
    if f is None: continue
    for fl in c.iter('field'):
        name=fl.get('name'); val=fl.text or ''
        if name in ('Footprint',): continue
        if f.HasField(name):
            if f.GetFieldText(name)!=val: f.GetField(name).SetText(val); n+=1
        else:
            fld=pcbnew.PCB_FIELD(f,f.GetNextFieldOrdinal(),name); fld.SetText(val); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab); f.Add(fld); n+=1
print("fields set",n)
pcbnew.SaveBoard('/tmp/rv/s9/sam_cpu.kicad_pcb',b)

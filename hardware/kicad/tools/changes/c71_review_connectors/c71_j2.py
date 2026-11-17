# c71 board: J2 pad 1 -> GND, pad 12 -> TAMPIN (old Net-(J2-Pin_1) front end), MEM_PROTECT renamed DED8, R93 / R117 values swapped.
import sys,re; sys.path.insert(0,'/tmp/claude-0/hr')
import hr
P=hr.PCB; t=open(P).read()
TA='/Dedicated switches 1-16/TAMPIN'
if 'Net-(J2-Pin_1)"' in t:
    i=t.index('(property "Reference" "J2"'); a=t.rfind('\n\t(footprint ',0,i); e=t.index('\n\t(footprint ',i); fp=t[a:e]
    def setnet(fp,pad,net):
        m=re.search(r'\(pad "%s" thru_hole'%pad,fp); j=fp.index('(net ',m.start()); k=fp.index(')',j)
        return fp[:j]+'(net "%s"'%net+fp[k:]
    fp=setnet(fp,'1','GND'); fp=setnet(fp,'12',TA)
    t=t[:a]+fp+t[e:]
    t=t.replace('"Net-(J2-Pin_1)"','"%s"'%TA).replace('"MEM_PROTECT"','"DED8"')
    for ref,old,new in (('R93','1.5k','4.7k'),('R117','4.7k','1.5k')):
        i=t.index(f'(property "Reference" "{ref}"'); j=t.index(f'(property "Value" "{old}"',i); assert j-i<800
        t=t[:j]+f'(property "Value" "{new}"'+t[j+len(f'(property "Value" "{old}"'):]
    open(P,'w').write(t)
b=hr.Board(); b.redump()
dele=['451bb144-1df7-447b-a08f-e9e41a2abfbc','eea5245a-63cd-4d60-9a2b-039fe7fcc34c','04ae9ffd-85ee-4bcf-95ca-93028b985b97','8b04932b-2a77-4a5c-b4a7-bb2afc6322c1','ca514475-f99d-494c-bd20-ceabd346c560','0b6882ff-2c50-4553-9cfe-e150f1c42133']
b.g['tracks']=[x for x in b.g['tracks'] if x['uuid'] not in dele]
import json; json.dump(b.g,open(hr.GEO,'w')); b.load()
p=hr.Path(TA,w=0.2).at(62.29,231.41,"B").to(62.29,234.6).to(63.3,235.61).to(63.3,237.041).to(63.744,237.485)
r=b.check(p)
b.view('j2c.png',(56,228,76,240),hl=(TA,),paths=(p,),size=12,netlabels=2)
if not r and 'go' in sys.argv:
    b.commit(p,delete=dele); hr.drc('c71b')

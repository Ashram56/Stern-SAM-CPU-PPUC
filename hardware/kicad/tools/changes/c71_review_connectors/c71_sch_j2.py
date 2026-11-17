# c71 (2026-11-17, functional review): J2 as on the original board 520-5246-00.
#   pin 1 -> GND (was the first input), pin 12 -> TAMPIN front end R93 / R94 -> U17 D0 (was GND),
#   pins 2,3,4,6,7,8,9 keep their front ends (U17 D1..D7 = D-1..D-7), pin 10 = D-8 -> U30 D0 (label DED8, was MEM_PROTECT).
#   R93 1.5k -> 4.7k (TAMPIN, as the original R17), R117 4.7k -> 1.5k (D-8).
# Run once from hardware/kicad/sam_cpu. Not idempotent.
import re,uuid
f='sw_dedicated_1.kicad_sch'; t=open(f).read()
def wire(x1,y1,x2,y2):
    return f'\t(wire\n\t\t(pts\n\t\t\t(xy {x1:g} {y1:g}) (xy {x2:g} {y2:g})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n'
def label(name,x,y,rot,just):
    return f'\t(label "{name}"\n\t\t(at {x:g} {y:g} {rot})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n'
def cut_wire(t,a,b):
    m=re.search(r'\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s\) \(xy %s\)[\s\S]*?\n\t\)\n'%(re.escape(a),re.escape(b)),t); assert m,(a,b)
    return t[:m.start()]+t[m.end():]
t=cut_wire(t,'20.32 152.4','22.86 152.4')        # pin 12 off GND
t=cut_wire(t,'20.32 124.46','33.02 124.46')      # pin 1 off the R93 / R94 net
# new GND symbol, upside down above pin 1
i=t.index('(reference "#PWR07001")'); a=t.rfind('\n\t(symbol',0,i)+1
d=0
for k in range(a,len(t)):
    if t[k]=='(': d+=1
    elif t[k]==')':
        d-=1
        if d==0: e=k+2; break
g=t[a:e].replace('#PWR07001','#PWR07064')
g=re.sub(r'\(uuid "[^"]+"\)',lambda m:f'(uuid "{uuid.uuid4()}")',g)
g=g.replace('(at 22.86 152.4 0)','(at 20.32 121.92 180)').replace('(at 22.86 158.75 0)','(at 20.32 115.57 0)').replace('(at 22.86 156.21 0)','(at 20.32 118.11 0)')
add=g+wire(20.32,124.46,20.32,121.92)+wire(27.94,124.46,33.02,124.46)+label('TAMPIN',27.94,124.46,0,'left bottom')+wire(20.32,152.4,20.32,157.48)+label('TAMPIN',20.32,157.48,270,'right bottom')
j=t.index('\t(wire\n'); t=t[:j]+add+t[j:]
def setval(t,ref,old,new):
    i=t.index(f'(property "Reference" "{ref}"'); j=t.index(f'(property "Value" "{old}"',i); assert j-i<600
    return t[:j]+f'(property "Value" "{new}"'+t[j+len(f'(property "Value" "{old}"'):]
t=setval(t,'R93','1.5k','4.7k'); t=setval(t,'R117','4.7k','1.5k')
t=t.replace('"MEM_PROTECT"','"DED8"'); open(f,'w').write(t)
f='dmd_panels.kicad_sch'; t=open(f).read(); t=t.replace('"MEM_PROTECT"','"DED8"'); open(f,'w').write(t)

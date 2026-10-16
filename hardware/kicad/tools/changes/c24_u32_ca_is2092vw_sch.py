"""c24: U32 ADM2682E (out of stock at JLCPCB) -> Chipanalog CA-IS2092VW (same SOIC-16W, different pinout).
Schematic part: rewrite the embedded symbol's pins in place (same pin positions, new numbers/names/types),
drop the Y/Z wires (the CA-IS2092VW has one A and one B pin), put no-connect flags on NC (11) and SEL (10, floating
= VISO 3.3 V, required because VCC is 3.3 V)."""
import re,sys
P=sys.argv[1] if len(sys.argv)>1 else 'hardware/kicad/sam_cpu/rs485_i2s.kicad_sch'
t=open(P).read()
# old pin number -> (new number, new name, new electrical type)
MAP={'2':('1','VCC','power_in'),'7':('7','VCCL','passive'),'6':('6','DI','input'),'5':('5','DE','input'),
     '3':('3','RO','output'),'4':('4','~{RE}','input'),'1':('2','GNDA','power_in'),'8':('8','GNDA','passive'),
     '10':('16','VISO','power_in'),'15':('14','VISOIN','power_in'),'11':('11','NC','no_connect'),
     '12':('10','SEL','input'),'14':('12','A','bidirectional'),'13':('13','B','bidirectional'),
     '9':('9','GNDB','power_in'),'16':('15','GNDB','passive')}
a=t.index('\t\t(symbol "Interface_UART:ADM2682E"'); b=t.index('\n\t\t(symbol "',a+10)
lib=t[a:b]
def fix(m):
    s=m.group(0)
    num=re.search(r'\(number "([^"]+)"',s).group(1)
    nn,name,ty=MAP[num]
    s=re.sub(r'^(\t+\(pin )\w+',lambda k:k.group(1)+ty,s)
    s=re.sub(r'\(name "[^"]*"','(name "%s"'%name,s,count=1)
    s=re.sub(r'\(number "[^"]+"','(number "%s"'%nn,s,count=1)
    return s
lib2,n=re.subn(r'\t+\(pin \w+ \w+\n(?:.*\n)*?\t\t\t\t\)\n(?=\t\t\t\t\(pin |\t\t\t\))',fix,lib)
assert n==16,n
lib2=lib2.replace('ADM2682E','CA-IS2092VW').replace('Interface_UART:CA-IS2092VW','sam_cpu:CA-IS2092VW')
lib2=lib2.replace('https://www.analog.com/media/en/technical-documentation/data-sheets/ADM2682E_2687E.pdf','https://www.chipanalog.com/en/product/CA-IS2092VW')
lib2=lib2.replace('Isolated RS485/RS422 Transceiver, Integrated Isolated DC-DC Converter, 16Mbps, SOIC-16W','Isolated RS485/RS422 transceiver with integrated isolated DC-DC, 0.5 Mbps, separate logic supply, SOIC-16W')
t=t[:a]+lib2+t[b:]
t=t.replace('(lib_id "Interface_UART:ADM2682E")','(lib_id "sam_cpu:CA-IS2092VW")')
t=t.replace('(property "Value" "ADM2682E"','(property "Value" "CA-IS2092VW"')
# wires from Y (142.24,101.6) and Z (142.24,104.14) to A/B, and the junctions they needed
for w in [('142.24 101.6','143.51 101.6'),('143.51 101.6','143.51 106.68'),('142.24 104.14','144.78 104.14'),('144.78 104.14','144.78 109.22')]:
    pat=r'\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s\) \(xy %s\)\n\t\t\)\n(?:\t\t.*\n)*?\t\)\n'%tuple(re.escape(x) for x in w)
    t,k=re.subn(pat,'',t); assert k==1,(w,k)
for j in ['143.51 106.68','144.78 109.22']:
    t,k=re.subn(r'\t\(junction\n\t\t\(at %s\)\n(?:\t\t.*\n)*?\t\)\n'%re.escape(j),'',t); assert k==1,(j,k)
import uuid
nc=''.join('\t(no_connect\n\t\t(at 142.24 %s)\n\t\t(uuid "%s")\n\t)\n'%(y,uuid.uuid4()) for y in ('101.6','104.14'))
i=t.index('\t(wire\n'); t=t[:i]+nc+t[i:]
t=t.replace('ADM2682E isolated\\ntransceiver','CA-IS2092VW isolated\\ntransceiver').replace("chip's own isoPower converter (VISO)","chip's own isolated DC-DC (VISO 3.3 V, SEL open)")
open(P,'w').write(t)
print('ok')
# project symbol library holding the new symbol, so ERC finds 'sam_cpu:CA-IS2092VW'
import os
d=os.path.dirname(P)
a=t.index('\t\t(symbol "sam_cpu:CA-IS2092VW"'); b=t.index('\n\t\t(symbol "',a+10) if '\n\t\t(symbol "' in t[a+10:t.index('\n\t)\n',a)] else t.index('\n\t)\n',a)
sym=t[a:b].replace('(symbol "sam_cpu:CA-IS2092VW"','(symbol "CA-IS2092VW"')
sym='\n'.join(l[1:] if l.startswith('\t') else l for l in sym.split('\n'))
open(os.path.join(d,'sam_cpu.kicad_sym'),'w').write('(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "kicad_symbol_editor")\n\t(generator_version "10.0")\n'+sym+'\n)\n')
open(os.path.join(d,'sym-lib-table'),'w').write('(sym_lib_table\n  (version 7)\n  (lib (name "sam_cpu")(type "KiCad")(uri "${KIPRJMOD}/sam_cpu.kicad_sym")(options "")(descr "Project symbols"))\n)\n')
print('lib written')

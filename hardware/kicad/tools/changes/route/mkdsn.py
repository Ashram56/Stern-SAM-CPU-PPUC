"""Make the routing DSN: drop the GND net (it is poured), turn the fixed GND copper into keepouts."""
import re,sys
CLR=200   # um, clearance kept around ground copper
s=open(sys.argv[1]).read()
i=s.index('(net GND'); d=0
for j in range(i,len(s)):
    if s[j]=='(': d+=1
    elif s[j]==')':
        d-=1
        if d==0: break
s=s[:i]+s[j+1:]
s=re.sub(r'(\(class kicad_default[^()]*?)\sGND(\s)', r'\1\2', s)
ko=[]
lines=[]
for l in s.split('\n'):
    if '(net GND)' not in l:
        lines.append(l); continue
    m=re.search(r'\(wire \(path (\S+) (\d+)\s+(.*?)\)\(net GND\)',l)
    if m:
        ko.append('    (keepout "" (path %s %d %s))'%(m.group(1),int(m.group(2))+2*CLR,m.group(3)))
        continue
    m=re.search(r'\(via "Via\[0-1\]_(\d+):\d+_um" +(\S+) (\S+)',l)
    if m:
        dia=int(m.group(1))+2*CLR
        for ly in ('F.Cu','B.Cu'):
            ko.append('    (keepout "" (circle %s %d %s %s))'%(ly,dia,m.group(2),m.group(3)))
        continue
    raise SystemExit('unhandled GND line: '+l)
s='\n'.join(lines)
k=s.index('    (via ')
s=s[:k]+'\n'.join(ko)+'\n'+s[k:]
open(sys.argv[2],'w').write(s)
print(len(ko),'keepouts')

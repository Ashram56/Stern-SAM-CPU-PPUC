# c71: J10 pinout as the original harness: 1 L+, 2 L-, 3 R+, 4 R- (was 1 L+, 2 R+, 3 L-, 4 R-)
import sys,re; sys.path.insert(0,'/tmp/claude-0/hr')
import hr
P=hr.PCB; t=open(P).read()
i=t.index('(property "Reference" "J10"'); a=t.rfind('\n\t(footprint ',0,i); e=t.index('\n\t(footprint ',i)
fp=t[a:e]
def setnet(fp,pad,net):
    m=re.search(r'\(pad "%s" thru_hole'%pad,fp); j=fp.index('(net ',m.start()); k=fp.index(')',j)
    return fp[:j]+'(net "%s"'%net+fp[k:]
print(re.findall(r'\(pad "(\d)" thru_hole[\s\S]*?\((net [^)]*)\)',fp))
fp=setnet(fp,'2','/Audio/SPK_L_N'); fp=setnet(fp,'3','/Audio/SPK_R_P')
open(P,'w').write(t[:a]+fp+t[e:])
b=hr.Board(); b.redump()
LN='/Audio/SPK_L_N'; RP='/Audio/SPK_R_P'
ln=hr.Path(LN).at(118.96,41.18,'F').to(118.96,32.0).to(169.3,32.0).to(169.3,33.3)
rp=hr.Path(RP).at(122.92,41.18,'F').to(122.92,33.3).to(167.6,33.3).via().to(169.3,33.3).to(170.6,34.6).via().to(170.6,79.42)
dele=['eb1ca3a9-36f7-4ac7-93fc-3dfd353b0a64','fc28e66f-99c9-4d9a-9126-06c3555054c5','4f293c22-4c4a-476a-912c-7247afd45584','6916bda0-5c25-4e8f-ad84-7dfbf97b2895','4bdf044d-3ddc-4675-a6f3-06d14f5763dd']
# check against board without the deleted tracks
b.g['tracks']=[x for x in b.g['tracks'] if x['uuid'] not in dele]
import json; json.dump(b.g,open(hr.GEO,'w')); b.load()
r1=b.check(ln); r2=b.check(rp)
if not r1 and not r2 and 'go' in sys.argv:
    b.commit(ln,rp,delete=dele); hr.drc('c71')
b.view('j10e.png',(160,28,174,42),hl=(LN,RP),paths=(ln,rp),size=9)

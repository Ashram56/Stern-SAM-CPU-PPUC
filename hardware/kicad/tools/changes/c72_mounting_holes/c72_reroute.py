# c72: tracks routed across the restored mounting holes (the holes were missing from the board between c63 and c72).
# MH5: the four speaker tracks go round the 8.6 mm pad; MH11: SW_LOAD_N dips south of the hole; MH12: I2S_BCK via moved up.
import sys; sys.path.insert(0,'/tmp/claude-0/hr')
import hr
b=hr.Board()
P=lambda n,w: hr.Path(n,w=w,vd=0.8,drill=0.4) if w==1.0 else hr.Path(n,w=w)
LN=P('/Audio/SPK_L_N',1.0).at(118.96,41.18,'F').to(118.96,31.5).to(169.3,31.5).to(169.3,33.3)
RP=P('/Audio/SPK_R_P',1.0).at(122.92,33.3,'F').to(133.4,33.3).to(133.9,33.8).to(133.9,39.2).to(136.9,42.2).to(141.5,42.2).to(144.5,39.2).to(144.5,33.8).to(145.0,33.3).to(167.6,33.3)
LP=P('/Audio/SPK_L_P',1.0).at(115.0,35.5,'B').to(133.4,35.5).to(133.9,36.0).to(133.9,39.2).to(136.9,42.2).to(141.5,42.2).to(144.5,39.2).to(144.5,36.0).to(145.0,35.5).to(150.0,35.5)
RN=P('/Audio/SPK_R_N',1.0).at(126.88,36.8,'B').to(132.1,36.8).to(132.6,37.3).to(132.6,39.74).to(136.36,43.5).to(142.04,43.5).to(145.8,39.74).to(145.8,37.3).to(146.3,36.8).to(170.6,36.8)
SL=P('SW_LOAD_N',0.2).at(46.09,130.233,'B').to(87.6,130.233).to(88.767,131.4).to(90.533,131.4).to(91.7,130.233).to(107.47,130.233)
BK=P('I2S_BCK',0.2).at(146.6,120.5,'B').to(146.6,127.6).via().layer('F').to(145.727,128.473).to(145.727,128.806)
dele=['6775f2ab-2438-4bd7-9586-f246e8be53ae','7add5163-cffa-40ce-9e4c-9241c3620e08','1acdb2bd-69e9-4eaa-84f1-29e6e164a5c3',
      '0e0ac248-0f8d-4454-8293-ab43ba05add0','c4964041-357b-4a9f-a0c7-e7f8f21e0dcc','743100db-40f8-4ed7-a7ce-603573c496bc',
      '109de251-dd2f-457c-9f76-76992f944d48','8e7cd42b-4bab-4394-834c-6d11b5aa7ae8','7b0bc4d9-c0f5-4d8d-9bd9-099a78ce81fb','367aa010-688b-404c-8953-0b2979debfd9']
b.g['tracks']=[x for x in b.g['tracks'] if x['uuid'] not in dele]; b.g['vias']=[x for x in b.g['vias'] if x['uuid'] not in dele]
import json; json.dump(b.g,open(hr.GEO,'w')); b.load()
paths=(LN,RP,LP,RN,SL,BK); bad=[]
for p in paths: bad+=b.check(p)
b.view('mh5n.png',(112,29,172,46),size=20,hl=('/Audio/SPK_L_P','/Audio/SPK_L_N','/Audio/SPK_R_P','/Audio/SPK_R_N'),paths=paths)
if not bad and 'go' in sys.argv:
    b.commit(*paths,delete=dele); hr.drc('c72b')
else: b.redump()

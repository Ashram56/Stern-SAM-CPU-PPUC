from fx import *
n='LINE_DET'
p=P(n,0.2).at(156.6,108.31,'B').to(156.6,108.938); p.vias.append((156.6,108.938))
q=P(n,0.2).at(156.6,108.938,'F').to(157.228,108.938)
r=P(n,0.2).at(156.6,108.938,'F').to(156.6,115.3)
fix('LD',[p,q,r],['85e20cee','89282eb7','dac73626'])
n='/Power/EXT_12V'
dl=['9d0c67c9','a1080bcf','482c9c86','6a7753da','735e7d1d','8f9049e1']+[t['uuid'][:8] for t in b.g['tracks'] if t['net']==n and t['layer']=='B' and abs(t['x1']-144.1)<1e-3 and abs(t['y1']-55.0)<1e-3]
for vd,dr in ((0.8,0.4),(0.6,0.3)):
  for vy in (50.4,50.3,50.2,50.1,50.0):
    f=P(n,0.3,vd,dr).at(145.025,49.0,'F').to(145.025,vy-0.925).to(144.1,vy); f.vias.append((144.1,vy))
    g=P(n,0.3,vd,dr).at(144.1,vy,'B').to(144.1,55.0).to(145.4,56.3)
    if fix('EXT %s %s'%(vd,vy),[f,g],dl): break
  else: continue
  break

from fx import *
n='/Power/EXT_12V'
dl=[t['uuid'][:8] for t in b.g['tracks'] if t['net']==n and t['layer']=='B']
for x in (144.1,144.0,143.9,143.8):
    p=P(n,0.8).at(144.6,49.9,'B').to(144.6,50.4-(144.1-x)).to(x,50.9-(144.1-x)+ (144.1-x)).to(x,55.0-(144.1-x)).to(145.4,56.3)
    print(x,p.segs)
    if fix('EXT%s'%x,[p],dl): break

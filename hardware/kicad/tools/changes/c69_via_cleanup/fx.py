import hr,json
b=hr.Board()
def full(p):
    m=[t['uuid'] for t in b.g['tracks']+b.g['vias'] if t['uuid'].startswith(p)]
    assert len(m)==1,(p,m); return m[0]
def fix(name,paths,dele):
    bad=[]
    dl=[full(p) for p in dele]
    for p in paths:
        bad+=[x for x in b.check(p,quiet=True) if not any(u in x for u in dl)]
    if bad:
        print('FAIL',name); [print('   ',x) for x in bad[:8]]; return False
    b.commit(*paths,delete=dl); print('OK',name); return True
P=hr.Path

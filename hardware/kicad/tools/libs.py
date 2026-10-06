import os,copy,sys
sys.path.insert(0,os.path.dirname(__file__))
from sexp import *
SYMDIR=os.environ.get('KICAD9_SYMBOL_DIR', '/usr/share/kicad/symbols')
_cache={}
def loadlib(lib):
    if lib not in _cache:
        p=lib if lib.endswith('.kicad_sym') else os.path.join(SYMDIR,lib+'.kicad_sym')
        t=parse(open(p).read())[0]
        _cache[lib]={x[1]:x for x in find(t,'symbol')}
    return _cache[lib]
def get_symbol(lib,name,path=None):
    """Return flattened symbol sexp (list) named name (no lib prefix)."""
    L=loadlib(path or lib)
    s=copy.deepcopy(L[name])
    ext=find1(s,'extends')
    if ext:
        parent=get_symbol(lib,ext[1],path)
        props={p[1]:p for p in find(s,'property')}
        out=[Sym('symbol'),name]
        for x in parent[2:]:
            if isinstance(x,list) and x[0]=='property':
                out.append(props.pop(x[1],x))
            elif isinstance(x,list) and x[0]=='symbol':
                y=copy.deepcopy(x); y[1]=name+y[1][len(ext[1]):]; out.append(y)
            else: out.append(x)
        # insert extra props after last property
        idx=max(i for i,x in enumerate(out) if isinstance(x,list) and x[0]=='property')
        for p in props.values(): idx+=1; out.insert(idx,p)
        s=out
    return s
def pins(sym):
    """list of dicts: number,name,type,x,y,angle,unit,length,hidden"""
    res=[]
    for sub in find(sym,'symbol'):
        parts=sub[1].rsplit('_',2); unit=int(parts[1]); style=int(parts[2])
        if style>1: continue
        for p in find(sub,'pin'):
            at=find1(p,'at'); 
            hidden=any(x=='hide' for x in p) or (find1(p,'hide') is not None and find1(p,'hide')[1]=='yes')
            res.append(dict(number=find1(p,'number')[1],name=find1(p,'name')[1],type=str(p[1]),
              x=float(at[1]),y=float(at[2]),angle=int(float(at[3])),unit=unit,length=float(find1(p,'length')[1]),hidden=hidden))
    return res
if __name__=='__main__':
    lib,name=sys.argv[1],sys.argv[2]
    s=get_symbol(lib,name)
    for p in pins(s): print(p['unit'],p['number'],p['name'],p['type'],p['x'],p['y'],p['angle'],'H' if p['hidden'] else '')

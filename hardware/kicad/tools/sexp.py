import re
TOK=re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')
class Sym(str):
    pass
def parse(s):
    pos=0; stack=[[]]
    while True:
        m=TOK.match(s,pos)
        if not m or m.end()==pos: break
        pos=m.end()
        if m.group(1): stack.append([])
        elif m.group(2):
            x=stack.pop(); stack[-1].append(x)
        elif m.group(3): stack[-1].append(m.group(3)[1:-1].replace('\\"','"').replace('\\\\','\\'))
        else: stack[-1].append(Sym(m.group(4)))
    return stack[0]
def q(s): return '"'+str(s).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"'
def dump(e,ind=0):
    if isinstance(e,list):
        if not e: return '()'
        simple=all(not isinstance(x,list) for x in e)
        if simple: return '('+' '.join(dump(x) for x in e)+')'
        out='('+' '.join(dump(x) for x in e if not isinstance(x,list))
        # keep order: emit atoms then lists in order but preserve original interleaving
        out='('
        first=True
        for x in e:
            if isinstance(x,list):
                out+='\n'+'\t'*(ind+1)+dump(x,ind+1)
            else:
                out+=('' if first else ' ')+dump(x)
            first=False
        return out+'\n'+'\t'*ind+')'
    if isinstance(e,Sym): return str(e)
    if isinstance(e,(int,float)): return fmtnum(e)
    return q(e)
def fmtnum(v):
    if isinstance(v,int): return str(v)
    s=('%.4f'%v).rstrip('0').rstrip('.')
    return '0' if s in ('-0','') else s
def find(e,key):
    return [x for x in e if isinstance(x,list) and x and x[0]==key]
def find1(e,key):
    r=find(e,key); return r[0] if r else None

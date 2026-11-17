# c72: restore the nine board-only mounting-hole footprints (MH3-MH7, MH9-MH12) that c63 removed with the
# "footprints gone from the schematic" sweep. Blocks are taken verbatim from the board at 5a1ae7c~1.
# usage: python3 c72_mounting_holes.py <board with the holes (5a1ae7c~1)> <board to fix>
import re,sys
src,dst=sys.argv[1:3]
t=open(src).read(); blocks=[]
for m in re.finditer(r'\n\t\(footprint "([^"]*(?:MountingHole|Keyhole)[^"]*)"',t):
    i=m.start()+1; d=0; j=i; q=False
    while True:
        c=t[j]
        if c=='"' and t[j-1]!='\\': q=not q
        elif not q:
            if c=='(': d+=1
            elif c==')':
                d-=1
                if d==0: break
        j+=1
    blocks.append(t[i:j+1])
assert len(blocks)==9,len(blocks)
s=open(dst).read(); assert 'MountingHole' not in s and 'Keyhole_SAM' not in s
i=s.index('\n\t(footprint ')
s=s[:i]+''.join('\n'+b for b in blocks)+s[i:]
open(dst,'w').write(s); print('restored',len(blocks))

import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
hs=(89,71,137,84)   # heatsink keep-out, KiCad mm
pi=(86,126,150.65,185)  # under the Pi (face down), KiCad mm
def inter(bb,r): return not (bb[2]<=r[0] or bb[0]>=r[2] or bb[3]<=r[1] or bb[1]>=r[3])
h=[];p=[]
for f in b.GetFootprints():
    c=f.GetCourtyard(pcbnew.F_CrtYd).BBox(); bb=[c.GetLeft()/1e6,c.GetTop()/1e6,c.GetRight()/1e6,c.GetBottom()/1e6]
    r=f.GetReference(); fpn=f.GetFPIDAsString()
    if inter(bb,hs): h.append(r)
    if inter(bb,pi) and not any(k in fpn for k in ('_0402','_0603','_0805','_1206','SOIC','TSSOP','SOT','QFN','SOD','R_Array','MountingHole','PinSocket','D_SMA','D_SMB')): p.append(r+':'+fpn.split(':')[-1])
print('heatsink area:',sorted(h)); print('under Pi, not low SMD:',p)

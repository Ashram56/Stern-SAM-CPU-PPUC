# stats for a routed board: track count/length, vias, iso-area intrusions
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
iso = [b.GetArea(i) for i in range(b.GetAreaCount()) if b.GetArea(i).GetNetname()=="GND_ISO"][0]
outline = iso.Outline()
def inside(p): return outline.Contains(p)
# iso nets: every pad of the net inside the GND_ISO outline
pads = {}
for fp in b.GetFootprints():
    for p in fp.Pads():
        pads.setdefault(p.GetNetname(), []).append(inside(p.GetPosition()))
isonets = {n for n,v in pads.items() if n and all(v)}
nseg=nvia=0; L=0.0; intr={}
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA":
        nvia+=1; pts=[t.GetPosition()]
    else:
        nseg+=1; L+=t.GetLength(); s,e=t.GetStart(),t.GetEnd()
        pts=[s,e, pcbnew.VECTOR2I((s.x+e.x)//2,(s.y+e.y)//2)]
    if t.GetNetname() not in isonets and any(inside(p) for p in pts):
        intr[t.GetNetname()] = intr.get(t.GetNetname(),0)+1
print(f"segments {nseg}  vias {nvia}  track length {L/1e6:.0f} mm")
print("iso nets:", sorted(isonets))
print("non-iso copper inside the GND_ISO outline:", intr)

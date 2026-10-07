import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
z=[b.GetArea(i) for i in range(b.GetAreaCount()) if b.GetArea(i).GetNetname()=='GND_ISO'][0]
ol=z.Outline()
ISO={'GND_ISO','Net-(D27-A1)','Net-(D27-A2)','Net-(JP2-A)','Net-(U32-VISOIN)'}
bad=[];out=[]
t=b.Tracks()
for i in range(t.size()):
    x=t[i]
    pts=[x.GetPosition()] if x.Type()==pcbnew.PCB_VIA_T else [x.GetStart(),x.GetEnd()]
    ins=any(ol.Contains(p) for p in pts)
    if ins and x.GetNetname() not in ISO: bad.append(x.GetNetname())
    if not all(ol.Contains(p) for p in pts) and x.GetNetname() in ISO and x.GetNetname()!='GND_ISO': out.append(x.GetNetname())
print('non-iso copper in iso area:',bad); print('iso copper outside:',out)

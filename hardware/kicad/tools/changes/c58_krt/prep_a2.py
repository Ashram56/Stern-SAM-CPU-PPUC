import pcbnew,uuid
mm=pcbnew.FromMM
b=pcbnew.LoadBoard('out.kicad_pcb')
AUD={'AUD_DAC_L','AUD_DAC_R','AUD_AMP_L','AUD_AMP_R'}
n=0; KEEP=[]
for t in list(b.GetTracks()):
    if t.GetNetname() in AUD: KEEP.append(t); b.Remove(t); n+=1
    else: t.SetLocked(True)
for r,(x,y) in {'TP19':(156.0,110.5),'TP20':(159.0,110.5)}.items():
    [f for f in b.GetFootprints() if f.GetReference()==r][0].SetPosition(pcbnew.VECTOR2I(mm(x),mm(y)))
s=pcbnew.PCB_SHAPE(b);s.SetShape(pcbnew.SHAPE_T_POLY);s.SetLayer(pcbnew.User_2);s.SetWidth(mm(0.1))
s.GetPolyShape().NewOutline()
for x,y in [(123,126),(141,126),(141,156),(123,156)]: s.GetPolyShape().Append(mm(x),mm(y))
b.Add(s); KEEP.append(s)
b.Save('a2/in.kicad_pcb');print('removed',n)

import pcbnew,sys
pcbnew.SwigPyIterator.next=pcbnew.SwigPyIterator.__next__
P=sys.argv[1]; b=pcbnew.LoadBoard(P)
LIB='/opt/k10/root/usr/share/kicad/footprints/Package_SO.pretty'; NAME='TSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.4x9.7mm_Mask3.1x4.05mm_ThermalVias'
keep=[]
for ref in ('U23','U24'):
    old=b.FindFootprintByReference(ref)
    new=pcbnew.FootprintLoad(LIB,NAME); new.SetFPID(pcbnew.LIB_ID('Package_SO',NAME))
    b.Add(new)
    new.SetPosition(old.GetPosition()); new.SetOrientation(old.GetOrientation())
    new.SetReference(ref); new.SetValue(old.GetValue()); new.SetPath(old.GetPath()); new.SetSheetname(old.GetSheetname()); new.SetSheetfile(old.GetSheetfile())
    for f in ('Description','Datasheet'):
        try: new.SetField(f, old.GetFieldText(f))
        except Exception as e: print('field',f,e)
    new.Reference().SetPosition(old.Reference().GetPosition()); new.Value().SetPosition(old.Value().GetPosition())
    nets={p.GetNumber():(p.GetNet(),p.GetPinFunction(),p.GetPinType()) for p in old.Pads() if p.GetNumber()}
    for p in new.Pads():
        if p.GetNumber() in nets:
            n,fn,ty=nets[p.GetNumber()]; p.SetNet(n); p.SetPinFunction(fn); p.SetPinType(ty)
            if p.GetNumber()=='29' and p.GetAttribute()==pcbnew.PAD_ATTRIB_PTH: p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            if p.GetNumber()=='29' and p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD: p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    keep.append(old); b.Remove(old)
pcbnew.SaveBoard(P,b); print('ok')

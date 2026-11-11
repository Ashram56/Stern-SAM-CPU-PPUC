import sys; sys.path.insert(0,'/tmp/rv/tools'); from lib import *
b=load('/tmp/rv/s2/sam_cpu.kicad_pcb')
ref=[z for z in b.Zones() if z.GetZoneName()=='GND_TOP'][0]
z=pcbnew.ZONE(b)
z.SetLayer(pcbnew.F_Cu); z.SetNet(b.FindNet('+3V3')); z.SetZoneName('U3_TAB_3V3')
ol=z.Outline(); ol.NewOutline()
for x,y in [(94.3,49.0),(101.0,49.0),(101.0,55.0),(94.3,55.0)]: ol.Append(M(x),M(y))
z.SetAssignedPriority(2); z.SetMinThickness(ref.GetMinThickness()); z.SetLocalClearance(M(0.2))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetThermalReliefGap(ref.GetThermalReliefGap()); z.SetThermalReliefSpokeWidth(ref.GetThermalReliefSpokeWidth())
z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
b.Add(z)
for x in (98.6,99.6,100.5):
    for y in (50.0,51.0,52.0,53.8):
        if abs(x-99.245)<0.8 and abs(y-52.845)<0.8: continue
        via(b,'+3V3',x,y)
pcbnew.SaveBoard('/tmp/rv/s3/sam_cpu.kicad_pcb',b)

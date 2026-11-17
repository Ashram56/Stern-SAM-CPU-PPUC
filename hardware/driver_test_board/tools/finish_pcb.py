"""Import the Freerouting session, add the ground pours and fill them.

kpy finish_pcb.py <placed.kicad_pcb> <routed.ses> <out.kicad_pcb>
GND pour on both layers over the whole board except the USB corner; GND_USB pour in the USB corner
(x < BAR_X, y > BAR_Y, same barrier as place_pcb.py) with a 1 mm gap between the two.
"""
import sys
import pcbnew
IN, SES, OUT = sys.argv[1:4]
W, H = 250.0, 150.0
BAR_X, BAR_Y = 35.5, 128.0
GAP = 1.0
mm = pcbnew.FromMM
b = pcbnew.LoadBoard(IN)
if SES != '-':
    assert pcbnew.ImportSpecctraSES(b, SES), 'SES import failed'
def netcode(name):
    for n, ni in b.GetNetInfo().NetsByName().items():
        if str(n).split('/')[-1] == name: return ni
    raise SystemExit('no net ' + name)
def zone(net, layer, pts, prio):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer); z.SetNet(netcode(net))
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts: ol.Append(mm(x), mm(y))
    z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.4)); z.SetThermalReliefSpokeWidth(mm(0.4))
    z.SetAssignedPriority(prio)
    b.Add(z)
e = 0.3
main = [(e, e), (W - e, e), (W - e, H - e), (BAR_X + GAP / 2, H - e), (BAR_X + GAP / 2, BAR_Y - GAP / 2), (e, BAR_Y - GAP / 2)]
usb = [(e, BAR_Y + GAP / 2), (BAR_X - GAP / 2, BAR_Y + GAP / 2), (BAR_X - GAP / 2, H - e), (e, H - e)]
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    zone('GND', layer, main, 0)
    zone('GND_USB', layer, usb, 0)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(OUT, b)
print('tracks', len(b.GetTracks()), 'zones', len(b.Zones()))

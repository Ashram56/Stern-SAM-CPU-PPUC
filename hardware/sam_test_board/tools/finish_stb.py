"""Import the Freerouting session, add the ground pours and fill them.

kpy finish_pcb.py <placed.kicad_pcb> <routed.ses> <out.kicad_pcb>
GND pour on both layers over the whole board except the USB corner; GND_USB pour in the bottom-right USB corner
(x > BAR_X, y > BAR_Y, same barrier as place_stb.py) with a 1 mm gap between the two.
"""
import sys
import pcbnew
IN, SES, OUT = sys.argv[1:4]
NOZONES = '--no-zones' in sys.argv
import os
W, H = float(os.environ.get('STB_W', 165)), float(os.environ.get('STB_H', 133))
BAR_X, BAR_Y = W - 36.0, H - 22.0
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
# smaller reference designators on the small parts (dense channel columns)
for fp in b.GetFootprints():
    if fp.GetReference()[:1] in 'RCDQL' and len(list(fp.Pads())) <= 3:
        t = fp.Reference(); t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.12))
e = 0.3
main = [(e, e), (W - e, e), (W - e, BAR_Y - GAP / 2), (BAR_X - GAP / 2, BAR_Y - GAP / 2), (BAR_X - GAP / 2, H - e), (e, H - e)]
usb = [(BAR_X + GAP / 2, BAR_Y + GAP / 2), (W - e, BAR_Y + GAP / 2), (W - e, H - e), (BAR_X + GAP / 2, H - e)]
for layer in ((pcbnew.F_Cu, pcbnew.B_Cu) if not NOZONES else ()):
    zone('GND', layer, main, 0)
    zone('GND_USB', layer, usb, 0)
if not NOZONES: pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(OUT, b)
print('tracks', len(b.GetTracks()), 'zones', len(b.Zones()))

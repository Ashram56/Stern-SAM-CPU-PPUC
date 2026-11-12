"""c66b (board): U4 pin 44 (GPIO35) on AMP_PDN, C158 100 nF. Route (hand, see the board): F stub to a via at
(79.05, 58.65); In2 (79.325, 58.375) -> (84.6, 58.375) -> (84.6, 71.9) -> via (95.5, 71.9); B east to x 109.4, down to
y 84.6, east to via (113.6, 84.6); F east to the AMP_PDN via (120.6, 84.6). The In2 run crosses only slow nets
(FRAME_CS_N, SW_DATA, SWCLK, AMP_SDA / SCL, U32-DI, +5V, +1V1), no fast clock. Run with KiCad's Python."""
import pcbnew
import sys
P=sys.argv[1]
b=pcbnew.LoadBoard(P); n=b.FindNet('AMP_PDN')
u=b.FindFootprintByReference('U4')
for p in u.Pads():
    if p.GetNumber()=='44': p.SetNet(n); print('U4.44 ->',p.GetNetname())
c=b.FindFootprintByReference('C158'); c.SetValue('100nF')
for f in c.GetFields():
    if f.GetName()=='Description': f.SetText('Capacitor 100 nF 50 V X7R 0805, CC0805KRX7R9BB104 (LCSC C49678)')
b.Save(P)

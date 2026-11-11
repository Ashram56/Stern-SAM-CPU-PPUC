"""c41 (board): the USB pair copper of e6c37a8 (hand-routed in c23: U4 pins 66 / 67 straight up at the 0.4 mm pin
pitch, R13 / R14, J19 A6 / B6 and A7 / B7 joined) comes back, every piece locked, so the router doesn't have to
escape the QFN with a coupled pair (DeepPCB dropped pins 66 / 67 as unreachable). Nets renamed to the c38 names. None
of it touches the current copper (checked at 0.15 mm).
Usage: kpython c41_board_usb_pair_from_e6c37a8.py in.kicad_pcb old.kicad_pcb (e6c37a8) out.kicad_pcb"""
import sys
import pcbnew

b = pcbnew.LoadBoard(sys.argv[1]); o = pcbnew.LoadBoard(sys.argv[2])
NETS = {'Net-(J19-D+-PadA6)': '/MCU and Pi/USB_C_D+', 'Net-(J19-D--PadA7)': '/MCU and Pi/USB_C_D-',
        'Net-(U4-USB_DP)': '/MCU and Pi/USB_D+', 'Net-(U4-USB_DM)': '/MCU and Pi/USB_D-'}
nets = {str(k): v for k, v in b.GetNetInfo().NetsByName().items()}
n = 0
for t in o.Tracks():
    if t.GetNetname() not in NETS or t.Type() == pcbnew.PCB_VIA_T:
        continue
    s = pcbnew.PCB_TRACK(b); s.SetStart(t.GetStart()); s.SetEnd(t.GetEnd()); s.SetWidth(t.GetWidth())
    s.SetLayer(t.GetLayer()); s.SetNet(nets[NETS[t.GetNetname()]]); s.SetLocked(True); b.Add(s); n += 1
b.Save(sys.argv[3]); print('USB pair segments', n)

#!/bin/sh
# Pass A: the commands that produced ../sam_cpu.kicad_pcb, in order.
# KRT = a KiCadRoutingTools checkout (tested at f2704836, v0.22.1); KICAD = KiCad 10.0.6 (kicad-cli + its Python).
# B = a work directory holding a copy of ../../sam_cpu/sam_cpu.kicad_pcb and .kicad_pro from the Freerouting branch.
set -e
P="$KRT/py_router"
R="--clearance 0.15 --track-width 0.2 --via-size 0.6 --via-drill 0.3 --max-ripup 5 --escalation board --no-fix-drc-settings"
L="--layers F.Cu In1.Cu In2.Cu B.Cu --layer-costs 1.0 3.0 3.0 1.0"
copypro() { cp "$B/sam_cpu.kicad_pro" "$B/$1.kicad_pro"; }

# 0. strip every track, via and zone fill (placement, outline, zone outlines and rules kept), refill the zones
python3 strip_routing.py "$B/sam_cpu.kicad_pcb" "$B/stripped.kicad_pcb"
python3 fill_zones.py "$B/stripped.kicad_pcb" "$B/s1.kicad_pcb"; copypro s1        # KiCad's Python
# 1. RP2354B (QFN-80, 0.4 mm) escape stubs
python3 "$P/qfn_fanout.py" "$B/s1.kicad_pcb" -o "$B/s2.kicad_pcb" -c U4 --nets "*" "!GND" "!+3V3" \
  --width 0.2 --clearance 0.15 --escalation board --no-fix-drc-settings
# 2. everything, 0.1 mm grid (73 min on 4 cores): 298 / 308 nets
python3 "$P/route.py" "$B/s2.kicad_pcb" "$B/r3.kicad_pcb" --nets "*" $L $R --grid-step 0.1 \
  --power-nets GND GND_ISO "+3V3" "+4V5" "+1V1" VREF "Net-(J19-VBUS-PadA4)" "Net-(U22-AVDD)" "Net-(U4-VREG_AVDD)" "+5V" \
               "+12V" "Net-(D1-A1)" "Net-(J11-Pin_1)" "Net-(JP1-A)" "Net-(JP1-B)" "Net-(J23-Pin_1)" "Net-(J10-Pin_*)" "Net-(J24-Pin_*)" \
  --power-nets-widths 0.3 0.3 0.25 0.25 0.25 0.25 0.25 0.25 0.25 0.5 0.8 0.8 0.8 0.8 0.8 0.8 1.0 1.0
# 3. clean-up passes on a 0.05 mm grid. Before them, a keep-out polygon was added on User.2:
#    the GND_ISO zone outline grown by 2 mm (see sam_cpu.kicad_pcb, User.2).
python3 "$P/route.py" "$B/r3.kicad_pcb" "$B/r4.kicad_pcb" $L $R --grid-step 0.05 --keepout --keepout-layer User.2 \
  --nets "+1V1" "/IO bus/BD2" "/IO bus/BD4" "/IO bus/BD5" "/IO bus/BD6" "/IO bus/BD7" BUS_OE_N FRAME_MOSI "Net-(U4-USB_DP)" SW_LOAD_N "unconnected-(J21-3V3-Pad1)" \
  --power-nets "+1V1" --power-nets-widths 0.25
python3 "$P/route.py" "$B/r4.kicad_pcb" "$B/r5.kicad_pcb" $L $R --grid-step 0.05 --keepout --keepout-layer User.2 \
  --nets "+1V1" SW_LOAD_N BUS_D5 BUS_D1 FRAME_MOSI "Net-(U4-USB_DM)" --power-nets "+1V1" --power-nets-widths 0.25
python3 "$P/route.py" "$B/r5.kicad_pcb" "$B/r6.kicad_pcb" $L $R --grid-step 0.05 --keepout --keepout-layer User.2 \
  --nets STB_DATA SW_LOAD_N "Net-(U20-QC)" "Net-(U4-USB_DP)" FRAME_MOSI --force-reroute
# 4. grade with the board's own rules (original .kicad_pro), zones refilled
copypro r6
kicad-cli pcb drc --refill-zones --save-board -o drc_krt.rpt "$B/r6.kicad_pcb"

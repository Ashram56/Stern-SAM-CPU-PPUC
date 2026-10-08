#!/bin/sh
# The commands that produced ../sam_io.kicad_pcb, in order. Run inside KiCad 10.0.6's Python
# (the kicad/kicad:10.0.6 Docker image, with numpy, scipy and shapely on PYTHONPATH) so KRT can
# refill the GND pour with KiCad's own filler.
#   KRT = a KiCadRoutingTools checkout (tested at f2704836, v0.22.1, Rust core 0.22.0)
#   B   = a work directory holding a copy of ../../sam_io/sam_io.kicad_pcb and .kicad_pro
# Wall clock on 4 cores: steps 1-2 931 s, step 3 145 s, 1077 s (18 min) in all.
set -e
P="$KRT/py_router"
cd "$B"
copypro() { cp sam_io.kicad_pro "$1.kicad_pro"; }

# 0. strip every track, via and zone fill (placement, outline, GND pour outline and rules kept), refill the pour
python3 strip_routing.py sam_io.kicad_pcb stripped.kicad_pcb
python3 fill_zones.py stripped.kicad_pcb s1.kicad_pcb; copypro s1

# Common settings. 0.15 mm clearance: at 0.2 mm the RP2040's 0.4 mm pitch boxes the router in
# (11 setups at 0.2 mm all left 19-35 nets open at U3). JLCPCB's 2-layer floor is 0.10 mm.
# --escalation off: no track is ever drawn below the width asked for; power nets only neck down
# where they land on a pad (KRT's default 2.5 mm neck-down at fine-pitch pads).
R="--layers F.Cu B.Cu --layer-costs 1.0 1.0 --clearance 0.15 --track-width 0.2 --via-size 0.6 --via-drill 0.3
   --escalation off --no-fix-drc-settings --grid-step 0.05"
PWR="--power-nets GND /5V_IN +5V +3V3 /1V1 /Out_S /A /B /SHD
     --power-nets-widths 0.3 1.0 0.5 0.3 0.3 1.0 0.5 0.5 0.5"

# 1. RP2040 (QFN-56, 0.4 mm pitch) escape stubs, every net but GND (the exposed pad and pour take GND)
python3 "$P/qfn_fanout.py" s1.kicad_pcb -o s2.kicad_pcb -c U3 --nets "*" "!GND" --width 0.2 --clearance 0.15 \
  --via-size 0.6 --via-drill 0.3 --grid-step 0.05 --escalation off --no-fix-drc-settings; copypro s2
# 2. every net: 2 nets left open (+3V3, BUS_D5)
python3 "$P/route.py" s2.kicad_pcb r1.kicad_pcb --nets "*" $R $PWR; copypro r1
# 3. clean-up pass, any routed net may be ripped up: 1 net left open (+3V3 at U3 pin 22)
python3 "$P/route.py" r1.kicad_pcb r2.kicad_pcb --nets "*" $R $PWR --rip-existing-nets "*" --max-ripup 10; copypro r2

# 4. grade: Default netclass clearance set to 0.15 mm, JLCPCB 2-layer rules (sam_io.kicad_dru + board
#    setup minimums from project-files hardware/jlcpcb_rules/README.md), zones refilled
kicad-cli pcb drc --refill-zones --save-board --severity-all -o drc_krt_jlc.rpt r2.kicad_pcb

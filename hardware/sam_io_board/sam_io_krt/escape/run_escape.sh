#!/bin/sh
# run_escape.sh <out_dir> <half_box_mm> <whole_net_regex> [extra route.py args]
# Keep the original board's hand-routed RP2040 escape (and the nets named by the regex, whole), strip the rest,
# then route everything else with KRT at the board's 0.2 mm clearance. Needs KiCad 10's python3 (pcbnew) with
# numpy/scipy/shapely, and KRT=<KiCadRoutingTools checkout at f2704836 with the Rust core built>.
set -e
O=$1; H=$2; RX=$3; shift 3
HERE=$(cd "$(dirname "$0")" && pwd); ORIG=$HERE/../../sam_io
P=$KRT/py_router
mkdir -p "$O"; cd "$O"
cp "$ORIG/sam_io.kicad_pro" "$ORIG/fp-lib-table" .; cp -r "$ORIG/IO_16_8_1.pretty" . 2>/dev/null || true
python3 "$HERE/keep_escape.py" "$ORIG/sam_io.kicad_pcb" s1.kicad_pcb "$H" "$RX"
R="--layers F.Cu B.Cu --layer-costs 1.0 1.0 --clearance 0.2 --track-width 0.2 --via-size 0.6 --via-drill 0.3 --escalation off --no-fix-drc-settings --grid-step 0.05"
PWR="--power-nets GND /5V_IN +5V +3V3 /1V1 /Out_S /A /B /SHD --power-nets-widths 0.3 1.0 0.5 0.3 0.3 1.0 0.5 0.5 0.5"
for f in s1 r1 r2; do cp sam_io.kicad_pro $f.kicad_pro; done
t0=$(date +%s)
python3 $P/route.py s1.kicad_pcb r1.kicad_pcb --nets "*" $R $PWR "$@" > r1.log 2>&1
t1=$(date +%s); echo "TIME main $((t1-t0)) s"
python3 $P/route.py r1.kicad_pcb r2.kicad_pcb --nets "*" $R $PWR --rip-existing-nets "*" --max-ripup 10 "$@" > r2.log 2>&1
t2=$(date +%s); echo "TIME cleanup $((t2-t1)) s total $((t2-t0)) s"
kicad-cli pcb drc --refill-zones --severity-all -o drc.rpt r2.kicad_pcb >/dev/null 2>&1 || true
grep -E "^\[" drc.rpt | grep -v lib_footprint | sed 's/\].*/]/' | sort | uniq -c | sort -rn

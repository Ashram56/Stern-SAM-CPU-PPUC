#!/bin/bash
# Changes 06-10 on the board run.sh made: 100 x 70 mm outline, SAM bus placement and routing.
# KPY = KiCad 10 python, KICAD_CLI = KiCad 10 kicad-cli, FR = "java -jar freerouting-2.5.0.jar"
# (Java 25). Usage: run_route.sh <board.kicad_pcb>   For the record: Freerouting's result can differ
# between versions, so a rerun needs a fresh look at c09 (it fixes what the router left).
set -e
H=$(dirname "$0"); B=$1; W=$(mktemp -d)
REFS=J9,RN1,RN2,RN3,U7,U8,R27,R28,R29,R30,C30,C31,C32,C33,Q1,TP3,TP4,TP5,TP6
$KPY $H/c06_outline_placement.py $B
python3 $H/c07_trim_copper.py $B
python3 $H/c08_bus_fanout.py $B
dsn() { $KPY -c "import sys, os, pcbnew; pcbnew.ExportSpecctraDSN(pcbnew.LoadBoard('$B'), '$W/b.dsn'); os._exit(0)"; }
for CL in 250 210; do       # two passes: the second one picks up what the first left
  dsn
  python3 $H/route_mkdsn.py $W/b.dsn $W/r.dsn $CL
  $FR --gui.enabled=false --router.fanout.enabled=false --router.optimizer.enabled=false \
      -de $W/r.dsn -do $W/r.ses -mp 40
  $KPY $H/route_import.py ses $B $W/r.ses $W/s.kicad_pcb
  python3 $H/route_import.py merge $B $W/s.kicad_pcb $REFS
done
python3 $H/c09_route_fixes.py $B
$KPY $H/c10_silk.py $B
$KICAD_CLI pcb drc --refill-zones --save-board --severity-all -o $B.drc.rpt $B
rm -rf $W

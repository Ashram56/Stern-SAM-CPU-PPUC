#!/bin/bash
# Rebuild sam_io.kicad_pcb from the original IO_16_8_1 board (changes 03-05), for the record.
# KPY = KiCad 10 python, KICAD_CLI = KiCad 10 kicad-cli. Usage: run.sh <netlist.xml> <board.kicad_pcb>
set -e
H=$(dirname "$0"); NET=$1; B=$2
$KPY $H/c03_board_update.py $NET $B remove
PYTHONPATH=$H python3 $H/c04_board_clean.py $NET $B
$KPY $H/c03_board_update.py $NET $B add
$KICAD_CLI pcb drc --refill-zones --save-board --format json -o $B.drc.json $B >/dev/null
PYTHONPATH=$H python3 $H/c05_drc_via_cleanup.py $B.drc.json $B
$KICAD_CLI pcb drc --refill-zones --save-board --severity-all -o $B.drc.rpt $B
rm -f $B.pads.json $B.drc.json

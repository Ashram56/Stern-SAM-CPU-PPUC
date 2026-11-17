#!/bin/sh
# make_fab.sh <board.kicad_pcb> <outdir>: JLCPCB gerbers + drill (zip), BOM/CPL, PNG renders.
# KC = kicad-cli, KPY = python with pcbnew (KiCad 9).
set -e
B=$1; O=$2; KC=${KC:-kicad-cli}; KPY=${KPY:-python3}; T=$(dirname "$0")
mkdir -p "$O/gerbers"
$KC pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --subtract-soldermask --no-x2 -o "$O/gerbers/" "$B"
$KC pcb export drill --format excellon --drill-origin absolute --excellon-units mm --generate-map --map-format gerberx2 \
    -o "$O/gerbers/" "$B"
(cd "$O/gerbers" && rm -f ../driver_test_board-gerbers.zip && zip -q ../driver_test_board-gerbers.zip *)
$KPY "$T/jlc_bom.py" "$B" "$O"
for side in top bottom; do
  if [ $side = top ]; then L=F.Cu,F.Silkscreen,Edge.Cuts; else L=B.Cu,B.Silkscreen,Edge.Cuts; fi
  $KC pcb export pdf --layers $L ${side:+$( [ $side = bottom ] && echo --mirror )} -o "$O/$side.pdf" "$B" >/dev/null
  pdftoppm -r 150 -png -singlefile "$O/$side.pdf" "$O/driver_test_board-$side"
  rm "$O/$side.pdf"
done

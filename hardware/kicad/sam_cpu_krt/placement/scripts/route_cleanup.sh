# usage: cleanup.sh NAME IN OUT nets...
set -x
N=$1; IN=$2; OUT=$3; shift 3; D=$WORK; S=$KRT/py_router
python3 - $D/$OUT.kicad_pro <<'PY'
import json,sys
p=json.load(open('$WORK/baseline.kicad_pro')); r=p['board']['design_settings']['rules']
r.update(min_hole_to_hole=0.5,min_hole_clearance=0.26)
json.dump(p,open(sys.argv[1],'w'),indent=2)
PY
python3 -X utf8 $S/route.py $D/$IN.kicad_pcb $D/$OUT.kicad_pcb --nets "$@" \
  --layers F.Cu In1.Cu In2.Cu B.Cu --layer-costs 1.0 3.0 3.0 1.0 \
  --clearance 0.15 --track-width 0.2 --via-size 0.6 --via-drill 0.3 --escalation off --no-fix-drc-settings --hole-to-hole-clearance 0.5 \
  --max-ripup 8 --grid-step 0.05 --keepout --keepout-layer User.2 \
  --power-nets GND "Net-(U22-AVDD)" --power-nets-widths 0.3 0.25
echo CHAIN_DONE

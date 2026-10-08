# usage: chain.sh NAME  (NAME.kicad_pcb = placed board, copper-free)
set -x
N=$1; D=$WORK; S=$KRT/py_router
mkpro() { python3 - "$1" <<'PY'
import json,sys
p=json.load(open('$WORK/baseline.kicad_pro')); r=p['board']['design_settings']['rules']
r.update(min_hole_to_hole=0.5,min_hole_clearance=0.26)
json.dump(p,open(sys.argv[1],'w'),indent=2)
PY
}
kcli python3 /work/fill.py /work/pl/$N.kicad_pcb /work/pl/${N}_f.kicad_pcb; mkpro $D/${N}_f.kicad_pro
R="--clearance 0.15 --track-width 0.2 --via-size 0.6 --via-drill 0.3 --escalation off --no-fix-drc-settings --hole-to-hole-clearance 0.5"
python3 -X utf8 $S/qfn_fanout.py $D/${N}_f.kicad_pcb -o $D/${N}_fan.kicad_pcb -c U4 --nets "*" "!GND" "!+3V3" --width 0.2 --clearance 0.15 --escalation off --no-fix-drc-settings; mkpro $D/${N}_fan.kicad_pro
L="--layers F.Cu In1.Cu In2.Cu B.Cu --layer-costs 1.0 3.0 3.0 1.0"
python3 -X utf8 $S/route.py $D/${N}_fan.kicad_pcb $D/${N}_iso.kicad_pcb --nets GND_ISO "Net-(D27-A1)" "Net-(D27-A2)" "Net-(JP2-A)" "Net-(U32-VISOIN)" $L $R --max-ripup 5 --grid-step 0.1 --power-nets GND_ISO --power-nets-widths 0.3
mkpro $D/${N}_iso.kicad_pro
python3 - $D/${N}_iso.kicad_pcb $D/${N}_in.kicad_pcb <<'PY'
import uuid,sys
s=open(sys.argv[1]).read().rstrip()
pts='(xy 144.0000 182.0000) (xy 144.0000 213.4000) (xy 150.0000 213.4000) (xy 150.0000 229.5000) (xy 174.0000 229.5000) (xy 174.0000 182.0000)'
poly=f'\t(gr_poly\n\t\t(pts {pts})\n\t\t(stroke (width 0.1) (type solid))\n\t\t(fill no)\n\t\t(layer "User.2")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n'
open(sys.argv[2],'w').write(s[:-1]+poly+')\n')
PY
mkpro $D/${N}_in.kicad_pro
python3 -X utf8 $S/route.py $D/${N}_in.kicad_pcb $D/${N}_routed.kicad_pcb --nets "*" "!GND_ISO" "!Net-(D27-A1)" "!Net-(D27-A2)" "!Net-(JP2-A)" "!Net-(U32-VISOIN)" \
  $L $R --max-ripup 5 --grid-step 0.1 --keepout --keepout-layer User.2 \
  --power-nets GND "+3V3" "+4V5" "+1V1" VREF "Net-(J19-VBUS-PadA4)" "Net-(U22-AVDD)" "Net-(U4-VREG_AVDD)" "+5V" "+12V" "Net-(D1-A1)" "Net-(J11-Pin_1)" "Net-(JP1-A)" "Net-(JP1-B)" "Net-(J23-Pin_1)" "Net-(J10-Pin_*)" "Net-(J24-Pin_*)" \
  --power-nets-widths 0.3 0.25 0.25 0.25 0.25 0.25 0.25 0.25 0.5 0.8 0.8 0.8 0.8 0.8 0.8 1.0 1.0
echo CHAIN_DONE

cd "$(dirname "$0")"
python3 -X utf8 $KRT/py_router/route.py in.kicad_pcb out.kicad_pcb --nets AUD_DAC_L AUD_DAC_R AUD_AMP_L AUD_AMP_R \
 --layers F.Cu In1.Cu In2.Cu B.Cu --layer-costs 1.0 -1 -1 1.0 --clearance 0.2 --track-width 0.2 --via-size 0.6 --via-drill 0.3 \
 --escalation off --no-fix-drc-settings --hole-to-hole-clearance 0.5 --board-edge-clearance 0.3 --keep-input-copper \
 --max-ripup 5 --grid-step 0.1 --keepout --keepout-layer User.2 > krt.log 2>&1
echo DONE >> krt.log

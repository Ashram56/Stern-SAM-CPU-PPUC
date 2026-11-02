cd "$(dirname "$0")"
mapfile -t N < u4_bus_nets.txt
python3 -X utf8 $KRT/py_router/route.py fan.kicad_pcb out.kicad_pcb --nets "${N[@]}" \
 --layers F.Cu In1.Cu In2.Cu B.Cu --layer-costs 1.0 -1 -1 1.0 --clearance 0.15 --track-width 0.2 --via-size 0.6 --via-drill 0.3 \
 --escalation off --no-fix-drc-settings --hole-to-hole-clearance 0.5 --board-edge-clearance 0.3 --keep-input-copper \
 --max-ripup 5 --grid-step 0.05 --bus --ordering bus > krt.log 2>&1
echo EXIT=$? >> krt.log

"""Write driver_test_board.kicad_pro (KiCad 9) with the board rules and net classes.

python3 make_pro.py <template.kicad_pro> <out.kicad_pro>
HV  : nets tied to +50 V / +20 V / +18 V (coil, lamp strobe and lamp column lines and their LED nodes):
      0.6 mm clearance (IPC-2221 B2, 31-50 V external uncoated), 0.3 mm tracks.
PWR : +5V, GND, isolated USB supply: 0.4 mm tracks.
Default: 0.2 mm tracks, 0.15 mm clearance, 0.6/0.3 mm vias (JLCPCB standard).
"""
import json, sys, copy
d = json.load(open(sys.argv[1]))
d['meta']['filename'] = 'driver_test_board.kicad_pro'
base = d['net_settings']['classes'][0]
base.update(track_width=0.2, clearance=0.15, via_diameter=0.6, via_drill=0.3)   # 0.4 mm QFN pitch
hv = copy.deepcopy(base); hv.update(name='HV', track_width=0.3, clearance=0.6, via_diameter=0.7, via_drill=0.35, priority=0)
pw = copy.deepcopy(base); pw.update(name='PWR', track_width=0.4, clearance=0.2, via_diameter=0.7, via_drill=0.35, priority=1)
d['net_settings']['classes'] = [base, hv, pw]
pats = []
for p in ['V50', 'V20S', 'V20F', 'V18L', 'COIL*', 'LA_COIL*', 'LSTB*', 'LA_LSTB*', 'LCOL*', 'LA_LCOL*', 'J13P*']:
    pats += [{'netclass': 'HV', 'pattern': p}, {'netclass': 'HV', 'pattern': '*/' + p}]
for p in ['GND', '+5V', 'VBUS*', 'VDD1', 'VDD2', 'GND_USB']:   # +3V3 / +1V1 reach 0.4 mm QFN pads: default width
    pats += [{'netclass': 'PWR', 'pattern': p}, {'netclass': 'PWR', 'pattern': '*/' + p}]
d['net_settings']['netclass_patterns'] = pats
r = d['board']['design_settings']['rules']
r.update(min_clearance=0.2, min_track_width=0.2, min_via_diameter=0.5, min_through_hole_diameter=0.3,
         min_hole_clearance=0.25, min_copper_edge_clearance=0.3, min_resolved_spokes=1)
json.dump(d, open(sys.argv[2], 'w'), indent=2)

import json,sys
p=json.load(open(sys.argv[1])); r=p['board']['design_settings']['rules']
r.update(min_clearance=0.09,min_track_width=0.09,min_via_annular_width=0.05,min_via_diameter=0.25,min_through_hole_diameter=0.15,min_hole_to_hole=0.2,min_copper_edge_clearance=0.3)
json.dump(p,open(sys.argv[2],'w'),indent=2)
print({k:r.get(k) for k in ('min_hole_clearance','min_clearance','min_hole_to_hole')})

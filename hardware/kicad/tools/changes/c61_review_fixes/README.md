# c61: fixes from the full review of 74ed0bb

Scripts run in order with KiCad 10.0.6 pcbnew (s1 .. s9), each checked with `kicad-cli pcb drc --refill-zones`
against the previous step: no new error at any step.

- s1: 12V_OR, 0.3 mm U34 SENSE track replaced by a 1.0 mm leg at x 141.0 (Q19/Q20 source bar to the 0.8 mm trunk).
  IO_12V: tapered B.Cu neck (0.2 to 0.68 mm) at (137.6, 52.7) widened to 0.8 mm.
- s2: 39 vias on the 12 V and 5 V power nets from 0.6/0.3 to 0.8/0.4 (skipvias.json: those that did not fit).
- s3: zone U3_TAB_3V3 (+3V3, F.Cu, priority 2, solid connection) under the U3 tab, 11 vias +3V3 to In2.
- s4/s5: GND stitching vias on F.Cu/B.Cu GND islands held by one via (pick.py, newvias.json), plus
  6 near the TPS54302 input and output caps (pick2.py, newvias2.json). J2.12 no longer on an isolated island.
- s6: dangling stubs and vias removed (J24-Pin_2 overlapping 19.9 mm segment, J10-Pin_2, SW_DATA overshoot,
  +5V micro-segments near (98.5, 63), vias J10-Pin_3 and BUS_IOSTB).
- s7: 55 off-angle segments split into 45/90 doglegs where clearance allowed (ang.py, angfix.json).
- s8: reference texts: size 1.0 / 0.15 mm, moved off pads and the board edge where room exists.
- s9: footprint fields (Description, Datasheet, MPN) copied from the schematic; TP1-TP22 and JP1 set
  "exclude from BOM" in the schematic like the board. Schematic parity 222 -> 0.

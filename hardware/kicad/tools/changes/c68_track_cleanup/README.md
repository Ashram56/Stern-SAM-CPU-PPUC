# c68: track cleanup over the whole board (2026-11-12)

Record of the scripts used on 286546b to remove odd routing that was electrically fine. They run on a working copy
with the hand-routing checker (`hr.py`, `dump.py`, see `hardware/kicad/README.md`) and are kept as a record, with
the paths of that session.

- `det.py`, `det2.py`: detectors (segments under 0.1 mm, segments off 0/45/90, acute corners, double-backs,
  detours, staircases, stubs).
- `simp.py`, `simp2.py`: replace a staircase between two junctions, pads or vias by a path of at most three
  0/45/90 segments when the clearance check passes. Nothing is moved to a new corridor, no via is added or moved.
- `fx.py`, `f1.py` to `f4.py`: the hand fixes (acute corners, double-back, off-45 segments, EXT_12V snake).
- `loc.py`: lists the tracks, vias and pads of a net around a point.

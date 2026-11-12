# c69: vias and layer changes cleanup (2026-11-12)

Second pass after c68, on cf7c7b3. Same conventions as `../c68_track_cleanup/` (session paths, `hr.py` checker).

- `det3.py`: finds vias where a track arrives and leaves again at less than 90 degrees ("via hook"), and chains
  that go beyond their two ends before coming back ("overshoot").
- `vh.py`: slides such a via along one of its tracks and redraws the others, when the clearance check passes.
- `vc.py`: replaces a piece of chain that changes layer and comes back by a single-layer path of at most two
  segments, and removes the vias it no longer needs. Guards: nets with a zone (GND, +3V3, GND_ISO) are never
  touched, nothing else of the net may touch the removed pieces (track end, track passing over a removed corner,
  via, pad), the ISO_GAP_2MM rule area is avoided.
- `inv.py`: removes segments lying entirely inside a via of their net. `dv2.py`: removes vias the DRC reports as
  connected on one layer only. `g1.py`, `g2.py`: hand fixes (LINE_DET via, EXT_12V, J11_5V).

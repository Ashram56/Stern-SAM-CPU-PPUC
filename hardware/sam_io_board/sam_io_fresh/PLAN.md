# SAM_IO fresh placement and 2-layer routing: job plan

Requested by Vincent on 2026-10-08. Runs entirely on his WSL machine (KiCad 10.0.6 native, KiCadRoutingTools
built in `~/krt_work/KiCadRoutingTools`, 8 cores). The cloud thread only coordinates and shares files.

## Goal

A complete, manufacturable **2-layer** SAM_IO board: 100 % routed, zero DRC errors against the JLCPCB 2-layer
rules, placed **from scratch**.

## Hard constraints

- **Input:** `../sam_io/sam_io.kicad_sch` and `../sam_io/sam_io.kicad_pcb` at commit `6a4a5f8` (QWIIC parts J2, R96,
  R97, C8 removed, R9 replaced by a wire). Use the board only for its footprints and netlist. **Do not reuse its
  placement, its routing, or anything from `../sam_io_krt/`** (earlier experiments; Vincent asked for a clean start).
- **Envelope: the PPUC IO_16_8_1 board, 100 x 100 mm.** In the board's coordinates the outline is
  x 75..175, y 39..139 (from `../original/IO_16_8_1.kicad_pcb`). Nothing may go outside it.
- **Mounting holes** (MountingHole_5.5mm_Pinball) at the PPUC positions: (80, 44), (170, 44), (80, 134), (170, 134).
- **Top-edge connectors at their PPUC IO_16_8_1 positions**, so the board drops in where a PPUC IO board goes:
  J1 power terminal (108.318, 43.5, 180 deg), J5 terminal (159.75, 43.5, 180 deg), J4 USB-C (130.81, 43.18, 180 deg).
  This is the default chosen for this job; everything else is free.
- **2 copper layers**, all parts on F.Cu (single-sided assembly).
- **Widths (minimums, no neck-down allowed except where a track enters a fine-pitch pad):**
  `/5V_IN`, `/Out_S` 1.0 mm; `+5V`, RS485 `/A`, `/B` 0.5 mm; `+3V3`, `/1V1`, GND 0.3 mm; signals 0.2 mm.
- **Clearance:** 0.2 mm (the board's Default netclass). A variant at 0.15 mm is allowed as a fallback and must be
  reported as such. Never below 0.15 mm.
- **Vias:** 0.6 mm pad / 0.3 mm drill (no JLC surcharge).
- **Rules:** copy `rules/jlcpcb_2layer.kicad_dru` next to every board as `<name>.kicad_dru` and set the board setup
  minimums from `rules/README.md` ("Board setup minimums", 2-layer column).
- **GND pour** on both layers, poured after routing.

## Phase 0: baseline

1. Copy the input board to `work/baseline.kicad_pcb`. Strip all tracks, vias and zone fills.
2. Record in `metrics.csv`: total airwire length, airwire crossings, parts area / board area.

## Phase 1: constraints (`placement_constraints.yaml`)

- Fixed: the 4 holes, J1, J5, J4 (above).
- Edge parts: J9 (SAM bus 2x10 IDC) on an edge with the cable exiting off-board. SW3 (ADDRESS DIP), JP1-JP3,
  SW1 (Reset), SW2 (Boot), D3 (LED) and J3 (SWD debug header, not mounted) reachable from the top.
- Functional groups, each with a region (derive the exact members from the schematic nets, not from the old
  placement): RP2040 U3 + crystal Y1 + its decoupling; QSPI flash U2; USB J4 + D6 and series resistors;
  power input and 3.3 V regulation (J1/J5 power pins, D5, D4, D16, U6 AP2112K and caps); RS485 (U1 ADM3483,
  D1/D2 SD15, termination); special output (U4 LMV321, Q1, U5, `/Out_S`); SAM bus buffers U7/U8 next to J9;
  config (SW3, JP1-JP3); user I/O (SW1, SW2, D3); test points TP*.
- Proximity: each decoupling cap within 2-3 mm of the pin it serves; Y1 and its load caps next to U3's XIN/XOUT
  with no via under Y1; regulator caps next to the regulator; pull-ups/series resistors next to their pin.
- Keep-outs: around holes and connector bodies. Leave room around U3 for its escape on two layers.
- Orientation: passives in a group aligned the same way; polarised parts consistent.

## Phase 2: placement

Generate **3 to 5 candidates** (scripted with pcbnew; any optimiser is fine as long as the constraints hold).
Snap passives to 0.25 mm, connectors to 1.27 mm. Zero courtyard overlaps. Score each: airwire length, crossings,
proximity violations. Render each (`kicad-cli pcb export svg` front + back, converted to PNG). Keep the best 2-3.

## Phase 3: routing (KiCadRoutingTools, in parallel)

On copper-free copies of the kept candidates. Order: power nets first with their widths, then U3 escape / bus /
flash, then the rest. Run several variants at once (different candidates, grid steps, rip-up limits, 0.2 vs
0.15 mm clearance), at most 7 jobs at a time. Then pour GND on both layers and run:

```
kicad-cli pcb drc --refill-zones --severity-all --format json -o drc.json board.kicad_pcb
```

Record per variant: unconnected, clearance errors, all other errors, via count, track length, run time.

## Phase 4: deliver

- Best board as `sam_io_fresh/sam_io.kicad_pcb` (+ `.kicad_pro`, `.kicad_dru`, `fp-lib-table`, `IO_16_8_1.pretty`
  copied from `../sam_io/`), its DRC report, renders (F.Cu, B.Cu, combined), `metrics.csv`, the scripts used and a
  short `README.md` (metrics baseline -> placement -> routing, what won and why, anything still open).
- Push to branch `claude/project-thread-bvwo0x` only.

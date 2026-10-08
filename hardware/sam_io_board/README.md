# SAM_IO board: PPUC IO board for the Stern SAM IO power driver board

A PPUC IO board (RP2040 on RS485) that drives a Stern SAM IO power driver board (520-5249-00) through its
CPU connector J1. It is the hardware for the `SAM_IO` board type (`PPUC_BOARD_TYPE=5`) in the io-boards
firmware (Ashram56/io-boards PR #1, `src/IODevices/SamBus/`): one board forwards every coil, flasher and lamp
of the machine to the SAM IO board's registers. It has no switch inputs and no output stage of its own.

It is derived from the PPUC **IO_16_8_1** board, version 1.1.1, by foenich
(<https://github.com/PPUC/Hardware_IO_16_8_1>, commit `46e0c47`), licensed under the
**TAPR Open Hardware License 1.0**. See [Licence](#licence-and-change-notice) below.

- [`DESIGN.md`](DESIGN.md): detailed design notes (circuit, power, reset, bus timing, signal list, BOM, PCB,
  manufacturing, bring-up).
- `sam_io/`: the KiCad 10 project (10.0 file format). Open `sam_io.kicad_pro`.
- `sam_io_krt/`: an experiment, the same board stripped and routed again from scratch with KiCadRoutingTools,
  with a side-by-side comparison. Not the board to build.
- `sam_io/sam_io_bom.csv`: bill of materials, grouped by value and footprint.
- `sam_io/sam_io.pdf`: the two schematic sheets, for reading without KiCad.
- `sam_io/pcb_render.png`: top view of the routed board; `sam_io/pcb_copper.png`: its copper (F.Cu red, B.Cu blue).
- `original/`: the unmodified IO_16_8_1 v1.1.1 files this design was made from (KiCad 6), its PDF schematic,
  README and change log.
- `tools/`: the scripts that made the changes, for the record (see the end of this file). From now on the
  KiCad files are the source of truth: edit them in KiCad.

## What changed from IO_16_8_1

| | IO_16_8_1 | SAM_IO |
|---|---|---|
| High-power outputs (sheet OUT8) | 8 MOSFET outputs, flyback diodes, F2, 3300 µF C56, J9-J11 | **removed** |
| Inputs (sheet IN16) | 16 inputs with 2N7002 level shifters, J6-J8 | **removed**: GPIO3-18 are the SAM bus |
| SAM bus (new sheet "SAM bus") | | J9 2x10 header, SN74LVC8T245, 74AHCT541, 2N7002 for NBRESET |
| RP2040, flash, crystal, USB-C J4, SWD J3, reset / boot buttons | | unchanged |
| RS485 (ADM3483, J1, JP1-JP3 bias / termination), QWIIC J2 | | unchanged |
| Power J5 (5 V in), AP2112 3.3 V, address DIP SW3 + ladder on GPIO28, LED on GPIO25 | | unchanged |
| Special output (GPIO29 through SN74AHCT1G125 to J5 pin 5) | | unchanged (the SAM_IO firmware does not use it) |

Every part that stays keeps its reference, its position on the board and its routing.

The board is **100 x 70 mm**, the size of the PPUC Opto_16 board (99.7 x 67.3 mm) plus 2.7 mm, because the
address DIP switch SW3 sits that low on IO_16_8_1. The lower 30 mm of IO_16_8_1 held only the output stage.
The four 5.5 mm mounting holes stay at the corners, 5 mm from the edges (the top two did not move, the
bottom two moved up to y = 104 mm). They are not Opto_16's hole pattern.

## Connectors

The kept connectors are the same parts as on IO_16_8_1:

| Ref | Part | Use |
|---|---|---|
| J1 | 6-way RTM push-in terminal | RS485: 1 A, 2 B, 3 SHD, 4 A, 5 B, 6 GND (unchanged) |
| J5 | 6-way RTM push-in terminal | 1, 3, 4 = +5 V in, 2, 6 = GND, 5 = special output (unchanged) |
| J4 | USB-C | programming and debug |
| J3 | 1x3 2.54 mm (not fitted) | SWD |
| J2 | JST SH 4-way (not fitted) | QWIIC |
| **J9** | **2x10 2.54 mm shrouded IDC header** | **SAM bus to the SAM IO board J1** |

J9 is the only new connector. It has the SAM IO board J1 pinout pin for pin, the same as J9 on the SAM CPU
replacement board, so a straight 20-way IDC ribbon (pin 1 to pin 1) connects the two:

| J9 pin | Signal | J9 pin | Signal |
|---|---|---|---|
| 1 | D3 | 2 | D4 |
| 3 | D2 | 4 | D5 |
| 5 | D1 | 6 | D6 |
| 7 | D0 | 8 | D7 |
| 9 | n.c. | 10 | n.c. |
| 11 | n.c. | 12 | A0 |
| 13 | NBRESET (open drain, active low) | 14 | A1 |
| 15 | IOSTB (active low) | 16 | A2 |
| 17 | n.c. | 18 | A3 |
| 19 | GND | 20 | GND |

The SAM IO board's J1 carries no supply, so this board is powered from J5 like every PPUC board.

## SAM bus circuit and GPIO map

The "SAM bus" sheet is a copy of the IO bus sheet of the SAM CPU replacement board
(`hardware/kicad/sam_cpu/io_bus.kicad_sch`, docs/ARCHITECTURE.md 3.1-3.2), so both boards that can drive a
SAM IO board use the same circuit:

- D0-D7: SN74LVC8T245 (U7), A side 3.3 V, B side 5 V. DIR comes from the firmware (1 = this board drives J9),
  10 k pull-down (R28).
- A0-A3 and IOSTB: 74AHCT541 (U8) at 5 V, TTL inputs. Unused inputs tied low.
- Both buffers share BUS_OE_N with a 10 k pull-up (R27): off at power-up, so the SAM IO board's own pull-ups
  hold IOSTB high and nothing latches while the RP2040 boots.
- NBRESET: 2N7002 (Q1) open drain against the SAM IO board's 10 k pull-up. Its gate has a 10 k pull-up (R30),
  so the SAM IO board is held in reset (all outputs off) until the firmware lets go.
- 33 R in series on every J9 line (RN1-RN3, R29), for the ribbon cable.
- Test points TP3 IOSTB, TP4 NBRESET, TP5 D0, TP6 A0.

The GPIOs match `src/IODevices/SamBus/SamBusPins.h` in io-boards exactly, so the firmware needs no change:

| GPIO | Signal | GPIO | Signal |
|---|---|---|---|
| 0, 1, 2 | RS485 TX, RX, DE (unchanged) | 15 | BUS_IOSTB |
| 3-10 | BUS_D0-D7 | 16 | BUS_DIR |
| 11-14 | BUS_A0-A3 | 17 | BUS_OE_N (low = buffers on) |
| 25 | status LED (unchanged) | 18 | NBRESET_DRV (high = SAM IO board in reset) |
| 28 | board id ladder, DIP SW3 (unchanged) | 29 | special output (unchanged) |
| 19-24, 26, 27 | not connected (were Out_1-Out_8) | | |

## Checks

- ERC (KiCad 10.0.6): 2 errors and 9 warnings, all inherited from IO_16_8_1 (ADC_AVDD and +5 V power-flag
  warnings, +5 V / VCC net name on U5, library symbols that differ from the KiCad 10 libraries). Nothing on the
  new sheet.
- The netlist was compared pin by pin with the original: every kept part keeps its nets, except the RP2040
  GPIO3-18 (now the bus) and GPIO19-24, 26, 27 (now unconnected).
- DRC: fully routed (no unconnected item), no new violation. The remaining items are the original's (USB-C J4
  pad to slot clearance, J2 / C8 courtyards, starved thermals on J4, U5 and C8, footprints that differ from the
  KiCad 10 libraries). Design rules are unchanged: 0.2 mm tracks and clearance, 0.5 / 0.3 mm vias.
- Schematic parity: no net differences. KiCad lists field differences (datasheet links, test point BOM flag)
  that one "Update PCB from Schematic" in KiCad clears.

## Open points

Nothing below blocks reviewing the design; the first group blocks ordering boards, the rest is to check on the
bench or to tidy up later. [DESIGN.md](DESIGN.md) has the details behind each one.

Before ordering:

- **Fabrication files**: no Gerbers, drill files or pick-and-place file yet. Generate them from KiCad (or
  `kicad-cli pcb export gerbers / drill / pos`) once the points below are settled.
- **Update PCB from Schematic**: run it once in KiCad to clear the remaining field differences (datasheet links,
  test point BOM flag). No net changes are expected; re-run DRC afterwards.
- **C31 via in pad**: there was no room for a GND via beside C31 (U7's 5 V decoupling), so its GND pad has
  one. Ask the fab for a filled or tented via, or check the solder joint.
- **Mounting holes**: the four corner holes of the 100 x 70 mm outline follow neither IO_16_8_1 nor Opto_16.
  Check where the board will sit in the machine (or on the SAM IO board's ribbon) and move them if needed.
- **Parts availability**: check stock for the new parts (SN74LVC8T245 in TSSOP-24, 74AHCT541 in TSSOP-20, 2N7002,
  4 x 33 R arrays, 2 x 10 IDC header) at the assembler; the BOM is `sam_io/sam_io_bom.csv`.

On the bench:

- **Bus timing against a real SAM IO board** (ARCHITECTURE.md Q4): setup, IOSTB width and hold as set by the
  firmware (140 / 175 / 245 ns), the STATUS read turnaround (DIR flip and U7 delay inside the read window),
  and edge quality on the 22 pF lines through the series resistors.
- **Watchdog and reset**: the SAM IO board must stay in reset while the RP2040 boots and come out of it only
  once lamp strobes run (DRV0 within 62.5-250 ms); NBRESET held low long enough for the DS1232 (about 20 ms).
- **Ribbon**: the 20-way cable carries only two GND wires; keep it short, check pin-1 orientation on both ends
  and the ground return under full lamp load.
- **5 V supply**: confirm which 5 V the board takes in the machine and that its ground is shared with the SAM
  IO board's logic ground.
- **Firmware**: the `SAM_IO` board type is in Ashram56/io-boards PR #1, still open. Board type `0x05` is a
  proposal to agree with PPUC upstream.

Later, if wanted:

- **References reused**: J9, Q1, R27-R30 and C30-C33 were IO_16_8_1 input / output parts and are now SAM bus
  parts (matching the CPU board's J9). Compare with `original/` by function, not by reference. A re-annotation
  would remove the confusion but break the comparison.
- **Spare resources**: RP2040 GPIO19-24, 26, 27 are unconnected and U8 has three unused channels (inputs tied
  to GND). They could carry the 20 V / 50 V interlock inputs or GI relay control later.
- **Library footprints**: several footprints inherited from IO_16_8_1 differ from the KiCad 10 libraries (DRC
  warnings only). Update them from the library if the board is reworked.
- **Copper tidy-up**: a few short GND tracks between stitching vias on B.Cu are left from IO_16_8_1's routing;
  harmless inside the pour, removable.

## Routing

Two layers, as on IO_16_8_1. The parts that stayed keep their routing; the SAM bus parts sit on the left, where
the input stage was:

- J9 on the left edge, RN1-RN3 and R29 next to it, then U7 (data) above U8 (address and IOSTB), close to the
  RP2040.
- RP2040 to buffers, routed by hand (`tools/c08_bus_fanout.py`). The RP2040 and both buffers number their pins
  anticlockwise, so a bus that keeps its bit order between them has to cross itself once. Each of the 13 lines
  leaves the RP2040 on the top layer (reusing IO_16_8_1's GPIO fanout next to the chip), drops through a via
  under its own buffer pin and crosses under the others on the bottom layer, then comes back up to the pin:
  two vias per line. DIR, OE_N and NBRESET_DRV reuse IO_16_8_1's GPIO16-18 fanout down the right of the RP2040.
- Buffers to J9, pull-ups and power: Freerouting 2.5, with every existing track locked, then a few touch-ups
  (`tools/c09_route_fixes.py`).
- GND is the pour on both layers, as before.

## Licence and change notice

This design is a modification of PPUC IO_16_8_1 v1.1.1 by foenich and is licensed, like the original, under the
**TAPR Open Hardware License 1.0** ([`LICENSE-TAPR-OHL.txt`](LICENSE-TAPR-OHL.txt), an unaltered copy). It is
not covered by the repository's CERN-OHL-S licence. The modifications are licensed under the terms of the TAPR
OHL.

Elements changed (TAPR OHL 4.2a):
- `IO_16_8_1.kicad_sch` -> `sam_io/sam_io.kicad_sch`: IN16 and OUT8 sheets and their labels removed; GPIO3-18
  labels renamed to the SAM bus global labels; no-connect flags on GPIO19-24, 26, 27; "SAM bus" sheet added;
  title block and a change note; file upgraded to KiCad 10.
- `IN16.kicad_sch`, `OUT8.kicad_sch`: removed.
- `sam_io/sam_bus.kicad_sch`: new (from the SAM CPU replacement board's IO bus sheet).
- `IO_16_8_1.kicad_pcb` -> `sam_io/sam_io.kicad_pcb`: IN16 / OUT8 footprints, their tracks and vias, the GNDPWR
  zone and the J6-J11 / fuse silkscreen removed; GND zone extended over the freed area; board name changed to
  "PPUC SAM_IO"; SAM bus parts added and routed; outline cut to 100 x 70 mm, bottom mounting holes, logo and
  board name moved up, copper below the new edge removed; file upgraded to KiCad 10.
- `IO_16_8_1.kicad_pro` -> `sam_io/sam_io.kicad_pro`: renamed, upgraded to KiCad 10.
- `logo.kicad_sym`, `IO_16_8_1.pretty`, `fp-lib-table`, `sym-lib-table`, `PPUC-Logo-PCB-230129.svg`: unchanged.

The original versions of the changed files are in `original/` (TAPR OHL 4.2b). The original documentation names
no licensor e-mail address, so section 3 asks nothing further. Before boards are made, add the Gerber and drill
files to this folder (TAPR OHL 4.2d).

## How the changes were made

`tools/c01_root_sheet.py` and `tools/c02_sam_bus_sheet.py` edited the schematic sheets.
`tools/run.sh` rebuilt the board from the original with `c03_board_update.py` (remove / add footprints, KiCad 10
Python), `c04_board_clean.py` (tracks, zones and silkscreen, on the file text) and `c05_drc_via_cleanup.py`
(leftover vias reported by DRC). `tools/run_route.sh` then made the 100 x 70 mm outline and the routing:
`c06_outline_placement.py` (outline, holes, placement), `c07_trim_copper.py` (copper below the new edge),
`c08_bus_fanout.py` (RP2040 side of the bus), two Freerouting passes (`route_mkdsn.py`, `route_import.py`),
`c09_route_fixes.py` and `c10_silk.py`. Do not rerun them over the current files.

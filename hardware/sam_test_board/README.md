# SAM universal test board (carte de test universelle, 48 voies)

One small board, made four times (JLCPCB batch of 5: one spare), that replaces the playfield and switch harnesses so
the new CPU board and the I/O Power Driver board 520-5249-00 can be tested with nothing at risk. Chosen by Vincent on
2026-11-18 instead of the single 250 x 150 mm board of `../driver_test_board/` (draft 0.1, abandoned).

## One channel (× 48)

Each pin of the four KK-396 12-pin headers A-D is a universal channel:

- **Load and indicator**: header common COMx → 33 k → red LED → pin, green LED back in parallel. With COMx on a rail,
  a low-side output that turns on lights red (about 1.4 mA at 50 V, 0.5 mA at 20 V); with COMx on GND, an output
  that drives high lights green. A 3-pad solder jumper per header (JP1-JP4) puts COMx on RAILx (J5), on GND, or
  leaves it open (switch simulation, sense only).
- **Sense**: 100 k / 220 k (header A: 22 k / 47 k) into a 74HC165 input, whose clamp diode holds the node at 3.3 V
  up to 50 V (0.46 mA, header A 2.1 mA). 3 × 220 R load the 3.3 V rail (45 mA) so the clamp current cannot lift it.
  Header A also goes straight to GPIO8-19: fast enough for the 300 ns aux strobes and the CPU switch strobes.
- **Drive**: BSS123 (100 V, 170 mA) from pin to ground, gate from a 74HCT595 chain (100 k pull-down), to close a
  simulated switch.

## Roles

Same board and firmware, role set by the JP9/JP10 solder jumpers. Cables are straight: pin n of the SAM connector on
pin n of the header (a 9 or 10 way housing plugs on pins 1-9 / 1-10).

| role | JP9 / JP10 | A | B | C | D | commons |
|---|---|---|---|---|---|---|
| coils | open / open | IO J8 (1-8) | IO J9 (9-16) | IO J7 (17-24) | IO J6 (25-32) | A, B on +50 V, C, D on +20 V (J5) |
| lamps + aux | closed / open | IO J3 (aux strobes 9-12) | IO J12 (lamp strobes) | IO J13 (lamp columns) | IO J2 (aux data) | per the output type, see below |
| switch matrix | open / closed | CPU J1 (strobes) | CPU J6 (returns 1-8) | CPU J12 (returns 9-16) | CPU J2 (D-1..D-8) | open |
| dedicated | closed / closed | CPU J3 (D-9..D-16) | CPU J13 (D-17..D-24) | free | free | open |

Coil outputs have a 1N4004 flyback diode to their rail on the driver board: the rails must be on (J5 RAILx and the
driver board), otherwise every output reads ON through its diode. For the lamp board, an output that pulls low needs
its header common on the matching rail (red LED), one that drives high needs the common on GND (green LED); +18 V
also arrives on J13 pin 9, so channel C9 reads high (check the J13 9/10 swap on your IO board).

## Files

- `kicad/`: KiCad 9 schematic draft 0.1 (ERC 0, `kicad/erc.rpt`), PCB `sam_test_board.kicad_pcb` (DRC `kicad/drc.rpt`).
- `sam_test_board_schematic_v0.1.pdf`
- `fab/`: JLCPCB BOM and CPL, renders (gerbers with `tools/make_fab.sh`).
- `firmware/`: RP2354B firmware (Pico SDK 2.2), see its README. `pc/stb_probe.py`: PC tool for one or several boards.
- `tools/`: `place_stb.py` (placement from the netlist), `make_pro.py` (net classes), `finish_stb.py` (Freerouting
  session import, GND / GND_USB pours), `jlc_bom.py`, `jlc_rotcheck.py`, `make_fab.sh`. The schematic generator is
  `../driver_test_board/tools/design_stb.py` (`build_dtb.py design_stb <outdir>`, it shares kigen with the large board).
  From now on edit the KiCad files directly; the generators are the record of how the draft was made.

## PCB (draft 0.1)

- 165 x 133 mm, 2 layers, 1.6 mm, every part on the top side (single-sided JLCPCB assembly). Four M3 holes in the
  corners (H1 = ground lug with pad).
- Headers A, B on the top edge, C, D on the bottom edge, J5 (rails + GND) top right, USB-C bottom right. KK-396
  friction ramps face inward.
- One column per channel facing its pin (red, green LED, 33 k, BSS123, 100 k gate, sense divider), 1.5 mm between
  courtyards; the 74HC165 / 74HCT595 in a strip across the middle under the channels they serve; RP2354B on the right.
- Net classes: HV (header pins, LED nodes, commons, rails): 0.6 mm clearance (IPC-2221 B2, 31-50 V), 0.3 mm tracks.
  Default 0.2 / 0.15 mm (0.4 mm pitch QFN). Power 0.4 mm.
- Isolation: GND_USB (PC side) in the bottom-right corner (x > 129 mm, y > 111 mm), a 0.5 mm strip with no copper
  separates it from GND; only U3 (ADuM3160) and PS1 (B0505S) straddle it.

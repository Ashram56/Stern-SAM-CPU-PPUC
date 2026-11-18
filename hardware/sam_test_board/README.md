# SAM universal test board (carte de test universelle, 48 voies)

One small board, made four times (JLCPCB batch of 5: one spare), that replaces the playfield and switch harnesses so
the new CPU board and the I/O Power Driver board 520-5249-00 can be tested with nothing at risk. Chosen by Vincent on
2026-11-18 instead of the single 250 x 150 mm board of `../driver_test_board/` (draft 0.1, abandoned).

## One channel (× 48)

Each pin of the four KK-396 12-pin headers A-D is a universal channel:

- **Load and indicator**: header common COMx → 33 k (0.5 W) → red LED → pin, green LED back in parallel. With COMx on a rail,
  a low-side output that turns on lights red (about 1.4 mA at 50 V, 0.5 mA at 20 V); with COMx on GND, an output
  that drives high lights green. A 3-pad solder jumper per header (JP1-JP4) puts COMx on RAILx (J5), on GND, or
  leaves it open (switch simulation, sense only).
- **Sense**: 100 k / 220 k (header A: 22 k 0.5 W / 47 k) into a 74HC165 input, whose clamp diode holds the node at 3.3 V
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

- `kicad/`: KiCad 9 schematic 0.2 (ERC 0, `kicad/erc.rpt`), PCB `sam_test_board.kicad_pcb` (DRC `kicad/drc.rpt`),
  project footprint library `sam_test_board.pretty` (PS1).
- `sam_test_board_schematic_v0.2.pdf`
- `fab/`: JLCPCB gerbers, BOM and CPL, renders (`tools/make_fab.sh`).
- `firmware/`: RP2354B firmware (Pico SDK 2.2), see its README. `pc/stb_probe.py`: PC tool for one or several boards.
- `tools/`: `place_stb.py` (placement from the netlist), `make_pro.py` (net classes), `finish_stb.py` (Freerouting
  session import, GND / GND_USB pours), `jlc_bom.py`, `jlc_rotcheck.py`, `make_fab.sh`. The schematic generator is
  `../driver_test_board/tools/design_stb.py` (`build_dtb.py design_stb <outdir>`, it shares kigen with the large board).
  From now on edit the KiCad files directly; the generators are the record of how the draft was made.

## PCB (0.2, reviewed 2026-11-18)

- 165 x 133 mm, 2 layers, 1.6 mm, every part on the top side (single-sided JLCPCB assembly). Four M3 holes in the
  corners (H1 = ground lug with pad).
- Headers A, B on the top edge, C, D on the bottom edge, J5 (rails + GND) top right, USB-C bottom right. KK-396
  friction ramps face inward.
- One column per channel facing its pin (red, green LED, 33 k, BSS123, 100 k gate, sense divider); the 74HC165 /
  74HCT595 in a strip across the middle under the channels they serve; RP2354B on the right.
- Net classes: HV (header pins, LED nodes, commons, rails): 0.6 mm clearance (IPC-2221 B2), 0.3 mm tracks.
  Default 0.2 / 0.15 mm (0.4 mm pitch QFN). Power 0.4 mm.
- Isolation: GND_USB (PC side) in the bottom-right corner (x > 129 mm, y > 111 mm), a strip with no copper separates
  it from GND; only U3 (ADuM3160) and PS1 (B0505S) straddle it.
- Fully routed: 0 open connection, ERC 0, DRC 0 error (`kicad/erc.rpt`, `kicad/drc.rpt`; the 2 warnings left are the
  USB-C silkscreen at the board edge). JP1-JP4 pads keep a 0.25 mm local clearance (solder jumper, 50 V max).
- Silkscreen: header names and pin numbers, J5 pin names, COM jumper sides (R = rail, G = GND), test point names, the
  role table (JP9 / JP10) and the LED legend.

## Review of 2026-11-18 (0.1 to 0.2)

Fixed:

1. **USB upstream series resistors.** The ADuM3160 needs a series resistor on each of its four data pins; UD+ / UD-
   went straight to the USB-C connector. Added R219 / R220 (24 R) between the connector (and its USBLC6) and U3.
2. **Power in the 50 V resistors.** Header A sense resistors (22 k) dissipate 96 mW at 50 V and 123 mW at 56 V on a
   125 mW 0805; the 33 k LED resistors 70 to 88 mW. Both are now 0.5 W 0805 parts (Panasonic ERJ-P06: C441987,
   C441956), same footprint: 25 % and 18 % of rating at 56 V.
3. **DC/DC module body.** PS1 used a bare 4-pin header footprint; the B0505S body (11.6 x 6.0 mm) reaches 4.8 mm
   left of the pin row and came within 0.3 mm of the C5 / C8 pads. PS1 now has its real outline and courtyard
   (`kicad/sam_test_board.pretty`), C5 / C8 are turned and moved (1.5 mm from the body).
4. **ADuM3160 decoupling.** C2 (VBUS1) and C3 / C4 (VDD1) were 5 to 9 mm from their pins; they now sit under pins
   1-2 and 3-5, each with its own via to the GND_USB return.
5. **4 open connections routed**: +1V1 to U5 pin 10 (via inside the QFN ring), COMB to JP2, VBUS_USB to U3 pin 1,
   G_B7 (needed G_B6 and S_B8 re-routed around it).
6. Symbols of test points, jumpers and holes marked "not in BOM" like their footprints (24 parity warnings gone).
7. Silkscreen labels added (there was no text on the board).

Checked and left as is:

- RP2354B pinout, core regulator, crystal, USB 27 R, QSPI_SS boot button, 74HC165 clamp current (0.46 mA, header A
  2.1 mA, 42 mA in total into +3V3 against 45 mA of fixed load), 74HCT595 at 5 V driving the BSS123 gates, rail
  dividers (2.7 V at 60 V), ADuM3160 strapping (full speed, pull-up always on), B0505S pin order.
- With the common on a rail and an output OFF, the sense divider still draws through the red LED: 0.14 mA on
  B-D (10 % of the ON current), **0.49 mA on header A (one third of ON)**. Header A LEDs glow when OFF; the PC
  reading is not affected. To avoid it use header A for the 20 V / logic connectors when a choice exists.
- NCP1117 with ceramic output capacitors only (10 u + 35 x 100 n): works in practice but is outside the datasheet
  ESR window. If +3V3 rings on the prototype, add a 10 u tantalum across C10 or use an LDO rated for ceramics in a
  later revision.
- BSS123 drives are only limited by the firmware role: closing a channel that is wired to a stiff source (lamp
  column +18 V) would exceed 170 mA.
- Spacing: SOT-23 / 0805 columns are 1.38 to 1.40 mm apart (3.96 mm pin pitch), the USB-C connector has parts at
  2.8 to 3.8 mm (C1, U2, R220, C4), PS1 body 1.5 mm from C5 / C8 / C2: below the 1.5 mm / 4 mm targets.
- Solder jumpers JP1-JP4 bridge 50 V with a 0.3 mm pad gap: never bridge the three pads (rail to GND short).

## JLCPCB

- 433 parts placed by JLC (432 SMD + PS1 B0505S through-hole), 35 LCSC codes, all in stock on the JLC assembly
  library on 2026-11-18 (lowest: 3.3 uH C167673 1 371, 22 k 0.5 W C441987 2 274, 74HCT595 C282339 6 348,
  ADuM3160 C284149 7 939, 33 k 0.5 W C441956 8 873).
- Hand soldered: the five KK-396 headers (Molex 26-60-4120 x 4, 26-60-4060), SWD and SYNC headers.
- CPL rotations checked against the EasyEDA footprint of each LCSC part (`tools/jlc_rotcheck.py`): offsets in
  `jlc_bom.py` (SOIC and SOT-23-6 +270, BSS123 and NCP1117 +180, B0505S +270 with its origin at the centre, USB-C
  origin shifted 1.575 mm). The tool prints CHECK for the LEDs, the NCP1117 and the buttons because their pad
  numbers differ; compared by pin name / position they are right (LED cathodes on the KiCad pad 1 side, NCP1117
  tab opposite the three pins).
- `fab/`: gerbers + drill (`sam_test_board-gerbers.zip`), BOM, CPL, renders. Regenerate with `tools/make_fab.sh`.

## Open

- Firmware untested on hardware. Check the placement preview on the JLCPCB order page before paying (LED and IC
  orientation), and re-check stock on the day of the order.

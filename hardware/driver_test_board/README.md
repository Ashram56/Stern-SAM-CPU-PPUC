# SAM driver output test board (banc de test des sorties driver)

R&D board that replaces the playfield and switch harnesses so the new CPU board can be tested without coils or
transistors at risk. Proposal and decisions: https://claude.ai/artifact/ANPhbTuL6jQy2aoAmm68Nv (Vincent, 2026-11-17).

- Plugs on the I/O Power Driver board 520-5249-00 outputs: J8, J9 (coils 1-16, 50 V), J7, J6 (coils/flashers 17-32,
  20 V), J10 (+50 V and ground; pin 1 = 24 VAC left open), J12 (10 lamp strobes), J13 (8 lamp columns, +18 V on
  pin 9 per the SAM schematic, JP1/JP2 swap pins 9 and 10), J2/J3 (aux data and strobes).
- Plugs on the CPU board switch inputs: J1 (8 strobes, read), J6/J12 (16 returns), J2/J3/J13 (24 dedicated), driven
  by 2N7002 from 74HCT595.
- Every output sees < 1 mA (47 k / 22 k + LED to its own rail), so a stuck output burns nothing. The 50 V and 20 V
  rails must be on: each output has a 1N4004 flyback diode to its rail on the driver board.
- 56 inputs sampled at 1 MHz by 7 x 74HC165 (PIO), aux lines direct on GPIO, rails on the ADC; RP2354B with USB
  isolated by an ADuM3160 and a 1 W B0505S.

## Files
- `kicad/`: KiCad 9 project: schematic draft 0.1 (ERC 0, `kicad/erc.rpt`) and the routed PCB
  `driver_test_board.kicad_pcb` (DRC report `kicad/drc.rpt`).
- `driver_test_board_schematic_v0.1.pdf`
- `fab/`: JLCPCB BOM and CPL (`driver_test_board-*-jlcpcb.csv`), copper renders. Gerbers come once routing is complete (`tools/make_fab.sh`).
- `firmware/`: RP2354B firmware (Pico SDK 2.2), see its README. `pc/sam_probe.py`: PC tool (pyserial).
- `tools/`: everything that produced the files above.
  - schematic: `build_dtb.py` + `design_dtb.py` (kigen/sexp/libs copied from `hardware/kicad/tools`);
  - PCB: `place_pcb.py` (placement from the netlist), `make_pro.py` (net classes), `finish_pcb.py`
    (Freerouting session import, GND / GND_USB pours), `jlc_bom.py` (BOM/CPL), `jlc_rotcheck.py` (JLC footprints).
  - From now on edit the KiCad files directly; the generators are the record of how the draft was made.

## PCB (draft 0.1)

- 250 x 150 mm, 2 layers, 1.6 mm. Four M3 holes in the corners (H1 = ground lug with pad).
- Edges: top = CPU J1, J6, J12, J2 + IO J2 (aux out); left = CPU J3, J13; right = IO J12, J13; bottom = IO J8, J9,
  J7, J6. Inside: IO J3 (aux strobes) and IO J10 (+50 V, ground). USB-C in the bottom-left corner, flush with the edge.
  All KK-396 friction ramps face the inside of the board.
- One column of parts per channel facing its pin (LED, pull-up, 220 k / 47 k divider), shift registers next to their
  channels, RP2354B in the middle with each decoupling capacitor at its supply pin.
- Net classes: HV (50 / 20 / 18 V lines and the LED nodes): 0.6 mm clearance (IPC-2221 B2, 31-50 V), 0.3 mm tracks.
  Default 0.2 mm / 0.15 mm (needed to leave the 0.4 mm pitch QFN). Power 0.4 mm.
- Isolation: GND_USB (PC side) covers x < 35.5 mm, y > 128 mm; a 0.5 mm strip with no track and no via separates it
  from GND, and the two pours are 1 mm apart. Only U3 (ADuM3160) and PS1 (B0505S) straddle it.
- Routed with Freerouting 1.9 (single thread: the multi-thread optimiser breaks clearances).

## JLCPCB

- 392 parts placed by JLC (391 SMD + PS1 B0505S through-hole), 31 LCSC codes, all in JLC stock on 2026-11-17 (RP2354B C39843328: 330, ADuM3160BRWZ-RL C284149:
  7984, B0505S-1WR3 C2992394: 34141, 3.3 uH FNR201610S3R3MT C167673 replaces the AOTA part, out of stock).
- Hand soldered: the 15 KK-396 headers (Molex 26-60-4090 / 4100 / 4120), SWD header, test points, solder jumpers.
- CPL rotations checked against the EasyEDA footprint of each LCSC part (`tools/jlc_rotcheck.py`): offsets in
  `jlc_bom.py` (SOIC and SOT-23-6 +270, 2N7002 and NCP1117 +180, B0505S +270 with its origin at the centre, USB-C
  origin shifted 1.575 mm). LEDs compared by K/A name (no offset), switch contacts 1-2 / 3-4 match the KiCad pads.

## Open
- **15 connections still to route by hand** (DRC `kicad/drc.rpt`, otherwise 0 clearance error): around the RP2354B
  (VREG_LX pin 63 to L1, VREG_AVDD pin 61, GND pin 62, +1V1, +3V3 pins 15/64, GP44 test point, ADC_V50, G_AUXO_P8,
  G_AUXO_P10, G_CSTB5, G_CSTB7) and the two J13 solder jumpers (JP1 pad 2 V18L, JP2 pad 2 LCOLX: Freerouting refuses
  the bridged pad). Then `tools/make_fab.sh` for the gerbers.
- Bring-up: firmware untested on hardware (see `firmware/README.md`).
- Silkscreen: reference designators overlap in the dense channel columns (cosmetic, DRC warnings only).

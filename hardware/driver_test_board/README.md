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
- `kicad/`: KiCad 9 project (schematic draft 0.1, no PCB yet). ERC: 0 violations (`kicad/erc.rpt`).
- `driver_test_board_schematic_v0.1.pdf`
- `tools/`: generator (`build_dtb.py` + `design_dtb.py`, kigen/sexp/libs copied from `hardware/kicad/tools`).
  `KICAD9_SYMBOL_DIR=<kicad symbols> python3 tools/build_dtb.py <out>` regenerates the schematic; after the PCB
  exists, edit the KiCad files directly instead.

## Open
- PCB layout, JLCPCB BOM/CPL with EasyEDA orientation check, stock (B0505S-1WR3, ADuM3160BRWZ, RP2354B).
- Firmware (PIO capture, switch scenarios) and the PC tool `sam_probe`.

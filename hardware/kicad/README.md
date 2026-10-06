# SAM CPU replacement board: KiCad project

Draft 0.1 of the schematic, drawn from [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md). No PCB yet.
Licence: CERN-OHL-S v2 (see [`LICENSE-HARDWARE`](../../LICENSE-HARDWARE)).

- `sam_cpu/`: the KiCad 10 project (10.0 file format). Open `sam_cpu.kicad_pro` in KiCad 10. All symbols come from
  the standard KiCad 10 libraries and are embedded in the sheets, so no project library is needed.
- `sam_cpu/sam_cpu.pdf`: the sheets exported to PDF, for reading without KiCad.
- `tools/`: the Python script that generated this first draft (see the end of this file).

## Sheets

| Sheet | Content | Architecture doc |
|---|---|---|
| Power | J11 (original pinout, from IO board J16), J17 external +5 V, ideal-diode mux with external priority, AMS1117 3.3 V, ADC supply monitors | 9.3 |
| MCU | RP2354B, crystal, core regulator parts, TPS3808 reset supervisor, RESET / BOOTSEL buttons, USB-C to the Pi, SWD header, status LED | 9.2 |
| Raspberry Pi | 40-pin header (Pi 4, same GPIO numbers on a CM4): UART0, SPI0 (DMD frames), I2S, RUN, BOOTSEL, SWD, IRQ | 4.2, 9.1 |
| IO bus | J9 to IO board J1: SN74LVC8T245 data, 74AHCT541 address + IOSTB, 2N7002 open-drain NBRESET, 33 R series resistors | 3.1, 3.2 |
| Switch returns | J6, J12, 16 returns: diode, 1 k to +4.5 V, 220 R + 100 nF, LM339 against 2.25 V (copy of the original) | 5.2, 5.3 |
| Dedicated switches | J2, J3, J13 (24 inputs), coin door memory protect, 8 DIP switches | 5.2, 5.3 |
| Switch scan | 6 x 74HC165 chain, 74HC595 + 8 MMBT3904 strobe drivers, J1 switch columns | 5.3, 5.4 |
| Display and GI | 74HCT245 driver for the original DMD on J5, J18 GI dimmer header | 8, 10.2 |
| Audio | PCM5102A DAC from Pi I2S, two TDA2030A on +-12 V, J10 speakers | 8 |

Connector references follow the original CPU/Sound board 520-5246-00 (J1, J2, J3, J5, J6, J9, J10, J11, J12,
J13), so the cabinet harness labels still match. New connectors start at J17: J17 external +5 V, J18 GI dimmer,
J19 USB-C to the Pi, J20 SWD, J21 Raspberry Pi header.

## Checks

- ERC (KiCad 10.0.6, `kicad-cli sch erc`): 0 errors, 1 warning. The warning is the unused 74HCT245 input A7 tied to
  ground, which KiCad reports because the pin is typed tri-state.
- The netlist KiCad exports was compared pin by pin with the nets the generator intended (`tools/verify.py`):
  1266 pins, 299 nets, no differences.

## Open items before layout

- **Power mux**: the doc names a TPS2121. KiCad has no symbol for it, so this draft uses two LTC4412 ideal-diode
  controllers with AO3401A P-MOSFETs (external path always on, J11 path turned off by `EXT_PRESENT`). Swap back to a
  TPS2121 with a checked custom symbol if preferred.
- **RP2354B support parts** (VREG inductor, VREG_AVDD filter, crystal load, USB series resistors) follow the Pico 2
  pattern from memory; check them against the RP2350 hardware design guide.
- **Pin orders to confirm with a meter** on a real board or harness: J6 / J12 return order, J2 / J3 / J13 dedicated
  input order, J1 strobe order, J5 DMD pinout (Q18).
- **Memory protect**: J2 pin 10 (coin door) goes to GPIO31, which the doc lists as spare.
- **Audio gain** and **LM339 / switch filter values** are starting points for the bench.
- **Part numbers**: footprints are JLCPCB-friendly packages (0603 passives, SOIC / TSSOP logic, SOT-23), but no LCSC
  numbers are filled in yet. They come with the BOM for layout.

## How the draft was generated

`tools/build.py` places symbols from the KiCad library, connects them with wires, net labels, hierarchical labels
and power symbols, and writes the sheets in the KiCad 9 format, which `kicad-cli sch upgrade` then converts to
KiCad 10 (run it on every sheet); `tools/verify.py` compares KiCad's exported netlist with the intended nets.

```
KICAD9_SYMBOL_DIR=/usr/share/kicad/symbols python3 tools/build.py /tmp/out
for f in /tmp/out/*.kicad_sch; do kicad-cli sch upgrade --force $f; done
kicad-cli sch export netlist -o /tmp/out/sam_cpu.net /tmp/out/sam_cpu.kicad_sch
python3 tools/verify.py /tmp/out/sam_cpu.net
```

From now on the `.kicad_sch` files are the source of truth. Edit them in KiCad; do not regenerate over them.

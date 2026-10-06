# SAM CPU replacement board: KiCad project

Draft 0.2 of the schematic, drawn from [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md). The PCB placement draft is described in [`PCB.md`](PCB.md).
Licence: CERN-OHL-S v2 (see [`LICENSE-HARDWARE`](../../LICENSE-HARDWARE)).

- `sam_cpu/`: the KiCad 10 project (10.0 file format). Open `sam_cpu.kicad_pro` in KiCad 10. All symbols come from
  the standard KiCad 10 libraries and are embedded in the sheets, so no project library is needed.
- `sam_cpu/sam_cpu.pdf`: the sheets exported to PDF, for reading without KiCad.
- `tools/`: the Python scripts that generated this draft (see the end of this file).

## Sheets

Every connection is drawn as a wire. Each connector sits on the same page as the parts that drive or read it.
Signals that go to another page use global labels, and each label shows the page numbers where the signal
continues, in square brackets.

| Page | Sheet | Content | Architecture doc |
|---|---|---|---|
| 2 | Power | J11 (original pinout, from IO board J16), J17 external +5 V, ideal-diode mux with external priority, AMS1117 3.3 V, +4.5 V switch supply, ADC supply monitors, rail test points | 9.3 |
| 3 | MCU and Pi | RP2354B, crystal, core regulator parts, TPS3808 reset supervisor, RESET / BOOTSEL buttons, status LED, J21 Raspberry Pi 4 40-pin header (UART0, SPI0, I2S, RUN, BOOTSEL, IRQ), J19 USB-C to the Pi, J20 SWD, U25 DS3231MZ real-time clock on the Pi I2C1 with a CR2032 (BT1) | 4.2, 9.1, 9.2 |
| 4 | IO bus | J9 to IO board J1: SN74LVC8T245 data, 74AHCT541 address + IOSTB, 2N7002 open-drain NBRESET, 33 R series resistor packs | 3.1, 3.2 |
| 5 | Switch columns | 74HC595 + 8 MMBT3904 strobe drivers, J1 switch columns | 5.3, 5.4 |
| 6 | Switch rows 1-8 | J6, 8 returns: diode, 1 k to +4.5 V, 220 R + 100 nF, LM339 against 2.25 V (copy of the original), 74HC165, VREF divider | 5.2, 5.3 |
| 7 | Switch rows 9-16 | J12, same circuit, 74HC165 | 5.2, 5.3 |
| 8 | Dedicated switches 1-16 | J2, J3, input filters, 2 x 74HC165, coin door memory protect | 5.2, 5.3 |
| 9 | Dedicated switches 17-24 | J13, input filters, 74HC165, 8 DIP switches with their 74HC165 | 5.2, 5.3 |
| 10 | Display and GI | 74HCT245 driver for the original DMD on J5, J18 GI dimmer header | 8, 10.2 |
| 11 | Audio | PCM5102A DAC from Pi I2S, two TDA2030A on +-12 V, J10 speakers, J22 second speaker connector (stereo pairs) | 8 |

The prototype uses a Raspberry Pi 4 plugged into the 40-pin header J21. The Pi keeps its own HDMI output, so no
high-speed signals are routed on this board. A CM4 is not planned for now.

Connector references follow the original CPU/Sound board 520-5246-00 (J1, J2, J3, J5, J6, J9, J10, J11, J12,
J13), so the cabinet harness labels still match. The harness connectors J1, J2, J3, J6, J12 and J13 use 3.96 mm
KK-396 headers like the original board, so the existing harness plugs fit. New connectors start at J17: J17 external +5 V, J18 GI dimmer,
J19 USB-C to the Pi, J20 SWD, J21 Raspberry Pi header.

Test points (TP1-TP22, 1.5 mm SMD pads): +5V, +3V3, +4V5, +12V, -12V and two GND on the power page; +1V1, RUN and
GND by the RP2354B; J9 IOSTB, NBRESET, D0 and A0 on the bus; strobes 1-2, SW_CLK and SW_DATA on the switch columns
page; VREF; DAC left / right outputs and GND on the audio page.

## Checks

- ERC (KiCad 10.0.6, `kicad-cli sch erc`): 0 errors, 1 warning. The warning is the unused 74HCT245 input A7 tied to
  ground, which KiCad reports because the pin is typed tri-state.
- The netlist KiCad exports was compared pin by pin with the nets the generator intended (`tools/verify2.py`):
  1303 pins, 302 nets, no differences.

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

`tools/design2.py` describes the parts, their nets and their placement on each page. `tools/build2.py` places the
symbols from the KiCad library, routes the wires on the 1.27 mm grid (`tools/sch.py`), adds power symbols and global
labels, and writes the sheets in the KiCad 9 format, which `kicad-cli sch upgrade` then converts to KiCad 10.
`tools/verify2.py` compares KiCad's exported netlist with the intended nets. `tools/run.sh` does all of it, plus ERC
and the PDF export:

```
KICAD_CLI=kicad-cli KICAD9_SYMBOL_DIR=/usr/share/kicad/symbols tools/run.sh /tmp/out
```

From now on the `.kicad_sch` files are the source of truth. Edit them in KiCad; do not regenerate over them.

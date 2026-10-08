# SAM_IO board: design notes

This file describes how the SAM_IO board works and why it is built the way it is. Read it with the schematic
([`sam_io/sam_io.pdf`](sam_io/sam_io.pdf)) and the board ([`sam_io/pcb_render.png`](sam_io/pcb_render.png),
[`sam_io/pcb_copper.png`](sam_io/pcb_copper.png)). [`README.md`](README.md) has the summary, the connector pinout,
the licence notice and the open points.

Contents:
1. [Purpose and system context](#1-purpose-and-system-context)
2. [Block diagram](#2-block-diagram)
3. [What comes from IO_16_8_1](#3-what-comes-from-io_16_8_1)
4. [The SAM bus interface](#4-the-sam-bus-interface)
5. [Power](#5-power)
6. [Power-up, reset and fault behaviour](#6-power-up-reset-and-fault-behaviour)
7. [Bus timing](#7-bus-timing)
8. [Signal list](#8-signal-list)
9. [Bill of materials](#9-bill-of-materials)
10. [PCB](#10-pcb)
11. [Manufacturing notes](#11-manufacturing-notes)
12. [Bring-up and test](#12-bring-up-and-test)

## 1. Purpose and system context

A Stern SAM machine has a CPU board and an IO power driver board (520-5249-00). The CPU board writes the IO board's
coil, flasher, lamp and aux latches over a 20-way ribbon (CPU J9 to IO J1), and reads its STATUS register (interlocks,
zero cross, lamp driver faults) the same way.

The SAM_IO board takes the CPU board's place on that ribbon, for a machine run by PPUC. It is a PPUC IO board: it sits
on the PPUC RS485 bus, has a board address set by its DIP switch, and runs the io-boards firmware built for board type
`SAM_IO` (`PPUC_BOARD_TYPE=5`, Ashram56/io-boards, `src/IODevices/SamBus/`). The firmware turns PPUC coil and lamp
commands into bus writes to the SAM IO board, scans the lamp matrix, and feeds the SAM IO board's watchdog.

```
 PPUC host (Pi / PC)
       |  RS485 (J1)
 +-----+---------------------------------------------+        20-way ribbon,       +--------------------+
 | SAM_IO board                                      |        pin 1 to pin 1       | Stern SAM IO board |
 |   RP2040 --GPIO3-18--> buffers --33 R--> J9 ======+=============================+ J1                 |
 |   (io-boards SAM_IO firmware)                     |                             |  coils, flashers,  |
 +---------------------------------------------------+                             |  lamps, GI relay   |
       |  5 V in (J5)                                                              +--------------------+
```

The SAM IO board's J1 carries no supply, so the SAM_IO board is powered through J5, like every PPUC board.

## 2. Block diagram

```
                 3.3 V side                                    5 V side
              +--------------+                             +--------------+
 GPIO3-10 ----| A1-A8  U7    |  SN74LVC8T245               | B1-B8 |--RN1/RN2 33R--> J9 D0-D7 (pins 7,5,3,1,2,4,6,8)
 GPIO16 DIR ->| DIR          |  VCCA 3.3 V, VCCB 5 V       |       |
 GPIO17 OE_N->| /OE          |                             +-------+
              +--------------+
              +--------------+
 GPIO11-14 -->| A1-A4  U8    |  74AHCT541 at 5 V           | Y1-Y4 |--RN3 33R------> J9 A0-A3 (pins 12,14,16,18)
 GPIO15 ----->| A5           |  TTL inputs take 3.3 V      | Y5    |--R29 33R------> J9 IOSTB (pin 15)
 GPIO17 OE_N->| /G1 /G2      |                             +-------+
              +--------------+
 GPIO18 ------> gate Q1 2N7002 (10k pull-up R30 to 3.3 V), drain ---------------> J9 NBRESET (pin 13), open drain
 BUS_OE_N: 10k pull-up R27 to 3.3 V.  BUS_DIR: 10k pull-down R28.
```

## 3. What comes from IO_16_8_1

Everything outside the "SAM bus" sheet is the PPUC IO_16_8_1 v1.1.1 design, unchanged, in the same place on the board
and with the same routing:

| Function | Parts | Notes |
|---|---|---|
| MCU | U3 RP2040, U2 W25Q128 16 MB flash, Y1 12 MHz crystal | SW1 reset, SW2 boot, J3 SWD (not fitted), J4 USB-C for programming |
| RS485 | U1 ADM3483, J1 6-way push-in terminal, JP1-JP3 bias and termination | GPIO0 TX, GPIO1 RX, GPIO2 DE |
| Power | J5 6-way terminal (5 V in), D5 SMAJ5.0 TVS, U6 AP2112K-3.3 | see section 5 |
| Board address | SW3 4-way DIP, resistor ladder R13/R14/R18/R19/R22/R23, U4 LMV321 buffer, into GPIO28 (ADC) | read by the firmware at start-up |
| Status LED | D3 on GPIO25 | |
| Special output | U5 SN74AHCT1G125 from GPIO29 to J5 pin 5 | 5 V level, used by io-boards for a WS2812 string; SAM_IO keeps it |
| QWIIC | removed (J2, R96, R97, C8) | GPIO0 / GPIO1 are only the RS485 TX / RX; R9 (0 ohm, RO to GPIO1) is a track |

Removed: the 16 input stages (sheet IN16, J6-J8) and the 8 MOSFET outputs with their fuse and bulk capacitor (sheet
OUT8, J9-J11, F2, C56). GPIO19-24, 26 and 27 were the outputs and are now unconnected.

## 4. The SAM bus interface

The "SAM bus" sheet is the IO bus sheet of the SAM CPU replacement board in this repository
(`hardware/kicad/sam_cpu/io_bus.kicad_sch`), so both boards that can drive a SAM IO board use the same circuit. The
reasoning is in [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) sections 3.1 and 3.2. In short:

**The far end.** On the SAM IO board, every J1 line has 100 R in series and 22 pF to ground. D0-D7 have 10 k pull-downs
and go into a 74HC245 at 5 V (VIH about 3.5 V, so 3.3 V drive is out of spec). For STATUS and AUX_IN reads, two more
74HC245 drive D0-D7 with 5 V levels. A0-A3 and IOSTB have 4.7 k pull-ups to 5 V and go to two 74LS138 decoders. Every
latch clocks on the rising edge of its decoder output, which follows IOSTB rising. NBRESET has a 10 k pull-up to 5 V
and goes into the push-button input of a DS1232 supervisor.

**D0-D7: U7, SN74LVC8T245.** Bidirectional, A side at 3.3 V (RP2040), B side at 5 V (J9). It drives full 5 V levels
into the far 74HC245, and shifts the 5 V STATUS read down to 3.3 V for the RP2040. DIR (GPIO16) comes from the PIO
program as a side-set pin, so the direction changes exactly with the bus cycle: 1 = this board drives J9, 0 = J9 drives
the RP2040. R28 pulls DIR low, so before the firmware runs the buffer could only ever drive towards the RP2040.

**A0-A3 and IOSTB: U8, 74AHCT541.** Output only, at 5 V. Its TTL inputs (VIH 2 V) accept the RP2040's 3.3 V, and it
drives full 5 V. It also keeps the far 5 V pull-ups and any cable fault away from the RP2040. Its unused inputs
(pins 7-9) are tied to GND; outputs Y6-Y8 are left open.

**Output enable.** U7 /OE and both U8 enables share BUS_OE_N (GPIO17), pulled up to 3.3 V by R27, so both buffers are
off (high impedance) until the firmware drives GPIO17 low. U8 at 5 V reads the 3.3 V pull-up as high (TTL input).

**NBRESET: Q1, 2N7002.** Open drain on J9 pin 13, against the SAM IO board's 10 k pull-up, as the original CPU board
does with a transistor. GPIO18 high (or floating, through R30) = Q1 on = SAM IO board held in reset. No level shifting
is needed. Pulling NBRESET low makes the SAM IO board's supervisor clear every output latch (all coils, lamps and aux
outputs off, GI relay released).

**Series resistors.** 33 R on every driven J9 line (RN1-RN3 arrays, R29 for IOSTB), at the J9 end, to damp ringing on
the ribbon together with the 100 R and 22 pF on the far board.

**Test points** on the J9 side: TP3 IOSTB, TP4 NBRESET, TP5 D0, TP6 A0. Scope these against the RP2040 side to see
buffer delays and edges.

**Decoupling.** C30 100 nF at U7 VCCA, C31 100 nF at U7 VCCB, C32 100 nF at U8 VCC, C33 10 µF bulk on the 5 V side.

**Why these GPIOs.** `sam_bus.pio` needs D0-D7 and A0-A3 on 12 consecutive GPIOs (one `out pins, 12`), then IOSTB and
DIR on the next two (side-set). GPIO3-16 is the first such run after the RS485 pins. OE_N and NBRESET follow on 17 and
18. These are IO_16_8_1's input GPIOs, so the RP2040 keeps its original fanout towards the left of the board.

## 5. Power

- **5 V** comes in on J5 pins 1, 3 and 4 (GND on 2 and 6), through the original protection (D5 SMAJ5.0 TVS). It
  supplies U7's B side, U8, the special output buffer U5 and the 3.3 V regulator.
- **3.3 V** comes from U6, AP2112K-3.3 (600 mA), as on IO_16_8_1. It supplies the RP2040, flash, RS485, U7's A side
  and the pull-ups.
- **Budget.** The RP2040 and flash take roughly 30-50 mA, the RS485 transceiver a few mA. The SAM bus side adds little:
  the buffers are CMOS, and the worst static load on the ribbon is the far board's pull-ups and pull-downs (D lines
  driven high into 10 k pull-downs, 0.5 mA each; A lines and IOSTB driven low against 4.7 k pull-ups, about 1 mA each),
  under 10 mA in total. A 5 V supply of 200 mA leaves plenty of margin.
- **Ground.** The ribbon has two GND wires (J9 pins 19, 20). The SAM_IO board's 5 V supply should come from the same
  machine supply as the SAM IO board's logic, so the two boards share a ground reference through the supply as well as
  through the ribbon.

## 6. Power-up, reset and fault behaviour

| State | BUS_OE_N | Buffers | J9 lines | NBRESET | SAM IO board |
|---|---|---|---|---|---|
| No power on SAM_IO | n/a | unpowered | far pull-ups / pull-downs | pulled up by far board, Q1 off | runs on its own; IOSTB idles high so nothing latches; its watchdog trips within 62.5-250 ms without lamp strobes and resets it |
| Power-up, RP2040 in reset or booting | high (R27) | off | far pull-ups hold IOSTB high | low (R30 turns Q1 on) | held in reset, all outputs off |
| Firmware running, bus enabled | low | on | driven by SAM_IO | released | runs; the firmware must strobe lamp line 0 at least every 62.5 ms to feed its watchdog |
| RP2040 reset, crash with GPIOs reset, or brown-out | high (R27) | off | idle | low (R30) | held in reset again |
| Firmware hang with GPIOs still driven | low | on | frozen | released | the lamp scan stops, so its own DS1232 watchdog resets it within 62.5-250 ms |

So the SAM IO board's outputs are off whenever the SAM_IO board is not actively running the bus, and the SAM IO
board's own watchdog covers a firmware hang. In the firmware, `SamBusDriver` also plays an all-off frame when a frame is
late or the io-boards watchdog holds outputs off.

Note the DS1232's push-button input needs NBRESET low for about 20 ms to register, and after any trigger keeps the
SAM IO board in reset for at least 250 ms.

## 7. Bus timing

From `sam_bus.pio` in io-boards (35 ns per PIO cycle: clock divider 7 at 200 MHz):

| Phase | Firmware | Original CPU board (measured) |
|---|---|---|
| address and data set up before IOSTB falls | at least 140 ns | valid when IOSTB falls |
| IOSTB low | 175 ns | about 100 ns |
| hold after IOSTB rises (latches clock on this edge) | 245 ns | at least 200 ns |
| one write, back to back | 18 cycles, 630 ns | about 650 ns |
| one read | 23 cycles, 805 ns | |

Reads: the PIO releases D0-D7 on the RP2040 first, then flips U7's DIR, then pulls IOSTB low; the byte is sampled at
the end of the strobe; then IOSTB rises, U7 turns back to driving J9, and the RP2040 drives D0-D7 again. Each step is at
least one 35 ns cycle, longer than U7's enable and disable times, so the RP2040 and U7 never drive the same line.

Buffer delays add a few ns on each line (U7 and U8 both under 10 ns at these supplies) and are the same on address,
data and strobe, so they do not eat into set-up or hold. The ribbon and the 33 R / 100 R / 22 pF network slow the edges
to tens of ns, still well inside the 175 ns strobe. These numbers still need a scope on a real SAM IO board (open point
in the README).

## 8. Signal list

| RP2040 | Net | Buffer pin (3.3 V side) | Buffer pin (5 V side) | Series R | J9 pin | Test point |
|---|---|---|---|---|---|---|
| GPIO3 (pin 5) | BUS_D0 | U7 A1 (3) | U7 B1 (21) | RN1 R4 | 7 | TP5 |
| GPIO4 (6) | BUS_D1 | U7 A2 (4) | U7 B2 (20) | RN1 R3 | 5 | |
| GPIO5 (7) | BUS_D2 | U7 A3 (5) | U7 B3 (19) | RN1 R2 | 3 | |
| GPIO6 (8) | BUS_D3 | U7 A4 (6) | U7 B4 (18) | RN1 R1 | 1 | |
| GPIO7 (9) | BUS_D4 | U7 A5 (7) | U7 B5 (17) | RN2 R4 | 2 | |
| GPIO8 (11) | BUS_D5 | U7 A6 (8) | U7 B6 (16) | RN2 R3 | 4 | |
| GPIO9 (12) | BUS_D6 | U7 A7 (9) | U7 B7 (15) | RN2 R2 | 6 | |
| GPIO10 (13) | BUS_D7 | U7 A8 (10) | U7 B8 (14) | RN2 R1 | 8 | |
| GPIO11 (14) | BUS_A0 | U8 A1 (2) | U8 Y1 (18) | RN3 R4 | 12 | TP6 |
| GPIO12 (15) | BUS_A1 | U8 A2 (3) | U8 Y2 (17) | RN3 R3 | 14 | |
| GPIO13 (16) | BUS_A2 | U8 A3 (4) | U8 Y3 (16) | RN3 R2 | 16 | |
| GPIO14 (17) | BUS_A3 | U8 A4 (5) | U8 Y4 (15) | RN3 R1 | 18 | |
| GPIO15 (18) | BUS_IOSTB | U8 A5 (6) | U8 Y5 (14) | R29 | 15 | TP3 |
| GPIO16 (27) | BUS_DIR | U7 DIR (2) | | R28 10 k to GND | | |
| GPIO17 (28) | BUS_OE_N | U7 /OE (22), U8 /G1 (1), /G2 (19) | | R27 10 k to 3.3 V | | |
| GPIO18 (29) | NBRESET_DRV | Q1 gate | Q1 drain, open drain | R30 10 k to 3.3 V on the gate | 13 | TP4 |
| | GND | | | | 19, 20 | |
| | not connected | | | | 9, 10, 11, 17 | |

(KiCad's 74AHCT541 symbol numbers its pins A0-A7 / Y0-Y7; the table uses the datasheet's A1-A8 / Y1-Y8.)

## 9. Bill of materials

The full BOM, grouped by value and footprint, is [`sam_io/sam_io_bom.csv`](sam_io/sam_io_bom.csv), exported from the
schematic. The parts the SAM bus adds:

| Ref | Value | Package | Function |
|---|---|---|---|
| J9 | 2x10 shrouded IDC header, 2.54 mm | through hole | SAM bus to the SAM IO board J1 |
| U7 | SN74LVC8T245 | TSSOP-24 | D0-D7 level shifter, bidirectional |
| U8 | 74AHCT541 (74HCT541 also works) | TSSOP-20 | A0-A3, IOSTB buffer at 5 V |
| Q1 | 2N7002 | SOT-23 | NBRESET open-drain driver |
| RN1, RN2, RN3 | 4 x 33 R array, convex | 4x0603 | series resistors |
| R29 | 33 R | 0603 | IOSTB series resistor |
| R27, R28, R30 | 10 k | 0603 | OE_N pull-up, DIR pull-down, NBRESET gate pull-up |
| C30, C31, C32 | 100 nF | 0603 | decoupling |
| C33 | 10 µF | 0805 | 5 V bulk |
| TP3-TP6 | test pad 1.5 mm | | scope points, not a BOM line |

The rest of the BOM is IO_16_8_1's. The parts it lost are listed in the README.

## 10. PCB

**Board.** 100 x 70 mm, two layers, 1.6 mm FR4, 35 µm copper, as IO_16_8_1. Four 5.5 mm mounting holes at the corners,
5 mm from the edges (centres 90 mm x 60 mm apart). GND pour on both layers, stitched with vias.

**Rules** (unchanged from IO_16_8_1): 0.2 mm minimum track and clearance, 0.5 mm vias with 0.3 mm drill, 0.33 mm hole
to copper. Every track is 0.2 mm except IO_16_8_1's power tracks.

**Placement.** The connectors stay where they are on IO_16_8_1: J1 (RS485) and J5 (power) along the top edge, J4 USB-C
between them. J9 sits on the left edge where IO_16_8_1's input terminals were, key towards the board edge, pin 1 top
left. The series resistors are next to J9, U7 (data) and U8 (address) between J9 and the RP2040, so the 3.3 V side of
each buffer faces the RP2040 and the 5 V side faces J9. Q1, its pull-up and the test points are along the bottom.

**Routing of the bus.** The RP2040 and both buffers number their pins anticlockwise. When two such chips face each
other, a bus that keeps its bit order between them has to reverse its order, which a single layer cannot do. Here each
of the 13 lines runs on the top layer from the RP2040 (reusing IO_16_8_1's fanout next to the chip), drops through a via
right under its own buffer pin, crosses under the other lines on the bottom layer, and comes back up next to the pin:
two vias per line, in a part of the board with nothing else on it. A pin swap in the schematic would have avoided the
vias but made the SAM bus sheet differ from the CPU board's. DIR, OE_N and NBRESET_DRV reuse IO_16_8_1's GPIO16-18 route
down the right of the RP2040. The 5 V side (buffers, resistors, J9), the pull-ups and the power were routed with
Freerouting and then checked by hand.

**Checks.** DRC with KiCad 10.0.6: no unconnected item and no violation that IO_16_8_1 does not already have. The
inherited ones are J4's pad-to-slot clearance (USB-C footprint), the J2 / C8 courtyard overlap, starved thermals on J4,
U5 and C8, and footprints that differ from the KiCad 10 libraries. ERC shows only inherited items. The PCB matches the
schematic net for net.

## 11. Manufacturing notes

- **Fab outputs** (Gerbers, drill, position file) are not in the repository yet. Generate them from
  `sam_io.kicad_pcb` before ordering, and add them to this folder (TAPR OHL 4.2d).
- **C31 has a via in its GND pad** (there was no room beside it). Ask the fab to fill or tent vias, or check that joint.
- **Assembly** is single-sided (all SMD parts on top). The smallest parts are IO_16_8_1's 0402 passives and the
  RP2040's QFN-56; the new parts are 0603, SOT-23 and 0.65 mm pitch TSSOP.
- **J9** must be a shrouded (boxed) header so the ribbon can only go in one way. Check the cable: pin 1 to pin 1, with
  the SAM IO board's J1 key in the same orientation as on the original CPU board.
- J3 (SWD) is not fitted, as on IO_16_8_1. The QWIIC option (J2) was removed.

## 12. Bring-up and test

1. Without the ribbon: power J5 with 5 V, check 3.3 V, flash the io-boards `SAM_IO` build over USB-C, set the board
   address on SW3.
2. Before the firmware enables the bus: TP4 (NBRESET) should be low (Q1 on, pulled up by nothing yet: measure with a
   10 k resistor to 5 V), and U7 / U8 outputs high impedance.
3. With the firmware running and the ribbon to a SAM IO board with its coil power off: scope TP3 (IOSTB), TP6 (A0) and
   TP5 (D0) against the RP2040 side. Check set-up, strobe and hold (section 7) at the SAM IO board's J1, and the edges
   for ringing.
4. Read STATUS: the 20 V and 50 V interlock bits and the zero-cross bit should follow the machine. This checks the
   read direction through U7.
5. Lamps, then flashers, then coils, with PPUC test commands. Check that the SAM IO board's yellow reset LED goes out
   when the firmware starts and comes back when the RP2040 is reset (SW1) or the lamp scan stops.

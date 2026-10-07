# RP2354B firmware

Firmware for the RP2354B on the SAM CPU replacement board. It replaces the
coil, lamp and switch nodes of a PPUC RS485 bus with one chip: the Pi runs
PinMAME and libppuc as usual and talks PPUC v2 to this board, and the board
drives the original Stern SAM IO power driver board over J9 instead of its own
MOSFETs.

```
Pi (PinMAME + libppuc) --UART0, PPUC v2--> core0: session, config
                                           core1: SAM bus (PIO0), switch chain (PIO1 SM0),
                                                  coils, lamp PWM, GI, interlocks
```

## Build

Pico SDK 2.2 or later, arm-none-eabi-gcc.

```
cmake -B build -DPICO_SDK_PATH=/path/to/pico-sdk
cmake --build build          # build/sam_cpu.uf2, runs from RAM (copy_to_ram)
```

Compile-time options (`-D...` on the cmake line):

| Option | Default | Meaning |
|---|---|---|
| `SAM_BOARD_MASK` | `0x03` | PPUC board ids this firmware answers for: 0 outputs, 1 switches |
| `SAM_LINK_BAUD` | 115200 | UART0 baud rate (PPUC's `kBaudRate`) |
| `SAM_GATE_COILS_ON_INTERLOCKS` | 1 | drop coils while the 20 V / 50 V interlocks read open (STATUS bit 1 = present) |

Host tests for everything under `src/core` (protocol, config, switches,
coils, lamps), no hardware needed:

```
cmake -B build-test test && cmake --build build-test && ./build-test/sam_core_tests
```

## Layout

| Path | What |
|---|---|
| `boards/sam_cpu_rp2354b.h` | board header: RP2354B, 2 MB flash, 200 MHz |
| `src/board_pins.h` | GPIO map, from the schematic (PR #4) |
| `src/ppuc/` | PPUC v2 protocol header (vendored from io-boards 82511ef) and config topics |
| `src/core/` | hardware-free logic, unit tested on the host |
| `src/hw/*.pio` | PIO programs |
| `src/hw/realtime.cpp` | core1 loop |
| `src/hw/link_uart.cpp` | core0 PPUC link driver |
| `test/` | host tests |

## PIO and DMA

| Block | SM | Program | Pins | Clock |
|---|---|---|---|---|
| PIO0 (base 0) | 0 | `sam_bus` | D0-D7, A0-A3 GPIO0-11, IOSTB 12, DIR 13 | /7, 35 ns |
| PIO1 (base 16) | 0 | `switch_chain` | CLK 16, LOAD_N 17, DATA in 18, STB_DATA 19 | /4, 10 MHz shift |

## SAM bus (core1)

`sam_bus` takes one 32-bit command per access: data in bits 7:0, register
A3-A0 in bits 11:8, bit 12 = read, bits 31:13 = idle cycles after the access.
IOSTB is low 175 ns, data is held 245 ns after it rises, about 700 ns per
write as on the original board. Reads turn the 8T245 around and push the byte.

Bring-up order: J9 buffers enabled with the IO board still in reset
(NBRESET_DRV high), all registers cleared, reg 0xB at its idle value, lamp
scan running for two frames, then reset released and everything written again.
From then on the lamp scan never stops: line 0 is DRV0, which feeds the IO
board's watchdog. The RP2354B watchdog (100 ms) is fed only while core1's loop
runs; on a reset NBRESET_DRV's pull-up puts the IO board back in reset.

## Lamps: brightness and ramps (LED replacement)

The IO board has no PWM: a lamp line is strobed once per frame and LMP_DRV
picks which of its 8 lamps get current. The firmware scans 10 lines of
250 us (2.5 ms frame, 400 Hz) and inside each line's window rewrites LMP_DRV
as lamps reach the end of their on-time (edge-sorted PWM, at most 9 writes per
line). Per lamp:

- `brightness` 0-255, perceived (gamma 2.2 applied), level when fully on;
- `lightUp` ms to ramp from off to full (incandescent warm-up);
- `afterGlow` ms to ramp from full to off (filament cooling).

Lamps without their own values use the board defaults (below). The strobed
aux boards (Tron LE ramp tubes: reg 0xB bits 4 and 5) get the same treatment
with one PWM period per frame.

## PPUC integration

The board shows up as two PPUC boards (`SAM_BOARD_MASK` = `0x03`):

| Board id | Role | Devices in the game config |
|---|---|---|
| 0 | SAM outputs: one entry point for every coil, flasher, lamp and aux output, sent over the SAM bus | `PWM` (coils, flashers, `lamp` type), `LAMPS`, game-on solenoid |
| 1 | SAM switches | `SWITCH_MATRIX`, `SWITCHES` |

There is no display on this board: the Pi drives the DMD (for example a
ZeDMD over USB with libzedmd).

Internally coils, lamps and switches share one device table, since their
port ranges do not overlap, so the ids only matter to the host. Other layouts
work by changing the mask (bit n = id n), up to 8 ids. When the switch token
reaches one of its ids and the chain's next board is another of its ids, it
sends that reply too, as the next node on RS485 would.
Version reports use board type `0x05`, which is a proposal and must be agreed
with PPUC. Firmware update over the link is refused (`kUpdateUnsupported`):
flash with picotool or SWD from the Pi.

### Ports

| Device | Port |
|---|---|
| Coils 1-32 (driver board), 33-40 (aux, latched by reg 0xB bit 6) | SAM coil number |
| Matrix lamps | SAM lamp number 1-80 |
| Aux latch outputs | 200 + (reg 0xB strobe bit - 3) x 8 + AUX_DRV bit. Tron LE left tube R/G/B = 213/212/211, right = 221/220/219 |
| Matrix switches | strobe x 16 + return + 1 (1-128) |
| Dedicated D1-D32 (D25-D32 = DIP switches) | 129-160 |
| Memory protect | 161 |
| 20 V / 50 V interlocks, lamp driver faults 1/2 (STATUS) | 162 / 163, 164 / 165 |

### Configuration

Existing PPUC topics work unchanged: `PWM` (coils: power, min/max pulse,
hold power and time, fast flip and stop switches; type `lamp` for a matrix
lamp), `LAMPS`, `SWITCHES` (debounce, fast flip mode), `SWITCH_MATRIX`,
`SWITCH_CHAIN` (next board), coin door, game-on solenoid, tilt.

Additions, to propose upstream (libppuc must send them):

- `PWM` / `LAMPS`: keys `BRIGHTNESS` (66), `LIGHT_UP` (85), `AFTER_GLOW` (71)
  on lamps.
- New topic `SAM_BOARD` (122), board-wide:

| Key | Meaning | Default |
|---|---|---|
| `DURATION` (65) | lamp line slot, us (100-2000) | 250 |
| `BRIGHTNESS` (66) | default lamp brightness | 255 |
| `LIGHT_UP` (85) | default lamp ramp up, ms | 0 |
| `AFTER_GLOW` (71) | default lamp ramp down, ms | 0 |
| `NUM_ROWS` (79) | matrix strobes driven (1-8) | 8 |
| `FREQUENCY` (70) | software PWM rate for coil power < 255, Hz | 83 |
| `MAX_PULSE_TIME` (84) | no OutputState for this long: coils off, ms | 50 |

### Switches

The 74HC165/595 chain is scanned continuously (one pass every ~6 us), so
dedicated switches and flipper buttons are sampled every pass. Debounce is
kept short because PinMAME runs the ROM's own debounce: matrix switches must
read the same on two consecutive scans, dedicated ones must hold for 50 us,
a configured debounce lengthens that, fast-flip switches close on the first
sample. Flipper coils follow their switch on the board (fast flip), within a
chain pass and one bus write.

## Open items

- Board type `0x05`, topic `SAM_BOARD` and the lamp keys must be agreed with
  PPUC, and libppuc taught to send them.
- GI dimmer PWM on GPIO38 (1 kHz, duty = level / 8) polarity to confirm.
  (AMP_MUTE, GPIO39, is active high and driven low: amplifiers on.)
- The aux strobe latching (data on AUX_DRV, latch on the strobe's rising
  edge) follows the ROM's aux coil burst; check on the Tron tube boards.
- VMON ADC inputs are not used yet.
- The RS485 port on GPIO20-22 (UART1) is not used yet.

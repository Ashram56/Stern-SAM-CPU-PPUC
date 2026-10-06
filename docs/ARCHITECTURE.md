# Stern SAM replacement CPU board: architecture

Status: **draft for review**. Nothing here is built yet. Section 11 lists what needs Vincent's answer or a
measurement before the schematic starts.

Sources this document builds on:
- **Bus docs**: [Tron-Legacy-LE-ROM-Decryption/io/bus](https://github.com/Ashram56/Tron-Legacy-LE-ROM-Decryption/tree/main/io/bus)
  (`README.md`, `CPU_BOARD_IO.md` and the CSVs). Register map, ISR schedule and every timing number come from there.
- **J1 schematic reading**: [Stern-SAM-Databus-Analysis](https://github.com/Ashram56/Stern-SAM-Databus-Analysis)
  (`IO board analysis`). Pinout, pull resistors and logic families come from there.
- **PPUC**: [github.com/PPUC](https://github.com/PPUC), read on 2026-10-06: `ppuc/docs/STACK.md`, `ppuc/docs/V2_PROTOCOL.md`,
  `io-boards/src/PPUCProtocolV2.h`, `io-boards/src/IODevices/SwitchMatrix*`, `libppuc/src/PPUC.cpp`.

Statements are tagged **[doc]** (from the sources above), **[ppuc]** (from PPUC source), or **[proposal]** (a design choice
made here, open to change).

---

## 1. Summary

```
   ┌──────────────────────────── Raspberry Pi (4 / 5 or CM4 / CM5) ───────────────────────────┐
   │ ppuc-pinmame: PinMAME runs the original SAM ROM, libppuc maps it to boards,              │
   │ libdmdutil drives the display, SDL audio goes out over I2S                               │
   └──────┬──────────────────────┬─────────────────────────┬──────────────────────┬───────────┘
          │ UART 1-3 Mbaud       │ GPIO: RUN, BOOTSEL,     │ I2S                  │ display link
          │ (PPUC v2 frames)     │ SWD, IRQ                │                      │ (section 8)
   ┌──────▼──────────────────────▼──────────┐       ┌──────▼──────┐        ┌──────▼──────┐
   │ RP2040 "SAM IO controller"             │       │ DAC + amp   │        │ DMD driver  │
   │  core0: PPUC protocol, config, safety  │       └─────────────┘        └─────────────┘
   │  core1: real-time scheduler            │
   │  PIO0: J1 bus master                   │
   │  PIO1: switch matrix + dedicated scan  │
   └───┬──────────────────────────────┬─────┘
       │ 3.3 V ⇄ 5 V buffers          │ input conditioning, 74HC165 chain, strobe drivers
   ┌───▼─────────────┐          ┌─────▼──────────────────────────────┐
   │ J1 → IO power   │          │ switch matrix (4 x 16), 24         │
   │ board (original)│          │ dedicated switches, DIP switches   │
   └─────────────────┘          └────────────────────────────────────┘
```

The key choices:
1. **The RP2040 looks like a PPUC IO board** [proposal]. It speaks PPUC's v2 protocol, so `ppuc-pinmame` and libppuc run
   unchanged at first. Behind that, instead of driving MOSFETs directly, it translates PPUC's coil, lamp and GI bitmaps into
   writes on the original SAM J1 bus. PPUC already accepts `platform: SAM` [ppuc], but nothing in PPUC drives a SAM IO board
   yet, so that translation is the new work.
2. **The Pi to RP2040 "high speed bus" is a UART at 1 to 3 Mbaud** carrying PPUC v2 frames, plus GPIO lines for reset,
   flashing and a "switch changed" interrupt [proposal]. Section 4 compares this with SPI.
3. **PIO does the J1 bus cycles, core1 does the timing** [proposal]. The IO power board is only decoders and edge-triggered
   latches with no timing of its own [doc], so every pulse width, lamp slot and blanking gap comes from the RP2040.
4. **Switches are read by a second PIO block** through 74HC165 shift registers, so one RP2040 has enough pins for the bus,
   64 matrix switches, 24 dedicated switches and 8 DIPs [proposal].
5. **The RP2040 owns safety**: coil pulse limits, the interlock gate, a host-loss timeout and NBRESET [proposal], using PPUC's
   board-owned pulse envelopes [ppuc].

## 2. What the replacement board must provide

From `CPU_BOARD_IO.md` §9 [doc], mapped to who does it here:

| Function | Original SAM CPU board | Here |
|---|---|---|
| IO power board bus (J1): 32 coils + 8 aux coils, 10x8 lamp matrix, GI relay, aux strobes, STATUS | AT91 EBI, 250 µs ISR | RP2040 PIO0 + core1 |
| Switch matrix, 4 strobes x 16 returns (64) | 0x01100000 / 0x01100008, 250 µs per column | RP2040 PIO1 |
| 24 dedicated switches + 8 DIP switches | 0x01100002/4/5 | RP2040 PIO1 (same shift chain) |
| Game logic | ROM on the AT91 | PinMAME on the Pi |
| DMD, 128 x 32, 16 shades | Xilinx FPGA scanner | Pi + display driver (section 8) |
| Audio, 24 kHz stereo + volume | Xilinx + PCM17xx-class DAC | Pi I2S + DAC + amplifier (section 8) |
| NVRAM, real-time clock | battery SRAM, DS1302-style RTC | Pi storage (PinMAME `nvram/`), Pi 5 RTC or an I2C RTC |
| LED sign port (9600 baud) | USART1 | optional, a Pi UART |

## 3. The J1 bus, electrically and logically

### 3.1 Signals [doc]

| J1 pin | Signal | IO board side |
|---|---|---|
| 7, 5, 3, 1, 2, 4, 6, 8 | D0 … D7 (pin 7 = D0, 5 = D1, 3 = D2, 1 = D3, 2 = D4, 4 = D5, 6 = D6, 8 = D7) | 74HC245, 10 k pull-down |
| 12, 14, 16, 18 | A0, A1, A2, A3 | two 74LS138, 4.7 k pull-up to 5 V |
| 15 | IOSTB (active low) | enables both 74LS138, 4.7 k pull-up |
| 13 | NBRESET | no pull-up |
| 20 | GND | |

Pins 9, 10, 11, 17 and 19 are not in the schematic notes (open question Q3).

Registers (`bus_register_map.csv`) [doc]:

| A3-A0 | Register | Dir | Use |
|---|---|---|---|
| 0 | SOL_A | W | coils 9-16 |
| 1 | SOL_B | W | coils 1-8 |
| 2 | SOL_C | W | coils 17-24 |
| 3 | FLSH_LMP | W | flashers, coils 25-32 |
| 5 | STATUS | R | D0 20 V interlock, D1 50 V interlock, D2 zero cross, D3/D4 lamp driver faults |
| 6 | AUX_DRV | W | data byte for strobed aux boards (J2) |
| 7 | AUX_IN | R | J3 pins 1-8 (unused by the ROM) |
| 8 | LMP_STB | W | lamp strobe lines 0-7 |
| 9 | AUX_LMP | W | lamp strobe lines 8-9 |
| 10 | LMP_DRV | W | lamp drive bits for the active line |
| 11 | aux/GI latch | W | bit 0 GI relay (0 = on), bits 3-7 aux strobes, idle high |

Every latch clocks on the **rising** edge of its decoder output, which follows IOSTB rising [doc].

### 3.2 Level shifting [proposal]

The IO board side is 5 V logic. The RP2040 is 3.3 V and **not 5 V tolerant**.
- **Address, IOSTB, NBRESET (outputs only)**: one 74AHCT541 (or 74HCT541) at 5 V. Its TTL-level inputs accept 3.3 V and it
  outputs full 5 V. The 74LS138s would also accept 3.3 V directly, but a buffer protects the RP2040 from the 5 V pull-ups and
  from cable faults.
- **D0-D7 (bidirectional)**: one SN74LVC8T245 (A side 3.3 V, B side 5 V). The data inputs on the IO board are a **74HC245 at
  5 V, whose VIH is about 3.5 V**, so driving them straight from 3.3 V is out of spec. The 8T245 also level-shifts the 5 V
  STATUS read down to 3.3 V. Its DIR pin is driven by the PIO program, so direction changes exactly with the bus cycle.
- **Power-up state**: both buffers' OE is pulled to "disabled" until firmware enables them. With the buffers off, the IO
  board's own pull-ups hold IOSTB high, so no latch can clock while the RP2040 boots.
- Series resistors (33 to 100 Ω) on the J1 side of every line, for the ribbon cable.

### 3.3 Bus cycle timing

Measured on the original board [doc]: IOSTB low about 100 ns (EBI setting predicts 125 ns), address and data valid when IOSTB
falls and for at least 200 ns after it rises, 650 ns between writes in a burst.

Target for the RP2040 [proposal]: the bus state machine runs with a clock divider of 4 at 125 MHz, so one PIO cycle is
32 ns. That keeps every delay inside the 3-bit delay field left over by a 2-bit side-set.

| Phase | Time | PIO cycles |
|---|---|---|
| address + data set up before IOSTB falls | ≈ 128 ns | 4 (the `out` and `jmp` instructions) |
| IOSTB low | 160 ns | 5 |
| hold after IOSTB rises | 224 ns | 7 |
| one write, back to back | ≈ 550 ns | 17 |

That is about 1.8 million writes per second, close to the original's 650 ns spacing. The ROM uses about 57,000 accesses per
second in a game [doc], so the bus has about 30 times the headroom we need, even with finer lamp PWM. All timings become
constants in the PIO program and should be checked with a scope against the real IO board (Q4).

Two lessons from the ROM to **not** copy [doc]:
- The ROM writes LMP_STB and AUX_LMP with one 16-bit store, so IOSTB stays low across two addresses. Here every access is
  a separate clean byte cycle.
- The ROM never reads STATUS bits 3-4 (lamp driver faults). We read and report them.

### 3.4 PIO0: the bus master program [proposal]

One state machine executes a stream of 32-bit commands from its TX FIFO:

```
bits  3:0   A3-A0
bits 11:4   D7-D0 (ignored on a read)
bit  12     1 = read (result pushed to the RX FIFO)
bits 31:13  delay after the cycle, in 32 ns units (up to ~16 ms)
```

Pins: OUT base = D0, 12 consecutive GPIOs (D0-D7, A0-A3). Side-set: IOSTB and the 8T245 DIR, on two consecutive GPIOs.

```
; sketch: assembles (17 instructions), not yet run on hardware. Clock divider 4 at 125 MHz: 1 cycle = 32 ns
.program sam_bus
.side_set 2                         ; side bit 0 = IOSTB, bit 1 = DIR (1 = RP2040 drives the J1 data lines)
.wrap_target
    pull block          side 0b11      ; idle: IOSTB high, 8T245 drives J1
    out pins, 12        side 0b11      ; address + data
    out x, 1            side 0b11      ; read flag
    out y, 19           side 0b11      ; delay after the cycle (these cycles are also the setup time)
    jmp !x write        side 0b11
read:
    mov osr, null       side 0b11
    out pindirs, 8      side 0b11      ; RP2040 releases D0-D7 first
    nop                 side 0b01      ; then the 8T245 turns around and drives the RP2040 side
    nop                 side 0b00 [4]  ; IOSTB low 160 ns: the IO board 245 drives STATUS / AUX_IN
    in pins, 8          side 0b00      ; sample at the end of the strobe
    push noblock        side 0b01 [1]  ; IOSTB high, give the IO board 245 time to let go
    mov osr, ~null      side 0b11 [1]  ; 8T245 drives J1 again
    out pindirs, 8      side 0b11      ; RP2040 drives D0-D7 again
    jmp delay           side 0b11
write:
    nop                 side 0b10 [4]  ; IOSTB low 160 ns
    nop                 side 0b11 [6]  ; IOSTB high: the latch clocks on this edge, data held 224 ns
delay:
    jmp y-- delay       side 0b11
.wrap
```

17 instructions, so about half of PIO0 stays free. The delay field lets core1 (or DMA) queue a whole timed sequence, such as
"blank, wait 24 µs, strobe line 3, drive data", and the PIO plays it with cycle accuracy.

### 3.5 Core1: the real-time scheduler [proposal]

Core1 runs a fixed tick (start with **50 µs**, five times finer than the ROM's 250 µs) and nothing else: no USB, no flash
writes, no interrupts from the host link. Each tick it:

1. **Coils**: evaluates PPUC pulse envelopes and fast-flip rules (`power`, `holdPower`, `holdPowerActivationTime`,
   `minPulseTime`, `maxPulseTime`, `fastFlipSwitch`, `stopSwitch`) [ppuc] against the latest debounced switches, and writes
   SOL_A, SOL_B, SOL_C, FLSH_LMP when they change. The ROM's rules run every 1 ms [doc]; here a flipper button to coil
   latency of about 50 to 100 µs is expected.
2. **Aux coils 33-40**: AUX_DRV, then the reg 11 shadow with bit 6 low, then with bit 6 high [doc].
3. **Lamp matrix**: section 6.
4. **GI and aux strobes**: always write reg 11 from one shadow byte, as the ROM does [doc], so a strobe pulse never disturbs
   the GI bit.
5. **STATUS**: read every 1 ms. Interlocks gate the coil outputs (section 7); zero cross is time-stamped for the line
   frequency.

Core0 hands core1 new targets through a lock-free double buffer. Core1 never waits on core0.

## 4. Pi to RP2040 link

### 4.1 What PPUC expects [ppuc]

- Half-duplex RS485 at 115200 baud, 8N1, up to 8 boards, opened by libserialport.
- Frames: `0xA5`, type and flags, next board, sequence, epoch, payload, CRC-16/CCITT.
- The host broadcasts a full OutputState (coil, lamp and GI bitmaps) every 4 ms.
- Switches are host-polled through a token chain: the board answers with a full SwitchState or a SwitchNoChange.
- Config, Setup and Mapping at start-up bind bitmap bits to PinMAME numbers and send pulse settings.

### 4.2 Proposal

| Layer | Choice |
|---|---|
| Physical | Pi UART (PL011) ↔ RP2040 UART0, 3.3 V point to point on the same PCB, no RS485 transceiver |
| Speed | 115200 at first, so stock libppuc works. Then **1 to 3 Mbaud** with a small libppuc change (configurable baud and output interval) |
| Protocol | PPUC v2 frames, unchanged. The RP2040 answers as one board (or two board ids, if splitting outputs and switches helps the YAML) |
| Extra GPIO | Pi → RP2040 RUN (reset) and BOOTSEL; Pi ↔ RP2040 SWCLK/SWDIO (flash and debug from the Pi with OpenOCD); RP2040 → Pi IRQ ("switch changed, poll me now") |

Why a UART rather than SPI:
- It is what libppuc already speaks, so the first boot needs no host-side code.
- At 3 Mbaud it carries 300 KB/s. A SAM OutputState is about 60 bytes (40 coil bits, 80 lamp bits, GI), so even a 1 ms
  output interval uses about 20 % of the link.
- Two pins. That matters on the RP2040 (section 9.2).

SPI (Pi as master at 10 to 30 MHz, RP2040 as PIO or hardware slave) stays an option if per-lamp brightness or LED strips
ever need more bandwidth. The frame format would not change, only the transport class in libppuc.

### 4.3 Latency budget [proposal]

| Step | Stock PPUC | Tuned |
|---|---|---|
| switch debounce on the RP2040 | 1-3 ms (configurable) | same |
| wait for the host's poll | up to one poll cycle | IRQ line triggers an immediate poll |
| PinMAME reacts | emulated ROM timing (1 ms rule granularity, the ROM's own) | same |
| next OutputState | up to 4 ms | 1 ms |
| RP2040 writes the bus | < 50 µs | same |

Flippers and slingshots do not go through the host at all: they run as RP2040 fast-flip rules [ppuc], so their latency is
the core1 tick.

## 5. Switches

### 5.1 What the ROM reads [doc]

- Matrix: **4 strobes x 16 returns = 64 switches**, one strobe every 250 µs, 1 ms full scan, 0 = closed.
- Dedicated: D1-D24 (coin slots, flipper buttons and EOS, tilt, slam, coin door buttons), read every 1 ms.
- DIP switches: 8, read once per OS tick.

The physical wiring on the SAM CPU board connectors (strobe and return voltages, pull-ups, comparators or opto inputs,
connector pinout) is not in either source repo yet (Q1, Q2).

### 5.2 Hardware [proposal]

48 inputs (16 returns + 24 dedicated + 8 DIP) go through **six 74HC165** shift registers in one chain, at 3.3 V, behind
input conditioning that matches whatever the original board does (likely a pull-up to 12 V and a comparator, or a divider
and Schmitt trigger: Q2). The 4 strobes are driven by open-collector drivers (ULN2803-style or discrete MOSFETs) from 4 RP2040
pins.

Cost: 3 RP2040 pins for 48 inputs, instead of 48 pins.

### 5.3 PIO1 scan program [proposal]

One state machine loops forever:
1. Drive strobe n (`set pins`), wait a settle time (start at 20 µs, the original waits 250 µs).
2. Pulse the 165 load line, then shift 48 bits (`in pins, 1` with the clock on side-set) at about 10 MHz: about 5 µs.
3. Push two words (returns for strobe n, plus the dedicated and DIP bits) and move to the next strobe.

A DMA channel copies the words into a ring in RAM. A full 4-strobe scan takes about 100 µs instead of 1 ms. Dedicated
switches are sampled on every strobe, so 4 times per scan.

This follows the structure of PPUC's `SwitchMatrix.cpp` and `SwitchMatrixPIO/*.pio` [ppuc] (one SM walks the strobes, a
second reads the returns, "two identical scans" filter), but PPUC's code reads at most 8 returns on direct GPIOs and caps at
8 rows. Our 16 returns through a shift chain need a new program either way.

### 5.4 Debounce and reporting [proposal]

- Core0 diffs each scan against the last, then applies PPUC's two debounce modes per switch: `standard` (an edge counts
  only after it holds) and `fastFlip` (a close counts at once, an open must hold) [ppuc].
- Changes go into the PPUC switch queue (32 deep) [ppuc] and raise the IRQ line to the Pi.
- Switch numbering follows PinMAME's SAM numbers, so libppuc's mapping is a straight pass-through. The dedicated switch
  PinMAME numbers are already listed in `Tron-Legacy-LE-ROM-Decryption/rom_data/states/dedicated_switches.csv` [doc].

## 6. Lamps

### 6.1 Matrix scan, phase 1 (ROM-compatible) [proposal]

Reproduce what the ROM does [doc]:
- 10 strobe lines (LMP_STB bits 0-7, AUX_LMP bits 0-1) x 8 drive bits (LMP_DRV).
- For each line: LMP_DRV = 0, LMP_STB = 0, AUX_LMP = 0 (blank), wait 24 µs, strobe the next line, then LMP_DRV = its data.
- 1 ms per line, 10 ms frame.
- Lamp state comes from PPUC's lamp bitmap (on/off) [ppuc].

**The IO board has a watchdog fed by the lamp strobe logic** [doc: "DRV_0 is generated from one of the insert matrix flip
flop as an input to a watchdog timer"]. The scan therefore runs from the moment the RP2040 enables the bus, whether or not
the Pi is connected, and stops only when we want the IO board to shut down (Q5).

### 6.2 Brightness, phase 2 [proposal]

The bus docs §10 [doc] show the existing IO board can do much finer lamp PWM than the ROM's 4 levels, without hardware
changes: at the start of each line slot, write every lamp that should be on, then rewrite LMP_DRV as each lamp's on-time
ends ("edge-sorted PWM", at most 9 writes per slot). With the PIO delay field this is just a sorted list of commands per
slot, built by core1.

PPUC's OutputState carries lamps as bits [ppuc], so dim levels (the ROM's 1/3 and 2/3 planes, and fades) are lost today.
Getting them needs either a PPUC protocol extension (a lamp brightness payload) or a dedicated "lamp levels" frame type
negotiated through the Admin frame. Proposed for phase 2, after the board works with on/off lamps.

### 6.3 Strobed aux boards (Tron LE ramp tubes and similar) [proposal]

Some SAM games hang extra boards off AUX_DRV and the reg 11 strobes [doc]. Tron LE uses ESTB and DSTB for the two RGB ramp
tubes, driven by the ROM with 4-bit BCM [doc], and PinMAME exposes them as lamps 101-106 [doc: `io/README.md`, PinMAME
`sam.c`]. The firmware gets a generic "aux latch device" configured per game: strobe bit, which AUX_DRV bits, which PPUC lamp
numbers. Phase 1 drives them on/off; with phase 2 brightness they get BCM or edge-sorted PWM like the matrix.

## 7. Safety [proposal]

| Risk | Mitigation |
|---|---|
| RP2040 boots or crashes with coils latched on (the latches hold their last value [doc]) | J1 buffers disabled at reset (IOSTB pulled high by the IO board). NBRESET held asserted until the firmware is configured (Q6: confirm NBRESET clears the latches). RP2040 hardware watchdog enabled; its reset path disables the buffers. |
| Pi hangs or the link drops | No valid OutputState for 50 ms → all coil registers written 0, fast-flip rules disabled, lamps keep scanning (IO board watchdog). PPUC has the same idea host-side [ppuc]. |
| Host asks for a coil too long | PPUC board-owned envelopes: `maxPulseTime` on every coil, enforced in core1 even for host-driven coils [ppuc]. |
| High voltage missing or door open | STATUS interlock bits gate coil outputs, like the ROM's mask at 0x3b984 [doc]. Which coils stay allowed without 50 V is Q7. |
| Lamp driver fault | STATUS bits 3-4 reported to the host as switches (the ROM ignores them [doc]). |
| Bus contention during STATUS reads | 8T245 DIR flips before IOSTB falls and back after it rises (section 3.4). |

## 8. Display and sound [proposal]

These are on the original CPU board, so the replacement has to provide them, but they belong to the Pi side, not the RP2040.

- **Display, two options** (Q8):
  - **A. Keep the original 128x32 DMD.** PinMAME already renders the 16-shade frame. The original Xilinx scans the display
    at 62.67 Hz, 12 slots of 41.55 µs per row, planes weighted 1/2/4/5 [doc]. A second small RP2040 (or the four free state
    machines on this one, if pins allow) receives frames from the Pi over SPI and generates the DMD signals with PIO. PPUC's
    `dmdreader` firmware [ppuc] already decodes SAM DMD signals, which documents their timing from the other side.
  - **B. Replace it with an LED panel** driven by ZeDMD, which ppuc-pinmame supports today through libdmdutil [ppuc]. No new
    firmware, but it changes the machine.
- **Sound**: PinMAME emulates the SAM sound system and ppuc-pinmame plays it through SDL [ppuc]. On the board: Pi I2S → a
  stereo DAC → an amplifier sized for the cabinet speakers, if the original amplifier is on the CPU board (Q9). The volume
  buttons are dedicated switches handled by the ROM, so volume stays the ROM's job.

## 9. Hardware

### 9.1 Pi choice [proposal]

Pi 4 or Pi 5 runs PinMAME's ARM7 SAM core comfortably (inferred, to confirm with a benchmark: Q10). Two packaging options:
- a carrier board in the SAM CPU board footprint with a 40-pin header for a standard Pi (cheapest, easy to swap);
- a Compute Module 4 / 5 socket (better mechanically, eMMC, more robust in a vibrating cabinet).

Default here: 40-pin header, keeping the Pi signals on the standard GPIO numbers so a CM carrier stays possible later.

### 9.2 RP2040 pin budget [proposal]

| Function | GPIOs |
|---|---|
| J1 D0-D7 + A0-A3 (consecutive, for `out pins, 12`) | 12 |
| IOSTB, 8T245 DIR (side-set, consecutive) | 2 |
| NBRESET | 1 |
| J1 buffer OE | 1 |
| 74HC165 chain: LOAD, CLK, DATA | 3 |
| Switch strobes 1-4 | 4 |
| UART0 TX, RX to the Pi | 2 |
| IRQ to the Pi | 1 |
| **Total** | **26 of 30** |

The 4 spare GPIOs (including ADC pins) can carry a status LED and a 5 V supply monitor. RUN, SWD and BOOTSEL are dedicated
RP2040 pins, wired to Pi GPIOs.

If the DMD driver (8.A) has to share this RP2040, it will not fit. The fallback is an **RP2350B** (48 GPIO, 3 PIO blocks,
12 state machines), which runs the same firmware. Alternatively a second RP2040 for the display.

### 9.3 Power [proposal]

The SAM CPU board is fed by the IO power board; which rails and on which connector is Q3. The new board needs 5 V at about
3 to 5 A for a Pi 5 (less for a Pi 4), 3.3 V for the RP2040 from its own regulator, and 12 V only if the switch matrix needs
it. A supervisor holds the RP2040 in reset until 3.3 V and 5 V are stable.

## 10. Software

### 10.1 RP2040 firmware [proposal]

- Base: PPUC `io-boards` (PlatformIO, Arduino earlephilhower core, pico-sdk PIO calls) [ppuc], as a new board type
  ("SAM_CPU"), so the protocol code, config parser and pulse envelope logic are reused rather than rewritten. That makes the
  firmware GPLv3 (Q11).
- New code: the J1 bus PIO program and scheduler (core1), the 165-chain switch scanner, the SAM lamp matrix, aux latch
  devices, the STATUS reader and the safety rules above.
- Core split: PPUC io-boards runs the bus and switches on core0 and LED effects on core1 [ppuc]. Here core1 becomes the SAM
  real-time scheduler instead, and LED effects (unused on SAM) are compiled out.

### 10.2 Pi side [proposal]

- `ppuc-pinmame` with a SAM game folder: `io-boards.yaml` with `platform: SAM`, the coil list (PinMAME numbers 1-32, aux
  33-40), 80 lamps, 64 matrix switches, the dedicated switches, plus pulse and fast-flip settings per coil.
- A generator script that builds that YAML from the ROM data already extracted for Tron (`rom_data/io/coils.csv`,
  `io/bus/lamp_matrix_map.csv`, `dedicated_switches.csv`), so other SAM titles follow the same route.
- libppuc changes, small and upstreamable: configurable baud rate and output interval; later the lamp brightness
  extension (section 6.2).
- Check: libppuc forces GI on for non-WPC platforms [ppuc], while the SAM ROM switches the GI relay itself (about 40 call
  sites in Tron [doc]). GI should follow PinMAME instead (Q12).

### 10.3 Rejected alternative: raw bus pass-through

Hook PinMAME's emulated SAM IO handlers and forward every register write to the RP2040, which replays them on J1. It would
reproduce the ROM exactly, but it needs about 57,000 accesses per second [doc] with emulator timing jitter on a non-real-time
host, it bypasses PPUC's logical model and safety envelopes, and it keeps the ROM's coarse lamp and coil timing. Kept only as a
debug mode for comparing the two paths on a logic analyzer.

## 11. Open questions for Vincent

| # | Question | Why it matters | Default if no answer |
|---|---|---|---|
| Q1 | Can you share the SAM CPU board schematic pages (switch matrix, dedicated inputs, J1, power, DMD and audio connectors)? The Shrek manual you used for the IO board probably has them. | Section 5 and 9.3 need the real connector pinouts and input circuits. | Wait for it before the schematic. |
| Q2 | How are switch strobes and returns conditioned on the original CPU board (voltage, pull-ups, comparators)? | Input stage design. | 12 V pull-ups, comparator to 3.3 V. |
| Q3 | J1 pins 9, 10, 11, 17, 19: ground, power or unused? Which connector powers the CPU board, and with which rails? | Power design, ground return on the ribbon. | Treat as ground. |
| Q4 | Can you put a scope (or the analyzer at 100 MS/s+) on IOSTB, one address and one data line at the IO board? | Confirms the PIO timing constants and edge rates. | Use the conservative timings in 3.3. |
| Q5 | What exactly does the IO board watchdog need (which line, how often, timeout), and what does it shut down when it trips? | Section 6.1 must never starve it. | Keep the ROM's 1 ms strobe cadence. |
| Q6 | Does NBRESET clear the output latches on the IO board? | Section 7, safe power-up. | Assume yes, verify on the bench with coil power off. |
| Q7 | Which coils may fire without 50 V present (if any)? | Interlock gating rule. | Gate all coils on both interlocks. |
| Q8 | Keep the original DMD (more firmware) or switch to a ZeDMD-style LED panel (works today)? | Section 8, and whether a second MCU or an RP2350B is needed. | Keep the original DMD; ZeDMD for bring-up. |
| Q9 | Is the audio amplifier on the original CPU board? | Section 8. | Yes: add DAC + amplifier. |
| Q10 | Pi 4, Pi 5 or a Compute Module? Header or CM socket? | Board outline and power. | Pi 5 on a 40-pin header. |
| Q11 | GPLv3 for the firmware (reusing PPUC io-boards) and an open hardware licence (PPUC boards use TAPR OHL) OK? | Licensing of this repo. | GPLv3 firmware, CERN-OHL-S hardware. |
| Q12 | Is "UART at 1 to 3 Mbaud with PPUC frames" acceptable as the high speed bus, or did you have SPI or a parallel bus in mind? | Section 4. | UART. |
| Q13 | Which SAM titles must this support first besides Tron LE? | Aux latch devices and game YAMLs. | Tron LE, then any SAM title without aux boards. |

## 12. Proposed plan

1. **Bench bring-up of the J1 bus**: an RP2040 dev board + the two level shifters on a prototype, the PIO bus program, and a
   logic analyzer next to a capture from the original CPU board. Coil power off.
2. **Lamp matrix + watchdog** running standalone on the IO board, with a test pattern.
3. **Switch scanner** on a prototype input stage.
4. **PPUC integration**: the RP2040 as a PPUC board over UART at 115200, Tron LE YAML, PinMAME running the ROM on the Pi.
   First full game.
5. **Coils with safety**: fast-flip rules, envelopes, interlocks, host-loss timeout. Then coil power on.
6. **Speed-up**: 1-3 Mbaud, 1 ms outputs, IRQ-driven polling.
7. **Display and sound** (per Q8 and Q9).
8. **PCB** in the SAM CPU board footprint.
9. **Phase 2**: lamp brightness, aux tube PWM, other SAM titles.

# Stern SAM replacement CPU board: architecture

Status: **draft for review**. Nothing here is built yet. Section 11 lists what needs Vincent's answer or a
measurement before the schematic starts.

Sources this document builds on:
- **Bus docs**: [Tron-Legacy-LE-ROM-Decryption/io/bus](https://github.com/Ashram56/Tron-Legacy-LE-ROM-Decryption/tree/main/io/bus)
  (`README.md`, `CPU_BOARD_IO.md` and the CSVs). Register map, ISR schedule and every timing number come from there.
- **J1 schematic reading**: [Stern-SAM-Databus-Analysis](https://github.com/Ashram56/Stern-SAM-Databus-Analysis)
  (`IO board analysis`). Pinout, pull resistors and logic families come from there.
- **Stern SAM manual extracts** in [`reference/`](reference/), shared by Vincent on 2026-10-06 (taken from the Indiana
  Jones manual; the SAM boards are the same across titles apart from minor variants):
  - [IO power driver board schematic](reference/Stern_SAM_Manual-IO_Power_Driver_Board_Schematic.pdf), 520-5249-00 Rev A;
  - [CPU/Sound board schematic, layout and parts](reference/Stern_SAM_Manual-CPU_Sound_Board_Schematic.pdf), 520-5246-00 Rev G;
  - [backbox wiring](reference/Stern_SAM_Manual-Backbox_Wiring.pdf),
    [playfield switch and lamp wiring](reference/Stern_SAM_Manual-Playfield_Switch_Lamp_Wiring.pdf),
    [cabinet and coin door wiring](reference/Stern_SAM_Manual-Cabinet_Coin_Door_Wiring.pdf).
- **PPUC**: [github.com/PPUC](https://github.com/PPUC), read on 2026-10-06: `ppuc/docs/STACK.md`, `ppuc/docs/V2_PROTOCOL.md`,
  `io-boards/src/PPUCProtocolV2.h`, `io-boards/src/IODevices/SwitchMatrix*`, `libppuc/src/PPUC.cpp`.

Statements are tagged **[doc]** (bus docs and schematic notes), **[io-sch]** (IO board schematic), **[cpu-sch]** (CPU/Sound board
schematic), **[ppuc]** (PPUC source), or **[proposal]** (a design choice made here, open to change).

---

## 1. Summary

```
   ┌──────────────────────────── Raspberry Pi (4 / 5 or CM4 / CM5) ───────────────────────────┐
   │ ppuc-pinmame: PinMAME runs the original SAM ROM, libppuc maps it to boards,              │
   │ libdmdutil drives the display, SDL audio goes out over I2S                               │
   └──────┬──────────────────────┬─────────────────────────┬──────────────────────┬───────────┘
          │ UART (or USB)        │ GPIO: RUN, BOOTSEL,     │ I2S                  │ display link
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
2. **The Pi to RP2040 link is on-board, with no RS485**: a GPIO UART at 1 to 3 Mbaud as the default and native USB as the
   second path, both carrying PPUC v2 frames, plus GPIO lines for reset, flashing and a "switch changed" interrupt
   [proposal]. Section 4 compares them.
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
| Switch matrix, 4 strobes x 16 returns (64) in the ROM; 8 strobe drivers on the board | 74LV273 + eight 2N3904 strobes (J1), LM339 returns (J6, J12) [cpu-sch] | RP2040 PIO1 |
| 24 dedicated switches + 8 DIP switches | 74LVC245 inputs on J2, J3, J13 [cpu-sch] | RP2040 PIO1 (same shift chain) |
| Game logic | ROM on the AT91 | PinMAME on the Pi |
| DMD, 128 x 32, 16 shades | Xilinx CPLD scanner, 7 signals on the 14-pin J5 [cpu-sch] | Pi + display driver (section 8) |
| Audio, 24 kHz stereo + volume | PCM1755 DAC, OPA2353, two TDA2030A amplifiers, speakers on J10 [cpu-sch] | Pi I2S + DAC + amplifier (section 8) |
| NVRAM, real-time clock | battery SRAM, DS1302-style RTC | Pi storage (PinMAME `nvram/`), Pi 5 RTC or an I2C RTC |
| LED sign port (9600 baud) | USART1 | optional, a Pi UART |

## 3. The J1 bus, electrically and logically

### 3.1 Signals [doc] [io-sch]

J1 is a 2x10 header on both boards (IO board J1, CPU board J9 [cpu-sch]).

| J1 pin | Signal | IO board side (every line also has 100 Ω in series and 22 pF to ground) |
|---|---|---|
| 7, 5, 3, 1, 2, 4, 6, 8 | D0 … D7 (pin 7 = D0, 5 = D1, 3 = D2, 1 = D3, 2 = D4, 4 = D5, 6 = D6, 8 = D7) | 10 k pull-down; 74HC245 input buffer U18; STATUS and AUX_IN buffers drive these pins on reads |
| 12, 14, 16, 18 | A0, A1, A2, A3 | 4.7 k pull-up to 5 V; two 74LS138 (U19, U20) |
| 15 | IOSTB (active low) | 4.7 k pull-up; enables both 74LS138 |
| 13 | NBRESET (active low) | **10 k pull-up to 5 V** (R144), 220 Ω + 470 pF into the watchdog chip (section 3.6) |
| 19, 20 | GND | |
| 9, 10, 11, 17 | not connected | |

Only two of the twenty wires are ground. The new board should keep both, and the ribbon should stay short.

How the IO board uses the data lines [io-sch]:
- **Writes**: U18 is a 74HC245 at 5 V with DIR tied high and its enable tied low, so it is a one-way input buffer that is
  always on. It feeds the 74HCT273 latches (and a 74LS74 for AUX_LMP).
- **STATUS read**: U22, a 74HC245, drives J1 D0-D7 only while the STATUS decode is active. D0 = 20 V interlock, D1 = 50 V
  interlock, D2 = zero cross (through a transistor), D3 = LMP1STAT, D4 = LMP2STAT, **D5-D7 are tied low**.
- **AUX_IN read**: U24, a 74HC245, drives J1 from J3 pins 1-8 (each with 39 k in series and a 1 k pull-up to 5 V).
- Both read buffers drive J1 with **5 V levels**.

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
- **What Stern did** [cpu-sch]: the original CPU board drives J9 through two **74LVC245 at 3.3 V** (U25, U26), with 47 pF on
  each line. So 3.3 V drive into the HC245 works in the field, but below its guaranteed threshold. A 74LVC245 (5 V tolerant
  inputs, 3.3 V outputs) is a proven fallback if the 8T245 causes trouble.
- **NBRESET**: open drain, as on the original, which pulls it low with a 2N3904 transistor on net IORESET [cpu-sch] against the IO
  board's 10 k pull-up. An N-MOSFET (2N7002) driven by the RP2040 does the same and needs no level shifting.
- **Power-up state**: both buffers' OE is pulled to "disabled" until firmware enables them. With the buffers off, the IO
  board's own pull-ups hold IOSTB high, so no latch can clock while the RP2040 boots. The NBRESET MOSFET's gate is pulled
  up, so the IO board is held in reset (all outputs off) until the firmware lets go.
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

### 3.6 What the IO board does on its own [io-sch]

**Reset and watchdog.** U23 is a DS1232 supervisor. Its /RST output drives the board-wide **NRESET** net, which goes to the
/MR (clear) pin of **every** output latch: the four coil and flasher 74HCT273s, LMP_STB, LMP_DRV, AUX_DRV, the aux/GI latch,
and the /CLR pins of the 74LS74 for AUX_LMP. While NRESET is low, every coil, lamp strobe, lamp drive and aux output is off and
the GI relay is released. NRESET goes low when any of these happens:

| Trigger | Wiring | Behaviour (DS1232 datasheet values, to verify on the bench) |
|---|---|---|
| 5 V supply low | DS1232 Vcc monitor, TOL set by a 0 Ω option (R146 / R147) | reset while 5 V is under 4.5 V or 4.75 V |
| CPU board pulls **NBRESET** low | J1 pin 13 → 220 Ω → /PBRST, 10 k pull-up, 470 pF | debounced push-button input: must stay low at least ~20 ms to register |
| **Watchdog**: no falling edge on **DRV0** in time | /ST = DRV0, TD tied to ground | timeout 62.5 ms minimum, 150 ms typical, 250 ms maximum |

After a trigger clears, NRESET stays low for at least 250 ms. The yellow LED L18 lights while the board is in reset.

**DRV0 is lamp strobe line 0.** It comes from bit 0 of the LMP_STB latch (U2) and also drives strobe MOSFET Q33. So the
watchdog is fed every time lamp strobe line 0 turns off. The ROM does this every 10 ms, about 6 times faster than the
shortest timeout. If the new board ever stops scanning lamps, the IO board shuts every output off within 62.5 to 250 ms,
which is a useful last line of defence and the reason the scan must start before anything else is enabled.

**Driver speeds**, which set the floor for any finer PWM in phase 2:
- Coils and flashers: STP22NE10L MOSFETs, gate driven through **39 k with 10 nF** to ground. That is an RC of about 0.4 ms,
  so a coil takes several hundred µs to switch fully. Coil hold PWM periods should stay at 1 ms or longer, as the ROM's are,
  and very short pulses will not reach full current.
- Lamp strobes: STP19NE06L, gate through 39 k (no extra capacitor), so tens of µs.
- Lamp drives: VN02N high-side smart switches through 6.8 k. Their status outputs are wired-OR into LMP1STAT and LMP2STAT.
- The ROM's 24 µs blank between strobe lines is in line with these. The exact edge times still need a scope (Q4).

**GI relay**: bit 0 of the aux/GI latch drives a 2N3904 that energises relay RLY1 (FRL264, 20 V coil). The GI strings run
through its normally closed contacts, which is why 0 = GI on.

**Bit order inside the board.** The 74HCT273s are wired with scrambled pin numbers: bus D0 enters chip pin D4, D4 enters D0,
and so on. Following the drawing, SOL_B bus bit 0 drives Q1 (J8 pin 1) and LMP_DRV bus bit 0 drives U10 (J13 pin 1). The
transistor tables in Stern-SAM-Databus-Analysis appear to use the chip's own pin names instead, which gives different
answers (SOL_B bit 0 = Q5, LMP_DRV bit 0 = J13 pin 9). This does not change the firmware, which only needs the ROM's bus bits,
but it matters for wiring and test fixtures (Q16).

## 4. Pi to RP2040 link

### 4.1 What PPUC expects [ppuc]

- Half-duplex RS485 at 115200 baud, 8N1, up to 8 boards, opened by libserialport.
- Frames: `0xA5`, type and flags, next board, sequence, epoch, payload, CRC-16/CCITT.
- The host broadcasts a full OutputState (coil, lamp and GI bitmaps) every 4 ms.
- Switches are host-polled through a token chain: the board answers with a full SwitchState or a SwitchNoChange.
- Config, Setup and Mapping at start-up bind bitmap bits to PinMAME numbers and send pulse settings.

### 4.2 Proposal

No RS485: the RP2040 sits on the same board as the Pi, so the link is either the Pi's GPIO UART or USB (Vincent, 2026-10-06).
Both get wired, and the firmware can speak PPUC frames on either.

| Layer | Choice |
|---|---|
| Primary transport | Pi UART (PL011) ↔ RP2040 UART0, 3.3 V point to point. 115200 at first, so stock libppuc works; then **1 to 3 Mbaud** with a small libppuc change (configurable baud and output interval) |
| Second transport | Pi USB ↔ RP2040 native USB (on-board, no connector). The RP2040 enumerates as a CDC serial port, which libppuc's libserialport opens like any other port, at full-speed USB rates and with no baud setting to change. The same USB port does firmware updates (BOOTSEL mode, `picotool`) |
| Protocol | PPUC v2 frames, unchanged, on either transport. The RP2040 answers as one board (or two board ids, if splitting outputs and switches helps the YAML) |
| Extra GPIO | Pi → RP2040 RUN (reset) and BOOTSEL; Pi ↔ RP2040 SWCLK/SWDIO (flash and debug from the Pi with OpenOCD); RP2040 → Pi IRQ ("switch changed, poll me now") |

Why the UART is the default:
- It is deterministic: no enumeration, no USB stack on the RP2040, no host-controller scheduling (USB full speed polls in
  1 ms frames), and nothing to re-enumerate if a coil spike glitches the bus.
- At 3 Mbaud it carries 300 KB/s. A SAM OutputState is about 60 bytes (40 coil bits, 80 lamp bits, GI), so even a 1 ms
  output interval uses about 20 % of the link.
- Two pins. That matters on the RP2040 (section 9.2).

USB costs no RP2040 GPIO, needs no libppuc change at all, and has more bandwidth, so it is a good choice for bring-up and the
obvious place to go if phase 2 lamp brightness needs more than the UART carries. Which one ships can be decided on the bench
by measuring switch-to-coil latency on both (Q12).

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

### 5.2 The original circuit [cpu-sch]

| Connector | Function | Circuit |
|---|---|---|
| J1, 1x9, key pin 2 ("SWITCH COLUMNS") | **8 strobes** on pins 1 and 3-9 | 74LV273 latch (SWSTB) → eight independent 2N3904 open-collector drivers (1 k base resistors); each line has a 1 k pull-up to +4.5 V and 0.1 µF to ground |
| J6, 1x10, key pin 4, and J12, 1x10, key pin 5 ("SWITCH ROWS") | **16 returns**, 8 per connector, plus a ground pin each | each return: series diode (SMT4148) from the connector, 220 Ω, 1 k pull-up to **+4.5 V**, 0.1 µF, into an **LM339** comparator against VREF (3.3 k / 3.3 k divider of 4.5 V, about 2.25 V, 22 µF); comparator outputs pulled up to 3.3 V (10 k) and read through 74LVC245s |
| J2 (1x12, key 5), J3 (1x10, key 3), J13 (1x10, key 2) | **24 dedicated inputs**, 8 per connector, plus ground pins | switches to ground; 1 k pull-up to +4.5 V (the parts list says 1.5 k), 39 k series, 47 pF, read through 5 V-tolerant 74LVC245s |
| SW1 | 8 DIP switches | on the board, 1 k pull-ups to 3.3 V |

+4.5 V is the 5 V rail through a diode (D10). So the matrix runs at about 4.5 V, not 12 V: a closed switch pulls its return
low through the playfield diode, the return diode and the active strobe transistor. Stern's manual describes it as a
"4 x 16 matrix of Switch Drives and Switch Returns" plus a "2 x 16" dedicated matrix that includes the 8 DIP positions.

The board has **8** strobe drivers, but the ROM scans 4 and the Indiana Jones playfield wiring diagram only uses switch
drives 1-4 (Q15).

### 5.3 Hardware [proposal]

- **Returns**: copy the original front end (1 k pull-up to 4.5 V, 220 Ω + 0.1 µF, LM339 against 2.25 V). The LM339's
  open-collector outputs, pulled up to 3.3 V, feed the shift registers directly. It is cheap, proven on these harnesses and
  immune to the ground offsets of a long cable.
- **Dedicated switches**: the same 1.5 k pull-up and 39 k / 47 pF filter, then either an LM339 stage like the returns or a
  divider into the 3.3 V shift registers.
- **Shift chain**: 48 inputs (16 returns + 24 dedicated + 8 DIP) through **six 74HC165** at 3.3 V.
- **Strobes**: **8** open-collector outputs, like the original, from a 74HC595 that shares the shift clock (below) and drives
  8 low-side transistors or a ULN2803-class array.

Cost: 5 RP2040 pins (shift clock, 165 load, 165 data, 595 data, 595 latch) for 48 inputs and 8 strobes.

### 5.4 PIO1 scan program [proposal]

One state machine loops forever:
1. Pulse the 165 load line, then clock 48 bits at about 10 MHz (about 5 µs). On every clock it does `in pins, 1` from the 165
   chain and `out pins, 1` to the 595, so the strobe pattern for the *next* strobe ends up in the 595 during the last 8 clocks.
2. Pulse the 595 latch: the next strobe turns on.
3. Push two words (returns for the strobe that was active, plus the dedicated and DIP bits) and wait a settle time (start
   at 20 µs; the original waits 250 µs, and the 0.1 µF return filters need to be checked against a shorter time).

A DMA channel copies the words into a ring in RAM. A full 4-strobe scan takes about 100 µs instead of 1 ms (200 µs with 8
strobes). Dedicated switches are sampled on every strobe.

This follows the structure of PPUC's `SwitchMatrix.cpp` and `SwitchMatrixPIO/*.pio` [ppuc] (one SM walks the strobes, a
second reads the returns, "two identical scans" filter), but PPUC's code reads at most 8 returns on direct GPIOs and caps at
8 rows. Our 16 returns through a shift chain need a new program either way.

### 5.5 Debounce and reporting [proposal]

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

**The IO board's watchdog is fed by lamp strobe line 0** [io-sch, section 3.6]: a falling edge on DRV0 at least every 62.5 ms
(worst case of the DS1232), or every output on the IO board is cleared. The scan therefore runs from the moment the RP2040
enables the bus, whether or not the Pi is connected. Stopping the scan is a deliberate way to shut the IO board down.

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
| RP2040 boots or crashes with coils latched on (the latches hold their last value [doc]) | J1 buffers disabled at reset (IOSTB pulled high by the IO board). NBRESET held low (gate pull-up on the open-drain MOSFET) until the firmware is configured: on the IO board this clears every output latch through the DS1232 [io-sch]. RP2040 hardware watchdog enabled; its reset path disables the buffers and asserts NBRESET. |
| RP2040 hangs with the bus enabled | The lamp scan stops, so the IO board's own watchdog clears every output within 62.5-250 ms [io-sch]. |
| Pi hangs or the link drops | No valid OutputState for 50 ms → all coil registers written 0, fast-flip rules disabled, lamps keep scanning. For a hard stop, assert NBRESET for at least 20 ms: the IO board then clears everything and holds it for at least 250 ms. PPUC has the same idea host-side [ppuc]. |
| Host asks for a coil too long | PPUC board-owned envelopes: `maxPulseTime` on every coil, enforced in core1 even for host-driven coils [ppuc]. |
| High voltage missing or door open | STATUS interlock bits gate coil outputs, like the ROM's mask at 0x3b984 [doc]. Which coils stay allowed without 50 V is Q7. |
| Lamp driver fault | STATUS bits 3-4 reported to the host as switches (the ROM ignores them [doc]). |
| Bus contention during STATUS reads | 8T245 DIR flips before IOSTB falls and back after it rises (section 3.4). |

## 8. Display and sound [proposal]

These are on the original CPU board, so the replacement has to provide them, but they belong to the Pi side, not the RP2040.

- **Display, two options** (Q8):
  - **A. Keep the original 128x32 DMD.** PinMAME already renders the 16-shade frame. The original scans the display at
    62.67 Hz, 12 slots of 41.55 µs per row, planes weighted 1/2/4/5 [doc]. The display cable is the 2x7 J5: the 7 signals on
    the odd pins, every even pin ground. They come from the XC95144XL CPLDs through a 74HCT245 at 5 V (U55) [cpu-sch]. In
    buffer order: pin 1 DE, 3 ROWDATA, 5 ROWCLK, 7 COLLATCH_A, 9 PIXCLK, 11 SDATA, 13 COLLATCH_B (read from the drawing;
    confirm with a meter before relying on it). The display's high voltage comes from its own Display Power Supply board (520-5138-00), not the CPU board.
    7 outputs and one state machine is a small PIO job: a second RP2040 (or an RP2350B instead of the RP2040, section 9.2)
    receives frames from the Pi over SPI and generates the signals. PPUC's `dmdreader` firmware [ppuc] already decodes SAM
    DMD signals, which documents their timing from the other side.
  - **B. Replace it with an LED panel** driven by ZeDMD, which ppuc-pinmame supports today through libdmdutil [ppuc]. No new
    firmware, but it changes the machine.
- **Sound**: PinMAME emulates the SAM sound system and ppuc-pinmame plays it through SDL [ppuc]. The original amplifier is on
  the CPU board [cpu-sch]: a PCM1755 DAC (I2S, with the 3-wire volume control), an OPA2353 buffer and **two TDA2030A power
  amplifiers on ±12 V**, with the speakers on the 1x4 J10 (pin 1 amplifier U50, pin 2 amplifier U51, pins 3-4 ground) [cpu-sch].
  The DAC runs from its own +5 V (LM340T-5 from +12 V). The new board does the same: Pi I2S → a stereo DAC → two
  amplifiers on J10, pin-compatible with the cabinet harness. The volume buttons are dedicated switches handled by the ROM,
  so volume stays the ROM's job.

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
| Switch chain: shift clock, 165 load, 165 data, 595 data, 595 latch | 5 |
| UART0 TX, RX to the Pi | 2 |
| IRQ to the Pi | 1 |
| **Total** | **24 of 30** |

The 6 spare GPIOs (including ADC pins) can carry a status LED, a 5 V supply monitor and a spare. RUN, SWD and BOOTSEL are dedicated
RP2040 pins, wired to Pi GPIOs.

If the DMD driver (8.A, 7 outputs) has to share this RP2040, it is one pin short. The fallback is an **RP2350B** (48 GPIO, 3 PIO blocks,
12 state machines), which runs the same firmware. Alternatively a second RP2040 for the display.

### 9.3 Power [proposal]

The CPU board is fed from IO board connector **J16** (15-pin KK156) [io-sch]. On the CPU board it arrives on **J11, 1x6**:
pin 1 +5 V, pin 3 -12 V, pin 6 +12 V, pins 2, 4, 5 ground, each through a ferrite bead and 47 µF [cpu-sch]. On board, an
LT1086 makes 3.3 V from 5 V and an LT1503 makes the AT91 core voltage. J16 on the IO board:

| J16 pin | Rail |
|---|---|
| 1 | -12 V |
| 2, 3 | +12 V |
| 4-8 | +5 V |
| 9-13, 15 | GND |
| 14 | key |

The +5 V comes from an **LM338K (5 A) on the IO board**, which also powers the IO board's own logic. ±12 V come from a bridge
and capacitors on the IO board. The new board needs:
- +5 V for the Pi, the RP2040 regulator, the switch inputs and the DMD buffer. A Pi 4 needs up to 3 A; a Pi 5 asks for 5 A,
  which the LM338K cannot spare. Either use a Pi 4 / CM4 on the existing +5 V, or give the Pi its own buck converter from
  +12 V, if the +12 V supply can carry it (Q14).
- ±12 V for the two audio amplifiers, as on the original.
- 3.3 V for the RP2040 from its own regulator. A supervisor holds the RP2040 in reset until 3.3 V and 5 V are stable.

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
  sites in Tron [doc]). GI should follow PinMAME instead (Q17).

### 10.3 Rejected alternative: raw bus pass-through

Hook PinMAME's emulated SAM IO handlers and forward every register write to the RP2040, which replays them on J1. It would
reproduce the ROM exactly, but it needs about 57,000 accesses per second [doc] with emulator timing jitter on a non-real-time
host, it bypasses PPUC's logical model and safety envelopes, and it keeps the ROM's coarse lamp and coil timing. Kept only as a
debug mode for comparing the two paths on a logic analyzer.

## 11. Open questions for Vincent

Answered so far:

| # | Question | Answer | Where |
|---|---|---|---|
| Q3 | J1 pins 9, 10, 11, 17, 19, and CPU board power | 9, 10, 11, 17 not connected; 19, 20 ground. Power from IO board J16 (+5 V, ±12 V) | IO schematic; 3.1, 9.3 |
| Q5 | What feeds the IO board watchdog | DS1232: falling edge on lamp strobe line 0 (DRV0) at least every 62.5 ms worst case | IO schematic; 3.6 |
| Q6 | Does NBRESET clear the latches? | Yes: NBRESET → DS1232 /PBRST → NRESET → /MR of every output latch; at least 250 ms reset | IO schematic; 3.6, 7 |
| Q1 | CPU/Sound board schematic | Shared as PDF; now in `reference/` | 5.2, 8, 9.3 |
| Q2 | Switch input conditioning | 4.5 V pull-ups, LM339 comparators on the returns, 8 independent 2N3904 open-collector strobes | CPU schematic; 5.2 |
| Q9 | Audio amplifier on the CPU board? | Yes: PCM1755 + two TDA2030A on ±12 V, speakers on J10 | CPU schematic; 8 |
| Q12 | The high speed bus | GPIO or USB, no RS485 (Vincent). Both wired; UART default | 4.2 |

Still open:

| # | Question | Why it matters | Default if no answer |
|---|---|---|---|
| Q4 | Can you put a scope (or the analyzer at 100 MS/s+) on IOSTB, one address and one data line at the IO board, and on a coil MOSFET gate? | Confirms the PIO timing constants and the real coil switching time (39 k / 10 nF gate). | Use the conservative timings in 3.3. |
| Q7 | Which coils may fire without 50 V present (if any)? | Interlock gating rule. | Gate all coils on both interlocks. |
| Q8 | Keep the original DMD (7 signals on J5, needs a PIO driver) or switch to a ZeDMD-style LED panel (works today)? | Section 8, and whether a second MCU or an RP2350B is needed. | Keep the original DMD; ZeDMD for bring-up. |
| Q10 | Pi 4, Pi 5 or a Compute Module? Header or CM socket? | Board outline and power (see Q14). | Pi 4 or CM4 on a 40-pin header / socket. |
| Q11 | GPLv3 for the firmware (reusing PPUC io-boards) and an open hardware licence (PPUC boards use TAPR OHL) OK? | Licensing of this repo. | GPLv3 firmware, CERN-OHL-S hardware. |
| Q13 | Which SAM titles must this support first besides Tron LE? | Aux latch devices and game YAMLs. | Tron LE, then any SAM title without aux boards. |
| Q14 | How much current can the IO board's +5 V (LM338K, 5 A, shared with its own logic) and +12 V spare for the CPU board? | A Pi 5 wants 5 A at 5 V. | Pi 4 on +5 V; leave room for a 12 V → 5 V buck. |
| Q15 | The CPU board has 8 independent strobe drivers but the ROM scans 4 and Indiana Jones wires drives 1-4. Do any SAM games use strobes 5-8? | Strobe count and scan time. | Drive all 8. |
| Q16 | The 74HCT273 input pins are scrambled (bus D0 → chip D4). Section 3.6 reads SOL_B bit 0 → Q1 / J8-1 and LMP_DRV bit 0 → J13-1, unlike the transistor tables in Stern-SAM-Databus-Analysis. Worth a continuity check? | Wiring docs and test fixtures, not firmware. | Trust the ROM's bus bits; check one coil and one lamp on the bench. |
| Q17 | GI: libppuc forces GI on for non-WPC platforms, but the SAM ROM drives the GI relay itself. Should GI follow PinMAME? | GI behaviour in attract and tilt. | Follow PinMAME (small libppuc change). |

## 12. Proposed plan

1. **Bench bring-up of the J1 bus**: an RP2040 dev board + the two level shifters on a prototype, the PIO bus program, and a
   logic analyzer next to a capture from the original CPU board. Coil power off.
2. **Lamp matrix + watchdog** running standalone on the IO board, with a test pattern.
3. **Switch scanner** on a prototype input stage.
4. **PPUC integration**: the RP2040 as a PPUC board over UART at 115200, Tron LE YAML, PinMAME running the ROM on the Pi.
   First full game.
5. **Coils with safety**: fast-flip rules, envelopes, interlocks, host-loss timeout. Then coil power on.
6. **Speed-up**: 1-3 Mbaud, 1 ms outputs, IRQ-driven polling.
7. **Display and sound** (per Q8; the amplifier copies the original, section 8).
8. **PCB** in the SAM CPU board footprint.
9. **Phase 2**: lamp brightness, aux tube PWM, other SAM titles.

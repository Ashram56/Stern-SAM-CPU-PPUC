# Driver test board firmware (RP2354B)

Pico SDK 2.2, C. Build:

```
cmake -S . -B build -DPICO_SDK_PATH=/path/to/pico-sdk && cmake --build build     # build/dtb.uf2
```

Flash: hold BOOTSEL, press RESET, copy `dtb.uf2` to the RP2350 drive (USB goes through the ADuM3160, full speed).

## What it does

- **Capture** (PIO0, GPIO base 0). SM0 clocks the seven 74HC165 in parallel: 75 cycles at 75 MHz, so exactly one
  sample per microsecond (load 53 ns, SR_CLK 9.4 MHz, Q7 read 107 ns after each rising edge). SM1 samples the 21 direct
  lines (13 aux, 8 CPU strobes) at the same instant (IRQ 0). Two DMA channels write endless rings (1 ms deep).
  Core1 compares each sample with the previous one and queues an event on any change (time in µs since start).
  SM2 watches the 13 aux lines alone at 150 MHz and queues every edge (the IO board aux strobes last 300 ns).
- **Switches** (PIO1, GPIO base 16). SM0 shifts 24 clocks into the two 74HCT595 chains at once (SER_RET 16 stages,
  SER_DED 24 stages) and latches, about 2 µs. Core1 watches the CPU strobes (active low) and reloads the returns of
  the active strobe each time it changes. The CPU board waits about 125 µs per strobe, so the margin is large.
  At power-up SR_CLR_N clears the registers and SR_OE_N stays high: no switch closes until the PC enables the outputs.
- **Rails**: ADC0-3 (GPIO40-43), 100 k / 4.7 k dividers, 16-sample average, reported in mV.

## State bits (events and status)

| word | bits | meaning |
|---|---|---|
| w0 | 0-31 | coils 1-32 (connector level; 0 = output on) |
| w1 | 0-9 | lamp strobes J12 pins 1-6, 8-11 (0 = on) |
| w1 | 10-16 | lamp columns J13 pins 1, 3-8 (1 = on) |
| w1 | 17 | column on J13 pin 10 (or 9, JP1/JP2) |
| w2 | 0-12 | aux: IO J2 pins 1, 2, 3, 5-10, IO J3 pins 9-12 |
| w2 | 13-20 | CPU J1 strobes 1-8 (0 = active) |

## USB protocol (CDC)

Frame: `0xA5, cmd, len (u16 LE), payload, CRC16-CCITT (init 0xFFFF, LE)` over cmd, len, payload. Answer = cmd | 0x40.

| cmd | payload | answer |
|---|---|---|
| 0x01 INFO | | version text |
| 0x02 STATUS | | running u8, now_us u64, lost events u32, switch updates u32, rails 4 x u16 mV, w0 w1 w2 |
| 0x10 START / 0x11 STOP | | capture on / off |
| 0x20 MATRIX | 8 x u16: closed returns per strobe | |
| 0x21 DEDICATED | u32: D-1..D-24 | |
| 0x22 ENABLE | u8 | switch outputs on (SR_OE_N low) / off |
| 0x80 (board to PC) | n x (kind u8, t_us u64, w0, w1, w2) | kind 0 = change, 1 = aux edge (w2 bits 0-12) |

PC side: `../pc/sam_probe.py` (VCD export, checks: coil on too long, several lamp or switch strobes at once, columns
without strobe, lamp scan frozen > 5 ms, rails low).

## Not tested on hardware yet

The board does not exist yet. Points to check at bring-up: 74HC165 timing at 3.3 V (lower the PIO clock if bits
shift), endless DMA rings, event rate on a busy lamp matrix (USB full speed, about 40 000 events/s max).

# SAM universal test board firmware (RP2354B)

Pico SDK 2.2, C. Build:

```
cmake -S . -B build -DPICO_SDK_PATH=/path/to/pico-sdk && cmake --build build     # build/stb.uf2
```

Flash: hold BOOTSEL, press RESET, copy `stb.uf2` to the RP2350 drive (USB goes through the ADuM3160, full speed).
The same image runs on every board; the role comes from the JP9/JP10 solder jumpers (closed = 0):

| JP9 (GPIO27) | JP10 (GPIO28) | role |
|---|---|---|
| open | open | 0 coils |
| closed | open | 1 lamps + aux |
| open | closed | 2 switch matrix |
| closed | closed | 3 dedicated switches |

## What it does

- **Capture** (PIO0). SM0 clocks the six 74HC165 in parallel: 75 cycles at 75 MHz, one sample of the 48 channels
  per microsecond. SM1 samples header A straight on GPIO8-19 at the same instant (IRQ 0). Two DMA channels fill
  endless rings (1 ms deep); core1 queues an event on any change (time in µs since start). SM2 watches header A alone
  at 150 MHz and queues every edge (the IO board aux strobes last 300 ns).
- **Switches** (PIO1). SM0 shifts 48 bits into the 74HCT595 chain (channel 47 first) and latches, about 4 µs.
  Output = static mask (dedicated switches) | drive mask of the active strobe. Up to 8 strobes are read on header A
  (active low); each has a 48-bit drive mask computed by the PC from the closed matrix switches. At power-up
  SR_CLR_N clears the registers and SR_OE_N stays high: nothing closes until the PC enables the outputs.
- **Sync**: START with mode 1 starts the capture and pulls SYNC (J11) low for 100 µs; boards started with mode 2
  begin on that edge, so captures of several boards share the same time origin within about 1 µs.
- **Rails**: ADC0-3 (GPIO40-43), RAILA-D through 100 k / 4.7 k, 16-sample average, reported in mV.

## Channels

Channel c = header × 12 + pin − 1 (A1 = 0, B1 = 12, C1 = 24, D1 = 36); the bit is the line level on the connector
(1 = high). 74HC165 chain k reads channels 8k..8k+7 (D0..D7); 74HCT595 k drives the same channels (QA..QH).
Signal names per role: `pc/stb_probe.py` (`role_map`).

## USB protocol (CDC)

Frame: `0xA5, cmd, len (u16 LE), payload, CRC16-CCITT (init 0xFFFF, LE)` over cmd, len, payload. Answer = cmd | 0x40.

| cmd | payload | answer |
|---|---|---|
| 0x01 INFO | | "stb 0.1", role u8, flash unique id (8 bytes) |
| 0x02 STATUS | | running u8, t_us u64, overflows u32, switch updates u32, rails mV u16 × 4, channels u64, header A u16 |
| 0x10 START | mode u8: 0 now, 1 master (SYNC pulse), 2 wait for SYNC | empty |
| 0x11 STOP | | empty |
| 0x20 MATRIX | strobe pin u8 × 8 (header A pin 0-11, 0xFF unused), drive mask u64 × 8 | empty |
| 0x21 STATIC | drive mask u64 | empty |
| 0x22 ENABLE | u8 (1 = outputs on) | empty |
| 0x80 events (board → PC) | n × 17 bytes: kind u8 (0 sample, 1 header A edge), t_us u64, channels 6 bytes, header A u16 | |

Untested on hardware.

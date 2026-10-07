// RP2354B GPIO map of the SAM CPU board.
//
// Source of truth: hardware/kicad/sam_cpu/mcu.kicad_sch (PR #4) and
// hardware/kicad/README.md "RP2354B GPIO map (two-panel version)".
// Keep this file in step with the schematic.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

// ---- PIO0, GPIO base 0: SAM IO bus on J9 ---------------------------------
// D0-D7 then A0-A3 on consecutive pins, so one `out pins, 12` drives a whole
// address + data word.
#define PIN_BUS_D0 0          // D0-D7 = GPIO0-7
#define PIN_BUS_A0 8          // A0-A3 = GPIO8-11
#define PIN_BUS_IOSTB 12      // side-set bit 0, active low (through 74AHCT541)
#define PIN_BUS_DIR 13        // side-set bit 1, SN74LVC8T245 DIR: 1 = RP2354B drives J9
#define PIN_NBRESET_DRV 14    // high = 2N7002 on = IO board held in reset (pulled up at boot)
#define PIN_BUS_OE_N 15       // low = both J9 buffers enabled (pulled up at boot)

// ---- PIO1, GPIO base 16: switch shift chain ------------------------------
#define PIN_SW_CLK 16         // shared 74HC165 / 74HC595 shift clock (side-set bit 0)
#define PIN_SW_LOAD_N 17      // 165 parallel load (low) + 595 latch (rising edge) (side-set bit 1)
#define PIN_SW_DATA 18        // serial data in from the 165 chain (U30 QH)
#define PIN_STB_DATA 19       // serial data out to the 595 chain (U31 SER)

// ---- PIO2, GPIO base 16: display ------------------------------------------
// HUB75 panel bus. Panel A R1 G1 B1 R2 G2 B2 on DMD_D0-D5, panel B on D6-D11.
#define PIN_DMD_D0 20         // DMD_D0-D11 = GPIO20-31
#define PIN_DMD_CLK 32
#define PIN_DMD_LAT 33
#define PIN_DMD_OE 34         // active low at the panel
#define PIN_DMD_A 35
#define PIN_DMD_B 36
// The original 128x32 DMD on J5 shares DMD_D0-D6 (only one display path runs).
#define PIN_J5_DE 20
#define PIN_J5_ROWDATA 21
#define PIN_J5_ROWCLK 22
#define PIN_J5_COLLATCH_A 23
#define PIN_J5_PIXCLK 24
#define PIN_J5_SDATA 25
#define PIN_J5_COLLATCH_B 26

// ---- Misc -----------------------------------------------------------------
#define PIN_RP_IRQ_N 37       // to the Pi: low = "switch changed, poll me"
#define PIN_GI_PWM 38         // J18 GI dimmer board, PWM (slice 11 A)
#define PIN_AMP_MUTE 39       // audio amplifier mute, high = muted (pull-down on the board)

// Frames from the Pi (Pi is SPI master, mode 0). Read by a PIO1 receiver.
#define PIN_FRAME_MOSI 40
#define PIN_FRAME_CS_N 41
#define PIN_FRAME_SCK 42

#define PIN_SPARE_43 43
#define PIN_LINK_UART_TX 44   // UART0 TX (function 2 on GPIO44)
#define PIN_LINK_UART_RX 45   // UART0 RX
#define PIN_VMON_5V 46        // ADC channel 6
#define PIN_VMON_12V 47       // ADC channel 7

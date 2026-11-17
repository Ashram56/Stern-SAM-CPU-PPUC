/*
 * Board header for the SAM driver output test board (RP2354B, 12 MHz crystal, 150 MHz).
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
// NOTE: also included by the assembler: preprocessor directives only.
#ifndef _BOARDS_DTB_RP2354B_H
#define _BOARDS_DTB_RP2354B_H

pico_board_cmake_set(PICO_PLATFORM, rp2350)

#define DTB_RP2354B
// RP2354B: RP2350B die (48 GPIOs) with 2 MB of flash in the package.
#define PICO_RP2350A 0
#define PICO_RP2350_A2_SUPPORTED 1
#define PICO_BOOT_STAGE2_CHOOSE_W25Q080 1
#ifndef PICO_FLASH_SIZE_BYTES
#define PICO_FLASH_SIZE_BYTES (2 * 1024 * 1024)
#endif
#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64
// 150 MHz default system clock: the capture PIO runs at clkdiv 2 (75 MHz, 75 cycles per microsecond).

#define PICO_DEFAULT_LED_PIN 36
#endif

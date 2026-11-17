/*
 * Board header for the Stern SAM replacement CPU board (RP2354B).
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

// -----------------------------------------------------
// NOTE: THIS HEADER IS ALSO INCLUDED BY ASSEMBLER SO
//       SHOULD ONLY CONSIST OF PREPROCESSOR DIRECTIVES
// -----------------------------------------------------

#ifndef _BOARDS_SAM_CPU_RP2354B_H
#define _BOARDS_SAM_CPU_RP2354B_H

pico_board_cmake_set(PICO_PLATFORM, rp2350)

#define SAM_CPU_RP2354B

// RP2354B: the 80-pin RP2350B die (48 GPIOs) with 2 MB of flash in the package.
#define PICO_RP2350A 0
#define PICO_RP2350_A2_SUPPORTED 1

#define PICO_BOOT_STAGE2_CHOOSE_W25Q080 1
#ifndef PICO_FLASH_SIZE_BYTES
#define PICO_FLASH_SIZE_BYTES (2 * 1024 * 1024)
#endif
// 200 MHz / 3 = 66 MHz QSPI. The real-time code runs from SRAM, so XIP speed
// only matters for core0.
#ifndef PICO_FLASH_SPI_CLKDIV
#define PICO_FLASH_SPI_CLKDIV 3
#endif

// 12 MHz crystal (ABM8-272-T3), 200 MHz system clock like PPUC io-boards.
#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64
#ifndef SYS_CLK_MHZ
#define SYS_CLK_MHZ 200
#endif
#define PLL_SYS_VCO_FREQ_HZ 1200000000
#define PLL_SYS_POSTDIV1 6
#define PLL_SYS_POSTDIV2 1

// No default UART: UART0 is the binary PPUC link to the Pi and must never
// carry stdio text.

#endif

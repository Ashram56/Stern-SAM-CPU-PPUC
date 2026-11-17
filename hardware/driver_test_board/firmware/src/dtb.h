// SAM driver output test board firmware: shared definitions.
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <stdint.h>
#include <stdbool.h>

#define DTB_FW_VERSION "dtb 0.1"

// GPIO map (hardware/driver_test_board/tools/design_dtb.py)
#define GP_SR_Q0      0     // 0-6: Q7 of the seven 74HC165
#define GP_SR_CLK     7
#define GP_SR_PL_N    8
#define GP_AUX0       9     // 9-21: AUXO_P1,2,3,5,6,7,8,9,10 then AUXS_P9..12
#define GP_CSTB0      22    // 22-29: CPU J1 strobes 1..8 (active low)
#define GP_SER_RET    30
#define GP_SER_DED    31
#define GP_SRCLK      32
#define GP_RCLK       33
#define GP_SR_OE_N    34
#define GP_SR_CLR_N   35
#define GP_LED        36
#define GP_ADC0       40    // 40-43: V50, V20S, V20F, V18L dividers (100 k / 4.7 k)

#define N_AUX   13
#define N_CSTB  8

// One captured state. All bits are "line high" (1) or "line low" (0) as seen on the connector:
//  w0: coils 1..32 at bits 0..31 (low-side outputs: 0 = output on)
//  w1: bits 0..9 lamp strobes J12 pins 1-6, 8-11 (0 = on); bits 10..16 lamp columns J13 1, 3-8;
//      bit 17 column on J13 pin 10 or 9 (JP2); bits 18..23 spare inputs (1 = on for columns)
//  w2: bits 0..12 aux lines (GPIO9-21), bits 13..20 CPU strobes 1..8 (0 = active)
typedef struct { uint32_t w0, w1, w2; } dtb_state_t;

typedef struct {
    uint64_t t_us;      // microseconds since capture start
    uint8_t kind;       // 0 = state change (1 us sampling), 1 = aux edge (20 ns), 2 = overflow marker
    dtb_state_t s;      // full state for kind 0; for kind 1 only s.w2 bits 0..12 are meaningful
} dtb_event_t;

// capture.c
void capture_init(void);
void capture_start(void);
void capture_stop(void);
bool capture_running(void);
void capture_poll(void);                // core1: process new samples
dtb_state_t capture_snapshot(void);
bool event_pop(dtb_event_t *e);         // core0
uint32_t capture_overflows(void);
uint64_t capture_now_us(void);

// switches.c
void switches_init(void);
void switches_set_matrix(const uint16_t ret_per_strobe[8]);
void switches_set_dedicated(uint32_t ded);
void switches_enable(bool on);
void switches_poll(uint32_t direct_word);  // core1: react to the CPU strobes (w2)
uint32_t switches_updates(void);

// rails.c
void rails_init(void);
void rails_read_mv(uint16_t mv[4]);

// proto.c
void proto_poll(void);

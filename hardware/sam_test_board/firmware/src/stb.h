// SAM universal test board firmware: shared definitions.
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <stdint.h>
#include <stdbool.h>

#define STB_FW_VERSION "stb 0.1"

// GPIO map (hardware/sam_test_board/tools/design_stb.py)
#define GP_SR_Q0      0     // 0-5: Q7 of the six 74HC165
#define GP_SR_CLK     6
#define GP_SR_PL_N    7
#define GP_HA0        8     // 8-19: header A pins 1-12, direct (22 k / 47 k divider)
#define GP_SER        20    // 74HCT595 chain
#define GP_SRCLK      21
#define GP_RCLK       22
#define GP_SR_OE_N    23
#define GP_SR_CLR_N   24
#define GP_LED        25
#define GP_SYNC       26    // board-to-board start line (J11), open drain, 10 k pull-up
#define GP_ID0        27    // role solder jumpers JP9/JP10 (closed = 0)
#define GP_ID1        28
#define GP_ADC0       40    // 40-43: RAILA-D dividers (100 k / 4.7 k)

#define N_CH    48          // channel c = header * 12 + pin - 1 (A1 = 0, B1 = 12, C1 = 24, D1 = 36)
#define N_HA    12
#define N_CHAIN 6
#define CH_MASK ((1ull << N_CH) - 1)

// Board role, from the ID jumpers (the PC knows which cable goes on which header for each role)
enum { ROLE_COILS = 0, ROLE_LAMPS = 1, ROLE_MATRIX = 2, ROLE_DEDICATED = 3 };

// One captured state: bit c of ch = channel c is high on the connector (1) or low (0);
// ha = header A pins sampled straight on the GPIO at the same instant (bit p-1 = pin p).
typedef struct { uint64_t ch; uint16_t ha; } stb_state_t;

typedef struct {
    uint64_t t_us;      // microseconds since capture start
    uint8_t kind;       // 0 = state change (1 us sampling), 1 = header A edge (20 ns resolution, only ha valid)
    stb_state_t s;
} stb_event_t;

// capture.c
void capture_init(void);
void capture_start(void);
void capture_stop(void);
bool capture_running(void);
void capture_poll(void);                // core1: process new samples
stb_state_t capture_snapshot(void);
bool event_pop(stb_event_t *e);         // core0
uint32_t capture_overflows(void);
uint64_t capture_now_us(void);

// switches.c: BSS123 drive (1 = channel pulled to ground)
void switches_init(void);
void switches_set_static(uint64_t mask);
void switches_set_matrix(const uint8_t strobe_pin[8], const uint64_t drive[8]);
void switches_enable(bool on);
void switches_poll(uint16_t ha);        // core1: react to the strobes on header A (active low)
uint32_t switches_updates(void);

// rails.c
void rails_init(void);
void rails_read_mv(uint16_t mv[4]);

// sync.c: start several boards together
void sync_init(void);
void sync_arm(int mode);                // 0 = start now, 1 = master (start + pulse SYNC), 2 = start on SYNC low
void sync_poll(void);                   // core1
int board_role(void);

// proto.c
void proto_poll(void);

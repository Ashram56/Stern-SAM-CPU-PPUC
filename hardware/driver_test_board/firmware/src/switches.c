// Switch simulation: 16 matrix returns + 24 dedicated inputs of the CPU board, driven by 2N7002 from
// 5 x 74HCT595 (PIO1 SM0). The matrix follows the CPU strobes (GPIO22-29, active low).
// SPDX-License-Identifier: GPL-3.0-or-later
#include "dtb.h"
#include "dtb.pio.h"
#include "hardware/pio.h"
#include "hardware/gpio.h"

static PIO const sp = pio1;
static uint16_t matrix[8];          // bit r = return r+1 closed while strobe s+1 is active
static volatile uint32_t dedicated; // bit d = D-(d+1) closed
static volatile uint32_t updates;
static int last_strobe = -2;
static volatile bool dirty = true;

uint32_t switches_updates(void) { return updates; }

static void load(uint16_t ret, uint32_t ded) {
    // clock k = 1..24 carries stage 24-k; RET has 16 stages, DED 24 (stage s drives G_xxx(s+1))
    uint32_t w[3] = {0, 0, 0};
    for (int k = 1; k <= 24; k++) {
        int s = 24 - k, i = (k - 1) % 8, j = (k - 1) / 8;
        if (s < 16 && (ret >> s & 1)) w[j] |= 1u << (2 * i);
        if (ded >> s & 1) w[j] |= 1u << (2 * i + 1);
    }
    for (int j = 0; j < 3; j++) pio_sm_put_blocking(sp, 0, w[j]);
    updates++;
}

void switches_init(void) {
    gpio_init(GP_SR_OE_N); gpio_put(GP_SR_OE_N, 1); gpio_set_dir(GP_SR_OE_N, true);
    gpio_init(GP_SR_CLR_N); gpio_put(GP_SR_CLR_N, 0); gpio_set_dir(GP_SR_CLR_N, true);
    pio_set_gpio_base(sp, 16);
    for (uint p = GP_SER_RET; p <= GP_RCLK; p++) pio_gpio_init(sp, p);
    uint off = pio_add_program(sp, &dtb_595_program);
    pio_sm_config c = dtb_595_program_get_default_config(off);
    sm_config_set_out_pins(&c, GP_SER_RET, 2);
    sm_config_set_sideset_pins(&c, GP_SRCLK);
    sm_config_set_set_pins(&c, GP_RCLK, 1);
    sm_config_set_out_shift(&c, true, true, 16);
    sm_config_set_clkdiv_int_frac8(&c, 3, 0);
    pio_sm_set_pins_with_mask64(sp, 0, 0, 0xFull << GP_SER_RET);
    pio_sm_set_pindirs_with_mask64(sp, 0, 0xFull << GP_SER_RET, 0xFull << GP_SER_RET);
    pio_sm_init(sp, 0, off, &c);
    pio_sm_set_enabled(sp, 0, true);
    gpio_put(GP_SR_CLR_N, 1);
    load(0, 0);
}

void switches_enable(bool on) { gpio_put(GP_SR_OE_N, on ? 0 : 1); }

void switches_set_matrix(const uint16_t r[8]) {
    for (int i = 0; i < 8; i++) matrix[i] = r[i];
    dirty = true;
}

void switches_set_dedicated(uint32_t d) { dedicated = d & 0xFFFFFF; dirty = true; }

// direct word: bits 13..20 = strobes 1..8 (0 = active)
void __not_in_flash_func(switches_poll)(uint32_t direct) {
    uint32_t act = ~(direct >> 13) & 0xFF;
    int s = act == 0 ? -1 : (act & (act - 1)) ? 8 : __builtin_ctz(act);   // 8 = several strobes at once
    if (s == last_strobe && !dirty) return;
    last_strobe = s; dirty = false;
    load((s >= 0 && s < 8) ? matrix[s] : 0, dedicated);
}

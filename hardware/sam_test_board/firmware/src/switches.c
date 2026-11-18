// Switch simulation: every channel has a BSS123 to ground, gates from 6 x 74HCT595 in one chain (PIO1 SM0).
// Static mask (dedicated switches, any role) + matrix emulation: up to 8 strobes read on header A (active low),
// each with the 48-bit drive mask the PC computed for its closed switches (returns on headers B-D).
// SPDX-License-Identifier: GPL-3.0-or-later
#include "stb.h"
#include "stb.pio.h"
#include "hardware/pio.h"
#include "hardware/gpio.h"

static PIO const sp = pio1;
static uint8_t strobe_pin[8] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};  // header A pin index 0-11
static uint64_t drive[8];
static uint16_t strobe_mask;          // header A bits used as strobes
static volatile uint64_t static_mask;
static volatile uint32_t updates;
static int last_strobe = -2;
static volatile bool dirty = true;

uint32_t switches_updates(void) { return updates; }

static void load(uint64_t m) {
    // shift right, channel 47 first: word 0 = channels 47..24, word 1 = 23..0
    uint32_t w0 = 0, w1 = 0;
    for (int i = 0; i < 24; i++) {
        if (m >> (47 - i) & 1) w0 |= 1u << i;
        if (m >> (23 - i) & 1) w1 |= 1u << i;
    }
    pio_sm_put_blocking(sp, 0, w0);
    pio_sm_put_blocking(sp, 0, w1);
    updates++;
}

void switches_init(void) {
    gpio_init(GP_SR_OE_N); gpio_put(GP_SR_OE_N, 1); gpio_set_dir(GP_SR_OE_N, true);
    gpio_init(GP_SR_CLR_N); gpio_put(GP_SR_CLR_N, 0); gpio_set_dir(GP_SR_CLR_N, true);
    pio_set_gpio_base(sp, 0);
    for (uint p = GP_SER; p <= GP_RCLK; p++) pio_gpio_init(sp, p);
    uint off = pio_add_program(sp, &stb_595_program);
    pio_sm_config c = stb_595_program_get_default_config(off);
    sm_config_set_out_pins(&c, GP_SER, 1);
    sm_config_set_sideset_pins(&c, GP_SRCLK);
    sm_config_set_set_pins(&c, GP_RCLK, 1);
    sm_config_set_out_shift(&c, true, true, 24);
    sm_config_set_clkdiv_int_frac8(&c, 3, 0);
    pio_sm_set_pins_with_mask(sp, 0, 0, 0x7u << GP_SER);
    pio_sm_set_pindirs_with_mask(sp, 0, 0x7u << GP_SER, 0x7u << GP_SER);
    pio_sm_init(sp, 0, off, &c);
    pio_sm_set_enabled(sp, 0, true);
    gpio_put(GP_SR_CLR_N, 1);
    load(0);
}

void switches_enable(bool on) { gpio_put(GP_SR_OE_N, on ? 0 : 1); }

void switches_set_static(uint64_t m) { static_mask = m & CH_MASK; dirty = true; }

void switches_set_matrix(const uint8_t pins[8], const uint64_t d[8]) {
    uint16_t sm = 0;
    for (int i = 0; i < 8; i++) {
        strobe_pin[i] = pins[i] < N_HA ? pins[i] : 0xFF;
        drive[i] = d[i] & CH_MASK;
        if (strobe_pin[i] != 0xFF) sm |= 1u << strobe_pin[i];
    }
    strobe_mask = sm;
    dirty = true;
}

// ha: header A levels (bit p-1 = pin p). One active (low) strobe -> its drive mask; none or several -> static only.
void __not_in_flash_func(switches_poll)(uint16_t ha) {
    uint16_t act = ~ha & strobe_mask;
    int s = -1;
    if (act && !(act & (act - 1))) {
        int pin = __builtin_ctz(act);
        for (int i = 0; i < 8; i++) if (strobe_pin[i] == pin) { s = i; break; }
    } else if (act) s = 8;
    if (s == last_strobe && !dirty) return;
    last_strobe = s; dirty = false;
    load(static_mask | ((s >= 0 && s < 8) ? drive[s] : 0));
}

// Start several boards together over the SYNC line (J11, open drain with 10 k pull-up, 330 R series):
// the master starts its capture and pulls SYNC low for 100 us; armed boards start on the falling edge
// (core1 polls it, so the boards start within about 1 us of each other). Board role from JP9/JP10.
// SPDX-License-Identifier: GPL-3.0-or-later
#include "stb.h"
#include "pico/stdlib.h"
#include "hardware/gpio.h"

static volatile bool armed;
static volatile uint64_t release_at;

void sync_init(void) {
    gpio_init(GP_SYNC); gpio_put(GP_SYNC, 0); gpio_set_dir(GP_SYNC, false);   // released (input)
    for (int p = GP_ID0; p <= GP_ID1; p++) { gpio_init(p); gpio_pull_up(p); }
}

int board_role(void) {
    // jumper closed = 0. Open/open = coils (0), JP9 closed = lamps (1), JP10 closed = matrix (2), both = dedicated (3)
    return (!gpio_get(GP_ID0) ? 1 : 0) | (!gpio_get(GP_ID1) ? 2 : 0);
}

void sync_arm(int mode) {
    if (mode == 2) { capture_stop(); armed = true; return; }
    armed = false;
    capture_start();
    if (mode == 1) {
        gpio_set_dir(GP_SYNC, true);          // drive low
        release_at = time_us_64() + 100;
    }
}

void __not_in_flash_func(sync_poll)(void) {
    if (armed && !gpio_get(GP_SYNC)) { armed = false; capture_start(); }
    if (release_at && time_us_64() >= release_at) { gpio_set_dir(GP_SYNC, false); release_at = 0; }
}

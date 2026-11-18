// SAM universal test board firmware (RP2354B).
// core0: USB protocol; core1: capture processing, switch matrix and SYNC (never blocks).
// SPDX-License-Identifier: GPL-3.0-or-later
#include "stb.h"
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/gpio.h"

static void __not_in_flash_func(core1_main)(void) {
    for (;;) {
        sync_poll();
        if (capture_running()) capture_poll();
        else switches_poll((gpio_get_all() >> GP_HA0) & 0xFFF);
    }
}

int main(void) {
    stdio_init_all();
    stdio_set_translate_crlf(&stdio_usb, false);
    gpio_init(GP_LED); gpio_set_dir(GP_LED, true);
    rails_init();
    sync_init();
    switches_init();         // registers cleared, outputs disabled until the PC enables them
    capture_init();
    multicore_launch_core1(core1_main);
    uint32_t t = 0;
    for (;;) {
        proto_poll();
        if (++t % 200000 == 0) gpio_xor_mask(1u << GP_LED);
    }
}

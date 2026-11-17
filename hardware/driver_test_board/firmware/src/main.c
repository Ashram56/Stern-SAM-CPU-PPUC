// SAM driver output test board firmware (RP2354B).
// core0: USB protocol; core1: capture processing and switch matrix (never blocks).
// SPDX-License-Identifier: GPL-3.0-or-later
#include "dtb.h"
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/gpio.h"

static void __not_in_flash_func(core1_main)(void) {
    for (;;) {
        if (capture_running()) capture_poll();
        else switches_poll((gpio_get_all() >> GP_AUX0) & 0x1FFFFF);
    }
}

int main(void) {
    stdio_init_all();
    stdio_set_translate_crlf(&stdio_usb, false);
    gpio_init(GP_LED); gpio_set_dir(GP_LED, true);
    rails_init();
    switches_init();         // registers cleared, outputs disabled until the PC enables them
    capture_init();
    multicore_launch_core1(core1_main);
    uint32_t t = 0;
    for (;;) {
        proto_poll();
        if (++t % 200000 == 0) gpio_xor_mask64(1ull << GP_LED);
    }
}

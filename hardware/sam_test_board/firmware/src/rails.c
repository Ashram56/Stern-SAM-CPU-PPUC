// Rail monitors: 100 k / 4.7 k dividers on GPIO40-43 (ADC0-3 of the RP2354B): RAILA-D from J5.
// SPDX-License-Identifier: GPL-3.0-or-later
#include "stb.h"
#include "hardware/adc.h"

void rails_init(void) {
    adc_init();
    for (int i = 0; i < 4; i++) adc_gpio_init(GP_ADC0 + i);
}

void rails_read_mv(uint16_t mv[4]) {
    for (int i = 0; i < 4; i++) {
        adc_select_input(i);
        uint32_t acc = 0;
        for (int k = 0; k < 16; k++) acc += adc_read();
        uint32_t pin_mv = acc * 3300u / (4096u * 16u);
        mv[i] = (uint16_t)(pin_mv * 1047u / 47u);     // (100 k + 4.7 k) / 4.7 k
    }
}

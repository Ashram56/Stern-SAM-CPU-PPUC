// Rail monitors: 100 k / 4.7 k dividers on GPIO40-43 (ADC0-3 of the RP2354B): V50, V20S, V20F, V18L.
// SPDX-License-Identifier: GPL-3.0-or-later
#include "dtb.h"
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
        // 3300 mV full scale, divider (100 k + 4.7 k) / 4.7 k
        uint32_t pin_mv = acc * 3300u / (4096u * 16u);
        mv[i] = (uint16_t)(pin_mv * 1047u / 47u);
    }
}

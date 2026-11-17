// Capture: 7 x 74HC165 + direct lines at 1 sample/us (PIO0 SM0/SM1 + DMA rings), aux edges (SM2),
// change detection on core1, event queue to core0.
// SPDX-License-Identifier: GPL-3.0-or-later
#include "dtb.h"
#include "dtb.pio.h"
#include "hardware/pio.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/sync.h"

#define RING_A_WORDS 2048          // 1024 samples x 2 words (8 KB ring)
#define RING_B_WORDS 1024          // 1024 samples x 1 word (4 KB ring)
#define EVQ 2048

static uint32_t ring_a[RING_A_WORDS] __attribute__((aligned(RING_A_WORDS * 4)));
static uint32_t ring_b[RING_B_WORDS] __attribute__((aligned(RING_B_WORDS * 4)));
static int dma_a, dma_b;
static PIO const cp = pio0;
static uint off_sr, off_direct, off_aux;

static dtb_event_t evq[EVQ];
static volatile uint32_t ev_head, ev_tail, ev_overflows;
static volatile bool running;
static volatile uint64_t sample_count;      // samples processed since start = microseconds
static uint32_t rd_a, rd_b;                 // ring read positions (words)
static uint32_t prev_a0, prev_a1, prev_b;
static volatile dtb_state_t snap;
static bool first;

// lookup: read r (0..7, D7 first) with 7-bit chain value v -> contribution to (w0, w1)
static uint32_t lut0[8][128], lut1[8][128];

static void build_lut(void) {
    for (int r = 0; r < 8; r++) {
        int d = 7 - r;                          // input D index of this read
        for (int v = 0; v < 128; v++) {
            uint32_t a = 0, b = 0;
            for (int k = 0; k < 7; k++) if (v & (1 << k)) {
                if (k < 4) a |= 1u << (8 * k + d); else b |= 1u << (8 * (k - 4) + d);
            }
            lut0[r][v] = a; lut1[r][v] = b;
        }
    }
}

static inline dtb_state_t decode(uint32_t a0, uint32_t a1, uint32_t b) {
    dtb_state_t s = {0, 0, b & 0x1FFFFF};
    for (int r = 0; r < 4; r++) {
        uint32_t v0 = (a0 >> (21 - 7 * r)) & 0x7f, v1 = (a1 >> (21 - 7 * r)) & 0x7f;
        s.w0 |= lut0[r][v0] | lut0[r + 4][v1];
        s.w1 |= lut1[r][v0] | lut1[r + 4][v1];
    }
    return s;
}

static void push_event(uint8_t kind, uint64_t t, dtb_state_t s) {
    uint32_t h = ev_head, n = (h + 1) % EVQ;
    if (n == ev_tail) { ev_overflows++; return; }
    evq[h].t_us = t; evq[h].kind = kind; evq[h].s = s;
    __dmb();
    ev_head = n;
}

bool event_pop(dtb_event_t *e) {
    uint32_t t = ev_tail;
    if (t == ev_head) return false;
    __dmb();
    *e = evq[t];
    ev_tail = (t + 1) % EVQ;
    return true;
}

uint32_t capture_overflows(void) { return ev_overflows; }
uint64_t capture_now_us(void) { return sample_count; }
bool capture_running(void) { return running; }
dtb_state_t capture_snapshot(void) { dtb_state_t s = {snap.w0, snap.w1, snap.w2}; return s; }

static void init_dma(int ch, const volatile void *src, uint32_t *ring, uint ring_bits, uint dreq) {
    dma_channel_config c = dma_channel_get_default_config(ch);
    channel_config_set_transfer_data_size(&c, DMA_SIZE_32);
    channel_config_set_read_increment(&c, false);
    channel_config_set_write_increment(&c, true);
    channel_config_set_ring(&c, true, ring_bits);
    channel_config_set_dreq(&c, dreq);
    dma_channel_configure(ch, &c, ring, src, dma_encode_endless_transfer_count(), false);
}

void capture_init(void) {
    build_lut();
    pio_set_gpio_base(cp, 0);
    for (uint p = GP_SR_Q0; p <= GP_CSTB0 + N_CSTB - 1; p++) {
        pio_gpio_init(cp, p);
        gpio_set_pulls(p, false, false);
    }
    gpio_set_input_hysteresis_enabled(GP_SR_CLK, false);
    off_sr = pio_add_program(cp, &dtb_sr_program);
    off_direct = pio_add_program(cp, &dtb_direct_program);
    off_aux = pio_add_program(cp, &dtb_aux_program);

    pio_sm_config c = dtb_sr_program_get_default_config(off_sr);
    sm_config_set_in_pins(&c, GP_SR_Q0);
    sm_config_set_in_pin_count(&c, 7);
    sm_config_set_sideset_pins(&c, GP_SR_CLK);
    sm_config_set_in_shift(&c, false, true, 28);
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_RX);
    sm_config_set_clkdiv_int_frac8(&c, 2, 0);              // 75 MHz: 75 cycles = 1 us
    pio_sm_set_pins_with_mask(cp, 0, 1u << GP_SR_PL_N, (1u << GP_SR_PL_N) | (1u << GP_SR_CLK));
    pio_sm_set_consecutive_pindirs(cp, 0, GP_SR_Q0, 7, false);
    pio_sm_set_consecutive_pindirs(cp, 0, GP_SR_CLK, 2, true);
    pio_sm_init(cp, 0, off_sr, &c);

    c = dtb_direct_program_get_default_config(off_direct);
    sm_config_set_in_pins(&c, GP_AUX0);
    sm_config_set_in_pin_count(&c, 21);
    sm_config_set_in_shift(&c, false, true, 21);
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_RX);
    pio_sm_set_consecutive_pindirs(cp, 1, GP_AUX0, 21, false);
    pio_sm_init(cp, 1, off_direct, &c);

    c = dtb_aux_program_get_default_config(off_aux);
    sm_config_set_in_pins(&c, GP_AUX0);
    sm_config_set_in_pin_count(&c, N_AUX);
    sm_config_set_in_shift(&c, false, true, N_AUX);
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_RX);
    pio_sm_init(cp, 2, off_aux, &c);

    dma_a = dma_claim_unused_channel(true);
    dma_b = dma_claim_unused_channel(true);
}

void capture_stop(void) {
    running = false;
    pio_set_sm_mask_enabled(cp, 0x7, false);
    dma_channel_abort(dma_a);
    dma_channel_abort(dma_b);
}

void capture_start(void) {
    capture_stop();
    for (uint sm = 0; sm < 3; sm++) {
        pio_sm_clear_fifos(cp, sm);
        pio_sm_restart(cp, sm);
        pio_sm_clkdiv_restart(cp, sm);
    }
    pio_interrupt_clear(cp, 0);
    pio_sm_exec(cp, 0, pio_encode_jmp(off_sr));
    pio_sm_exec(cp, 1, pio_encode_jmp(off_direct));
    pio_sm_exec(cp, 2, pio_encode_jmp(off_aux));
    init_dma(dma_a, &cp->rxf[0], ring_a, 13, pio_get_dreq(cp, 0, false));
    init_dma(dma_b, &cp->rxf[1], ring_b, 12, pio_get_dreq(cp, 1, false));
    rd_a = rd_b = 0; sample_count = 0; first = true;
    ev_head = ev_tail = 0; ev_overflows = 0;
    dma_start_channel_mask((1u << dma_a) | (1u << dma_b));
    __dmb();
    running = true;
    pio_enable_sm_mask_in_sync(cp, 0x7);
}

static inline uint32_t ring_pos(int ch, uint32_t *ring) {
    return ((uint32_t)dma_channel_hw_addr(ch)->write_addr - (uint32_t)ring) / 4;
}

// core1: called in a tight loop. Must keep up with 1 sample/us on average (the rings hold 1 ms).
void __not_in_flash_func(capture_poll)(void) {
    if (!running) return;
    uint32_t wa = ring_pos(dma_a, ring_a), wb = ring_pos(dma_b, ring_b);
    uint32_t na = ((wa - rd_a) & (RING_A_WORDS - 1)) / 2;  // complete samples in ring A
    uint32_t nb = (wb - rd_b) & (RING_B_WORDS - 1);
    uint32_t n = na < nb ? na : nb;
    // the switch matrix reacts to the newest strobe sample first
    if (nb) switches_poll(ring_b[(wb - 1) & (RING_B_WORDS - 1)]);
    while (n--) {
        uint32_t a0 = ring_a[rd_a], a1 = ring_a[rd_a + 1], b = ring_b[rd_b] & 0x1FFFFF;
        rd_a = (rd_a + 2) & (RING_A_WORDS - 1);
        rd_b = (rd_b + 1) & (RING_B_WORDS - 1);
        if (first || a0 != prev_a0 || a1 != prev_a1 || b != prev_b) {
            dtb_state_t s = decode(a0, a1, b);
            push_event(0, sample_count, s);
            snap.w0 = s.w0; snap.w1 = s.w1; snap.w2 = s.w2;
            prev_a0 = a0; prev_a1 = a1; prev_b = b; first = false;
        }
        sample_count++;
    }
    while (!pio_sm_is_rx_fifo_empty(cp, 2)) {
        dtb_state_t s = {0, 0, pio_sm_get(cp, 2) & ((1u << N_AUX) - 1)};
        push_event(1, sample_count, s);
    }
}

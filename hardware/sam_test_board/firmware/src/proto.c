// USB CDC protocol. Frame: 0xA5, cmd, len (u16 LE), payload, CRC16-CCITT (0x1021, init 0xFFFF, LE)
// over cmd, len and payload. Replies use cmd | 0x40; events 0x80; error 0x7F. All integers little endian.
//   0x01 INFO    -> "stb 0.1", role u8, board id u64 (flash unique id)
//   0x02 STATUS  -> running u8, t_us u64, overflows u32, switch updates u32, rails mV u16 x 4, ch u64, ha u16
//   0x10 START   payload: mode u8 (0 now, 1 master + SYNC pulse, 2 wait for SYNC)
//   0x11 STOP
//   0x20 MATRIX  payload: strobe pin u8 x 8 (header A pin 0-11, 0xFF unused), drive mask u64 x 8
//   0x21 STATIC  payload: drive mask u64 (bit c = channel c pulled to ground)
//   0x22 ENABLE  payload: u8 (1 = 74HCT595 outputs on)
//   0x80 EVENTS  n x 17 bytes: kind u8, t_us u64, ch 48 bits (6 bytes), ha u16
// SPDX-License-Identifier: GPL-3.0-or-later
#include <string.h>
#include "stb.h"
#include "pico/stdlib.h"
#include "pico/unique_id.h"

enum { C_INFO = 0x01, C_STATUS = 0x02, C_START = 0x10, C_STOP = 0x11,
       C_MATRIX = 0x20, C_STATIC = 0x21, C_SWEN = 0x22, E_EVENTS = 0x80, E_ERR = 0x7F };
#define EV_SIZE 17

static uint16_t crc16(const uint8_t *p, size_t n, uint16_t c) {
    while (n--) {
        c ^= (uint16_t)(*p++) << 8;
        for (int i = 0; i < 8; i++) c = (c & 0x8000) ? (c << 1) ^ 0x1021 : c << 1;
    }
    return c;
}

static void send(uint8_t cmd, const uint8_t *pl, uint16_t len) {
    uint8_t h[4] = {0xA5, cmd, (uint8_t)len, (uint8_t)(len >> 8)};
    uint16_t c = crc16(h + 1, 3, 0xFFFF);
    c = crc16(pl, len, c);
    for (int i = 0; i < 4; i++) putchar_raw(h[i]);
    for (uint16_t i = 0; i < len; i++) putchar_raw(pl[i]);
    putchar_raw(c & 0xFF); putchar_raw(c >> 8);
}

static inline uint8_t *put16(uint8_t *p, uint16_t v) { memcpy(p, &v, 2); return p + 2; }
static inline uint8_t *put32(uint8_t *p, uint32_t v) { memcpy(p, &v, 4); return p + 4; }
static inline uint8_t *put64(uint8_t *p, uint64_t v) { memcpy(p, &v, 8); return p + 8; }

static void handle(uint8_t cmd, const uint8_t *pl, uint16_t len) {
    uint8_t out[64], *p = out;
    switch (cmd) {
    case C_INFO: {
        memcpy(p, STB_FW_VERSION, sizeof STB_FW_VERSION - 1); p += sizeof STB_FW_VERSION - 1;
        *p++ = (uint8_t)board_role();
        pico_unique_board_id_t id; pico_get_unique_board_id(&id);
        memcpy(p, id.id, 8); p += 8;
        send(cmd | 0x40, out, p - out); return;
    }
    case C_STATUS: {
        uint16_t mv[4]; rails_read_mv(mv);
        stb_state_t s = capture_snapshot();
        *p++ = capture_running();
        p = put64(p, capture_now_us()); p = put32(p, capture_overflows()); p = put32(p, switches_updates());
        memcpy(p, mv, 8); p += 8;
        p = put64(p, s.ch); p = put16(p, s.ha);
        send(cmd | 0x40, out, p - out); return;
    }
    case C_START:
        sync_arm(len >= 1 ? pl[0] : 0); send(cmd | 0x40, 0, 0); return;
    case C_STOP: capture_stop(); send(cmd | 0x40, 0, 0); return;
    case C_MATRIX:
        if (len != 8 + 64) break;
        { uint64_t d[8]; memcpy(d, pl + 8, 64); switches_set_matrix(pl, d); }
        send(cmd | 0x40, 0, 0); return;
    case C_STATIC:
        if (len != 8) break;
        { uint64_t d; memcpy(&d, pl, 8); switches_set_static(d); }
        send(cmd | 0x40, 0, 0); return;
    case C_SWEN:
        if (len != 1) break;
        switches_enable(pl[0] != 0); send(cmd | 0x40, 0, 0); return;
    default: break;
    }
    uint8_t e = cmd; send(E_ERR, &e, 1);
}

static uint8_t rx[300];
static uint16_t rx_n, rx_len;

void proto_poll(void) {
    int ch;
    while ((ch = getchar_timeout_us(0)) != PICO_ERROR_TIMEOUT) {
        uint8_t b = (uint8_t)ch;
        if (rx_n == 0 && b != 0xA5) continue;
        rx[rx_n++] = b;
        if (rx_n == 4) {
            rx_len = rx[2] | rx[3] << 8;
            if (rx_len > sizeof rx - 6) { rx_n = 0; continue; }
        }
        if (rx_n >= 4 && rx_n == rx_len + 6) {
            uint16_t c = crc16(rx + 1, 3 + rx_len, 0xFFFF);
            if ((rx[rx_n - 2] | rx[rx_n - 1] << 8) == c) handle(rx[1], rx + 4, rx_len);
            rx_n = 0;
        }
    }
    static uint8_t ev[48 * EV_SIZE];
    int n = 0; stb_event_t e;
    while (n < 48 && event_pop(&e)) {
        uint8_t *p = ev + n * EV_SIZE;
        *p++ = e.kind; p = put64(p, e.t_us);
        for (int i = 0; i < 6; i++) *p++ = (uint8_t)(e.s.ch >> (8 * i));
        put16(p, e.s.ha);
        n++;
    }
    if (n) send(E_EVENTS, ev, n * EV_SIZE);
}

// SPDX-License-Identifier: GPL-3.0-or-later
#include "link_uart.h"

#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/uart.h"

#include "../board_pins.h"

namespace sam {

namespace {

constexpr size_t kRingBytes = 4096;  // power of two
uint8_t g_ring[kRingBytes];
volatile uint32_t g_head = 0;  // written by the IRQ
volatile uint32_t g_tail = 0;  // written by Read()
volatile uint32_t g_overruns = 0;

void OnUartRx() {
  while (uart_is_readable(uart0)) {
    const uint8_t b = static_cast<uint8_t>(uart_get_hw(uart0)->dr & 0xFF);
    const uint32_t head = g_head;
    if (head - g_tail >= kRingBytes) {
      g_overruns = g_overruns + 1;
      continue;
    }
    g_ring[head & (kRingBytes - 1)] = b;
    g_head = head + 1;
  }
}

}  // namespace

void UartLink::Init(uint32_t baud) {
  uart_init(uart0, baud);
  gpio_set_function(PIN_LINK_UART_TX, GPIO_FUNC_UART);
  gpio_set_function(PIN_LINK_UART_RX, GPIO_FUNC_UART);
  gpio_pull_up(PIN_LINK_UART_RX);
  uart_set_format(uart0, 8, 1, UART_PARITY_NONE);
  uart_set_hw_flow(uart0, false, false);
  uart_set_fifo_enabled(uart0, true);
  irq_set_exclusive_handler(UART0_IRQ, OnUartRx);
  irq_set_enabled(UART0_IRQ, true);
  uart_set_irq_enables(uart0, true, false);
}

size_t UartLink::Read(uint8_t* out, size_t max) {
  size_t n = 0;
  uint32_t tail = g_tail;
  const uint32_t head = g_head;
  while (tail != head && n < max) out[n++] = g_ring[tail++ & (kRingBytes - 1)];
  g_tail = tail;
  return n;
}

void UartLink::Write(const uint8_t* data, size_t len) { uart_write_blocking(uart0, data, len); }

uint32_t UartLink::Overruns() const { return g_overruns; }

}  // namespace sam

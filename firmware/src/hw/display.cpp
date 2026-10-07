// SPDX-License-Identifier: GPL-3.0-or-later
#include "display.h"

#include <string.h>

#include <initializer_list>

#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/pio.h"

#include "../board_pins.h"
#include "../core/devices.h"
#include "../core/dmd_frames.h"
#include "dmd_j5.pio.h"
#include "frame_rx.pio.h"
#include "hub75.pio.h"

namespace sam {

namespace {

PIO const kRxPio = pio1;  // shared with the switch chain (SM0, core1)
constexpr uint kRxSm = 1;
PIO const kOutPio = pio2;

// HUB75: 30 ns PIO cycles (clock divider 6); plane 0 lit for 60 cycles.
constexpr uint32_t kHubClkDiv = 6;
constexpr uint32_t kHubOeBaseCycles = 60;
constexpr uint32_t kJ5PixelClkDiv = 10;  // 200 ns per dot
constexpr uint32_t kJ5CtrlClkDiv = 25;   // dmd::kJ5CtrlCycleNs

// ---- Frame receiver -------------------------------------------------------

alignas(4) uint8_t g_rx[2][dmd::kMaxFrameBytes];
uint32_t g_rx_len[2];
volatile int g_rx_ready = -1;  // buffer holding a complete frame, or -1
int g_rx_active = 0;           // buffer the DMA fills
int g_rx_dma = -1;
uint g_rx_offset = 0;

// ---- Output streams -------------------------------------------------------

// Front/back buffers, sized for the larger (HUB75) stream.
constexpr size_t kOutWords = dmd::kHubPixelWords;
static_assert(dmd::kJ5PixelWords <= kOutWords, "");
alignas(4) uint32_t g_px[2][kOutWords];
alignas(4) uint32_t g_fixed[dmd::kJ5StepWords > dmd::kHubRows ? dmd::kJ5StepWords : dmd::kHubRows];
// Read by the reload DMA channels at every stream wrap.
const uint32_t* volatile g_px_front = g_px[0];
const uint32_t* volatile g_fixed_ptr = g_fixed;
int g_front = 0;

int g_px_dma = -1, g_px_reload = -1, g_fixed_dma = -1, g_fixed_reload = -1;
uint8_t g_mode = kDisplayNone;
size_t g_px_words = 0;
DisplayStats g_stats = {};

void ArmRx() {
  dma_channel_config c = dma_channel_get_default_config(static_cast<uint>(g_rx_dma));
  channel_config_set_transfer_data_size(&c, DMA_SIZE_8);
  channel_config_set_read_increment(&c, false);
  channel_config_set_write_increment(&c, true);
  channel_config_set_dreq(&c, pio_get_dreq(kRxPio, kRxSm, false));
  dma_channel_configure(static_cast<uint>(g_rx_dma), &c, g_rx[g_rx_active],
                        &kRxPio->rxf[kRxSm], dmd::kMaxFrameBytes, true);
}

// FRAME_CS_N rising: the frame is complete. Restart the receiver so a
// partial byte can never carry into the next frame.
void OnFrameCs(uint gpio, uint32_t events) {
  if (gpio != PIN_FRAME_CS_N || !(events & GPIO_IRQ_EDGE_RISE)) return;
  for (int i = 0; i < 64 && !pio_sm_is_rx_fifo_empty(kRxPio, kRxSm); ++i) {
  }
  const uint32_t remaining =
      dma_channel_hw_addr(static_cast<uint>(g_rx_dma))->transfer_count & DMA_CH0_TRANS_COUNT_COUNT_BITS;
  const uint32_t len = dmd::kMaxFrameBytes - remaining;
  dma_channel_abort(static_cast<uint>(g_rx_dma));
  pio_sm_restart(kRxPio, kRxSm);
  pio_sm_clear_fifos(kRxPio, kRxSm);
  pio_sm_exec(kRxPio, kRxSm, pio_encode_jmp(g_rx_offset));

  if (len >= dmd::kHeaderBytes) {
    if (g_rx_ready < 0) {
      g_rx_len[g_rx_active] = len;
      g_rx_ready = g_rx_active;
      g_rx_active ^= 1;
    } else {
      g_stats.frames_dropped++;
    }
  }
  ArmRx();
}

void InitFrameRx() {
  // PIO1's GPIO base is set to 16 by the switch chain setup (realtime.cpp).
  g_rx_offset = pio_add_program(kRxPio, &frame_rx_program);
  pio_sm_config c = frame_rx_program_get_default_config(g_rx_offset);
  sm_config_set_in_pins(&c, PIN_FRAME_MOSI);
  sm_config_set_in_shift(&c, false, true, 8);  // MSB first, a byte per push
  sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_RX);
  pio_gpio_init(kRxPio, PIN_FRAME_MOSI);
  pio_gpio_init(kRxPio, PIN_FRAME_SCK);
  pio_sm_set_pindirs_with_mask64(kRxPio, kRxSm, 0,
                                 (1ull << PIN_FRAME_MOSI) | (1ull << PIN_FRAME_SCK));
  pio_sm_init(kRxPio, kRxSm, g_rx_offset, &c);

  g_rx_dma = dma_claim_unused_channel(true);
  ArmRx();
  pio_sm_set_enabled(kRxPio, kRxSm, true);

  gpio_init(PIN_FRAME_CS_N);
  gpio_pull_up(PIN_FRAME_CS_N);
  gpio_set_irq_enabled_with_callback(PIN_FRAME_CS_N, GPIO_IRQ_EDGE_RISE, true, OnFrameCs);
}

// A DMA channel that feeds `words` words to a state machine forever, from
// the buffer `*ptr` points to at the start of each pass.
void StartLoop(int data, int reload, uint sm, const uint32_t* const volatile* ptr, size_t words) {
  dma_channel_config c = dma_channel_get_default_config(static_cast<uint>(data));
  channel_config_set_transfer_data_size(&c, DMA_SIZE_32);
  channel_config_set_read_increment(&c, true);
  channel_config_set_write_increment(&c, false);
  channel_config_set_dreq(&c, pio_get_dreq(kOutPio, sm, true));
  channel_config_set_chain_to(&c, static_cast<uint>(reload));
  dma_channel_configure(static_cast<uint>(data), &c, &kOutPio->txf[sm], nullptr, words, false);

  dma_channel_config r = dma_channel_get_default_config(static_cast<uint>(reload));
  channel_config_set_transfer_data_size(&r, DMA_SIZE_32);
  channel_config_set_read_increment(&r, false);
  channel_config_set_write_increment(&r, false);
  dma_channel_configure(static_cast<uint>(reload), &r,
                        &dma_hw->ch[data].al3_read_addr_trig, ptr, 1, true);
}

void StopOutput() {
  for (int ch : {g_px_reload, g_fixed_reload, g_px_dma, g_fixed_dma}) {
    if (ch >= 0) dma_channel_abort(static_cast<uint>(ch));
  }
  // An abort can race a chain trigger: abort the data channels once more.
  for (int ch : {g_px_dma, g_fixed_dma}) {
    if (ch >= 0) dma_channel_abort(static_cast<uint>(ch));
  }
  pio_set_sm_mask_enabled(kOutPio, 0x3u, false);
  pio_clear_instruction_memory(kOutPio);
  for (uint sm = 0; sm < 2; ++sm) {
    pio_sm_clear_fifos(kOutPio, sm);
    pio_sm_restart(kOutPio, sm);
  }
}

void StartJ5() {
  for (uint pin = PIN_J5_DE; pin <= PIN_J5_COLLATCH_B; ++pin) pio_gpio_init(kOutPio, pin);
  const uint64_t mask = 0x7Full << PIN_J5_DE;
  pio_sm_set_pins_with_mask64(kOutPio, 1, 0, mask);
  pio_sm_set_pindirs_with_mask64(kOutPio, 1, mask, mask);

  const uint px_off = pio_add_program(kOutPio, &dmd_j5_pixels_program);
  pio_sm_config c = dmd_j5_pixels_program_get_default_config(px_off);
  sm_config_set_out_pins(&c, PIN_J5_SDATA, 1);
  sm_config_set_sideset_pins(&c, PIN_J5_PIXCLK);
  sm_config_set_out_shift(&c, true, true, 32);
  sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX);
  sm_config_set_clkdiv_int_frac8(&c, kJ5PixelClkDiv, 0);
  pio_sm_init(kOutPio, 0, px_off, &c);

  const uint ctrl_off = pio_add_program(kOutPio, &dmd_j5_ctrl_program);
  pio_sm_config k = dmd_j5_ctrl_program_get_default_config(ctrl_off);
  sm_config_set_out_pins(&k, PIN_J5_DE, 4);
  sm_config_set_set_pins(&k, PIN_J5_COLLATCH_B, 1);
  sm_config_set_out_shift(&k, true, true, 32);
  sm_config_set_fifo_join(&k, PIO_FIFO_JOIN_TX);
  sm_config_set_clkdiv_int_frac8(&k, kJ5CtrlClkDiv, 0);
  pio_sm_init(kOutPio, 1, ctrl_off, &k);

  dmd::BuildJ5Steps(g_fixed);
  g_px_words = dmd::kJ5PixelWords;
  pio_sm_put(kOutPio, 0, dmd::kJ5Width - 1);
  pio_sm_put(kOutPio, 1, dmd::J5PrimeWord());
  StartLoop(g_px_dma, g_px_reload, 0, &g_px_front, dmd::kJ5PixelWords);
  StartLoop(g_fixed_dma, g_fixed_reload, 1, &g_fixed_ptr, dmd::kJ5StepWords);
  pio_enable_sm_mask_in_sync(kOutPio, 0x3u);
}

void StartHub75() {
  for (uint pin = PIN_DMD_D0; pin <= PIN_DMD_B; ++pin) pio_gpio_init(kOutPio, pin);
  const uint64_t mask = 0x1FFFFull << PIN_DMD_D0;  // GPIO20-36
  pio_sm_set_pins_with_mask64(kOutPio, 1, 1ull << PIN_DMD_OE, mask);  // dark
  pio_sm_set_pindirs_with_mask64(kOutPio, 1, mask, mask);

  const uint data_off = pio_add_program(kOutPio, &hub75_data_program);
  pio_sm_config c = hub75_data_program_get_default_config(data_off);
  sm_config_set_out_pins(&c, PIN_DMD_D0, 12);
  sm_config_set_sideset_pins(&c, PIN_DMD_CLK);
  sm_config_set_out_shift(&c, true, true, 32);
  sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX);
  sm_config_set_clkdiv_int_frac8(&c, kHubClkDiv, 0);
  pio_sm_init(kOutPio, 0, data_off, &c);

  const uint row_off = pio_add_program(kOutPio, &hub75_row_program);
  pio_sm_config k = hub75_row_program_get_default_config(row_off);
  sm_config_set_out_pins(&k, PIN_DMD_A, 2);
  sm_config_set_sideset_pins(&k, PIN_DMD_LAT);
  sm_config_set_out_shift(&k, true, true, 32);
  sm_config_set_clkdiv_int_frac8(&k, kHubClkDiv, 0);
  pio_sm_init(kOutPio, 1, row_off, &k);

  dmd::BuildHub75Rows(kHubOeBaseCycles, g_fixed);
  g_px_words = dmd::kHubPixelWords;
  pio_sm_put(kOutPio, 0, dmd::kHubWordsPerRow - 1);
  StartLoop(g_px_dma, g_px_reload, 0, &g_px_front, dmd::kHubPixelWords);
  StartLoop(g_fixed_dma, g_fixed_reload, 1, &g_fixed_ptr, dmd::kHubRows);
  pio_enable_sm_mask_in_sync(kOutPio, 0x3u);
}

bool BackBufferFree() {
  const uintptr_t back = reinterpret_cast<uintptr_t>(g_px[g_front ^ 1]);
  const uintptr_t r = dma_hw->ch[g_px_dma].read_addr;
  return r < back || r > back + g_px_words * sizeof(uint32_t);
}

}  // namespace

void DisplayInit() {
  pio_set_gpio_base(kOutPio, 16);
  g_px_dma = dma_claim_unused_channel(true);
  g_px_reload = dma_claim_unused_channel(true);
  g_fixed_dma = dma_claim_unused_channel(true);
  g_fixed_reload = dma_claim_unused_channel(true);
  InitFrameRx();
}

void DisplaySetMode(uint8_t mode) {
  if (mode == g_mode) return;
  StopOutput();
  memset(g_px, 0, sizeof(g_px));
  g_front = 0;
  g_px_front = g_px[0];
  g_mode = mode;
  if (mode == kDisplayJ5) {
    StartJ5();
  } else if (mode == kDisplayHub75) {
    StartHub75();
  } else {
    g_mode = kDisplayNone;
  }
}

uint8_t DisplayMode() { return g_mode; }

void DisplayService() {
  const int ready = g_rx_ready;
  if (ready < 0) return;
  if (g_mode == kDisplayNone) {
    g_rx_ready = -1;
    return;
  }
  if (!BackBufferFree()) return;  // the old front is still being shown

  dmd::FrameHeader h;
  const uint8_t* frame = g_rx[ready];
  bool ok = dmd::ParseHeader(frame, g_rx_len[ready], h);
  uint32_t* back = g_px[g_front ^ 1];
  if (ok) {
    ok = g_mode == kDisplayJ5
             ? dmd::BuildJ5Pixels(h, frame + dmd::kHeaderBytes, back)
             : dmd::BuildHub75Pixels(h, frame + dmd::kHeaderBytes, dmd::kDefaultTint, back);
  }
  g_rx_ready = -1;
  if (!ok) {
    g_stats.frames_bad++;
    return;
  }
  g_front ^= 1;
  g_px_front = back;
  g_stats.frames_shown++;
}

DisplayStats GetDisplayStats() { return g_stats; }

}  // namespace sam

// core1 loop. Nothing here blocks for more than a few bus cycles, so the
// switch chain (a pass every ~6 us) is drained continuously and a flipper
// button reaches its coil within one pass plus one bus write.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#include "realtime.h"

#include <string.h>

#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/pio.h"
#include "hardware/pwm.h"
#include "hardware/timer.h"
#include "pico/platform.h"

#include "../board_pins.h"
#include "../core/coil_engine.h"
#include "../core/io_scheduler.h"
#include "../core/lamp_engine.h"
#include "../core/switch_chain.h"
#include "../core/switch_scanner.h"
#include "sam_bus.pio.h"
#include "switch_chain.pio.h"

namespace sam {

namespace {

PIO const kBusPio = pio0;
constexpr uint kBusSm = 0;
PIO const kChainPio = pio1;
constexpr uint kChainSm = 0;

// Idle PIO cycles after each bus access: with the cycle itself this gives
// about 700 ns per write, the ROM's spacing.
constexpr uint32_t kBusIdleCycles = 2;
constexpr uint32_t kCoilPeriodUs = 250;
// Coils fire only while both interlocks read present (STATUS D0/D1 = 1 when
// the 20 V / 50 V supplies are up, confirmed by Vincent 2026-10-07). Opening
// the coin door therefore drops every coil and re-arms held flipper buttons.
#ifndef SAM_GATE_COILS_ON_INTERLOCKS
#define SAM_GATE_COILS_ON_INTERLOCKS 1
#endif
constexpr uint32_t kGiPwmWrap = 999;  // 1 kHz at 1 MHz PWM clock

Devices* g_devices = nullptr;
Shared* g_shared = nullptr;

class PioBus : public Bus {
 public:
  void Write(uint8_t reg, uint8_t value) override {
    pio_sm_put_blocking(kBusPio, kBusSm, sam_bus_write_cmd(reg, value, kBusIdleCycles));
  }
  void Read(uint8_t reg) override {
    pio_sm_put_blocking(kBusPio, kBusSm, sam_bus_read_cmd(reg, kBusIdleCycles));
  }
};

class Lookup : public SwitchLookup {
 public:
  Lookup(const SwitchScanner& scanner, const SwitchRefs& refs) : scanner_(scanner), refs_(refs) {}
  bool Closed(uint16_t number) const override {
    for (uint8_t k = 0; k < refs_.count; ++k) {
      if (refs_.number[k] != number) continue;
      if (refs_.port[k]) return scanner_.State(refs_.port[k]);
      return (refs_.remote >> k) & 1u;
    }
    return false;
  }

 private:
  const SwitchScanner& scanner_;
  const SwitchRefs& refs_;
};

void InitBusPio() {
  const uint offset = pio_add_program(kBusPio, &sam_bus_program);
  pio_sm_config c = sam_bus_program_get_default_config(offset);
  sm_config_set_out_pins(&c, PIN_BUS_D0, 12);
  sm_config_set_in_pins(&c, PIN_BUS_D0);
  sm_config_set_sideset_pins(&c, PIN_BUS_IOSTB);
  sm_config_set_out_shift(&c, true, false, 32);   // command word LSB first
  sm_config_set_in_shift(&c, false, false, 32);   // read byte ends in bits 7:0
  sm_config_set_clkdiv_int_frac8(&c, 7, 0);       // 35 ns per cycle
  for (uint pin = PIN_BUS_D0; pin <= PIN_BUS_DIR; ++pin) pio_gpio_init(kBusPio, pin);
  // IOSTB high and DIR = drive before the buffers are enabled.
  pio_sm_set_pins_with_mask(kBusPio, kBusSm, (1u << PIN_BUS_IOSTB) | (1u << PIN_BUS_DIR),
                            0x3FFFu);
  pio_sm_set_consecutive_pindirs(kBusPio, kBusSm, PIN_BUS_D0, 14, true);
  pio_sm_init(kBusPio, kBusSm, offset, &c);
  pio_sm_set_enabled(kBusPio, kBusSm, true);
}

void InitChainPio() {
  pio_set_gpio_base(kChainPio, 16);
  const uint offset = pio_add_program(kChainPio, &switch_chain_program);
  pio_sm_config c = switch_chain_program_get_default_config(offset);
  sm_config_set_sideset_pins(&c, PIN_SW_CLK);
  sm_config_set_in_pins(&c, PIN_SW_DATA);
  sm_config_set_out_pins(&c, PIN_STB_DATA, 1);
  sm_config_set_in_shift(&c, true, true, 32);    // first bit in bit 0, autopush
  sm_config_set_out_shift(&c, false, false, 32); // pattern MSB first
  sm_config_set_clkdiv_int_frac8(&c, 4, 0);      // 20 ns per cycle, 10 MHz shift clock
  pio_gpio_init(kChainPio, PIN_SW_CLK);
  pio_gpio_init(kChainPio, PIN_SW_LOAD_N);
  pio_gpio_init(kChainPio, PIN_SW_DATA);
  pio_gpio_init(kChainPio, PIN_STB_DATA);
  pio_sm_set_pins_with_mask64(kChainPio, kChainSm, 1ull << PIN_SW_LOAD_N,
                              (1ull << PIN_SW_CLK) | (1ull << PIN_SW_LOAD_N) |
                                  (1ull << PIN_STB_DATA));
  pio_sm_set_pindirs_with_mask64(kChainPio, kChainSm,
                                 (1ull << PIN_SW_CLK) | (1ull << PIN_SW_LOAD_N) |
                                     (1ull << PIN_STB_DATA),
                                 (1ull << PIN_SW_CLK) | (1ull << PIN_SW_LOAD_N) |
                                     (1ull << PIN_SW_DATA) | (1ull << PIN_STB_DATA));
  pio_sm_init(kChainPio, kChainSm, offset, &c);
  // Started from core1 once the loop is ready to drain it.
}

void InitGiPwm() {
  gpio_set_function(PIN_GI_PWM, GPIO_FUNC_PWM);
  const uint slice = pwm_gpio_to_slice_num(PIN_GI_PWM);
  pwm_config c = pwm_get_default_config();
  pwm_config_set_clkdiv(&c, static_cast<float>(clock_get_hz(clk_sys)) / 1000000.0f);
  pwm_config_set_wrap(&c, kGiPwmWrap);
  pwm_init(slice, &c, true);
  pwm_set_gpio_level(PIN_GI_PWM, 0);
}

void SetGiPwm(uint8_t level) {
  // GI dimmer board on J18: duty = level / 8. Polarity to be confirmed.
  pwm_set_gpio_level(PIN_GI_PWM, static_cast<uint16_t>((kGiPwmWrap + 1) * level / 8));
}

// Statics rather than locals: core1's stack is small.
LampEngine g_lamps;
SwitchScanner g_scanner;
CoilEngine g_coils;
PioBus g_bus;
IoScheduler g_io(g_bus, g_lamps);
HostOutputs g_out;
SwitchRefs g_refs;
SwitchSnapshot g_snap;

}  // namespace

void RealtimeInit(Devices* devices, Shared* shared) {
  g_devices = devices;
  g_shared = shared;

  // IO board held in reset and J9 buffers off until core1 has the lamp scan
  // running (both lines are also pulled that way on the board).
  gpio_init(PIN_NBRESET_DRV);
  gpio_put(PIN_NBRESET_DRV, 1);
  gpio_set_dir(PIN_NBRESET_DRV, GPIO_OUT);
  gpio_init(PIN_BUS_OE_N);
  gpio_put(PIN_BUS_OE_N, 1);
  gpio_set_dir(PIN_BUS_OE_N, GPIO_OUT);

  InitBusPio();
  InitChainPio();
  InitGiPwm();
}

void RealtimeMain() {
  Devices& d = *g_devices;
  Shared& sh = *g_shared;

  g_lamps.Reset();
  g_scanner.Reset();
  g_coils.Reset();
  memset(&g_out, 0, sizeof(g_out));
  memset(&g_refs, 0, sizeof(g_refs));
  memset(&g_snap, 0, sizeof(g_snap));
  Lookup lookup(g_scanner, g_refs);

  // Bring-up: buffers on, every register cleared and the lamp scan running
  // while the IO board is still in reset, then release it and clear again so
  // its watchdog sees DRV0 toggling from the first moment.
  gpio_put(PIN_BUS_OE_N, 0);
  uint32_t now = time_us_32();
  g_io.Start(now, d);
  const uint32_t release_at = now + 2u * d.board.lamp_slot_us * kLampLines;
  while (static_cast<int32_t>(time_us_32() - release_at) < 0) {
    g_io.Poll(time_us_32(), d, nullptr);
  }
  gpio_put(PIN_NBRESET_DRV, 0);
  g_io.Start(time_us_32(), d);
  sh.io_board_up = true;

  pio_sm_clear_fifos(kChainPio, kChainSm);
  pio_sm_set_enabled(kChainPio, kChainSm, true);

  // Switch chain decoding: three words per pass.
  uint8_t phase = 0;
  uint32_t word0 = 0;
  uint16_t pattern_hist[3] = {0, 0, 0};  // pass N, N-1, N-2
  uint8_t strobe = 0;
  uint32_t strobe_at = time_us_32();
  uint32_t last_change = g_scanner.ChangeCount();
  uint32_t coil_at = 0;
  uint32_t outputs_version = 0;
  uint32_t refs_version = 0;
  uint8_t drive_on[kNumCoilPorts] = {};
  uint8_t status = 0;
  uint8_t gi_level = 0xFF;

  for (;;) {
    now = time_us_32();
    sh.core1_heartbeat = sh.core1_heartbeat + 1;

    if (sh.outputs.Version() != outputs_version) {
      outputs_version = sh.outputs.Version();
      sh.outputs.Read(g_out);
      coil_at = now;  // re-evaluate coils right away
    }
    if (sh.refs.Version() != refs_version) {
      refs_version = sh.refs.Version();
      sh.refs.Read(g_refs);
    }

    // Switch chain.
    while (!pio_sm_is_rx_fifo_empty(kChainPio, kChainSm)) {
      const uint32_t w = pio_sm_get(kChainPio, kChainSm);
      if (phase == 0) {
        pattern_hist[2] = pattern_hist[1];
        pattern_hist[1] = pattern_hist[0];
        pattern_hist[0] = static_cast<uint16_t>(w);
        phase = 1;
      } else if (phase == 1) {
        word0 = w;
        phase = 2;
      } else {
        phase = 0;
        g_scanner.OnPass(time_us_32(), pattern_hist[2], DecodeChain(ChainStream(word0, w)), d);
      }
    }

    // Next matrix strobe.
    const uint8_t strobes =
        d.board.switch_strobes >= 1 && d.board.switch_strobes <= kMaxStrobes ? d.board.switch_strobes : 8;
    if (now - strobe_at >= d.board.strobe_dwell_us && !pio_sm_is_tx_fifo_full(kChainPio, kChainSm)) {
      strobe_at = now;
      strobe = static_cast<uint8_t>((strobe + 1) % strobes);
      // Status LED: slow blink with a host session, fast without.
      const bool led = (now >> (g_out.running ? 19 : 17)) & 1u;
      pio_sm_put(kChainPio, kChainSm, StrobePattern(static_cast<int8_t>(strobe), led, false));
    }

    // STATUS bytes queued by the scheduler.
    while (!pio_sm_is_rx_fifo_empty(kBusPio, kBusSm)) {
      status = static_cast<uint8_t>(pio_sm_get(kBusPio, kBusSm) & 0xFF);
      g_scanner.OnStatus(now, status, d);
    }

    // Coils: at once on a switch change or new host outputs, else every 250 us.
    const uint32_t changes = g_scanner.ChangeCount();
    if (changes != last_change || now - coil_at >= kCoilPeriodUs) {
      coil_at = now;
      const bool host_alive =
          g_out.running &&
          now - g_out.stamp_us < static_cast<uint32_t>(d.board.host_timeout_ms) * 1000u;
      bool allowed = host_alive;
#if SAM_GATE_COILS_ON_INTERLOCKS
      allowed = allowed && g_scanner.State(kSwitch20V) && g_scanner.State(kSwitch50V);
#endif
      CoilInputs in = {g_out.coils, g_out.game_on, allowed};
      g_coils.Update(now, d, in, lookup, drive_on);
      g_io.SetCoils(now, drive_on);
    }
    if (changes != last_change) {
      last_change = changes;
      memcpy(g_snap.bitmap, g_scanner.StableBitmap(), sizeof(g_snap.bitmap));
      g_snap.change_count = changes;
      g_snap.status = status;
      sh.switches.Write(g_snap);
    }

    // Lamps and GI.
    g_io.Poll(now, d, g_out.running ? g_out.lamps : nullptr);
    const uint8_t gi = g_out.running ? g_out.gi_level : 0;
    g_io.SetGiRelay(now, d, gi > 0);
    if (gi != gi_level) {
      gi_level = gi;
      SetGiPwm(gi);
    }
  }
}

}  // namespace sam

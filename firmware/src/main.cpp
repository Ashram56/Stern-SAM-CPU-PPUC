// SAM CPU board replacement, RP2354B firmware.
//
// core0: PPUC v2 link to the Pi (UART0), session and configuration.
// core1: SAM IO bus, switch chain, coils and lamps
//        (hw/realtime.cpp). See ../README.md.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#include <string.h>

#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/watchdog.h"
#include "pico/multicore.h"
#include "pico/stdlib.h"

#include "board_pins.h"
#include "core/devices.h"
#include "core/ppuc_session.h"
#include "core/shared.h"
#include "hw/link_uart.h"
#include "hw/realtime.h"

#ifndef SAM_LINK_BAUD
#define SAM_LINK_BAUD ppuc::v2::kBaudRate
#endif
// Virtual PPUC boards this firmware answers for (bit n = board id n).
#ifndef SAM_BOARD_MASK
#define SAM_BOARD_MASK 0x03  // 0 = outputs, 1 = switches
#endif
#ifndef SAM_BUILD_ID
#define SAM_BUILD_ID 0
#endif

namespace sam {
namespace {

constexpr uint32_t kWatchdogMs = 100;

Devices g_devices;
Shared g_shared;
UartLink g_link;

class Listener : public SessionListener {
 public:
  void OnRestart(bool hard_reset) override;
  void OnOutputs() override;
};

Listener g_listener;
PpucSession g_session(g_devices, g_link, g_listener);

void PublishOutputs() {
  HostOutputs o;
  memset(&o, 0, sizeof(o));
  o.running = g_session.Running();
  if (o.running) {
    memcpy(o.coils, g_session.CoilsByPort(), sizeof(o.coils));
    memcpy(o.lamps, g_session.LampsByPort(), sizeof(o.lamps));
    o.gi_level = g_session.GiLevel(0);
    o.game_on = g_session.GameOn();
  }
  o.stamp_us = time_us_32();
  g_shared.outputs.Write(o);
}

// The switches the coil rules depend on, resolved for core1.
void PublishSwitchRefs() {
  SwitchRefs r;
  memset(&r, 0, sizeof(r));
  auto add = [&r](uint16_t number) {
    if (number == 0) return;
    for (uint8_t k = 0; k < r.count; ++k) {
      if (r.number[k] == number) return;
    }
    if (r.count >= SwitchRefs::kMax) return;
    uint16_t port = 0;
    for (uint16_t p = 1; p < kNumSwitchPorts; ++p) {
      if (g_devices.sw[p].used && g_devices.sw[p].number == number) {
        port = p;
        break;
      }
    }
    r.number[r.count] = number;
    r.port[r.count] = port;
    if (port == 0 && g_session.RemoteSwitch(number)) r.remote |= 1u << r.count;
    r.count++;
  };
  add(g_devices.high_power.coin_door_switch);
  add(g_devices.high_power.tilt_switch);
  for (uint8_t port = kCoilPortFirst; port <= kCoilPortLast; ++port) {
    const CoilConfig& c = g_devices.coil[port];
    if (!c.used) continue;
    add(c.fast_switch);
    for (uint16_t s : c.stop_switch) add(s);
  }
  g_shared.refs.Write(r);
}

void Listener::OnRestart(bool hard_reset) {
  (void)hard_reset;
  PublishOutputs();
  PublishSwitchRefs();
}

void Listener::OnOutputs() {
  PublishSwitchRefs();
  PublishOutputs();
}

void Core1Entry() { RealtimeMain(); }

}  // namespace
}  // namespace sam

int main() {
  using namespace sam;

  // 200 MHz comes from the board header (PLL_SYS_* in boards/sam_cpu_rp2354b.h).
  DevicesReset(g_devices);

  gpio_init(PIN_RP_IRQ_N);
  gpio_put(PIN_RP_IRQ_N, 1);
  gpio_set_dir(PIN_RP_IRQ_N, GPIO_OUT);
  // AMP_MUTE: high mutes the amplifiers (pull-down on the board). Unmuted.
  gpio_init(PIN_AMP_MUTE);
  gpio_put(PIN_AMP_MUTE, 0);
  gpio_set_dir(PIN_AMP_MUTE, GPIO_OUT);

  RealtimeInit(&g_devices, &g_shared);
  PublishOutputs();
  PublishSwitchRefs();
  multicore_launch_core1(Core1Entry);

  g_session.SetBoardMask(SAM_BOARD_MASK);
  g_session.SetBuildId(SAM_BUILD_ID);
  g_link.Init(SAM_LINK_BAUD);

  if (watchdog_enable_caused_reboot()) {
    // Nothing to keep: the host restarts the session when the board stops
    // answering, and the IO board was held in reset by the pull-up.
  }
  watchdog_enable(kWatchdogMs, true);

  uint8_t rx[256];
  SwitchSnapshot snap;
  uint32_t switch_count = 0xFFFFFFFFu;
  uint32_t heartbeat = g_shared.core1_heartbeat;
  uint32_t heartbeat_at = time_us_32();
  bool was_running = false;

  for (;;) {
    const uint32_t now = time_us_32();

    // Link.
    const size_t n = g_link.Read(rx, sizeof(rx));
    if (n) g_session.Feed(rx, n);

    // Local switches into the PPUC report rings.
    if (g_shared.switches.Version() != 0) {
      g_shared.switches.Read(snap);
      if (snap.change_count != switch_count) {
        switch_count = snap.change_count;
        g_session.UpdateLocalSwitches(snap.bitmap);
      }
    }
    gpio_put(PIN_RP_IRQ_N, !g_session.HasQueuedReports());

    // Session up or down without an OutputState (restart, mapping done).
    if (g_session.Running() != was_running) {
      was_running = g_session.Running();
      PublishOutputs();
      PublishSwitchRefs();
    }

    // Feed the watchdog only while core1 is alive.
    if (g_shared.core1_heartbeat != heartbeat) {
      heartbeat = g_shared.core1_heartbeat;
      heartbeat_at = now;
    }
    if (now - heartbeat_at < kWatchdogMs * 500u) watchdog_update();
  }
}

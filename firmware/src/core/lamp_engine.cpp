// SPDX-License-Identifier: GPL-3.0-or-later
#include "lamp_engine.h"

#include <math.h>
#include <string.h>

namespace sam {

LampEngine::LampEngine() {
  for (int i = 0; i < 256; ++i) {
    const double v = pow(i / 255.0, 2.2) * 65535.0;
    gamma_[i] = static_cast<uint16_t>(v + 0.5);
  }
  // Anything above zero must light, however dimly.
  for (int i = 1; i < 256 && gamma_[i] == 0; ++i) gamma_[i] = 1;
  Reset();
}

void LampEngine::Reset() { memset(level_, 0, sizeof(level_)); }

void LampEngine::UpdateLevels(uint32_t dt_us, const Devices& d, const uint8_t* lamp_on) {
  for (uint16_t port = 1; port < kNumLampPorts; ++port) {
    const LampConfig& c = d.lamp[port];
    if (!c.used) {
      level_[port] = 0;
      continue;
    }
    const bool on = (lamp_on[port / 8] >> (port % 8)) & 1u;
    const uint8_t brightness = c.brightness ? c.brightness : d.board.default_brightness;
    const uint32_t target = on ? brightness * 257u : 0u;
    const uint32_t cur = level_[port];
    if (cur == target) continue;
    const uint16_t ramp_ms = cur < target
        ? (c.light_up_ms == 0xFFFF ? d.board.default_light_up_ms : c.light_up_ms)
        : (c.after_glow_ms == 0xFFFF ? d.board.default_after_glow_ms : c.after_glow_ms);
    if (ramp_ms == 0) {
      level_[port] = static_cast<uint16_t>(target);
      continue;
    }
    // Full scale (65535) in ramp_ms.
    uint32_t step = static_cast<uint32_t>((65535ull * dt_us) / (ramp_ms * 1000ull));
    if (step == 0) step = 1;
    if (cur < target) {
      level_[port] = static_cast<uint16_t>(target - cur <= step ? target : cur + step);
    } else {
      level_[port] = static_cast<uint16_t>(cur - target <= step ? target : cur - step);
    }
  }
}

uint8_t LampEngine::Build(const uint8_t* ports, uint16_t window_us,
                          LampStep out[kMaxLampSteps]) const {
  // ports[b] = lamp port driven by bit b, 0 = none.
  uint16_t on_us[8];
  uint8_t all = 0;
  for (uint8_t b = 0; b < 8; ++b) {
    on_us[b] = 0;
    if (ports[b] == 0) continue;
    const uint16_t duty = gamma_[level_[ports[b]] >> 8];
    if (duty == 0) continue;
    uint32_t t = (static_cast<uint32_t>(duty) * window_us + 32768u) >> 16;
    if (t == 0) t = 1;
    on_us[b] = static_cast<uint16_t>(t);
    all |= static_cast<uint8_t>(1u << b);
  }
  if (!all) return 0;

  uint8_t n = 0;
  out[n++] = {0, all};
  uint8_t remaining = all;
  while (remaining) {
    // Earliest end among the lamps still on.
    uint16_t t = 0xFFFF;
    for (uint8_t b = 0; b < 8; ++b) {
      if ((remaining >> b) & 1u && on_us[b] < t) t = on_us[b];
    }
    if (t >= window_us) break;  // the rest stay on until the next blank
    for (uint8_t b = 0; b < 8; ++b) {
      if ((remaining >> b) & 1u && on_us[b] == t) remaining &= static_cast<uint8_t>(~(1u << b));
    }
    out[n++] = {t, remaining};
  }
  return n;
}

uint8_t LampEngine::BuildLine(uint8_t line, uint16_t window_us,
                              LampStep out[kMaxLampSteps]) const {
  uint8_t ports[8];
  for (uint8_t k = 0; k < 8; ++k) {
    // Lamp line * 8 + k + 1 is on LMP_DRV bit 7 - k.
    ports[7 - k] = static_cast<uint8_t>(line * 8 + k + 1);
  }
  return Build(ports, window_us, out);
}

uint8_t LampEngine::BuildAux(uint8_t strobe_bit, uint16_t period_us,
                             LampStep out[kMaxLampSteps]) const {
  uint8_t ports[8];
  for (uint8_t b = 0; b < 8; ++b) {
    ports[b] = static_cast<uint8_t>(kAuxLampPortFirst + (strobe_bit - 3) * 8 + b);
  }
  return Build(ports, period_us, out);
}

bool LampEngine::AuxUsed(uint8_t strobe_bit, const Devices& d) const {
  for (uint8_t b = 0; b < 8; ++b) {
    if (d.lamp[kAuxLampPortFirst + (strobe_bit - 3) * 8 + b].used) return true;
  }
  return false;
}

}  // namespace sam

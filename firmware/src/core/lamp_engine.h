// LED lamp brightness and ramping on the SAM lamp matrix.
//
// The IO board has no PWM of its own: each lamp strobe line is on for one slot
// per frame, and LMP_DRV selects which of its 8 lamps get current. Brightness
// comes from rewriting LMP_DRV inside the slot ("edge-sorted PWM",
// Tron-Legacy-LE-ROM-Decryption io/bus/README.md section 10A): at the start of
// the slot every lamp that should glow is on, then each lamp is dropped when
// its on-time ends, at most 9 writes per slot.
//
// Per lamp:
//   brightness   level when fully on (0-255, perceived; gamma 2.2 applied)
//   light_up     ramp time from off to full (incandescent warm-up)
//   after_glow   ramp time from full to off (filament cooling)
// Lamps without their own values use the board defaults. The same scheme
// drives the strobed aux boards (Tron LE ramp tubes), one PWM period per frame.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>

#include "devices.h"

namespace sam {

struct LampStep {
  uint16_t t_us;   // from the start of the on-window
  uint8_t drive;   // value to write (LMP_DRV, or AUX_DRV for an aux board)
};
constexpr uint8_t kMaxLampSteps = 9;

class LampEngine {
 public:
  LampEngine();
  void Reset();

  // Advances every lamp's level towards its target. `lamp_on` is a bitmap by
  // lamp port. Call once per frame.
  void UpdateLevels(uint32_t dt_us, const Devices& d, const uint8_t* lamp_on);

  // Edge list for matrix strobe line `line` (0-9) and an on-window of
  // `window_us`. Returns the number of steps (0 = line stays dark).
  uint8_t BuildLine(uint8_t line, uint16_t window_us, LampStep out[kMaxLampSteps]) const;

  // Edge list for the aux board latched by reg 0xB bit `strobe_bit` (3-7).
  uint8_t BuildAux(uint8_t strobe_bit, uint16_t period_us, LampStep out[kMaxLampSteps]) const;
  // Whether any aux lamp port of this strobe is configured.
  bool AuxUsed(uint8_t strobe_bit, const Devices& d) const;

  uint16_t Level(uint8_t port) const { return level_[port]; }
  // 0-65535 duty after gamma.
  uint16_t Duty(uint8_t port) const { return gamma_[level_[port] >> 8]; }

 private:
  uint8_t Build(const uint8_t* ports, uint16_t window_us, LampStep out[kMaxLampSteps]) const;

  uint16_t level_[kNumLampPorts];
  uint16_t gamma_[256];
};

}  // namespace sam

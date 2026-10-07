// Coil pulse envelopes, fast flips and stop switches, run on the board.
//
// Behaviour follows PPUC io-boards PwmDevices (src/IODevices/PwmDevices.cpp,
// commit 82511ef) so a game YAML means the same thing on this board:
// power / minPulseTime / maxPulseTime / holdPower / holdPowerActivationTime /
// fastFlipSwitch / stopSwitch, the game-on solenoid and coin door gate, and
// tilt dropping fast-flip outputs. Differences:
//   - it is evaluated from levels on every call instead of from events, so a
//     missed edge cannot leave a coil on;
//   - "power" below 255 becomes a software PWM over the slow SAM drivers
//     (period BoardSettings::coil_pwm_period_us, ROM hold = 1 ms on / 11 off);
//   - an extra `allowed` gate (session up, host alive, both interlocks)
//     drops every coil and demands a fresh press of any held flipper button.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>

#include "devices.h"

namespace sam {

// Switch state by PPUC switch number (local or reported by another board).
class SwitchLookup {
 public:
  virtual bool Closed(uint16_t number) const = 0;
};

struct CoilInputs {
  const uint8_t* host_on;  // bitmap by coil port: host wants the coil on
  bool game_on;            // the configured game-on solenoid is on (or none configured)
  bool allowed;            // session, host link and interlocks all good
};

class CoilEngine {
 public:
  void Reset();
  // Returns, per port, whether the driver should be on right now.
  void Update(uint32_t now_us, const Devices& d, const CoilInputs& in, const SwitchLookup& sw,
              uint8_t drive_on[kNumCoilPorts]);

  uint8_t CurrentPower(uint8_t port) const { return st_[port].power; }
  bool HighPowerAvailable() const { return power_on_ && coin_door_closed_; }

 private:
  struct State {
    bool active;
    uint32_t since_us;
    uint8_t power;
    bool scheduled_off;
    bool fast_managed;
    bool fast_closed;
    bool wait_release;
    bool stop_engaged;
    bool stop_closed[kMaxStopSwitches];
    bool host_prev;
  };

  void Activate(State& s, const CoilConfig& c, uint32_t now_us, bool fast);
  static void Deactivate(State& s);

  State st_[kNumCoilPorts] = {};
  bool power_on_ = false;
  bool coin_door_closed_ = false;
  bool tilt_ = false;
};

}  // namespace sam

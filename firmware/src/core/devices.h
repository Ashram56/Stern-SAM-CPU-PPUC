// Device tables filled from PPUC ConfigFrames.
//
// One table serves every virtual board id this firmware answers to: coils,
// lamps and switches use disjoint port ranges (sam_io.h), so it does not
// matter which id a device was configured under.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>

#include "sam_io.h"

namespace sam {

constexpr uint8_t kMaxStopSwitches = 2;

struct CoilConfig {
  bool used;
  uint8_t type;                // PWM_TYPE_*
  uint16_t number;             // PPUC device number
  uint8_t power;               // 0-255 initial power
  uint8_t hold_power;          // 0-255 after hold_activation_ms
  uint16_t min_pulse_ms;
  uint16_t max_pulse_ms;       // 0 = unbounded (warned about by libppuc)
  uint16_t hold_activation_ms;
  uint16_t fast_switch;        // switch number, 0 = none
  uint16_t stop_switch[kMaxStopSwitches];
};

struct LampConfig {
  bool used;
  uint16_t number;             // PPUC device number
  uint8_t brightness;          // 0-255 full-on level (before gamma)
  uint16_t light_up_ms;        // ramp from off to full, 0 = instant
  uint16_t after_glow_ms;      // ramp from full to off, 0 = instant
};

struct SwitchConfig {
  bool used;
  uint8_t board;               // virtual board id the switch was configured under
  uint16_t number;             // PPUC device number
  uint16_t debounce_ms;
  uint8_t mode;                // SWITCH_DEBOUNCE_*
};

// Board-wide settings (CONFIG_TOPIC_SAM_BOARD, a proposal). Defaults follow
// ARCHITECTURE.md and the ROM.
enum DisplayMode : uint8_t {
  kDisplayNone = 0,
  kDisplayJ5 = 1,        // original 128x32 DMD on J5
  kDisplayHub75 = 2,     // two HUB75 panels, 256x64 in total
};

struct BoardSettings {
  uint16_t lamp_slot_us;       // time per lamp strobe line; 10 lines per frame
  uint16_t lamp_blank_us;      // dark gap before each line (ROM: 24 us)
  uint8_t default_brightness;
  uint16_t default_light_up_ms;
  uint16_t default_after_glow_ms;
  uint8_t switch_strobes;      // matrix strobes driven, 1-8
  uint16_t strobe_dwell_us;    // time each strobe is active
  uint16_t strobe_settle_us;   // returns are sampled only after this
  uint16_t coil_pwm_period_us; // software PWM period for power < 255
  uint16_t gi_relay_min_ms;    // minimum time between GI relay changes
  uint16_t host_timeout_ms;    // no OutputState for this long -> coils off
  uint8_t display;             // DisplayMode
};

struct HighPowerConfig {
  uint16_t coin_door_switch;   // 0 = no coin door: treated as closed
  uint16_t game_on_solenoid;   // 0 = no game-on coil: power always on
  uint16_t tilt_switch;        // 0 = none
};

struct Devices {
  CoilConfig coil[kNumCoilPorts];
  LampConfig lamp[kNumLampPorts];
  SwitchConfig sw[kNumSwitchPorts];
  BoardSettings board;
  HighPowerConfig high_power;
  uint8_t platform;
  uint8_t next_board[8];       // token successor per virtual board id
};

void DevicesReset(Devices& d);

// Applies ConfigFrames in the order libppuc sends them. A PORT key starts a
// new device in its section; the following keys of that section fill it in.
class ConfigApplier {
 public:
  explicit ConfigApplier(Devices& d) : d_(d) {}
  void Reset();
  // Returns false for keys this board does not know (still acknowledged:
  // PPUC acks every frame addressed to the board).
  bool Apply(uint8_t board, uint8_t topic, uint8_t index, uint8_t key, uint32_t value);

 private:
  // A PWM output is staged until its TYPE arrives: the same port number means
  // a coil for a solenoid and a matrix lamp for type "lamp".
  struct PendingPwm {
    CoilConfig coil;
    uint8_t brightness;
    uint16_t light_up_ms;
    uint16_t after_glow_ms;
    bool has_ramp;
  };

  Devices& d_;
  PendingPwm pending_ = {};
  uint16_t pwm_port_ = 0;
  uint16_t lamp_port_ = 0;
  uint16_t switch_port_ = 0;
  uint16_t matrix_port_ = 0;
};

}  // namespace sam

// SPDX-License-Identifier: GPL-3.0-or-later
#include "devices.h"

#include <string.h>

#include "../ppuc/ppuc_topics.h"

namespace sam {

void DevicesReset(Devices& d) {
  memset(&d, 0, sizeof(d));
  d.board.lamp_slot_us = 250;         // 2.5 ms frame, 400 Hz: no visible LED flicker
  d.board.lamp_blank_us = 24;         // ROM value
  d.board.default_brightness = 255;
  d.board.default_light_up_ms = 0;
  d.board.default_after_glow_ms = 0;
  d.board.switch_strobes = 8;         // ARCHITECTURE.md Q15: drive all 8
  d.board.strobe_dwell_us = 125;      // 8 strobes -> 1 ms full scan, like the ROM
  d.board.strobe_settle_us = 100;     // 1 k / 100 nF return filter needs ~70 us
  d.board.coil_pwm_period_us = 12000; // ROM flipper hold: 1 ms on / 11 ms off
  d.board.gi_relay_min_ms = 100;
  d.board.host_timeout_ms = 50;
  for (auto& n : d.next_board) n = 0xFF;
}

void ConfigApplier::Reset() {
  pwm_port_ = lamp_port_ = switch_port_ = matrix_port_ = 0;
}

namespace {

constexpr uint16_t Clamp16(uint32_t v) { return v > 0xFFFF ? 0xFFFF : static_cast<uint16_t>(v); }
constexpr uint8_t Clamp8(uint32_t v) { return v > 0xFF ? 0xFF : static_cast<uint8_t>(v); }

}  // namespace

bool ConfigApplier::Apply(uint8_t board, uint8_t topic, uint8_t index, uint8_t key,
                          uint32_t value) {
  (void)index;
  switch (topic) {
    case CONFIG_TOPIC_PLATFORM:
      d_.platform = Clamp8(value);
      return true;

    case CONFIG_TOPIC_COIN_DOOR_CLOSED_SWITCH:
      if (key != CONFIG_TOPIC_NUMBER) return false;
      d_.high_power.coin_door_switch = Clamp16(value);
      return true;

    case CONFIG_TOPIC_GAME_ON_SOLENOID:
      if (key != CONFIG_TOPIC_NUMBER) return false;
      d_.high_power.game_on_solenoid = Clamp16(value);
      return true;

    case CONFIG_TOPIC_TILT_SWITCH:
      if (key != CONFIG_TOPIC_NUMBER) return false;
      d_.high_power.tilt_switch = Clamp16(value);
      return true;

    case CONFIG_TOPIC_SWITCH_CHAIN:
      if (key == CONFIG_TOPIC_NEXT_BOARD) {
        if (board < 8) d_.next_board[board] = Clamp8(value);
        return true;
      }
      // SWITCH_REPLY_DELAY_US is an RS485 turnaround setting; there is no
      // shared bus here.
      return key == CONFIG_TOPIC_SWITCH_REPLY_DELAY_US;

    case CONFIG_TOPIC_PWM: {
      switch (key) {
        case CONFIG_TOPIC_PORT:
          memset(&pending_, 0, sizeof(pending_));
          pwm_port_ = Clamp16(value);
          return true;
        case CONFIG_TOPIC_NUMBER: pending_.coil.number = Clamp16(value); return true;
        case CONFIG_TOPIC_POWER: pending_.coil.power = Clamp8(value); return true;
        case CONFIG_TOPIC_MIN_PULSE_TIME: pending_.coil.min_pulse_ms = Clamp16(value); return true;
        case CONFIG_TOPIC_MAX_PULSE_TIME: pending_.coil.max_pulse_ms = Clamp16(value); return true;
        case CONFIG_TOPIC_HOLD_POWER: pending_.coil.hold_power = Clamp8(value); return true;
        case CONFIG_TOPIC_HOLD_POWER_ACTIVATION_TIME:
          pending_.coil.hold_activation_ms = Clamp16(value);
          return true;
        case CONFIG_TOPIC_FAST_SWITCH: pending_.coil.fast_switch = Clamp16(value); return true;
        case CONFIG_TOPIC_STOP_SWITCH: pending_.coil.stop_switch[0] = Clamp16(value); return true;
        case CONFIG_TOPIC_STOP_SWITCH_2: pending_.coil.stop_switch[1] = Clamp16(value); return true;
        // Lamp extensions (proposal): only meaningful for type "lamp".
        case CONFIG_TOPIC_BRIGHTNESS: pending_.brightness = Clamp8(value); return true;
        case CONFIG_TOPIC_LIGHT_UP:
          pending_.light_up_ms = Clamp16(value);
          pending_.has_ramp = true;
          return true;
        case CONFIG_TOPIC_AFTER_GLOW:
          pending_.after_glow_ms = Clamp16(value);
          pending_.has_ramp = true;
          return true;
        case CONFIG_TOPIC_TYPE: {
          const uint8_t type = Clamp8(value);
          if (type == PWM_TYPE_LAMP) {
            if (pwm_port_ >= kNumLampPorts) return false;
            LampConfig& l = d_.lamp[pwm_port_];
            l.used = true;
            l.number = pending_.coil.number;
            l.brightness = pending_.brightness ? pending_.brightness : pending_.coil.power;
            l.light_up_ms = pending_.has_ramp ? pending_.light_up_ms : 0xFFFF;
            l.after_glow_ms = pending_.has_ramp ? pending_.after_glow_ms : 0xFFFF;
            return true;
          }
          if (pwm_port_ < kCoilPortFirst || pwm_port_ > kCoilPortLast) return false;
          CoilConfig& c = d_.coil[pwm_port_];
          c = pending_.coil;
          c.type = type;
          c.used = true;
          return true;
        }
      }
      return false;
    }

    case CONFIG_TOPIC_LAMPS:
      // PPUC sends PORT, TYPE, NUMBER, LED_NUMBER, COLOR for LED lamps. Here the
      // port is a SAM lamp port and LED-specific keys are ignored.
      if (key == CONFIG_TOPIC_PORT) {
        lamp_port_ = Clamp16(value);
        if (lamp_port_ >= kNumLampPorts) return false;
        LampConfig& l = d_.lamp[lamp_port_];
        memset(&l, 0, sizeof(l));
        l.used = true;
        l.light_up_ms = 0xFFFF;
        l.after_glow_ms = 0xFFFF;
        return true;
      }
      if (lamp_port_ == 0 || lamp_port_ >= kNumLampPorts) return false;
      switch (key) {
        case CONFIG_TOPIC_NUMBER: d_.lamp[lamp_port_].number = Clamp16(value); return true;
        case CONFIG_TOPIC_BRIGHTNESS: d_.lamp[lamp_port_].brightness = Clamp8(value); return true;
        case CONFIG_TOPIC_LIGHT_UP: d_.lamp[lamp_port_].light_up_ms = Clamp16(value); return true;
        case CONFIG_TOPIC_AFTER_GLOW: d_.lamp[lamp_port_].after_glow_ms = Clamp16(value); return true;
        default: return true;  // TYPE, LED_NUMBER, COLOR: nothing to do
      }

    case CONFIG_TOPIC_SWITCHES:
      switch (key) {
        case CONFIG_TOPIC_PORT:
          switch_port_ = Clamp16(value);
          return switch_port_ < kNumSwitchPorts;
        case CONFIG_TOPIC_NUMBER:
          if (switch_port_ == 0 || switch_port_ >= kNumSwitchPorts) return false;
          d_.sw[switch_port_].used = true;
          d_.sw[switch_port_].board = board;
          d_.sw[switch_port_].number = Clamp16(value);
          return true;
        case CONFIG_TOPIC_DEBOUNCE_TIME:
          if (switch_port_ == 0 || switch_port_ >= kNumSwitchPorts) return false;
          d_.sw[switch_port_].debounce_ms = Clamp16(value);
          return true;
        case CONFIG_TOPIC_MODE:
          if (switch_port_ == 0 || switch_port_ >= kNumSwitchPorts) return false;
          d_.sw[switch_port_].mode = Clamp8(value);
          return true;
      }
      return false;

    case CONFIG_TOPIC_SWITCH_MATRIX:
      // Rows and polarity are fixed by the hardware; the port is the SAM number.
      switch (key) {
        case CONFIG_TOPIC_ACTIVE_LOW:
        case CONFIG_TOPIC_NUM_ROWS:
          return true;
        case CONFIG_TOPIC_PORT:
          matrix_port_ = Clamp16(value);
          return matrix_port_ >= kSwitchMatrixFirst && matrix_port_ <= kSwitchMatrixLast;
        case CONFIG_TOPIC_NUMBER:
          if (matrix_port_ < kSwitchMatrixFirst || matrix_port_ > kSwitchMatrixLast) return false;
          d_.sw[matrix_port_].used = true;
          d_.sw[matrix_port_].board = board;
          d_.sw[matrix_port_].number = Clamp16(value);
          return true;
      }
      return false;

    case CONFIG_TOPIC_SAM_BOARD:
      switch (key) {
        case CONFIG_TOPIC_DURATION:
          if (value < 100 || value > 2000) return false;
          d_.board.lamp_slot_us = Clamp16(value);
          return true;
        case CONFIG_TOPIC_BRIGHTNESS: d_.board.default_brightness = Clamp8(value); return true;
        case CONFIG_TOPIC_LIGHT_UP: d_.board.default_light_up_ms = Clamp16(value); return true;
        case CONFIG_TOPIC_AFTER_GLOW: d_.board.default_after_glow_ms = Clamp16(value); return true;
        case CONFIG_TOPIC_NUM_ROWS:
          if (value < 1 || value > 8) return false;
          d_.board.switch_strobes = Clamp8(value);
          d_.board.strobe_dwell_us = static_cast<uint16_t>(1000 / value);
          return true;
        case CONFIG_TOPIC_FREQUENCY:
          if (value < 20 || value > 1000) return false;
          d_.board.coil_pwm_period_us = static_cast<uint16_t>(1000000 / value);
          return true;
        case CONFIG_TOPIC_MAX_PULSE_TIME:
          if (value < 10 || value > 1000) return false;
          d_.board.host_timeout_ms = Clamp16(value);
          return true;
      }
      return false;
  }
  return false;
}

}  // namespace sam

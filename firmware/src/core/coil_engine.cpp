// SPDX-License-Identifier: GPL-3.0-or-later
#include "coil_engine.h"

#include <string.h>

#include "../ppuc/ppuc_topics.h"

namespace sam {

namespace {

bool HostDriven(uint8_t type) {
  return type == PWM_TYPE_SOLENOID || type == PWM_TYPE_FLASHER || type == PWM_TYPE_MOTOR ||
         type == PWM_TYPE_SHAKER;
}

bool SwitchDriven(uint8_t type) { return type == PWM_TYPE_SOLENOID || type == PWM_TYPE_MOTOR; }

bool BitOf(const uint8_t* bitmap, uint8_t port) { return (bitmap[port / 8] >> (port % 8)) & 1u; }

}  // namespace

void CoilEngine::Reset() {
  memset(st_, 0, sizeof(st_));
  power_on_ = coin_door_closed_ = tilt_ = false;
}

void CoilEngine::Activate(State& s, const CoilConfig& c, uint32_t now_us, bool fast) {
  s.active = true;
  s.since_us = now_us;
  s.power = c.power;
  s.scheduled_off = false;
  s.fast_managed = fast;
}

void CoilEngine::Deactivate(State& s) {
  s.active = false;
  s.power = 0;
  s.scheduled_off = false;
  s.fast_managed = false;
}

void CoilEngine::Update(uint32_t now_us, const Devices& d, const CoilInputs& in,
                        const SwitchLookup& sw, uint8_t drive_on[kNumCoilPorts]) {
  const HighPowerConfig& hp = d.high_power;
  power_on_ = hp.game_on_solenoid == 0 || in.game_on;
  coin_door_closed_ = hp.coin_door_switch == 0 || sw.Closed(hp.coin_door_switch);
  const bool tilt = hp.tilt_switch != 0 && sw.Closed(hp.tilt_switch);
  const bool tilt_rising = tilt && !tilt_;
  tilt_ = tilt;

  const bool available = power_on_ && coin_door_closed_ && in.allowed;
  const bool fast_allowed = available && !tilt;

  for (uint8_t port = kCoilPortFirst; port <= kCoilPortLast; ++port) {
    State& s = st_[port];
    const CoilConfig& c = d.coil[port];
    drive_on[port] = 0;
    if (!c.used) {
      Deactivate(s);
      continue;
    }

    const bool host_on = BitOf(in.host_on, port);
    const bool host_rise = host_on && !s.host_prev;
    const bool host_fall = !host_on && s.host_prev;
    s.host_prev = host_on;

    if (!available) {
      // High power gone, link lost or interlock open: everything off, and a
      // held flipper button must be released before it fires again.
      Deactivate(s);
      s.fast_closed = false;
      s.wait_release = c.fast_switch != 0;
      // host_prev keeps tracking, so when power comes back a coil the host
      // still holds on fires only on its next command, as in PPUC.
      continue;
    }

    if (tilt_rising && c.fast_switch != 0) {
      Deactivate(s);
      s.fast_closed = false;
      s.wait_release = true;
    }

    // Stop switches: engage on the closing edge while on, release on level.
    bool any_stop_closed = false;
    bool stop_edge = false;
    for (uint8_t k = 0; k < kMaxStopSwitches; ++k) {
      if (c.stop_switch[k] == 0) continue;
      const bool closed = sw.Closed(c.stop_switch[k]);
      if (closed && !s.stop_closed[k]) stop_edge = true;
      s.stop_closed[k] = closed;
      any_stop_closed |= closed;
    }
    if (SwitchDriven(c.type)) {
      if (stop_edge && s.active) {
        s.stop_engaged = true;
        Deactivate(s);
      }
      if (s.stop_engaged && !any_stop_closed) s.stop_engaged = false;
    }

    // Fast-flip switch.
    if (c.fast_switch != 0 && SwitchDriven(c.type)) {
      if (fast_allowed) {
        s.fast_closed = sw.Closed(c.fast_switch);
        if (!s.fast_closed) s.wait_release = false;
        if (!s.active && s.fast_closed && !s.wait_release && !s.stop_engaged) {
          Activate(s, c, now_us, true);
        }
      } else {
        s.fast_closed = false;
        s.wait_release = true;
      }
    }

    // Host commands.
    if (HostDriven(c.type)) {
      if (host_rise && !s.stop_engaged && !s.active) {
        Activate(s, c, now_us, false);
      } else if (host_fall && s.active) {
        const uint32_t on_ms = (now_us - s.since_us) / 1000u;
        if (c.min_pulse_ms > 0 && on_ms < c.min_pulse_ms) {
          s.scheduled_off = true;
        } else {
          Deactivate(s);
        }
      }
    }

    // Envelope.
    if (s.active) {
      const uint32_t on_ms = (now_us - s.since_us) / 1000u;
      const bool min_elapsed = c.min_pulse_ms == 0 || on_ms > c.min_pulse_ms;
      if (c.max_pulse_ms > 0 && on_ms > c.max_pulse_ms) {
        if (s.fast_managed && s.fast_closed) s.wait_release = true;
        Deactivate(s);
      } else if (s.scheduled_off && min_elapsed) {
        Deactivate(s);
      } else if (s.fast_managed && min_elapsed && !s.fast_closed) {
        Deactivate(s);
      } else if (c.hold_activation_ms > 0 && s.power > c.hold_power &&
                 on_ms > c.hold_activation_ms) {
        s.power = c.hold_power;
      }
    }

    if (s.active && s.power > 0) {
      if (s.power >= 255) {
        drive_on[port] = 1;
      } else {
        const uint32_t period = d.board.coil_pwm_period_us ? d.board.coil_pwm_period_us : 12000;
        const uint32_t phase = (now_us - s.since_us) % period;
        drive_on[port] = phase < (period * s.power) / 255u;
      }
    }
  }
}

}  // namespace sam

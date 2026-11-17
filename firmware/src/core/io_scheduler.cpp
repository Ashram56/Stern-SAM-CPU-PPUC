// SPDX-License-Identifier: GPL-3.0-or-later
#include "io_scheduler.h"

#include <string.h>

namespace sam {

namespace {
constexpr uint8_t kSolRegs[4] = {kRegSolB, kRegSolA, kRegSolC, kRegFlshLmp};
constexpr uint8_t kAuxCoilBoard = kAuxCoilStrobeBit - 3;

// The device table is cleared on a host restart while this runs: keep the
// scan going with sane timing whatever it holds.
uint16_t SlotUs(const Devices& d) {
  const uint16_t v = d.board.lamp_slot_us;
  return v < 50 ? 50 : (v > 5000 ? 5000 : v);
}
uint16_t BlankUs(const Devices& d) {
  const uint16_t v = d.board.lamp_blank_us;
  return v >= SlotUs(d) ? static_cast<uint16_t>(SlotUs(d) / 2) : v;
}
}  // namespace

void IoScheduler::WriteAuxGi() {
  bus_.Write(kRegAuxGi, gi_on_ ? kAuxGiIdle : static_cast<uint8_t>(kAuxGiIdle | kAuxGiRelayOff));
}

void IoScheduler::LatchAux(uint8_t strobe_bit, uint8_t value) {
  // AUX_DRV, then a low pulse on the board's strobe: the latch takes the data
  // on the rising edge, as in the ROM's aux coil burst.
  const uint8_t idle = gi_on_ ? kAuxGiIdle : static_cast<uint8_t>(kAuxGiIdle | kAuxGiRelayOff);
  bus_.Write(kRegAuxDrv, value);
  bus_.Write(kRegAuxGi, static_cast<uint8_t>(idle & ~(1u << strobe_bit)));
  bus_.Write(kRegAuxGi, idle);
}

void IoScheduler::Start(uint32_t now_us, const Devices& d) {
  gi_on_ = false;
  gi_changed_us_ = now_us;
  WriteAuxGi();
  for (uint8_t r : kSolRegs) bus_.Write(r, 0);
  memset(sol_, 0, sizeof(sol_));
  sol_valid_ = true;
  sol_refresh_us_ = now_us;
  memset(aux_, 0, sizeof(aux_));
  for (uint8_t b = 3; b <= 7; ++b) LatchAux(b, 0);
  bus_.Write(kRegLmpDrv, 0);
  bus_.Write(kRegLmpStb, 0);
  bus_.Write(kRegAuxLmp, 0);
  started_ = true;
  line_ = kLampLines - 1;  // the first slot is line 0
  frame_start_us_ = now_us;
  status_due_us_ = now_us;
  StartSlot(now_us, d, nullptr);
}

void IoScheduler::StartSlot(uint32_t now_us, const Devices& d, const uint8_t* lamps_on) {
  // Dark first, then move the strobe to the next line.
  bus_.Write(kRegLmpDrv, 0);
  if (line_ < 8) {
    bus_.Write(kRegLmpStb, 0);
  } else {
    bus_.Write(kRegAuxLmp, 0);
  }
  line_ = static_cast<uint8_t>((line_ + 1) % kLampLines);
  if (line_ < 8) {
    bus_.Write(kRegLmpStb, static_cast<uint8_t>(1u << line_));
  } else {
    bus_.Write(kRegAuxLmp, static_cast<uint8_t>(1u << (line_ - 8)));
  }
  slot_start_us_ = now_us;

  if (line_ == 0) {
    // New lamp frame: move the ramps on, and plan the aux boards' PWM
    // period (one per frame).
    static const uint8_t kNone[(kNumLampPorts + 7) / 8] = {};
    lamps_.UpdateLevels(now_us - frame_start_us_, d, lamps_on ? lamps_on : kNone);
    frame_start_us_ = now_us;
    frames_++;
    const uint16_t period = static_cast<uint16_t>(SlotUs(d) * kLampLines);
    for (uint8_t b = 3; b <= 7; ++b) {
      AuxBoard& a = aux_[b - 3];
      a.next = 0;
      a.steps = 0;
      if (b == kAuxCoilStrobeBit || !lamps_.AuxUsed(b, d)) continue;
      a.steps = lamps_.BuildAux(b, period, a.step);
      if (a.steps == 0 && a.last != 0) {
        // Everything dark: the latch would otherwise keep what it had.
        a.step[0] = {0, 0};
        a.steps = 1;
      }
    }
  }

  blank_us_ = BlankUs(d);
  const uint16_t window = static_cast<uint16_t>(SlotUs(d) - blank_us_);
  steps_ = lamps_on ? lamps_.BuildLine(line_, window, step_) : 0;
  next_step_ = 0;
}

void IoScheduler::Poll(uint32_t now_us, const Devices& d, const uint8_t* lamps_on) {
  if (!started_) return;

  if (now_us - slot_start_us_ >= SlotUs(d)) {
    StartSlot(now_us, d, lamps_on);
  }
  while (next_step_ < steps_ &&
         now_us - slot_start_us_ >= static_cast<uint32_t>(blank_us_) + step_[next_step_].t_us) {
    bus_.Write(kRegLmpDrv, step_[next_step_].drive);
    next_step_++;
  }

  for (uint8_t b = 3; b <= 7; ++b) {
    AuxBoard& a = aux_[b - 3];
    while (a.next < a.steps && now_us - frame_start_us_ >= a.step[a.next].t_us) {
      if (a.step[a.next].drive != a.last) {
        LatchAux(b, a.step[a.next].drive);
        a.last = a.step[a.next].drive;
      }
      a.next++;
    }
  }

  if (static_cast<int32_t>(now_us - status_due_us_) >= 0) {
    bus_.Read(kRegStatus);
    status_due_us_ = now_us + kStatusPeriodUs;
  }
}

void IoScheduler::SetCoils(uint32_t now_us, const uint8_t drive_on[kNumCoilPorts]) {
  uint8_t v[5] = {};
  for (uint8_t port = kCoilPortFirst; port <= kCoilPortLast; ++port) {
    if (drive_on[port]) v[(port - 1) / 8] |= static_cast<uint8_t>(1u << ((port - 1) % 8));
  }
  const bool refresh = !sol_valid_ || now_us - sol_refresh_us_ >= kCoilRefreshUs;
  for (uint8_t i = 0; i < 4; ++i) {
    if (refresh || v[i] != sol_[i]) bus_.Write(kSolRegs[i], v[i]);
  }
  if (refresh || v[4] != sol_[4]) {
    LatchAux(kAuxCoilStrobeBit, v[4]);
    aux_[kAuxCoilBoard].last = v[4];
  }
  if (refresh) sol_refresh_us_ = now_us;
  memcpy(sol_, v, sizeof(sol_));
  sol_valid_ = true;
}

void IoScheduler::SetGiRelay(uint32_t now_us, const Devices& d, bool on) {
  if (on == gi_on_) return;
  if (now_us - gi_changed_us_ < static_cast<uint32_t>(d.board.gi_relay_min_ms) * 1000u) return;
  gi_on_ = on;
  gi_changed_us_ = now_us;
  WriteAuxGi();
}

}  // namespace sam

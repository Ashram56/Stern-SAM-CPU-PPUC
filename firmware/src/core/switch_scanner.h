// Switch debouncing for the 74HC165 chain.
//
// The board must not add a long debounce: PinMAME runs the ROM's own two-stage
// debounce on whatever we report (ARCHITECTURE.md 5.5). So this only filters
// electrical glitches:
//   - matrix switches: a change must be seen on 2 consecutive scans, like the
//     ROM's first stage;
//   - dedicated switches: sampled on every chain pass (about 6 us), a change
//     must hold for kDedicatedMinWindowUs;
//   - a configured `debounce` (ms) lengthens either window;
//   - PPUC fastFlip mode accepts a closing edge on its first sample.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>

#include "devices.h"
#include "switch_chain.h"

namespace sam {

constexpr uint32_t kDedicatedMinWindowUs = 50;

class SwitchScanner {
 public:
  void Reset();

  // One chain pass. `latched_pattern` is the strobe pattern that was active
  // in the 595s while the 165s captured `in`.
  void OnPass(uint32_t now_us, uint16_t latched_pattern, const ChainInputs& in,
              const Devices& d);

  // STATUS register read on the IO board (interlocks, lamp driver faults).
  void OnStatus(uint32_t now_us, uint8_t status, const Devices& d);

  bool State(uint16_t port) const {
    return port < kNumSwitchPorts && ((stable_[port / 32] >> (port % 32)) & 1u);
  }
  const uint32_t* StableBitmap() const { return stable_; }
  uint32_t ChangeCount() const { return change_count_; }
  // Raw matrix returns of each strobe, for diagnostics.
  uint16_t MatrixRaw(uint8_t strobe) const { return strobe < kMaxStrobes ? column_[strobe] : 0; }

  static constexpr uint8_t kWords = (kNumSwitchPorts + 31) / 32;

 private:
  void Feed(uint16_t port, bool raw, uint32_t now_us, uint32_t min_window_us,
            const Devices& d);
  void CommitColumn(int8_t strobe, uint16_t returns, uint32_t now_us, const Devices& d);

  uint32_t stable_[kWords] = {};
  uint32_t pending_[kWords] = {};
  uint32_t pending_since_[kNumSwitchPorts] = {};
  uint32_t change_count_ = 0;

  int8_t cur_strobe_ = -1;
  uint32_t strobe_since_us_ = 0;
  bool have_sample_ = false;
  uint16_t sample_ = 0;
  uint16_t column_[kMaxStrobes] = {};
};

}  // namespace sam

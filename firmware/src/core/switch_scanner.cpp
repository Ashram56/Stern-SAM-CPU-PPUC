// SPDX-License-Identifier: GPL-3.0-or-later
#include "switch_scanner.h"

#include <string.h>

#include "../ppuc/ppuc_topics.h"

namespace sam {

void SwitchScanner::Reset() {
  memset(stable_, 0, sizeof(stable_));
  memset(pending_, 0, sizeof(pending_));
  memset(pending_since_, 0, sizeof(pending_since_));
  memset(column_, 0, sizeof(column_));
  cur_strobe_ = -1;
  have_sample_ = false;
  change_count_++;
}

void SwitchScanner::Feed(uint16_t port, bool raw, uint32_t now_us, uint32_t min_window_us,
                         const Devices& d) {
  const uint32_t mask = 1u << (port % 32);
  uint32_t& stable = stable_[port / 32];
  uint32_t& pending = pending_[port / 32];
  const bool cur = (stable & mask) != 0;
  if (raw == cur) {
    pending &= ~mask;
    return;
  }
  if (!(pending & mask)) {
    pending |= mask;
    pending_since_[port] = now_us;
  }
  uint32_t window = min_window_us;
  const SwitchConfig& c = d.sw[port];
  if (c.used) {
    const uint32_t configured = static_cast<uint32_t>(c.debounce_ms) * 1000u;
    if (configured > window) window = configured;
    if (c.mode == SWITCH_DEBOUNCE_FAST_FLIP && raw) window = 0;
  }
  if (now_us - pending_since_[port] >= window) {
    if (raw) {
      stable |= mask;
    } else {
      stable &= ~mask;
    }
    pending &= ~mask;
    change_count_++;
  }
}

void SwitchScanner::CommitColumn(int8_t strobe, uint16_t returns, uint32_t now_us,
                                 const Devices& d) {
  column_[strobe] = returns;
  // Seen on two consecutive scans: one sample per scan, so a window just under
  // one scan period accepts the change on the second sample.
  const uint32_t scan_us =
      static_cast<uint32_t>(d.board.strobe_dwell_us) * d.board.switch_strobes;
  const uint32_t window = scan_us - scan_us / 4;
  for (uint8_t r = 0; r < 16; ++r) {
    Feed(MatrixSwitchPort(static_cast<uint8_t>(strobe), r), (returns >> r) & 1u, now_us,
         window, d);
  }
}

void SwitchScanner::OnPass(uint32_t now_us, uint16_t latched_pattern, const ChainInputs& in,
                           const Devices& d) {
  // Matrix: keep the last sample taken after the returns have settled, and
  // file it when the strobe moves on.
  const int8_t strobe = PatternStrobe(latched_pattern);
  if (strobe != cur_strobe_) {
    if (cur_strobe_ >= 0 && have_sample_) {
      CommitColumn(cur_strobe_, sample_, now_us, d);
    }
    cur_strobe_ = strobe;
    strobe_since_us_ = now_us;
    have_sample_ = false;
  } else if (strobe >= 0 && now_us - strobe_since_us_ >= d.board.strobe_settle_us) {
    sample_ = in.returns;
    have_sample_ = true;
  }

  // Dedicated switches and DIPs, every pass.
  for (uint8_t k = 0; k < 32; ++k) {
    Feed(static_cast<uint16_t>(kSwitchDedicatedFirst + k), (in.dedicated >> k) & 1u, now_us,
         kDedicatedMinWindowUs, d);
  }
  Feed(kSwitchMemProtect, in.mem_protect, now_us, kDedicatedMinWindowUs, d);
}

void SwitchScanner::OnStatus(uint32_t now_us, uint8_t status, const Devices& d) {
  // Interlocks change slowly and the ROM filters them over ~128 ms; 20 ms is
  // enough to ignore zero-cross ripple on the sense lines.
  constexpr uint32_t kStatusWindowUs = 20000;
  Feed(kSwitch20V, status & kStatus20V, now_us, kStatusWindowUs, d);
  Feed(kSwitch50V, status & kStatus50V, now_us, kStatusWindowUs, d);
  Feed(kSwitchLmp1Fault, status & kStatusLmp1Fault, now_us, kStatusWindowUs, d);
  Feed(kSwitchLmp2Fault, status & kStatusLmp2Fault, now_us, kStatusWindowUs, d);
}

}  // namespace sam

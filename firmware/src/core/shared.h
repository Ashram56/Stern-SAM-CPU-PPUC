// State handed between the two cores.
//
// core0 runs the PPUC link, the session and the display; core1 runs the IO
// bus, switch chain, coils and lamps (hw/realtime.cpp). Each block below has
// exactly one writer and is copied whole under a sequence lock, so a reader
// never sees half of an update.
//
// The device tables (Devices) are shared directly: core0 fills them while the
// host configures the board, before it sends any output.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>
#include <string.h>

#include "sam_io.h"
#include "switch_scanner.h"

namespace sam {

template <typename T>
class SeqLock {
 public:
  void Write(const T& v) {
    seq_ = seq_ + 1;
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
    memcpy(&data_, &v, sizeof(T));
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
    seq_ = seq_ + 1;
  }
  void Read(T& out) const {
    for (;;) {
      const uint32_t s = seq_;
      if (s & 1u) continue;
      __atomic_thread_fence(__ATOMIC_SEQ_CST);
      memcpy(&out, &data_, sizeof(T));
      __atomic_thread_fence(__ATOMIC_SEQ_CST);
      if (seq_ == s) return;
    }
  }
  uint32_t Version() const { return seq_; }

 private:
  volatile uint32_t seq_ = 0;
  T data_ = {};
};

// core0 -> core1: what the host wants.
struct HostOutputs {
  uint8_t coils[(kNumCoilPorts + 7) / 8];  // bitmap by coil port
  uint8_t lamps[(kNumLampPorts + 7) / 8];  // bitmap by lamp port
  uint8_t gi_level;                        // GI string 1, 0-8
  bool game_on;
  bool running;                            // session configured and mapped
  uint32_t stamp_us;                       // when the last OutputState arrived
};

// core0 -> core1: switches the coil rules look at (fast flip, stop, coin
// door, tilt), resolved to a local port, or to a state reported by another
// board.
struct SwitchRefs {
  static constexpr uint8_t kMax = 32;
  uint8_t count;
  uint16_t number[kMax];
  uint16_t port[kMax];   // 0 = not on this board: use `remote`
  uint32_t remote;       // bit k = number[k] closed on another board
};

// core1 -> core0: debounced switch states.
struct SwitchSnapshot {
  uint32_t bitmap[SwitchScanner::kWords];  // by switch port
  uint32_t change_count;
  uint8_t status;                          // last STATUS byte read
};

struct Shared {
  SeqLock<HostOutputs> outputs;
  SeqLock<SwitchRefs> refs;
  SeqLock<SwitchSnapshot> switches;
  volatile uint32_t core1_heartbeat;
  volatile bool io_board_up;               // lamp scan running, IO board out of reset
};

}  // namespace sam

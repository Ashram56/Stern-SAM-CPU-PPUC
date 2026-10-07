// Everything core1 writes to the IO board, in time order: the lamp matrix
// scan with its in-slot PWM edges, the strobed aux boards (aux coils 33-40,
// ramp tubes), the four coil registers, the GI relay and the STATUS reads.
//
// Kept free of hardware so the host tests can check the register sequence;
// hw/realtime.cpp feeds it the time and sends its writes to the bus PIO.
//
// The lamp scan never stops once started: line 0 is LMP_STB bit 0 (DRV0),
// which feeds the IO board's watchdog. If the strobes stop, the IO board
// drops every driver.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>

#include "devices.h"
#include "lamp_engine.h"

namespace sam {

class Bus {
 public:
  virtual void Write(uint8_t reg, uint8_t value) = 0;
  // Queue a read; the byte comes back through the bus PIO's RX FIFO.
  virtual void Read(uint8_t reg) = 0;
};

class IoScheduler {
 public:
  static constexpr uint32_t kStatusPeriodUs = 1000;
  static constexpr uint32_t kCoilRefreshUs = 20000;

  IoScheduler(Bus& bus, LampEngine& lamps) : bus_(bus), lamps_(lamps) {}

  // Clears every output register and starts the lamp scan at line 0.
  void Start(uint32_t now_us, const Devices& d);

  // Runs whatever is due. `lamps_on` is the host's lamp bitmap by port, or
  // nullptr for all lamps off.
  void Poll(uint32_t now_us, const Devices& d, const uint8_t* lamps_on);

  // Coil drivers by port (CoilEngine output). Writes the registers that
  // changed, and all of them every kCoilRefreshUs.
  void SetCoils(uint32_t now_us, const uint8_t drive_on[kNumCoilPorts]);

  // GI relay (reg 0xB bit 0, 0 = on). Changes are at least
  // BoardSettings::gi_relay_min_ms apart.
  void SetGiRelay(uint32_t now_us, const Devices& d, bool on);

  uint32_t Frames() const { return frames_; }
  uint8_t Line() const { return line_; }

 private:
  struct AuxBoard {
    uint8_t steps;
    uint8_t next;
    uint8_t last;           // last value latched
    LampStep step[kMaxLampSteps];
  };

  void StartSlot(uint32_t now_us, const Devices& d, const uint8_t* lamps_on);
  void LatchAux(uint8_t strobe_bit, uint8_t value);
  void WriteAuxGi();

  Bus& bus_;
  LampEngine& lamps_;

  // Lamp scan.
  bool started_ = false;
  uint8_t line_ = 0;
  uint32_t slot_start_us_ = 0;
  uint32_t frame_start_us_ = 0;
  uint32_t frames_ = 0;
  uint16_t blank_us_ = 0;
  uint8_t steps_ = 0;
  uint8_t next_step_ = 0;
  LampStep step_[kMaxLampSteps];
  AuxBoard aux_[5];         // reg 0xB bits 3-7 (bit 6 = aux coils, not a lamp board)

  // Coils.
  uint8_t sol_[5] = {};     // SOL_B, SOL_A, SOL_C, FLSH_LMP, aux coils
  bool sol_valid_ = false;
  uint32_t sol_refresh_us_ = 0;

  // Reg 0xB.
  bool gi_on_ = false;
  uint32_t gi_changed_us_ = 0;

  uint32_t status_due_us_ = 0;
};

}  // namespace sam

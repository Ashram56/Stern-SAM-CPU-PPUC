// The SAM IO power driver board as seen from the bus, and the device ports
// this firmware exposes to PPUC.
//
// Register map and bit meanings: Tron-Legacy-LE-ROM-Decryption
// io/bus/bus_register_map.csv and io/bus/README.md (sections 5-8).
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>

namespace sam {

// J1/J9 registers, A3-A0.
enum Reg : uint8_t {
  kRegSolA = 0x0,     // W coils 9-16, bit 0 = coil 9
  kRegSolB = 0x1,     // W coils 1-8, bit 0 = coil 1
  kRegSolC = 0x2,     // W coils 17-24
  kRegFlshLmp = 0x3,  // W coils 25-32 (flashers)
  kRegStatus = 0x5,   // R D0 20 V interlock, D1 50 V interlock, D2 zero cross,
                      //   D3 LMP1STAT, D4 LMP2STAT
  kRegAuxDrv = 0x6,   // W data byte for the strobed aux boards
  kRegAuxIn = 0x7,    // R J3 pins 1-8
  kRegLmpStb = 0x8,   // W lamp strobe lines 0-7 (bit 0 = DRV0 feeds the IO watchdog)
  kRegAuxLmp = 0x9,   // W lamp strobe lines 8-9
  kRegLmpDrv = 0xA,   // W lamp drive bits of the active line
  kRegAuxGi = 0xB,    // W bit 0 GI relay (0 = on), bits 3-7 aux strobes (idle high)
};

// STATUS bits.
constexpr uint8_t kStatus20V = 0x01;
constexpr uint8_t kStatus50V = 0x02;
constexpr uint8_t kStatusZeroCross = 0x04;
constexpr uint8_t kStatusLmp1Fault = 0x08;
constexpr uint8_t kStatusLmp2Fault = 0x10;

// Register 0xB. The ROM keeps bits 1-2 high as well, idle value 0xFE with GI on.
constexpr uint8_t kAuxGiIdle = 0xFE;
constexpr uint8_t kAuxGiRelayOff = 0x01;
// Aux coils 33-40 are latched by strobe bit 6 in every SAM ROM coil burst.
constexpr uint8_t kAuxCoilStrobeBit = 6;

// ---------------------------------------------------------------------------
// PPUC ports
//
// PPUC configures each device with a board-specific `port`. On this board the
// port is the device's SAM number wherever SAM has one, so a game YAML can be
// generated straight from PinMAME's numbering.
// ---------------------------------------------------------------------------

// Coils: SAM coil numbers. 1-32 on the driver board, 33-40 aux coils (AUX_DRV
// latched with reg 0xB bit 6).
constexpr uint8_t kCoilPortFirst = 1;
constexpr uint8_t kCoilPortLast = 40;
constexpr uint8_t kNumCoilPorts = 41;  // index by port, 0 unused

// Lamps: SAM matrix lamp numbers 1-80. Lamp n is strobe line (n-1)/8 and
// LMP_DRV bit 7-((n-1)%8).
constexpr uint8_t kLampPortFirst = 1;
constexpr uint8_t kLampPortLast = 80;
constexpr uint8_t kLampLines = 10;
// Aux latch outputs (ramp tubes and similar): port 200 + (strobe - 3) * 8 + bit,
// where strobe is the reg 0xB bit (3-7) that latches the board and bit is the
// AUX_DRV bit. Tron LE: left tube ESTB = bit 4 (R 205, G 204, B 203), right
// tube DSTB = bit 5 (R 213, G 212, B 211).
constexpr uint8_t kAuxLampPortFirst = 200;
constexpr uint8_t kAuxLampPortLast = 239;
constexpr uint8_t kNumLampPorts = 240;

inline bool IsMatrixLampPort(uint16_t port) {
  return port >= kLampPortFirst && port <= kLampPortLast;
}
inline bool IsAuxLampPort(uint16_t port) {
  return port >= kAuxLampPortFirst && port <= kAuxLampPortLast;
}
inline uint8_t AuxLampStrobeBit(uint16_t port) {
  return static_cast<uint8_t>(3 + (port - kAuxLampPortFirst) / 8);
}
inline uint8_t AuxLampDrvBit(uint16_t port) {
  return static_cast<uint8_t>((port - kAuxLampPortFirst) % 8);
}
inline uint8_t LampLine(uint16_t port) { return static_cast<uint8_t>((port - 1) / 8); }
inline uint8_t LampDrvBit(uint16_t port) { return static_cast<uint8_t>(7 - (port - 1) % 8); }

// Coil port -> register and bit.
inline bool CoilPortToBus(uint16_t port, uint8_t& reg, uint8_t& bit) {
  if (port < 1 || port > 40) return false;
  const uint8_t i = static_cast<uint8_t>(port - 1);
  bit = i % 8;
  switch (i / 8) {
    case 0: reg = kRegSolB; return true;
    case 1: reg = kRegSolA; return true;
    case 2: reg = kRegSolC; return true;
    case 3: reg = kRegFlshLmp; return true;
    default: reg = kRegAuxDrv; return true;  // aux coils, latched by strobe bit 6
  }
}

// Switches: SAM switch numbers. Matrix strobe s (0-7), return r (0-15) is
// s * 16 + r + 1 (1-128; the ROM scans strobes 0-3). Dedicated D1-D32 are
// 129-160 (D25-D32 = the DIP switches). Extra inputs follow.
constexpr uint16_t kSwitchMatrixFirst = 1;
constexpr uint16_t kSwitchMatrixLast = 128;
constexpr uint16_t kSwitchDedicatedFirst = 129;  // D1
constexpr uint16_t kSwitchDedicatedLast = 160;   // D32 = DIP 8
constexpr uint16_t kSwitchMemProtect = 161;      // coin door memory protect (J2 pin 10)
constexpr uint16_t kSwitch20V = 162;             // STATUS D0, 1 = present
constexpr uint16_t kSwitch50V = 163;             // STATUS D1
constexpr uint16_t kSwitchLmp1Fault = 164;       // STATUS D3
constexpr uint16_t kSwitchLmp2Fault = 165;       // STATUS D4
constexpr uint16_t kNumSwitchPorts = 166;        // index by port, 0 unused

inline uint16_t MatrixSwitchPort(uint8_t strobe, uint8_t ret) {
  return static_cast<uint16_t>(strobe * 16 + ret + 1);
}

}  // namespace sam

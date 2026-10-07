// Bit layout of the 74HC165 input chain and the 74HC595 strobe chain.
//
// Chain order from the schematic (PR #4): SW_DATA (GPIO18) <- U30 <- U19 <- U18
// <- U17 <- U16 <- U15 <- U14 (serial input tied low). After the load pulse the
// first bit on SW_DATA is U30 input H, then U30 G ... A, then U19 H ... A, and
// so on: input k (D0-D7 = A-H) of the chip at stream offset o is stream bit
// o + 7 - k.
//
//   offset  chip  inputs D0..D7
//      0    U30   MEM_PROTECT, then 7 x GND
//      8    U19   matrix returns 1-8   (J6)
//     16    U18   matrix returns 9-16  (J12)
//     24    U17   dedicated D1-D8      (J2)
//     32    U16   dedicated D9-D16     (J3)
//     40    U15   dedicated D17-D24    (J13)
//     48    U14   DIP switches 1-8     (SW3) = D25-D32
//
// Every input reads 0 when its switch is closed (LM339 returns, dedicated
// inputs pulled to ground, DIP switches to ground). The decoded values below
// use 1 = closed.
//
// Strobe chain: STB_DATA (GPIO19) -> U31 -> U20. Of the 56 bits shifted out per
// pass only the last 16 stay in the 595s. Shifted MSB first from a 16-bit
// pattern word:
//   bit 15..8  -> U20 QH..QA = strobe 8..1   (1 = strobe active, line pulled low)
//   bit 7..2   -> U31 QH..QC = spare outputs
//   bit 1      -> U31 QB = GI_SPARE
//   bit 0      -> U31 QA = LED_STATUS
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>

namespace sam {

constexpr uint8_t kChainBits = 56;
constexpr uint8_t kMaxStrobes = 8;

struct ChainInputs {
  uint16_t returns;    // bit r = matrix return r + 1 closed
  uint32_t dedicated;  // bit k = D(k+1) closed, D25-D32 = DIP switches
  bool mem_protect;    // 1 = input pulled low (switch closed)
};

inline uint64_t ChainStream(uint32_t word0, uint32_t word1) {
  // word0 = stream bits 0-31 (first bit in bit 0). word1 holds stream bits
  // 32-55 in its top 24 bits (manual push after 24 more bits, shift right).
  return static_cast<uint64_t>(word0) | (static_cast<uint64_t>(word1 >> 8) << 32);
}

inline uint8_t ChainByte(uint64_t stream, uint8_t offset) {
  // Reassemble D0..D7 of the chip at `offset`: D_k is stream bit offset+7-k.
  uint8_t v = 0;
  for (uint8_t k = 0; k < 8; ++k) {
    if ((stream >> (offset + 7 - k)) & 1u) v |= static_cast<uint8_t>(1u << k);
  }
  return v;
}

inline ChainInputs DecodeChain(uint64_t stream) {
  ChainInputs in;
  const uint8_t u30 = static_cast<uint8_t>(~ChainByte(stream, 0));
  const uint8_t ret_lo = static_cast<uint8_t>(~ChainByte(stream, 8));
  const uint8_t ret_hi = static_cast<uint8_t>(~ChainByte(stream, 16));
  const uint8_t d1 = static_cast<uint8_t>(~ChainByte(stream, 24));
  const uint8_t d9 = static_cast<uint8_t>(~ChainByte(stream, 32));
  const uint8_t d17 = static_cast<uint8_t>(~ChainByte(stream, 40));
  const uint8_t dip = static_cast<uint8_t>(~ChainByte(stream, 48));
  in.returns = static_cast<uint16_t>(ret_lo | (ret_hi << 8));
  in.dedicated = static_cast<uint32_t>(d1) | (static_cast<uint32_t>(d9) << 8) |
                 (static_cast<uint32_t>(d17) << 16) | (static_cast<uint32_t>(dip) << 24);
  in.mem_protect = (u30 & 0x01) != 0;
  return in;
}

inline uint16_t StrobePattern(int8_t strobe, bool led_status, bool gi_spare) {
  uint16_t p = 0;
  if (strobe >= 0 && strobe < kMaxStrobes) p |= static_cast<uint16_t>(1u << (8 + strobe));
  if (gi_spare) p |= 0x0002;
  if (led_status) p |= 0x0001;
  return p;
}

// Which strobe a pattern word drives, or -1 for none.
inline int8_t PatternStrobe(uint16_t pattern) {
  const uint8_t s = static_cast<uint8_t>(pattern >> 8);
  for (int8_t i = 0; i < kMaxStrobes; ++i) {
    if (s == (1u << i)) return i;
  }
  return -1;
}

}  // namespace sam

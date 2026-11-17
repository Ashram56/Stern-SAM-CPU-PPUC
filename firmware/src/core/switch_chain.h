// Bit layout of the 74HC165 input chain and the 74HC595 strobe chain.
//
// Chain order from the schematic (board with the J2 / J10 review fixes):
// SW_DATA (GPIO18) <- U30 <- U19 <- U18 <- U17 <- U16 <- U15 (serial input tied
// low). After the load pulse the first bit on SW_DATA is U30 input H, then
// U30 G ... A, then U19 H ... A, and so on: input k (D0-D7 = A-H) of the chip
// at stream offset o is stream bit o + 7 - k.
//
//   offset  chip  inputs D0..D7
//      0    U30   D0 = dedicated D8 (J2 pin 10), then 7 x GND
//      8    U19   matrix returns 8..1   (J6: D0 = return 8 ... D7 = return 1)
//     16    U18   matrix returns 16..9  (J12: D0 = return 16 ... D7 = return 9)
//     24    U17   D0 = TAMPIN / memory protect (J2 pin 12), D1-D7 = dedicated
//                 D1-D7 (J2 pins 2, 3, 4, 6, 7, 8, 9)
//     32    U16   dedicated D9-D16     (J3)
//     40    U15   dedicated D17-D24    (J13)
//
// J6 and J12 follow the original pinout (return 1 on J6 pin 9, return 9 on
// J12 pin 9) while the board wires pin 1 to D0, so each return byte is bit
// reversed here. The board has no DIP switches: D25-D32 always read open.
//
// Every input reads 0 when its switch is closed (LM339 returns, dedicated
// inputs pulled to ground). The decoded values below use 1 = closed.
//
// Strobe chain: STB_DATA (GPIO19) -> U31 -> U20. Of the 48 bits shifted out per
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

constexpr uint8_t kChainBits = 48;
constexpr uint8_t kMaxStrobes = 8;

struct ChainInputs {
  uint16_t returns;    // bit r = matrix return r + 1 closed
  uint32_t dedicated;  // bit k = D(k+1) closed; D25-D32 are not fitted (always 0)
  bool mem_protect;    // 1 = input pulled low (switch closed)
};

inline uint64_t ChainStream(uint32_t word0, uint32_t word1) {
  // word0 = stream bits 0-31 (first bit in bit 0). word1 holds stream bits
  // 32-47 in its top 16 bits (manual push after 16 more bits, shift right).
  return static_cast<uint64_t>(word0) | (static_cast<uint64_t>(word1 >> 16) << 32);
}

inline uint8_t ChainByte(uint64_t stream, uint8_t offset) {
  // Reassemble D0..D7 of the chip at `offset`: D_k is stream bit offset+7-k.
  uint8_t v = 0;
  for (uint8_t k = 0; k < 8; ++k) {
    if ((stream >> (offset + 7 - k)) & 1u) v |= static_cast<uint8_t>(1u << k);
  }
  return v;
}

inline uint8_t ReverseBits8(uint8_t v) {
  v = static_cast<uint8_t>(((v & 0xF0) >> 4) | ((v & 0x0F) << 4));
  v = static_cast<uint8_t>(((v & 0xCC) >> 2) | ((v & 0x33) << 2));
  v = static_cast<uint8_t>(((v & 0xAA) >> 1) | ((v & 0x55) << 1));
  return v;
}

inline ChainInputs DecodeChain(uint64_t stream) {
  ChainInputs in;
  const uint8_t u30 = static_cast<uint8_t>(~ChainByte(stream, 0));
  const uint8_t u19 = static_cast<uint8_t>(~ChainByte(stream, 8));
  const uint8_t u18 = static_cast<uint8_t>(~ChainByte(stream, 16));
  const uint8_t u17 = static_cast<uint8_t>(~ChainByte(stream, 24));
  const uint8_t d9 = static_cast<uint8_t>(~ChainByte(stream, 32));
  const uint8_t d17 = static_cast<uint8_t>(~ChainByte(stream, 40));
  // Returns: D7 of each chip is the lowest return number.
  in.returns = static_cast<uint16_t>(ReverseBits8(u19) | (ReverseBits8(u18) << 8));
  // J2: D1-D7 on U17 D1-D7, D8 on U30 D0, memory protect on U17 D0.
  const uint8_t d1 = static_cast<uint8_t>((u17 >> 1) | ((u30 & 0x01) << 7));
  in.dedicated = static_cast<uint32_t>(d1) | (static_cast<uint32_t>(d9) << 8) |
                 (static_cast<uint32_t>(d17) << 16);
  in.mem_protect = (u17 & 0x01) != 0;
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

// Display frames from the Pi and the PIO streams built from them.
//
// The Pi sends one frame per SPI transfer (chip select low for the whole
// frame, then high for at least 20 us before the next one):
//
//   byte 0-1  'S' 'D'
//   byte 2    format: 1 = 4-bit grey, two pixels per byte, left pixel in the
//             high nibble; 2 = RGB565 big endian; 3 = RGB888
//   byte 3    flags (none defined yet, send 0)
//   byte 4-5  width, big endian
//   byte 6-7  height, big endian
//   then width x height pixels, row by row from the top left.
//
// A 128 x 32 frame on the HD panels is shown at twice the size; any frame on
// J5 is reduced to 16 grey levels.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace sam {
namespace dmd {

enum Format : uint8_t { kGray4 = 1, kRgb565 = 2, kRgb888 = 3 };

struct FrameHeader {
  uint8_t format;
  uint8_t flags;
  uint16_t width;
  uint16_t height;
};

constexpr size_t kHeaderBytes = 8;
constexpr uint16_t kMaxWidth = 256;
constexpr uint16_t kMaxHeight = 64;
constexpr size_t kMaxFrameBytes = kHeaderBytes + kMaxWidth * kMaxHeight * 3;

// Checks the header and that `len` holds every pixel.
bool ParseHeader(const uint8_t* frame, size_t len, FrameHeader& h);

// ---- Original 128 x 32 DMD on J5 -----------------------------------------
//
// Each row is shown for 12 slots of 41.55 us, split into 4 bit planes of 1, 2,
// 4 and 5 slots (62.67 Hz, PinMAME's figures). Every grey level 0-15 maps to
// the plane set closest to level * 12 / 15 slots.
constexpr uint16_t kJ5Width = 128;
constexpr uint16_t kJ5Height = 32;
constexpr uint8_t kJ5Planes = 4;
constexpr uint8_t kJ5PlaneSlots[kJ5Planes] = {1, 2, 4, 5};
constexpr uint32_t kJ5SlotNs = 41550;
constexpr size_t kJ5RowPlanes = kJ5Height * kJ5Planes;
constexpr size_t kJ5PixelWords = kJ5RowPlanes * (kJ5Width / 32);
constexpr size_t kJ5StepsPerRowPlane = 4;
constexpr size_t kJ5StepWords = kJ5RowPlanes * kJ5StepsPerRowPlane / 2;
// dmd_j5_ctrl runs at 8 MHz (clock divider 25 at 200 MHz).
constexpr uint32_t kJ5CtrlCycleNs = 125;

// Bit p set = plane p lit for this grey level.
uint8_t J5PlaneMask(uint8_t gray4);

// Pixel stream for dmd_j5_pixels: row-plane by row-plane (row 0 planes 0-3,
// row 1 ...), 4 words each, dot 0 in bit 0 of the first word.
bool BuildJ5Pixels(const FrameHeader& h, const uint8_t* pixels, uint32_t* out);

// One dmd_j5_ctrl step (see dmd_j5.pio).
enum J5Pin : uint8_t { kJ5De = 1, kJ5RowData = 2, kJ5RowClk = 4, kJ5LatchA = 8 };
uint16_t J5Step(uint8_t pins, bool latch_b, bool start_next, bool wait_shifted, uint32_t hold_ns);
// The fixed step list of one frame, two steps per word (first step in the
// low half). Timing inside a slot is provisional (ARCHITECTURE.md Q18).
void BuildJ5Steps(uint32_t* out);
// Word to queue once before the streams start: shifts the first row-plane.
uint32_t J5PrimeWord();

// ---- Two HUB75 panels, 256 x 64 ------------------------------------------
//
// Panel A shows columns 0-127, panel B columns 128-255, both 64 rows high,
// R1/G1/B1 the top half and R2/G2/B2 the bottom half. With only the A and B
// row lines, each of the 4 row addresses carries 8 rows per half: chain
// position q of address a is column q % 128, row a + 4 * (q / 128). This
// order depends on the panel model and is the one place to change once the
// panels are chosen (see README, open items).
constexpr uint16_t kHubWidth = 256;
constexpr uint16_t kHubHeight = 64;
constexpr uint16_t kHubPanelWidth = 128;
constexpr uint8_t kHubAddresses = 4;
constexpr uint8_t kHubRowsPerAddress = kHubHeight / 2 / kHubAddresses;  // 8
constexpr uint16_t kHubChainLength = kHubPanelWidth * kHubRowsPerAddress;
constexpr uint8_t kHubPlanes = 6;
constexpr size_t kHubWordsPerRow = kHubChainLength / 2;  // two clocks per word
constexpr size_t kHubRows = kHubAddresses * kHubPlanes;
constexpr size_t kHubPixelWords = kHubRows * kHubWordsPerRow;

// Grey frames take this colour on the HD panels (classic DMD orange).
struct Rgb {
  uint8_t r, g, b;
};
constexpr Rgb kDefaultTint = {255, 88, 0};

// Data stream for hub75_data: for each address, planes 0-5, each one row of
// kHubWordsPerRow words.
bool BuildHub75Pixels(const FrameHeader& h, const uint8_t* pixels, Rgb tint, uint32_t* out);
// Row stream for hub75_row, same order: address | (on-time << 2), the on-time
// of plane p being base_cycles << p.
void BuildHub75Rows(uint32_t base_cycles, uint32_t* out);

}  // namespace dmd
}  // namespace sam

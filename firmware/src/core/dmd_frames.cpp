// SPDX-License-Identifier: GPL-3.0-or-later
#include "dmd_frames.h"

#include <math.h>
#include <string.h>

namespace sam {
namespace dmd {

namespace {

size_t BytesPerFrame(const FrameHeader& h) {
  const size_t n = static_cast<size_t>(h.width) * h.height;
  switch (h.format) {
    case kGray4: return (n + 1) / 2;
    case kRgb565: return n * 2;
    case kRgb888: return n * 3;
    default: return 0;
  }
}

Rgb PixelAt(const FrameHeader& h, const uint8_t* px, uint16_t x, uint16_t y, Rgb tint) {
  const size_t i = static_cast<size_t>(y) * h.width + x;
  switch (h.format) {
    case kGray4: {
      const uint8_t b = px[i / 2];
      const uint8_t g = (i & 1u) ? (b & 0x0F) : (b >> 4);
      return {static_cast<uint8_t>(tint.r * g / 15), static_cast<uint8_t>(tint.g * g / 15),
              static_cast<uint8_t>(tint.b * g / 15)};
    }
    case kRgb565: {
      const uint16_t v = static_cast<uint16_t>((px[i * 2] << 8) | px[i * 2 + 1]);
      const uint8_t r = static_cast<uint8_t>((v >> 11) & 0x1F);
      const uint8_t g = static_cast<uint8_t>((v >> 5) & 0x3F);
      const uint8_t b = static_cast<uint8_t>(v & 0x1F);
      return {static_cast<uint8_t>((r << 3) | (r >> 2)), static_cast<uint8_t>((g << 2) | (g >> 4)),
              static_cast<uint8_t>((b << 3) | (b >> 2))};
    }
    default:
      return {px[i * 3], px[i * 3 + 1], px[i * 3 + 2]};
  }
}

uint8_t Gray4At(const FrameHeader& h, const uint8_t* px, uint16_t x, uint16_t y) {
  if (h.format == kGray4) {
    const size_t i = static_cast<size_t>(y) * h.width + x;
    const uint8_t b = px[i / 2];
    return (i & 1u) ? (b & 0x0F) : (b >> 4);
  }
  const Rgb c = PixelAt(h, px, x, y, kDefaultTint);
  const uint32_t luma = (c.r * 77u + c.g * 150u + c.b * 29u) >> 8;
  return static_cast<uint8_t>(luma >> 4);
}

struct Gamma6 {
  uint8_t v[256];
  Gamma6() {
    for (int i = 0; i < 256; ++i) v[i] = static_cast<uint8_t>(pow(i / 255.0, 2.2) * 63.0 + 0.5);
  }
};
const Gamma6 kGamma;

}  // namespace

bool ParseHeader(const uint8_t* frame, size_t len, FrameHeader& h) {
  if (len < kHeaderBytes || frame[0] != 'S' || frame[1] != 'D') return false;
  h.format = frame[2];
  h.flags = frame[3];
  h.width = static_cast<uint16_t>((frame[4] << 8) | frame[5]);
  h.height = static_cast<uint16_t>((frame[6] << 8) | frame[7]);
  if (h.width == 0 || h.height == 0 || h.width > kMaxWidth || h.height > kMaxHeight) return false;
  const size_t need = BytesPerFrame(h);
  return need != 0 && len >= kHeaderBytes + need;
}

uint8_t J5PlaneMask(uint8_t gray4) {
  if (gray4 > 15) gray4 = 15;
  const uint8_t target = static_cast<uint8_t>((gray4 * 12 + 7) / 15);
  uint8_t best = 0;
  uint8_t best_err = 0xFF;
  for (uint8_t m = 0; m < 16; ++m) {
    uint8_t slots = 0;
    for (uint8_t p = 0; p < kJ5Planes; ++p) {
      if ((m >> p) & 1u) slots = static_cast<uint8_t>(slots + kJ5PlaneSlots[p]);
    }
    const uint8_t err = static_cast<uint8_t>(slots > target ? slots - target : target - slots);
    if (err < best_err) {
      best = m;
      best_err = err;
    }
  }
  return best;
}

bool BuildJ5Pixels(const FrameHeader& h, const uint8_t* pixels, uint32_t* out) {
  uint8_t masks[16];
  for (uint8_t g = 0; g < 16; ++g) masks[g] = J5PlaneMask(g);
  memset(out, 0, kJ5PixelWords * sizeof(uint32_t));
  for (uint16_t y = 0; y < kJ5Height; ++y) {
    const uint16_t sy = static_cast<uint16_t>(y * h.height / kJ5Height);
    for (uint16_t x = 0; x < kJ5Width; ++x) {
      const uint16_t sx = static_cast<uint16_t>(x * h.width / kJ5Width);
      const uint8_t m = masks[Gray4At(h, pixels, sx, sy)];
      for (uint8_t p = 0; p < kJ5Planes; ++p) {
        if ((m >> p) & 1u) {
          out[(y * kJ5Planes + p) * (kJ5Width / 32) + x / 32] |= 1u << (x % 32);
        }
      }
    }
  }
  return true;
}

namespace {
// About 11 cycles of decoding per step, then 4 cycles per hold unit + 4.
constexpr uint32_t kJ5StepOverheadCycles = 15;
uint32_t J5StepNs(uint16_t step) {
  return (kJ5StepOverheadCycles + 4u * (step >> 7)) * kJ5CtrlCycleNs;
}
}  // namespace

uint16_t J5Step(uint8_t pins, bool latch_b, bool start_next, bool wait_shifted, uint32_t hold_ns) {
  constexpr uint32_t kOverheadCycles = kJ5StepOverheadCycles;
  const uint32_t cycles = hold_ns / kJ5CtrlCycleNs;
  uint32_t units = cycles > kOverheadCycles ? (cycles - kOverheadCycles) / 4 : 0;
  if (units > 511) units = 511;
  return static_cast<uint16_t>((pins & 0x0F) | (latch_b ? 0x10 : 0) | (start_next ? 0x20 : 0) |
                               (wait_shifted ? 0x40 : 0) | (units << 7));
}

void BuildJ5Steps(uint32_t* out) {
  // Per row-plane, with the plane's dots already shifted:
  //   1. display off, wait until the dots are in, 1 us
  //   2. column latches high (and the row clock on a new row), 0.5 us
  //   3. latches and row clock low, 0.5 us
  //   4. display on for the plane's slots; start shifting the next row-plane.
  // ROWDATA is high for row 0 only, so the row shift register walks one bit.
  constexpr uint32_t kOffNs = 1000;
  constexpr uint32_t kLatchNs = 500;
  size_t n = 0;
  uint16_t steps[kJ5RowPlanes * kJ5StepsPerRowPlane];
  for (uint16_t row = 0; row < kJ5Height; ++row) {
    for (uint8_t p = 0; p < kJ5Planes; ++p) {
      const uint8_t rowdata = row == 0 ? kJ5RowData : 0;
      const uint8_t rowclk = p == 0 ? kJ5RowClk : 0;
      const uint16_t off = J5Step(rowdata, false, false, true, kOffNs);
      const uint16_t latch = J5Step(rowdata | rowclk | kJ5LatchA, true, false, false, kLatchNs);
      const uint16_t settle = J5Step(rowdata, false, false, false, kLatchNs);
      // The real length of the first three steps comes off the lit time, so
      // a row-plane lasts exactly its slots.
      const uint32_t on_ns = kJ5PlaneSlots[p] * kJ5SlotNs - J5StepNs(off) - J5StepNs(latch) -
                             J5StepNs(settle);
      steps[n++] = off;
      steps[n++] = latch;
      steps[n++] = settle;
      steps[n++] = J5Step(kJ5De | rowdata, false, true, false, on_ns);
    }
  }
  for (size_t i = 0; i < kJ5StepWords; ++i) {
    out[i] = static_cast<uint32_t>(steps[2 * i]) | (static_cast<uint32_t>(steps[2 * i + 1]) << 16);
  }
}

uint32_t J5PrimeWord() {
  return static_cast<uint32_t>(J5Step(0, false, true, false, 0)) |
         (static_cast<uint32_t>(J5Step(0, false, false, false, 0)) << 16);
}

bool BuildHub75Pixels(const FrameHeader& h, const uint8_t* pixels, Rgb tint, uint32_t* out) {
  for (uint8_t a = 0; a < kHubAddresses; ++a) {
    uint32_t* blocks = out + static_cast<size_t>(a) * kHubPlanes * kHubWordsPerRow;
    for (uint16_t q = 0; q < kHubChainLength; ++q) {
      const uint16_t col = q % kHubPanelWidth;
      const uint16_t top = static_cast<uint16_t>(a + kHubAddresses * (q / kHubPanelWidth));
      // The 4 pixels clocked out together: panel A top/bottom, panel B top/bottom.
      const uint16_t xs[2] = {col, static_cast<uint16_t>(col + kHubPanelWidth)};
      const uint16_t ys[2] = {top, static_cast<uint16_t>(top + kHubHeight / 2)};
      uint8_t c[12];
      for (uint8_t panel = 0; panel < 2; ++panel) {
        for (uint8_t half = 0; half < 2; ++half) {
          const uint16_t sx = static_cast<uint16_t>(xs[panel] * h.width / kHubWidth);
          const uint16_t sy = static_cast<uint16_t>(ys[half] * h.height / kHubHeight);
          const Rgb px = PixelAt(h, pixels, sx, sy, tint);
          uint8_t* dst = &c[panel * 6 + half * 3];
          dst[0] = kGamma.v[px.r];
          dst[1] = kGamma.v[px.g];
          dst[2] = kGamma.v[px.b];
        }
      }
      for (uint8_t p = 0; p < kHubPlanes; ++p) {
        uint32_t bits = 0;
        for (uint8_t k = 0; k < 12; ++k) bits |= static_cast<uint32_t>((c[k] >> p) & 1u) << k;
        uint32_t& w = blocks[p * kHubWordsPerRow + q / 2];
        if (q & 1u) {
          w = (w & 0x0000FFFFu) | (bits << 16);
        } else {
          w = (w & 0xFFFF0000u) | bits;
        }
      }
    }
  }
  return true;
}

void BuildHub75Rows(uint32_t base_cycles, uint32_t* out) {
  size_t n = 0;
  for (uint8_t a = 0; a < kHubAddresses; ++a) {
    for (uint8_t p = 0; p < kHubPlanes; ++p) {
      uint32_t on = base_cycles << p;
      if (on > 0x3FFFFFFFu) on = 0x3FFFFFFFu;
      out[n++] = (a & 3u) | (on << 2);
    }
  }
}

}  // namespace dmd
}  // namespace sam

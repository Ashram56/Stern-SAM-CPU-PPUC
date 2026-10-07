// Display path on core0: frames from the Pi (PIO1 SM1 + DMA), converted to
// PIO2 streams for either the original DMD on J5 or the two HUB75 panels.
// Only one of the two outputs runs at a time.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stdint.h>

namespace sam {

void DisplayInit();
// kDisplayNone / kDisplayJ5 / kDisplayHub75 (devices.h). Stops the current
// output and starts the new one.
void DisplaySetMode(uint8_t mode);
uint8_t DisplayMode();
// Converts a received frame when the back buffer is free. Call often.
void DisplayService();

struct DisplayStats {
  uint32_t frames_shown, frames_bad, frames_dropped;
};
DisplayStats GetDisplayStats();

}  // namespace sam

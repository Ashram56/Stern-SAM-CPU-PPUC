// core1: the SAM IO bus, the switch chain, coils and lamps.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include "../core/devices.h"
#include "../core/shared.h"

namespace sam {

// Called on core0 before core1 starts: claims PIO0 SM0 (bus) and PIO1 SM0
// (switch chain) and parks the IO board in reset with its buffers off.
void RealtimeInit(Devices* devices, Shared* shared);

// core1 entry point. Never returns.
void RealtimeMain();

}  // namespace sam

// PPUC link to the Pi on UART0 (GPIO44 TX, GPIO45 RX), point to point.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "../core/ppuc_session.h"

namespace sam {

class UartLink : public LinkWriter {
 public:
  void Init(uint32_t baud);
  // Bytes received since the last call, up to `max`.
  size_t Read(uint8_t* out, size_t max);
  void Write(const uint8_t* data, size_t len) override;
  uint32_t Overruns() const;
};

}  // namespace sam

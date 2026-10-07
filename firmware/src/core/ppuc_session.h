// PPUC v2 protocol, board side, for one RP2354B that stands in for several
// PPUC boards ("virtual boards").
//
// Frame format and session rules: PPUC ppuc/docs/V2_PROTOCOL.md and
// io-boards src/PPUCProtocolV2.h (vendored unchanged in ../ppuc/). The
// behaviour mirrors io-boards src/EventDispatcher/EventDispatcher.cpp:
// Restart/Setup/Mapping/Config, snapshot-driven OutputState, the switch token
// chain with a 32-deep report ring, and the admin version/stats queries.
//
// What differs, because the link is point to point (UART or USB) and not a
// shared RS485 pair:
//   - the firmware answers for every board id in `board_mask`. When a reply
//     for one of its ids names another of its ids as the next board, it sends
//     that reply too, exactly as the next board on the RS485 bus would;
//   - no DE line and no reply delay;
//   - firmware update over the link is refused (kUpdateUnsupported). Flash
//     with picotool over USB or with SWD from the Pi.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "../ppuc/PPUCProtocolV2.h"
#include "devices.h"

namespace sam {

// Board type reported in the version report. Not assigned upstream yet; the
// value must be agreed with PPUC before release.
constexpr uint8_t kBoardTypeSamCpu = 0x05;

constexpr uint8_t kFirmwareMajor = 0;
constexpr uint8_t kFirmwareMinor = 1;
constexpr uint8_t kFirmwarePatch = 0;

class LinkWriter {
 public:
  virtual void Write(const uint8_t* data, size_t len) = 0;
};

class SessionListener {
 public:
  // kFrameRestart (soft) or kFrameReset (hard): outputs off, devices cleared.
  virtual void OnRestart(bool hard_reset) = 0;
  // A valid OutputState arrived; the session's output bitmaps are updated.
  virtual void OnOutputs() = 0;
};

class PpucSession {
 public:
  static constexpr uint8_t kRingSize = 32;

  PpucSession(Devices& devices, LinkWriter& tx, SessionListener& listener);

  void SetBoardMask(uint8_t mask) { board_mask_ = mask; }
  uint8_t BoardMask() const { return board_mask_; }
  void SetBuildId(uint32_t id) { build_id_ = id; }

  // Bytes from the link, in order.
  void Feed(const uint8_t* data, size_t len);

  // Local switch states by port (bitmap of kNumSwitchPorts bits). Call when
  // the scanner's change count moves; queues a report snapshot per changed
  // virtual board, like io-boards does per switch event.
  void UpdateLocalSwitches(const uint32_t* port_bitmap);

  // Session state for the output side.
  bool Running() const { return config_valid_ && mapping_complete_; }
  // Host's desired state, translated to this board's ports. Valid after
  // OnOutputs().
  const uint8_t* CoilsByPort() const { return coils_by_port_; }
  const uint8_t* LampsByPort() const { return lamps_by_port_; }
  uint8_t GiLevel(uint8_t string) const { return gi_[string]; }
  bool GameOn() const { return game_on_; }
  // Switch state by PPUC number for numbers this board does not own,
  // as reported by other boards (or the host for virtual boards).
  bool RemoteSwitch(uint16_t number) const;
  // Switch reports waiting for a token (drives the Pi's IRQ line).
  bool HasQueuedReports() const;

  struct Stats {
    uint32_t rx_frames, rx_crc_fail, raw_bytes, tx_frames, selected;
    uint32_t version_queries, version_replies, resyncs;
  };
  const Stats& GetStats() const { return stats_; }

 private:
  enum ParseState : uint8_t { kHunt, kHeader, kAdminPrefix, kChunkHead, kBody };

  void ResetParser(bool resynced);
  bool PayloadBytesFor(uint8_t type, size_t& out) const;
  bool AdminBodyBytes(uint8_t command, size_t& out) const;
  void HandleFrame(const uint8_t* frame, size_t payload_bytes);
  void HandleAdmin(const uint8_t* payload);
  void ClearSession();
  void ResetSession(uint8_t epoch, const ppuc::v2::RuntimeConfig& cfg);
  void RebuildPortIndex();
  void TranslateOutputs(const uint8_t* coils, const uint8_t* lamps, const uint8_t* gi);
  void ApplyRemoteSwitches(const uint8_t* bitmap);
  void AnswerToken(uint8_t board);
  void SendSwitchReply(uint8_t board, uint8_t next);
  void SendConfigAck(uint8_t board, uint8_t topic, uint8_t index, uint8_t key, uint8_t status);
  uint8_t StatusFlags() const;
  bool Ours(uint8_t board) const { return board < 8 && ((board_mask_ >> board) & 1u); }
  int16_t FindIndex(const uint16_t* table, uint16_t count, uint16_t number) const;

  Devices& d_;
  LinkWriter& tx_;
  SessionListener& listener_;
  ConfigApplier applier_;
  uint8_t board_mask_ = 0x07;
  uint32_t build_id_ = 0;

  // Parser.
  ParseState ps_ = kHunt;
  uint8_t rx_[ppuc::v2::kMaxFrameBytes];
  size_t rx_len_ = 0;
  size_t rx_need_ = 0;
  size_t payload_bytes_ = 0;

  // Session.
  ppuc::v2::RuntimeConfig cfg_;
  bool config_valid_ = false;
  bool mapping_complete_ = false;
  uint16_t expected_mappings_ = 0;
  uint16_t received_mappings_ = 0;
  uint8_t epoch_ = 0;
  uint8_t tx_seq_ = 0;
  uint8_t last_host_seq_ = 0;       // last OutputState / SwitchRefresh sequence
  uint8_t last_host_frame_seq_ = 0;
  bool last_host_frame_seq_valid_ = false;
  bool seq_gap_ = false;
  bool parser_resynced_ = false;
  bool force_refresh_ = false;
  uint8_t no_change_replies_ = 0;

  uint16_t coil_index_to_number_[ppuc::v2::kMaxCoilBits];
  uint16_t lamp_index_to_number_[ppuc::v2::kMaxLampBits];
  uint16_t switch_index_to_number_[ppuc::v2::kMaxSwitchBits];
  // Port -> bitmap index, -1 when the device is not in the mapping.
  int16_t coil_port_index_[kNumCoilPorts];
  int16_t lamp_port_index_[kNumLampPorts];
  int16_t switch_port_index_[kNumSwitchPorts];
  int16_t game_on_index_ = -1;
  bool port_index_dirty_ = true;

  uint8_t coils_by_port_[(kNumCoilPorts + 7) / 8] = {};
  uint8_t lamps_by_port_[(kNumLampPorts + 7) / 8] = {};
  uint8_t gi_[ppuc::v2::kGiStrings] = {};
  bool game_on_ = false;

  // Switch reporting (bitmaps indexed by mapping index).
  uint8_t remote_[ppuc::v2::kMaxSwitchBytes] = {};
  uint8_t local_[ppuc::v2::kMaxSwitchBytes] = {};
  uint8_t local_owned_[ppuc::v2::kMaxSwitchBytes] = {};
  struct Ring {
    uint8_t snap[kRingSize][ppuc::v2::kMaxSwitchBytes];
    uint8_t head, tail;
    bool overflow;
  };
  Ring ring_[8];
  uint32_t last_port_bitmap_[(kNumSwitchPorts + 31) / 32] = {};

  Stats stats_ = {};
  uint8_t tx_buf_[ppuc::v2::kMaxFrameBytes];
};

}  // namespace sam

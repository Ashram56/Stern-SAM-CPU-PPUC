// SPDX-License-Identifier: GPL-3.0-or-later
#include "ppuc_session.h"

#include <string.h>

namespace sam {

using namespace ppuc::v2;

namespace {
constexpr uint8_t kMaxNoChangeReplies = 100;  // io-boards kMaxConsecutiveSwitchNoChangeReplies

bool Bit(const uint8_t* bitmap, uint16_t i) { return (bitmap[i / 8] >> (i % 8)) & 1u; }
bool PortBit(const uint32_t* bitmap, uint16_t port) { return (bitmap[port / 32] >> (port % 32)) & 1u; }
}  // namespace

PpucSession::PpucSession(Devices& devices, LinkWriter& tx, SessionListener& listener)
    : d_(devices), tx_(tx), listener_(listener), applier_(devices) {
  ClearSession();
}

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

void PpucSession::ResetParser(bool resynced) {
  ps_ = kHunt;
  rx_len_ = 0;
  rx_need_ = 0;
  if (resynced) {
    parser_resynced_ = true;
    stats_.resyncs++;
  }
}

bool PpucSession::PayloadBytesFor(uint8_t type, size_t& out) const {
  switch (type) {
    case kFrameSetup: out = kSetupPayloadBytes; return true;
    case kFrameMapping: out = kMappingPayloadBytes; return true;
    case kFrameConfig: out = kConfigPayloadBytes; return true;
    case kFrameConfigAck: out = kConfigAckPayloadBytes; return true;
    case kFrameTrigger: out = kTriggerPayloadBytes; return true;
    case kFrameSwitchNoChange: out = kSwitchStatusBytes; return true;
    case kFrameReset:
    case kFrameRestart:
    case kFrameSwitchRefresh:
    case kFrameHeartbeat:
    case kFrameError:
      out = 0;
      return true;
    case kFrameOutputState:
      if (!config_valid_) return false;
      out = OutputPayloadBytes(cfg_);
      return true;
    case kFrameSwitchState:
      if (!config_valid_) return false;
      out = SwitchPayloadBytes(cfg_);
      return true;
    default:
      return false;
  }
}

bool PpucSession::AdminBodyBytes(uint8_t command, size_t& out) const {
  switch (command) {
    case kAdminVersionQuery:
    case kAdminVersionReport: out = kAdminDataBytes; return true;
    case kAdminUpdateBegin: out = kUpdateBeginBodyBytes; return true;
    case kAdminUpdateBeginAck:
    case kAdminUpdateChunkAck:
    case kAdminUpdateResult: out = kUpdateAckBodyBytes; return true;
    case kAdminUpdateCommit:
    case kAdminStatsQuery: out = 0; return true;
    case kAdminStatsReport: out = kStatsBodyBytes; return true;
    default: return false;  // no derivable length: resync rather than guess
  }
}

void PpucSession::Feed(const uint8_t* data, size_t len) {
  for (size_t i = 0; i < len; ++i) {
    const uint8_t b = data[i];
    stats_.raw_bytes++;
    if (ps_ == kHunt) {
      if (b != kSyncByte) continue;
      rx_[0] = b;
      rx_len_ = 1;
      rx_need_ = kHeaderBytes;
      ps_ = kHeader;
      continue;
    }
    rx_[rx_len_++] = b;

    // Advance as far as the buffered bytes allow. A failure drops the leading
    // sync byte and hunts for the next one inside what is already buffered.
    while (ps_ != kHunt && rx_len_ >= rx_need_) {
      bool ok = true;
      switch (ps_) {
        case kHeader: {
          const uint8_t type = ExtractType(rx_[1]);
          size_t n = 0;
          if (type == kFrameAdmin) {
            ps_ = kAdminPrefix;
            rx_need_ = kHeaderBytes + kAdminPrefixBytes;
          } else if (PayloadBytesFor(type, n)) {
            payload_bytes_ = n;
            rx_need_ = kHeaderBytes + n + kCrcBytes;
            ps_ = kBody;
          } else {
            ok = false;
          }
          break;
        }
        case kAdminPrefix: {
          const uint8_t command = rx_[kHeaderBytes];
          size_t body = 0;
          if (command == kAdminUpdateChunk) {
            ps_ = kChunkHead;
            rx_need_ = kHeaderBytes + kAdminPrefixBytes + kUpdateChunkHeadBytes;
          } else if (AdminBodyBytes(command, body)) {
            payload_bytes_ = kAdminPrefixBytes + body;
            rx_need_ = kHeaderBytes + payload_bytes_ + kCrcBytes;
            ps_ = kBody;
          } else {
            ok = false;
          }
          break;
        }
        case kChunkHead: {
          const uint16_t length = ReadU16(&rx_[kHeaderBytes + kAdminPrefixBytes + 4]);
          if (length > kAdminChunkBytes) {
            ok = false;
            break;
          }
          payload_bytes_ = kAdminPrefixBytes + kUpdateChunkHeadBytes + length;
          rx_need_ = kHeaderBytes + payload_bytes_ + kCrcBytes;
          ps_ = kBody;
          break;
        }
        case kBody:
          if (VerifyCrc(rx_, rx_need_)) {
            stats_.rx_frames++;
            ps_ = kHunt;
            rx_len_ = 0;
            HandleFrame(rx_, payload_bytes_);
          } else {
            stats_.rx_crc_fail++;
            ok = false;
          }
          break;
        case kHunt:
          break;
      }
      if (!ok) {
        size_t s = 1;
        while (s < rx_len_ && rx_[s] != kSyncByte) ++s;
        const size_t keep = rx_len_ - s;
        ResetParser(true);
        if (keep > 0) {
          memmove(rx_, rx_ + s, keep);
          rx_len_ = keep;
          rx_need_ = kHeaderBytes;
          ps_ = kHeader;
        }
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

void PpucSession::ClearSession() {
  cfg_ = RuntimeConfig();
  config_valid_ = false;
  mapping_complete_ = false;
  expected_mappings_ = received_mappings_ = 0;
  last_host_seq_ = last_host_frame_seq_ = 0;
  last_host_frame_seq_valid_ = false;
  seq_gap_ = parser_resynced_ = force_refresh_ = false;
  no_change_replies_ = 0;
  for (uint16_t i = 0; i < kMaxCoilBits; ++i) coil_index_to_number_[i] = i;
  for (uint16_t i = 0; i < kMaxLampBits; ++i) lamp_index_to_number_[i] = i;
  for (uint16_t i = 0; i < kMaxSwitchBits; ++i) switch_index_to_number_[i] = i;
  memset(coils_by_port_, 0, sizeof(coils_by_port_));
  memset(lamps_by_port_, 0, sizeof(lamps_by_port_));
  memset(gi_, 0, sizeof(gi_));
  game_on_ = false;
  memset(remote_, 0, sizeof(remote_));
  memset(local_, 0, sizeof(local_));
  memset(local_owned_, 0, sizeof(local_owned_));
  memset(ring_, 0, sizeof(ring_));
  DevicesReset(d_);
  applier_.Reset();
  port_index_dirty_ = true;
}

void PpucSession::ResetSession(uint8_t epoch, const RuntimeConfig& cfg) {
  epoch_ = epoch;
  cfg_ = cfg;
  config_valid_ = true;
  expected_mappings_ = static_cast<uint16_t>(cfg.coilBits + cfg.lampBits + cfg.switchBits);
  received_mappings_ = 0;
  mapping_complete_ = expected_mappings_ == 0;
  last_host_seq_ = last_host_frame_seq_ = 0;
  last_host_frame_seq_valid_ = false;
  seq_gap_ = parser_resynced_ = false;
  no_change_replies_ = 0;
  for (uint16_t i = 0; i < kMaxCoilBits; ++i) coil_index_to_number_[i] = i;
  for (uint16_t i = 0; i < kMaxLampBits; ++i) lamp_index_to_number_[i] = i;
  for (uint16_t i = 0; i < kMaxSwitchBits; ++i) switch_index_to_number_[i] = i;
  port_index_dirty_ = true;
}

int16_t PpucSession::FindIndex(const uint16_t* table, uint16_t count, uint16_t number) const {
  for (uint16_t i = 0; i < count; ++i) {
    if (table[i] == number) return static_cast<int16_t>(i);
  }
  return -1;
}

void PpucSession::RebuildPortIndex() {
  for (uint16_t p = 0; p < kNumCoilPorts; ++p) {
    coil_port_index_[p] =
        d_.coil[p].used ? FindIndex(coil_index_to_number_, cfg_.coilBits, d_.coil[p].number) : -1;
  }
  for (uint16_t p = 0; p < kNumLampPorts; ++p) {
    lamp_port_index_[p] =
        d_.lamp[p].used ? FindIndex(lamp_index_to_number_, cfg_.lampBits, d_.lamp[p].number) : -1;
  }
  memset(local_owned_, 0, sizeof(local_owned_));
  for (uint16_t p = 0; p < kNumSwitchPorts; ++p) {
    switch_port_index_[p] =
        d_.sw[p].used ? FindIndex(switch_index_to_number_, cfg_.switchBits, d_.sw[p].number) : -1;
    if (switch_port_index_[p] >= 0) SetBitmapBit(local_owned_, switch_port_index_[p], true);
  }
  game_on_index_ = d_.high_power.game_on_solenoid
                       ? FindIndex(coil_index_to_number_, cfg_.coilBits, d_.high_power.game_on_solenoid)
                       : -1;
  port_index_dirty_ = false;
}

void PpucSession::TranslateOutputs(const uint8_t* coils, const uint8_t* lamps, const uint8_t* gi) {
  if (port_index_dirty_) RebuildPortIndex();
  memset(coils_by_port_, 0, sizeof(coils_by_port_));
  memset(lamps_by_port_, 0, sizeof(lamps_by_port_));
  for (uint16_t p = 0; p < kNumCoilPorts; ++p) {
    const int16_t i = coil_port_index_[p];
    if (i >= 0 && Bit(coils, static_cast<uint16_t>(i))) SetBitmapBit(coils_by_port_, p, true);
  }
  for (uint16_t p = 0; p < kNumLampPorts; ++p) {
    const int16_t i = lamp_port_index_[p];
    if (i >= 0 && Bit(lamps, static_cast<uint16_t>(i))) SetBitmapBit(lamps_by_port_, p, true);
  }
  for (uint8_t s = 0; s < kGiStrings; ++s) gi_[s] = ClampGiLevel(GetPackedNibble(gi, s));
  game_on_ = game_on_index_ >= 0 && Bit(coils, static_cast<uint16_t>(game_on_index_));
}

void PpucSession::ApplyRemoteSwitches(const uint8_t* bitmap) {
  const size_t n = BitsToBytes(cfg_.switchBits);
  for (size_t i = 0; i < n; ++i) remote_[i] = static_cast<uint8_t>(bitmap[i] & ~local_owned_[i]);
}

bool PpucSession::RemoteSwitch(uint16_t number) const {
  if (!config_valid_) return false;
  const int16_t i = FindIndex(switch_index_to_number_, cfg_.switchBits, number);
  return i >= 0 && Bit(remote_, static_cast<uint16_t>(i));
}

bool PpucSession::HasQueuedReports() const {
  for (uint8_t b = 0; b < 8; ++b) {
    if (Ours(b) && ring_[b].head != ring_[b].tail) return true;
  }
  return false;
}

void PpucSession::UpdateLocalSwitches(const uint32_t* port_bitmap) {
  uint8_t changed_boards = 0;
  for (uint16_t p = 1; p < kNumSwitchPorts; ++p) {
    if (PortBit(port_bitmap, p) != PortBit(last_port_bitmap_, p) && d_.sw[p].used) {
      changed_boards |= Ours(d_.sw[p].board) ? static_cast<uint8_t>(1u << d_.sw[p].board) : board_mask_;
    }
  }
  memcpy(last_port_bitmap_, port_bitmap, sizeof(last_port_bitmap_));
  if (!mapping_complete_ || !changed_boards) return;
  if (port_index_dirty_) RebuildPortIndex();

  memset(local_, 0, sizeof(local_));
  for (uint16_t p = 1; p < kNumSwitchPorts; ++p) {
    const int16_t i = switch_port_index_[p];
    if (i >= 0 && PortBit(port_bitmap, p)) SetBitmapBit(local_, static_cast<uint16_t>(i), true);
  }
  for (uint8_t b = 0; b < 8; ++b) {
    if (!((changed_boards >> b) & 1u)) continue;
    Ring& r = ring_[b];
    const uint8_t next = static_cast<uint8_t>((r.head + 1) % kRingSize);
    if (next == r.tail) {
      r.overflow = true;
      r.tail = static_cast<uint8_t>((r.tail + 1) % kRingSize);
    }
    memcpy(r.snap[r.head], local_, sizeof(local_));
    r.head = next;
  }
}

uint8_t PpucSession::StatusFlags() const {
  uint8_t f = 0;
  if (config_valid_ && mapping_complete_) f |= kStatusInSync;
  if (!config_valid_) f |= kStatusNeedsSetup;
  if (config_valid_ && !mapping_complete_) f |= kStatusMappingIncomplete;
  if (seq_gap_) f |= kStatusSequenceGap;
  if (parser_resynced_) f |= kStatusParserResynced;
  return f;
}

void PpucSession::SendSwitchReply(uint8_t board, uint8_t next) {
  Ring& r = ring_[board];
  const bool queued = r.head != r.tail;
  const bool force = force_refresh_ || no_change_replies_ >= kMaxNoChangeReplies;
  uint8_t flags = StatusFlags();
  if (r.overflow) flags |= kStatusSwitchOverflow;
  size_t len;
  if (queued || force) {
    const size_t n = BitsToBytes(cfg_.switchBits);
    const uint8_t* src = queued ? r.snap[r.tail] : local_;
    uint8_t bitmap[kMaxSwitchBytes];
    for (size_t i = 0; i < n; ++i) {
      bitmap[i] = static_cast<uint8_t>((remote_[i] & ~local_owned_[i]) | (src[i] & local_owned_[i]));
    }
    len = BuildSwitchReplyFrame(tx_buf_, true, next, tx_seq_++, epoch_, epoch_, last_host_seq_,
                                flags, bitmap, n);
    if (queued) r.tail = static_cast<uint8_t>((r.tail + 1) % kRingSize);
    no_change_replies_ = 0;
    seq_gap_ = parser_resynced_ = false;
    r.overflow = false;
  } else {
    len = BuildSwitchReplyFrame(tx_buf_, false, next, tx_seq_++, epoch_, epoch_, last_host_seq_,
                                flags, nullptr, 0);
    no_change_replies_++;
  }
  tx_.Write(tx_buf_, len);
  stats_.tx_frames++;
}

void PpucSession::AnswerToken(uint8_t board) {
  // Follow the chain through every id this firmware answers for, as the next
  // board on a shared bus would on hearing the previous reply.
  for (uint8_t hops = 0; hops < 8 && Ours(board); ++hops) {
    stats_.selected++;
    const uint8_t next = d_.next_board[board];
    SendSwitchReply(board, next);
    if (next == board) break;
    board = next;
  }
  force_refresh_ = false;
}

void PpucSession::SendConfigAck(uint8_t board, uint8_t topic, uint8_t index, uint8_t key,
                                uint8_t status) {
  const size_t len = BuildConfigAckFrame(tx_buf_, kNoBoard, tx_seq_++, epoch_, board, topic,
                                         index, key, status);
  tx_.Write(tx_buf_, len);
  stats_.tx_frames++;
}

void PpucSession::HandleAdmin(const uint8_t* p) {
  const uint8_t command = p[0];
  const uint8_t target = p[1];
  if (!Ours(target)) return;
  size_t len = 0;
  switch (command) {
    case kAdminVersionQuery:
      stats_.version_queries++;
      len = BuildVersionReportFrame(tx_buf_, target, tx_seq_++, epoch_, kFirmwareMajor,
                                    kFirmwareMinor, kFirmwarePatch,
                                    kAdminCapabilityVersionReport, kBoardTypeSamCpu, build_id_);
      tx_.Write(tx_buf_, len);
      stats_.tx_frames++;
      stats_.version_replies++;
      return;
    case kAdminStatsQuery:
      len = BuildStatsReportFrame(tx_buf_, target, tx_seq_++, epoch_, stats_.rx_frames,
                                  stats_.rx_crc_fail, stats_.raw_bytes, stats_.tx_frames,
                                  stats_.selected, stats_.version_queries,
                                  stats_.version_replies, 0);
      tx_.Write(tx_buf_, len);
      return;
    case kAdminUpdateBegin:
      len = BuildUpdateAckFrame(tx_buf_, kAdminUpdateBeginAck, target, tx_seq_++, epoch_,
                                kUpdateUnsupported, 0);
      break;
    case kAdminUpdateChunk:
      len = BuildUpdateAckFrame(tx_buf_, kAdminUpdateChunkAck, target, tx_seq_++, epoch_,
                                kUpdateUnsupported, ReadU32(&p[kAdminPrefixBytes]));
      break;
    case kAdminUpdateCommit:
      len = BuildUpdateAckFrame(tx_buf_, kAdminUpdateResult, target, tx_seq_++, epoch_,
                                kUpdateUnsupported, 0);
      break;
    default:
      return;  // reports from other boards
  }
  tx_.Write(tx_buf_, len);
  stats_.tx_frames++;
}

void PpucSession::HandleFrame(const uint8_t* frame, size_t payload_bytes) {
  (void)payload_bytes;
  const uint8_t type = ExtractType(frame[1]);
  const uint8_t seq = frame[3];
  const uint8_t epoch = frame[4];
  const uint8_t* p = frame + kHeaderBytes;

  const bool host_originated =
      type == kFrameSetup || type == kFrameMapping || type == kFrameConfig ||
      type == kFrameTrigger || type == kFrameOutputState || type == kFrameSwitchRefresh ||
      type == kFrameHeartbeat || type == kFrameError || type == kFrameReset ||
      type == kFrameRestart;
  const bool host_poll = type == kFrameOutputState || type == kFrameSwitchRefresh;
  auto note_host_seq = [&]() {
    if (last_host_frame_seq_valid_ && static_cast<uint8_t>(last_host_frame_seq_ + 1) != seq) {
      seq_gap_ = true;
    }
    last_host_frame_seq_ = seq;
    last_host_frame_seq_valid_ = true;
    if (host_poll) last_host_seq_ = seq;
  };

  if (type == kFrameSetup) {
    RuntimeConfig cfg;
    ReadSetupPayload(p, cfg);
    if (IsValidRuntimeConfig(cfg)) ResetSession(epoch, cfg);
    return;
  }
  if (type == kFrameReset || type == kFrameRestart) {
    ClearSession();
    note_host_seq();
    listener_.OnRestart(type == kFrameReset);
    return;
  }
  // Administration is answered before a session exists (V2_PROTOCOL.md 7).
  if (type == kFrameAdmin) {
    HandleAdmin(p);
    return;
  }
  if (host_originated && epoch != epoch_) {
    seq_gap_ = true;
    if (type != kFrameConfig) return;  // config is session-independent
  }
  if (host_originated) note_host_seq();

  switch (type) {
    case kFrameMapping: {
      if (!config_valid_) return;
      uint8_t domain;
      uint16_t index, number;
      ReadMappingPayload(p, domain, index, number);
      if (domain == kDomainCoil && index < cfg_.coilBits) {
        coil_index_to_number_[index] = number;
      } else if (domain == kDomainLamp && index < cfg_.lampBits) {
        lamp_index_to_number_[index] = number;
      } else if (domain == kDomainSwitch && index < cfg_.switchBits) {
        switch_index_to_number_[index] = number;
      }
      if (received_mappings_ < expected_mappings_) received_mappings_++;
      port_index_dirty_ = true;
      const bool was_complete = mapping_complete_;
      mapping_complete_ = received_mappings_ >= expected_mappings_;
      if (mapping_complete_ && !was_complete) {
        // Announce every local switch now that numbers resolve (see
        // io-boards announceLocalSwitchStates for why this matters).
        memset(ring_, 0, sizeof(ring_));
        uint32_t current[(kNumSwitchPorts + 31) / 32];
        memcpy(current, last_port_bitmap_, sizeof(current));
        memset(last_port_bitmap_, 0xFF, sizeof(last_port_bitmap_));
        for (uint16_t q = 1; q < kNumSwitchPorts; ++q) {
          if (!PortBit(current, q)) continue;
          last_port_bitmap_[q / 32] &= ~(1u << (q % 32));
        }
        UpdateLocalSwitches(current);
      }
      return;
    }
    case kFrameOutputState: {
      if (!config_valid_) return;
      AnswerToken(frame[2]);  // reply first: switch latency must not wait on outputs
      const size_t coil_bytes = BitsToBytes(cfg_.coilBits);
      const size_t lamp_bytes = BitsToBytes(cfg_.lampBits);
      TranslateOutputs(p, p + coil_bytes, p + coil_bytes + lamp_bytes);
      listener_.OnOutputs();
      return;
    }
    case kFrameSwitchRefresh:
      if (!config_valid_) return;
      force_refresh_ = true;
      AnswerToken(frame[2]);
      return;
    case kFrameSwitchState:
      if (!config_valid_ || epoch != epoch_) return;
      ApplyRemoteSwitches(p + kSwitchStatusBytes);
      AnswerToken(frame[2]);
      return;
    case kFrameSwitchNoChange:
      if (config_valid_ && epoch == epoch_) AnswerToken(frame[2]);
      return;
    case kFrameConfig: {
      uint8_t board, topic, index, key;
      uint32_t value;
      ReadConfigPayload(p, board, topic, index, key, value);
      if (!Ours(board)) return;
      applier_.Apply(board, topic, index, key, value);
      port_index_dirty_ = true;
      SendConfigAck(board, topic, index, key, kConfigAckAccepted);
      return;
    }
    default:
      return;  // Trigger (no effects engine here), Heartbeat, Error, ConfigAck
  }
}

}  // namespace sam

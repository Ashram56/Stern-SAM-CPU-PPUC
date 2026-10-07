// Host tests for src/core. No framework: each CHECK prints the failing line.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#include <stdio.h>
#include <string.h>

#include <vector>

#include "../src/core/coil_engine.h"
#include "../src/core/devices.h"
#include "../src/core/dmd_frames.h"
#include "../src/core/io_scheduler.h"
#include "../src/core/lamp_engine.h"
#include "../src/core/ppuc_session.h"
#include "../src/core/switch_chain.h"
#include "../src/core/switch_scanner.h"
#include "../src/ppuc/ppuc_topics.h"

using namespace sam;

static int g_failures = 0;
static int g_checks = 0;
#define CHECK(cond)                                                  \
  do {                                                               \
    ++g_checks;                                                      \
    if (!(cond)) {                                                   \
      ++g_failures;                                                  \
      printf("%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, #cond); \
    }                                                                \
  } while (0)

// ---- Switch chain ----------------------------------------------------------

// Stream with every input open (1) except the listed ones.
struct StreamBuilder {
  uint64_t bits = (1ull << kChainBits) - 1;
  void Close(uint8_t chip_offset, uint8_t input) {
    bits &= ~(1ull << (chip_offset + 7 - input));
  }
  // The two words switch_chain.pio pushes for this stream.
  uint32_t Word0() const { return static_cast<uint32_t>(bits); }
  uint32_t Word1() const { return static_cast<uint32_t>((bits >> 32) & 0xFFFFFF) << 8; }
};

static void TestChainDecode() {
  StreamBuilder s;
  s.Close(0, 0);    // U30 D0: memory protect
  s.Close(8, 2);    // U19 D2: matrix return 3
  s.Close(16, 7);   // U18 D7: matrix return 16
  s.Close(24, 4);   // U17 D4: D5
  s.Close(48, 0);   // U14 D0: DIP 1 = D25
  const ChainInputs in = DecodeChain(ChainStream(s.Word0(), s.Word1()));
  CHECK(in.mem_protect);
  CHECK(in.returns == ((1u << 2) | (1u << 15)));
  CHECK(in.dedicated == ((1u << 4) | (1u << 24)));

  CHECK(PatternStrobe(StrobePattern(3, true, false)) == 3);
  CHECK(StrobePattern(3, true, true) == ((1u << 11) | 0x3));
  CHECK(PatternStrobe(0) == -1);
}

static void TestScanner() {
  Devices d;
  DevicesReset(d);
  SwitchScanner sc;
  sc.Reset();
  ChainInputs open = {0, 0, false};

  // Dedicated D1 closes at t = 0, sampled every 6 us: accepted after 50 us.
  ChainInputs d1 = open;
  d1.dedicated = 1;
  uint32_t t = 0;
  for (; t < 48; t += 6) sc.OnPass(t, 0, d1, d);
  CHECK(!sc.State(kSwitchDedicatedFirst));
  for (; t < 60; t += 6) sc.OnPass(t, 0, d1, d);
  CHECK(sc.State(kSwitchDedicatedFirst));

  // Matrix switch strobe 2 / return 1 (SAM switch 33): needs two scans.
  sc.Reset();
  auto scan = [&](uint32_t& now) {
    for (uint8_t s = 0; s < 8; ++s) {
      const uint32_t start = now;
      for (; now < start + d.board.strobe_dwell_us; now += 6) {
        ChainInputs in = open;
        if (s == 2) in.returns = 1;
        sc.OnPass(now, StrobePattern(static_cast<int8_t>(s), false, false), in, d);
      }
    }
  };
  t = 0;
  scan(t);  // first sample of strobe 2, filed when strobe 3 starts
  CHECK(!sc.State(MatrixSwitchPort(2, 0)));
  scan(t);  // second sample one scan later: accepted
  CHECK(sc.State(MatrixSwitchPort(2, 0)));
  CHECK(!sc.State(MatrixSwitchPort(1, 0)));
  CHECK(!sc.State(MatrixSwitchPort(3, 0)));
}

// ---- Lamps -----------------------------------------------------------------

static void TestLampSteps() {
  Devices d;
  DevicesReset(d);
  LampEngine le;
  d.lamp[1].used = true;    // line 0, LMP_DRV bit 7
  d.lamp[1].brightness = 255;
  d.lamp[1].light_up_ms = 0;
  d.lamp[1].after_glow_ms = 0;
  d.lamp[8].used = true;    // line 0, bit 0
  d.lamp[8].brightness = 128;
  d.lamp[8].light_up_ms = 0;
  d.lamp[8].after_glow_ms = 0;
  uint8_t on[(kNumLampPorts + 7) / 8] = {};
  on[0] = (1u << 1);
  on[1] = 1;  // port 8
  le.UpdateLevels(2500, d, on);

  LampStep st[kMaxLampSteps];
  const uint8_t n = le.BuildLine(0, 226, st);
  CHECK(n == 2);
  CHECK(st[0].t_us == 0 && st[0].drive == 0x81);
  // 128/255 after gamma 2.2 is ~21.8 % of 226 us.
  CHECK(st[1].t_us >= 45 && st[1].t_us <= 52);
  CHECK(st[1].drive == 0x80);
  CHECK(le.BuildLine(1, 226, st) == 0);

  // Light-up ramp: 100 ms to full, 10 ms in -> about 10 %.
  d.lamp[2].used = true;
  d.lamp[2].brightness = 255;
  d.lamp[2].light_up_ms = 100;
  d.lamp[2].after_glow_ms = 0;
  on[0] |= (1u << 2);
  for (int i = 0; i < 4; ++i) le.UpdateLevels(2500, d, on);
  CHECK(le.Level(2) > 6000 && le.Level(2) < 7200);
  on[0] &= static_cast<uint8_t>(~(1u << 2));
  le.UpdateLevels(2500, d, on);
  CHECK(le.Level(2) == 0);  // after_glow 0: off at once
}

// ---- IO scheduler ----------------------------------------------------------

struct BusOp {
  uint32_t t;
  uint8_t reg;
  uint8_t value;
  bool read;
};

class FakeBus : public Bus {
 public:
  uint32_t now = 0;
  std::vector<BusOp> log;
  void Write(uint8_t reg, uint8_t value) override { log.push_back({now, reg, value, false}); }
  void Read(uint8_t reg) override { log.push_back({now, reg, 0, true}); }
};

static void TestScheduler() {
  Devices d;
  DevicesReset(d);
  d.lamp[1].used = true;
  d.lamp[1].brightness = 128;
  d.lamp[1].light_up_ms = 0;
  d.lamp[1].after_glow_ms = 0;
  uint8_t on[(kNumLampPorts + 7) / 8] = {};
  on[0] = 1u << 1;

  FakeBus bus;
  LampEngine le;
  IoScheduler io(bus, le);
  io.Start(0, d);
  for (bus.now = 0; bus.now <= 5100; ++bus.now) io.Poll(bus.now, d, on);

  int line0 = 0, aux_lines = 0, reads = 0;
  uint32_t lamp_on_at = 0, lamp_off_at = 0;
  for (const auto& w : bus.log) {
    if (w.read && w.reg == kRegStatus) reads++;
    if (!w.read && w.reg == kRegLmpStb && w.value == 1) line0++;
    if (!w.read && w.reg == kRegAuxLmp && w.value != 0) aux_lines++;
    if (!w.read && w.reg == kRegLmpDrv && w.value == 0x80 && w.t >= 2500 && !lamp_on_at) lamp_on_at = w.t;
    if (!w.read && w.reg == kRegLmpDrv && w.value == 0 && lamp_on_at && !lamp_off_at && w.t > lamp_on_at)
      lamp_off_at = w.t;
  }
  // Line 0 (DRV0, the IO board watchdog) every 2.5 ms; lines 8-9 on AUX_LMP.
  CHECK(line0 == 3);
  CHECK(aux_lines == 4);
  CHECK(reads == 6);
  // Lamp 1 lit 24 us after its slot starts (frame 2: the first frame's levels
  // were still 0 when its line 0 slot was planned), dropped ~49 us later.
  CHECK(lamp_on_at == 2500 + 24);
  CHECK(lamp_off_at >= lamp_on_at + 45 && lamp_off_at <= lamp_on_at + 52);

  // Coils: coil 1 -> SOL_B bit 0, coil 9 -> SOL_A bit 0, coil 33 -> aux latch.
  bus.log.clear();
  uint8_t drive[kNumCoilPorts] = {};
  drive[1] = drive[9] = drive[33] = 1;
  io.SetCoils(5101, drive);
  bool sol_b = false, sol_a = false, aux = false, strobe6 = false;
  for (const auto& w : bus.log) {
    if (w.reg == kRegSolB && w.value == 1) sol_b = true;
    if (w.reg == kRegSolA && w.value == 1) sol_a = true;
    if (w.reg == kRegAuxDrv && w.value == 1) aux = true;
    if (w.reg == kRegAuxGi && !(w.value & (1u << kAuxCoilStrobeBit))) strobe6 = true;
  }
  CHECK(sol_b && sol_a && aux && strobe6);
  bus.log.clear();
  io.SetCoils(5102, drive);
  CHECK(bus.log.empty());  // nothing changed, no refresh due
}

// ---- Coils -----------------------------------------------------------------

class FakeSwitches : public SwitchLookup {
 public:
  bool closed[256] = {};
  bool Closed(uint16_t n) const override { return n < 256 && closed[n]; }
};

static void TestCoils() {
  Devices d;
  DevicesReset(d);
  CoilConfig& c = d.coil[1];
  c.used = true;
  c.type = PWM_TYPE_SOLENOID;
  c.power = 255;
  c.max_pulse_ms = 30;
  CoilConfig& f = d.coil[2];
  f.used = true;
  f.type = PWM_TYPE_SOLENOID;
  f.power = 255;
  f.hold_power = 0;
  f.fast_switch = 5;

  CoilEngine ce;
  ce.Reset();
  FakeSwitches sw;
  uint8_t host[(kNumCoilPorts + 7) / 8] = {};
  uint8_t drive[kNumCoilPorts];
  CoilInputs in = {host, false, true};

  host[0] = 1u << 1;
  ce.Update(0, d, in, sw, drive);
  CHECK(drive[1]);
  ce.Update(29000, d, in, sw, drive);
  CHECK(drive[1]);
  ce.Update(31500, d, in, sw, drive);
  CHECK(!drive[1]);  // max pulse cuts it although the host still holds it

  // Fast flip: on with the switch, off on release, without the host.
  sw.closed[5] = true;
  ce.Update(40000, d, in, sw, drive);
  CHECK(drive[2]);
  sw.closed[5] = false;
  ce.Update(41000, d, in, sw, drive);
  CHECK(!drive[2]);

  // Link lost while the button is held: off, and stays off until released.
  sw.closed[5] = true;
  ce.Update(42000, d, in, sw, drive);
  CHECK(drive[2]);
  in.allowed = false;
  ce.Update(43000, d, in, sw, drive);
  CHECK(!drive[2]);
  in.allowed = true;
  ce.Update(44000, d, in, sw, drive);
  CHECK(!drive[2]);
  sw.closed[5] = false;
  ce.Update(45000, d, in, sw, drive);
  sw.closed[5] = true;
  ce.Update(46000, d, in, sw, drive);
  CHECK(drive[2]);
}

// ---- PPUC session ----------------------------------------------------------

class CaptureLink : public LinkWriter {
 public:
  std::vector<std::vector<uint8_t>> frames;
  void Write(const uint8_t* data, size_t len) override { frames.emplace_back(data, data + len); }
};

class CountListener : public SessionListener {
 public:
  int restarts = 0, outputs = 0;
  void OnRestart(bool) override { restarts++; }
  void OnOutputs() override { outputs++; }
};

static void TestSession() {
  using namespace ppuc::v2;
  Devices d;
  DevicesReset(d);
  CaptureLink link;
  CountListener listener;
  PpucSession s(d, link, listener);
  s.SetBoardMask(0x07);

  uint8_t f[kMaxFrameBytes];
  uint8_t seq = 0;
  const uint8_t epoch = 3;
  auto send = [&](size_t len) { s.Feed(f, len); };

  send(BuildBareFrame(f, kFrameRestart, kFlagNone, kNoBoard, seq++, epoch));
  CHECK(listener.restarts == 1);

  // Config, as libppuc sends it: coil port 1 (number 7) on board 0, switch D1
  // (port 129, number 20) on board 2, token chain 0 -> 2 -> host.
  link.frames.clear();
  auto cfg = [&](uint8_t board, uint8_t topic, uint8_t key, uint32_t value) {
    send(BuildConfigFrame(f, kNoBoard, seq++, epoch, board, topic, 0, key, value));
  };
  cfg(0, CONFIG_TOPIC_PWM, CONFIG_TOPIC_PORT, 1);
  cfg(0, CONFIG_TOPIC_PWM, CONFIG_TOPIC_NUMBER, 7);
  cfg(0, CONFIG_TOPIC_PWM, CONFIG_TOPIC_POWER, 255);
  cfg(0, CONFIG_TOPIC_PWM, CONFIG_TOPIC_TYPE, PWM_TYPE_SOLENOID);
  cfg(2, CONFIG_TOPIC_SWITCHES, CONFIG_TOPIC_PORT, 129);
  cfg(2, CONFIG_TOPIC_SWITCHES, CONFIG_TOPIC_NUMBER, 20);
  cfg(0, CONFIG_TOPIC_SWITCH_CHAIN, CONFIG_TOPIC_NEXT_BOARD, 2);
  cfg(2, CONFIG_TOPIC_SWITCH_CHAIN, CONFIG_TOPIC_NEXT_BOARD, kNoBoard);
  cfg(5, CONFIG_TOPIC_PWM, CONFIG_TOPIC_PORT, 3);  // not ours: no ack
  CHECK(link.frames.size() == 8);
  CHECK(d.coil[1].used && d.coil[1].number == 7);
  CHECK(d.sw[129].used && d.sw[129].board == 2 && d.sw[129].number == 20);

  RuntimeConfig rc;
  rc.coilBits = 8;
  rc.lampBits = 8;
  rc.switchBits = 8;
  send(BuildSetupFrame(f, kNoBoard, seq++, epoch, rc));
  CHECK(!s.Running());
  for (uint16_t i = 0; i < 8; ++i) send(BuildMappingFrame(f, kNoBoard, seq++, epoch, kDomainCoil, i, i + 5));
  for (uint16_t i = 0; i < 8; ++i) send(BuildMappingFrame(f, kNoBoard, seq++, epoch, kDomainLamp, i, i + 1));
  for (uint16_t i = 0; i < 8; ++i) send(BuildMappingFrame(f, kNoBoard, seq++, epoch, kDomainSwitch, i, i + 17));
  CHECK(s.Running());

  // OutputState with coil index 2 (number 7) on, token to board 0.
  link.frames.clear();
  uint8_t coils[kMaxCoilBytes] = {0x04};
  uint8_t lamps[kMaxLampBytes] = {};
  uint8_t gi[kGiStrings] = {5, 0, 0, 0, 0};
  send(BuildOutputStateFrame(f, 0, seq++, epoch, rc, coils, lamps, gi));
  CHECK(listener.outputs == 1);
  CHECK(s.CoilsByPort()[0] & (1u << 1));
  CHECK(s.GiLevel(0) == 5);
  // Board 0 answers, then board 2 (next in the chain, also ours) answers.
  CHECK(link.frames.size() == 2);
  if (link.frames.size() == 2) {
    CHECK(ExtractType(link.frames[0][1]) == kFrameSwitchNoChange || ExtractType(link.frames[0][1]) == kFrameSwitchState);
    CHECK(link.frames[0][2] == 2);
    CHECK(link.frames[1][2] == kNoBoard);
    CHECK(VerifyCrc(link.frames[1].data(), link.frames[1].size()));
  }

  // D1 closes: board 2's next reply carries it (switch number 20 = index 3).
  uint32_t ports[(kNumSwitchPorts + 31) / 32] = {};
  ports[129 / 32] |= 1u << (129 % 32);
  s.UpdateLocalSwitches(ports);
  CHECK(s.HasQueuedReports());
  link.frames.clear();
  send(BuildOutputStateFrame(f, 0, seq++, epoch, rc, coils, lamps, gi));
  CHECK(link.frames.size() == 2);
  if (link.frames.size() == 2) {
    const auto& r = link.frames[1];
    CHECK(ExtractType(r[1]) == kFrameSwitchState);
    CHECK(r.size() > kHeaderBytes + kSwitchStatusBytes);
    if (r.size() > kHeaderBytes + kSwitchStatusBytes) {
      CHECK(r[kHeaderBytes + kSwitchStatusBytes] == (1u << 3));
    }
  }
  CHECK(!s.HasQueuedReports());

  // Version query for board 1 is answered with this board's type.
  link.frames.clear();
  send(BuildVersionQueryFrame(f, 1, seq++, epoch));
  CHECK(link.frames.size() == 1);

  // A corrupted frame is dropped and the parser recovers on the next one.
  const size_t len = BuildOutputStateFrame(f, 0, seq++, epoch, rc, coils, lamps, gi);
  f[len - 1] ^= 0xFF;
  link.frames.clear();
  send(len);
  CHECK(link.frames.empty());
  send(BuildOutputStateFrame(f, 0, seq++, epoch, rc, coils, lamps, gi));
  CHECK(link.frames.size() == 2);
}

// ---- Display frames --------------------------------------------------------

static void TestDmdFrames() {
  using namespace dmd;
  // Every grey level maps to the closest slot count out of 12.
  uint8_t prev_slots = 0;
  for (uint8_t g = 0; g < 16; ++g) {
    const uint8_t m = J5PlaneMask(g);
    uint8_t slots = 0;
    for (uint8_t p = 0; p < kJ5Planes; ++p) {
      if ((m >> p) & 1u) slots = static_cast<uint8_t>(slots + kJ5PlaneSlots[p]);
    }
    CHECK(slots >= prev_slots);
    prev_slots = slots;
  }
  CHECK(J5PlaneMask(0) == 0 && J5PlaneMask(15) == 0x0F);

  // 128x32 grey frame, pixel (5, 1) at level 15.
  static uint8_t frame[kHeaderBytes + 128 * 32 / 2];
  memset(frame, 0, sizeof(frame));
  const uint8_t hdr[8] = {'S', 'D', kGray4, 0, 0, 128, 0, 32};
  memcpy(frame, hdr, 8);
  frame[kHeaderBytes + (1 * 128 + 5) / 2] = 0x0F;  // x = 5 is odd: low nibble
  FrameHeader h;
  CHECK(ParseHeader(frame, sizeof(frame), h));
  FrameHeader h2;
  CHECK(!ParseHeader(frame, sizeof(frame) - 1, h2));
  ParseHeader(frame, sizeof(frame), h);
  static uint32_t px[kJ5PixelWords];
  BuildJ5Pixels(h, frame + kHeaderBytes, px);
  for (uint8_t p = 0; p < kJ5Planes; ++p) {
    CHECK(px[(1 * kJ5Planes + p) * 4 + 0] == (1u << 5));
    CHECK(px[(0 * kJ5Planes + p) * 4 + 0] == 0);
  }

  // J5 steps: 128 row-planes x 4 steps, one frame = 32 x 12 slots.
  static uint32_t steps[kJ5StepWords];
  BuildJ5Steps(steps);
  uint64_t cycles = 0;
  for (size_t i = 0; i < kJ5StepWords; ++i) {
    for (int k = 0; k < 2; ++k) {
      const uint16_t st = static_cast<uint16_t>(steps[i] >> (16 * k));
      cycles += 15 + 4u * (st >> 7);
    }
  }
  const double frame_ms = cycles * kJ5CtrlCycleNs / 1e6;
  CHECK(frame_ms > 15.8 && frame_ms < 16.1);  // 62.67 Hz
  if (!(frame_ms > 15.8 && frame_ms < 16.1)) printf("  J5 frame: %.3f ms\n", frame_ms);

  // HUB75: a red pixel at (130, 40) = panel B, bottom half, row 8 -> address 0,
  // chain position 2 * 128 + 2.
  static uint8_t rgb[kHeaderBytes + 256 * 64 * 3];
  memset(rgb, 0, sizeof(rgb));
  const uint8_t hdr2[8] = {'S', 'D', kRgb888, 0, 1, 0, 0, 64};
  memcpy(rgb, hdr2, 8);
  rgb[kHeaderBytes + (40 * 256 + 130) * 3] = 255;
  CHECK(ParseHeader(rgb, sizeof(rgb), h));
  static uint32_t hub[kHubPixelWords];
  BuildHub75Pixels(h, rgb + kHeaderBytes, kDefaultTint, hub);
  const size_t q = 2 * 128 + 2;
  for (uint8_t p = 0; p < kHubPlanes; ++p) {
    CHECK(hub[p * kHubWordsPerRow + q / 2] == (1u << 9));  // panel B R2, first of the pair
  }
  static uint32_t rows[kHubRows];
  BuildHub75Rows(60, rows);
  CHECK(rows[0] == (0u | (60u << 2)));
  CHECK(rows[kHubPlanes + 5] == (1u | ((60u << 5) << 2)));
}

int main() {
  TestChainDecode();
  TestScanner();
  TestLampSteps();
  TestScheduler();
  TestCoils();
  TestSession();
  TestDmdFrames();
  printf("%d checks, %d failed\n", g_checks, g_failures);
  return g_failures ? 1 : 0;
}

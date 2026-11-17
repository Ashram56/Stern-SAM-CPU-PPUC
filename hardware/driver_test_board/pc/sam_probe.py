#!/usr/bin/env python3
"""sam_probe: PC tool for the SAM driver output test board (USB CDC, firmware dtb 0.1).

  sam_probe.py [--port /dev/ttyACM0] info
  sam_probe.py status                          rails, current state of every output
  sam_probe.py capture -s 10 --vcd run.vcd --report run.md [--max-on-ms 50]
  sam_probe.py switch --matrix 3:5=1 ...       close matrix switch strobe 3 / return 5 (1-based); =0 opens
  sam_probe.py switch --ded 7=1 --enable 1     dedicated D-7 closed, outputs enabled
  sam_probe.py replay run.bin --vcd x.vcd      re-run the checks on a saved raw capture

Needs pyserial. Frames: 0xA5, cmd, len u16 LE, payload, CRC16-CCITT (init 0xFFFF) LE over cmd..payload.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse, struct, sys, time, json, os

# ---------------------------------------------------------------- channel names (state bits)
COILS = [f'coil{c:02d}' for c in range(1, 33)]                          # w0, active low
J12_STB = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11]
J13_COL = [1, 3, 4, 5, 6, 7, 8]
W1 = [f'lamp_strobe_J12p{p}' for p in J12_STB] + [f'lamp_col_J13p{p}' for p in J13_COL] + ['lamp_col_J13p10'] + \
     [f'spare{i}' for i in range(6)]
AUX = ['auxo_p1', 'auxo_p2', 'auxo_p3', 'auxo_p5', 'auxo_p6', 'auxo_p7', 'auxo_p8', 'auxo_p9', 'auxo_p10',
       'auxs_p9', 'auxs_p10', 'auxs_p11', 'auxs_p12']
W2 = AUX + [f'cpu_strobe{i}' for i in range(1, 9)]
RAILS = ['V50', 'V20S', 'V20F', 'V18L']
RAIL_MIN_MV = {'V50': 40000, 'V20S': 16000, 'V20F': 16000, 'V18L': 14000}


def crc16(data, c=0xFFFF):
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) if c & 0x8000 else c << 1
            c &= 0xFFFF
    return c


class Board:
    def __init__(self, port):
        import serial
        self.s = serial.Serial(port, 115200, timeout=0.05)
        self.buf = b''
        self.events = []

    def send(self, cmd, payload=b''):
        body = struct.pack('<BH', cmd, len(payload)) + payload
        self.s.write(b'\xA5' + body + struct.pack('<H', crc16(body)))

    def frames(self):
        self.buf += self.s.read(65536)
        while True:
            i = self.buf.find(b'\xA5')
            if i < 0: self.buf = b''; return
            self.buf = self.buf[i:]
            if len(self.buf) < 4: return
            cmd, n = struct.unpack_from('<BH', self.buf, 1)
            if len(self.buf) < n + 6: return
            body, crc = self.buf[1:4 + n], struct.unpack_from('<H', self.buf, 4 + n)[0]
            self.buf = self.buf[n + 6:]
            if crc16(body) != crc: continue
            yield cmd, body[3:]

    def call(self, cmd, payload=b'', timeout=2.0):
        self.send(cmd, payload)
        t0 = time.time()
        while time.time() - t0 < timeout:
            for c, p in self.frames():
                if c == 0x80: self.events += parse_events(p)
                elif c == (cmd | 0x40): return p
                elif c == 0x7F: raise RuntimeError(f'board refused command 0x{cmd:02x}')
        raise TimeoutError(f'no answer to 0x{cmd:02x}')


def parse_events(p):
    return [struct.unpack_from('<BQIII', p, i) for i in range(0, len(p) - 20, 21)]


def parse_status(p):
    run, now, ovf, upd = struct.unpack_from('<BQII', p, 0)
    mv = struct.unpack_from('<4H', p, 17)
    w0, w1, w2 = struct.unpack_from('<III', p, 25)
    return dict(running=run, now_us=now, overflows=ovf, switch_updates=upd, rails_mv=dict(zip(RAILS, mv)), w=(w0, w1, w2))


def active(name, bit):
    """True when the channel is ON: low-side outputs and CPU strobes are active low, lamp columns active high."""
    if name.startswith('lamp_col') or name.startswith('spare'): return bool(bit)
    if name.startswith('aux'): return bool(bit)
    return not bit


def unpack(w):
    out = {}
    for i, n in enumerate(COILS): out[n] = (w[0] >> i) & 1
    for i, n in enumerate(W1): out[n] = (w[1] >> i) & 1
    for i, n in enumerate(W2): out[n] = (w[2] >> i) & 1
    return out


# ---------------------------------------------------------------- checks
def check(events, max_on_ms=50.0, lamp_stuck_ms=5.0):
    """events: (kind, t_us, w0, w1, w2) sorted by time. Returns a list of findings (strings) and stats."""
    findings, on_since, stats = [], {}, {n: dict(pulses=0, longest_ms=0.0) for n in COILS}
    last = None
    lamp_last_change = None
    for kind, t, w0, w1, w2 in events:
        if kind != 0: continue
        st = unpack((w0, w1, w2))
        for n in COILS:
            on = active(n, st[n])
            if on and n not in on_since: on_since[n] = t; stats[n]['pulses'] += 1
            if not on and n in on_since:
                ms = (t - on_since.pop(n)) / 1000
                stats[n]['longest_ms'] = max(stats[n]['longest_ms'], ms)
                if ms > max_on_ms: findings.append(f'{t / 1e6:10.6f} s  {n} on for {ms:.1f} ms (> {max_on_ms} ms)')
        strobes = [n for n in W1[:10] if active(n, st[n])]
        if len(strobes) > 1: findings.append(f'{t / 1e6:10.6f} s  several lamp strobes at once: {", ".join(strobes)}')
        cols = [n for n in W1[10:18] if active(n, st[n])]
        if cols and not strobes: findings.append(f'{t / 1e6:10.6f} s  lamp columns on without a strobe: {", ".join(cols)}')
        cs = [n for n in W2[13:] if active(n, st[n])]
        if len(cs) > 1: findings.append(f'{t / 1e6:10.6f} s  several CPU switch strobes at once: {", ".join(cs)}')
        key = w1 & 0x3FF
        if last is None or key != last: lamp_last_change, last = t, key
    if events:
        t_end = events[-1][1]
        for n, t0 in on_since.items():
            ms = (t_end - t0) / 1000
            if ms > max_on_ms: findings.append(f'end          {n} still on after {ms:.1f} ms')
        if lamp_last_change is not None and (t_end - lamp_last_change) / 1000 > lamp_stuck_ms:
            findings.append(f'end          lamp strobes frozen for {(t_end - lamp_last_change) / 1000:.1f} ms (IO watchdog will reset)')
    return findings, stats


def write_vcd(events, path):
    names = COILS + W1 + W2
    ids = {n: ''.join(chr(33 + (i // 94 ** k) % 94) for k in range(2)) for i, n in enumerate(names)}
    with open(path, 'w') as f:
        f.write('$timescale 1 us $end\n$scope module dtb $end\n')
        for n in names: f.write(f'$var wire 1 {ids[n]} {n} $end\n')
        f.write('$upscope $end\n$enddefinitions $end\n')
        prev = {}
        aux_w = None
        for kind, t, w0, w1, w2 in events:
            st = unpack((w0, w1, w2)) if kind == 0 else {n: (w2 >> i) & 1 for i, n in enumerate(AUX)}
            ch = [(n, v) for n, v in st.items() if prev.get(n) != v]
            if not ch: continue
            f.write(f'#{t}\n')
            for n, v in ch: f.write(f'{v}{ids[n]}\n'); prev[n] = v


def report(events, findings, stats, rails, path, max_on_ms):
    lines = ['# sam_probe report', '', f'Events: {len(events)}, duration {events[-1][1] / 1e6 if events else 0:.3f} s', '']
    if rails:
        lines += ['## Rails', ''] + [f'- {k}: {v / 1000:.1f} V' + ('' if v >= RAIL_MIN_MV[k] else '  **LOW: outputs read "on" through the flyback diodes, results invalid**')
                                     for k, v in rails.items()] + ['']
    lines += [f'## Findings (max on time {max_on_ms} ms)', ''] + ([f'- {x}' for x in findings[:500]] or ['- none']) + ['']
    lines += ['## Coils', '', '| coil | pulses | longest (ms) |', '|---|---|---|']
    lines += [f'| {n} | {s["pulses"]} | {s["longest_ms"]:.2f} |' for n, s in stats.items() if s['pulses']]
    open(path, 'w').write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', default=os.environ.get('DTB_PORT', '/dev/ttyACM0'))
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('info'); sub.add_parser('status')
    c = sub.add_parser('capture'); c.add_argument('-s', '--seconds', type=float, default=5)
    c.add_argument('--vcd'); c.add_argument('--report'); c.add_argument('--raw', help='save events (json lines)')
    c.add_argument('--max-on-ms', type=float, default=50.0)
    s = sub.add_parser('switch'); s.add_argument('--matrix', nargs='*', default=[]); s.add_argument('--ded', nargs='*', default=[])
    s.add_argument('--enable', type=int)
    r = sub.add_parser('replay'); r.add_argument('raw'); r.add_argument('--vcd'); r.add_argument('--report')
    r.add_argument('--max-on-ms', type=float, default=50.0)
    a = ap.parse_args()

    if a.cmd == 'replay':
        ev = [tuple(json.loads(l)) for l in open(a.raw)]
        fnd, st = check(ev, a.max_on_ms)
        if a.vcd: write_vcd(ev, a.vcd)
        if a.report: report(ev, fnd, st, None, a.report, a.max_on_ms)
        print('\n'.join(fnd) or 'no findings'); return

    b = Board(a.port)
    if a.cmd == 'info':
        print(b.call(0x01).decode())
    elif a.cmd == 'status':
        st = parse_status(b.call(0x02))
        print(json.dumps({k: v for k, v in st.items() if k != 'w'}, indent=1))
        on = [n for n, v in unpack(st['w']).items() if active(n, v) and not n.startswith('spare')]
        print('on:', ', '.join(on) or 'nothing')
    elif a.cmd == 'switch':
        m = [0] * 8; d = 0
        for x in a.matrix:
            k, v = x.split('='); s_, r_ = map(int, k.split(':'))
            if int(v): m[s_ - 1] |= 1 << (r_ - 1)
        for x in a.ded:
            k, v = x.split('=')
            if int(v): d |= 1 << (int(k) - 1)
        b.call(0x20, struct.pack('<8H', *m)); b.call(0x21, struct.pack('<I', d))
        if a.enable is not None: b.call(0x22, bytes([a.enable]))
        print('ok')
    elif a.cmd == 'capture':
        rails = parse_status(b.call(0x02))['rails_mv']
        low = [k for k, v in rails.items() if v < RAIL_MIN_MV[k]]
        if low: print('WARNING: rails low (' + ', '.join(low) + '): every output reads ON through its flyback diode', file=sys.stderr)
        b.events = []
        b.call(0x10)
        t0 = time.time()
        while time.time() - t0 < a.seconds:
            for c_, p in b.frames():
                if c_ == 0x80: b.events += parse_events(p)
        b.call(0x11)
        time.sleep(0.2)
        for c_, p in b.frames():
            if c_ == 0x80: b.events += parse_events(p)
        ev = sorted(b.events, key=lambda e: e[1])
        ovf = parse_status(b.call(0x02))['overflows']
        if ovf: print(f'WARNING: {ovf} events lost (USB too slow)', file=sys.stderr)
        if a.raw:
            with open(a.raw, 'w') as f:
                for e in ev: f.write(json.dumps(e) + '\n')
        fnd, st = check(ev, a.max_on_ms)
        if a.vcd: write_vcd(ev, a.vcd)
        if a.report: report(ev, fnd, st, rails, a.report, a.max_on_ms)
        print(f'{len(ev)} events'); print('\n'.join(fnd[:50]) or 'no findings')


if __name__ == '__main__':
    main()

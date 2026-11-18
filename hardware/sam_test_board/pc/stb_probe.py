#!/usr/bin/env python3
"""stb_probe: PC tool for the SAM universal test boards (USB CDC, firmware stb 0.1), one or several at once.

  stb_probe.py list                                   boards found, role (ID jumpers), firmware
  stb_probe.py status                                 rails and line states of every board
  stb_probe.py capture -s 10 --vcd run.vcd --report run.md [--max-on-ms 50]
                                                      all boards start together (first = SYNC master)
  stb_probe.py switch --matrix 3:5=1 --ded 7=1 --enable 1
                                                      matrix switch strobe 3 / return 5, dedicated D-7 (1-based)
  stb_probe.py replay run.jsonl --vcd x.vcd           re-run the checks on a saved capture

Boards are found by USB id (2e8a) or given with --port (several allowed). Each board reports its role from the
JP9/JP10 solder jumpers; the cables are straight (pin n of the SAM connector on pin n of the header):

  role 0 coils     : A = IO J8 (coils 1-8), B = IO J9 (9-16), C = IO J7 (17-24), D = IO J6 (25-32)
  role 1 lamps+aux : A = IO J3 (aux strobes on 9-12, edge capture), B = IO J12 (lamp strobes),
                     C = IO J13 (lamp columns), D = IO J2 (aux data)
  role 2 matrix    : A = CPU J1 (strobes, read fast), B = CPU J6 (returns 1-8), C = CPU J12 (returns 9-16),
                     D = CPU J2 (D-1..D-8)
  role 3 dedicated : A = CPU J3 (D-9..D-16), B = CPU J13 (D-17..D-24), C and D free

Needs pyserial. Frames: 0xA5, cmd, len u16 LE, payload, CRC16-CCITT (init 0xFFFF) LE over cmd..payload.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse, struct, sys, time, json, os

# ---------------------------------------------------------------- SAM connector pinouts (SAM schematics)
J8_PINS = {1: 1, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9}            # coil -> pin (key 2)
J9_PINS = {9: 1, 10: 2, 11: 4, 12: 5, 13: 6, 14: 7, 15: 8, 16: 9}     # key 3
J7_PINS = {17: 2, 18: 3, 19: 4, 20: 6, 21: 7, 22: 8, 23: 9, 24: 10}   # +20 V on 1, key 5
J6_PINS = {25 + i: 1 + i for i in range(8)}                             # +20 V on 10, key 9
J12_STB = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11]                              # key 7, GND 12
J13_COL = [1, 3, 4, 5, 6, 7, 8, 10]                                     # +18 V on 9 (or 10: check the 9/10 swap)
J2_AUX = [1, 2, 3, 5, 6, 7, 8, 9, 10]
J3_ASTB = [9, 10, 11, 12]
CPU_J1_STB = [1, 3, 4, 5, 6, 7, 8, 9]                                   # strobes 1..8, key 2
CPU_J6_RET = [9, 8, 7, 6, 5, 3, 2, 1]                                   # return 1..8, GND 10
CPU_J12_RET = [9, 8, 7, 6, 4, 3, 2, 1]                                  # return 9..16, GND 10
CPU_J2_DED = [2, 3, 4, 6, 7, 8, 9, 10]                                  # D-1..D-8
CPU_J3_DED = [1, 2, 4, 5, 6, 7, 8, 9]                                   # D-9..D-16
CPU_J13_DED = [1, 3, 4, 5, 6, 7, 8, 9]                                  # D-17..D-24
HEADERS = 'ABCD'
def chan(h, p): return HEADERS.index(h) * 12 + p - 1                    # channel bit of header h pin p

ROLE_NAMES = ['coils', 'lamps', 'matrix', 'dedicated']
def role_map(role):
    """channel bit -> signal name for a board role"""
    m = {}
    if role == 0:
        for h, pins in zip(HEADERS, (J8_PINS, J9_PINS, J7_PINS, J6_PINS)):
            for c, p in pins.items(): m[chan(h, p)] = f'coil{c:02d}'
    elif role == 1:
        for p in J3_ASTB: m[chan('A', p)] = f'auxs_p{p}'
        for p in J12_STB: m[chan('B', p)] = f'lamp_strobe_J12p{p}'
        for p in J13_COL: m[chan('C', p)] = f'lamp_col_J13p{p}'
        for p in J2_AUX: m[chan('D', p)] = f'auxo_p{p}'
    elif role == 2:
        for i, p in enumerate(CPU_J1_STB): m[chan('A', p)] = f'cpu_strobe{i + 1}'
        for i, p in enumerate(CPU_J6_RET): m[chan('B', p)] = f'return{i + 1:02d}'
        for i, p in enumerate(CPU_J12_RET): m[chan('C', p)] = f'return{i + 9:02d}'
        for i, p in enumerate(CPU_J2_DED): m[chan('D', p)] = f'ded{i + 1:02d}'
    elif role == 3:
        for i, p in enumerate(CPU_J3_DED): m[chan('A', p)] = f'ded{i + 9:02d}'
        for i, p in enumerate(CPU_J13_DED): m[chan('B', p)] = f'ded{i + 17:02d}'
    return m

def active(name, bit):
    """True when the signal is ON: low-side outputs, CPU strobes and switch lines are active low;
    lamp columns and aux lines active high."""
    if name.startswith(('lamp_col', 'aux')): return bool(bit)
    return not bit

RAIL_MIN_MV = 4000      # a header common on a rail below 4 V: outputs with flyback diodes read ON, results invalid


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
        self.port = port
        self.s = serial.Serial(port, 115200, timeout=0.05)
        self.buf = b''
        self.events = []
        info = self.call(0x01)
        self.fw = info[:7].decode(); self.role = info[7]; self.uid = info[8:16].hex()
        self.names = role_map(self.role)

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

    def pump(self):
        for c, p in self.frames():
            if c == 0x80: self.events += parse_events(p)

    def call(self, cmd, payload=b'', timeout=2.0):
        self.send(cmd, payload)
        t0 = time.time()
        while time.time() - t0 < timeout:
            for c, p in self.frames():
                if c == 0x80: self.events += parse_events(p)
                elif c == (cmd | 0x40): return p
                elif c == 0x7F: raise RuntimeError(f'board refused command 0x{cmd:02x}')
        raise TimeoutError(f'no answer to 0x{cmd:02x}')

    def status(self):
        p = self.call(0x02)
        run, now, ovf, upd = struct.unpack_from('<BQII', p, 0)
        mv = struct.unpack_from('<4H', p, 17)
        ch, ha = struct.unpack_from('<QH', p, 25)
        return dict(running=run, now_us=now, overflows=ovf, switch_updates=upd,
                    rails_mv=dict(zip(['RAILA', 'RAILB', 'RAILC', 'RAILD'], mv)), ch=ch, ha=ha)


def parse_events(p):
    out = []
    for i in range(0, len(p) - 16, 17):
        kind, t = struct.unpack_from('<BQ', p, i)
        ch = int.from_bytes(p[i + 9:i + 15], 'little'); ha = struct.unpack_from('<H', p, i + 15)[0]
        out.append((kind, t, ch, ha))
    return out


def named_events(boards):
    """merge the boards' events: (t_us, kind, {name: level}) sorted by time"""
    out = []
    for b in boards:
        for kind, t, ch, ha in b.events:
            if kind == 0: st = {n: (ch >> c) & 1 for c, n in b.names.items()}
            else: st = {n: (ha >> c) & 1 for c, n in b.names.items() if c < 12}
            out.append((t, kind, st))
    out.sort(key=lambda e: e[0])
    return out


# ---------------------------------------------------------------- checks
def check(events, max_on_ms=50.0, lamp_stuck_ms=5.0):
    findings, on_since, stats = [], {}, {}
    level = {}
    lamp_last_change, last_strobes = None, None
    for t, kind, st in events:
        level.update(st)
        for n, v in st.items():
            if not n.startswith('coil'): continue
            stats.setdefault(n, dict(pulses=0, longest_ms=0.0))
            on = active(n, v)
            if on and n not in on_since: on_since[n] = t; stats[n]['pulses'] += 1
            if not on and n in on_since:
                ms = (t - on_since.pop(n)) / 1000
                stats[n]['longest_ms'] = max(stats[n]['longest_ms'], ms)
                if ms > max_on_ms: findings.append(f'{t / 1e6:10.6f} s  {n} on for {ms:.1f} ms (> {max_on_ms} ms)')
        if kind != 0: continue
        strobes = sorted(n for n, v in level.items() if n.startswith('lamp_strobe') and active(n, v))
        if len(strobes) > 1: findings.append(f'{t / 1e6:10.6f} s  several lamp strobes at once: {", ".join(strobes)}')
        cols = [n for n, v in level.items() if n.startswith('lamp_col') and active(n, v)]
        if cols and not strobes and any(n.startswith('lamp_strobe') for n in level):
            findings.append(f'{t / 1e6:10.6f} s  lamp columns on without a strobe: {", ".join(sorted(cols))}')
        cs = [n for n, v in level.items() if n.startswith('cpu_strobe') and active(n, v)]
        if len(cs) > 1: findings.append(f'{t / 1e6:10.6f} s  several CPU switch strobes at once: {", ".join(sorted(cs))}')
        if strobes != last_strobes: lamp_last_change, last_strobes = t, strobes
    if events:
        t_end = events[-1][0]
        for n, t0 in on_since.items():
            ms = (t_end - t0) / 1000
            if ms > max_on_ms: findings.append(f'end          {n} still on after {ms:.1f} ms')
        if lamp_last_change is not None and any(n.startswith('lamp_strobe') for n in level) \
                and (t_end - lamp_last_change) / 1000 > lamp_stuck_ms:
            findings.append(f'end          lamp strobes frozen for {(t_end - lamp_last_change) / 1000:.1f} ms (IO watchdog will reset)')
    return findings, stats


def write_vcd(events, path):
    names = sorted({n for _, _, st in events for n in st})
    ids = {n: ''.join(chr(33 + (i // 94 ** k) % 94) for k in range(2)) for i, n in enumerate(names)}
    with open(path, 'w') as f:
        f.write('$timescale 1 us $end\n$scope module sam $end\n')
        for n in names: f.write(f'$var wire 1 {ids[n]} {n} $end\n')
        f.write('$upscope $end\n$enddefinitions $end\n')
        prev = {}
        for t, kind, st in events:
            ch = [(n, v) for n, v in st.items() if prev.get(n) != v]
            if not ch: continue
            f.write(f'#{t}\n')
            for n, v in ch: f.write(f'{v}{ids[n]}\n'); prev[n] = v


def report(events, findings, stats, rails, path, max_on_ms):
    dur = events[-1][0] / 1e6 if events else 0
    lines = ['# stb_probe report', '', f'Events: {len(events)}, duration {dur:.3f} s', '']
    if rails:
        lines += ['## Rails (J5)', '']
        for board, mv in rails.items():
            lines += [f'- {board} {k}: {v / 1000:.1f} V' for k, v in mv.items()]
        lines += ['']
    lines += [f'## Findings (max on time {max_on_ms} ms)', ''] + ([f'- {x}' for x in findings[:500]] or ['- none']) + ['']
    if stats:
        lines += ['## Coils', '', '| coil | pulses | longest (ms) |', '|---|---|---|']
        lines += [f'| {n} | {s["pulses"]} | {s["longest_ms"]:.2f} |' for n, s in sorted(stats.items()) if s['pulses']]
    open(path, 'w').write('\n'.join(lines) + '\n')


def find_ports():
    from serial.tools import list_ports
    return [p.device for p in list_ports.comports() if p.vid == 0x2E8A]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', action='append', help='serial port (repeat for several boards); default: all found')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list'); sub.add_parser('status')
    c = sub.add_parser('capture'); c.add_argument('-s', '--seconds', type=float, default=5)
    c.add_argument('--vcd'); c.add_argument('--report'); c.add_argument('--raw', help='save named events (json lines)')
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

    boards = [Board(p) for p in (a.port or find_ports())]
    if not boards: sys.exit('no board found')
    label = lambda b: f'{ROLE_NAMES[b.role]}@{b.port}'
    if a.cmd == 'list':
        for b in boards: print(f'{b.port}  {b.fw}  role {b.role} ({ROLE_NAMES[b.role]})  id {b.uid}')
    elif a.cmd == 'status':
        for b in boards:
            st = b.status()
            print(label(b), json.dumps({k: v for k, v in st.items() if k not in ('ch', 'ha')}))
            on = sorted(n for c, n in b.names.items() if active(n, (st['ch'] >> c) & 1))
            print('  on:', ', '.join(on) or 'nothing')
    elif a.cmd == 'switch':
        mat = [b for b in boards if b.role == 2]; ded = [b for b in boards if b.role in (2, 3)]
        closed = {}
        for x in a.matrix:
            k, v = x.split('='); s_, r_ = map(int, k.split(':'))
            if int(v): closed.setdefault(s_, set()).add(r_)
        for b in mat:
            pins = bytes(p - 1 for p in CPU_J1_STB)
            inv = {n: c for c, n in b.names.items()}
            drive = [sum(1 << inv[f'return{r_:02d}'] for r_ in closed.get(s_ + 1, ())) for s_ in range(8)]
            b.call(0x20, pins + struct.pack('<8Q', *drive))
        for b in ded:
            inv = {n: c for c, n in b.names.items()}
            m = 0
            for x in a.ded:
                k, v = x.split('=')
                if int(v) and f'ded{int(k):02d}' in inv: m |= 1 << inv[f'ded{int(k):02d}']
            b.call(0x21, struct.pack('<Q', m))
            if a.enable is not None: b.call(0x22, bytes([a.enable]))
        print('ok' if ded else 'no matrix / dedicated board found')
    elif a.cmd == 'capture':
        rails = {label(b): b.status()['rails_mv'] for b in boards}
        for b in boards: b.events = []
        for b in boards[1:]: b.call(0x10, bytes([2]))                    # armed: start on SYNC
        boards[0].call(0x10, bytes([1 if len(boards) > 1 else 0]))       # master: start + SYNC pulse
        t0 = time.time()
        while time.time() - t0 < a.seconds:
            for b in boards: b.pump()
        for b in boards: b.call(0x11)
        time.sleep(0.2)
        for b in boards: b.pump()
        for b in boards:
            ovf = b.status()['overflows']
            if ovf: print(f'WARNING: {label(b)}: {ovf} events lost (USB too slow)', file=sys.stderr)
        ev = named_events(boards)
        if a.raw:
            with open(a.raw, 'w') as f:
                for e in ev: f.write(json.dumps(e) + '\n')
        fnd, st = check(ev, a.max_on_ms)
        if a.vcd: write_vcd(ev, a.vcd)
        if a.report: report(ev, fnd, st, rails, a.report, a.max_on_ms)
        print(f'{len(ev)} events'); print('\n'.join(fnd[:50]) or 'no findings')


if __name__ == '__main__':
    main()

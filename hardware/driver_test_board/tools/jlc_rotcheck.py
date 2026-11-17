"""Compare JLC (EasyEDA) footprints with the KiCad ones at the CPL pose.

kpy jlc_rotcheck.py <board.kicad_pcb> <cache dir with <LCSC>.json from easyeda.com/api/products/<LCSC>/components>
For each LCSC code: takes one KiCad instance, rotates the EasyEDA pads by the KiCad orientation (+ JLC_ROT) and prints the
worst pad distance per pad number, plus the best rotation offset / origin shift if that is not ~0.
"""
import sys, json, math, os
import pcbnew
sys.argv, (BOARD, CACHE) = sys.argv[:1], sys.argv[1:3]
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location('bom', os.path.join(os.path.dirname(__file__), 'jlc_bom.py'))
src = open(spec.origin).read().split('b = pcbnew.LoadBoard')[0]
ns = {}; exec(src, ns)
LCSC, JLC_ROT, JLC_POS = ns['LCSC'], ns['JLC_ROT'], ns['JLC_POS']
b = pcbnew.LoadBoard(BOARD)
inst = {}
for fp in b.GetFootprints():
    code = LCSC.get((fp.GetValue(), fp.GetFPID().GetLibItemName().wx_str()))
    if code and code not in inst: inst[code] = fp
def rot(x, y, deg):
    a = math.radians(deg); return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)
for code, fp in sorted(inst.items()):
    f = os.path.join(CACHE, code + '.json')
    if not os.path.exists(f): print(code, 'no cache'); continue
    ds = json.load(open(f))['result']['packageDetail']['dataStr']
    ox, oy = float(ds['head']['x']), float(ds['head']['y'])
    jl = {}
    for s in ds['shape']:
        if s.startswith('PAD~'):
            t = s.split('~'); jl.setdefault(t[8], []).append(((float(t[2]) - ox) * 0.254, (float(t[3]) - oy) * 0.254))
    px, py = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
    kd = {}
    for p in fp.Pads():
        kd.setdefault(p.GetNumber(), []).append((pcbnew.ToMM(p.GetPosition().x) - px, pcbnew.ToMM(p.GetPosition().y) - py))
    r0 = fp.GetOrientationDegrees()
    best = None
    for off in ((JLC_ROT.get(code, 0) % 360,) + tuple(o for o in (0, 90, 180, 270) if o != JLC_ROT.get(code, 0) % 360)):
        for shift in [(0, 0)]:
            err = 0; n = 0
            for num, pts in kd.items():
                if num not in jl or not num: continue
                for kx, ky in pts:
                    d = min(math.hypot(kx - (rx + sx), ky - (ry + sy)) for (jx, jy) in jl[num]
                            for rx, ry in [rot(jx, jy, r0 + off)] for sx, sy in [rot(JLC_POS.get(code, (0, 0))[0], -JLC_POS.get(code, (0, 0))[1], r0)])
                    err = max(err, d); n += 1
            if best is None or err < best[0]: best = (err, off, n)
    cur = JLC_ROT.get(code, 0) % 360
    status = 'OK' if best[1] == cur and best[0] < 0.5 else 'CHECK'
    print(f'{code:10s} {fp.GetReference():6s} {fp.GetValue():14s} rot {r0:5.0f}  best offset {best[1]:3d} (current {cur:3d})  max err {best[0]:.2f} mm over {best[2]} pads  {status}')

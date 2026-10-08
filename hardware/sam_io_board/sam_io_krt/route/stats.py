# routing stats: segments, vias, length per layer, narrowest track per power net, signal width spread
import pcbnew, sys, collections
b = pcbnew.LoadBoard(sys.argv[1])
want = {'/5V_IN': 1.0, '/Out_S': 1.0, '+5V': 0.5, '+3V3': 0.3, '/1V1': 0.3, 'GND': 0.3, '/A': 0.5, '/B': 0.5, '/SHD': 0.5}
lay = collections.Counter(); ns = nv = 0; mn = {}; under = collections.Counter(); tot = collections.Counter(); sig = collections.Counter()
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA": nv += 1; continue
    ns += 1; L = t.GetLength()/1e6; w = round(t.GetWidth()/1e6, 3); n = t.GetNetname(); lay[t.GetLayerName()] += L
    if n in want:
        tot[n] += L; mn[n] = min(mn.get(n, 9), w)
        if w < want[n] - 1e-6: under[n] += L
    else: sig[w] += L
print(f"segments {ns}  vias {nv}  length {sum(lay.values()):.0f} mm  " + "  ".join(f"{k} {v:.0f}" for k, v in sorted(lay.items())))
print("signal mm by width:", {k: round(v) for k, v in sorted(sig.items())})
for n in want: print(f"  {n:8s} min {mn.get(n, 0):.2f}  {under[n]:5.1f} of {tot[n]:5.1f} mm below {want[n]}")

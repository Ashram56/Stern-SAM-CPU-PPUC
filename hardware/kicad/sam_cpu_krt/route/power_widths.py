import pcbnew,sys,collections
b=pcbnew.LoadBoard(sys.argv[1])
want={'+12V':0.8,'Net-(D1-A1)':0.8,'Net-(J11-Pin_1)':0.8,'Net-(JP1-A)':0.8,'Net-(JP1-B)':0.8,'Net-(J23-Pin_1)':0.8,'+5V':0.5,'+3V3':0.25,'+4V5':0.25,'+1V1':0.25,'VREF':0.25}
for i in range(1,5): want[f'Net-(J10-Pin_{i})']=1.0; want[f'Net-(J24-Pin_{i})']=1.0
tot=collections.defaultdict(float); under=collections.defaultdict(float); mn={}
sig=collections.Counter()
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA": continue
    n=t.GetNetname(); w=t.GetWidth()/1e6; L=t.GetLength()/1e6
    if n in want:
        tot[n]+=L; mn[n]=min(mn.get(n,9),w)
        if w<want[n]-1e-6: under[n]+=L
    else: sig[round(w,3)]+=L
for n in sorted(tot): print(f"{n:22s} want {want[n]}  min {mn[n]:.2f}  {under[n]:6.1f}/{tot[n]:6.1f} mm under")
print("other nets by width (mm of track):", {k:round(v) for k,v in sorted(sig.items())})

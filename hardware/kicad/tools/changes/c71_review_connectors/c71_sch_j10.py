# c71: J10 pin order as the original harness expects: 1 L+, 2 L-, 3 R+, 4 R- (was 1 L+, 2 R+, 3 L-, 4 R-).
# Swaps the two local labels on J10 pins 2 and 3 in audio.kicad_sch. Run once.
import re
f='audio.kicad_sch'; t=open(f).read()
a=re.search(r'\(label "SPK_R_P"(?=\n\t\t\(at 287.02 134.62 180\))',t); b=re.search(r'\(label "SPK_L_N"(?=\n\t\t\(at 287.02 137.16 180\))',t)
assert a and b
t=t[:a.start()]+'(label "SPK_L_N"'+t[a.end():b.start()]+'(label "SPK_R_P"'+t[b.end():]
open(f,'w').write(t)

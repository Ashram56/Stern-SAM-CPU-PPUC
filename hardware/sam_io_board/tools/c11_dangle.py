"""Change 11 (2026-10-08): dangle.py <board> <drc_before.json> <drc_now.json>: delete tracks and vias that DRC reports dangling now but
did not before (the copper that only served removed parts). Prints how many were removed."""
import json, sys
def dang(f):
    d = json.load(open(f)); u = set()
    for v in d.get('violations', []):
        if v['type'] in ('track_dangling', 'via_dangling'):
            for it in v['items']: u.add(it['uuid'])
    return u
new = dang(sys.argv[3]) - dang(sys.argv[2])
s = open(sys.argv[1]).read(); n = 0
for u in new:
    k = s.find('(uuid "%s")' % u)
    if k < 0: continue
    a = max(s.rfind('\n\t(segment', 0, k), s.rfind('\n\t(via', 0, k), s.rfind('\n\t(arc', 0, k))
    e = s.find('\n\t)', k) + 3
    s = s[:a] + s[e:]; n += 1
open(sys.argv[1], 'w').write(s); print(n)

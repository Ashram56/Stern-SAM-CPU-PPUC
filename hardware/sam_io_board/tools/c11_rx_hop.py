"""Change 11 (2026-10-08): main_rx_hop.py <board>: on ../sam_io (hand-routed), R9 cannot become a straight F.Cu track because /485_DE runs
between its pads. Instead the former RO track drops through a via at (108.458, 61.9) and runs on B.Cu to the
existing /485_RX via at (109.347, 66.294). The RO and RX stubs that went to R9's pads are deleted."""
import re, sys, uuid
p = sys.argv[1]; s = open(p).read()
def drop(pat):
    global s
    m = re.search(r'\n\t\(segment\n\t\t\(start ' + pat + r'\)\n.*?\n\t\)', s, re.S)
    assert m, pat; s = s[:m.start()] + s[m.end():]
drop(r'107\.442 63\.945\)\n\t\t\(end 107\.442 65\.595')            # the straight R9 track added by c11_remove_qwiic_pcb.py
drop(r'107\.505 63\.945\)\n\t\t\(end 107\.442 63\.945')
drop(r'108\.458 62\.992\)\n\t\t\(end 107\.505 63\.945')
drop(r'107\.759 65\.595\)\n\t\t\(end 107\.442 65\.595')
s = s.replace('(start 108.458 62.992)\n\t\t(end 108.458 61.722)', '(start 108.458 61.9)\n\t\t(end 108.458 61.722)')
def seg(a, b, layer):
    return ('\n\t(segment\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(width 0.2)\n\t\t(layer "%s")\n\t\t(net "/485_RX")\n'
            '\t\t(uuid "%s")\n\t)' % (a[0], a[1], b[0], b[1], layer, uuid.uuid4()))
via = ('\n\t(via\n\t\t(at 108.458 61.9)\n\t\t(size 0.5)\n\t\t(drill 0.3)\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "/485_RX")\n'
       '\t\t(uuid "%s")\n\t)' % uuid.uuid4())
add = via + seg((108.458, 61.9), (108.458, 65.405), 'B.Cu') + seg((108.458, 65.405), (109.347, 66.294), 'B.Cu')
k = s.find('\n\t(segment'); s = s[:k] + add + s[k:]
open(p, 'w').write(s)

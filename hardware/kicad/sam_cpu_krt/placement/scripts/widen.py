"""Widen the board above the Pi: right edge from x 150.65 to 172 (KiCad mm) between y 30 and 126.5; zones follow."""
import sys, uuid
s = open(sys.argv[1]).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, (a, s.count(a)); s = s.replace(a, b)
rep('(start 30 30)\n\t\t(end 150.65 30)', '(start 30 30)\n\t\t(end 172 30)')
rep('(start 150.65 30)\n\t\t(end 150.65 184)', '(start 150.65 126.5)\n\t\t(end 150.65 184)')
def line(x1, y1, x2, y2):
    return (f'\t(gr_line\n\t\t(start {x1} {y1})\n\t\t(end {x2} {y2})\n\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
s = s.rstrip(); assert s.endswith(')')
s = s[:-1] + line(172, 30, 172, 126.5) + line(172, 126.5, 150.65, 126.5) + ')\n'
n = s.count('(xy 30 30) (xy 150.65 30) (xy 150.65 182)')
s = s.replace('(xy 30 30) (xy 150.65 30) (xy 150.65 182)', '(xy 30 30) (xy 172 30) (xy 172 126.5) (xy 150.65 126.5) (xy 150.65 182)')
print('zones widened:', n)
open(sys.argv[2], 'w').write(s)

"""Change 12 (2026-10-07): take the DMD interfaces off the board (follows c11 on the schematic).

    kpython c12_board_remove_dmd.py ../../sam_cpu/sam_cpu.kicad_pcb

- Deletes the 28 DMD footprints (J5 path and the HUB75 path, see c11) and every track and via of their signal nets.
- Ground / power copper that only served those footprints goes too: tracks with an end on a removed pad, then any
  unlocked or fan-out track left dangling, then power vias left with no track and no pad.
- RP2354B GPIO20-36 pads lose their DMD nets (now unconnected).
- The 142 mm extension below the Pi held only J25 / J26 and the HUB75 buffers, so the outline goes back to the
  original 120.65 x 231.76 mm rectangle and the four zones follow it.
- U30 / U31 / C125 / C126 and the GI parts get their new sheet names. No remaining part moves.
"""
import sys
import pcbnew

MM = pcbnew.FromMM
OX, OY = 30.0, 30.0
W, H = 120.65, 231.76
GONE = ('C95 J5 R176 R177 R178 R179 R180 R181 R182 RN4 RN5 U21 '
        'C122 C123 C124 J25 J26 RN6 RN7 RN8 RN9 RN10 RN11 TP23 TP24 U27 U28 U29').split()
POWER = {'GND', '+5V', '+3V3'}
# U4 pad -> GPIO for the freed pins (RP2354B QFN-80)
GPIO = {'20': 20, '21': 21, '22': 22, '23': 23, '25': 24, '26': 25, '27': 26, '28': 27, '36': 28, '37': 29,
        '38': 30, '39': 31, '40': 32, '42': 33, '43': 34, '44': 35, '45': 36}
SHEETS = {'Display and GI': 'GI dimmer', 'DMD panels': 'Switch chain extensions'}


def pt(x, y):
    return pcbnew.VECTOR2I(MM(x + OX), MM(y + OY))


def items(coll):
    return [coll[i] for i in range(coll.size())] if hasattr(coll, 'size') else list(coll)


def main(path):
    b = pcbnew.LoadBoard(path)
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    # take every list up front: pcbnew's collection proxies break once items are removed
    edges = [d for d in items(b.Drawings()) if d.GetLayer() == pcbnew.Edge_Cuts]
    zones = [z for z in items(b.Zones()) if not z.GetIsRuleArea()]
    gone_pads = [p for r in GONE for p in fps[r].Pads()]
    sig = {p.GetNetname() for p in gone_pads} - POWER - {''}
    # U4 pads on DMD nets lose them
    # freed RP2354B pins get the 'unconnected-(...)' net KiCad gives no-connect pins
    freed = []
    for p in fps['U4'].Pads():
        if p.GetNetname().startswith('DMD_'):
            freed.append(p.GetNumber())
            n = pcbnew.NETINFO_ITEM(b, 'unconnected-(U4-GPIO%s-Pad%s)' % (GPIO[p.GetNumber()], p.GetNumber()))
            b.Add(n)
            p.SetNet(n)

    tracks = items(b.Tracks())
    drop = [t for t in tracks if t.GetNetname() in sig]

    def on_gone_pad(t, q):
        for p in gone_pads:
            if p.GetNetname() == t.GetNetname() and p.IsOnLayer(t.GetLayer()) and p.HitTest(q):
                return True
        return False
    for t in tracks:
        if t.GetNetname() in POWER and t.Type() == pcbnew.PCB_TRACE_T and (
                on_gone_pad(t, t.GetStart()) or on_gone_pad(t, t.GetEnd())):
            drop.append(t)
    # copper reaching into the extension that goes away (x > W - 0.3 below the Pi)
    for t in tracks:
        bb = t.GetBoundingBox()
        if pcbnew.ToMM(bb.GetRight()) - OX > W - 0.3 and pcbnew.ToMM(bb.GetBottom()) - OY > 154.0 and t not in drop:
            drop.append(t)
    for r in GONE:
        b.Remove(fps[r])
    for t in drop:
        b.Remove(t)
    # pcbnew's Tracks() proxy breaks after removals, so the live list is kept here
    gone_ids = {id(d) for d in drop}
    live = [t for t in tracks if id(t) not in gone_ids]
    n_sig = sum(1 for t in drop if t.GetNetname() in sig)

    # dangling power copper left behind
    pads = [p for r, f in fps.items() if r not in GONE for p in f.Pads()]
    extra = 0
    while True:
        segs = [t for t in live if t.Type() == pcbnew.PCB_TRACE_T]
        vias = [t for t in live if t.Type() == pcbnew.PCB_VIA_T]

        def touches(t, q):
            net = t.GetNetCode()
            for p in pads:
                if p.GetNetCode() == net and p.IsOnLayer(t.GetLayer()) and p.HitTest(q):
                    return True
            for o in segs:
                if o is not t and o.GetNetCode() == net and o.GetLayer() == t.GetLayer() and o.HitTest(q, 0):
                    return True
            for v in vias:
                if v.GetNetCode() == net and v.HitTest(q, 0):
                    return True
            return False
        dead = [t for t in segs if t.GetNetname() in POWER and
                not (touches(t, t.GetStart()) and touches(t, t.GetEnd()))]
        for v in vias:
            if v.GetNetname() not in POWER:
                continue
            q = v.GetPosition()
            on = {s.GetLayer() for s in segs if s.GetNetCode() == v.GetNetCode() and s.HitTest(q, 0)}
            if len(on) >= 2 or on and v.GetNetname() != '+5V':      # GND / +3V3 vias also land on a plane
                continue
            if any(p.GetNetCode() == v.GetNetCode() and p.HitTest(q) for p in pads):
                continue
            dead.append(v)
        if not dead:
            break
        for t in dead:
            b.Remove(t)
        dead_ids = {id(d) for d in dead}
        live = [t for t in live if id(t) not in dead_ids]
        extra += len(dead)

    # outline back to the original rectangle; zones follow
    for d in edges:
        b.Remove(d)
    rect = [(0, 0), (W, 0), (W, H), (0, H)]
    for a, c in zip(rect, rect[1:] + rect[:1]):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a))
        s.SetEnd(pt(*c))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        b.Add(s)
    for z in zones:
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for x, y in rect:
            o.Append(pt(x, y))

    for r, f in fps.items():
        if r in GONE:
            continue
        if f.GetSheetname() in SHEETS:
            f.SetSheetname(SHEETS[f.GetSheetname()])
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(path)
    print('footprints removed:', len(GONE))
    print('signal nets cleared:', len(sig), ' items:', n_sig)
    print('power copper removed: %d on removed pads, %d left dangling' % (len(drop) - n_sig, extra))
    print('U4 pads freed:', ' '.join(sorted(freed, key=int)))


if __name__ == '__main__':
    main(sys.argv[1])

"""Move footprints with their copper: private plane-via stubs travel with the part, other attached tracks get an
axis-aligned jog (E -> E+d), so no new odd angles appear."""
import pcbnew

def U(i): return i.m_Uuid.AsString()
PLANE = {'GND', '+3V3'}
MM = pcbnew.FromMM
keep = []

def P(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))

def _items_at(board, pt, net, tol=MM(0.005)):
    out = []
    for t in board.GetTracks():
        if t.GetNetCode() != net: continue
        if t.GetClass() == 'PCB_VIA':
            if (t.GetPosition() - pt).EuclideanNorm() <= tol: out.append((t, None))
        else:
            if (t.GetStart() - pt).EuclideanNorm() <= tol: out.append((t, 's'))
            if (t.GetEnd() - pt).EuclideanNorm() <= tol: out.append((t, 'e'))
    return out

def _pads_at(board, pt, net, layer):
    return [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetCode() == net and p.IsOnLayer(layer) and p.HitTest(pt)]

def move(board, ref, dx, dy, log=print):
    f = board.FindFootprintByReference(ref)
    d = P(dx, dy)
    mine = set(U(p) for p in f.Pads())
    moved = set(); jogs = []
    for t in list(board.GetTracks()):
        if t.GetClass() == 'PCB_VIA' or U(t) in moved: continue
        for end in ('s', 'e'):
            pt = t.GetStart() if end == 's' else t.GetEnd()
            pads = [p for p in f.Pads() if p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(t.GetLayer()) and p.HitTest(pt)]
            if not pads: continue
            # follow the chain from this pad
            chain = [t]; cur = t; far = t.GetEnd() if end == 's' else t.GetStart(); private = False
            for _ in range(4):
                if _pads_at(board, far, cur.GetNetCode(), cur.GetLayer()) and not any(U(p) in mine for p in _pads_at(board, far, cur.GetNetCode(), cur.GetLayer())):
                    break
                at = [(i, e) for i, e in _items_at(board, far, cur.GetNetCode()) if U(i) != U(cur)]
                vias = [i for i, e in at if e is None]
                segs = [(i, e) for i, e in at if e is not None]
                if vias and not segs and cur.GetNetname() in PLANE:
                    v = vias[0]
                    others = [i for i, e in _items_at(board, v.GetPosition(), v.GetNetCode()) if U(i) != U(v) and U(i) not in {U(c) for c in chain}]
                    if not others: chain.append(v); private = True
                    break
                if len(segs) == 1 and not vias and segs[0][0].GetLayer() == cur.GetLayer():
                    nxt, e2 = segs[0]; chain.append(nxt); cur = nxt
                    far = nxt.GetEnd() if e2 == 's' else nxt.GetStart(); continue
                break
            if private:
                for i in chain: i.Move(d); moved.add(U(i))
                log('  %s: moved private %s stub (%d items)' % (ref, t.GetNetname(), len(chain)))
            else:
                a = t.GetStart() if end == 's' else t.GetEnd()
                v = t.GetEnd() - t.GetStart()
                par = (v.x * d.y - v.y * d.x) == 0
                if par:
                    if end == 's': t.SetStart(a + d)
                    else: t.SetEnd(a + d)
                    log('  %s: stretched %s' % (ref, t.GetNetname()))
                else:
                    assert dx == 0 or dy == 0, '%s: a diagonal move would leave an odd-angle jog' % ref
                    n = pcbnew.PCB_TRACK(board); n.SetStart(a); n.SetEnd(a + d); n.SetWidth(t.GetWidth()); n.SetLayer(t.GetLayer()); n.SetNetCode(t.GetNetCode())
                    board.Add(n); keep.append(n); jogs.append(n)
                    log('  %s: jog on %s' % (ref, t.GetNetname()))
                moved.add(U(t))
            break
    f.Move(d)
    return jogs

def delete_net_copper(board, netname):
    n = 0
    for t in list(board.GetTracks()):
        if t.GetNetname() == netname: keep.append(t); board.Remove(t); n += 1
    return n

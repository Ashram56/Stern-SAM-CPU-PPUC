# c63: board side of c62 (TAS5805M x2 + PCM1808 + 74HC157 replace TDA7297 x2, OPA1678, PCM5102A).
# Run with KiCad 10 python, from hardware/kicad:
#   kpython tools/changes/c63_board_audio_tas5805m.py sam_cpu <netlist from c62 schematic>
# What it does, in sam_cpu/sam_cpu.kicad_pcb:
#   1. removes the footprints that are gone from the schematic or whose footprint changed (old audio parts),
#   2. removes the copper of nets that no longer exist, then the short stubs (power, GND) that only fed a
#      removed pad, walking each chain back to the first junction (at most STUB_MAX mm),
#   3. sets every pad net from the netlist (also renames U4 AMP_MUTE -> AMP_SCL etc.),
#   4. adds the new footprints from the KiCad library with value, fields, sheet path, and places them (PLACE),
#   5. updates the netclass patterns (Speaker class follows the new speaker nets).
# Routing is done by hand afterwards (hand_route tools), not here.
import pcbnew, re, sys, os, json, math
pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
D = sys.argv[1]; NETF = sys.argv[2]
PCB = os.path.join(D, 'sam_cpu.kicad_pcb'); PRO = os.path.join(D, 'sam_cpu.kicad_pro')
FPDIR = os.environ.get('KICAD10_FOOTPRINT_DIR', '/opt/k10dl/root/usr/share/kicad/footprints')
STUB_MAX = 6.0           # mm of dangling chain removed per stub
NO_STUB_CLEAN = ('I2S_BCK', 'I2S_LRCK', 'I2S_DIN')   # kept as they are, rerouted to the mux by hand
MM = 1e6

# ---------------------------------------------------------------- netlist
def parse_netlist(fn):
    t = open(fn).read(); comps = {}; nets = {}
    for m in re.finditer(r'\(comp\n(.*?)\n\t\t\)\n', t, re.S):
        b = m.group(1)
        g = lambda k: (re.search(r'\(%s "([^"]*)"\)' % k, b) or [None, None])[1]
        sp = re.search(r'\(sheetpath\s*\(names "([^"]*)"\)\s*\(tstamps "([^"]*)"\)\s*\)', b)
        comps[g('ref')] = dict(value=g('value'), footprint=g('footprint'), datasheet=g('datasheet'),
                               description=g('description'), sheetnames=sp[1], sheet=sp[2],
                               uuid=re.findall(r'\(tstamps "([^"]*)"\)', b)[-1])
    for m in re.finditer(r'\(net\s*\(code "\d+"\)\s*\(name "((?:[^"\\]|\\.)*)"\)(.*?)\n\t\t\)', t, re.S):
        for r, p in re.findall(r'\(node\s*\(ref "([^"]*)"\)\s*\(pin "([^"]*)"\)', m.group(2)):
            nets[(r, p)] = m.group(1).replace('\\"', '"')
    return comps, nets

COMPS, PADNET = parse_netlist(NETF)
SHEETFILE = {'/Audio/': 'audio.kicad_sch', '/RS485 and I2S/': 'rs485_i2s.kicad_sch', '/MCU and Pi/': 'mcu.kicad_sch'}

# ---------------------------------------------------------------- placement (x, y, rotation), all on F.Cu
PLACE = json.load(open(os.environ.get('C63_PLACE') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c63_place.json')))
PARK = [180.0, 40.0]     # anything without a place goes off-board, right of the outline

b = pcbnew.LoadBoard(PCB)
KEEP = []   # python references to removed items (avoid SWIG freeing them under us)

# 1. footprints to remove: gone, changed, or any audio part except the connectors and bulk caps (re-placed fresh)
KEEP_FP = {'J10', 'J22', 'J24', 'C108', 'C118'}
removed_pads = []
for fp in list(b.GetFootprints()):
    ref = fp.GetReference(); c = COMPS.get(ref)
    if ref.startswith('#') or ref == '' : continue
    if c is None or c['footprint'] != fp.GetFPIDAsString() or (c['sheetnames'] == '/Audio/' and ref not in KEEP_FP):
        for p in fp.Pads(): removed_pads.append(p)
        b.Remove(fp); KEEP.append(fp)
print('removed footprints:', len(KEEP))

# 1b. kept footprints that move go first, so the copper that fed their old place is pruned below
for fp in b.GetFootprints():
    if fp.GetReference() in PLACE:
        x, y, r = PLACE[fp.GetReference()]
        fp.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM))); fp.SetOrientationDegrees(r)

# 2a. copper of nets that no longer exist
newnets = set(PADNET.values())
for t in list(b.GetTracks()):
    n = t.GetNetname()
    if n and n not in newnets:
        b.Remove(t); KEEP.append(t)

# 2b. stubs that only fed a removed pad
def ends(t):
    if t.Type() == pcbnew.PCB_VIA_T: return [t.GetPosition()]
    return [t.GetStart(), t.GetEnd()]
def same(a, c): return abs(a.x - c.x) < 2000 and abs(a.y - c.y) < 2000
def on_removed_pad(pt, layer):
    return any(p.IsOnLayer(layer) and p.HitTest(pt) for p in removed_pads)
def live_pad_at(pt, layer):
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer) and p.HitTest(pt): return True
    return False
tracks = [t for t in b.GetTracks()]
alive = set(id(t) for t in tracks)
def items_at(pt, layer, skip):
    out = []
    for t in tracks:
        if id(t) not in alive or t is skip: continue
        if t.Type() == pcbnew.PCB_VIA_T:
            if same(t.GetPosition(), pt): out.append(t)
        elif t.GetLayer() == layer and (same(t.GetStart(), pt) or same(t.GetEnd(), pt)):
            out.append(t)
    return out
def kill(t):
    alive.discard(id(t)); b.Remove(t); KEEP.append(t)
nstub = 0
for t in list(tracks):
    if id(t) not in alive or t.Type() == pcbnew.PCB_VIA_T or t.GetNetname() in NO_STUB_CLEAN: continue
    L = t.GetLayer()
    for e0, e1 in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
        if on_removed_pad(e0, L) and not live_pad_at(e0, L) and not items_at(e0, L, t):
            # walk the chain from e1 while it stays a simple chain
            cur, far, length = t, e1, 0.0
            while True:
                length += cur.GetLength() / MM if cur.Type() != pcbnew.PCB_VIA_T else 0
                if length > STUB_MAX: break
                kill(cur); nstub += 1
                if live_pad_at(far, L): break
                nxt = items_at(far, L, None)
                if len(nxt) != 1: break
                n = nxt[0]
                if n.Type() == pcbnew.PCB_VIA_T:
                    others = [x for x in tracks if id(x) in alive and x is not n and x.Type() != pcbnew.PCB_VIA_T
                              and (same(x.GetStart(), far) or same(x.GetEnd(), far))]
                    if others: break
                    kill(n); nstub += 1; break       # orphan via that only took the stub to a plane
                cur = n; far = n.GetEnd() if same(n.GetStart(), far) else n.GetStart()
            break
# vias that sat inside a removed pad (thermal vias of old parts)
for t in list(tracks):
    if id(t) in alive and t.Type() == pcbnew.PCB_VIA_T and on_removed_pad(t.GetPosition(), pcbnew.F_Cu) \
       and not live_pad_at(t.GetPosition(), pcbnew.F_Cu):
        kill(t); nstub += 1
print('stub items removed:', nstub)

# 2c. +12V / +5V have no plane: prune every dead branch (leaf track or via that reaches no pad) inside the
#     audio area, so the old amplifier feeds go and the feeds of other blocks stay.
PRUNE = ('+12V', '+5V'); AREA = (85 * MM, 35 * MM, 172 * MM, 130 * MM)
def inside(pt): return AREA[0] <= pt.x <= AREA[2] and AREA[1] <= pt.y <= AREA[3]
def touches(pt, layer, me, items):
    if live_pad_at(pt, layer): return True
    for x in items:
        if x is me or id(x) not in alive: continue
        if x.Type() == pcbnew.PCB_VIA_T:
            if same(x.GetPosition(), pt): return True
        elif x.GetLayer() == layer:
            if same(x.GetStart(), pt) or same(x.GetEnd(), pt): return True
            # a T junction on the body counts, but not the body of a neighbour this track is chained to
            if me.Type() != pcbnew.PCB_VIA_T and any(same(e, f) for e in (x.GetStart(), x.GetEnd())
                                                    for f in (me.GetStart(), me.GetEnd())):
                continue
            if x.HitTest(pt, 0): return True
    return False
npr = 0
for net in PRUNE:
    items = [t for t in tracks if id(t) in alive and t.GetNetname() == net]
    changed = True
    while changed:
        changed = False
        for t in items:
            if id(t) not in alive: continue
            if t.Type() == pcbnew.PCB_VIA_T:
                p = t.GetPosition()
                if not inside(p): continue
                n = sum(1 for x in items if id(x) in alive and x is not t and x.Type() != pcbnew.PCB_VIA_T
                        and (same(x.GetStart(), p) or same(x.GetEnd(), p)))
                if n <= 1 and not live_pad_at(p, pcbnew.F_Cu) and not live_pad_at(p, pcbnew.B_Cu):
                    kill(t); npr += 1; changed = True
            else:
                for e in (t.GetStart(), t.GetEnd()):
                    if inside(e) and not touches(e, t.GetLayer(), t, items):
                        kill(t); npr += 1; changed = True; break
print('dead +12V/+5V branches removed:', npr)

# 3. nets
def netinfo(name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name); b.Add(n)
    return n

# 4. new footprints, kept ones get path / fields
have = {fp.GetReference(): fp for fp in b.GetFootprints()}
added = []
for ref, c in sorted(COMPS.items()):
    fp = have.get(ref)
    if fp is None:
        lib, name = c['footprint'].split(':', 1)
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name)
        assert fp is not None, c['footprint']
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref); fp.SetValue(c['value'])
        b.Add(fp); added.append(ref)
        x, y, r = PLACE.get(ref, (PARK[0], PARK[1], 0))
        if ref not in PLACE: PARK[1] += 6
        fp.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM))); fp.SetOrientationDegrees(r)
    elif ref in PLACE:
        x, y, r = PLACE[ref]
        fp.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM))); fp.SetOrientationDegrees(r)
    if c['sheetnames'] in ('/Audio/',) or ref in added:
        fp.SetPath(pcbnew.KIID_PATH(c['sheet'] + c['uuid']))
        fp.SetSheetname(c['sheetnames'].strip('/')); fp.SetSheetfile(SHEETFILE[c['sheetnames']])
        fp.SetValue(c['value'])
        if c['datasheet']: fp.SetField('Datasheet', c['datasheet'])
        if c['description']: fp.SetField('Description', c['description'])
    for p in fp.Pads():
        n = PADNET.get((ref, p.GetNumber()))
        if n is None and p.GetNumber() != '': n = ''
        if n is not None: p.SetNet(netinfo(n) if n else b.FindNet(''))
print('added footprints:', len(added), ' '.join(added))

# drop nets nothing uses any more
used = set()
for fp in b.GetFootprints():
    for p in fp.Pads(): used.add(p.GetNetname())
for t in b.GetTracks(): used.add(t.GetNetname())
for z in b.Zones(): used.add(z.GetNetname())
pcbnew.SaveBoard(PCB, b)

# 5. netclass patterns (project file)
pro = json.load(open(PRO)); ns = pro['net_settings']
ns['netclass_patterns'] = [p for p in ns['netclass_patterns']
                           if not re.match(r'Net-\((J10|J24)-Pin_\d\)|Net-\(U22-AVDD\)', p['pattern'])]
for n in ['/Audio/SPK_L_P', '/Audio/SPK_L_N', '/Audio/SPK_R_P', '/Audio/SPK_R_N',
          '/Audio/SUB1_P', '/Audio/SUB1_N', '/Audio/SUB2_P', '/Audio/SUB2_N']:
    ns['netclass_patterns'].append({'netclass': 'Speaker', 'pattern': n})
for n in ['/Audio/ADC_VCC']:
    ns['netclass_patterns'].append({'netclass': 'Power', 'pattern': n})
json.dump(pro, open(PRO, 'w'), indent=2); open(PRO, 'a').write('\n')
print('done; nets in use', len(used))

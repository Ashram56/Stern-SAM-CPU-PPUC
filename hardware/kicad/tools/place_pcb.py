#!/usr/bin/env python3
"""Build the draft PCB placement (outline, holes, connectors and a first placement of every part).

Run with KiCad 10's Python (the one that can `import pcbnew`):
    kicad-cli sch export netlist -o /tmp/sam_cpu.net hardware/kicad/sam_cpu/sam_cpu.kicad_sch
    python3 hardware/kicad/tools/place_pcb.py /tmp/sam_cpu.net hardware/kicad/sam_cpu/sam_cpu.kicad_pcb

Coordinates below are board millimetres with the origin at the top-left corner, X right, Y down, seen from the
component side as the board hangs in the backbox: the same frame as docs/mechanical (original board 520-5246-00).
The board is drawn at (ORIGIN_X, ORIGIN_Y) on the page; the grid and drill origins are set to the board corner so
KiCad shows the same numbers as this file.

Connectors, holes and the RP2354B are placed by hand. Decoupling capacitors and the parts that belong to one IC pin
(RP2354B regulator, crystal, USB resistors) are placed right next to that pin; everything else is packed into an
area per schematic sheet, next to the connector it serves. Tall parts stay out from under the Pi.
Once the board is edited in KiCad, do not rerun this.
"""
import os
import re
import sys

import pcbnew

ORIGIN_X, ORIGIN_Y = 30.0, 30.0
W, H = 120.65, 231.76          # 4.75 x 9.125 in; original is 219.06 x 231.76
FPDIR = os.environ.get("KICAD10_FOOTPRINT_DIR", "/usr/share/kicad/footprints")

# Raspberry Pi 4, mounted face down on J21 (female 2x20 socket on this board's component side), so the Pi's
# USB / Ethernet end hangs past the right edge. Pi frame: 85 x 56, holes at 3.5 / 61.5 x 3.5 / 52.5, header pin 1
# at (8.37, 4.77) from the corner away from USB, header rows 3.5 mm from the long edge (HAT mechanical spec).
PI_X0 = W - 64.5               # USB / Ethernet start about 65 mm from the Pi's left edge: keep them off the board
PI_YE = 152.0                  # Pi long edge at the header (the lower edge, Pi face down)

MCU_X, MCU_Y = 44.0 - 5.6, 26.0 - 3.8   # RP2354B pin 1 (QFN-80 centre at 44, 26)
J19_X = 45.6                             # USB-C centre on the top edge, data pads above RP2354B pins 66/67

KK_ROW1 = 221.73               # original J1/J2/J3 pin row, 10.03 mm above the bottom edge
KK_ROW2 = KK_ROW1 - 20.32      # second stacked row

# ref: (x, y, rotation) of pin 1. KK-396 rotations put the friction ramp toward the board centre, as on the original.
FIXED = {
    # left edge: unchanged from the original board
    "J9":  (12.70, 52.07, 180),
    "J12": (10.03, 103.51, 90),
    "J6":  (10.03, 163.83, 90),
    "J13": (10.03, 208.28, 90),
    # bottom edge: J3 unchanged, J2 and J1 moved left into a second row (order J3 / J2 / J1 kept left to right)
    "J3":  (85.09, KK_ROW1, 180),
    "J2":  (75.85, KK_ROW2, 180),
    "J1":  (115.57, KK_ROW2, 180),
    # top edge: J11 unchanged, J10 audio moved left next to it
    "J11": (58.41, 11.18, 0),
    "J10": (85.00, 11.18, 0),
    "J17": (114.50, 18.00, 270),   # external +5 V terminal block, wires enter from the right edge
    "J22": (115.00, 30.00, 270),   # second speaker connector (stereo pairs)
    # right edge: DMD moved from x 211.4 to the new right edge, same height and orientation
    "J5":  (115.57, 176.46, 180),
    "J18": (116.50, 193.00, 90),   # GI dimmer header
    "U4":  (MCU_X, MCU_Y, 0),      # RP2354B (pad 1), near J9 and J19
    "J21": (PI_X0 + 8.37, PI_YE - 4.77, 90),
}

# packing areas (x0, y0, x1, y1[, "low"]); "low" areas (under the Pi or its plugs) take only low parts
LOW = "low"
UNDER_PI = (58, 98, 118, 135, LOW)
REGIONS = {
    "power.kicad_sch":          [(55, 17, 107, 31), (55, 31, 75, 47), (58, 67, 84, 95, LOW)],
    "io_bus.kicad_sch":         [(17, 21, 33.8, 59)],
    "audio.kicad_sch":          [(84, 67, 112, 95, LOW), (75, 31, 110, 62), (55, 47, 75, 62), UNDER_PI],
    "sw_rows_9.kicad_sch":      [(17, 60, 55, 104)],
    "sw_rows_1.kicad_sch":      [(17, 128, 55, 168), UNDER_PI],
    "display_gi.kicad_sch":     [(84, 154, 108.5, 169), UNDER_PI],
    "sw_columns.kicad_sch":     [(84, 170, 108.5, 196), (100, 208, 119, 229)],
    "sw_dedicated_2.kicad_sch": [(17, 170, 51, 197), (57, 154, 83, 168), UNDER_PI],
    "sw_dedicated_1.kicad_sch": [(52, 170, 83, 196), (17, 211, 45, 229), UNDER_PI],
    "mcu_misc":                 [(34, 38, 56, 59)],
    "pi_if":                    [(60, 136, 112, 143, LOW)],
    "rtc":                      [(17, 104.5, 55, 127)],
}
GROUP_OF = {r: "mcu_misc" for r in ("U5", "R9", "SW1", "SW2", "R15", "J20", "D3", "R17", "R10", "R11", "R12")}
GROUP_OF.update({r: "pi_if" for r in ("R18", "R19", "R20", "R21", "R22")})
GROUP_OF.update({r: "rtc" for r in ("U25", "BT1")})
GROUP_OF.update({r: "mcu_misc" for r in ("TP8", "TP9", "TP10")})
TALL = ("Capacitor_SMD:CP_Elec", "Package_TO_SOT_THT", "TerminalBlock", "Battery", "Button_Switch_THT",
        "Connector_", "Relay")
# RP2354B parts that sit on one of its pins, in placement order: (ref, pad of U4)
U4_SATS = [("L1", "63"), ("C11", "61"), ("R8", "61"), ("R13", "66"), ("R14", "67"), ("C24", "65")]
SUPPLY = ("+3V3", "+1V1", "+5V", "+4V5", "+12V", "-12V", "+3V3_A")

HOLES = [
    # (name, x, y, kind) screw positions from docs/mechanical; keyholes open upward
    ("MH6", 8.24, 6.27, "keyhole"),
    ("MH3", 8.24, 215.17, "keyhole"),
    ("MH7", 8.25, 116.84, "round"),
    ("MH5", 109.20, 6.98, "round"),
    ("MH4", 97.14, 222.86, "round"),
    # Pi 4 standoffs (M2.5)
    ("MH9", PI_X0 + 3.5, PI_YE - 3.5, "pi"),
    ("MH10", PI_X0 + 61.5, PI_YE - 3.5, "pi"),
    ("MH11", PI_X0 + 3.5, PI_YE - 52.5, "pi"),
    ("MH12", PI_X0 + 61.5, PI_YE - 52.5, "pi"),
]


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(ORIGIN_X + x), mm(ORIGIN_Y + y))


# --- netlist -------------------------------------------------------------------------------------------------------
def sexp(s):
    st = [[]]
    for t in re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s):
        if t == "(":
            st.append([])
        elif t == ")":
            x = st.pop()
            st[-1].append(x)
        else:
            st[-1].append(t[1:-1] if t.startswith('"') else t)
    return st[0][0]


def find(lst, k):
    return [x for x in lst if isinstance(x, list) and x and x[0] == k]


def one(lst, k):
    r = find(lst, k)
    return r[0] if r else None


def load_netlist(path):
    t = sexp(open(path).read())
    comps = {}
    for c in find(one(t, "components"), "comp"):
        props = {one(p, "name")[1]: (one(p, "value") or [None, ""])[1] for p in find(c, "property")}
        sp = one(c, "sheetpath")
        comps[one(c, "ref")[1]] = dict(
            value=one(c, "value")[1], fp=one(c, "footprint")[1], sheet=props.get("Sheetfile"),
            sheetname=props.get("Sheetname"), path=one(sp, "tstamps")[1] + one(c, "tstamps")[1])
    nets = [(one(n, "name")[1], [(one(x, "ref")[1], one(x, "pin")[1]) for x in find(n, "node")])
            for n in find(one(t, "nets"), "net")]
    return comps, nets


# --- board ---------------------------------------------------------------------------------------------------------
def edge_rect(board, x0, y0, x1, y1, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(pt(x0, y0))
    s.SetEnd(pt(x1, y1))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)


def text(board, s, x, y, layer, size=1.5):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(t)


def board_only(fp):
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM
                     | pcbnew.FP_EXCLUDE_FROM_POS_FILES)


def npth(fp, shape, size, offset=(0, 0)):
    p = pcbnew.PAD(fp)
    p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    p.SetShape(shape)
    p.SetSize(pcbnew.VECTOR2I(mm(size[0]), mm(size[1])))
    p.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE if shape == pcbnew.PAD_SHAPE_CIRCLE
                    else pcbnew.PAD_DRILL_SHAPE_OBLONG)
    p.SetDrillSize(pcbnew.VECTOR2I(mm(size[0]), mm(size[1])))
    p.SetLayerSet(p.UnplatedHoleMask())
    p.SetNumber("")
    fp.Add(p)
    p.SetFPRelativePosition(pcbnew.VECTOR2I(mm(offset[0]), mm(offset[1])))
    return p


def keyhole(board, name, x, y):
    """Keyhole opening upward: screw at (x, y), 10.4 mm clearance circle 7.42 mm below it, 4.4 mm slot."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(name)
    fp.SetValue("Keyhole")
    fp.SetFPID(pcbnew.LIB_ID("sam_cpu", "Keyhole_SAM"))
    board.Add(fp)
    fp.SetPosition(pt(x, y))
    npth(fp, pcbnew.PAD_SHAPE_CIRCLE, (10.4, 10.4), (0, 7.42))
    npth(fp, pcbnew.PAD_SHAPE_OVAL, (4.4, 7.42 + 4.4), (0, 3.71))
    c = pcbnew.PCB_SHAPE(fp)
    c.SetShape(pcbnew.SHAPE_T_CIRCLE)
    c.SetLayer(pcbnew.F_CrtYd)
    c.SetWidth(mm(0.05))
    fp.Add(c)
    c.SetCenter(pt(x, y + 7.42))
    c.SetEnd(pt(x + 5.7, y + 7.42))
    board_only(fp)
    fp.Reference().SetPosition(pt(x + 7, y))
    fp.Value().SetVisible(False)
    return fp


def load_fp(libref):
    lib, name = libref.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
    if fp is None:
        sys.exit("missing footprint " + libref)
    return fp


def courtyard(fp):
    try:
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if bb.GetWidth() > 0:
            return bb
    except Exception:
        pass
    return fp.GetBoundingBox(False)


def box(fp, grow=0.0):
    """courtyard box in board mm: (x0, y0, x1, y1)"""
    bb = courtyard(fp)
    return (pcbnew.ToMM(bb.GetX()) - ORIGIN_X - grow, pcbnew.ToMM(bb.GetY()) - ORIGIN_Y - grow,
            pcbnew.ToMM(bb.GetRight()) - ORIGIN_X + grow, pcbnew.ToMM(bb.GetBottom()) - ORIGIN_Y + grow)


def overlaps(a, b, gap=0.15):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def is_tall(fp):
    lib = fp.GetFPID().GetLibNickname().wx_str() + ":" + fp.GetFPID().GetLibItemName().wx_str()
    return lib.startswith(TALL)


def move_box_to(fp, x, y):
    """move so the courtyard's top-left lands at board (x, y)"""
    bb = courtyard(fp)
    pos = fp.GetPosition()
    fp.SetPosition(pcbnew.VECTOR2I(pos.x + mm(ORIGIN_X + x) - bb.GetX(), pos.y + mm(ORIGIN_Y + y) - bb.GetY()))


def pack(fps, rects, occ, margin=None, gap=0.6):
    """Shelf-pack footprints (tallest first) into the rectangles, skipping anything already on the board;
    margin[ref] keeps a free ring around a part (room for its decoupling capacitors). Rectangles marked LOW take
    only low parts. Returns the refs that did not fit."""
    margin = margin or {}
    def size(f):
        b, m = box(f), margin.get(f.GetReference(), 0.0)
        return b[2] - b[0] + 2 * m, b[3] - b[1] + 2 * m
    order = sorted(fps, key=lambda f: (-size(f)[1], -size(f)[0], f.GetReference()))
    state = [None] * len(rects)          # per rectangle: (cx, cy, shelf)
    left = []
    for f in order:
        w, h = size(f)
        m = margin.get(f.GetReference(), 0.0)
        done = False
        for i in range(len(rects)):
            r = rects[i]
            if len(r) > 4 and is_tall(f):
                continue
            x0, y0, x1, y1 = r[:4]
            cx, cy, shelf = state[i] or (x0, y0, 0.0)
            while True:
                if cx + w > x1:
                    cx, cy, shelf = x0, cy + shelf + gap, 0.0
                if cy + h > y1:
                    break
                ring = (cx, cy, cx + w, cy + h)
                if occ.free(ring, reserved=True):
                    move_box_to(f, cx + m, cy + m)
                    occ.add(f)
                    occ.reserve(ring)
                    state[i] = (cx + w + gap, cy, max(shelf, h))
                    done = True
                    break
                cx += 1.0
            if done:
                break
            state[i] = (cx, cy, shelf)
        if not done:
            left.append(f.GetReference())
    return left


class Occupancy:
    """Courtyards already on the board, plus the rings packing keeps free around ICs for their capacitors."""
    def __init__(self):
        self.boxes, self.rings = [], []

    def add(self, fp):
        self.boxes.append(box(fp))

    def reserve(self, b):
        self.rings.append(b)

    def free(self, b, reserved=False):
        if b[0] < 0.3 or b[1] < 0.3 or b[2] > W - 0.3 or b[3] > H - 0.3:
            return False
        if any(overlaps(b, o) for o in self.boxes):
            return False
        return not (reserved and any(overlaps(b, o) for o in self.rings))


def pad_xy(pad):
    p = pad.GetPosition()
    return pcbnew.ToMM(p.x) - ORIGIN_X, pcbnew.ToMM(p.y) - ORIGIN_Y


def place_satellite(fp, ic, pad, occ, toward_pad="1"):
    """Put a 2-pad part just outside the IC side where `pad` sits, its pad `toward_pad` facing the IC.
    Slides along the side, then outward, until the courtyard is free."""
    b = box(ic)
    px, py = pad_xy(pad)
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    dx, dy = (px - cx) / (b[2] - b[0]), (py - cy) / (b[3] - b[1])
    if abs(dx) >= abs(dy):
        out, edge, rot = ((1, 0), b[2], 0) if dx > 0 else ((-1, 0), b[0], 180)
    else:
        out, edge, rot = ((0, 1), b[3], 270) if dy > 0 else ((0, -1), b[1], 90)
    fp.SetOrientationDegrees(rot)
    pads = {p.GetNumber(): p for p in fp.Pads()}
    if toward_pad == "2":
        fp.SetOrientationDegrees((rot + 180) % 360)
    tan = (-out[1], out[0])
    for k in range(20):                      # outward rows
        for j in [0] + [s * i for i in range(1, 12) for s in (1, -1)]:
            fp.SetPosition(pcbnew.VECTOR2I(0, 0))
            fb = box(fp)
            half_out = (fb[2] - fb[0]) / 2 if out[0] else (fb[3] - fb[1]) / 2
            d = 0.1 + half_out + k * 1.0
            if out[0]:
                x, y = edge + out[0] * d, py + tan[1] * j * 0.9
            else:
                x, y = px + tan[0] * j * 0.9, edge + out[1] * d
            # centre the courtyard on (x, y)
            ccx, ccy = (fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2
            fp.SetPosition(pcbnew.VECTOR2I(mm(x - ccx), mm(y - ccy)))
            if occ.free(box(fp)):
                occ.add(fp)
                return True
    return False


def main(netfile, out):
    comps, nets = load_netlist(netfile)
    board = pcbnew.BOARD()
    board.SetFileName(out)
    ds = board.GetDesignSettings()
    ds.SetAuxOrigin(pt(0, 0))
    ds.SetGridOrigin(pt(0, 0))
    board.SetCopperLayerCount(2)

    netinfo = {}
    for name, _ in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        netinfo[name] = n
    padnet = {(r, p): name for name, nodes in nets for r, p in nodes}

    fps = {}
    for ref, c in sorted(comps.items()):
        fp = load_fp(c["fp"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetFPID(pcbnew.LIB_ID(*c["fp"].split(":")))
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetSheetname(c["sheetname"] or "")
        fp.SetSheetfile(c["sheet"] or "")
        board.Add(fp)
        for pad in fp.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        fps[ref] = fp

    for ref, (x, y, rot) in FIXED.items():
        fp = fps[ref]
        fp.SetOrientationDegrees(rot)
        # pin 1 at (x, y); footprint origin for parts without a pad "1" (USB-C)
        p1 = [p for p in fp.Pads() if p.GetNumber() == "1"]
        off = p1[0].GetPosition() - fp.GetPosition() if p1 else pcbnew.VECTOR2I(0, 0)
        fp.SetPosition(pt(x, y) - off)
        fp.SetLocked(ref.startswith("J"))

    # USB-C on the top edge above the RP2354B (rotated so the plug enters from the top edge)
    j19 = fps["J19"]
    j19.SetOrientationDegrees(180)
    j19.SetPosition(pt(J19_X, 10))
    jb = box(j19)
    j19.SetPosition(pt(J19_X, 10 - jb[1] - 0.2))
    j19.SetLocked(True)

    occ = Occupancy()
    placed = set(FIXED) | {"J19"}
    for r in placed:
        occ.add(fps[r])
    # holes first, so nothing lands on them
    hole_fps = []
    for name, x, y, kind in HOLES:
        if kind == "keyhole":
            fp = keyhole(board, name, x, y)
        else:
            lib = ("MountingHole:MountingHole_4.3mm_M4_Pad" if kind == "round"
                   else "MountingHole:MountingHole_2.7mm_M2.5")
            fp = load_fp(lib)
            fp.SetReference(name)
            fp.SetFPID(pcbnew.LIB_ID(*lib.split(":")))
            board.Add(fp)
            fp.SetPosition(pt(x, y))
            board_only(fp)
        fp.SetLocked(True)
        occ.add(fp)

    netof = {(r, p): n for (r, p), n in padnet.items()}
    def pad(ref, num):
        return [p for p in fps[ref].Pads() if p.GetNumber() == num][0]

    # RP2354B: regulator, USB, decoupling and crystal on their pins
    u4 = fps["U4"]
    for ref, num in U4_SATS:
        net = netof[(ref, "1")]
        toward = "1" if net == padnet[("U4", num)] or ref == "R8" else "2"
        if ref == "R8":           # R8 is +3V3 -> VREG_AVDD: its VREG_AVDD end faces the chip
            toward = "2"
        place_satellite(fps[ref], u4, pad("U4", num), occ, toward)
        placed.add(ref)
    u4_supply = {}
    for p in u4.Pads():
        n = padnet.get(("U4", p.GetNumber()))
        if n in ("+3V3", "+1V1"):
            u4_supply.setdefault(n, []).append(p)
    used = {}
    for ref in sorted((r for r in comps if comps[r]["sheet"] == "mcu.kicad_sch" and r.startswith("C")),
                      key=lambda r: int(r[1:])):
        if ref in placed or ref == "C119" or netof.get((ref, "2")) != "GND" or netof.get((ref, "1")) not in u4_supply:
            continue
        cands = sorted(u4_supply[netof[(ref, "1")]], key=lambda p: used.get(p.GetNumber(), 0))
        used[cands[0].GetNumber()] = used.get(cands[0].GetNumber(), 0) + 1
        place_satellite(fps[ref], u4, cands[0], occ, "1")
        placed.add(ref)
    for ref, num, toward in (("Y1", "30", "1"), ("C28", "30", "1"), ("R16", "31", "2"), ("C29", "31", "1")):
        place_satellite(fps[ref], u4, pad("U4", num), occ, toward)
        placed.add(ref)

    # decoupling capacitors of the other ICs: placed on their supply pins after packing
    decaps = {}
    for ref, c in comps.items():
        if ref in placed or not ref.startswith("C") or c["fp"].startswith("Capacitor_SMD:CP_"):
            continue
        n1, n2 = netof.get((ref, "1")), netof.get((ref, "2"))
        sup = n1 if n2 == "GND" else n2 if n1 == "GND" else None
        if sup not in SUPPLY:
            continue
        ics = [(r, p) for (r, p), n in padnet.items() if n == sup and r.startswith("U") and r != "U4"
               and comps[r]["sheet"] == c["sheet"]]
        if ics:
            decaps[ref] = (sup, "1" if sup == n1 else "2", ics)
    ic_margin = {r: (1.2 if comps[r]["fp"].startswith("Package_TO_SOT_THT") else 2.2)
                 for r in comps if r.startswith("U")}

    groups = {}
    for ref, c in comps.items():
        if ref in placed or ref in decaps:
            continue
        groups.setdefault(GROUP_OF.get(ref, c["sheet"]), []).append(fps[ref])
    for g in ("mcu_misc", "pi_if", "rtc"):
        left = pack(groups.pop(g), REGIONS[g], occ, ic_margin)
        if left:
            print("did not fit, %s: %s" % (g, " ".join(left)))
    for g, members in sorted(groups.items()):
        left = pack(members, REGIONS[g], occ, ic_margin)
        if left:
            print("did not fit, %s: %s" % (g, " ".join(left)))
    count = {}
    for ref, (sup, toward, ics) in sorted(decaps.items(), key=lambda kv: int(kv[0][1:])):
        ics.sort(key=lambda rp: (count.get(rp[0], 0), rp[0]))
        ic, num = ics[0]
        count[ic] = count.get(ic, 0) + 1
        if not place_satellite(fps[ref], fps[ic], pad(ic, num), occ, toward):
            print("decap without room:", ref, ic)

    edge_rect(board, 0, 0, W, H, pcbnew.Edge_Cuts, 0.1)
    # Pi body and the space its connectors need, on User.Drawings
    dl = pcbnew.Dwgs_User
    edge_rect(board, PI_X0, PI_YE - 56, PI_X0 + 85, PI_YE, dl, 0.2)
    edge_rect(board, PI_X0 + 64.5, PI_YE - 56, PI_X0 + 87.5, PI_YE, dl, 0.2)
    edge_rect(board, PI_X0, PI_YE - 56 - 30, PI_X0 + 64.5, PI_YE - 56, dl, 0.1)
    text(board, "RASPBERRY PI 4, FACE DOWN ON J21 (11 MM STACK): ONLY PARTS UNDER ~3 MM HERE",
         PI_X0 + 1, PI_YE - 30, dl, 1.0)
    text(board, "PI USB / ETHERNET (OFF BOARD)", PI_X0 + 65.5, PI_YE - 30, dl, 1.0)
    text(board, "PI USB-C / MICRO-HDMI PLUGS: KEEP LOW", PI_X0 + 1, PI_YE - 70, dl, 1.0)
    # original board outline for reference
    edge_rect(board, 0, 0, 219.06, H, pcbnew.Cmts_User, 0.1)
    text(board, "ORIGINAL 520-5246-00 OUTLINE (219.06 x 231.76)", 125, 4, pcbnew.Cmts_User, 2.0)

    board.Save(out)
    print("wrote", out, len(fps), "parts")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

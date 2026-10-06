#!/usr/bin/env python3
"""Build the draft PCB (outline, holes, connectors) from the schematic netlist; other parts go off the board.

Run with KiCad 10's Python (the one that can `import pcbnew`):
    kicad-cli sch export netlist -o /tmp/sam_cpu.net hardware/kicad/sam_cpu/sam_cpu.kicad_sch
    python3 hardware/kicad/tools/place_pcb.py /tmp/sam_cpu.net hardware/kicad/sam_cpu/sam_cpu.kicad_pcb

Coordinates below are board millimetres with the origin at the top-left corner, X right, Y down, seen from the
component side as the board hangs in the backbox: the same frame as docs/mechanical (original board 520-5246-00).
The board is drawn at (ORIGIN_X, ORIGIN_Y) on the page; the grid and drill origins are set to the board corner so
KiCad shows the same numbers as this file.

Only the outline, holes and connectors are placed. Every other part is left off the board, to the right, in one
block per schematic sheet, ready for manual placement. Once the board is edited in KiCad, do not rerun this.
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
PI_YE = 140.0                  # Pi long edge at the header (the lower edge, Pi face down)

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
    "J17": (24.00, 10.00, 0),      # external +5 V terminal block
    # right edge: DMD moved from x 211.4 to the new right edge, same height and orientation
    "J5":  (115.57, 164.46, 180),
    "J18": (116.50, 193.00, 90),   # GI dimmer header
    "J19": (115.50, 176.00, 90),   # USB-C, RP2354B to a Pi USB port
    "J21": (PI_X0 + 8.37, PI_YE - 4.77, 90),
}

# off-board blocks, one per sheet, to the right of the Pi overhang
OFF_X, OFF_W, OFF_H = 150.0, 48.0, 85.0

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


def pack(fps, rects, gap=0.6):
    """Shelf-pack footprints (tallest first) into the rectangles. Returns the refs that did not fit."""
    order = sorted(fps, key=lambda f: (-courtyard(f).GetHeight(), -courtyard(f).GetWidth(), f.GetReference()))
    left = []
    ri, cx, cy, shelf = 0, None, None, 0.0
    for f in order:
        bb = courtyard(f)
        w = pcbnew.ToMM(bb.GetWidth())
        h = pcbnew.ToMM(bb.GetHeight())
        while ri < len(rects):
            x0, y0, x1, y1 = rects[ri]
            if cx is None:
                cx, cy, shelf = x0, y0, 0.0
            if cx + w > x1:
                cx, cy, shelf = x0, cy + shelf + gap, 0.0
            if cy + h <= y1 and cx + w <= x1:
                break
            ri, cx = ri + 1, None
        if ri >= len(rects):
            left.append(f.GetReference())
            continue
        # move so the courtyard's top-left lands at (cx, cy)
        pos = f.GetPosition()
        dx = mm(ORIGIN_X + cx) - bb.GetX()
        dy = mm(ORIGIN_Y + cy) - bb.GetY()
        f.SetPosition(pcbnew.VECTOR2I(pos.x + dx, pos.y + dy))
        cx += w + gap
        shelf = max(shelf, h)
    return left


def main(netfile, out):
    comps, nets = load_netlist(netfile)
    board = pcbnew.BOARD()
    board.SetFileName(out)
    ds = board.GetDesignSettings()
    ds.SetAuxOrigin(pt(0, 0))
    ds.SetGridOrigin(pt(0, 0))
    board.SetCopperLayerCount(4)

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

    groups = {}
    for ref, c in comps.items():
        if ref not in FIXED:
            groups.setdefault(c["sheet"], []).append(fps[ref])
    for i, (sheet, members) in enumerate(sorted(groups.items())):
        x0, y0 = OFF_X + (i % 3) * (OFF_W + 5), (i // 3) * (OFF_H + 5)
        left = pack(members, [(x0, y0, x0 + OFF_W, y0 + OFF_H)])
        if left:
            print("did not fit, sheet %s: %s" % (sheet, " ".join(left)))

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

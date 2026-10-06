#!/usr/bin/env python3
"""Derive connector and mounting-hole positions of the original Stern SAM
CPU/Sound board (520-5246-00 Rev G) from the vector component-layout page of
the manual (docs/reference/Stern_SAM_Manual-CPU_Sound_Board_Schematic.pdf,
page 11).

The layout page is a vector drawing.  The PDF-point coordinates below were
read from its path data with PyMuPDF (page.get_drawings()).  The drawing is
uniformly scaled; the scale is calibrated from connector bodies whose real
length is fixed by their standard:

  J3  KK-396 1x10  93.09 pt = 10 x 3.96 mm
  J2  KK-396 1x12 111.73 pt = 12 x 3.96 mm
  J1  KK-396 1x9   83.79 pt =  9 x 3.96 mm
  J9  2x10 box header 77.57 pt = 33.02 mm (25.4 + 7.62)
  J5  2x7  box header 59.67 pt = 25.40 mm
  J7  2x10 pin field  59.67 pt = 10 x 2.54 mm

All agree on 59.675 pt per inch to within 0.05 %.

Output coordinates: millimetres, origin = top-left corner of the board,
X to the right, Y down (KiCad convention), seen from the component side
with the board as mounted in the backbox (J11 power at the top, switch
connectors on the left and bottom edges).

Usage: python3 sam_cpu_mechanical.py <layout.pdf> <out_dir>
Writes positions.csv, outline.dxf and annotated.png (PyMuPDF + Pillow).
"""
import csv
import math
import os
import sys

PT_PER_IN = 59.675
MM = 25.4 / PT_PER_IN          # mm per PDF point
P396 = 3.96 / MM               # 0.156" pitch in PDF points
P254 = 2.54 / MM

# Board outline (PDF points), page 11
BX0, BY0, BX1, BY1 = 25.54, 36.05, 540.20, 580.55


def mm(x, y):
    return round((x - BX0) * MM, 2), round((y - BY0) * MM, 2)


# KK-396 headers: body rect (x0, y0, x1, y1), pins, pin-1 end, ramp side.
# The friction-ramp strip (a line 3.6 pt inside the body) faces the board
# interior; the pin row is taken as the centre of the body without the ramp.
KK396 = {
    # name: (x0, y0, x1, y1, pins, axis, pin1_end, ramp_pt, ramp_side, function)
    "J1":  (404.40, 545.65, 488.19, 564.74, 9,  "x", "max", 3.58, "min", "Switch drive (rows 1-8 strobes)"),
    "J2":  (275.01, 545.65, 386.75, 564.74, 12, "x", "max", 3.58, "min", "Lower dedicated switch in"),
    "J3":  (137.02, 545.65, 230.11, 564.74, 10, "x", "max", 3.58, "min", "Upper dedicated switch in"),
    "J12": (41.35, 190.80, 60.44, 283.89, 10, "y", "max", 3.58, "max", "Upper switch return (columns 9-16)"),
    "J6":  (41.35, 332.52, 60.44, 425.61, 10, "y", "max", 3.58, "max", "Lower switch return (columns 1-8)"),
    "J13": (41.35, 436.94, 60.44, 530.03, 10, "y", "max", 3.58, "max", "Dedicated switch in (DIP / SW D17-24)"),
    "J11": (158.11, 54.25, 213.50, 75.73, 6, "x", "min", 5.37, "max", "Power in (+5, GND, -12, AGND, AGND, +12)"),
    "J10": (387.84, 48.88, 425.09, 67.98, 4, "x", "min", 3.58, "max", "Audio out"),
}

# 0.1" headers: pin-field rect and pin-1 corner; outer body rect.
HDR = {
    # name: (pin field x0,y0,x1,y1), (body x0,y0,x1,y1), cols, rows, pin1 corner, function
    "J9": ((52.39 - P254 / 2, 131.525 - 4.5 * P254, 52.39 + P254 / 2, 131.525 + 4.5 * P254),
           (41.95, 92.74, 62.83, 170.31), 2, 10, ("max", "max"), "Bus to I/O board (2x10 IDC)"),
    "J5": ((513.35 + P254 / 2, 383.64 + P254 / 2, 525.28 - P254 / 2, 425.41 - P254 / 2),
           (508.87, 374.69, 529.76, 434.36), 2, 7, ("max", "max"), "DMD display (2x7 IDC)"),
    "J7": ((514.84 + P254 / 2, 227.00 + P254 / 2, 526.78 - P254 / 2, 286.67 - P254 / 2),
           (510.07, 219.15, 531.55, 294.58), 2, 10, ("max", "max"), "Processor JTAG (2x10)"),
}
# J9's body centre is the pin-field centre (box header); the rect above is
# built from it.  For J5/J7 the drawn pin field is shrunk by half a pitch to
# get pin centres.

OTHER = {
    "J8":  ((507.38, 326.95, 525.28, 362.75), "Xilinx JTAG (outline only)"),
    "J14": ((462.93, 404.97, 502.31, 436.95), "Serial header (outline only)"),
    "J4":  ((511.36, 442.91, 554.92, 516.21), "DB9 serial, overhangs right edge (outline only)"),
    "J15": ((505.34, 177.97, 540.20, 213.82), "USB-B, opens at right edge (outline only)"),
}

# Mounting holes.  Keyholes: Ø24.4 pt clearance circle with a 10.44 pt slot
# running up; the screw shank rests at the top of the slot (board hangs on
# it).  Round holes: Ø14.87 pt circle in a 23.87 pt square pad.
KEY_DY_SLOT = 68.21 - 50.77     # big-circle centre to slot-end centre
KEYHOLES = {"MH6": (44.905, 68.21), "MH1": (519.29, 68.21),
            "MH3": (44.905, 559.01), "MH2": (519.29, 559.01)}
ROUND = {"MH5": (282.10, 52.44), "MH4": (253.76, 559.65),
         "MH7": (44.93, 310.55), "MH8": (519.32, 310.55)}
KEY_BIG_D, KEY_SLOT_W, ROUND_D, ROUND_PAD = 24.41, 10.44, 14.87, 23.87


def kk_pins(name):
    x0, y0, x1, y1, n, axis, p1, ramp, rside, _ = KK396[name]
    pins = []
    if axis == "x":
        cy = (y0 + ramp + y1) / 2 if rside == "min" else (y0 + y1 - ramp) / 2
        for i in range(n):
            x = x1 - (i + 0.5) * P396 if p1 == "max" else x0 + (i + 0.5) * P396
            pins.append((i + 1, x, cy))
    else:
        cx = (x0 + x1 - ramp) / 2 if rside == "max" else (x0 + ramp + x1) / 2
        for i in range(n):
            y = y1 - (i + 0.5) * P396 if p1 == "max" else y0 + (i + 0.5) * P396
            pins.append((i + 1, cx, y))
    return pins


def hdr_pins(name):
    (fx0, fy0, fx1, fy1), _, cols, rows, _, _ = HDR[name]
    # pin 1 bottom-right (inner column, toward the board centre for J9),
    # odd pins in the right column, numbering upward.
    pins = []
    for r in range(rows):
        y = fy1 - r * P254
        pins.append((2 * r + 1, fx1, y))
        pins.append((2 * r + 2, fx0, y))
    return pins


def rows():
    out = []
    w, h = mm(BX1, BY1)
    out.append(dict(item="BOARD", kind="outline", x_mm=0, y_mm=0, x2_mm=w, y2_mm=h,
                    note="board edge, %.2f x %.2f mm" % (w, h)))
    for name, (cx, cy) in KEYHOLES.items():
        x, y = mm(cx, cy - KEY_DY_SLOT)
        bx, by = mm(cx, cy)
        out.append(dict(item=name, kind="keyhole screw", x_mm=x, y_mm=y, x2_mm=bx, y2_mm=by,
                        note="screw at slot top (x,y); clearance circle centre (x2,y2) D%.1f, slot W%.1f"
                        % (KEY_BIG_D * MM, KEY_SLOT_W * MM)))
    for name, (cx, cy) in ROUND.items():
        x, y = mm(cx, cy)
        out.append(dict(item=name, kind="round hole", x_mm=x, y_mm=y, x2_mm="", y2_mm="",
                        note="circle D%.1f in %.1f mm square pad" % (ROUND_D * MM, ROUND_PAD * MM)))
    for name, v in KK396.items():
        x0, y0, x1, y1 = v[:4]
        a, b = mm(x0, y0)
        c, d = mm(x1, y1)
        out.append(dict(item=name, kind="KK-396 1x%d body" % v[4], x_mm=a, y_mm=b, x2_mm=c, y2_mm=d, note=v[-1]))
        for pin, x, y in kk_pins(name):
            px, py = mm(x, y)
            out.append(dict(item="%s.%d" % (name, pin), kind="pin", x_mm=px, y_mm=py, x2_mm="", y2_mm="", note=""))
    for name, v in HDR.items():
        bx0, by0, bx1, by1 = v[1]
        a, b = mm(bx0, by0)
        c, d = mm(bx1, by1)
        out.append(dict(item=name, kind="%dx%d 2.54 body" % (v[2], v[3]), x_mm=a, y_mm=b, x2_mm=c, y2_mm=d, note=v[-1]))
        for pin, x, y in hdr_pins(name):
            if pin in (1, 2, 2 * v[3] - 1, 2 * v[3]):
                px, py = mm(x, y)
                out.append(dict(item="%s.%d" % (name, pin), kind="pin", x_mm=px, y_mm=py, x2_mm="", y2_mm="", note=""))
    for name, ((x0, y0, x1, y1), note) in OTHER.items():
        a, b = mm(x0, y0)
        c, d = mm(x1, y1)
        out.append(dict(item=name, kind="outline", x_mm=a, y_mm=b, x2_mm=c, y2_mm=d, note=note))
    return out


def write_dxf(path):
    """Minimal R12 DXF: layer EDGE (board), HOLES, CONN (bodies), PINS.
    DXF Y points up, so Y is negated (import into KiCad with origin at the
    board's top-left corner)."""
    ents = []

    def line(layer, x1, y1, x2, y2):
        ents.append("0\nLINE\n8\n%s\n10\n%.3f\n20\n%.3f\n11\n%.3f\n21\n%.3f\n" % (layer, x1, -y1, x2, -y2))

    def circle(layer, x, y, r):
        ents.append("0\nCIRCLE\n8\n%s\n10\n%.3f\n20\n%.3f\n40\n%.3f\n" % (layer, x, -y, r))

    def arc(layer, x, y, r, a0, a1):
        ents.append("0\nARC\n8\n%s\n10\n%.3f\n20\n%.3f\n40\n%.3f\n50\n%.3f\n51\n%.3f\n" % (layer, x, -y, r, a0, a1))

    def rect(layer, x0, y0, x1, y1):
        line(layer, x0, y0, x1, y0); line(layer, x1, y0, x1, y1)
        line(layer, x1, y1, x0, y1); line(layer, x0, y1, x0, y0)

    w, h = mm(BX1, BY1)
    rect("EDGE", 0, 0, w, h)
    R, r = KEY_BIG_D * MM / 2, KEY_SLOT_W * MM / 2
    dslot = KEY_DY_SLOT * MM
    for cx, cy in KEYHOLES.values():
        x, y = mm(cx, cy)
        # clearance circle open at the top where the slot joins
        t = math.degrees(math.asin(r / R))
        arc("HOLES", x, y, R, 90 + t, 360 + 90 - t)
        yj = y - math.sqrt(R * R - r * r)
        line("HOLES", x - r, yj, x - r, y - dslot)
        line("HOLES", x + r, yj, x + r, y - dslot)
        arc("HOLES", x, y - dslot, r, 0, 180)
    for cx, cy in ROUND.values():
        x, y = mm(cx, cy)
        circle("HOLES", x, y, ROUND_D * MM / 2)
    for name, v in KK396.items():
        a, b = mm(*v[:2]); c, d = mm(*v[2:4])
        rect("CONN", a, b, c, d)
        for pin, x, y in kk_pins(name):
            px, py = mm(x, y)
            circle("PINS", px, py, 0.8 if pin > 1 else 1.2)
    for name, v in HDR.items():
        a, b = mm(*v[1][:2]); c, d = mm(*v[1][2:])
        rect("CONN", a, b, c, d)
        for pin, x, y in hdr_pins(name):
            px, py = mm(x, y)
            circle("PINS", px, py, 0.5 if pin > 1 else 0.8)
    for (x0, y0, x1, y1), _ in OTHER.values():
        a, b = mm(x0, y0); c, d = mm(x1, y1)
        rect("CONN", a, b, c, d)
    with open(path, "w") as f:
        f.write("0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n")
        f.write("0\nSECTION\n2\nENTITIES\n" + "".join(ents) + "0\nENDSEC\n0\nEOF\n")


def annotate(pdf, path, table):
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont
    dpi = 300
    s = dpi / 72
    page = pymupdf.open(pdf)[10]
    clip = pymupdf.Rect(BX0 - 20, BY0 - 20, BX1 + 20, BY1 + 20) & page.rect
    pix = page.get_pixmap(dpi=dpi, clip=clip)
    page_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    pad = 420                                   # room for right-edge labels
    img = Image.new("RGB", (pix.width + pad, pix.height), "white")
    img.paste(page_img, (0, 0))
    dr = ImageDraw.Draw(img)
    text = dr.text

    def label(xy, t, fill, font):
        box = dr.textbbox(xy, t, font=font)
        dr.rectangle([box[0] - 3, box[1] - 3, box[2] + 3, box[3] + 3], fill="white", outline=fill)
        text(xy, t, fill=fill, font=font)
    dr.text = label
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except OSError:
        font = ImageFont.load_default()

    def P(x, y):
        return ((x - clip.x0) * s, (y - clip.y0) * s)

    red, blue = (220, 0, 0), (0, 70, 220)
    for name, (cx, cy) in list(KEYHOLES.items()):
        x, y = P(cx, cy - KEY_DY_SLOT)
        dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=red, width=4)
        X, Y = mm(cx, cy - KEY_DY_SLOT)
        dr.text((x + 60, y - 50 if cy > 300 else y + 10), "%s (%.1f, %.1f)" % (name, X, Y), fill=red, font=font)
    for name, (cx, cy) in ROUND.items():
        x, y = P(cx, cy)
        dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=red, width=4)
        X, Y = mm(cx, cy)
        dr.text((x + 30, y - 12), "%s (%.1f, %.1f)" % (name, X, Y), fill=red, font=font)
    for name in KK396:
        for pin, x, y in kk_pins(name):
            px, py = P(x, y)
            rr = 9 if pin == 1 else 5
            dr.ellipse([px - rr, py - rr, px + rr, py + rr], outline=blue, width=3)
        pin, x, y = kk_pins(name)[0]
        X, Y = mm(x, y)
        px, py = P(x, y)
        if KK396[name][5] == "x":
            dr.text((px - 230, py - 95 if y > 300 else py + 40), "%s.1 (%.1f, %.1f)" % (name, X, Y), fill=blue, font=font)
        else:
            dr.text((px + 90, py - 40), "%s.1 (%.1f, %.1f)" % (name, X, Y), fill=blue, font=font)
    for name in HDR:
        pin, x, y = hdr_pins(name)[0]
        px, py = P(x, y)
        dr.ellipse([px - 9, py - 9, px + 9, py + 9], outline=blue, width=3)
        X, Y = mm(x, y)
        if name == "J9":
            dr.text((px + 40, py - 14), "J9.1 (%.1f, %.1f)" % (X, Y), fill=blue, font=font)
        else:
            dr.text((px + 30, py + 40), "%s.1 (%.1f, %.1f)" % (name, X, Y), fill=blue, font=font)
    ox, oy = P(BX0, BY0)
    dr.text((ox + 8, oy - 30), "origin (0,0), X right, Y down, mm", fill=red, font=font)
    img.save(path, optimize=True)


def main():
    pdf, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    table = rows()
    with open(os.path.join(out, "sam_cpu_520-5246-00_positions.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["item", "kind", "x_mm", "y_mm", "x2_mm", "y2_mm", "note"])
        wr.writeheader()
        wr.writerows(table)
    write_dxf(os.path.join(out, "sam_cpu_520-5246-00_outline.dxf"))
    annotate(pdf, os.path.join(out, "sam_cpu_520-5246-00_annotated.png"), table)
    for r in table:
        if r["kind"] != "pin" or r["item"].endswith(".1"):
            print(r)


if __name__ == "__main__":
    main()

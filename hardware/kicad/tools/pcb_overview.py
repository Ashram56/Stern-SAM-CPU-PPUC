#!/usr/bin/env python3
"""Draw the new board over the original 520-5246-00 outline (PNG), from a footprint dump of the .kicad_pcb.

    python3 tools/pcb_dump.py sam_cpu/sam_cpu.kicad_pcb /tmp/fp.json        (KiCad's Python)
    python3 tools/pcb_overview.py /tmp/fp.json docs/mechanical/..._positions.csv sam_cpu/pcb_overview.png
"""
import csv
import json
import sys

from PIL import Image, ImageDraw, ImageFont

S = 6.0          # px per mm
M = 40           # margin px
W_NEW, H = 120.65, 231.76
PI_X0, PI_YE = W_NEW - 64.5, 152.0
MOVED = {"J1": "J1", "J2": "J2", "J10": "J10", "J5": "J5"}
HEATSINK = (59.0, 41.0, 107.0, 54.0)


def P(x, y):
    return (M + x * S, M + 30 + y * S)


def main(fpjson, poscsv, out):
    fps = {f["ref"]: f for f in json.load(open(fpjson))}
    orig = {r["item"]: r for r in csv.DictReader(open(poscsv)) if r["kind"] != "pin"}
    img = Image.new("RGB", (int(2 * M + 226 * S), int(2 * M + 30 + H * S)), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    d.text((M, 8), "Placement draft (green, 120.65 x 231.76 mm) over the original 520-5246-00 "
           "(grey, 219.06 x 231.76 mm)", fill="black", font=font)

    # original board, its connectors and holes
    d.rectangle([P(0, 0), P(219.06, H)], outline=(150, 150, 150), width=3)
    for k, r in orig.items():
        if k == "BOARD":
            continue
        if r["kind"].startswith(("KK", "2x", "outline")):
            d.rectangle([P(float(r["x_mm"]), float(r["y_mm"])), P(float(r["x2_mm"]), float(r["y2_mm"]))],
                        outline=(170, 170, 170), fill=(238, 238, 238), width=2)
            d.text(P(float(r["x_mm"]) + 0.5, float(r["y_mm"]) - 4), k + " (orig)", fill=(120, 120, 120), font=small)
        else:
            x, y = float(r["x_mm"]), float(r["y_mm"])
            d.ellipse([P(x - 2.5, y - 2.5), P(x + 2.5, y + 2.5)], outline=(170, 170, 170), width=2)
            d.text(P(x + 3.5, y - 1.5), k, fill=(120, 120, 120), font=small)

    # new board
    d.rectangle([P(0, 0), P(W_NEW, H)], outline=(0, 120, 60), fill=(225, 242, 230), width=4)
    # Pi
    d.rectangle([P(PI_X0, PI_YE - 86), P(PI_X0 + 64.5, PI_YE - 56)], outline=(90, 120, 200), width=1,
                fill=(232, 238, 252))
    d.rectangle([P(PI_X0, PI_YE - 56), P(PI_X0 + 85, PI_YE)], outline=(40, 80, 200), width=3)
    d.rectangle([P(PI_X0 + 64.5, PI_YE - 56), P(PI_X0 + 87.5, PI_YE)], outline=(40, 80, 200), width=2,
                fill=(215, 225, 250))
    d.text(P(PI_X0 + 2, PI_YE - 53), "Raspberry Pi 4, face down on J21", fill=(40, 80, 200), font=small)
    d.text(P(PI_X0 + 2, PI_YE - 49), "(~11 mm stack: low parts only below)", fill=(40, 80, 200), font=small)
    d.text(P(PI_X0 + 65.5, PI_YE - 30), "USB/ETH", fill=(40, 80, 200), font=small)
    d.text(P(PI_X0 + 65.5, PI_YE - 26), "off board", fill=(40, 80, 200), font=small)
    d.text(P(PI_X0 + 2, PI_YE - 84), "Pi USB-C / micro-HDMI plug space", fill=(90, 120, 200), font=small)

    d.rectangle([P(*HEATSINK[:2]), P(*HEATSINK[2:])], outline=(200, 90, 0), width=2, fill=(250, 232, 210))
    d.text(P(HEATSINK[0] + 1, HEATSINK[1] + 1), "heatsink for U23 / U24", fill=(170, 70, 0), font=small)
    for ref, f in fps.items():
        if f["x0"] > W_NEW + 10:
            continue  # parts waiting off the board
        conn = ref.startswith(("J", "SW")) or ref in ("U4", "U23", "U24")
        hole = ref.startswith("MH")
        if not hole:
            d.rectangle([P(f["x0"], f["y0"]), P(f["x1"], f["y1"])],
                        outline=(0, 90, 40) if conn else (120, 160, 130),
                        fill=(170, 220, 185) if conn else None, width=2 if conn else 1)
        for x, y, w, h, num, np_ in f["pads"]:
            if hole:
                d.ellipse([P(x - w / 2, y - h / 2), P(x + w / 2, y + h / 2)], fill=(200, 30, 30))
            elif conn and ref.startswith("J"):
                c = (200, 120, 0) if num == "1" else (60, 60, 60)
                d.ellipse([P(x - 0.8, y - 0.8), P(x + 0.8, y + 0.8)], fill=c)
        if conn or hole:
            lx, ly = (f["x1"] + 1, f["y0"]) if not hole else (f["x1"] + 0.5, f["y0"] - 1)
            if ref in ("J12", "J6", "J13", "J9"):
                lx = f["x1"] + 1
            d.text(P(lx, ly), ref, fill=(0, 70, 30) if not hole else (200, 30, 30), font=font)
    # arrows from original to new position for the moved connectors
    for ref in MOVED:
        r, f = orig[ref], fps[ref]
        a = P((float(r["x_mm"]) + float(r["x2_mm"])) / 2, (float(r["y_mm"]) + float(r["y2_mm"])) / 2)
        b = P((f["x0"] + f["x1"]) / 2, (f["y0"] + f["y1"]) / 2)
        d.line([a, b], fill=(220, 100, 0), width=3)
        d.ellipse([b[0] - 6, b[1] - 6, b[0] + 6, b[1] + 6], fill=(220, 100, 0))
    for i, line in enumerate(["Orange dot = pin 1, orange line = connector moved",
                              "Red = holes: keyholes MH6/MH3 and round MH7/MH5/MH4",
                              "on original screw positions, MH9-12 Pi standoffs"]):
        d.text(P(124, 200 + 4 * i), line, fill="black", font=small)
    img.save(out)


if __name__ == "__main__":
    main(*sys.argv[1:4])

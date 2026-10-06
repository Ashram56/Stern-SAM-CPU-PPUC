# PCB placement draft (0.2)

`sam_cpu/sam_cpu.kicad_pcb` has the board outline, the mounting holes, the connectors and a first placement of all
429 parts, on **2 copper layers**. Nothing is routed. It matches the schematic (KiCad schematic parity: 0 footprint
errors) and has no courtyard overlaps.

![Overview](sam_cpu/pcb_overview.png)

`sam_cpu/pcb_overview.png` shows the new board over the original 520-5246-00 outline, with arrows for the
connectors that moved. `sam_cpu/pcb_render.png` is KiCad's top render.

Coordinates are millimetres from the top-left board corner, Y down, component side, as the board hangs in the
backbox (same frame as `docs/mechanical/`). KiCad's grid and drill origins are set to that corner.

## Outline

**120.65 x 231.76 mm** (4.75 x 9.125 in), 55 % of the original 219.06 mm width. Height and the left edge are
unchanged. The width is set by three things: the Pi's USB/Ethernet end must hang past the right edge, the round
hole MH5 at X 109.2 is kept, and the J2 + J1 row needs about 88 mm. 2 copper layers.

## Mounting holes

All on original backbox screw positions (`docs/mechanical/README.md`):

| Hole | Type | Screw X, Y |
|---|---|---|
| MH6 | keyhole, opens upward, top-left | 8.24, 6.27 |
| MH3 | keyhole, opens upward, bottom-left | 8.24, 215.17 |
| MH7 | round, left middle | 8.25, 116.84 |
| MH5 | round, top | 109.20, 6.98 |
| MH4 | round, bottom | 97.14, 222.86 |
| MH9-MH12 | M2.5, Raspberry Pi 4 standoffs | 59.65 / 117.65, 99.5 / 148.5 |

The original right-hand holes (MH1, MH8, MH2) fall outside the narrower board. The round holes use a 4.3 mm plated
pad (M4) until the real screw is measured.

## Connectors (pin 1 position)

| Conn | Function | Pin 1 X, Y | Original pin 1 | Change |
|---|---|---|---|---|
| J9 | IO bus 2x10 | 12.70, 52.07 | same | none |
| J12 | switch returns 9-16 | 10.03, 103.51 | same | none |
| J6 | switch returns 1-8 | 10.03, 163.83 | same | none |
| J13 | dedicated 17-24 | 10.03, 208.28 | same | none |
| J3 | dedicated in (upper) | 85.09, 221.73 | same | none |
| J2 | dedicated in (lower), 12 pin | 75.85, 201.41 | 151.77, 221.73 | 76 mm left, second row 20.3 mm up |
| J1 | switch strobes, 9 pin | 115.57, 201.41 | 194.94, 221.73 | 79 mm left, second row 20.3 mm up |
| J11 | power in | 58.41, 11.18 | same | none |
| J10 | speakers | 85.00, 11.18 | 156.19, 8.76 | 71 mm left |
| J5 | DMD 2x7 | 115.57, 176.46 | 211.44, 164.46 | 96 mm left, 12 mm down |
| J22 | second speaker connector (L+ L- R+ R-) | 115.0, 30.0 | new | right edge |
| J17 | external +5 V terminal, wires from the right edge | 114.5, 18.0 | new | |
| J18 | GI dimmer header | 116.5, 193.0 | new | |
| J19 | USB-C to the Pi, on the top edge | centre X 45.6 | new | 13 mm from the RP2354B USB pins |
| J21 | Raspberry Pi 40-pin socket | 64.52, 147.23 | new | |

The KK-396 headers keep the original orientation: pin 1 at the bottom of the left-edge connectors and at the right
end of the bottom ones, friction ramp toward the board centre. J3 stays in the bottom row; J2 and J1 form a second
row above it, keeping the left-to-right order J3 / J2 / J1 so the harness branches do not cross.

## Raspberry Pi 4

Assumed mounted **face down** on J21 (female 2x20 socket on this board), about 11 mm above the board, with its
USB/Ethernet end hanging past the right edge and its micro-SD card facing out. Under the Pi only low SMD parts
(under ~3 mm) can go. Its USB-C and micro-HDMI plugs point toward the top of the board; the area above the Pi is
for low parts only. If you prefer the Pi face up on a ribbon cable, J21 becomes a 2x20 box header and the
board could lose about 10 mm of width.

## Placement

- **RP2354B (U4)** sits at (44, 26), right next to the bus buffers and J9. The USB-C J19 is on the top edge
  above it: 13 mm from the connector's D+/D- pads to the chip's USB pins, with the 27 R series resistors in
  between, so the USB pair can be routed short on 2 layers without impedance control.
- Around U4, each 100 nF sits on its own IOVDD / DVDD pin, the regulator inductor L1 and the VREG_AVDD filter
  (R8, C11) are on the regulator pins (61-65), and the crystal with its load capacitors and 1 k sits on XIN / XOUT.
  Reset and BOOTSEL buttons, the SWD header J20 and the status LED are just below.
- Every other IC has its decoupling capacitor on its supply pin. The rest is grouped by schematic sheet next to its
  connector: power under J11 (power-path parts toward J17), bus buffers beside J9, switch inputs beside J12, J6,
  J13, J2/J3 and J1, DMD driver beside J5, audio amplifiers under J10 next to J22.
- The RTC and its CR2032 holder are at the left middle, reachable without removing the Pi.
- The Pi was moved down 12 mm (and J5 with it) to leave room for the audio parts above its plug area. Only low
  parts (SMD, no electrolytics or TO-220) are placed under the Pi and under its USB-C / micro-HDMI plugs.
- This is a first pass made by a script: expect to tighten the U4 area, rotate parts for routing, and spread the
  dense resistor blocks once routing starts.

## Checks

- `kicad-cli pcb drc --schematic-parity` (KiCad 10.0.6): 0 footprint errors, no courtyard overlaps, no shorts,
  no hole clearance issues. The remaining reports are expected before routing: unconnected pads, overlapping
  reference designators, and the keyhole footprints coming from an in-board library.

## To confirm

- The measurements listed in `docs/mechanical/README.md` (board size, KK pin row from the edge, screws in the round
  holes and their diameter).
- Pi orientation (face down on the socket, or face up on a ribbon).
- Whether the TDA2030A amplifiers need a heatsink at the volume you run.
- Harness reach for J1, J2, J5 and J10 at their new positions.

## How it was generated

```
kicad-cli sch export netlist -o /tmp/sam_cpu.net sam_cpu/sam_cpu.kicad_sch
python3 tools/place_pcb.py /tmp/sam_cpu.net sam_cpu/sam_cpu.kicad_pcb      # KiCad 10's Python (import pcbnew)
python3 tools/pcb_dump.py sam_cpu/sam_cpu.kicad_pcb /tmp/fp.json           # KiCad 10's Python
python3 tools/pcb_overview.py /tmp/fp.json <docs/mechanical positions CSV> sam_cpu/pcb_overview.png
```

From now on edit the board in KiCad; rerunning `place_pcb.py` overwrites it.

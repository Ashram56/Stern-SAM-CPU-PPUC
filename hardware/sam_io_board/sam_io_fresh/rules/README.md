# JLCPCB manufacturing rules (2-layer and 4-layer)

Compiled 2026-10-08 for the SAM CPU PPUC board (4 layers) and the SAM_IO standalone board (2 layers).

**Source:** JLCPCB PCB capabilities, https://jlcpcb.com/capabilities/pcb-capabilities
(standard process, FR-4, 1 oz outer copper, 0.5 oz inner copper on 4-layer, 1.6 mm).

**How these numbers were obtained.** jlcpcb.com is blocked from the cloud sandbox, so the page
could not be read directly. Values come from search-engine extracts of that page and of JLCPCB's
own help and blog pages (BGA guide, via-in-pad page, silkscreen guidance), cross-checked against the
community rule set [labtroll/KiCad-DesignRules](https://github.com/labtroll/KiCad-DesignRules)
(`JLCPCB/JLCPCB.kicad_dru`), which the files here start from. The "Confidence" column says which
numbers were confirmed that way and which are from the older page layout. Before ordering, open the
live page once and check the rows marked *verify*.

## Values

| Item | 2-layer | 4-layer | Confidence |
|---|---|---|---|
| Min track width, outer (1 oz) | 0.10 mm (4 mil) | 0.09 mm (3.5 mil) | confirmed |
| Min track spacing, outer (1 oz) | 0.10 mm | 0.09 mm | confirmed |
| Min track width / spacing, inner (0.5 oz) | n/a | 0.09 mm / 0.09 mm | confirmed (3.5 mil for 4-6 layers) |
| 2 oz copper track/space | 0.16 / 0.16 mm | 0.15 / 0.15 mm | confirmed |
| Via drill, absolute min | 0.15 mm (pad 0.25 mm) | 0.15 mm (pad 0.25 mm) | confirmed; older page said 0.3/0.5 mm for 2-layer |
| Via drill with no surcharge | 0.3 mm (pad 0.4-0.45 mm) | 0.3 mm | *verify* (pricing, not capability) |
| Via pad vs drill | pad >= drill + 0.10 mm (0.15 mm preferred) | same | confirmed |
| Min plated hole (PTH) | 0.20 mm | 0.20 mm | confirmed |
| PTH annular ring | 0.15 mm min (enlarged to this in production), 0.25 mm recommended | same | confirmed |
| Max drill | 6.3 mm | 6.3 mm | confirmed |
| Min NPTH | 0.5 mm | 0.5 mm | community set |
| Plated slot min width | 0.5 mm | 0.5 mm | community set |
| Non-plated slot min width | 1.0 mm | 1.0 mm | community set |
| Hole to hole, via to via | 0.2 mm | 0.2 mm | confirmed |
| Hole to hole, pad holes | 0.45 mm | 0.45 mm | confirmed |
| Hole to hole, different nets | 0.5 mm | 0.5 mm | community set, *verify* |
| Via hole to track | 0.254 mm | 0.254 mm | community set |
| PTH hole to track | 0.33 mm | 0.33 mm | community set |
| NPTH hole to copper | 0.254 mm | 0.254 mm | community set |
| Inner layer: hole to unconnected plane | n/a | 0.2 mm | *verify* |
| Pad to track | 0.2 mm | 0.2 mm | older page, *verify* (not in the .kicad_dru, see below) |
| SMD pad to pad, different nets | 0.127 mm | 0.127 mm | community set (not in the .kicad_dru) |
| Copper to routed edge | 0.2 mm tracks; 0.3 mm pads and pours (JLC support) | same | confirmed; rules use 0.3 mm for all copper |
| Copper to V-cut edge | 0.4 mm | 0.4 mm | confirmed |
| Solder mask web (dam) | 0.1 mm (green) | 0.1 mm | *verify* (other colours larger) |
| Silkscreen line width | 0.15 mm | 0.15 mm | confirmed |
| Silkscreen text height | 1.0 mm (0.8 mm prints, may be illegible) | same | confirmed |
| Pad to silkscreen | 0.15 mm | 0.15 mm | confirmed (JLC removes silk on pads) |
| Via-in-pad (resin filled, capped, POFV) | not offered as standard | paid option on 4-layer; free only on 6+ layers | confirmed (free on 6-32 layers) |
| BGA | 0.25 mm pads, 0.35 mm drill to BGA pad | same | confirmed (JLC BGA guide) |

Copper weights and stackup: 4-layer default is 1 oz outer / 0.5 oz inner; 2 oz inner is
only on the 1.6 mm JLC2313 stackup with 2 oz outer.

## Files

- `jlcpcb_2layer.kicad_dru` and `jlcpcb_4layer.kicad_dru`: KiCad custom rules (KiCad 8 or later,
  tested on 10.0.6). Copy next to the project as `<project>.kicad_dru`. Rules named `JLC ...`;
  surcharge and "recommended" rows are warnings, hard limits are errors.
- Board setup minimums below go into **Board Setup > Design Rules > Constraints**
  (`board.design_settings.rules` in the `.kicad_pro`).

Copper-to-copper clearance is deliberately **not** a custom rule. In KiCad a matching custom rule
overrides the netclass clearance, so a JLC 0.1 mm rule would silently lower the boards' own
netclass clearances (for example Power_HI 0.25 mm). The JLC limit goes in the board setup minimum
instead, which is a floor under the netclasses. The same reasoning keeps pad-to-track 0.2 mm out of
the file: keep the Default netclass clearance at 0.2 mm or more if you want that margin.

Note also that the hole-clearance rules in the files replace the project's own board-setup hole
clearance (the SAM_IO project uses 0.33 mm for every hole; with the file, vias drop to the JLC 0.254 mm).

## Board setup minimums

| Constraint (`.kicad_pro` key) | 2-layer | 4-layer |
|---|---|---|
| Minimum clearance (`min_clearance`) | 0.10 | 0.09 |
| Minimum track width (`min_track_width`) | 0.10 | 0.09 |
| Minimum annular width (`min_via_annular_width`) | 0.05 | 0.05 |
| Minimum via diameter (`min_via_diameter`) | 0.25 | 0.25 |
| Minimum through hole (`min_through_hole_diameter`) | 0.15 | 0.15 |
| Hole to hole (`min_hole_to_hole`) | 0.20 | 0.20 |
| Hole clearance (`min_hole_clearance`) | 0.20 | 0.20 |
| Copper to edge (`min_copper_edge_clearance`) | 0.30 | 0.30 |
| Min text height (`min_text_height`) | 1.0 | 1.0 |
| Min text thickness (`min_text_thickness`) | 0.15 | 0.15 |
| Solder mask min web (`solder_mask_min_width`) | 0.10 | 0.10 |

These are fab limits, not routing targets. For routing, stay at or above: track 0.15-0.2 mm signal,
clearance 0.15-0.2 mm, vias 0.3 mm drill / 0.6 mm pad (no surcharge, 0.15 mm ring).

## Checking a board

```
kicad-cli pcb drc --refill-zones --severity-all --format json -o drc.json board.kicad_pcb
```
with the `.kicad_dru` and the board setup minimums in place. In this sandbox KiCad 10.0.6 runs
from the `kicad/kicad:10.0.6` Docker image (`dockerd &` then `docker run ... kicad-cli`).

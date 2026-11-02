# c58 routing record (KiCadRoutingTools)

How the board left by `../c58_widen_right.py` was routed, 2026-11-01. This is a record of what was run:
the files only make sense run in order on the intermediate boards. `$KRT` is a checkout of
[KiCadRoutingTools](https://github.com/drandyhaas/KiCadRoutingTools) at bf0405d8, with its Rust router built
(`python3 build_router.py`; pip scipy shapely ortools). Every step keeps the inner layers out
(`--layer-costs 1.0 -1 -1 1.0`) and uses `--escalation off`. KRT rips neighbouring copper even with
`--keep-input-copper`, so every step first locks the copper it must keep (`lock.py`, `rip.py`).

1. `1_route_ripped.sh`: the 16 nets c58 ripped (12 V OR, +5V, J10, J30 audio, VMON_5V), power widths per net.
   17 unconnected items (20 before the widening).
2. `prep_a2.py` + `2_route_audio.sh`: TP19 / TP20 moved above J30 (they had ridden along with the OR block),
   a User.2 keepout around the buck U35 / L2 (removed afterwards), AUD_DAC / AUD_AMP L / R rerouted: DAC tracks
   90 / 87 mm, at least 10.6 mm from the buck switch node.
3. `inward.py in out 4.0`: the +3V3 vias of U4 pins 5, 76, 24 and 29 (bus side) move under the package, 4 mm
   from its centre, between the pad rows and the exposed pad (tented). DRC unchanged.
4. `rip.py` (nets in `u4_bus_nets.txt`), `qfn_fanout.py -c U4 --width 0.2 --clearance 0.15`, then
   `4_route_u4_bus.sh` (`--bus --ordering bus`, 0.15 clearance, 0.05 grid): the 24 bus-side U4 nets.
   BUS_D0-D7 / A0-A3 leave U4 as an ordered 45 degree bundle to U6 / U7.
5. `graft.py` puts back the previous copper of SW_CLK, SW_LOAD_N, SW_DATA, STB_DATA, RP_RS485_RX and
   RP_RS485_DE (KRT routed them in long detours); `cut.py`, run twice on the DRC report, removes the grafted
   pieces that touch the new bus. Those six links are left for hand routing.
6. `locks.py` restores the lock flags the committed board had.

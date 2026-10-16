"""c28: project footprint library sam_cpu.pretty for the footprints c26/c27 drew from datasheets (BT1 XDCR-2032-603,
J27/J29 DS1128-05-S8B8P), registered in fp-lib-table, so "sam_cpu:" footprints resolve and Update PCB keeps them.
Also points the schematic Footprint fields of BT1, J27 and J29 at them, and renames the U32 logic nets after the
CA-IS2092VW pin names (Net-(U32-RXD) -> Net-(U32-RO), Net-(U32-TXD) -> Net-(U32-DI)) so they match the schematic.
Usage: c28_fp_library.py board.kicad_pcb project_dir"""
import os, sys, re
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); d = sys.argv[2]
lib = os.path.join(d, 'sam_cpu.pretty')

os.makedirs(lib, exist_ok=True); io = pcbnew.PCB_IO_KICAD_SEXPR()
DESCR = {'BT1': ('CR2032 SMD holder, Lianxin XDCR-2032-603 (LCSC C7498148), pads per maker drawing', 'battery CR2032 SMD'),
         'J27': ('RJ45 8P8C side entry, unshielded, through hole, CONNFLY DS1128-05-S8B8P (LCSC C86577), drawing C-DS1128-05-XXXXX-A', 'RJ45 8P8C horizontal'),
         'J29': ('RJ45 8P8C side entry, unshielded, through hole, CONNFLY DS1128-05-S8B8P (LCSC C86577), drawing C-DS1128-05-XXXXX-A', 'RJ45 8P8C horizontal')}
for ref, (de, kw) in DESCR.items():
    f = b.FindFootprintByReference(ref); f.SetLibDescription(de); f.SetKeywords(kw)
nets = {n.GetNetname(): n for n in b.GetNetInfo().NetsByName().values()}
for old, new in (('Net-(U32-RXD)', 'Net-(U32-RO)'), ('Net-(U32-TXD)', 'Net-(U32-DI)')):
    if old not in nets: continue
    o = nets[old]; n = pcbnew.NETINFO_ITEM(b, new); b.Add(n)
    T = b.Tracks()
    for x in [T[i] for i in range(T.size())] + [p for fp in b.GetFootprints() for p in fp.Pads()] + list(b.Zones()):
        if x.GetNetCode() == o.GetNetCode(): x.SetNet(n)
b.Save(sys.argv[1])
for ref in ('BT1', 'J27'):
    f = pcbnew.FOOTPRINT(b.FindFootprintByReference(ref))
    f.SetOrientationDegrees(0); f.SetPosition(pcbnew.VECTOR2I(0, 0)); f.SetLocked(False)
    for p in f.Pads(): p.SetNetCode(0)
    f.SetReference('REF**'); f.SetValue(f.GetFPID().GetUniStringLibItemName())
    f.SetPath(pcbnew.KIID_PATH())
    for fld in list(f.GetFields()):
        if fld.GetName() not in ('Reference', 'Value', 'Footprint', 'Datasheet', 'Description'): f.RemoveField(fld.GetName())
    io.FootprintSave(lib, f)
    print('saved', f.GetFPID().GetUniStringLibItemName())
t = os.path.join(d, 'fp-lib-table')
if not os.path.exists(t):
    open(t, 'w').write('(fp_lib_table\n  (version 7)\n  (lib (name "sam_cpu")(type "KiCad")(uri "${KIPRJMOD}/sam_cpu.pretty")(options "")(descr "SAM CPU project footprints"))\n)\n')
FP = {'mcu.kicad_sch': [('Battery:BatteryHolder_Keystone_3034_1x20mm', 'sam_cpu:BatteryHolder_Lianxin_XDCR-2032-603')],
      'rs485_i2s.kicad_sch': [('Connector_RJ:RJ45_OST_PJ012-8P8CX_Vertical', 'sam_cpu:RJ45_Connfly_DS1128-05-S8B8P_Horizontal')]}
for fn, reps in FP.items():
    p = os.path.join(d, fn); s = open(p).read()
    for a, c in reps: s = s.replace('(property "Footprint" "%s"' % a, '(property "Footprint" "%s"' % c)
    open(p, 'w').write(s)

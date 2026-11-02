"""c37 (board): IO bus series resistor arrays next to the J9 pins they drive (second CPU board alternative).
RN1-RN3 sat in a row under U6 / U7, so the address lines left U7, went down to RN3 and came back up to J9 pins 12-18,
across the data lines. Now each array stands in the strip between J9 and the buffers, level with its J9 pins:
RN3 (address, J9 12-18) between U6 and U7, RN2 (J9 2-8) and RN1 (J9 1-7) by the data pins. TP10-TP13 move down a row.
Board mm (KiCad - 30). Usage: c37_board_bus_arrays_by_j9.py in.kicad_pcb out.kicad_pcb"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from movelib import Board
b = Board(sys.argv[1])
b.move('RN3', 18.59, 35.65)
b.move('RN2', 18.59, 45.30)
b.move('RN1', 18.59, 49.35)
for i, ref in enumerate(('TP10', 'TP11', 'TP12', 'TP13')):
    b.move(ref, 21.5 + 3.2 * i, 57.6)
b.save(sys.argv[2])

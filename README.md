# Stern SAM CPU PPUC

A replacement CPU board for the Stern SAM pinball platform. A Raspberry Pi runs the original game ROM under PinMAME
through the [PPUC](https://github.com/PPUC) stack. An RP2040 on the same board drives the original IO power board bus (J1)
with its PIO, and reads the switch matrix, dedicated switches and DIP switches.

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): architecture, bus timing, pin budget, safety, and open questions.
- [docs/reference/](docs/reference/): Stern SAM manual extracts (IO power driver and CPU/Sound board schematics, backbox,
  playfield, cabinet and coin door wiring).

Background:
- [Tron-Legacy-LE-ROM-Decryption/io/bus](https://github.com/Ashram56/Tron-Legacy-LE-ROM-Decryption/tree/main/io/bus):
  the CPU to IO board bus as the SAM ROM drives it.
- [Stern-SAM-Databus-Analysis](https://github.com/Ashram56/Stern-SAM-Databus-Analysis): J1 pinout and IO board schematic notes.

## Licence

- Firmware and software: GNU GPL v3 ([LICENSE](LICENSE)), matching PPUC.
- Hardware design files: CERN Open Hardware Licence v2, strongly reciprocal ([LICENSE-HARDWARE](LICENSE-HARDWARE)).
- The manual extracts in `docs/reference/` are Stern Pinball's material, kept for reference, and are not covered by
  either licence.

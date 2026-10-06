#!/bin/sh
# Regenerate the draft: build, upgrade to KiCad 10, ERC, PDF, netlist check.
# Usage: KICAD_CLI=kicad-cli KICAD9_SYMBOL_DIR=/usr/share/kicad/symbols tools/run.sh /tmp/out
set -e
T=$(dirname "$0")
OUT=${1:-/tmp/sam_cpu_out}
CLI=${KICAD_CLI:-kicad-cli}
[ -z "$ONLY" ] && rm -rf "$OUT"; mkdir -p "$OUT"
python3 "$T/build2.py" "$OUT"
for f in "$OUT"/*.kicad_sch; do $CLI sch upgrade --force "$f" >/dev/null 2>&1; done
$CLI sch erc --severity-all -o "$OUT/erc.rpt" "$OUT/sam_cpu.kicad_sch" >/dev/null 2>&1 || true
grep -E "ERC messages|Errors|Warnings" "$OUT/erc.rpt" | tail -3
$CLI sch export pdf -o "$OUT/sam_cpu.pdf" "$OUT/sam_cpu.kicad_sch" >/dev/null 2>&1
$CLI sch export netlist -o "$OUT/sam_cpu.net" "$OUT/sam_cpu.kicad_sch" >/dev/null 2>&1
python3 "$T/verify2.py" "$OUT/sam_cpu.net" 2>&1 | grep -v "single connection" | tail -6

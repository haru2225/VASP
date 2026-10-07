#!/usr/bin/env bash
# Build POTCAR (order Si Al O H, PAW_PBE) in every vasp/<name>/{relax,static}/.
# Usage: VASP_POTCAR_DIR=/path/to/potpaw_PBE bash make_potcar.sh
set -euo pipefail
: "${VASP_POTCAR_DIR:?set VASP_POTCAR_DIR to the PAW_PBE (potpaw_PBE) directory}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for d in "$here"/vasp/*/*/; do
  species=$(sed -n 6p "$d/POSCAR" 2>/dev/null || true)
  [[ -n "$species" ]] || species="Si Al O H"   # static dirs get POSCAR at run time; same species order
  : > "$d/POTCAR"
  for s in $species; do cat "$VASP_POTCAR_DIR/$s/POTCAR" >> "$d/POTCAR"; done
done
echo "POTCARs written"

#!/usr/bin/env bash
# Build POTCAR (order Si Al O H, PAW_PBE) in every vasp/<name>/{relax,static}/.
# Usage: VASP_POTCAR_DIR=/path/to/potpaw_PBE bash make_potcar.sh   (POTCAR, POTCAR.gz or POTCAR.Z)
set -euo pipefail
: "${VASP_POTCAR_DIR:?set VASP_POTCAR_DIR to the PAW_PBE (potpaw_PBE) directory}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
get() {  # print POTCAR of element $1
  local d="$VASP_POTCAR_DIR/$1"
  if [[ -f "$d/POTCAR" ]]; then cat "$d/POTCAR"
  elif [[ -f "$d/POTCAR.gz" ]]; then gzip -dc "$d/POTCAR.gz"
  elif [[ -f "$d/POTCAR.Z" ]]; then gzip -dc "$d/POTCAR.Z"
  else echo "no POTCAR for $1 in $d" >&2; return 1; fi
}
for d in "$here"/vasp/*/*/; do
  : > "$d/POTCAR"
  for s in Si Al O H; do get "$s" >> "$d/POTCAR"; done
done
echo "POTCARs written (Si Al O H)"

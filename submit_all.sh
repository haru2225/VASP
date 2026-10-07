#!/usr/bin/env bash
# Optional: one independent job per structure (faster in parallel). Normally just `qsub run_vasp.pbs`.
cd "$(dirname "${BASH_SOURCE[0]}")"
for d in vasp/*/; do n=$(basename "$d"); qsub -N "clay_$n" -v NAME="$n" "$@" run_vasp.pbs; done

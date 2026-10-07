#!/usr/bin/env bash
# Submit every structure (independent jobs). Usage: bash submit_all.sh [extra qsub args]
cd "$(dirname "${BASH_SOURCE[0]}")"
for d in vasp/*/; do n=$(basename "$d"); qsub -N "clay_$n" -v NAME="$n" "$@" run_vasp.pbs; done

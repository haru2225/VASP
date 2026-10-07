#!/usr/bin/env python3
"""Write CP2K inputs for every structure in ../structures -> cp2k/runs/<name>/{start.xyz,opt.inp,sp.inp}.

    python3 make_cp2k.py

opt: GEO_OPT (LBFGS, PBE, SZV-MOLOPT-SR-GTH, 300 Ry), ions only, cell fixed.
sp : ENERGY on opt's last geometry (relaxed.xyz), DZVP-MOLOPT-SR-GTH, 400 Ry,
     Hirshfeld + Mulliken charges.  Cells are 3D periodic with vacuum.
"""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIND = {"H": "q1", "O": "q6", "Al": "q3", "Si": "q4"}


def kinds(basis):
    return "\n".join(f"    &KIND {e}\n      BASIS_SET {basis}\n      POTENTIAL GTH-PBE-{q}\n    &END KIND"
                     for e, q in KIND.items())


def inp(name, cell, mode):
    opt = mode == "opt"
    basis = "SZV-MOLOPT-SR-GTH" if opt else "DZVP-MOLOPT-SR-GTH"
    cutoff, rel = (300, 40) if opt else (400, 50)
    coord = "start.xyz" if opt else "relaxed.xyz"
    printblk = "" if opt else """
    &PRINT
      &HIRSHFELD
        SELF_CONSISTENT .FALSE.
        SHAPE_FUNCTION DENSITY
        REFERENCE_CHARGE ATOMIC
      &END HIRSHFELD
      &MULLIKEN ON
      &END MULLIKEN
    &END PRINT"""
    motion = """
&MOTION
  &GEO_OPT
    TYPE MINIMIZATION
    OPTIMIZER LBFGS
    MAX_ITER 200
    MAX_FORCE 1.0E-3
  &END GEO_OPT
&END MOTION
""" if opt else ""
    return f"""&GLOBAL
  PROJECT {mode}
  RUN_TYPE {"GEO_OPT" if opt else "ENERGY"}
  PRINT_LEVEL LOW
&END GLOBAL
{motion}
&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME GTH_POTENTIALS
    &MGRID
      CUTOFF {cutoff}
      REL_CUTOFF {rel}
    &END MGRID
    &QS
      EPS_DEFAULT 1.0E-10
    &END QS
    &SCF
      SCF_GUESS ATOMIC
      EPS_SCF {"1.0E-5" if opt else "5.0E-6"}
      MAX_SCF 200
      &OT
        PRECONDITIONER FULL_SINGLE_INVERSE
        MINIMIZER DIIS
      &END OT
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC{printblk}
  &END DFT
  &SUBSYS
    &CELL
      ABC {cell[0]:.5f} {cell[1]:.5f} {cell[2]:.5f}
      PERIODIC XYZ
    &END CELL
    &TOPOLOGY
      COORD_FILE_NAME {coord}
      COORD_FILE_FORMAT XYZ
    &END TOPOLOGY
{kinds(basis)}
  &END SUBSYS
&END FORCE_EVAL
"""


def main():
    for xyz in sorted((HERE.parent / "structures").glob("*.xyz")):
        name = xyz.stem
        cell = json.loads((xyz.with_suffix(".json")).read_text())["cell"]
        d = HERE / "runs" / name
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(xyz, d / "start.xyz")
        (d / "opt.inp").write_text(inp(name, cell, "opt"))
        (d / "sp.inp").write_text(inp(name, cell, "sp"))
        print("wrote", d)


if __name__ == "__main__":
    main()

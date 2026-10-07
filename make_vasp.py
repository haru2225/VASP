#!/usr/bin/env python3
"""Write VASP inputs (relax + static/Bader) for every structure in structures/.

    python make_vasp.py          # -> vasp/<name>/{relax,static}/{POSCAR,INCAR,KPOINTS} + order.json

POTCAR is NOT included (VASP licence): on the cluster run `bash make_potcar.sh`.
Species order in POSCAR/POTCAR is fixed: Si Al O H  (the atoms are grouped by species,
order.json maps POSCAR index -> index in structures/<name>.xyz).

Level of theory: PBE, PAW, ENCUT 520 eV, Gamma-centred k-mesh (~20 A / L, 1 along vacuum),
Gaussian smearing 0.05 eV, closed shell. `relax` = ionic relaxation (cell fixed, EDIFFG -0.02);
`static` starts from relax/CONTCAR and writes AECCAR0/AECCAR2/CHGCAR for Bader (LAECHG).
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPECIES = ["Si", "Al", "O", "H"]
ZVAL = {"Si": 4, "Al": 3, "O": 6, "H": 1}  # PAW_PBE Si, Al, O, H

COMMON = """SYSTEM = {name} {stage}
PREC = Accurate
ENCUT = 520
ISMEAR = 0
SIGMA = 0.05
EDIFF = 1E-6
ALGO = Normal
LASPH = .TRUE.
LREAL = {lreal}
NELM = 200
ISPIN = 1
LWAVE = .FALSE.
{extra}"""
RELAX = """IBRION = 2
ISIF = 2
NSW = 200
EDIFFG = -0.02
POTIM = 0.3
LCHARG = .FALSE.
"""
STATIC = """IBRION = -1
NSW = 0
LCHARG = .TRUE.
LAECHG = .TRUE.
"""


def read_xyz(path):
    L = Path(path).read_text().splitlines()[2:]
    return [l.split()[0] for l in L], [[float(x) for x in l.split()[1:4]] for l in L]


def kmesh(cell):
    return [1 if L > 25.0 else max(1, math.ceil(20.0 / L)) for L in cell]


def poscar(name, el, pos, cell):
    order = [i for s in SPECIES for i, e in enumerate(el) if e == s]
    counts = [sum(e == s for e in el) for s in SPECIES]
    keep = [(s, c) for s, c in zip(SPECIES, counts) if c]
    lines = [f"{name}", "1.0"] + [
        " ".join(f"{(cell[j] if j == k else 0.0):.8f}" for k in range(3)) for j in range(3)]
    lines += [" ".join(s for s, _ in keep), " ".join(str(c) for _, c in keep), "Cartesian"]
    lines += [" ".join(f"{x:.8f}" for x in pos[i]) for i in order]
    return "\n".join(lines) + "\n", order


def main():
    names = sorted(p.stem for p in (HERE / "structures").glob("*.xyz"))
    for name in names:
        el, pos = read_xyz(HERE / "structures" / f"{name}.xyz")
        meta = json.loads((HERE / "structures" / f"{name}.json").read_text())
        cell = meta["cell"]
        text, order = poscar(name, el, pos, cell)
        ribbon = name.startswith("rib_")
        lreal = ".FALSE." if len(el) < 60 else "Auto"
        dip = ""
        if ribbon:  # dipole correction along the edge-normal direction (1 = x, 2 = y)
            axis = 2 if name.startswith("rib_y") else 1
            dip = f"LDIPOL = .TRUE.\nIDIPOL = {axis}\n"
        root = HERE / "vasp" / name
        for stage, body in (("relax", RELAX), ("static", STATIC)):
            d = root / stage
            d.mkdir(parents=True, exist_ok=True)
            if stage == "relax":
                (d / "POSCAR").write_text(text)  # static gets CONTCAR from relax at run time
            (d / "INCAR").write_text(COMMON.format(name=name, stage=stage, lreal=lreal, extra=dip) + body)
            k = kmesh(cell)
            (d / "KPOINTS").write_text(f"Gamma\n0\nGamma\n{k[0]} {k[1]} {k[2]}\n0 0 0\n")
        (root / "order.json").write_text(json.dumps(dict(species=SPECIES, poscar_to_xyz=order, n=len(el))))
        print(f"{name}: {len(el)} atoms, kmesh {kmesh(cell)}")


if __name__ == "__main__":
    main()

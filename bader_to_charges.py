#!/usr/bin/env python3
"""Convert Bader ACF.dat -> vasp/<name>/static/charges.dat in the *structures/<name>.xyz* atom order.

    python bader_to_charges.py <name>
net charge q = ZVAL - ACF charge (PAW_PBE ZVAL: Si 4, Al 3, O 6, H 1).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ZVAL = {"Si": 4, "Al": 3, "O": 6, "H": 1}


def main(name):
    root = HERE / "vasp" / name
    order = json.loads((root / "order.json").read_text())
    sp = order["species"]
    pos = (root / "static" / "POSCAR").read_text().splitlines()
    names, counts = pos[5].split(), [int(c) for c in pos[6].split()]
    elems = [n for n, c in zip(names, counts) for _ in range(c)]  # POSCAR order
    rows = [l.split() for l in (root / "static" / "ACF.dat").read_text().splitlines()
            if l.strip() and l.split()[0].isdigit()]
    assert len(rows) == len(elems), (len(rows), len(elems))
    q_xyz = [None] * order["n"]
    el_xyz = [None] * order["n"]
    for k, (e, r) in enumerate(zip(elems, rows)):
        i = order["poscar_to_xyz"][k]
        q_xyz[i], el_xyz[i] = ZVAL[e] - float(r[4]), e
    (root / "static" / "charges.dat").write_text(
        "# index element net_charge(Bader)  [xyz order]\n" + "".join(
            f"{i} {e} {q:.5f}\n" for i, (e, q) in enumerate(zip(el_xyz, q_xyz))))
    print(f"{name}: total charge {sum(q_xyz):+.4f} e over {len(q_xyz)} atoms")


if __name__ == "__main__":
    main(sys.argv[1])

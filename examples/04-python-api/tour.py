"""A tour of the nanopnp Python API (IF-01): run, inspect, substitute, read back.

Run from this directory::

    python tour.py

Everything here is the stable public surface: ``from nanopnp import ...`` and the
case schema in ``nanopnp.case``. The tour writes ``tour.json``, the record the example's
test reads, and ``fields.csv``; it plots ``potential.png`` when matplotlib is installed
(the ``examples`` extra).
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
from pathlib import Path

import meshio

from nanopnp import Case, Session, Store
from nanopnp.case import Mesh

log = logging.getLogger("tour")


def main() -> None:
    """Walk the tour, one step per section of the README."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session = Session(Store(Path("store")))
    case = Case.load("tour.case.yaml")

    # 1. Every stage describes itself without importing its implementation.
    for stage in session.stages:
        log.info("stage %2d  %-10s %s", stage.number, stage.name, stage.schema)

    # 2. Run the case through the solve and the field export. Progress arrives
    #    as a fraction and a caption; a GUI would draw a bar from it.
    captions: list[str] = []
    result = session.run(
        case, progress=lambda fraction, message: captions.append(f"{fraction:.2f} {message}")
    )
    log.info("run directory %s, %d progress reports", result.directory, len(captions))
    for record in result.stages:
        log.info("  %-10s %s %s", record.name, record.hash[:12], "cached" if record.cached else "")

    # 3. Every stage left a typed, content-hashed artefact; inspect one.
    mesh = result.artefacts["mesh"]
    log.info("mesh artefact %s: %s", mesh.hash[:12], dict(mesh.summary))

    # 4. Change an input by hand (FR-27). A stage's key moves exactly when one of
    #    its inputs does. A finer element size moves the mesh artefact and not the
    #    materials artefact, which never reads the mesh. The generated mesh, supplied
    #    as a file instead of the pore that made it, is a mesh like any other: a
    #    byte-identical copy under another name keeps its key. A walk to a stage
    #    runs that stage's inputs and nothing else, so the walks cost no solve.
    before = {record.name: record.hash for record in result.stages}
    shutil.copyfile(mesh.payload["mesh"], "pore.msh")
    shutil.copyfile("pore.msh", "renamed.msh")
    variants = {
        "finer": case.with_(maxh_nm=2.0),
        "supplied": _supplied(case, "pore.msh"),
        "renamed": _supplied(case, "renamed.msh"),
    }
    after = {name: _walked(session, variant) for name, variant in variants.items()}
    for name, hashes in after.items():
        for stage in ("mesh", "materials"):
            log.info("%-9s %-10s %s -> %s", name, stage, before[stage][:12], hashes[stage][:12])

    # 5. Read the exported fields back (IF-07): XDMF with HDF5 heavy data, in SI
    #    with the unit in each attribute's name. Omega is the whole domain and
    #    Omega_w the fluid alone; nothing is padded over a solid.
    exported = {path.stem: meshio.read(path) for path in result.files if path.suffix == ".xdmf"}
    names = sorted({name for fields in exported.values() for name in fields.point_data})
    log.info("exported fields: %s", ", ".join(names))
    whole = exported["fields_omega"]
    with Path("fields.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["r_nm", "z_nm", "phi_V"])
        writer.writerows(
            zip(whole.points[:, 0], whole.points[:, 1], whole.point_data["phi_V"], strict=True)
        )
    _plot(whole.points, whole.point_data["phi_V"])

    Path("tour.json").write_text(
        json.dumps(
            {
                "stages": before,
                "substituted": after,
                "field_names": names,
                "species": [species.name for species in case.electrolyte.species],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _supplied(case: Case, mesh: str) -> Case:
    """Return ``case`` with the mesh file ``mesh`` in the place of the pore it meshes."""
    return case.with_(
        {
            "geometry": None,
            "numerics.mesh": Mesh(),
            "inputs.mesh.path": mesh,
            "inputs.mesh.format": "msh41",
        }
    )


def _walked(session: Session, case: Case) -> dict[str, str]:
    """Return each stage's hash for ``case`` walked to the mesh and to the materials."""
    hashes: dict[str, str] = {}
    for upto in ("mesh", "materials"):
        hashes.update({record.name: record.hash for record in session.run(case, upto=upto).stages})
    return hashes


def _plot(coordinates: object, potential: object) -> None:
    """Plot the potential over the fluid, if matplotlib is installed."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log.info("matplotlib is not installed; fields.csv holds the numbers")
        return
    figure, axes = plt.subplots(figsize=(4, 6))
    points = axes.scatter(coordinates[:, 0], coordinates[:, 1], c=potential, s=4)  # type: ignore[index]
    figure.colorbar(points, label="phi (V)")
    axes.set_xlabel("r (nm)")
    axes.set_ylabel("z (nm)")
    axes.set_aspect("equal")
    figure.savefig("potential.png", dpi=150, bbox_inches="tight")
    log.info("wrote potential.png")


if __name__ == "__main__":
    main()

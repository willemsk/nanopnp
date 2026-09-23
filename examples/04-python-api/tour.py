"""A tour of the nanopnp Python API (IF-01): run, inspect, substitute, read back.

Run from this directory, after ``nanopnp mesh cylinder --out pore.msh`` and
``nanopnp mesh cylinder --maxh-nm 2 --out finer.msh``::

    python tour.py

Everything here is the stable public surface: ``from nanopnp import ...``. The
tour writes ``tour.json``, the record the example's test reads, and ``fields.csv``;
it plots ``potential.png`` when matplotlib is installed (the ``examples`` extra).
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
from pathlib import Path

import meshio

from nanopnp import (
    CaseDocument,
    RunResult,
    Store,
    dumps_case,
    load_case,
    registered_stages,
    run_case,
    run_document,
)

log = logging.getLogger("tour")


def main() -> None:
    """Walk the tour, one step per section of the README."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store = Store(Path("store"))

    # 1. Every stage describes itself without importing its implementation.
    for stage in registered_stages():
        log.info("stage %2d  %-10s %s", stage.number, stage.name, stage.artefact_schema)

    # 2. Run the case through the solve and the field export. Progress arrives
    #    as a fraction and a caption; a GUI would draw a bar from it.
    captions: list[str] = []
    result = run_case(
        Path("tour.case.yaml"),
        store=store,
        progress=lambda fraction, message: captions.append(f"{fraction:.2f} {message}"),
    )
    log.info("run directory %s, %d progress reports", result.directory, len(captions))
    for record in result.stages:
        log.info("  %-10s %s %s", record.name, record.hash[:12], "cached" if record.cached else "")

    # 3. Every stage left a typed, content-hashed artefact; inspect one.
    mesh = result.artefacts["mesh"]
    log.info("mesh artefact %s: %s", mesh.hash[:12], dict(mesh.summary))

    # 4. Substitute the mesh by hand (FR-27): the same document with one input
    #    changed. A stage's key moves exactly when one of its inputs does, so the
    #    mesh artefact moves and the materials artefact, which never reads the
    #    mesh, does not. Stopping at stage 8 costs no solve.
    before = {record.name: record.hash for record in result.stages}
    shutil.copyfile("pore.msh", "renamed.msh")
    after = {
        path: {
            record.name: record.hash
            for record in _substituted(Path("tour.case.yaml"), path, store).stages
        }
        for path in ("finer.msh", "renamed.msh")
    }
    for path, hashes in after.items():
        for name in ("mesh", "materials"):
            log.info("%-12s %-10s %s -> %s", path, name, before[name][:12], hashes[name][:12])

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
                "species": _species(Path("tour.case.yaml")),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _species(case: Path) -> list[str]:
    """Return the names of the species a case solves for."""
    return [species.name for species in load_case(case).electrolyte.species]


def _substituted(case: Path, mesh: str, store: Store) -> RunResult:
    """Return the case run to stage 8 with ``inputs.mesh.path`` replaced."""
    data = load_case(case).model_dump(mode="json", by_alias=True, exclude_none=True)
    data["inputs"]["mesh"]["path"] = mesh
    variant = CaseDocument.model_validate(data)
    return run_document(
        variant, case_text=dumps_case(variant), store=store, upto="materials", write=False
    )


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

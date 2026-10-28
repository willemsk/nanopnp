"""A one-axis sweep of a case held in Python, written to the store and planned as a file."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from nanopnp.io.artefact import SWEEP_SCHEMA, SweepArtefact
from nanopnp.io.case import FieldValue, dumps_case
from nanopnp.io.store import Store, atomic_write_bytes
from nanopnp.pipeline.handle import Case, field_path, input_paths
from nanopnp.sweep.collect import collect
from nanopnp.sweep.document import loads_sweep
from nanopnp.sweep.plan import SweepPlan, SweepPlanError, build_plan, write_plan
from nanopnp.sweep.run import run_plan

__all__ = ["BASE_FILENAME", "SWEEP_FILENAME", "Sweep", "sweep"]

BASE_FILENAME = "base.case.yaml"

SWEEP_FILENAME = "sweep.yaml"


@dataclass(frozen=True)
class Sweep:
    """A planned sweep, its files in one directory of the store."""

    plan: SweepPlan
    directory: Path
    store: Store

    def run(self, *, workers: int = 1) -> SweepArtefact:
        """Run every point, warm-starting each from its parent, and collect the dataset."""
        write_plan(self.plan, self.directory)
        run_plan(self.plan, self.directory, store=self.store, workers=workers)
        return collect(self.plan, self.directory)


def _plain(value: FieldValue) -> FieldValue:
    # An element of an ndarray is a numpy scalar, and a row of a 2-D one an array: neither can be
    # written by YAML or the content hash, and ``tolist`` turns both into plain Python.
    tolist = getattr(value, "tolist", None)
    return tolist() if callable(tolist) else value


def sweep(
    case: Case,
    *,
    axis: str,
    values: Sequence[FieldValue],
    origin: int = 0,
    check_meshes: bool = True,
) -> Sweep:
    """Plan a sweep of ``case`` over one field, as a sweep file over the same base would.

    Parameters
    ----------
    axis
        The field swept: a dotted case path, or the leaf name one field ends in.
    origin
        Index into ``values`` of the point every other point warm-starts towards.
    check_meshes
        Whether to run the mesh gate once per distinct mesh with a wall correction.

    Raises
    ------
    SweepPlanError
        The case names an input file by a relative path, which the store's copy of the case
        would read against another directory.
    """
    relative = [
        f"{dotted} = {value}"
        for dotted, value in input_paths(case.document).items()
        if not Path(value).is_absolute()
    ]
    if relative:
        raise SweepPlanError(
            f"case {case.document.name!r} names {', '.join(relative)} by a relative path; its "
            "copy in the store would read it against another directory. Build the case with "
            "Case.load, or a Case factory, which write every input path absolute"
        )
    dotted = field_path(axis)
    name = case.document.name
    document = {
        "schema": SWEEP_SCHEMA,
        "name": name,
        "base": BASE_FILENAME,
        "axes": [
            {
                "name": dotted.rsplit(".", 1)[-1],
                "path": dotted,
                "values": [_plain(value) for value in values],
                "origin": origin,
            }
        ],
    }
    store = case.store or Store()
    text = yaml.safe_dump(document, sort_keys=False)
    base_text = dumps_case(case.document).encode("utf-8")
    # The directory is named by the plan's hash, as the sweep command names it, so the plan is
    # first built beside its files in a staging directory to read that hash. The hash does not
    # depend on where the base case lies, so the plan is built once and moved.
    sweeps = store.root / "sweeps"
    sweeps.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=sweeps, prefix=".staging-") as scratch:
        staging = Path(scratch)
        atomic_write_bytes(staging / BASE_FILENAME, base_text)
        atomic_write_bytes(staging / SWEEP_FILENAME, text.encode("utf-8"))
        staged = build_plan(
            loads_sweep(text, source=str(staging / SWEEP_FILENAME)),
            source=staging / SWEEP_FILENAME,
            check_meshes=check_meshes,
        )
    directory = store.sweep_directory(name, staged.hash)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(directory / BASE_FILENAME, base_text)
    atomic_write_bytes(directory / SWEEP_FILENAME, text.encode("utf-8"))
    plan = replace(staged, base_path=(directory / BASE_FILENAME).resolve())
    return Sweep(plan, directory, store)

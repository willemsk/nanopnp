"""A one-axis sweep of a case held in Python, written to the store and planned as a file."""

from __future__ import annotations

import os
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
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
    # An element of an ndarray is a numpy scalar, which YAML and the content hash cannot write.
    item = getattr(value, "item", None)
    return item() if callable(item) else value


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
    # first built in a staging directory to read that hash.
    staging = store.root / "sweeps" / f".staging-{os.getpid()}"
    try:
        staging.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(staging / BASE_FILENAME, base_text)
        atomic_write_bytes(staging / SWEEP_FILENAME, text.encode("utf-8"))
        staged = build_plan(
            loads_sweep(text, source=str(staging / SWEEP_FILENAME)),
            source=staging / SWEEP_FILENAME,
            check_meshes=False,
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    directory = store.sweep_directory(name, staged.hash)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(directory / BASE_FILENAME, base_text)
    source = directory / SWEEP_FILENAME
    atomic_write_bytes(source, text.encode("utf-8"))
    plan = build_plan(
        loads_sweep(text, source=str(source)), source=source, check_meshes=check_meshes
    )
    return Sweep(plan, directory, store)

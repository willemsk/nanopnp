"""Reopening a finished run for the Tier-3 comparison, without re-solving it.

A Tier-3 report is post-processing: the twenty solves of the attribution ladder
are dispatched by the sweep runner (FR-24) and the comparison then reads what
they produced. Re-solving here would double the hours section 7.1 budgets for the
tier and, worse, would compare a *second* solution against the golden while the
manifest described the first.

Two things come out of a run directory. The converged state, through
:func:`~nanopnp.solve.state.restore`, which ingests the run's own mesh and
rebuilds the operator from the same :func:`~nanopnp.solve.continuation.ladder`
the solve used — so the restored solution cannot differ from the solved one in a
switch. And the **recorded** quantities, read from ``run.json`` rather than
re-extracted: FR-25 archived what the run reported, and a comparison that
recomputed them would be comparing the golden against something the manifest
does not describe.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, decode_floats
from nanopnp.io.manifest import CASE_FILENAME
from nanopnp.io.run import RUN_RECORD_FILENAME

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.scaling import Scales
    from nanopnp.io.case import CaseDocument
    from nanopnp.io.store import Store
    from nanopnp.physics.models import ModelSolution

__all__ = ["ReopenedRun", "RunError", "reopen"]

SOLVE_STAGE = "solve"
"""The artefact whose payload carries the converged state (section 5.2, stage 10)."""


class RunError(ValueError):
    """A run directory cannot be reopened for comparison.

    A ``ValueError`` and IF-02's case class: the fix is to point at a different
    directory, or to re-run the member, never to retry (QR-12).
    """


@dataclass(frozen=True)
class ReopenedRun:
    """One finished run, ready to be sampled on a probe grid.

    Parameters
    ----------
    directory
        Where it was read from.
    case
        The case document the run wrote beside its manifest, which is the
        document the state is restored into.
    solution
        The converged state, on its own mesh and operator.
    scales
        The NUM-09 scale set the state was solved in, which
        :func:`~nanopnp.validation.compare.sample_on_probe` needs to return SI.
    quantities
        What the run *recorded* — the stage-11 summary, floats restored.
    """

    directory: Path
    case: CaseDocument
    solution: ModelSolution
    scales: Scales
    quantities: Mapping[str, Canonicalisable]


def reopen(directory: str | Path, *, store: Store | None = None) -> ReopenedRun:
    """Return a finished run's solution and recorded quantities.

    Parameters
    ----------
    directory
        A run directory, as ``nanopnp run`` or a sweep member wrote it: it holds
        ``run.json``, ``manifest.json`` and ``case.yaml``.
    store
        The artefact store holding the solve payload. The run record names the
        store it used; passing one overrides that, which is what lets a report be
        produced on a machine that mounted the store somewhere else.

    Returns
    -------
    ReopenedRun

    Raises
    ------
    RunError
        If the directory is not a run directory, if the run stopped before the
        solve, or if the store does not hold the solve artefact — each named,
        because "no state" and "the state is elsewhere" are different problems
        with different fixes.
    """
    from nanopnp.io.case import load_case, resolve
    from nanopnp.io.store import Store
    from nanopnp.physics.coefficients import mesh_unit_scales
    from nanopnp.solve.state import restore, warm_start_payload

    source = Path(directory)
    record = _record(source)
    entry = _solve_entry(source, record)

    configured = record.get("store")
    holding = store if store is not None else Store(str(configured) if configured else None)
    artefact = holding.get(str(entry["schema"]), str(entry["hash"]))
    if artefact is None:
        raise RunError(
            f"the store at {holding.root} holds no {entry['schema']} artefact "
            f"{str(entry['hash'])[:12]}, which is the converged state {source} names. The run "
            "was made against another store, or the store has been pruned; point --store at the "
            "one the run used, or re-run the member"
        )

    case_path = source / CASE_FILENAME
    if not case_path.is_file():
        raise RunError(
            f"{case_path} is not there, so the state cannot be restored: the space its "
            "coefficients live on is built from the case's own mesh and element orders"
        )
    document = load_case(case_path)
    resolved = resolve(document)
    solution = restore(warm_start_payload(artefact), case=document)
    quantities = record.get("quantities")
    return ReopenedRun(
        directory=source,
        case=document,
        solution=solution,
        scales=mesh_unit_scales(resolved.electrolyte, resolved.concentration_M),
        quantities=dict(quantities) if isinstance(quantities, dict) else {},
    )


def _record(directory: Path) -> Mapping[str, Canonicalisable]:
    """Return the run record, floats restored."""
    path = directory / RUN_RECORD_FILENAME
    if not path.is_file():
        raise RunError(
            f"{path} is not there, so {directory} is not a run directory. A run written by "
            "'nanopnp run' or by a sweep member carries one beside its manifest"
        )
    decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(decoded, dict):
        raise RunError(f"{path} does not hold a run record object")
    return decoded


def _solve_entry(directory: Path, record: Mapping[str, Canonicalisable]) -> Mapping[str, str]:
    """Return the solve artefact's schema and hash from a run record."""
    artefacts = record.get("artefacts")
    entry = artefacts.get(SOLVE_STAGE) if isinstance(artefacts, dict) else None
    if not isinstance(entry, dict) or "schema" not in entry or "hash" not in entry:
        produced = ", ".join(sorted(artefacts)) if isinstance(artefacts, dict) else "nothing"
        raise RunError(
            f"{directory} records no {SOLVE_STAGE!r} artefact; it produced {produced}. The run "
            "stopped before the solve, so there is no converged state to compare"
        )
    return {"schema": str(entry["schema"]), "hash": str(entry["hash"])}

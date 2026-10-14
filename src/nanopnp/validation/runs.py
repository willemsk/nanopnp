"""Reopening a finished run for the Tier-3 comparison, without re-solving it."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, decode_floats
from nanopnp.io.manifest import CASE_FILENAME
from nanopnp.pipeline.run import RUN_RECORD_FILENAME

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.scaling import Scales
    from nanopnp.io.artefact import Artefact
    from nanopnp.io.case import CaseDocument
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.io.store import Store
    from nanopnp.physics.models import ModelSolution

__all__ = ["ReopenedRun", "RunError", "reopen"]

SOLVE_STAGE = "solve"


class RunError(ValueError):
    """A run directory cannot be reopened for comparison."""


@dataclass(frozen=True)
class ReopenedRun:
    """One finished run, ready to be sampled on a probe grid."""

    directory: Path
    case: CaseDocument
    resolved: ResolvedCase
    solution: ModelSolution
    scales: Scales
    quantities: Mapping[str, Canonicalisable]
    upstream: Mapping[str, Artefact]


def reopen(directory: str | Path, *, store: Store | None = None) -> ReopenedRun:
    """Return a finished run's solution and recorded quantities.

    Parameters
    ----------
    directory
        A run directory holding ``run.json``, ``manifest.json`` and ``case.yaml``.
    store
        Artefact store overriding the one the run record names.

    Raises
    ------
    RunError
        Not a run directory, the run stopped before the solve, or the store lacks its artefact.
    """
    from nanopnp.io.store import Store
    from nanopnp.physics.coefficients import mesh_unit_scales
    from nanopnp.pipeline.case import load_case, resolve
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
    mesh = record.get("artefacts", {}).get("mesh")
    # A generated mesh is read from the run's own stage-6 payload, never
    # regenerated; a supplied one is re-read from inputs.mesh.
    generated = (
        holding.get(str(mesh["schema"]), str(mesh["hash"])) if isinstance(mesh, dict) else None
    )
    if isinstance(mesh, dict) and generated is None and resolved.generates_mesh:
        raise RunError(
            f"the store at {holding.root} holds no {mesh['schema']} artefact "
            f"{str(mesh['hash'])[:12]}, which is the generated mesh {source} was solved on. The "
            "run was made against another store, or the store has been pruned; point --store at "
            "the one the run used, or re-run the member"
        )
    # A deposited charge and a derived chi are read from the run's own stage-7
    # artefact, never made again; a supplied field is re-read
    # from inputs:.
    charge = record.get("artefacts", {}).get("charge")
    stage7 = (
        holding.get(str(charge["schema"]), str(charge["hash"]))
        if isinstance(charge, dict)
        else None
    )
    needed = (
        "deposited charge"
        if resolved.deposits_charge
        else "derived solid fraction"
        if resolved.derives_eps_r
        else None
    )
    if isinstance(charge, dict) and stage7 is None and needed is not None:
        raise RunError(
            f"the store at {holding.root} holds no {charge['schema']} artefact "
            f"{str(charge['hash'])[:12]}, which is the {needed} {source} was solved with. "
            "The run was made against another store, or the store has been pruned; point --store "
            "at the one the run used, or re-run the member"
        )
    upstream = _upstream(source, record, holding, resolved) if needed is not None else {}
    solution = restore(
        warm_start_payload(artefact),
        resolved=resolved,
        mesh_artefact=generated,
        charge_artefact=stage7,
    )
    quantities = record.get("quantities")
    return ReopenedRun(
        directory=source,
        case=document,
        resolved=resolved,
        solution=solution,
        scales=mesh_unit_scales(resolved.electrolyte, resolved.concentration_M),
        quantities=dict(quantities) if isinstance(quantities, dict) else {},
        upstream=upstream,
    )


def _upstream(
    source: Path, record: Mapping[str, Canonicalisable], holding: Store, resolved: ResolvedCase
) -> dict[str, Artefact]:
    names = (["structure"] if resolved.structure is not None else []) + (
        ["protonation"] if resolved.deposits_charge else []
    )
    artefacts = record.get("artefacts", {})
    found: dict[str, Artefact] = {}
    for name in names:
        entry = artefacts.get(name) if isinstance(artefacts, dict) else None
        if not isinstance(entry, dict):
            raise RunError(
                f"{source} records no {name!r} artefact, which the case's identity is read from; "
                "re-run the member"
            )
        artefact = holding.get(str(entry["schema"]), str(entry["hash"]))
        if artefact is None:
            raise RunError(
                f"the store at {holding.root} holds no {entry['schema']} artefact "
                f"{str(entry['hash'])[:12]}, which is the {name} {source} was solved from. The "
                "run was made against another store, or the store has been pruned; point --store "
                "at the one the run used, or re-run the member"
            )
        found[name] = artefact
    return found


def _record(directory: Path) -> Mapping[str, Canonicalisable]:
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
    artefacts = record.get("artefacts")
    entry = artefacts.get(SOLVE_STAGE) if isinstance(artefacts, dict) else None
    if not isinstance(entry, dict) or "schema" not in entry or "hash" not in entry:
        produced = ", ".join(sorted(artefacts)) if isinstance(artefacts, dict) else "nothing"
        raise RunError(
            f"{directory} records no {SOLVE_STAGE!r} artefact; it produced {produced}. The run "
            "stopped before the solve, so there is no converged state to compare"
        )
    return {"schema": str(entry["schema"]), "hash": str(entry["hash"])}

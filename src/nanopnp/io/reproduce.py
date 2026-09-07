"""QR-08 made executable: a run directory back to the same numbers.

Section 3.3 promises that a result's manifest is sufficient to reconstruct the
run that produced it. A test can assert that; a *user* holding an archived run
directory and no test harness cannot, and a promise only a test can exercise is
not one. This module is the check, and :mod:`nanopnp.cli` is a shell over it.

**The cache must be defeated or the check asserts nothing.**
:meth:`~nanopnp.io.store.Store.get_or_compute` would serve the stored solution
artefact and the "reproduction" would be the assertion that a dictionary lookup
is deterministic. So the reproduction runs into a store that does not hold the
run, and :func:`reproduce` refuses — loudly, naming the store — if the solve was
served rather than re-entered (section 5.3.2 NOTE, QR-08).

**Input drift is fatal; library drift is reported.** A mesh whose contents moved
under a run makes the reproduction a different calculation, and nothing about
the numbers that come out of it would say so. A NumPy patch release is not that:
it is recorded, and if it moved a number the quantity diff is what catches it —
which is the assertion that matters. ``strict_environment`` turns the report
into a refusal for a caller who wants the stronger promise.
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, decode_floats, file_hash
from nanopnp.io.manifest import CASE_FILENAME, MANIFEST_FILENAME, environment
from nanopnp.io.manifest import read as read_manifest
from nanopnp.io.run import RUN_RECORD_FILENAME, run_case
from nanopnp.io.store import Store

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping

    from nanopnp.core.stages import CancelToken, Progress
    from nanopnp.io.run import RunResult

__all__ = [
    "DEFAULT_TOLERANCE",
    "Drift",
    "EnvironmentDrift",
    "InputMovedError",
    "Reproduction",
    "ReproductionError",
    "reproduce",
]

logger = logging.getLogger(__name__)

DEFAULT_TOLERANCE = 1e-6
"""Relative agreement every scalar must reach.

The case schema's own ``numerics.nonlinear.rtol`` (section 5.3.1, NUM-16) and
not a number chosen for this check: reproduction to solver tolerance is exactly
what QR-08 asks for. In process, on a deterministic direct solve, the expected
difference is 0.
"""


class InputMovedError(RuntimeError):
    """An input file's contents differ from what the manifest recorded."""


class ReproductionError(RuntimeError):
    """The run could not be reproduced, or the check could not be made honestly."""


@dataclass(frozen=True)
class Drift:
    """One scalar that did not come back, and by how much.

    Parameters
    ----------
    path
        Dotted path into the run record's quantities, e.g.
        ``currents_A.Na+``, so that a reader is pointed at the number rather
        than at the block containing it.
    recorded, reproduced
        The archived value and the one this run produced.
    relative
        ``|reproduced - recorded| / |recorded|``, or the absolute difference
        where the recorded value is zero. ``None`` where the values are not
        numbers, which is an inequality rather than a drift.
    """

    path: str
    recorded: Canonicalisable
    reproduced: Canonicalisable
    relative: float | None

    def summary(self) -> dict[str, Canonicalisable]:
        """Return this drift as plain data, for the CLI's ``--json``."""
        return {
            "quantity": self.path,
            "recorded": self.recorded,
            "reproduced": self.reproduced,
            "relative": self.relative,
        }


@dataclass(frozen=True)
class EnvironmentDrift:
    """One library, interpreter or platform key whose value moved."""

    key: str
    recorded: Canonicalisable
    current: Canonicalisable

    def summary(self) -> dict[str, Canonicalisable]:
        """Return this difference as plain data."""
        return {"key": self.key, "recorded": self.recorded, "current": self.current}


@dataclass(frozen=True)
class Reproduction:
    """What a reproduction attempt found.

    Parameters
    ----------
    directory
        The run directory that was reproduced.
    manifest_hash
        The archived manifest's hash, so a report names the run it is about.
    run
        The result of re-running the pipeline.
    quantities
        The recorded quantities, as the archived run record holds them.
    worst
        The largest relative difference over every scalar compared, or ``None``
        when the run recorded no number to compare.
    drifts
        Every scalar outside ``tolerance``, or unequal where it is not a number.
    environment
        Library, interpreter and platform differences. Reported, not fatal,
        unless ``strict_environment``.
    tolerance
        The relative agreement that was required.
    """

    directory: Path
    manifest_hash: str
    run: RunResult
    quantities: Mapping[str, Canonicalisable]
    worst: float | None
    drifts: tuple[Drift, ...]
    environment: tuple[EnvironmentDrift, ...]
    tolerance: float

    @property
    def reproduced(self) -> bool:
        """Whether every scalar came back within tolerance."""
        return not self.drifts

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the whole finding as plain data, for the CLI's ``--json``."""
        return {
            "directory": str(self.directory),
            "manifest": self.manifest_hash,
            "reproduced": self.reproduced,
            "tolerance": self.tolerance,
            "worst_relative_difference": self.worst,
            "compared": len(self.quantities),
            "drifts": [drift.summary() for drift in self.drifts],
            "environment": [difference.summary() for difference in self.environment],
            "stages": [record.summary() for record in self.run.stages],
        }


def _flatten(value: Canonicalisable, prefix: str = "") -> dict[str, Canonicalisable]:
    """Return a nested quantity record flattened to dotted paths.

    ``currents_A`` is a mapping of ion to current and ``route_agreement`` a
    mapping of route to figure; comparing them whole would report "the block
    differs" and leave a reader to find the ion.
    """
    if isinstance(value, dict):
        flat: dict[str, Canonicalisable] = {}
        for key, item in value.items():
            flat.update(_flatten(item, f"{prefix}.{key}" if prefix else str(key)))
        return flat
    return {prefix: value}


def _relative(recorded: float, reproduced: float) -> float:
    """Return the relative difference, falling back to the absolute one at zero."""
    difference = abs(reproduced - recorded)
    return difference / abs(recorded) if recorded != 0.0 else difference


def compare(
    recorded: Mapping[str, Canonicalisable],
    reproduced: Mapping[str, Canonicalisable],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> tuple[tuple[Drift, ...], float | None]:
    """Compare two quantity records and return the drifts and the worst figure.

    Every scalar is compared relatively; anything that is not a number — the
    ``2 pi`` convention, the route-check flag, the indicator band — must be
    *equal*, because a convention that changed makes the numbers beside it
    incomparable rather than merely different.

    Raises
    ------
    ReproductionError
        If the reproduction produced no value for a quantity the run recorded.
        A missing number is not a matching one.
    """
    left, right = _flatten(dict(recorded)), _flatten(dict(reproduced))
    missing = sorted(set(left) - set(right))
    if missing:
        raise ReproductionError(
            f"the reproduction produced no value for {', '.join(missing)}, which the archived "
            "run recorded; the case selects what is extracted, so this is a changed case rather "
            "than a changed number"
        )

    drifts: list[Drift] = []
    worst: float | None = None
    for path, value in sorted(left.items()):
        other = right[path]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            if value != other:
                drifts.append(Drift(path=path, recorded=value, reproduced=other, relative=None))
            continue
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            drifts.append(Drift(path=path, recorded=value, reproduced=other, relative=None))
            continue
        difference = _relative(float(value), float(other))
        worst = difference if worst is None else max(worst, difference)
        if difference > tolerance:
            drifts.append(Drift(path=path, recorded=value, reproduced=other, relative=difference))
    return tuple(drifts), worst


def check_inputs(manifest: Mapping[str, Canonicalisable], *, where: Path) -> None:
    """Re-hash every input file the manifest recorded, aborting on any that moved.

    Raises
    ------
    InputMovedError
        If a recorded input is absent or its contents differ. Both are fatal:
        a reproduction against a different mesh is a different calculation, and
        nothing about the numbers it produces would say so.
    """
    inputs = manifest.get("inputs")
    files = inputs.get("files", {}) if isinstance(inputs, dict) else {}
    if not isinstance(files, dict):
        return
    for role, record in sorted(files.items()):
        if not isinstance(record, dict):
            continue
        path = Path(str(record["path"]))
        recorded = str(record["sha256"])
        if role == "case":
            # The case travelled with the run: it is `case.yaml` in the run
            # directory, and the manifest embeds its text. Its recorded path is
            # wherever it was read from, which need not still exist.
            path = where / CASE_FILENAME
        if not path.is_file():
            raise InputMovedError(
                # Quoted rather than ``!r``: ``repr`` of a Windows path doubles
                # every separator, so the message would name a path the reader
                # cannot open. QR-12 asks for the location, not an escaping of
                # it (VER-35).
                f"the {role!r} input '{path}' recorded in {where / MANIFEST_FILENAME} "
                "is not there; a reproduction cannot be made from an input that is gone"
            )
        found = file_hash(path)
        if found != recorded:
            raise InputMovedError(
                f"the {role!r} input '{path}' has moved: the manifest recorded sha256 "
                f"{recorded} and the file now hashes to {found}. Reproducing against it would be "
                "a different calculation reported as the same one (QR-08)"
            )


def check_environment(
    manifest: Mapping[str, Canonicalisable],
) -> tuple[EnvironmentDrift, ...]:
    """Return every environment key whose value differs from this machine's."""
    recorded = manifest.get("environment")
    if not isinstance(recorded, dict):
        return ()
    current = environment()
    differences: list[EnvironmentDrift] = []
    for group in sorted(set(recorded) | set(current)):
        was, now = recorded.get(group), current.get(group)
        if not isinstance(was, dict) or not isinstance(now, dict):
            if was != now:
                differences.append(EnvironmentDrift(key=group, recorded=was, current=now))
            continue
        for key in sorted(set(was) | set(now)):
            if was.get(key) != now.get(key):
                differences.append(
                    EnvironmentDrift(
                        key=f"{group}.{key}", recorded=was.get(key), current=now.get(key)
                    )
                )
    return tuple(differences)


def _recorded_quantities(directory: Path) -> Mapping[str, Canonicalisable]:
    """Return the quantities the archived run record holds.

    Raises
    ------
    ReproductionError
        If there is no run record, or it carries no quantity. The manifest says
        how the run was configured; the run record is what it *produced*, and
        there is nothing to reproduce without it.
    """
    path = directory / RUN_RECORD_FILENAME
    if not path.is_file():
        raise ReproductionError(
            f"{path} is not there, so this run directory records no quantities to reproduce. "
            "A run written by 'nanopnp run' carries one beside its manifest"
        )
    # ``RunResult.write`` writes the record through ``canonical``, so every float
    # on disk is a ``{"__f__": <hex>}`` wrapper. Undo that here rather than in
    # ``compare``: the live side of the comparison holds bare floats, and a
    # comparison whose two sides disagree about the *encoding* reports a missing
    # quantity where the number is in fact there (section 5.3.2, QR-08).
    record = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    quantities = record.get("quantities") if isinstance(record, dict) else None
    if not isinstance(quantities, dict) or not quantities:
        raise ReproductionError(
            f"{path} records no quantities; the run it describes stopped before stage 11 and "
            "produced no number for a reproduction to compare"
        )
    return quantities


def reproduce(
    directory: str | Path,
    *,
    store: Store | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
    strict_environment: bool = False,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
) -> Reproduction:
    """Re-run an archived run and compare every scalar it reported (QR-08).

    Parameters
    ----------
    directory
        A run directory: ``manifest.json``, ``case.yaml`` and ``run.json``.
    store
        Where the reproduction's artefacts go. It must not already hold this
        run's solution — see the module docstring. ``None`` runs into a
        temporary directory that is removed afterwards, which is the honest
        default: the artefacts of a reproduction are not a result, the
        comparison is.
    tolerance
        Relative agreement every scalar must reach; :data:`DEFAULT_TOLERANCE`.
    strict_environment
        Whether a library, interpreter or platform difference is fatal.
    progress, cancel
        Threaded into the run.

    Returns
    -------
    Reproduction
        The comparison, whether or not it succeeded. The caller decides what a
        drift means; the CLI exits non-zero on one.

    Raises
    ------
    InputMovedError
        If a recorded input file is absent or its contents moved.
    ReproductionError
        If the run directory is incomplete, if its ``case.yaml`` disagrees with
        the text the manifest embeds, if the solve was served from the store
        rather than re-entered, or if the reproduction produced no value for a
        recorded quantity.
    """
    where = Path(directory)
    manifest_path = where / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ReproductionError(f"{manifest_path} is not there; this is not a run directory")
    manifest = read_manifest(manifest_path)

    case_path = where / CASE_FILENAME
    if not case_path.is_file():
        raise ReproductionError(f"{case_path} is not there; this is not a run directory")
    embedded = manifest.get("case")
    if isinstance(embedded, dict) and case_path.read_text(encoding="utf-8") != embedded.get("text"):
        raise ReproductionError(
            f"{case_path} differs from the case text embedded in {manifest_path}. They are written "
            "from one string, so one of them has been edited since the run"
        )

    recorded = _recorded_quantities(where)
    check_inputs(manifest, where=where)
    drift = check_environment(manifest)
    if drift and strict_environment:
        listed = ", ".join(f"{item.key}: {item.recorded!r} -> {item.current!r}" for item in drift)
        raise ReproductionError(
            f"the environment differs from the one recorded in {manifest_path} and "
            f"strict_environment is set: {listed}"
        )
    for item in drift:
        logger.warning(
            "environment differs: %s recorded %r, now %r", item.key, item.recorded, item.current
        )

    with tempfile.TemporaryDirectory(prefix="nanopnp-reproduce-") as scratch:
        target = store if store is not None else Store(Path(scratch) / "store")
        result = run_case(
            case_path,
            store=target,
            workspace=Path(scratch) / "work",
            write=False,
            progress=progress,
            cancel=cancel,
        )
        solve = next((record for record in result.stages if record.name == "solve"), None)
        if solve is not None and solve.cached:
            raise ReproductionError(
                f"the solve was served from the store at {target.root} rather than re-entered, so "
                "this reproduction would assert that a dictionary lookup is deterministic and "
                "nothing else. Reproduce into a store that does not hold the run (QR-08)"
            )
        drifts, worst = compare(recorded, result.quantities, tolerance=tolerance)

    reproduction = Reproduction(
        directory=where,
        manifest_hash=str(manifest.get("hash", "")),
        run=result,
        quantities=recorded,
        worst=worst,
        drifts=drifts,
        environment=drift,
        tolerance=tolerance,
    )
    logger.info(
        "reproduced %s: %d quantities, worst relative difference %s",
        where,
        len(_flatten(dict(recorded))),
        "none compared" if worst is None else f"{worst:.3e}",
    )
    return reproduction

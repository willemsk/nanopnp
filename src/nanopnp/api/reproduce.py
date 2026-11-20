"""QR-08 made executable: re-run an archived run directory and compare its numbers."""

from __future__ import annotations

import json
import logging
import math
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.core.hashing import Canonicalisable, decode_floats, file_hash
from nanopnp.io.artefact import FIELD_NORMS
from nanopnp.io.manifest import CASE_FILENAME, MANIFEST_FILENAME, environment
from nanopnp.io.manifest import read as read_manifest
from nanopnp.io.store import Store
from nanopnp.pipeline.run import RUN_RECORD_FILENAME, recorded_base

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.stages import CancelToken, Progress
    from nanopnp.pipeline.run import RunResult

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

# The schema default of numerics.nonlinear.rtol (NUM-16), the reproduction QR-08 asks for.
DEFAULT_TOLERANCE = 1e-6


class InputMovedError(RuntimeError):
    """An input file's contents differ from what the manifest recorded."""


class ReproductionError(RuntimeError):
    """The run could not be reproduced, or the check could not be made honestly."""


@dataclass(frozen=True)
class Drift:
    """One scalar that did not come back, and by how much."""

    path: str
    recorded: Canonicalisable
    reproduced: Canonicalisable
    relative: float | None

    def summary(self) -> dict[str, Canonicalisable]:
        """Return this drift as plain data."""
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
    worst
        The largest relative difference over every scalar compared, or None.
    drifts
        The scalars outside the tolerance, or unequal where they are not numbers.
    unchecked
        What the record could not be compared on, each said in words.
    """

    directory: Path
    manifest_hash: str
    run: RunResult
    quantities: Mapping[str, Canonicalisable]
    worst: float | None
    drifts: tuple[Drift, ...]
    environment: tuple[EnvironmentDrift, ...]
    tolerance: float
    upto: str | None = None
    unchecked: tuple[str, ...] = ()

    @property
    def reproduced(self) -> bool:
        """Return whether every scalar came back within tolerance."""
        return not self.drifts

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the whole finding as plain data."""
        return {
            "directory": str(self.directory),
            "manifest": self.manifest_hash,
            "reproduced": self.reproduced,
            "tolerance": self.tolerance,
            "upto": self.upto,
            "worst_relative_difference": self.worst,
            "compared": len(self.quantities),
            "not_compared": list(self.unchecked),
            "drifts": [drift.summary() for drift in self.drifts],
            "environment": [difference.summary() for difference in self.environment],
            "stages": [record.summary() for record in self.run.stages],
        }


def _flatten(value: Canonicalisable, prefix: str = "") -> dict[str, Canonicalisable]:
    if isinstance(value, dict):
        flat: dict[str, Canonicalisable] = {}
        for key, item in value.items():
            flat.update(_flatten(item, f"{prefix}.{key}" if prefix else str(key)))
        return flat
    return {prefix: value}


def _relative(recorded: float, reproduced: float) -> float:
    if recorded == reproduced or (math.isnan(recorded) and math.isnan(reproduced)):
        return 0.0
    if not (math.isfinite(recorded) and math.isfinite(reproduced)):
        return math.inf
    difference = abs(reproduced - recorded)
    return difference / abs(recorded) if recorded != 0.0 else difference


def compare(
    recorded: Mapping[str, Canonicalisable],
    reproduced: Mapping[str, Canonicalisable],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> tuple[tuple[Drift, ...], float | None]:
    """Compare two quantity records; return the drifts and the worst relative difference."""
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
        if not difference <= tolerance:
            drifts.append(Drift(path=path, recorded=value, reproduced=other, relative=difference))
    return tuple(drifts), worst


def check_inputs(manifest: Mapping[str, Canonicalisable], *, where: Path) -> None:
    """Re-hash every input file the manifest recorded, aborting on any that moved."""
    inputs = manifest.get("inputs")
    files = inputs.get("files", {}) if isinstance(inputs, dict) else {}
    if not isinstance(files, dict):
        return
    # A study's run reads its case.yaml, the merged case the manifest embeds; the study and model
    # files it was formed from are not read again, so an edit of them moves no reproduction.
    study = any(str(role).startswith("models.") for role in files)
    for role, record in sorted(files.items()):
        if not isinstance(record, dict):
            continue
        if study and (role == "case" or str(role).startswith("models.")):
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


def _recorded_directory(manifest: Mapping[str, Canonicalisable]) -> Path:
    # A relative path of the case is read against the directory of the case file the run read, so
    # the reproduction reads the files the run read (QR-08); a case held in memory read the
    # working directory.
    inputs = manifest.get("inputs")
    found = recorded_base(inputs) if isinstance(inputs, Mapping) else None
    return found if found is not None else Path.cwd()


def check_mesh(manifest: Mapping[str, Canonicalisable], result: RunResult, *, where: Path) -> None:
    """Abort if the reproduced mesh is not the one the manifest recorded."""
    group = manifest.get("geometry_and_mesh")
    recorded = group.get("content_hash") if isinstance(group, dict) else None
    artefact = result.artefacts.get("mesh")
    if recorded is None or artefact is None:
        return
    reproduced = artefact.summary.get("content_hash")
    if reproduced != recorded:
        origin = "generated" if group.get("generated") else "supplied"  # type: ignore[union-attr]
        raise InputMovedError(
            f"the {origin} mesh has moved: {where / MANIFEST_FILENAME} recorded content hash "
            f"{recorded} and the reproduction's mesh hashes to {reproduced}. A mesher that "
            "places vertices differently on this platform makes a different calculation, "
            "reported as the same one (QR-08, WP21 D13)"
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


def _recorded_run(directory: Path) -> Mapping[str, Canonicalisable]:
    path = directory / RUN_RECORD_FILENAME
    if not path.is_file():
        raise ReproductionError(
            f"{path} is not there, so this run directory records no stages to reproduce. "
            "A run written by 'nanopnp run' carries one beside its manifest"
        )
    # ``RunResult.write`` writes the record through ``canonical``, so every float
    # on disk is a ``{"__f__": <hex>}`` wrapper. Undo that here rather than in
    # ``compare``: the live side of the comparison holds bare floats, and a
    # comparison whose two sides disagree about the *encoding* reports a missing
    # quantity where the number is in fact there (section 5.3.2, QR-08).
    record = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(record, dict):
        raise ReproductionError(f"{path} is not a run record")
    return record


FLOOR = 1e-6
"""The share of the largest of a kind that a field's number is compared against at least: the
absolute floor of NUM-16's update test, under which Newton does not resolve a field."""


def compare_norms(
    recorded: Mapping[str, Canonicalisable],
    reproduced: Mapping[str, Canonicalisable],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> tuple[tuple[Drift, ...], float | None]:
    """Compare the solve's recorded field norms and integrals; return the drifts and the worst.

    Each number is compared relative to itself, or to ``FLOOR`` times the largest of its kind
    over the fields where it is smaller, as Newton converges a field (NUM-16). A number on one
    side only is a drift: the model's fields changed.
    """
    left = {path: value for path, value in _flatten(dict(recorded)).items()}
    right = {path: value for path, value in _flatten(dict(reproduced)).items()}
    largest: dict[str, float] = {}
    for path, value in left.items():
        if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
            kind = path.rsplit(".", 1)[-1].split("_")[0]
            largest[kind] = max(largest.get(kind, 0.0), abs(float(value)))
    drifts: list[Drift] = []
    worst: float | None = None
    for path in sorted(set(left) | set(right)):
        was, now = left.get(path), right.get(path)
        where = f"{FIELD_NORMS}.{path}"
        if not isinstance(was, int | float) or not isinstance(now, int | float):
            drifts.append(Drift(path=where, recorded=was, reproduced=now, relative=None))
            continue
        kind = path.rsplit(".", 1)[-1].split("_")[0]
        scale = max(abs(float(was)), FLOOR * max(largest.get(kind, 0.0), 1.0))
        if not (math.isfinite(was) and math.isfinite(now)):
            relative = 0.0 if was == now else math.inf
        else:
            relative = abs(float(now) - float(was)) / scale
        worst = relative if worst is None else max(worst, relative)
        if relative > tolerance:
            drifts.append(Drift(path=where, recorded=was, reproduced=now, relative=relative))
    return tuple(drifts), worst


def _recorded_stages(record: Mapping[str, Canonicalisable], *, where: Path) -> list[str]:
    entries = record.get("stages")
    names = (
        [str(entry["stage"]) for entry in entries if isinstance(entry, dict)]
        if isinstance(entries, list)
        else []
    )
    if not names:
        raise ReproductionError(f"{where / RUN_RECORD_FILENAME} lists no stage the run reached")
    return names


def _target_stage(upto: str | None, recorded: list[str], *, where: Path) -> str | None:
    last = recorded[-1]
    if upto is not None and upto not in recorded:
        raise ReproductionError(
            f"upto {upto!r} is past what {where / RUN_RECORD_FILENAME} recorded: the run stopped "
            f"at {last!r} (it reached {', '.join(recorded)}), so there is nothing recorded at "
            f"{upto!r} to reproduce"
        )
    if upto is not None:
        return upto
    return None if "qoi" in recorded else last


def _compare_artefacts(
    record: Mapping[str, Canonicalisable], result: RunResult, walked: Sequence[str]
) -> tuple[Drift, ...]:
    held = record.get("artefacts")
    recorded = held if isinstance(held, dict) else {}
    drifts: list[Drift] = []
    # A stage the record made within the walk that the reproduction did not make is a walk that
    # changed, not one that matched.
    for stage in walked:
        entry = recorded.get(stage)
        was = entry.get("hash") if isinstance(entry, dict) else None
        if was is not None and stage not in result.artefacts:
            drifts.append(
                Drift(path=f"artefacts.{stage}", recorded=was, reproduced=None, relative=None)
            )
    for stage, artefact in result.artefacts.items():
        entry = recorded.get(stage)
        was = entry.get("hash") if isinstance(entry, dict) else None
        if was is not None and was != artefact.hash:
            drifts.append(
                Drift(
                    path=f"artefacts.{stage}",
                    recorded=was,
                    reproduced=artefact.hash,
                    relative=None,
                )
            )
    return tuple(drifts)


def reproduce(
    directory: str | Path,
    *,
    store: Store | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
    strict_environment: bool = False,
    upto: str | None = None,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
) -> Reproduction:
    """Re-run an archived run and compare every scalar it reported.

    Parameters
    ----------
    directory
        A run directory holding manifest.json, case.yaml and run.json.
    store
        Where the artefacts go; None runs into a temporary directory.
    tolerance
        Relative agreement every scalar must reach.
    upto
        Reproduce only up to this stage, which the record must have reached; ``None`` reproduces
        the record to its last stage.
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
    if isinstance(embedded, dict) and case_path.read_bytes().decode("utf-8") != embedded.get(
        "text"
    ):
        raise ReproductionError(
            f"{case_path} differs from the case text embedded in {manifest_path}. They are written "
            "from one string, so one of them has been edited since the run"
        )

    record = _recorded_run(where)
    reached = _recorded_stages(record, where=where)
    last = _target_stage(upto, reached, where=where)
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
        session = Session(target, write=False, workspace=Path(scratch) / "work")
        result = session.run(
            Case.load(case_path, base=_recorded_directory(manifest)),
            upto=last,
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
        if solve is None and result.stages and all(stage.cached for stage in result.stages):
            raise ReproductionError(
                f"every stage up to {result.stages[-1].name!r} was served from the store at "
                f"{target.root} rather than re-entered, so this reproduction would compare the "
                "record with itself. Reproduce into a store that does not hold the run (QR-08)"
            )
        check_mesh(manifest, result, where=where)
        walked = reached if last is None else reached[: reached.index(last) + 1]
        stage_drifts = _compare_artefacts(record, result, walked)
        # A walk stopped short of the record's that did not run stage 7 records why it did not,
        # not what the record's stage 7 made, so its charge group has nothing to compare.
        charge_drifts: tuple[Drift, ...] = ()
        charge_worst: float | None = None
        if last is None or last == reached[-1] or "charge" in result.artefacts:
            was_charge = decode_floats(manifest.get("charge", {}))
            charge_drifts, charge_worst = compare(
                {"charge": was_charge if isinstance(was_charge, dict) else {}},
                {"charge": dict(result.manifest.charge)},
                tolerance=tolerance,
            )
        recorded: Mapping[str, Canonicalisable] = {}
        quantity_drifts: tuple[Drift, ...] = ()
        quantity_worst: float | None = None
        if "qoi" in result.artefacts:
            held = record.get("quantities")
            if not isinstance(held, dict) or not held:
                raise ReproductionError(
                    f"{where / RUN_RECORD_FILENAME} records no quantities although the run "
                    "reached the qoi stage; there is no number for a reproduction to compare"
                )
            recorded = held
            quantity_drifts, quantity_worst = compare(
                recorded, result.quantities, tolerance=tolerance
            )
        # The solve's key covers its inputs, not the state it reached: the fields' norms are the
        # numbers a reproduction stopped at its solve compares.
        norm_drifts: tuple[Drift, ...] = ()
        norm_worst: float | None = None
        unchecked: tuple[str, ...] = ()
        held_norms = record.get(FIELD_NORMS)
        if "solve" in result.artefacts and isinstance(held_norms, dict) and held_norms:
            norm_drifts, norm_worst = compare_norms(
                held_norms, result.field_norms, tolerance=tolerance
            )
        elif "solve" in result.artefacts:
            unchecked = (
                "the solve's state: the record was written before the solve recorded its "
                "fields' norms, so no number of the solve is compared",
            )
            logger.warning("%s: %s", where, unchecked[0])
        drifts = stage_drifts + charge_drifts + quantity_drifts + norm_drifts
        found = [value for value in (charge_worst, quantity_worst, norm_worst) if value is not None]
        worst = max(found) if found else None

    reproduction = Reproduction(
        directory=where,
        manifest_hash=str(manifest.get("hash", "")),
        run=result,
        quantities=recorded,
        worst=worst,
        drifts=drifts,
        environment=drift,
        tolerance=tolerance,
        upto=last,
        unchecked=unchecked,
    )
    logger.info(
        "reproduced %s: %d quantities, worst relative difference %s",
        where,
        len(_flatten(dict(recorded))),
        "none compared" if worst is None else f"{worst:.3e}",
    )
    return reproduction

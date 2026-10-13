"""Collection of the members' records into one dataset, and the rectification (FR-24, FR-23)."""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from nanopnp.core.hashing import Canonicalisable, canonical, decode_floats
from nanopnp.io.artefact import SWEEP_SCHEMA, SweepArtefact
from nanopnp.io.store import atomic_write_bytes
from nanopnp.sweep.plan import SweepPlan
from nanopnp.sweep.run import MEMBERS_DIRNAME, MemberResult, member_from_row

logger = logging.getLogger(__name__)

__all__ = [
    "DATASET_CSV",
    "DATASET_FILENAME",
    "SweepCollectionError",
    "collect",
    "read_members",
    "write_csv",
]

DATASET_FILENAME = "dataset.json"

DATASET_CSV = "dataset.csv"

CSV_NOTE = (
    "# derived export of dataset.json; the dataset is the artefact (SPECIFICATION.md 5.3.4). "
    "An empty quantity cell is a member that produced no number -- read the status column."
)


class SweepCollectionError(RuntimeError):
    """A dataset cannot be built from the members that ran."""


def read_members(directory: Path) -> tuple[MemberResult, ...]:
    """Read every member record under a sweep directory, in index order."""
    members = directory / MEMBERS_DIRNAME
    found: list[MemberResult] = []
    for path in sorted(members.glob("*.json")):
        try:
            raw = decode_floats(json.loads(path.read_text(encoding="utf-8")))
            if not isinstance(raw, dict):
                raise TypeError(f"holds a {type(raw).__name__}, not a member record")
            found.append(member_from_row(raw))
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise SweepCollectionError(
                f"{path} is not a readable member record: {error}. A member whose result cannot "
                "be read is not a member that failed; re-run it rather than collecting around it"
            ) from None
    return tuple(sorted(found, key=lambda member: member.index))


def _rectification(
    plan: SweepPlan, rows: Mapping[int, MemberResult]
) -> tuple[list[dict[str, Canonicalisable]], list[str]]:
    from nanopnp.post.qoi import rectification_ratio

    produced: list[dict[str, Canonicalisable]] = []
    notes: list[str] = []
    for forward_index, reverse_index in plan.pairs:
        forward, reverse = rows.get(forward_index), rows.get(reverse_index)
        plus, minus = _current(forward), _current(reverse)
        if forward is None or reverse is None or plus is None or minus is None:
            notes.append(
                f"no rectification for points {forward_index} and {reverse_index}: "
                + ", ".join(
                    f"point {index} {_why(rows.get(index))}"
                    for index in (forward_index, reverse_index)
                )
            )
            continue
        plus_V, minus_V = _bias(forward), _bias(reverse)
        if plus_V is not None and minus_V is not None and plus_V < 0.0:
            # Under ground: trans the recorded bias is the cis-referenced one, the
            # negative of the assigned bias (post.qoi.cis_referenced_bias), so the
            # pair planned as (+V, -V) solved (-V, +V) in the current's convention.
            forward_index, reverse_index = reverse_index, forward_index
            forward, reverse = reverse, forward
            plus, minus = minus, plus
            plus_V, minus_V = minus_V, plus_V
        if plus_V is None or minus_V is None or plus_V <= 0.0 or plus_V + minus_V != 0.0:
            raise SweepCollectionError(
                f"points {forward_index} and {reverse_index} were paired as opposite biases but "
                f"the members recorded {plus_V} V and {minus_V} V; the ratio would compare "
                "two unrelated operating points"
            )
        if minus == 0.0:
            notes.append(
                f"no rectification for points {forward_index} and {reverse_index}: the reverse "
                "current is exactly zero, where the ratio is undefined"
            )
            continue
        produced.append(
            {
                "forward": forward_index,
                "reverse": reverse_index,
                "forward_id": forward.point_id,
                "reverse_id": reverse.point_id,
                "bias_V": plus_V,
                "rectification": rectification_ratio(plus, minus),
            }
        )
    return produced, notes


def _current(member: MemberResult | None) -> float | None:
    if member is None or member.quantities is None:
        return None
    found = member.quantities.get("current_A")
    return float(found) if isinstance(found, int | float) else None


def _bias(member: MemberResult) -> float | None:
    if member.quantities is None:
        return None
    found = member.quantities.get("bias_V")
    return float(found) if isinstance(found, int | float) else None


def _why(member: MemberResult | None) -> str:
    if member is None:
        return "was never dispatched"
    if member.status != "ok":
        return f"exited {member.exit_class} ({member.status})"
    return "reported no current; its case did not ask for one"


def collect(
    plan: SweepPlan,
    directory: Path,
    *,
    members: Sequence[MemberResult] | None = None,
) -> SweepArtefact:
    """Assemble the dataset over one sweep's members and write it.

    Parameters
    ----------
    plan
        The plan the members were dispatched from; it supplies the point order.
    """
    found = tuple(members) if members is not None else read_members(directory)
    by_index = {member.index: member for member in found}
    unknown = sorted(set(by_index) - {point.index for point in plan.points})
    if unknown:
        raise SweepCollectionError(
            f"{directory} holds records for points {unknown}, which this plan does not "
            f"enumerate ({len(plan.points)} points); the directory belongs to another sweep"
        )

    rows = [
        by_index[point.index].row()
        if point.index in by_index
        else _undispatched(point.index, point.point_id, point.assignments, point.wave)
        for point in plan.points
    ]
    ratios, notes = _rectification(plan, by_index) if plan.rectification else ([], [])
    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1

    summary: dict[str, Canonicalisable] = {
        "plan": plan.hash,
        "points": len(plan.points),
        "counts": dict(sorted(counts.items())),
        "exit_classes": _exit_classes(rows),
        "seconds": sum(float(row["seconds"]) for row in rows),
        "iterations": sum(int(row["iterations"] or 0) for row in rows),
        "uncached": sum(1 for row in rows if row["status"] == "ok" and not row["cached"]),
        "warnings": list(plan.warnings),
        "rectification": ratios,
        "rectification_notes": notes,
        "rows": rows,
    }
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / DATASET_FILENAME
    atomic_write_bytes(path, canonical({"schema": SWEEP_SCHEMA, **summary}) + b"\n")
    logger.info(
        "collected %d point(s) into %s: %s",
        len(rows),
        path,
        ", ".join(f"{count} {status}" for status, count in sorted(counts.items())),
    )
    return SweepArtefact(
        plan_hash=plan.hash,
        base_hash=plan.base_hash,
        name=plan.name,
        points=len(plan.points),
        payload={"dataset": path},
        summary=summary,
    )


def _undispatched(
    index: int, point_id: str, assignments: Mapping[str, Canonicalisable], wave: int
) -> dict[str, Canonicalisable]:
    row = MemberResult(
        index=index,
        point_id=point_id,
        assignments=assignments,
        wave=wave,
        status="not_dispatched",
    ).row()
    row["exit_class"] = None
    return row


def _exit_classes(rows: Sequence[Mapping[str, Canonicalisable]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        if row["status"] == "ok" or row["exit_class"] is None:
            continue
        key = str(row["exit_class"])
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


CSV_COLUMNS: tuple[str, ...] = (
    "status",
    "index",
    "id",
    "wave",
    "exit_class",
    "cached",
    "seconds",
    "iterations",
    "route_agreement",
    "warm_start",
    "min_wall_distance_nm",
)


def write_csv(artefact: SweepArtefact, directory: Path) -> Path:
    """Write the flat CSV export beside the dataset and return its path."""
    rows = artefact.summary.get("rows", [])
    assignments = sorted({path for row in rows for path in dict(row["assignments"])})
    # Scalars only. A flat table has one cell per quantity, and a quantity that
    # is a mapping or a list -- the per-species currents, the indicator band --
    # would be rendered as its ``repr`` and read back as a string. Those live in
    # the dataset, which is the artefact; this is the export.
    quantities = sorted(
        {
            name
            for row in rows
            if row["quantities"] is not None
            for name, value in dict(row["quantities"]).items()
            if isinstance(value, bool | int | float | str) or value is None
        }
    )
    path = directory / DATASET_CSV
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"{CSV_NOTE}\n")
        writer = csv.writer(handle)
        writer.writerow([*CSV_COLUMNS, *assignments, *quantities])
        for row in rows:
            values = dict(row["quantities"] or {})
            wall = dict(row["wall_distance"] or {})
            warm = dict(row["warm_start"] or {})
            writer.writerow(
                [
                    row["status"],
                    row["index"],
                    row["id"],
                    row["wave"],
                    "" if row["exit_class"] is None else row["exit_class"],
                    row["cached"],
                    f"{float(row['seconds']):.3f}",
                    "" if row["iterations"] is None else row["iterations"],
                    "" if row["route_agreement"] is None else row["route_agreement"],
                    warm.get("status", ""),
                    wall.get("minimum_nm", ""),
                    *[dict(row["assignments"]).get(path, "") for path in assignments],
                    *["" if row["status"] != "ok" else values.get(name, "") for name in quantities],
                ]
            )
    logger.info("wrote %s", path)
    return path

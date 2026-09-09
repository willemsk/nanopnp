"""Collection: the members' records into one dataset, and the rectification (FR-24, FR-23).

The dataset is the artefact a sweep produces, and its shape is decided by one
requirement: **a failed member must be distinguishable** — from a refused one,
from one that was never dispatched, and above all from one that returned a
number (QR-06). So every row carries a status and, where it failed, the §3.1
exit class and the diagnostic verbatim; and a member that did not succeed has
its quantities recorded as ``null`` rather than defaulted. Canonical JSON has
``null``; a flat CSV has the empty string, which a reader parses as ``0.0`` on a
bad day, which is why the CSV is a derived export that says so in its header and
why its **first column is the status**.

``rectification`` is the one derived quantity produced here, and the only one.
``RR = |I(+V)|/|I(-V)|`` is the single quantity of §6.7 that one operating point
cannot produce, and §5.3.1 already says it can only come from a sweep. Everything
else the members report is already per-point. An I-V slope or a fitted
conductance would each be a term nobody checks against an analytic result, and
post-processing has its own tier.
"""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from nanopnp.core.hashing import Canonicalisable, canonical, decode_floats
from nanopnp.io.artefact import SWEEP_SCHEMA, SweepArtefact
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
"""The collected dataset, written through the canonical serialisation of §5.3.2."""

DATASET_CSV = "dataset.csv"
"""The flat export beside it. Derived, not normative; see :func:`write_csv`."""

CSV_NOTE = (
    "# derived export of dataset.json; the dataset is the artefact (SPECIFICATION.md 5.3.4). "
    "An empty quantity cell is a member that produced no number -- read the status column."
)
"""Header comment the CSV carries, so a reader of the flat file knows what it is."""


class SweepCollectionError(RuntimeError):
    """A dataset cannot be built from the members that ran.

    A ``RuntimeError`` and IF-02 exit 4, the gate class: rather than report a
    table it cannot build honestly, the collector stops and names what is wrong
    (QR-12). Distinguished from :class:`~nanopnp.sweep.plan.SweepPlanError`,
    which refuses a sweep before it runs: this one is raised after members have
    already produced results, and the fix is to run the missing ones rather than
    to edit a document.
    """


def read_members(directory: Path) -> tuple[MemberResult, ...]:
    """Read every member record written under a sweep directory.

    Whatever is there, in index order. A job array writes these from independent
    processes and possibly from independent machines, so the collector's job is
    to read what arrived rather than to know what should have.

    Raises
    ------
    SweepCollectionError
        If a record is not readable JSON or is missing a field. A truncated
        record is a member whose result is *unknown*, which is not the same as
        a member that failed, and guessing which would put a wrong row in the
        dataset.
    """
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
    """Return the rectification of every matched pair, and a note for each one missing.

    A pair contributes a ratio only when *both* its members succeeded and both
    reported a current. A pair with one failed member is reported as a note
    rather than as a null row: the sweep knows exactly why that ratio is absent,
    and a reader who has to infer it from a gap is a reader who will infer
    something else.

    The ratio is ``|I(+V)|/|I(-V)|``, which is
    :func:`nanopnp.post.qoi.rectification_ratio` — the same function
    :func:`nanopnp.post.qoi.rectification` computes after checking the signs of
    the two biases. The signs are checked here too, against the *recorded*
    biases rather than against the plan's assignments, because the assignment is
    what was asked for and the recorded bias is what the member solved.
    """
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
    """Return a member's total current, or ``None`` if it produced none."""
    if member is None or member.quantities is None:
        return None
    found = member.quantities.get("current_A")
    return float(found) if isinstance(found, int | float) else None


def _bias(member: MemberResult) -> float | None:
    """Return the bias the member actually solved at, from its own record."""
    if member.quantities is None:
        return None
    found = member.quantities.get("bias_V")
    return float(found) if isinstance(found, int | float) else None


def _why(member: MemberResult | None) -> str:
    """Return why one half of a pair contributed nothing, in a phrase."""
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
        The plan the members were dispatched from. It supplies the point order,
        the identities and the rectification pairs, so a dataset is a statement
        about a plan rather than about whichever files happened to be present.
    directory
        The sweep directory. ``dataset.json`` is written into it.
    members
        The records, when the caller already has them. Read from
        ``members/`` otherwise, which is the job-array path.

    Returns
    -------
    SweepArtefact
        Keyed on the plan and the base case; carrying the rows, the counts and
        the rectification as its summary, and ``dataset.json`` as its payload.
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
    path.write_bytes(canonical({"schema": SWEEP_SCHEMA, **summary}) + b"\n")
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
    """Return the row of a point no member record was found for.

    A row rather than a gap. "Never dispatched" is one of the three states QR-06
    asks a reader to be able to tell apart, and it is the one a missing row
    would render as silence.
    """
    return {
        "index": index,
        "id": point_id,
        "assignments": dict(assignments),
        "wave": wave,
        "status": "not_dispatched",
        "exit_class": None,
        "error": None,
        "quantities": None,
        "directory": None,
        "manifest": None,
        "solution": None,
        "seconds": 0.0,
        "iterations": None,
        "cached": False,
        "warm_start": None,
        "wall_distance": None,
        "route_agreement": None,
    }


def _exit_classes(rows: Sequence[Mapping[str, Canonicalisable]]) -> dict[str, int]:
    """Return how many members ended in each §3.1 exit class."""
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
"""Fixed leading columns of the CSV export, status first.

Status first on purpose: it is the column a reader must not be able to miss,
and the assignments and quantities that follow are the ones they came for.
"""


def write_csv(artefact: SweepArtefact, directory: Path) -> Path:
    """Write the flat export beside the dataset and return its path.

    The format the author actually opens, and a *derived* one: the dataset is
    the artefact, the CSV says so in its first line, and every quantity cell of
    a non-``ok`` row is left empty rather than filled with a zero that a reader
    would parse as a measurement.
    """
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

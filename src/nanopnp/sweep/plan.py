"""The sweep plan: the points, the warm-start forest, and everything checked before a solve.

FR-24 is one sentence with four verbs — sweep any case-file field, dispatch the
points as independent jobs, warm-start each solve from a converged neighbour,
collect the results into one dataset — and the second and third contradict each
other on their face. Independent jobs have no predecessors; a warm start is a
predecessor. This module is where they are reconciled, and the shape of the
answer is a **forest**.

**The forest.** For a grid of axis lengths ``n_1 … n_k`` with origins ``o_j``,
the parent of the point at ``(i_1 … i_k)`` is that point with the **last** index
differing from its origin moved one step towards it. Every point therefore has
exactly one parent, every edge is one grid step — 50 mV in bias, one
multiplicative step in concentration, both steps the envelope walk has already
demonstrated — and the depth of a point is ``Σ_j |i_j - o_j|``. Points at one
depth are mutually independent, so the depth *is* the wave, and the plan orders
its points by it, which makes each wave a contiguous range of indices a job
array can be submitted over (§5.3.4).

**Everything is checked here.** Every point is substituted, validated and
``resolve()``d when the plan is built, before a single solve, because
:func:`~nanopnp.io.case.resolve` is pure Python — no NGSolve, no mesh — and it is
where the NUM-18 refusals live. A 3,675-point plan whose two-thousandth point is
inadmissible must fail in seconds rather than at hour twenty-two. The NUM-34
wall-distance gate runs here too, once per *distinct mesh* where any point
activates a wall correction: one linear solve on a command run once, against
3,675 identical aborts at wave 0.

**Identity is not the index.** A point's ``point_id`` is the content hash of its
assignment mapping; its index is its position in the plan. Inserting one
concentration renumbers every index after it, and a dataset keyed on the index
would silently relabel last week's results.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import cast

from nanopnp.core.hashing import Canonicalisable, canonical, content_hash, decode_floats, short
from nanopnp.io.artefact import SWEEP_SCHEMA, CaseArtefact
from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
    FieldValue,
    UnknownCasePathError,
    field_at,
    load_case,
    resolve,
    substitute,
)
from nanopnp.sweep.document import SweepDocument, load_sweep, merged

logger = logging.getLogger(__name__)

__all__ = [
    "PLAN_FILENAME",
    "POINT_SCHEMA",
    "Point",
    "SweepPlan",
    "SweepPlanError",
    "build_plan",
    "plan_from_document",
    "read_plan",
    "write_plan",
]

PLAN_FILENAME = "plan.json"
"""Name of the plan file inside a sweep directory."""

POINT_SCHEMA = "nanopnp/sweep/point/v1"
"""Domain separator of a point's identity hash.

Its own schema rather than the sweep's, because what is hashed is one point's
assignment mapping and nothing else: the same operating point reached from two
different sweep documents is the same point, and keying the dataset on it is
what lets a second sweep over an overlapping grid recognise the members it
already has.
"""

ID_LENGTH = 12
"""Hex characters of the point identity carried in a member's name and dataset row.

Twelve, matching :func:`nanopnp.core.hashing.short`: long enough that a
collision over the thousands of points of §8.3 is not a thing that happens, and
short enough to read in a run directory's name. A collision is refused rather
than trusted not to occur -- see :func:`_identify`.
"""

RECTIFICATION = "rectification"
"""The one output a sweep strips from its members and produces in collection."""


class SweepPlanError(ValueError):
    """A sweep cannot be planned as written.

    A ``ValueError`` and IF-02 exit 3, the case class: a plan is refused by an
    edit to the sweep document or to the base case, never by a retry. Every
    message names what was wrong and where, as QR-12 requires -- the axis, the
    point, the path, or the mesh.
    """


@dataclass(frozen=True)
class Point:
    """One member of a sweep: what it varies, where it sits, and who it starts from.

    Parameters
    ----------
    index
        Position in the plan, and the integer a job array dispatches on. Points
        are ordered by wave, so a wave is a contiguous range of these.
    point_id
        The first :data:`ID_LENGTH` hex characters of the content hash of
        :attr:`assignments`. This is the identity: it keys the dataset, it names
        the member, and it does not move when a value is inserted on another
        axis.
    coordinates
        The point's index along each axis, in declaration order.
    assignments
        Dotted case-file paths to the values this member sets.
    parent
        Index of the point one grid step nearer the origins, or ``None`` for the
        root of a tree.
    wave
        The point's depth, ``Σ_j |i_j - o_j|``. Every point of one wave is
        independent of every other.
    name
        The member's case ``name:``, ``f"{base}-{point_id}"``. It reaches the
        manifest and the run directory and nothing that keys a solve, which is
        what makes rewriting it free.
    """

    index: int
    point_id: str
    coordinates: tuple[int, ...]
    assignments: Mapping[str, FieldValue]
    parent: int | None
    wave: int
    name: str

    def summary(self) -> dict[str, Canonicalisable]:
        """Return this point as the plan file records it."""
        return {
            "index": self.index,
            "id": self.point_id,
            "coordinates": list(self.coordinates),
            "assignments": dict(self.assignments),
            "parent": self.parent,
            "wave": self.wave,
            "name": self.name,
        }


@dataclass(frozen=True)
class SweepPlan:
    """Every point of a sweep, ordered by wave, with the checks already made.

    Parameters
    ----------
    name
        The sweep's name, from its document.
    base_path
        Path of the base case, as the plan will read it back.
    base_hash
        Content hash of the validated base case document. In the plan's digest,
        so that a plan built against an edited base case is a different plan.
    document
        The sweep document's own record of what was asked for.
    points
        Every point, ordered by wave and, within a wave, by the Cartesian
        product in axis declaration order.
    rectification
        Whether the base case asked for it, and the matched opposite-bias pairs
        the collector will produce it from.
    warnings
        Plan-time warnings: an axis over ``inputs.mesh`` defeats the warm start
        and is warned about rather than refused, VAL-04's mesh-convergence study
        being a sweep of exactly that shape.
    wall_distance
        The NUM-34 measurement of each distinct mesh a point activates a wall
        correction on, by the mesh's content hash.
    """

    name: str
    base_path: Path
    base_hash: str
    document: Mapping[str, Canonicalisable]
    points: tuple[Point, ...]
    rectification: bool = False
    pairs: tuple[tuple[int, int], ...] = ()
    warnings: tuple[str, ...] = ()
    wall_distance: Mapping[str, Canonicalisable] = field(default_factory=dict)

    @property
    def hash(self) -> str:
        """The plan's content hash: what it enumerates, not what it produced."""
        return content_hash(
            SWEEP_SCHEMA,
            {
                "name": self.name,
                "document": dict(self.document),
                "points": [point.summary() for point in self.points],
            },
            {"base_case": self.base_hash},
        )

    def waves(self) -> tuple[tuple[int, int], ...]:
        """Return each wave as a half-open ``(first, last + 1)`` index range.

        Contiguous by construction: the points are ordered by wave, so a
        scheduler submits one dependent array per range and needs to know
        nothing else about the forest.
        """
        ranges: list[tuple[int, int]] = []
        for point in self.points:
            if point.wave == len(ranges):
                ranges.append((point.index, point.index + 1))
            else:
                first, _ = ranges[point.wave]
                ranges[point.wave] = (first, point.index + 1)
        return tuple(ranges)

    def point(self, index: int) -> Point:
        """Return one point by index.

        Raises
        ------
        SweepPlanError
            If the index is not one this plan enumerates. Named rather than an
            ``IndexError``: a job array submitted over the wrong range is a
            configuration mistake, and the message says how many points there
            are.
        """
        if not 0 <= index < len(self.points):
            raise SweepPlanError(
                f"this plan enumerates {len(self.points)} points, 0 to {len(self.points) - 1}; "
                f"there is no point {index}"
            )
        return self.points[index]

    def case(self, index: int) -> CaseDocument:
        """Return the validated case document of one member.

        Rebuilt from the base case and the point's assignments rather than
        stored: the plan file would otherwise carry thousands of whole case
        documents, and a case rebuilt by the same :func:`substitute` the plan
        validated with cannot be a different one.

        Raises
        ------
        SweepPlanError
            If the base case is not where the plan left it, or if its content
            hash has moved. A job array dispatches over a plan file and rebuilds
            each member from the base case on disk; a base case edited between
            planning and dispatch — or a plan file copied to a machine where that
            path means something else — would have every member solve a case the
            plan never enumerated and report it under the plan's own point
            identities. That is the one way this design can produce a whole
            dataset of plausible wrong answers, so it is checked rather than
            assumed (QR-12).
        """
        point = self.point(index)
        try:
            base = load_case(self.base_path)
        except FileNotFoundError as error:
            raise SweepPlanError(
                f"this plan's base case {self.base_path} is not there: {error}. A member is "
                "rebuilt from the base case on disk, so the plan and the case have to travel "
                "together"
            ) from None
        found = CaseArtefact(base).hash
        if found != self.base_hash:
            raise SweepPlanError(
                f"this plan was built against a different {self.base_path}:\n"
                f"  planned against: {self.base_hash}\n"
                f"  on disk now:     {found}\n"
                "Every member would solve a case this plan never enumerated and report it under "
                "the plan's own point identities; re-plan the sweep"
            )
        return _member(base, point)

    def document_record(self) -> dict[str, Canonicalisable]:
        """Return the plan as it is written to disk."""
        return {
            "schema": SWEEP_SCHEMA,
            "name": self.name,
            "hash": self.hash,
            "base": {"path": str(self.base_path), "hash": self.base_hash},
            "sweep": dict(self.document),
            "rectification": self.rectification,
            "pairs": [list(pair) for pair in self.pairs],
            "warnings": list(self.warnings),
            "wall_distance": dict(self.wall_distance),
            "waves": [list(span) for span in self.waves()],
            "points": [point.summary() for point in self.points],
        }


def _member(base: CaseDocument, point: Point) -> CaseDocument:
    """Return the case document one point runs.

    The point's assignments, the rewritten ``name:``, and ``rectification``
    stripped from ``outputs:`` — the last because it is a two-point quantity the
    collector produces from a matched pair, and a member asking for it at one
    operating point is refused by the §5.3.1 NOTE.
    """
    assignments = dict(point.assignments)
    assignments["name"] = point.name
    outputs = [word for word in base.outputs if word != RECTIFICATION]
    if outputs != list(base.outputs):
        assignments["outputs"] = outputs
    return substitute(base, assignments)


def _shown(assignments: Mapping[str, FieldValue]) -> str:
    """Return an assignment mapping as one readable line, for a diagnostic."""
    return json.dumps(dict(assignments), sort_keys=True, default=str)


def _identify(
    assignments: Mapping[str, FieldValue], seen: dict[str, Mapping[str, FieldValue]]
) -> str:
    """Return a point's identity, refusing a collision rather than trusting one away.

    Two distinct assignment mappings sharing an identity would key one dataset
    row, and the sweep would report one of them twice. Equal mappings sharing one
    is a *duplicate point*, which means an axis declares the same value twice,
    and is refused with the axis's own vocabulary rather than a hash.
    """
    digest = short(content_hash(POINT_SCHEMA, dict(assignments)), ID_LENGTH)
    previous = seen.get(digest)
    if previous is not None:
        if dict(previous) == dict(assignments):
            raise SweepPlanError(
                f"two points of this sweep carry identical assignments {_shown(assignments)}; "
                "an axis declares the same value twice, and the two members would key one "
                "dataset row"
            )
        raise SweepPlanError(  # pragma: no cover - a 48-bit collision
            f"two different points share the identity {digest!r}; widen ID_LENGTH"
        )
    seen[digest] = dict(assignments)
    return digest


def _parent_of(coordinates: Sequence[int], origins: Sequence[int]) -> tuple[int, ...] | None:
    """Return the grid coordinates of a point's parent, or ``None`` for a root.

    The **last** index differing from its origin, moved one step towards it. The
    last rather than the first so that the axes declared earlier are walked
    outermost, which is what makes a wave of the deepest axis contiguous in the
    Cartesian product and keeps the trees shallow in the axes a sweep varies
    most finely.
    """
    for axis in range(len(coordinates) - 1, -1, -1):
        if coordinates[axis] != origins[axis]:
            step = -1 if coordinates[axis] > origins[axis] else 1
            moved = list(coordinates)
            moved[axis] += step
            return tuple(moved)
    return None


def _depth(coordinates: Sequence[int], origins: Sequence[int]) -> int:
    """Return a point's depth in the forest: the sum of its distances from the origins."""
    return sum(abs(index - origin) for index, origin in zip(coordinates, origins, strict=True))


def _check_axes(document: SweepDocument) -> None:
    """Check every path and every value against the case schema, before any point exists.

    Two loud failures rather than one: :func:`~nanopnp.io.case.field_at` names a
    component that does not exist and the prefix that does, and
    :meth:`~nanopnp.io.case.FieldReference.validate` names a value the declared
    type would not accept. Re-validating each substituted document would catch
    both, but only per point and only after the plan had committed to thousands
    of them.
    """
    for axis in document.axes:
        for position, assignment in enumerate(axis.points()):
            for path, value in assignment.items():
                try:
                    field_at(path).validate(value)
                except (UnknownCasePathError, CaseValidationError) as error:
                    raise SweepPlanError(f"axis {axis.name!r}, value {position}: {error}") from None


def _warnings(document: SweepDocument) -> tuple[str, ...]:
    """Return the plan-time warnings, naming the axis each one is about.

    One today: an axis over ``inputs.mesh``. It is warned about and not refused.
    :func:`~nanopnp.solve.continuation.transfer` refuses a cross-mesh
    interpolation deliberately — a point evaluation outside the source domain
    returns a plausible number rather than raising — so the forest degenerates
    to one-point trees and every member is cold. That is correct, only slower,
    and VAL-04's mesh-convergence study is a sweep of exactly that shape.
    """
    found = [
        f"axis {axis.name!r} varies {path!r}, so no member can warm-start from its neighbour: "
        "a transfer between two meshes is a point evaluation outside the source domain, which "
        "returns a plausible number rather than raising, and is refused. Every member of this "
        "sweep will climb the full NUM-18 ladder"
        for axis in document.axes
        for path in axis.paths()
        if path == "inputs.mesh" or path.startswith("inputs.mesh.")
    ]
    return tuple(found)


def _pairs(points: Sequence[Point]) -> tuple[tuple[int, int], ...]:
    """Return the ``(forward, reverse)`` index pairs the rectification comes from.

    Two points pair when their assignment mappings are equal except at
    ``boundary_conditions.bias_V``, and those two biases are **exactly**
    opposite. Exactly, not approximately:
    :func:`~nanopnp.post.qoi.rectification` already refuses two biases of the
    same sign, and a tolerance on the pairing would let an asymmetric bias axis
    report the ratio between 100 mV and -95 mV as a rectification (§5.3.1 NOTE).
    """
    bias = "boundary_conditions.bias_V"
    by_rest: dict[str, dict[float, int]] = {}
    for point in points:
        if bias not in point.assignments:
            continue
        rest = {path: value for path, value in point.assignments.items() if path != bias}
        key = canonical(rest).decode("utf-8")
        by_rest.setdefault(key, {})[float(point.assignments[bias])] = point.index
    found: list[tuple[int, int]] = []
    for biases in by_rest.values():
        for value, index in sorted(biases.items()):
            if value > 0.0 and -value in biases:
                found.append((index, biases[-value]))
    return tuple(sorted(found))


def build_plan(
    document: SweepDocument,
    *,
    source: Path | None = None,
    check_meshes: bool = True,
) -> SweepPlan:
    """Enumerate, check and order every point of a sweep (FR-24, §5.3.4).

    Parameters
    ----------
    document
        The validated sweep specification.
    source
        Where it was read from, used to resolve the base case's relative path.
    check_meshes
        Whether to run the NUM-34 gate once per distinct mesh where a point
        activates a wall correction. On by default; ``False`` is for a caller
        that has no NGSolve available and wants the combinatorics alone.

    Returns
    -------
    SweepPlan
        Points in wave order, every one of them substituted, validated and
        resolved.

    Raises
    ------
    SweepPlanError
        If an axis names a path the case schema does not have, if a value is not
        one the declared type accepts, if a point produces an inadmissible case,
        if two points are identical, or if ``rectification`` was asked for and
        the axes produce no exactly-opposite bias pair.
    nanopnp.solve.gates.GateViolationError
        If a mesh a point would solve on violates NUM-34.
    """
    _check_axes(document)
    base_path = document.base_path(source)
    try:
        base = load_case(base_path)
    except FileNotFoundError as error:
        raise SweepPlanError(
            f"the sweep names base case {base_path}, which is not there: {error}"
        ) from None

    axes = list(document.axes)
    shape = document.shape()
    origins = document.origins()
    grid = list(product(*(range(length) for length in shape))) if shape else [()]

    seen: dict[str, Mapping[str, FieldValue]] = {}
    enumerated: list[tuple[int, tuple[int, ...], str, Mapping[str, FieldValue]]] = []
    for coordinates in grid:
        try:
            assignments = merged(
                [axis.points()[index] for axis, index in zip(axes, coordinates, strict=True)], axes
            )
        except ValueError as error:
            raise SweepPlanError(str(error)) from None
        enumerated.append(
            (_depth(coordinates, origins), coordinates, _identify(assignments, seen), assignments)
        )

    # Ordered by wave, and within a wave by the Cartesian product's own order.
    # ``sorted`` is stable, so the second key is the enumeration above and needs
    # no tie-breaker of its own.
    ordered = sorted(range(len(enumerated)), key=lambda position: enumerated[position][0])
    index_of: dict[tuple[int, ...], int] = {
        enumerated[position][1]: index for index, position in enumerate(ordered)
    }

    points: list[Point] = []
    for index, position in enumerate(ordered):
        depth, coordinates, point_id, values = enumerated[position]
        parent = _parent_of(coordinates, origins)
        points.append(
            Point(
                index=index,
                point_id=point_id,
                coordinates=coordinates,
                assignments=values,
                parent=None if parent is None else index_of[parent],
                wave=depth,
                name=f"{base.name}-{point_id}",
            )
        )

    plan = SweepPlan(
        name=document.name,
        base_path=base_path,
        base_hash=CaseArtefact(base).hash,
        document=document.summary(),
        points=tuple(points),
        rectification=RECTIFICATION in base.outputs,
        pairs=_pairs(points),
        warnings=_warnings(document),
    )
    resolved = _resolve_every_point(base, plan)
    if plan.rectification and not plan.pairs:
        raise SweepPlanError(
            f"the base case asks for {RECTIFICATION!r}, which is the two-point ratio "
            "I(+V)/I(-V) and can only come from a matched pair of members, but no two points "
            "of this sweep differ only in 'boundary_conditions.bias_V' at exactly opposite "
            "values. Give the bias axis a symmetric set of values, or drop the output"
        )
    if check_meshes:
        plan = _gate_meshes(plan, resolved)
    for warning in plan.warnings:
        logger.warning("%s", warning)
    return plan


def _resolve_every_point(base: CaseDocument, plan: SweepPlan) -> tuple[CaseDocument, ...]:
    """Substitute, validate and resolve every point, and return the documents.

    ``resolve`` is pure Python — no NGSolve, no mesh — and it is where the
    NUM-18 refusals live: a case setting ``physics.flow: false`` and still
    selecting ``default_ladder`` is refused there. Running it over the whole
    plan costs seconds and is what stops a two-thousandth inadmissible point
    from surfacing at hour twenty-two (§5.3.4).
    """
    documents: list[CaseDocument] = []
    for point in plan.points:
        try:
            member = _member(base, point)
            resolve(member)
        except (CaseValidationError, UnknownCasePathError, NotImplementedError) as error:
            raise SweepPlanError(
                f"point {point.index} ({point.point_id}) is not a case this build can run.\n"
                f"  assignments: {_shown(point.assignments)}\n"
                f"  {error}"
            ) from None
        documents.append(member)
    return tuple(documents)


def _gate_meshes(plan: SweepPlan, members: Sequence[CaseDocument]) -> SweepPlan:
    """Run the NUM-34 gate once per distinct mesh a wall correction is active on.

    Once per *mesh*, not once per point: the distance field is a function of the
    mesh and the wall-distance settings alone, and 3,675 members of one sweep
    share one of them. At plan time it costs one linear solve and the NGSolve
    import on a command run once, and it buys the difference between a sweep
    refused in seconds and 3,675 identical aborts at wave 0.

    Raises
    ------
    nanopnp.solve.gates.GateViolationError
        Propagated unchanged from the gate, naming the mesh, the measured
        minimum, its location and the fraction of samples below zero (QR-12).
        Not wrapped in a :class:`SweepPlanError`: it is the same abort a member
        would produce, and IF-02 gives it the gate class rather than the case
        one.
    """
    from dataclasses import replace as replace_dataclass

    from nanopnp.mesh.ingest import IngestedMesh, ingest
    from nanopnp.physics.measures import AXISYMMETRIC
    from nanopnp.solve.state import check_wall_distance, reads_wall, wall_distance_field

    measured: dict[str, Canonicalisable] = {}
    checked: set[tuple[str, str, float, int]] = set()
    # Memoised on what the case says about the mesh rather than on what reading
    # it produced: a plan whose 3,675 points share one mesh must read that file
    # once, and the content hash -- the thing the gate is keyed on -- is only
    # available *after* the read. Two cases naming the same file with the same
    # vocabulary mapping ingest to the same mesh by construction (§5.3.2).
    ingested_meshes: dict[tuple[str, str | None, tuple[tuple[str, str], ...]], object] = {}
    for point, member in zip(plan.points, members, strict=True):
        resolved = resolve(member)
        if not reads_wall(resolved.electrolyte):
            continue
        order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
        supplied = resolved.mesh
        source = (
            str(supplied.path or supplied.artefact),
            supplied.format,
            tuple(sorted(supplied.groups.items())),
        )
        if source not in ingested_meshes:
            ingested_meshes[source] = ingest(supplied, resolved)
        ingested = cast("IngestedMesh", ingested_meshes[source])
        signature = (
            ingested.content_hash,
            resolved.wall_distance_sources,
            resolved.wall_distance_max_nm,
            order,
        )
        if signature in checked:
            continue
        checked.add(signature)
        measures = replace_dataclass(AXISYMMETRIC, element_order=order)
        distance = wall_distance_field(resolved, ingested.mesh, order=order)
        found = check_wall_distance(
            resolved, ingested.mesh, distance, coordinates=measures.coordinate_names
        )
        if found is not None:
            logger.info(
                "NUM-34: mesh %s reads d with min %.3g nm (point %d)",
                short(ingested.content_hash),
                found.minimum_nm,
                point.index,
            )
            measured[ingested.content_hash] = found.summary()
    return replace_dataclass(plan, wall_distance=measured)


def write_plan(plan: SweepPlan, directory: Path) -> Path:
    """Write the plan into a sweep directory and return its path.

    Through :func:`~nanopnp.core.hashing.canonical`, exactly as ``manifest.json``
    and ``run.json`` are written, so that the file a reader sees and the bytes
    that were hashed cannot disagree and every float round-trips exactly.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / PLAN_FILENAME
    path.write_bytes(canonical(plan.document_record()) + b"\n")
    return path


def read_plan(path: Path) -> SweepPlan:
    """Read a plan back from disk.

    Read rather than rebuilt: a job-array member must run from the plan the
    dispatch was submitted over, and rebuilding it from the sweep document would
    silently re-plan against whatever the base case says *now*.

    Raises
    ------
    SweepPlanError
        If the file is not a plan of this schema.
    """
    parsed = decode_floats(json.loads(Path(path).read_text(encoding="utf-8")))
    if not isinstance(parsed, dict) or parsed.get("schema") != SWEEP_SCHEMA:
        found = parsed.get("schema") if isinstance(parsed, dict) else type(parsed).__name__
        raise SweepPlanError(f"{path} declares schema {found!r}; this build reads {SWEEP_SCHEMA!r}")
    # ``cast`` and not a check: the file was written by ``write_plan`` through
    # ``canonical``, and one that was not is refused by the schema line above.
    raw = cast("dict[str, Canonicalisable]", parsed)
    base = raw["base"]
    points = tuple(
        Point(
            index=int(entry["index"]),
            point_id=str(entry["id"]),
            coordinates=tuple(int(value) for value in entry["coordinates"]),
            assignments=dict(entry["assignments"]),
            parent=None if entry["parent"] is None else int(entry["parent"]),
            wave=int(entry["wave"]),
            name=str(entry["name"]),
        )
        for entry in raw["points"]
    )
    return SweepPlan(
        name=str(raw["name"]),
        base_path=Path(str(base["path"])),
        base_hash=str(base["hash"]),
        document=dict(raw["sweep"]),
        points=points,
        rectification=bool(raw["rectification"]),
        pairs=tuple((int(a), int(b)) for a, b in raw["pairs"]),
        warnings=tuple(str(line) for line in raw["warnings"]),
        wall_distance=dict(raw["wall_distance"]),
    )


def plan_from_document(path: Path, *, check_meshes: bool = True) -> SweepPlan:
    """Load a sweep document and build its plan.

    The two steps the CLI's ``sweep plan`` takes, together, so that "read the
    file, resolve its base case, enumerate the points" happens once rather than
    in each caller.
    """
    source = Path(path)
    return build_plan(load_sweep(source), source=source, check_meshes=check_meshes)

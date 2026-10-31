"""The sweep plan: the points, the warm-start forest, and every check made before a solve."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cached_property, lru_cache
from itertools import product
from pathlib import Path
from typing import cast

from nanopnp.core.hashing import (
    Canonicalisable,
    canonical,
    content_hash,
    decode_floats,
    file_hash,
    short,
)
from nanopnp.io.artefact import SWEEP_SCHEMA, CaseArtefact
from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
    FieldValue,
)
from nanopnp.io.case_paths import (
    UnknownCasePathError,
    field_at,
    substitute,
)
from nanopnp.io.resolved import ResolvedCase
from nanopnp.io.store import atomic_write_bytes
from nanopnp.materials.corrections import load_corrections
from nanopnp.mesh.sizing import resolve_wall_size
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import input_files
from nanopnp.sweep.document import SweepDocument, load_sweep, merged

logger = logging.getLogger(__name__)

__all__ = [
    "PLAN_FILENAME",
    "POINT_SCHEMA",
    "WARM_START_BARRIERS",
    "Point",
    "SweepPlan",
    "SweepPlanError",
    "build_plan",
    "plan_from_document",
    "read_plan",
    "write_plan",
]

PLAN_FILENAME = "plan.json"

POINT_SCHEMA = "nanopnp/sweep/point/v0.5"

ID_LENGTH = 12

RECTIFICATION = "rectification"

WARM_START_BARRIERS: tuple[str, ...] = (
    # A cross-mesh transfer is a point evaluation outside the source domain,
    # which returns a plausible number rather than raising, and ``transfer``
    # refuses it. ``numerics.mesh`` is the same barrier one step earlier: the
    # mesher, its wall size and its boundary layer all move the mesh a member is
    # solved on, so VAL-04's mesh-convergence study severs here even though no
    # axis of it names a mesh file.
    "inputs.mesh",
    "numerics.mesh",
    # The same barrier further upstream still, since stages 5 and 6 generate the
    # mesh from them: the structure and its contour, the membrane and the
    # reservoir, and a supplied profile each move it.
    "structure",
    "geometry",
    "inputs.profile",
    # Under ``charge:`` but a geometry key all the same: a non-zero offset makes
    # stage 5 build the ion-exclusion shell, which moves the mesh.
    # ``dielectric_transition_nm`` moves only a coefficient, and does not sever.
    "charge.exclusion_offset_nm",
    # The element spaces. A coefficient vector is a function only relative to a
    # space, and ``load_initial`` gates on ``model.elements`` exactly as
    # ``restore`` does.
    "numerics.elements",
    # Not a space, and gated anyway: the reference mode of NUM-14 exists to
    # compare two numbers, and a comparison whose two sides were reached through
    # each other is not one (section 5.3.2, and ``state.SPACE_KEYS``).
    "numerics.stabilisation",
    # The declared field set: a model solving for a velocity and one that does
    # not are two different spaces however equal everything else is.
    "physics.model",
    "physics.flow",
    # It moves which degrees of freedom are constrained without moving any count.
    "boundary_conditions.ground",
)


class SweepPlanError(ValueError):
    """A sweep cannot be planned as written; the message names what was wrong and where."""


@dataclass(frozen=True)
class Point:
    """One member of a sweep: what it varies, where it sits, and who it starts from.

    Parameters
    ----------
    point_id
        The leading hex characters of the content hash of the assignments: the identity.
    wave
        The point's depth in the warm-start forest.
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
    base_hash
        Content hash of the validated base case document.
    workers
        The default worker count for a local dispatch; outside the plan hash.
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
    files: Mapping[str, str] = field(default_factory=dict)
    workers: int | None = None

    @cached_property
    def hash(self) -> str:
        """Return the plan's content hash: what it enumerates, not what it produced."""
        return content_hash(
            SWEEP_SCHEMA,
            {
                "name": self.name,
                "document": dict(self.document),
                "points": [point.summary() for point in self.points],
            },
            {"base_case": self.base_hash, **{f"file {path}": d for path, d in self.files.items()}},
        )

    def waves(self) -> tuple[tuple[int, int], ...]:
        """Return each wave as a half-open (first, last + 1) index range."""
        ranges: list[tuple[int, int]] = []
        for point in self.points:
            if point.wave == len(ranges):
                ranges.append((point.index, point.index + 1))
            else:
                first, _ = ranges[point.wave]
                ranges[point.wave] = (first, point.index + 1)
        return tuple(ranges)

    def point(self, index: int) -> Point:
        """Return one point by index; refuse an index this plan does not enumerate."""
        if not 0 <= index < len(self.points):
            raise SweepPlanError(
                f"this plan enumerates {len(self.points)} points, 0 to {len(self.points) - 1}; "
                f"there is no point {index}"
            )
        return self.points[index]

    def base_case(self) -> CaseDocument:
        """Return the base case from disk, refusing one whose hash has moved."""
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
        self._check_files()
        return base

    def _check_files(self) -> None:
        for path, planned in self.files.items():
            try:
                found = _digest_of_file(Path(path))
            except FileNotFoundError:
                raise SweepPlanError(
                    f"this plan was built against {path}, which is not there now (working "
                    f"directory {Path.cwd()}). A member reads its input files from the "
                    "dispatching process's working directory; dispatch from where the plan "
                    "was built, or re-plan the sweep"
                ) from None
            if found != planned:
                raise SweepPlanError(
                    f"this plan was built against a different {path}:\n"
                    f"  planned against: {planned}\n"
                    f"  on disk now:     {found}\n"
                    "Every member would solve a file this plan never enumerated and report it "
                    "under the plan's own point identities; re-plan the sweep"
                )

    def case(self, index: int, *, base: CaseDocument | None = None) -> CaseDocument:
        """Return the validated case document of one member, rebuilt from the base case.

        Parameters
        ----------
        base
            A base case already read and gated, to share one parse across members.
        """
        point = self.point(index)
        return _member(self.base_case() if base is None else base, point)

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
            "files": dict(self.files),
            "workers": self.workers,
            "waves": [list(span) for span in self.waves()],
            "points": [point.summary() for point in self.points],
        }


@lru_cache(maxsize=256)
def _digest_at(resolved: str, size: int, mtime_ns: int) -> str:
    return file_hash(resolved)


def _digest_of_file(path: Path) -> str:
    status = path.stat()
    return _digest_at(str(path.resolve()), status.st_size, status.st_mtime_ns)


def _planned_files(resolved: Sequence[ResolvedCase]) -> dict[str, str]:
    files: dict[str, str] = {}
    for member in resolved:
        for path in input_files(member, None).values():
            if str(path) not in files and path.is_file():
                files[str(path)] = _digest_of_file(path)
    return dict(sorted(files.items()))


def _member(base: CaseDocument, point: Point) -> CaseDocument:
    assignments = dict(point.assignments)
    assignments["name"] = point.name
    outputs = [word for word in base.outputs if word != RECTIFICATION]
    if outputs != list(base.outputs):
        assignments["outputs"] = outputs
    return substitute(base, assignments)


def _shown(assignments: Mapping[str, FieldValue]) -> str:
    return json.dumps(dict(assignments), sort_keys=True, default=str)


def _identify(
    assignments: Mapping[str, FieldValue], seen: dict[str, Mapping[str, FieldValue]]
) -> str:
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


def _barriers(document: SweepDocument) -> tuple[bool, ...]:
    return tuple(
        any(
            path == barrier or path.startswith(f"{barrier}.")
            for path in axis.paths()
            for barrier in WARM_START_BARRIERS
        )
        for axis in document.axes
    )


WALL_SIZE_PATHS: tuple[str, ...] = (
    "electrolyte.concentration_M",
    "electrolyte.temperature_K",
    "electrolyte.parameters",
    "electrolyte.species",
)


def _wall_size_barriers(
    document: SweepDocument,
    base: CaseDocument,
    grid: Sequence[tuple[int, ...]],
    barriers: Sequence[bool],
) -> tuple[bool, ...]:
    candidates = [
        index
        for index, axis in enumerate(document.axes)
        if not barriers[index]
        and any(
            path == entry or path.startswith(f"{entry}.")
            for path in axis.paths()
            for entry in WALL_SIZE_PATHS
        )
    ]
    if not candidates:
        return tuple(barriers)
    sizes: dict[tuple[int, ...], float | None] = {}
    for coordinates in grid:
        try:
            assignments = merged(
                [axis.points()[i] for axis, i in zip(document.axes, coordinates, strict=True)],
                document.axes,
            )
            member = substitute(base, assignments)
        except (CaseValidationError, UnknownCasePathError, ValueError):
            sizes[coordinates] = None
            continue
        if member.inputs.mesh is not None or member.numerics.mesh.wall_h_nm != "auto":
            sizes[coordinates] = None
            continue
        try:
            parameters = load_corrections(member.electrolyte.parameters)
            sizes[coordinates] = resolve_wall_size(
                member, permittivity_0=parameters.solvent.permittivity.eps_r0
            ).wall_h_nm
        except (ValueError, FileNotFoundError) as error:
            raise SweepPlanError(
                f"the point {dict(assignments)} generates its mesh with wall_h_nm: auto, and its "
                f"wall size cannot be resolved: {error}"
            ) from None
    flags = list(barriers)
    for index in candidates:
        lines: dict[tuple[int, ...], set[float]] = {}
        for coordinates, size in sizes.items():
            if size is None:
                continue
            rest = coordinates[:index] + coordinates[index + 1 :]
            lines.setdefault(rest, set()).add(size)
        flags[index] = any(len(values) > 1 for values in lines.values())
    return tuple(flags)


def _parent_of(
    coordinates: Sequence[int], origins: Sequence[int], barriers: Sequence[bool] = ()
) -> tuple[int, ...] | None:
    for axis in range(len(coordinates) - 1, -1, -1):
        if axis < len(barriers) and barriers[axis]:
            continue
        if coordinates[axis] != origins[axis]:
            step = -1 if coordinates[axis] > origins[axis] else 1
            moved = list(coordinates)
            moved[axis] += step
            return tuple(moved)
    return None


def _depth(
    coordinates: Sequence[int], origins: Sequence[int], barriers: Sequence[bool] = ()
) -> int:
    flags = tuple(barriers) + (False,) * (len(coordinates) - len(barriers))
    return sum(
        abs(index - origin)
        for index, origin, barrier in zip(coordinates, origins, flags, strict=True)
        if not barrier
    )


def _check_axes(document: SweepDocument) -> None:
    for axis in document.axes:
        for position, assignment in enumerate(axis.points()):
            for path, value in assignment.items():
                try:
                    field_at(path).validate(value)
                except (UnknownCasePathError, CaseValidationError) as error:
                    raise SweepPlanError(f"axis {axis.name!r}, value {position}: {error}") from None


def _warnings(document: SweepDocument, barriers: Sequence[bool]) -> tuple[str, ...]:
    found: list[str] = []
    for axis, barrier in zip(document.axes, barriers, strict=True):
        if not barrier:
            continue
        crossed = sorted(
            path
            for path in axis.paths()
            for entry in (*WARM_START_BARRIERS, *WALL_SIZE_PATHS)
            if path == entry or path.startswith(f"{entry}.")
        )
        found.append(
            f"axis {axis.name!r} varies {', '.join(repr(path) for path in crossed)}, which a warm "
            "start cannot cross (section 5.3.2): a coefficient vector is a function only relative "
            "to its space and its operator, and reading one onto another either raises on a "
            "length mismatch or silently seeds Newton with a meaningless state. Each value of "
            f"this axis is therefore its own warm-start component, rooted and cold, so "
            f"{len(axis.points())} members of this sweep climb the full NUM-18 ladder"
        )
    return tuple(found)


def _pairs(points: Sequence[Point]) -> tuple[tuple[int, int], ...]:
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
    """Enumerate, check and order every point of a sweep.

    Parameters
    ----------
    check_meshes
        Whether to run the mesh gate once per distinct mesh with a wall correction.
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
    barriers = _wall_size_barriers(document, base, grid, _barriers(document))

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
            (
                _depth(coordinates, origins, barriers),
                coordinates,
                _identify(assignments, seen),
                assignments,
            )
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
        parent = _parent_of(coordinates, origins, barriers)
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
        warnings=_warnings(document, barriers),
        workers=document.workers,
    )
    # Before the resolve rather than after it: an asymmetric bias axis makes the
    # plan impossible whatever its points resolve to, and the point of checking
    # here at all is that a sweep is refused in seconds (§5.3.4).
    if plan.rectification and not plan.pairs:
        raise SweepPlanError(
            f"the base case asks for {RECTIFICATION!r}, which is the two-point ratio "
            "I(+V)/I(-V) and can only come from a matched pair of members, but no two points "
            "of this sweep differ only in 'boundary_conditions.bias_V' at exactly opposite "
            "values. Give the bias axis a symmetric set of values, or drop the output"
        )
    resolved = _resolve_every_point(base, plan, beside=base_path.parent)
    plan = replace(plan, files=_planned_files(resolved))
    if check_meshes:
        plan = _gate_meshes(plan, resolved)
    for warning in plan.warnings:
        logger.warning("%s", warning)
    return plan


def _resolve_every_point(
    base: CaseDocument, plan: SweepPlan, *, beside: Path
) -> tuple[ResolvedCase, ...]:
    cases: list[ResolvedCase] = []
    for point in plan.points:
        try:
            cases.append(resolve(_member(base, point), base=beside))
        except (CaseValidationError, UnknownCasePathError, NotImplementedError) as error:
            raise SweepPlanError(
                f"point {point.index} ({point.point_id}) is not a case this build can run.\n"
                f"  assignments: {_shown(point.assignments)}\n"
                f"  {error}"
            ) from None
    return tuple(cases)


def _gate_meshes(plan: SweepPlan, members: Sequence[ResolvedCase]) -> SweepPlan:
    from nanopnp.mesh.ingest import IngestedMesh, ingest
    from nanopnp.numerics.measures import AXISYMMETRIC
    from nanopnp.solve.state import check_wall_distance, reads_distance, wall_distance_field

    measured: dict[str, Canonicalisable] = {}
    checked: set[tuple[str, str, float, int]] = set()
    # Memoised on what the case says about the mesh rather than on what reading
    # it produced: a plan whose 3,675 points share one mesh must read that file
    # once, and the content hash -- the thing the gate is keyed on -- is only
    # available *after* the read. Two cases naming the same file with the same
    # vocabulary mapping ingest to the same mesh by construction (§5.3.2).
    ingested_meshes: dict[tuple[str, str | None, tuple[tuple[str, str], ...]], object] = {}
    # ``members`` are the cases ``_resolve_every_point`` already resolved: a
    # second ``resolve`` over 3,675 points would be a second answer to a question
    # already asked, and slower to be no more certain of it.
    for point, resolved in zip(plan.points, members, strict=True):
        if not reads_distance(resolved):
            continue
        supplied = resolved.mesh
        if supplied is None:
            # A generated mesh does not exist until the member's stage 6 runs,
            # and meshing every distinct region here would put stages 1 to 6 of
            # the whole sweep in front of its first member. The member's solve
            # gates NUM-34 on the mesh it generated, as every solve does.
            continue
        order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
        assert supplied.path is not None  # resolve refuses artefact: on inputs.mesh
        source = (
            str(supplied.path),
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
        measures = AXISYMMETRIC.at_order(order)
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
    return replace(plan, wall_distance=measured)


def write_plan(plan: SweepPlan, directory: Path) -> Path:
    """Write the plan into a sweep directory and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / PLAN_FILENAME
    atomic_write_bytes(path, canonical(plan.document_record()) + b"\n")
    return path


def read_plan(path: Path) -> SweepPlan:
    """Read a plan back from disk, rather than rebuilding it from the sweep document."""
    parsed = decode_floats(json.loads(Path(path).read_text(encoding="utf-8")))
    if not isinstance(parsed, dict) or parsed.get("schema") != SWEEP_SCHEMA:
        found = parsed.get("schema") if isinstance(parsed, dict) else type(parsed).__name__
        raise SweepPlanError(f"{path} declares schema {found!r}; this build reads {SWEEP_SCHEMA!r}")
    # ``cast`` and not a check: the file was written by ``write_plan`` through
    # ``canonical``, and one that was not is refused by the schema line above.
    raw = cast("dict[str, Canonicalisable]", parsed)
    recorded = raw.get("files")
    if not isinstance(recorded, dict):
        raise SweepPlanError(
            f"{path} records no input file digests, as a plan written before they were "
            "recorded does not; re-plan the sweep so that its members are bound to the "
            "files it was built against"
        )
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
    plan = SweepPlan(
        name=str(raw["name"]),
        base_path=Path(str(base["path"])),
        base_hash=str(base["hash"]),
        document=dict(raw["sweep"]),
        points=points,
        rectification=bool(raw["rectification"]),
        pairs=tuple((int(a), int(b)) for a, b in raw["pairs"]),
        warnings=tuple(str(line) for line in raw["warnings"]),
        wall_distance=dict(raw["wall_distance"]),
        files={str(name): str(digest) for name, digest in recorded.items()},
        workers=None if raw.get("workers") is None else int(raw["workers"]),
    )
    # The file carries its own identities; a hand edit or a merge of two plans would
    # otherwise run other operating points under the recorded point ids (QR-12).
    for point in plan.points:
        if short(content_hash(POINT_SCHEMA, dict(point.assignments)), ID_LENGTH) != point.point_id:
            raise SweepPlanError(
                f"{path}: point {point.index} is recorded as {point.point_id!r} but its "
                "assignments hash to another identity; the plan was edited, re-plan it"
            )
    if plan.hash != raw["hash"]:
        raise SweepPlanError(
            f"{path}: records hash {raw['hash']} but its contents hash to {plan.hash}; "
            "the plan was edited, re-plan it"
        )
    return plan


def plan_from_document(path: Path, *, check_meshes: bool = True) -> SweepPlan:
    """Load a sweep document and build its plan."""
    source = Path(path)
    return build_plan(load_sweep(source), source=source, check_meshes=check_meshes)

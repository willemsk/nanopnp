"""VAL-01 and VAL-02: what a solution and a golden differ by, and where.

Three numbers per field, and the second of them is the point of the module.

``rel_L2_r`` is the *r*-weighted axisymmetric relative L2 error — the norm the
weak forms of section 6.2 are posed in, and therefore the VAL-01 quantity:

    ||v||_r^2 = sum_{p in P_f}  w_p r_p v_p^2 ,     w_p = dr dz of p's patch

with the ``2 pi`` cancelling in every ratio reported. It is also **blind on the
axis**: the weight ``r_p`` is 0.005 nm on the near-axis line and about 3 nm at
the pore wall, so a defect confined to the first column of probe points
contributes of order 1e-3 of what the same defect contributes at the wall. The
axis is exactly where the ``1/r`` forms of section 6.2 and the NUM-06 natural
condition are fragile — section 7.1's own warning about integration order lives
there — so a comparison reporting only ``rel_L2_r`` would be least sensitive
precisely where this implementation is most likely to be wrong.

``rel_l2`` is therefore reported beside it, weighting every probe point alike,
and ``max_abs_rel`` with its ``(r, z)`` beside both, so a reader has a location
and not only a magnitude (QR-12).

**Pressure is compared gauge-free.** ``p`` enters the momentum equation only
through ``grad p``, so any solution is a solution with a constant added unless a
Dirichlet condition pins it, and COMSOL's pin is not ours and is not in the model
report. Comparing raw ``p`` would make a gauge offset ``c`` contribute
``|c| ||1||_r / ||g||_r``, of order 1 on a reservoir-scale grid — a 100 %
discrepancy that looks like a flow defect and is not one. Both fields have their
*r*-weighted mean removed first and the removed constants are reported.

**The mask agreement is a gate, not a filter.** NGSolve returns ``0`` outside a
space's ``definedon`` region and COMSOL writes ``NaN`` outside its solved domain;
those are two independent statements about the same geometry, so comparing them
tests the geometry. Intersecting them instead would silently absorb a real
difference between our reference geometry and the one the export was made from,
which is the one thing this comparison is in a position to notice.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.io.fields import field_scale, sample_at
from nanopnp.physics.models import PRESSURE, VELOCITY
from nanopnp.validation.comsol import Golden, GoldenQuantities
from nanopnp.validation.probe import ProbeGrid, ProbeGridError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.scaling import Scales
    from nanopnp.core.typing import FESpace
    from nanopnp.physics.models import ModelSolution
    from nanopnp.validation.probe import ProbeDocument

__all__ = [
    "FieldComparison",
    "QoIComparison",
    "check_mask_agreement",
    "compare_fields",
    "compare_quantities",
    "field_error",
    "golden_grid",
    "probe_domains",
    "sample_on_probe",
    "unavailable_quantities",
]

PRESSURE_FIELD = "pressure"
"""The one field compared gauge-free; see the module docstring."""

VELOCITY_COMPONENTS: tuple[str, str] = ("velocity_r", "velocity_z")
"""The golden's names for the two components of the half-plane velocity.

Split because COMSOL exports ``u`` and ``w`` as two scalar expressions and a
``%Grid`` table holds one scalar, so the transport format decides the vocabulary
here rather than our own vector field doing so.
"""

COMPARED_QUANTITIES: tuple[str, ...] = (
    "current_A",
    "conductance_S",
    "transport_number",
    "eof_m3_s",
)
"""The NUM-27 scalars VAL-02 compares, in the order the report prints them.

``RR`` is absent deliberately: it is a two-point ratio (section 5.3.1 NOTE) and
belongs to the matched opposite-bias *pair*, not to either case on its own, so
the attribution report forms it from two comparisons rather than this function
inventing one from a single golden.
"""


@dataclass(frozen=True)
class FieldComparison:
    """What one field of one solution differs from one golden by.

    Parameters
    ----------
    field
        The field's name, in the golden's vocabulary.
    points
        Number of probe points the norms were taken over, after the mask.
    rel_L2_r, rel_l2
        The two relative norms of the module docstring.
    max_abs_rel
        ``max |s - g| / max |g|`` over the retained points. Normalised by the
        field's own scale rather than pointwise by ``|g_p|``: a pointwise ratio
        diverges wherever the field crosses zero, which the potential does by
        construction under a grounded cis electrode, and would report a
        meaningless infinity at a point where nothing is wrong.
    max_at_nm
        ``(r, z)`` of that maximum. QR-12's "naming the quantity and its
        location", and the difference between a number and a diagnosis.
    gauge_removed
        ``(ours, golden)`` *r*-weighted means removed before the norms, for
        :data:`PRESSURE_FIELD`, and ``None`` for every other field. A large gauge
        difference is not a defect but it is worth seeing.
    """

    field: str
    points: int
    rel_L2_r: float
    rel_l2: float
    max_abs_rel: float
    max_at_nm: tuple[float, float]
    gauge_removed: tuple[float, float] | None = None

    def summary(self) -> dict[str, object]:
        """Return this comparison as the report records it (FR-25)."""
        record: dict[str, object] = {
            "field": self.field,
            "points": self.points,
            "rel_L2_r": self.rel_L2_r,
            "rel_l2": self.rel_l2,
            "max_abs_rel": self.max_abs_rel,
            "max_at_nm": {"r": self.max_at_nm[0], "z": self.max_at_nm[1]},
        }
        if self.gauge_removed is not None:
            record["gauge_removed_Pa"] = {
                "ours": self.gauge_removed[0],
                "golden": self.gauge_removed[1],
                "difference": self.gauge_removed[0] - self.gauge_removed[1],
            }
        return record


@dataclass(frozen=True)
class QoIComparison:
    """One scalar quantity of interest, ours against the golden's (VAL-02).

    Parameters
    ----------
    name
        The quantity, as :data:`COMPARED_QUANTITIES` names it.
    ours, golden
        The two values, both in section 6.7's sign convention and in SI.
    relative
        ``(ours - golden) / |golden|``, **signed**: the direction of a
        discrepancy is half of what attributes it, and a magnitude alone cannot
        say whether a stabilised mode raised the current or lowered it.
    """

    name: str
    ours: float
    golden: float
    relative: float

    def summary(self) -> dict[str, object]:
        """Return this comparison as the report records it."""
        return {
            "quantity": self.name,
            "ours": self.ours,
            "golden": self.golden,
            "relative": self.relative,
        }


def probe_domains(solution: ModelSolution) -> dict[str, str | None]:
    """Return each comparable field's ``definedon`` materials, from the model itself.

    Taken from :attr:`nanopnp.physics.models.Field.domain` rather than restated
    in the probe document, so that a probe grid cannot disagree with the physics
    about where a field exists. The velocity contributes both of its components
    under one domain, which is what makes the golden's two scalar tables and our
    one vector field the same statement.
    """
    domains: dict[str, str | None] = {}
    for field in solution.model.fields:
        if field.element == "number":
            continue
        if field.name == VELOCITY:
            domains.update(dict.fromkeys(VELOCITY_COMPONENTS, field.domain))
        elif field.name == PRESSURE:
            domains[PRESSURE_FIELD] = field.domain
        else:
            domains[field.name] = field.domain
    return domains


def golden_grid(document: ProbeDocument, golden: Golden) -> ProbeGrid:
    """Return a grid carrying a probe document's points but no mesh, for two goldens.

    VAL-04's ``Delta_ref`` compares two *exports* and never touches a mesh, so
    there is no ``definedon`` region to mask against and the mask that belongs to
    the comparison is the finer golden's own ``NaN`` set — which
    :func:`~nanopnp.validation.attribution.reference_error` passes to the mask
    gate itself. The masks here are therefore all-true placeholders, and the
    weights and coordinates are what the caller is really after.

    Parameters
    ----------
    document
        The probe grid both goldens were exported onto.
    golden
        Either of the pair; only its field names are read.
    """
    import numpy as np

    keep = np.ones(document.count, dtype=bool)
    return ProbeGrid(
        document=document,
        points_nm=document.points_nm(),
        weights_nm2=document.weights_nm2(),
        masks=dict.fromkeys(sorted(golden.values), keep),
        dropped=dict.fromkeys(sorted(golden.values), 0),
    )


def sample_on_probe(
    solution: ModelSolution, grid: ProbeGrid, *, scales: Scales
) -> dict[str, np.ndarray]:
    """Return every comparable field of ``solution`` at ``grid``'s points, in SI.

    Parameters
    ----------
    solution
        The converged state, in the NUM-09 nondimensional variables.
    grid
        The probe grid, already bound to this solution's mesh.
    scales
        The NUM-09 scale set the state was solved in, as
        :func:`~nanopnp.io.fields.export_fields` takes it. Passed rather than
        read off the model, because :class:`~nanopnp.physics.models.PhysicsModel`
        is a protocol and a scale set is a property of the *case*.

    Returns
    -------
    dict of str to ndarray
        Field name to a ``(n,)`` array in the probe document's flattening order,
        ``NaN`` wherever the field's mask drops the point. ``NaN`` rather than
        zero on purpose: zero is what NGSolve returns outside a ``definedon``
        region, and a masked-out point that came back as a number would enter a
        norm as a fabricated agreement (section 3 of the WP13 plan).

    Notes
    -----
    Every value is multiplied by its NUM-09 scale on the way out, so the arrays
    are in the units :func:`~nanopnp.validation.comsol.field_unit` declares and
    the comparison never carries a scale of its own.
    """
    import numpy as np

    mesh = solution.space.mesh
    points = grid.points_nm
    carriers: dict[tuple[int, int], FESpace] = {}
    sampled: dict[str, np.ndarray] = {}
    for field in solution.model.fields:
        if field.element == "number":
            continue
        vector = field.element == "vector_h1"
        values = sample_at(
            mesh,
            solution.component(field.name),
            points,
            order=field.order,
            dimension=2 if vector else 1,
            materials=field.domain,
            carriers=carriers,
        ) * field_scale(field.name, scales)
        if vector:
            for index, name in enumerate(VELOCITY_COMPONENTS):
                sampled[name] = values[:, index]
        else:
            sampled[PRESSURE_FIELD if field.name == PRESSURE else field.name] = values[:, 0]
    for name, values in sampled.items():
        mask = grid.masks.get(name)
        if mask is None:  # pragma: no cover - probe_domains fixes the two key sets
            raise ProbeGridError(
                f"the probe grid carries no mask for field {name!r}; build it with "
                "ProbeGrid.on_mesh(document, mesh, probe_domains(solution))"
            )
        values[~mask] = np.nan
    return sampled


def compare_fields(
    ours: Mapping[str, np.ndarray], golden: Golden, grid: ProbeGrid
) -> tuple[FieldComparison, ...]:
    """Compare every field the golden carries, in the golden's own field order.

    Parameters
    ----------
    ours
        As :func:`sample_on_probe` returned it.
    golden
        The archived reference solution.
    grid
        The probe grid both are expressed on.

    Returns
    -------
    tuple of FieldComparison
        One per field present in both, sorted by name. Fields the golden does
        not carry are not silently skipped: :meth:`~Golden.unavailable` names
        them and the attribution report prints them.

    Raises
    ------
    ProbeGridError
        If the two masks disagree anywhere, naming the worst point's ``(r, z)``
        and its distance from the nearest retained point of the other mask.
    """
    import numpy as np

    comparisons: list[FieldComparison] = []
    for field in sorted(set(ours) & set(golden.values)):
        mine = np.asarray(ours[field], dtype=np.float64)
        theirs = np.asarray(golden.values[field], dtype=np.float64)
        keep = np.asarray(grid.masks[field], dtype=bool)
        check_mask_agreement(field, keep, golden.defined(field), grid)
        _check_finite(field, mine, keep, grid)
        comparisons.append(field_error(field, mine, theirs, grid, keep))
    return tuple(comparisons)


def compare_quantities(
    ours: Mapping[str, object], golden: GoldenQuantities
) -> tuple[QoIComparison, ...]:
    """Compare the NUM-27 scalars of one case (VAL-02).

    Parameters
    ----------
    ours
        What the run **recorded** — :meth:`QuantitiesOfInterest.summary`, or the
        ``quantities`` block of its ``run.json``. A mapping rather than the
        object, because FR-25 archived what the run reported and a comparison
        that re-extracted the numbers would be comparing the golden against
        something the manifest does not describe.
    golden
        The reference's, already converted to section 6.7's sign convention by
        :func:`~nanopnp.validation.comsol.load_golden`.

    Returns
    -------
    tuple of QoIComparison
        One per quantity of :data:`COMPARED_QUANTITIES` that *both* sides carry.
        A quantity either side lacks is omitted here and reported as unavailable
        by the attribution report, so a comparison over three quantities cannot
        read as one over four.
    """
    compared: list[QoIComparison] = []
    for name in COMPARED_QUANTITIES:
        mine, theirs = ours.get(name), getattr(golden, name, None)
        if mine is None or theirs is None:
            continue
        if not isinstance(mine, (int, float)) or isinstance(mine, bool):
            raise ProbeGridError(
                f"the run records {name!r} as {mine!r}, which is not a number. A quantity of "
                "interest that is present and not comparable is a defect in what produced it; "
                "omitting it here would report the comparison as having covered it"
            )
        recorded = float(mine)
        scale = abs(float(theirs))
        if scale == 0.0:
            # A reference value of exactly zero has no relative error. It
            # happens at zero bias, where both currents are round-off, and
            # dividing by it would report a discrepancy of order 1 on two
            # numbers that agree.
            continue
        compared.append(
            QoIComparison(
                name=name,
                ours=recorded,
                golden=float(theirs),
                relative=(recorded - float(theirs)) / scale,
            )
        )
    return tuple(compared)


def check_mask_agreement(field: str, ours: np.ndarray, theirs: np.ndarray, grid: ProbeGrid) -> None:
    """Abort where two statements about where a field exists disagree.

    Public for VAL-04, which asks it of a coarse and a fine golden: two
    refinements of one model that disagree about the domain are not two
    refinements of one model.
    """
    import numpy as np

    disagreeing = np.flatnonzero(ours != theirs)
    if disagreeing.size == 0:
        return
    points = grid.points_nm
    worst_index, worst_distance = _furthest(points, disagreeing, ours, theirs)
    r_nm, z_nm = points[worst_index]
    only_ours = int(np.count_nonzero(ours & ~theirs))
    raise ProbeGridError(
        f"field {field!r}: the two domain masks disagree at "
        f"{disagreeing.size} of {ours.size} probe points ({only_ours} kept only by us, "
        f"{disagreeing.size - only_ours} only by the golden). The worst is (r, z) = "
        f"({r_nm:.6g}, {z_nm:.6g}) nm, {worst_distance:.6g} nm from the nearest point the other "
        "mask retains. With the margin rule in place that is a real difference between this "
        "geometry and the one the export was made from, not a boundary-resolution accident; "
        "intersecting the two masks instead would absorb it silently"
    )


def _furthest(
    points: np.ndarray, disagreeing: np.ndarray, ours: np.ndarray, theirs: np.ndarray
) -> tuple[int, float]:
    """Return the disagreeing point furthest from the other mask, and that distance.

    Furthest rather than first: a one-element fringe along a boundary is a
    different diagnosis from a block of points in the wrong place, and the
    distance is what tells them apart. Brute force over the probe points, which
    costs a few thousand squared only on the path that is about to abort.
    """
    import numpy as np

    best_index, best_distance = int(disagreeing[0]), 0.0
    for index in disagreeing:
        # The "other" mask is whichever of the two does *not* retain this point.
        other = theirs if ours[index] else ours
        retained = points[other]
        if retained.size == 0:
            distance = float("inf")
        else:
            distance = float(np.min(np.linalg.norm(retained - points[index], axis=1)))
        if distance > best_distance:
            best_index, best_distance = int(index), distance
    return best_index, best_distance


def field_error(
    field: str,
    ours: np.ndarray,
    theirs: np.ndarray,
    grid: ProbeGrid,
    keep: np.ndarray,
) -> FieldComparison:
    """Return the three norms of one field over the points ``keep`` retains.

    Public because VAL-04's ``Delta_ref`` is the same three norms taken between
    two *goldens* rather than between a solution and one, and a second
    implementation of the gauge-free pressure path would be a second chance to
    get it wrong.

    Parameters
    ----------
    field
        The field's name; :data:`PRESSURE_FIELD` selects the gauge-free path.
    ours, theirs
        Full-length arrays in the probe document's flattening order.
    grid
        The probe grid, for the weights and the coordinates.
    keep
        Boolean mask of the points to take the norms over.
    """
    import numpy as np

    points = np.asarray(grid.points_nm, dtype=np.float64)[keep]
    radial = np.asarray(grid.weights_nm2, dtype=np.float64)[keep] * points[:, 0]
    mine, reference = ours[keep], theirs[keep]
    gauge: tuple[float, float] | None = None
    if field == PRESSURE_FIELD:
        total = float(radial.sum())
        if total > 0.0:
            gauge = (
                float(np.dot(radial, mine) / total),
                float(np.dot(radial, reference) / total),
            )
            mine, reference = mine - gauge[0], reference - gauge[1]
    difference = mine - reference
    scale = float(np.max(np.abs(reference))) if reference.size else 0.0
    worst = int(np.argmax(np.abs(difference))) if difference.size else 0
    location = points[worst] if points.size else np.zeros(2)
    return FieldComparison(
        field=field,
        points=int(keep.sum()),
        rel_L2_r=_relative(difference, reference, radial),
        rel_l2=_relative(difference, reference, None),
        max_abs_rel=float(np.max(np.abs(difference)) / scale) if scale > 0.0 else 0.0,
        max_at_nm=(float(location[0]), float(location[1])),
        gauge_removed=gauge,
    )


def _check_finite(field: str, ours: np.ndarray, keep: np.ndarray, grid: ProbeGrid) -> None:
    """Abort on a non-finite value at a point the mask retains.

    A ``NaN`` outside the mask is this module's own marker and expected; one
    *inside* it came from the solve, and filtering it out would take the norm
    over the points where the solution is fine and report agreement (QR-12).
    """
    import numpy as np

    bad = np.flatnonzero(keep & ~np.isfinite(ours))
    if bad.size == 0:
        return
    r_nm, z_nm = np.asarray(grid.points_nm, dtype=np.float64)[int(bad[0])]
    raise ProbeGridError(
        f"field {field!r} is not finite at {bad.size} of the {int(keep.sum())} probe points its "
        f"mask retains, the first at (r, z) = ({r_nm:.6g}, {z_nm:.6g}) nm. That value came from "
        "the solve, not from the mask; dropping it would take the norm over the points where the "
        "solution is well and report agreement"
    )


def _relative(difference: np.ndarray, reference: np.ndarray, weights: np.ndarray | None) -> float:
    """Return ``||difference|| / ||reference||`` in the given weighted L2 norm.

    A reference of exactly zero returns ``0.0`` when the difference is zero too
    and ``inf`` otherwise, rather than ``nan``: "identical" and "the reference is
    nowhere and we are somewhere" are different facts, and ``nan`` is neither.
    """
    import numpy as np

    if weights is None:
        top = float(np.dot(difference, difference))
        bottom = float(np.dot(reference, reference))
    else:
        top = float(np.dot(weights, difference * difference))
        bottom = float(np.dot(weights, reference * reference))
    if bottom <= 0.0:
        return 0.0 if top <= 0.0 else float("inf")
    return float(np.sqrt(top / bottom))


def unavailable_quantities(ours: Mapping[str, object], golden: GoldenQuantities) -> tuple[str, ...]:
    """Return the :data:`COMPARED_QUANTITIES` either side did not supply."""
    return tuple(
        name
        for name in COMPARED_QUANTITIES
        if ours.get(name) is None or getattr(golden, name, None) is None
    )

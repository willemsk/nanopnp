"""VAL-01 and VAL-02: what a solution and a golden differ by, and where."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.io.vocabulary import PRESSURE, VELOCITY
from nanopnp.post.export import (
    field_scale,
    logarithmic_fields,
    sample_at,
)
from nanopnp.validation.comsol import Golden, GoldenQuantities
from nanopnp.validation.probe import ProbeGrid, ProbeGridError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.scaling import Scales
    from nanopnp.core.typing import FESpace
    from nanopnp.physics.models import ModelSolution

__all__ = [
    "FieldComparison",
    "QoIComparison",
    "check_mask_agreement",
    "compare_fields",
    "compare_quantities",
    "field_error",
    "probe_domains",
    "sample_on_probe",
    "unavailable_quantities",
    "zero_reference_quantities",
]

PRESSURE_FIELD = "pressure"

VELOCITY_COMPONENTS: tuple[str, str] = ("velocity_r", "velocity_z")

COMPARED_QUANTITIES: tuple[str, ...] = (
    "current_A",
    "conductance_S",
    "transport_number",
    "eof_m3_s",
)


@dataclass(frozen=True)
class FieldComparison:
    """What one field of one solution differs from one golden by.

    Parameters
    ----------
    max_abs_rel
        ``max |s - g| / max |g|`` over the retained points, normalised by the field's scale.
    max_at_nm
        ``(r, z)`` of that maximum.
    gauge_removed
        ``(ours, golden)`` mean removed before the norms for the pressure, else ``None``.
    """

    field: str
    points: int
    rel_L2_r: float
    rel_l2: float
    max_abs_rel: float
    max_at_nm: tuple[float, float]
    gauge_removed: tuple[float, float] | None = None

    def summary(self) -> dict[str, object]:
        """Return this comparison as the report records it."""
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
    """One scalar quantity of interest, ours against the golden's.

    Parameters
    ----------
    relative
        ``(ours - golden) / |golden|``, signed.
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
    """Return each comparable field's ``definedon`` materials, from the model itself."""
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


def sample_on_probe(
    solution: ModelSolution, grid: ProbeGrid, *, scales: Scales
) -> dict[str, np.ndarray]:
    """Return every comparable field of ``solution`` at ``grid``'s points, in SI.

    Parameters
    ----------
    scales
        The NUM-09 scale set the state was solved in.

    Returns
    -------
    dict of str to ndarray
        Field name to a ``(n,)`` array, ``NaN`` wherever the field's mask drops the point.
    """
    import numpy as np

    mesh = solution.space.mesh
    points = grid.points_nm
    carriers: dict[tuple[int, int], FESpace] = {}
    sampled: dict[str, np.ndarray] = {}
    logarithmic = logarithmic_fields(solution.model)
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
        )
        if field.name in logarithmic:
            values = np.exp(values)
        values = values * field_scale(field.name, scales)
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

    Raises
    ------
    ProbeGridError
        If the two masks disagree outside the margin band, naming the worst point.
    """
    import numpy as np

    comparisons: list[FieldComparison] = []
    for field in sorted(set(ours) & set(golden.values)):
        mine = np.asarray(ours[field], dtype=np.float64)
        theirs = np.asarray(golden.values[field], dtype=np.float64)
        keep = np.asarray(grid.masks[field], dtype=bool)
        # The golden must be defined at every kept point and NaN outside the bare
        # test; in the margin band between, a COMSOL export carries values and a
        # self-golden does not, and the band is in neither the gate nor the norms.
        band = np.asarray(grid.band(field), dtype=bool)
        check_mask_agreement(field, keep, np.where(band, keep, golden.defined(field)), grid)
        _check_finite(field, mine, keep, grid)
        comparisons.append(field_error(field, mine, theirs, grid, keep))
    return tuple(comparisons)


def compare_quantities(
    ours: Mapping[str, object], golden: GoldenQuantities
) -> tuple[QoIComparison, ...]:
    """Compare the NUM-27 scalars of one case.

    Parameters
    ----------
    ours
        The quantities the run recorded, as a mapping.
    golden
        The reference's, already in section 6.7's sign convention.
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
    """Abort where two statements about where a field exists disagree."""
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

    Parameters
    ----------
    field
        The field's name; the pressure selects the gauge-free path.
    """
    import numpy as np

    if not bool(np.any(keep)):
        raise ProbeGridError(
            f"field {field!r}: the mask retains no probe point, so there is nothing to compare. "
            "A norm over no points is 0 and would read as exact agreement (QR-12)"
        )
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
        max_abs_rel=(
            float(np.max(np.abs(difference)) / scale)
            if scale > 0.0
            else (float("inf") if np.any(difference) else 0.0)
        ),
        max_at_nm=(float(location[0]), float(location[1])),
        gauge_removed=gauge,
    )


def _check_finite(field: str, ours: np.ndarray, keep: np.ndarray, grid: ProbeGrid) -> None:
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


def zero_reference_quantities(
    ours: Mapping[str, object], golden: GoldenQuantities
) -> dict[str, float]:
    """Return our value of each ``COMPARED_QUANTITIES`` whose golden is exactly zero."""
    zero: dict[str, float] = {}
    for name in COMPARED_QUANTITIES:
        value = ours.get(name)
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and getattr(golden, name, None) == 0.0
        ):
            zero[name] = float(value)
    return zero


def unavailable_quantities(ours: Mapping[str, object], golden: GoldenQuantities) -> tuple[str, ...]:
    """Return the ``COMPARED_QUANTITIES`` either side did not supply."""
    return tuple(
        name
        for name in COMPARED_QUANTITIES
        if ours.get(name) is None or getattr(golden, name, None) is None
    )

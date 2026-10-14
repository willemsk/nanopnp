"""The Cₙ axis by chain-permutation superposition, its gates and the model frame (FR-01, FR-02)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

# Thresholds: SPECIFICATION.md §5.3.1 NOTE on structure:; margins:
# .knowledge/07-software-stack/index.md.
SPACING_FRACTION = 0.25

ANGLE_TOLERANCE_DEG = 1.0

ORIENTATION_LIMIT_DEG = 10.0

DISPLACEMENT_BUDGET_NM = 0.01

_Z = (0.0, 0.0, 1.0)


class SymmetryGateError(ValueError):
    """A stage-1 symmetry gate refused the structure."""


@dataclass(frozen=True)
class RigidFit:
    """A least-squares rigid superposition: ``rotation @ x + translation``."""

    rotation: np.ndarray
    translation: np.ndarray
    rmsd_nm: float

    def apply(self, points: np.ndarray) -> np.ndarray:
        """Return ``points`` (``(..., 3)``) moved by this transform."""
        import numpy as np

        return np.asarray(points @ self.rotation.T + self.translation, dtype=np.float64)


def kabsch(mobile: np.ndarray, reference: np.ndarray) -> RigidFit:
    """Return the rigid transform that best superposes ``mobile`` on ``reference``."""
    import numpy as np

    mobile = np.asarray(mobile, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    if mobile.shape != reference.shape or mobile.ndim != 2 or mobile.shape[1] != 3:
        raise ValueError(
            f"a superposition needs two (m, 3) arrays of the same shape; got {mobile.shape} and "
            f"{reference.shape}"
        )
    mobile_centre = mobile.mean(axis=0)
    reference_centre = reference.mean(axis=0)
    covariance = (mobile - mobile_centre).T @ (reference - reference_centre)
    u, _, vt = np.linalg.svd(covariance)
    sign = 1.0 if np.linalg.det(vt.T @ u.T) >= 0.0 else -1.0
    rotation = vt.T @ np.diag([1.0, 1.0, sign]) @ u.T
    translation = reference_centre - rotation @ mobile_centre
    moved = mobile @ rotation.T + translation
    rmsd = float(np.sqrt(np.mean(np.sum((moved - reference) ** 2, axis=1))))
    return RigidFit(rotation=rotation, translation=translation, rmsd_nm=rmsd)


def rotation_axis(rotation: np.ndarray) -> tuple[np.ndarray, float]:
    """Return a rotation's axis (eigenvalue 1) and its signed angle, in radians."""
    import numpy as np

    _, _, vt = np.linalg.svd(rotation - np.eye(3))
    axis = vt[-1] / np.linalg.norm(vt[-1])
    if axis[2] < 0.0:
        axis = -axis
    skew = np.array(
        [
            rotation[2, 1] - rotation[1, 2],
            rotation[0, 2] - rotation[2, 0],
            rotation[1, 0] - rotation[0, 1],
        ]
    )
    cosine = (np.trace(rotation) - 1.0) / 2.0
    sine = float(skew @ axis) / 2.0
    return axis, math.atan2(sine, max(-1.0, min(1.0, float(cosine))))


def _perpendicular_basis(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np

    seed = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    first = seed - (seed @ axis) * axis
    first /= np.linalg.norm(first)
    return first, np.cross(axis, first)


def azimuths(centroids: np.ndarray, axis: np.ndarray, point: np.ndarray) -> np.ndarray:
    """Return each centroid's azimuth about the line through ``point`` along ``axis``, in rad."""
    import numpy as np

    first, second = _perpendicular_basis(axis)
    offset = centroids - point
    return np.asarray(np.arctan2(offset @ second, offset @ first), dtype=np.float64)


def initial_axis(chains: np.ndarray) -> np.ndarray:
    """Return the ordering axis, signed to the file's +z."""
    import numpy as np

    total = np.zeros((3, 3))
    for chain in chains:
        total += kabsch(chains[0], chain).rotation
    symmetric = (total + total.T) / (2.0 * len(chains))
    values, vectors = np.linalg.eigh(symmetric)
    axis = vectors[:, int(np.argmax(values))]
    axis = axis / np.linalg.norm(axis)
    return axis if axis[2] >= 0.0 else -axis


def chain_order(chains: np.ndarray, axis: np.ndarray) -> tuple[int, ...]:
    """Return the chain indices counter-clockwise about ``axis``, starting at chain 0."""
    import numpy as np

    centroid = chains.reshape(-1, 3).mean(axis=0)
    phi = azimuths(chains.mean(axis=1), axis, centroid)
    relative = np.mod(phi - phi[0], 2.0 * np.pi)
    return tuple(int(index) for index in np.argsort(relative, kind="stable"))


@dataclass(frozen=True)
class CyclicFit:
    """The rotation superposing an ordered assembly on its cyclic permutation."""

    axis: np.ndarray
    centroid_nm: np.ndarray
    angle_rad: float
    rmsd_nm: float


def cyclic_fit(chains: np.ndarray, order: Sequence[int]) -> CyclicFit:
    """Superpose the assembly on itself with the chain at position k mapped to k + 1."""
    import numpy as np

    ordered = chains[list(order)]
    mobile = ordered.reshape(-1, 3)
    target = np.roll(ordered, -1, axis=0).reshape(-1, 3)
    fit = kabsch(mobile, target)
    axis, angle = rotation_axis(fit.rotation)
    return CyclicFit(
        axis=axis, centroid_nm=mobile.mean(axis=0), angle_rad=angle, rmsd_nm=fit.rmsd_nm
    )


@dataclass(frozen=True)
class AxisRecord:
    """The Cₙ axis in the file's frame, with every gate measurement."""

    n: int
    axis: np.ndarray
    centroid_nm: np.ndarray
    foot_nm: np.ndarray
    order: tuple[int, ...]
    angle_deg: float
    spacings_deg: tuple[float, ...]
    tilt_deg: float
    rmsd_nm: float

    @property
    def spacing_error_deg(self) -> float:
        """Worst departure of an azimuthal gap from ``360/n``, in degrees."""
        nominal = 360.0 / self.n
        return max(abs(gap - nominal) for gap in self.spacings_deg)

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the record as plain data, for the artefact header."""
        return {
            "n": self.n,
            "axis": [float(value) for value in self.axis],
            "centroid_nm": [float(value) for value in self.centroid_nm],
            "foot_nm": [float(value) for value in self.foot_nm],
            "order": list(self.order),
            "angle_deg": self.angle_deg,
            "spacings_deg": list(self.spacings_deg),
            "spacing_error_deg": self.spacing_error_deg,
            "tilt_deg": self.tilt_deg,
            "rmsd_nm": self.rmsd_nm,
        }


def tilt_deg(axis: np.ndarray) -> float:
    """Return the angle between a unit ``axis`` and the file's z, in degrees."""
    return math.degrees(math.acos(max(-1.0, min(1.0, float(axis[2])))))


def measure_axis(chains: np.ndarray, n: int) -> AxisRecord:
    """Find the Cₙ axis of an assembly, without gating it."""
    import numpy as np

    chains = np.asarray(chains, dtype=np.float64)
    if n < 2:
        raise SymmetryGateError(
            "symmetry.axis: auto needs a permutation to superpose, and C1 has none; set "
            "symmetry.axis: z, which takes the file's z axis through its origin unchecked"
        )
    if chains.shape[0] != n:
        raise ValueError(f"expected {n} chains for C{n}, got {chains.shape[0]}")

    order = chain_order(chains, initial_axis(chains))
    fit = cyclic_fit(chains, order)
    nominal = 360.0 / n
    # Wrapped about the nominal angle so a half turn (n = 2) read as -180 degrees is no error.
    angle_error = (math.degrees(fit.angle_rad) - nominal + 180.0) % 360.0 - 180.0
    phi = np.degrees(azimuths(chains[list(order)].mean(axis=1), fit.axis, fit.centroid_nm))
    centroid = fit.centroid_nm
    return AxisRecord(
        n=n,
        axis=fit.axis,
        centroid_nm=centroid,
        foot_nm=centroid - (centroid @ fit.axis) * fit.axis,
        order=order,
        angle_deg=nominal + angle_error,
        spacings_deg=tuple(float(gap) for gap in np.mod(np.roll(phi, -1) - phi, 360.0)),
        tilt_deg=tilt_deg(fit.axis),
        rmsd_nm=fit.rmsd_nm,
    )


def gate_axis(record: AxisRecord) -> AxisRecord:
    """Apply the spacing, angle and orientation gates to a measured axis.

    Raises
    ------
    SymmetryGateError
        When the spacing, the cyclic angle or the axis orientation is out of tolerance.
    """
    n = record.n
    nominal = 360.0 / n
    limit = SPACING_FRACTION * nominal
    if not record.spacing_error_deg <= limit:
        errors = [abs(gap - nominal) for gap in record.spacings_deg]
        worst = errors.index(max(errors))
        raise SymmetryGateError(
            f"azimuthal spacing gate: the chains of C{n} should be {nominal:g} degrees apart, but "
            f"the gap after chain position {worst} is {record.spacings_deg[worst]:.2f} degrees, "
            f"{record.spacing_error_deg:.2f} degrees from nominal against a limit of {limit:g} "
            f"(a quarter of the spacing); the assembly is not C{n} about one axis"
        )
    angle_error = abs(record.angle_deg - nominal)
    if not angle_error <= ANGLE_TOLERANCE_DEG:
        raise SymmetryGateError(
            f"rotation-angle gate: superposing the assembly on its cyclic permutation is a turn "
            f"of {record.angle_deg:.3f} degrees, {angle_error:.3f} degrees from the {nominal:g} "
            f"of C{n} against a limit of {ANGLE_TOLERANCE_DEG:g}; the assembly is not C{n}"
        )
    if not record.tilt_deg <= ORIENTATION_LIMIT_DEG:
        raise SymmetryGateError(
            f"orientation gate: the detected axis is {record.tilt_deg:.2f} degrees from the "
            f"file's z against a limit of {ORIENTATION_LIMIT_DEG:g}; the axis is signed by the "
            "file's +z, which must point from trans to cis, and a frame this far from it does "
            "not name an end (SPECIFICATION.md section 5.3.1 NOTE on structure:)"
        )
    return record


def detect_axis(chains: np.ndarray, n: int) -> AxisRecord:
    """Find the Cₙ axis of an assembly and gate it.

    Raises
    ------
    SymmetryGateError
        On C1, which has no permutation to superpose, and on any gate failure.
    """
    return gate_axis(measure_axis(chains, n))


@dataclass(frozen=True)
class Displacement:
    """How far the file's z axis strays from the detected axis over the C-alpha extent."""

    tilt_deg: float
    offset_nm: float
    displacement_nm: float

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the measurement as plain data."""
        return {
            "tilt_deg": self.tilt_deg,
            "offset_nm": self.offset_nm,
            "displacement_nm": self.displacement_nm,
            "budget_nm": DISPLACEMENT_BUDGET_NM,
        }


def z_displacement(
    axis: np.ndarray, point_nm: np.ndarray, z_extent_nm: tuple[float, float]
) -> Displacement:
    """Measure the file's z axis against the detected axis."""
    import numpy as np

    worst = 0.0
    for height in z_extent_nm:
        on_axis = point_nm + ((height - point_nm[2]) / axis[2]) * axis
        worst = max(worst, float(np.hypot(on_axis[0], on_axis[1])))
    foot = point_nm - (point_nm @ axis) * axis
    return Displacement(
        tilt_deg=tilt_deg(axis),
        offset_nm=float(np.linalg.norm(foot)),
        displacement_nm=worst,
    )


def check_z_axis(record: AxisRecord, z_extent_nm: tuple[float, float]) -> Displacement:
    """Admit ``symmetry.axis: z`` only inside the displacement budget.

    Raises
    ------
    SymmetryGateError
        When the displacement exceeds the budget.
    """
    found = z_displacement(record.axis, record.centroid_nm, z_extent_nm)
    if not found.displacement_nm <= DISPLACEMENT_BUDGET_NM:
        raise SymmetryGateError(
            f"axis: z displacement gate: the file's z axis is {found.displacement_nm:.4f} nm from "
            f"the detected C{record.n} axis over the C-alpha axial extent "
            f"[{z_extent_nm[0]:.2f}, {z_extent_nm[1]:.2f}] nm (tilt {found.tilt_deg:.3f} "
            f"degrees, offset {found.offset_nm:.4f} nm), against a budget of "
            f"{DISPLACEMENT_BUDGET_NM:g} nm; use symmetry.axis: auto"
        )
    return found


def minimal_rotation(axis: np.ndarray) -> np.ndarray:
    """Return the smallest rotation taking the unit ``axis`` to the file's z."""
    import numpy as np

    z = np.array(_Z)
    cross = np.cross(axis, z)
    sine = float(np.linalg.norm(cross))
    cosine = float(axis @ z)
    if sine < 1e-15:
        if cosine > 0.0:
            return np.eye(3)
        raise ValueError("the axis is antiparallel to z; the orientation gate refuses this")
    k = cross / sine
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.asarray(np.eye(3) + sine * skew + (1.0 - cosine) * (skew @ skew), dtype=np.float64)


def frame_rotation(record: AxisRecord, first_centroid_nm: np.ndarray) -> np.ndarray:
    """Return ``Q``: the axis onto z, then a turn putting chain 0 on +x."""
    import numpy as np

    align = minimal_rotation(record.axis)
    moved = align @ (first_centroid_nm - record.foot_nm)
    psi = -math.atan2(float(moved[1]), float(moved[0]))
    turn = np.array(
        [[math.cos(psi), -math.sin(psi), 0.0], [math.sin(psi), math.cos(psi), 0.0], [0, 0, 1.0]]
    )
    return np.asarray(turn @ align, dtype=np.float64)

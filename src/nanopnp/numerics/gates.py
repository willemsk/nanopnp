"""Solver gates asserted at every nonlinear iterate (NUM-17, PHY-06, QR-12)."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import numpy as np

from nanopnp.core.constants import AVOGADRO
from nanopnp.core.scaling import MOL_PER_M3_PER_MOL_PER_L, NM_PER_M
from nanopnp.core.typing import Expression, Mesh

logger = logging.getLogger(__name__)

# Steric diameters a_i (Bazant 2009; a model parameter) and a_0: SPECIFICATION.md PHY-05.
ION_DIAMETER_NM = 0.5

WATER_DIAMETER_NM = 0.311

PACKING_LIMIT = 1.0

# Why this, PACKING_WARNING and MINIMUM_WALL_DISTANCE_NM: .knowledge/06, Gate constants.
INTERIOR_OFFSET = 1e-4

PACKING_WARNING = 0.8


class GateViolationError(RuntimeError):
    """A numerical gate failed (NUM-17); the solve must stop."""

    def __init__(
        self,
        gate: str,
        quantity: str,
        value: float,
        location: tuple[float, float] | None = None,
        coordinates: tuple[str, str] = ("r", "z"),
        detail: str = "",
    ) -> None:
        self.gate = gate
        self.quantity = quantity
        self.value = value
        self.location = location
        self.detail = detail
        where = (
            ""
            if location is None
            else (
                f" at {coordinates[0]} = {location[0]:.6g} nm, "
                f"{coordinates[1]} = {location[1]:.6g} nm"
            )
        )
        clause = f"; {detail}" if detail else ""
        super().__init__(f"{gate} gate failed: {quantity} = {value:.6g}{where}{clause}")


_SAMPLER_CACHE = "_nanopnp_field_samplers"


@dataclass
class FieldSampler:
    """Evaluate coefficient functions at a mesh's P2 nodal set, restricted to ``materials``."""

    mesh: Mesh
    coordinates: tuple[str, str] = ("r", "z")
    materials: str | None = None
    _points: np.ndarray | None = field(default=None, init=False, repr=False, compare=False)
    _located: Expression | None = field(default=None, init=False, repr=False, compare=False)

    @classmethod
    def shared(
        cls,
        mesh: Mesh,
        *,
        coordinates: tuple[str, str] = ("r", "z"),
        materials: str | None = None,
    ) -> FieldSampler:
        """Return the one sampler of this mesh and material set, cached on the mesh."""
        cache: dict[tuple[tuple[str, str], str | None], FieldSampler] | None = getattr(
            mesh, _SAMPLER_CACHE, None
        )
        if cache is None:
            cache = {}
            setattr(mesh, _SAMPLER_CACHE, cache)
        key = (coordinates, materials)
        found = cache.get(key)
        if found is None:
            found = cache[key] = cls(mesh, coordinates=coordinates, materials=materials)
        return found

    @property
    def points(self) -> np.ndarray:
        """Return the sample points as an ``(n, 2)`` array, computed once."""
        if self._points is None:
            self._points = self._build_points()
        return self._points

    @property
    def located(self) -> Expression:
        """Return the sample points located in the mesh, computed once."""
        if self._located is None:
            points = self.points
            self._located = self.mesh(points[:, 0], points[:, 1])
        return self._located

    def _build_points(self) -> np.ndarray:
        import ngsolve as ngs
        import numpy as np

        elements = self.mesh.Elements(ngs.VOL)
        if self.materials is not None:
            selected = self.mesh.Materials(self.materials).Mask()
            if selected.NumSet() == 0:
                known = ", ".join(sorted(set(self.mesh.GetMaterials())))
                raise ValueError(
                    f"no material matching {self.materials!r} in this mesh; it has {known}"
                )
            elements = [el for el in elements if selected[el.index]]
        corners = np.array([[self.mesh[v].point for v in el.vertices] for el in elements])
        centroids = corners.mean(axis=1)
        midpoints = np.concatenate(
            [0.5 * (corners[:, a, :] + corners[:, b, :]) for a, b in ((0, 1), (1, 2), (2, 0))]
        )
        if self.materials is None:
            stacked = np.concatenate([corners.reshape(-1, 2), midpoints, centroids])
        else:
            pull = np.concatenate([corners.reshape(-1, 2), midpoints, centroids])
            owners = np.concatenate(
                [
                    # corners run element by element, midpoints edge by edge over all
                    # elements, so the centroid array repeats differently for each.
                    np.repeat(centroids, corners.shape[1], axis=0),
                    np.tile(centroids, (3, 1)),
                    centroids,
                ]
            )
            stacked = pull + INTERIOR_OFFSET * (owners - pull)
        rounded = np.round(stacked, 12)
        rounded[rounded == 0.0] = 0.0  # collapse -0.0, which reads as a bug in a diagnostic
        return np.unique(rounded, axis=0)

    def evaluate(self, expression: Expression) -> np.ndarray:
        """Return ``expression`` at every sample point; ValueError if not scalar."""
        import numpy as np

        values = np.asarray(expression(self.located)).reshape(len(self.points), -1)
        if values.shape[1] != 1:
            raise ValueError(
                f"gate expressions must be scalar, got {values.shape[1]} components; "
                "sample each component separately"
            )
        return values[:, 0]

    def minimum(self, expression: Expression) -> tuple[float, tuple[float, float]]:
        """Return the smallest sampled value of ``expression`` and where it occurred."""
        import numpy as np

        values = self.evaluate(expression)
        index = int(np.argmin(values))
        return float(values[index]), (float(self.points[index, 0]), float(self.points[index, 1]))

    def maximum(self, expression: Expression) -> tuple[float, tuple[float, float]]:
        """Return the largest sampled value of ``expression`` and where it occurred."""
        import numpy as np

        values = self.evaluate(expression)
        index = int(np.argmax(values))
        return float(values[index]), (float(self.points[index, 0]), float(self.points[index, 1]))

    def maximum_magnitude(self, expression: Expression) -> tuple[float, tuple[float, float]]:
        """Return the largest sampled ``|expression|`` and where it occurred."""
        import numpy as np

        values = np.abs(self.evaluate(expression))
        index = int(np.argmax(values))
        return float(values[index]), (float(self.points[index, 0]), float(self.points[index, 1]))


class Gate(Protocol):
    """One assertion checked at every Newton iterate."""

    name: str

    def check(self) -> None:
        """Raise :class:`GateViolationError` if the current state violates the gate."""
        ...
        ...


@dataclass
class PositivityGate:
    """``min_i c_i > 0``: a negative concentration makes ``ln c`` undefined."""

    sampler: FieldSampler
    concentrations: Mapping[str, Expression]
    name: str = "concentration positivity"

    def check(self) -> None:
        """Raise if any species is non-positive anywhere in the sample set."""
        for species, concentration in self.concentrations.items():
            value, location = self.sampler.minimum(concentration)
            if not value > 0.0:
                raise GateViolationError(
                    self.name, species, value, location, self.sampler.coordinates
                )


@dataclass
class PackingFractionGate:
    """``Phi = sum_j N_A a_j^3 c_j < 1``, with concentrations in mol/m^3 and diameters in nm.

    Parameters
    ----------
    diameters_nm
        Steric cubic diameter per species; defaults to the ion diameter for every species.
    """

    sampler: FieldSampler
    concentrations: Mapping[str, Expression]
    diameters_nm: Mapping[str, float] | None = None
    limit: float = PACKING_LIMIT
    name: str = "packing fraction"

    def __post_init__(self) -> None:
        if not self.concentrations:
            raise ValueError(
                "the packing-fraction gate needs at least one species; an empty mapping "
                "would make Phi undefined and the NUM-17 assertion vacuous"
            )

    def diameter_nm(self, species: str) -> float:
        """Return the steric cubic diameter of a species, in nm."""
        if self.diameters_nm is None:
            return ION_DIAMETER_NM
        return self.diameters_nm.get(species, ION_DIAMETER_NM)

    @property
    def packing_fraction(self) -> Expression:
        """Return ``Phi`` as a coefficient function."""
        terms = [
            excluded_volume_m3_per_mol(self.diameter_nm(species)) * concentration
            for species, concentration in self.concentrations.items()
        ]
        total = terms[0]
        for term in terms[1:]:
            total = total + term
        return total

    def check(self) -> None:
        """Raise if ``Phi`` reaches the limit anywhere in the sample set."""
        value, location = self.sampler.maximum(self.packing_fraction)
        # ``not <`` so that NaN fails: the sampler's argmax lands on a NaN.
        if not value < self.limit:
            raise GateViolationError(
                self.name, "packing fraction Phi", value, location, self.sampler.coordinates
            )
        if value >= PACKING_WARNING:
            logger.warning(
                "packing fraction Phi = %.4g at %s = %.6g nm, %s = %.6g nm, approaching the "
                "singularity of the steric flux at Phi = 1 (PHY-06)",
                value,
                self.sampler.coordinates[0],
                location[0],
                self.sampler.coordinates[1],
                location[1],
            )


@dataclass
class PotentialIncrementGate:
    """``||delta phi||_inf <= V_T`` on the damped increment (cap 1 nondimensional)."""

    sampler: FieldSampler
    increment: Expression
    limit: float = 1.0
    name: str = "potential increment cap"

    def check(self) -> None:
        """Raise if the damped increment exceeds the cap anywhere."""
        value, location = self.sampler.maximum_magnitude(self.increment)
        if not value <= self.limit:  # NaN fails
            raise GateViolationError(
                self.name,
                "|delta phi| / V_T",
                value,
                location,
                self.sampler.coordinates,
            )


MINIMUM_WALL_DISTANCE_NM = -1.0e-3


@dataclass(frozen=True)
class WallDistanceMeasurement:
    """What the wall-distance gate measured, whether or not it passed."""

    minimum_nm: float
    location: tuple[float, float]
    negative_fraction: float
    samples: int

    def summary(self) -> dict[str, float | int | list[float]]:
        """Return this measurement as plain data, for the manifest and the dataset."""
        return {
            "minimum_nm": self.minimum_nm,
            "location_nm": [self.location[0], self.location[1]],
            "negative_fraction": self.negative_fraction,
            "samples": self.samples,
        }


@dataclass
class WallDistanceGate:
    """``min d >= -1e-3 nm`` over the fluid, wherever a wall correction is active."""

    sampler: FieldSampler
    distance: Expression
    minimum_nm: float = MINIMUM_WALL_DISTANCE_NM
    name: str = "wall-distance admissibility"

    def measure(self) -> WallDistanceMeasurement:
        """Return the sampled minimum, where it occurred, and the negative fraction."""
        import numpy as np

        values = self.sampler.evaluate(self.distance)
        index = int(np.argmin(values))
        return WallDistanceMeasurement(
            minimum_nm=float(values[index]),
            location=(float(self.sampler.points[index, 0]), float(self.sampler.points[index, 1])),
            negative_fraction=float(np.count_nonzero(values < 0.0) / values.size),
            samples=int(values.size),
        )

    def check(self) -> None:
        """Raise if the field samples below the threshold anywhere in the fluid."""
        self.checked()

    def checked(self) -> WallDistanceMeasurement:
        """Sample the field once, raise if it fails, and return what was measured."""
        found = self.measure()
        if not found.minimum_nm >= self.minimum_nm:  # NaN fails
            raise GateViolationError(
                self.name,
                "min d",
                found.minimum_nm,
                found.location,
                self.sampler.coordinates,
                detail=(
                    f"NUM-34 requires min d >= {self.minimum_nm:.6g} nm wherever a wall "
                    f"correction is active, and {found.negative_fraction:.3%} of the "
                    f"{found.samples} fluid samples are negative. The ion wall function's root "
                    "is at d = -0.01 nm, so a field this far below zero reverses the sign of "
                    "the diffusivity and mobility rather than attenuating them: refine the mesh "
                    "at the wall (numerics.mesh.wall_h_nm), do not widen this gate"
                ),
            )
        logger.debug(
            "wall-distance gate: min d = %.6g nm at (%.4g, %.4g) over %d fluid samples",
            found.minimum_nm,
            found.location[0],
            found.location[1],
            found.samples,
        )
        return found


PECLET_WARNING = 1.0


@dataclass(frozen=True)
class PecletMeasurement:
    """What the cell-Peclet diagnostic measured; ``Pe_K`` assumes no Einstein relation."""

    maximum: float
    species: str
    location: tuple[float, float]
    exceeding: int
    samples: int
    per_species: Mapping[str, float]
    expression: str = "||b_i|| h_K / (2 D_i), b_i = z_i mu_i grad(phi~) + D_i beta_i - Pe u~"

    @property
    def exceeding_fraction(self) -> float:
        """Return the fraction of samples at or above the threshold."""
        return 0.0 if self.samples == 0 else self.exceeding / self.samples

    def summary(self) -> dict[str, float | int | str | list[float] | dict[str, float]]:
        """Return this measurement as plain data, for the manifest and the dataset."""
        return {
            "maximum": self.maximum,
            "species": self.species,
            "location_nm": [self.location[0], self.location[1]],
            "exceeding": self.exceeding,
            "exceeding_fraction": self.exceeding_fraction,
            "samples": self.samples,
            "per_species": dict(self.per_species),
            "expression": self.expression,
        }


@dataclass
class PecletDiagnostic:
    """``Pe_K`` on a converged state: a warning, never a gate."""

    sampler: FieldSampler
    peclet: Mapping[str, Expression]
    threshold: float = PECLET_WARNING
    name: str = "cell Peclet"

    def measure(self) -> PecletMeasurement:
        """Return the largest sampled ``Pe_K``, where, and how many samples exceed it."""
        import numpy as np

        if not self.peclet:
            raise ValueError(
                "the Pe_h diagnostic was given no species; NUM-12 evaluates it on the "
                "advective velocity of each ion, so an empty mapping reports a maximum of "
                "zero from a diagnostic that sampled nothing"
            )
        best = -1.0
        best_species = ""
        best_location = (0.0, 0.0)
        exceeding = 0
        samples = 0
        per_species: dict[str, float] = {}
        for species in sorted(self.peclet):
            values = self.sampler.evaluate(self.peclet[species])
            index = int(np.argmax(values))
            per_species[species] = float(values[index])
            exceeding += int(np.count_nonzero(values >= self.threshold))
            samples += int(values.size)
            if float(values[index]) > best:
                best = float(values[index])
                best_species = species
                best_location = (
                    float(self.sampler.points[index, 0]),
                    float(self.sampler.points[index, 1]),
                )
        return PecletMeasurement(
            maximum=best,
            species=best_species,
            location=best_location,
            exceeding=exceeding,
            samples=samples,
            per_species=per_species,
        )

    def report(self) -> PecletMeasurement:
        """Measure, log at the level the number deserves, and return the measurement."""
        found = self.measure()
        if found.maximum >= self.threshold:
            logger.warning(
                "%s diagnostic: Pe_K = %.4g for %s at %s = %.4g nm, %s = %.4g nm, over "
                "%d of %d fluid samples at or above %.4g (NUM-12). The mesh does not resolve "
                "the double layer at the NUM-30 rate there; the transport operator is "
                "under-resolved and the NUM-17 positivity gate is what will fail if it has "
                "become inadmissible. Evaluated as %s",
                self.name,
                found.maximum,
                found.species,
                self.sampler.coordinates[0],
                found.location[0],
                self.sampler.coordinates[1],
                found.location[1],
                found.exceeding,
                found.samples,
                self.threshold,
                found.expression,
            )
        else:
            logger.info(
                "%s diagnostic: max Pe_K = %.4g for %s over %d fluid samples, below %.4g",
                self.name,
                found.maximum,
                found.species,
                found.samples,
                self.threshold,
            )
        return found


def excluded_volume_m3_per_mol(diameter_nm: float) -> float:
    """Return ``N_A a^3`` in m^3/mol, the volume one mole of a species occupies."""
    return AVOGADRO * (diameter_nm / NM_PER_M) ** 3


def maximum_packing_M(diameter_nm: float = ION_DIAMETER_NM) -> float:
    """Return the concentration in mol/L at which one species alone reaches ``Phi = 1``."""
    return 1.0 / (excluded_volume_m3_per_mol(diameter_nm) * MOL_PER_M3_PER_MOL_PER_L)


def check_all(gates: Sequence[Gate]) -> None:
    """Run every gate in order; the first violation aborts."""
    for gate in gates:
        gate.check()

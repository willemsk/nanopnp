"""Solver gates asserted at every nonlinear iterate (NUM-17, PHY-06, QR-12).

A nonlinear solve for this system fails in two ways. It can diverge, which is
loud and harmless. Or it can converge to a state that is not a solution of the
physical problem — a slightly negative concentration inside the double layer, a
packing fraction that has crossed 1 so that the steric term ``beta_i`` passed
through its singularity — and report success. The second is the dangerous one,
because the run then produces a current that looks entirely plausible and is
wrong by per cent, which is the size of the rectification signal being measured.

So each of the three conditions of NUM-17 is asserted at every step, and a
violation aborts with a diagnostic naming the gate, the offending quantity, its
value and where in the mesh it occurred. Never a plausible wrong answer.

Sampling
--------
The gates evaluate at the P2 nodal set — element vertices and edge midpoints —
plus element centroids. For a P2 field those points carry the degrees of freedom
themselves, so a violation localised to one node is always caught. A field that
dips below zero strictly *between* nodal points, over a subregion narrower than
an element, can in principle be missed; that is a mesh that does not resolve the
double layer, which NUM-30 and the ``Pe_h`` warning of NUM-12 address separately.
This is a deliberate accuracy/cost trade: a quadrature-based gate at high order
would cost more than the Newton step it guards.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import numpy as np

from nanopnp.core.constants import AVOGADRO
from nanopnp.core.typing import Expression, Mesh

logger = logging.getLogger(__name__)

NM_TO_M = 1e-9
"""Metres per nanometre; the steric diameters are quoted in nm."""

ION_DIAMETER_NM = 0.5
"""Steric cubic diameter ``a_i`` of every ion, in nm (PHY-05, Bazant 2009).

Maximum packing 13.3 M. There is no experimental determination of this value;
it is a model parameter, and it is the one that sets where ``beta_i`` becomes
singular.
"""

WATER_DIAMETER_NM = 0.311
"""Steric cubic diameter ``a_0`` of water, in nm (PHY-05). Maximum packing 55.2 M."""

PACKING_LIMIT = 1.0
"""``Phi`` at which ``beta_i`` is singular (PHY-06)."""

PACKING_WARNING = 0.8
"""Where to start logging that the steric term is approaching its singularity.

Not a specified threshold; chosen so that a run drifting towards ``Phi = 1``
leaves a trace in the log before it aborts.
"""


class GateViolationError(RuntimeError):
    """A NUM-17 assertion failed; the solve must stop.

    Parameters
    ----------
    gate
        Name of the gate, as it appears in NUM-17.
    quantity
        The physical quantity that violated it, e.g. ``"c_Na"``.
    value
        Its offending value.
    location
        Where it occurred, in mesh units, or ``None`` for a global quantity.
    coordinates
        Names of the two coordinates, for the message.
    """

    def __init__(
        self,
        gate: str,
        quantity: str,
        value: float,
        location: tuple[float, float] | None = None,
        coordinates: tuple[str, str] = ("r", "z"),
    ) -> None:
        self.gate = gate
        self.quantity = quantity
        self.value = value
        self.location = location
        where = (
            ""
            if location is None
            else (
                f" at {coordinates[0]} = {location[0]:.6g} nm, "
                f"{coordinates[1]} = {location[1]:.6g} nm"
            )
        )
        super().__init__(f"{gate} gate failed: {quantity} = {value:.6g}{where}")


@dataclass
class FieldSampler:
    """Evaluates coefficient functions at the P2 nodal set of a mesh.

    Parameters
    ----------
    mesh
        The mesh to sample.
    coordinates
        Names of the two coordinates, used only in diagnostics.
    """

    mesh: Mesh
    coordinates: tuple[str, str] = ("r", "z")
    _points: np.ndarray | None = field(default=None, init=False, repr=False)

    @property
    def points(self) -> np.ndarray:
        """Return the sample points as an ``(n, 2)`` array, computed once."""
        if self._points is None:
            self._points = self._build_points()
        return self._points

    def _build_points(self) -> np.ndarray:
        """Collect vertices, edge midpoints and centroids of every element."""
        import ngsolve as ngs
        import numpy as np

        corners = np.array(
            [[self.mesh[v].point for v in el.vertices] for el in self.mesh.Elements(ngs.VOL)]
        )
        centroids = corners.mean(axis=1)
        midpoints = np.concatenate(
            [0.5 * (corners[:, a, :] + corners[:, b, :]) for a, b in ((0, 1), (1, 2), (2, 0))]
        )
        stacked = np.concatenate([corners.reshape(-1, 2), midpoints, centroids])
        rounded = np.round(stacked, 12)
        rounded[rounded == 0.0] = 0.0  # collapse -0.0, which reads as a bug in a diagnostic
        return np.unique(rounded, axis=0)

    def evaluate(self, expression: Expression) -> np.ndarray:
        """Return ``expression`` evaluated at every sample point, as a flat array."""
        import numpy as np

        points = self.points
        mesh_points = self.mesh(points[:, 0], points[:, 1])
        return np.asarray(expression(mesh_points)).reshape(len(points), -1)[:, 0]

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


@dataclass
class PositivityGate:
    """``min_i c_i > 0`` (NUM-17).

    A negative concentration is unphysical, makes ``ln c`` undefined for the
    log-variable branch, and reverses the sign of that species' contribution to
    the current. It is the single most common way a PNP solve returns a wrong
    answer quietly.

    Parameters
    ----------
    sampler
        Sampler over the solve mesh.
    concentrations
        Species name to the coefficient function holding its concentration.
    """

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
    """``Phi = sum_j N_A a_j^3 c_j < 1`` (NUM-17, PHY-06).

    ``beta_i`` carries ``1/(1 - Phi)``, so the steric flux is singular at
    ``Phi = 1`` and changes sign beyond it — ions would then be driven *into*
    the crowded region and the solve diverges. The gate exists so the abort
    names the crowding rather than the divergence.

    Concentrations are in mol/m^3 and diameters in nm; both conversions happen
    here.

    Parameters
    ----------
    sampler
        Sampler over the solve mesh.
    concentrations
        Species name to its concentration coefficient function, in mol/m^3.
    diameters_nm
        Species name to its steric cubic diameter ``a_j``, in nm. Defaults to
        ``ION_DIAMETER_NM`` for every species present.
    limit
        Packing fraction at which to abort.
    """

    sampler: FieldSampler
    concentrations: Mapping[str, Expression]
    diameters_nm: Mapping[str, float] | None = None
    limit: float = PACKING_LIMIT
    name: str = "packing fraction"

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
        if value >= self.limit:
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
    """``||delta phi||_inf <= V_T`` (NUM-17).

    In the nondimensional variables of NUM-09 the potential is measured in
    ``V_T``, so the cap is 1. A Newton step that moves the potential by more
    than a thermal voltage anywhere has left the basin in which the Boltzmann
    factors are meaningful; damping is the cure, and this gate is what tells the
    damping loop that the step is too long.

    Parameters
    ----------
    sampler
        Sampler over the solve mesh.
    increment
        Coefficient function holding the potential component of the *damped*
        Newton increment, in units of ``V_T``.
    limit
        Cap, in units of ``V_T``.
    """

    sampler: FieldSampler
    increment: Expression
    limit: float = 1.0
    name: str = "potential increment cap"

    def check(self) -> None:
        """Raise if the damped increment exceeds the cap anywhere."""
        value, location = self.sampler.maximum_magnitude(self.increment)
        if value > self.limit:
            raise GateViolationError(
                self.name,
                "|delta phi| / V_T",
                value,
                location,
                self.sampler.coordinates,
            )


def excluded_volume_m3_per_mol(diameter_nm: float) -> float:
    """Return ``N_A a^3`` in m^3/mol, the volume one mole of a species occupies.

    Multiplying by a concentration in mol/m^3 gives the dimensionless packing
    contribution. For the ion default ``a = 0.5 nm`` this is
    7.528e-5 m^3/mol, so ``Phi = 1`` at 13.3 M; for water ``a_0 = 0.311 nm`` it
    is 1.811e-5 m^3/mol, so ``Phi = 1`` at 55.2 M (PHY-05).
    """
    return AVOGADRO * (diameter_nm * NM_TO_M) ** 3


def maximum_packing_M(diameter_nm: float = ION_DIAMETER_NM) -> float:
    """Return the concentration in mol/L at which one species alone reaches ``Phi = 1``."""
    return 1.0 / (excluded_volume_m3_per_mol(diameter_nm) * 1e3)


def check_all(gates: Sequence[Gate]) -> None:
    """Run every gate in order; the first violation aborts."""
    for gate in gates:
        gate.check()

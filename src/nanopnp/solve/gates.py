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
from nanopnp.core.scaling import MOL_PER_M3_PER_MOL_PER_L, NM_PER_M
from nanopnp.core.typing import Expression, Mesh

logger = logging.getLogger(__name__)

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

INTERIOR_OFFSET = 1e-4
"""How far a restricted sampler pulls its points towards their element's centroid.

A vertex or edge midpoint on the fluid/solid interface belongs to elements on
both sides, and NGSolve's point location may resolve it into the solid one. A
concentration lives on the fluid alone, so evaluated there it comes back as
**zero** — not positive — and the gate would abort on a membrane on every
realistic mesh before Newton took a step. Contracting each element's sample
points towards its own centroid by this fraction puts them strictly inside the
element they came from.

The value is measured rather than chosen for tidiness: at 1e-6 the shifted
points still resolve into the solid on the analytic pore at both ``maxh`` 6 nm
and 2 nm, and 1e-5 is the first that does not. 1e-4 keeps an order of margin.
For a P2 field the sampled value then differs from the nodal one by 1e-4 of the
field's variation across that element, which no gate threshold can notice.
"""

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
    detail
        One further clause appended to the message, for a gate whose diagnostic
        needs more than one number to be actionable -- the NUM-34 gate reports
        the *extent* of the violation as well as its worst point, because a
        field one node below the threshold and a field negative over 8 % of the
        fluid ask for different responses.
    """

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


@dataclass
class FieldSampler:
    """Evaluates coefficient functions at the P2 nodal set of a mesh.

    Parameters
    ----------
    mesh
        The mesh to sample.
    coordinates
        Names of the two coordinates, used only in diagnostics.
    materials
        Material-name regular expression restricting the sample set to those
        domains. Required whenever the sampled field lives on a subdomain: a
        finite-element function evaluated outside its own ``definedon`` region
        comes back as zero, and a concentration gate sampling the membrane would
        then abort on a solid, reporting a violation that does not exist.
    """

    mesh: Mesh
    coordinates: tuple[str, str] = ("r", "z")
    materials: str | None = None
    _points: np.ndarray | None = field(default=None, init=False, repr=False, compare=False)
    _located: Expression | None = field(default=None, init=False, repr=False, compare=False)

    @property
    def points(self) -> np.ndarray:
        """Return the sample points as an ``(n, 2)`` array, computed once."""
        if self._points is None:
            self._points = self._build_points()
        return self._points

    @property
    def located(self) -> Expression:
        """Return the sample points located in the mesh, computed once.

        Locating a point is a search over the elements, and the gates evaluate
        several coefficient functions at the same fixed points at every trial
        step of every Newton iteration. Doing the search once per sampler rather
        than once per evaluation takes it off the inner loop entirely; the mesh
        does not move during a solve, so the located points stay valid.
        """
        if self._located is None:
            points = self.points
            self._located = self.mesh(points[:, 0], points[:, 1])
        return self._located

    def _build_points(self) -> np.ndarray:
        """Collect vertices, edge midpoints and centroids of every element.

        Raises
        ------
        ValueError
            If ``materials`` selects no domain, which would leave the gate with
            nothing to sample and its assertion vacuous.
        """
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
            # Keep every point inside the element that contributed it; see
            # INTERIOR_OFFSET. Deduplication no longer merges the copies a shared
            # vertex produces, which is the cost of the guarantee.
            pull = np.concatenate([corners.reshape(-1, 2), midpoints, centroids])
            owners = np.concatenate(
                [
                    # corners.reshape runs element by element; the midpoint
                    # blocks run edge by edge over all elements. The two need
                    # different repetitions of the centroid array to line up.
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
        """Return ``expression`` evaluated at every sample point, as a flat array.

        Raises
        ------
        ValueError
            If ``expression`` is not scalar. Silently keeping the first
            component would leave the gate reporting on one component of a
            vector field and passing on the others, which is exactly the quiet
            wrong answer the gates exist to prevent.
        """
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

    def __post_init__(self) -> None:
        """Reject a gate with nothing to sum, which would silently assert nothing."""
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


MINIMUM_WALL_DISTANCE_NM = -1.0e-3
"""NUM-34: how far below zero the discrete distance field may sample.

Bounded on both sides and chosen between them, and held here as one named
constant because the two places that read it -- the per-solve gate and the
per-mesh check a sweep plan runs -- must not be able to disagree.

It cannot be zero. ``GridFunction.Set`` projects element-wise, and although
:func:`nanopnp.mesh.distance.wall_distance` zeroes the constrained degrees of
freedom outright so that the wall itself is exact, the interior residual is a
few times ``1e-4`` nm with a platform-dependent sign; a gate at zero would gate
the rounding mode.

It cannot be ``-1e-2`` nm, which is ``-P2``, the ion wall function's own root:
a gate there admits a diffusivity of exactly zero as its last passing state, and
it would restate a fitted coefficient in Python rather than reading it from the
correction data.

One order inside the root and one order outside the projection residual. What
the PHY-02 clamp can then silently absorb is bounded: at ``d = -1e-3`` the
unclamped ion factor is ``1 - exp(-0.0558) = 0.0543`` against the clamped
``0.0601``, a difference of ``5.8e-3`` on a factor whose wall value is
``6.0e-2`` (SPECIFICATION.md NUM-34).
"""


@dataclass(frozen=True)
class WallDistanceMeasurement:
    """What the NUM-34 gate measured, whether or not it passed.

    Recorded in the artefact summary and in the FR-25 manifest as NUM-34
    requires, so that a field which passed *narrowly* is visible in the record
    of a sweep rather than only in the log of the one member that failed.
    """

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
    """``min d >= -1e-3 nm`` over the fluid, wherever a wall correction is active (NUM-34).

    Not a NUM-17 gate: it is checked once per solve, on a field that does not
    change between Newton steps, rather than at every iterate. It is here
    because it is the same kind of assertion against the same sampler, and
    because a run must not be able to reach Newton at all on a field whose sign
    the corrections will misread.

    The ion wall function ``1 - exp(-P1 (d + P2))`` has its root at ``d = -P2``,
    so a negative sample reverses the sign of ``D_i`` and ``mu_i`` rather than
    attenuating them. PHY-02's clamp keeps that from producing a *plausible*
    wrong current; this gate keeps it from producing one at all, because a field
    that is genuinely negative is under-resolved at the wall and the clamp
    resolves nothing.

    Parameters
    ----------
    sampler
        Sampler over the fluid materials of the solve mesh. Restricted to the
        fluid because the field is solved there and a solid sample would report
        a violation that no correction ever reads.
    distance
        The distance field as the corrections read it -- after mollification
        where NUM-31's smoothing pass is applied, because a mollified field is a
        different field and gating the un-mollified one would gate something no
        form evaluates.
    minimum_nm
        The threshold. Defaults to :data:`MINIMUM_WALL_DISTANCE_NM`.
    """

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
        found = self.measure()
        if found.minimum_nm < self.minimum_nm:
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


def excluded_volume_m3_per_mol(diameter_nm: float) -> float:
    """Return ``N_A a^3`` in m^3/mol, the volume one mole of a species occupies.

    Multiplying by a concentration in mol/m^3 gives the dimensionless packing
    contribution. For the ion default ``a = 0.5 nm`` this is
    7.528e-5 m^3/mol, so ``Phi = 1`` at 13.3 M; for water ``a_0 = 0.311 nm`` it
    is 1.811e-5 m^3/mol, so ``Phi = 1`` at 55.2 M (PHY-05).
    """
    return AVOGADRO * (diameter_nm / NM_PER_M) ** 3


def maximum_packing_M(diameter_nm: float = ION_DIAMETER_NM) -> float:
    """Return the concentration in mol/L at which one species alone reaches ``Phi = 1``."""
    return 1.0 / (excluded_volume_m3_per_mol(diameter_nm) * MOL_PER_M3_PER_MOL_PER_L)


def check_all(gates: Sequence[Gate]) -> None:
    """Run every gate in order; the first violation aborts."""
    for gate in gates:
        gate.check()

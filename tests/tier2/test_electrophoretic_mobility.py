"""VER-21: the electrophoretic mobility of a charged sphere, in both limits.

A free particle in an applied field moves at the speed at which the total force
on it vanishes. The problem is linear in ``(E_0, U)`` at low ``zeta``, so two
solves on one mesh give that speed without iterating:

* **the field solve** — the body held, ``E~_0`` applied, quiescent far field —
  returns ``F_E``;
* **the drag solve** — no field, the fluid streaming past the held body at
  ``U~_0`` — returns ``F_U``.

The combination that is force-free streams past the body at
``U~ = -F_E U~_0 / F_U``; in the laboratory frame the body moves at ``-U~``, so
``mu~_e = F_E U~_0 / (F_U E~_0)``. In the NUM-09 variables the mobility scale is
``eps V_T / eta``, which strips both closed forms of every material constant:
Hueckel is ``mu~_e = 2 zeta~/3`` and Smoluchowski is ``mu~_e = zeta~``.

**Why the far field here is uniform and VER-19's is not.** VER-19 measures a
single confined solve, where a uniform stream at ``R = 10a`` adds an ``a/R`` wall
correction of 28 %. Here the two solves are combined into the force-free state,
whose true far field *is* uniform to ``O((a/R)^3)`` — a force-free particle
radiates no Stokeslet. Imposing the exact translating-sphere field on ``outer``
would inject exactly the ``O(a/R)`` Stokeslet the physical solution does not
have, so the pair is posed with a uniform stream on purpose and the large wall
corrections in ``F_E`` and ``F_U`` divide out of the ratio.

**What is asserted, and why it is Henry's function.** ``mu_e = (2 eps zeta/3 eta)
f(kappa a)`` with ``f(0) = 1`` and ``f(inf) = 3/2`` is the closed form at *any*
``kappa a`` in the low-zeta limit; Hueckel and Smoluchowski are its two ends.
Ohshima's approximation to it,

    f(x) = 1 + 1 / (2 [1 + 2.5/(x (1 + 2 exp(-x)))]^3)

is used as the reference. The approach to Smoluchowski goes as ``1/kappa a`` and
is slow: at ``kappa a = 16.5``, the largest this test can afford in a Tier-2
budget, Henry is still 11.5 % below ``eps zeta/eta``. So the gate against
Smoluchowski is stated at 15 % — a 5 % gate there would be asserting something
untrue — while the gate against Henry, which is the real verification, is 5 % at
every ``kappa a``, and the *approach* is asserted by requiring ``mu~_e/zeta~`` to
rise monotonically towards 1 across the three points. The Hueckel end needs no
such allowance: at ``kappa a = 0.5``, ``f = 1.014``.

**zeta is measured, not prescribed.** The body carries a surface charge and the
zeta potential is read back as the ``r``-weighted mean of ``phi~`` over its
surface. Prescribing ``phi~ = zeta`` there instead would make the body an
equipotential, which expels the applied field rather than letting it refract
through a dielectric — a different problem with a different ``f(kappa a)``. The
applied perturbation is odd in ``z`` and averages out of the mean, so the value
read from the field solve is the equilibrium ``zeta`` to linear order; the drag
solve carries no applied field at all, and the two agreeing is the check that it
is.
"""

import logging
import math
from dataclasses import dataclass
from itertools import pairwise

import ngsolve as ngs
import pytest

from nanopnp.geometry.analyte import ANALYTE_BOUNDARY, AnalyteInBoxGeometry, SphereBody
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledBoundaries, CoupledModel, ModelSolution
from nanopnp.post.forces import axial_extension, extract

logger = logging.getLogger(__name__)

FIELD = 0.02
"""``E~_0``, the applied axial field in ``V_T`` per nm.

Small enough that ``E_0 lambda_D`` stays far below ``V_T`` — 0.006 ``V_T`` at the
thinnest double layer here — so the layer responds linearly and is not polarised.
"""

SPEED = 0.05
"""``U~_0`` of the drag solve, in ``u_0``. Only the ratio ``F_E/F_U`` is used."""

ZETA = 0.5
"""Target zeta in ``V_T``: 12.8 mV, inside the linear regime Henry assumes."""

HENRY_TOLERANCE = 0.05
"""VER-21's stated tolerance against Henry's closed form: 5 %.

The specification leaves it open; this states it. The measured departures are
2.3 %, 0.9 % and 1.5 % at the three ``kappa a``, set by the finite domain and by
reading a nonlinear ``zeta`` into a linear-response formula.
"""

SMOLUCHOWSKI_TOLERANCE = 0.15
"""What ``eps zeta/eta`` can honestly be asserted to at ``kappa a = 16.5``.

Henry itself is 11.5 % below Smoluchowski there, so this gate is loose by
necessity and is not the verification; the Henry gate above is.
"""


@dataclass(frozen=True)
class Case:
    """One ``kappa a`` of the sweep: the geometry and the electrolyte that set it."""

    radius_nm: float
    concentration_M: float
    outer_ratio: float
    wall_fraction: float = 0.2
    """``wall_h_nm`` as a fraction of the Debye length: five elements across it."""


CASES = (
    Case(radius_nm=1.0, concentration_M=0.0231, outer_ratio=16.0),
    Case(radius_nm=2.0, concentration_M=0.1, outer_ratio=12.0),
    Case(radius_nm=5.0, concentration_M=1.0, outer_ratio=10.0),
)
"""``kappa a`` of 0.50, 2.08 and 16.5. The last is the Tier-2 budget's limit at
about 44 000 degrees of freedom and 16 s; ``kappa a`` costs a mesh of about
``50 kappa a`` elements across, whatever the physical sizes, so reaching the 40
that a 5 % Smoluchowski gate would need is a different tier of run."""


def henry_function(kappa_a: float) -> float:
    """Return Ohshima's approximation to Henry's ``f(kappa a)``.

    Ohshima, *J. Colloid Interface Sci.* **168**, 269 (1994). Monotone from
    ``f(0) = 1``, the Hueckel end, to ``f(inf) = 3/2``, the Smoluchowski end.
    """
    return 1.0 + 1.0 / (2.0 * (1.0 + 2.5 / (kappa_a * (1.0 + 2.0 * math.exp(-kappa_a)))) ** 3)


@dataclass(frozen=True)
class Mobility:
    """One measured point: the mobility, the zeta it was measured at, and ``kappa a``."""

    kappa_a: float
    zeta: float
    mobility: float
    zeta_drift: float
    """``|zeta| `` read from the field solve minus the one read from the drag solve."""


def _surface_mean_potential(solution: ModelSolution, mesh: ngs.Mesh) -> float:
    """Return the ``r``-weighted mean of ``phi~`` over the body's surface.

    The lift is :func:`ngsolve.BoundaryFromVolumeCF` rather than a plain trace,
    for the reason ``post.forces`` documents: a coefficient evaluated on a
    boundary region is otherwise the surface restriction and not the volume
    value. Weighted by ``r`` because that is the axisymmetric surface measure.
    """
    region = mesh.Boundaries(ANALYTE_BOUNDARY)
    lifted = ngs.BoundaryFromVolumeCF(solution.potential)
    weighted = float(ngs.Integrate(lifted * ngs.x, mesh, definedon=region))
    area = float(ngs.Integrate(ngs.x, mesh, definedon=region))
    return weighted / area


def _measure(case: Case) -> Mobility:
    """Solve the field and drag problems on one mesh and return the mobility."""
    model = models.create(
        "pnp-ns",
        concentration_M=case.concentration_M,
        inertia=False,
        variable_density=False,
        pressure_constraint=True,
        solid_permittivities={"analyte": 20.0},
    )
    assert isinstance(model, CoupledModel)
    debye_nm = model.scales.debye_length_nm
    outer_nm = case.outer_ratio * case.radius_nm
    mesh = AnalyteInBoxGeometry(
        SphereBody(radius_nm=case.radius_nm), outer_radius_nm=outer_nm
    ).generate(maxh_nm=0.15 * outer_nm, wall_h_nm=case.wall_fraction * debye_nm)
    extension = axial_extension(mesh, inner_nm=1.2 * case.radius_nm, outer_nm=3.0 * case.radius_nm)

    # Debye-Hueckel around a sphere: sigma_s = eps zeta (1/a + 1/lambda_D).
    # It only has to land near the target; zeta is read back, not assumed.
    surface_charge = ZETA * (1.0 / case.radius_nm + 1.0 / debye_nm)
    still = ngs.CF((0.0, 0.0))
    common = {
        "boundaries": CoupledBoundaries(
            potential="outer",
            concentration="outer",
            velocity="analyte|outer",
            velocity_axis="axis",
        ),
        "surface_charge": ngs.CF(surface_charge),
        "surface_charge_boundary": ANALYTE_BOUNDARY,
    }
    field = model.solve(
        mesh, AXISYMMETRIC, potential_values=-FIELD * ngs.y, velocity_values=still, **common
    )
    drag = model.solve(
        mesh,
        AXISYMMETRIC,
        potential_values=0.0,
        velocity_values=mesh.BoundaryCF({"outer": ngs.CF((0.0, SPEED))}, default=still),
        **common,
    )
    field_N = extract(field, AXISYMMETRIC, extension).total_N
    drag_N = extract(drag, AXISYMMETRIC, extension).total_N
    zeta_field = _surface_mean_potential(field, mesh)
    zeta_drag = _surface_mean_potential(drag, mesh)

    point = Mobility(
        kappa_a=case.radius_nm / debye_nm,
        zeta=zeta_drag,
        mobility=field_N * SPEED / (drag_N * FIELD),
        zeta_drift=abs(zeta_field - zeta_drag),
    )
    logger.info(
        "kappa a = %.2f: zeta~ = %.4f, mu~_e = %.4f against Hueckel %.4f, Henry %.4f and "
        "Smoluchowski %.4f (f = %.4f)",
        point.kappa_a,
        point.zeta,
        point.mobility,
        2.0 * point.zeta / 3.0,
        2.0 * point.zeta / 3.0 * henry_function(point.kappa_a),
        point.zeta,
        henry_function(point.kappa_a),
    )
    return point


@pytest.fixture(scope="module")
def mobilities() -> tuple[Mobility, ...]:
    """Measure the mobility at each ``kappa a`` of the sweep."""
    return tuple(_measure(case) for case in CASES)


def test_ver21_the_mobility_follows_henrys_function_at_every_screening_ratio(
    mobilities: tuple[Mobility, ...],
) -> None:
    """``mu~_e = (2 zeta~/3) f(kappa a)`` to 5 %, across two decades of ``kappa a``.

    The real verification: one closed form covering both limits, so a mobility
    that is right at one end and wrong at the other cannot pass. A systematic
    offset in one direction at every point would be a scale error in the force
    or in the mobility unit; an error at the thin-layer end alone would be the
    double layer under-resolved.
    """
    for point in mobilities:
        expected = 2.0 * point.zeta / 3.0 * henry_function(point.kappa_a)
        error = abs(point.mobility / expected - 1.0)
        assert error < HENRY_TOLERANCE, (
            f"at kappa a = {point.kappa_a:.2f} the measured mu~_e = {point.mobility:.4f} against "
            f"Henry's {expected:.4f} (zeta~ = {point.zeta:.4f}, f = "
            f"{henry_function(point.kappa_a):.4f}): a relative error of {error:.3g} beyond the "
            f"stated {HENRY_TOLERANCE:.0%}"
        )


def test_ver21_the_huckel_limit_is_recovered_at_small_kappa_a(
    mobilities: tuple[Mobility, ...],
) -> None:
    """``mu_e = 2 eps zeta / 3 eta`` at ``kappa a = 0.5``, to 5 %.

    Henry's ``f`` is 1.014 there, so the limit is its own closed form to well
    inside the tolerance and no allowance is needed for the approach.
    """
    point = mobilities[0]
    assert point.kappa_a < 1.0, (
        f"the small-kappa_a case sits at kappa a = {point.kappa_a:.2f}, which is not the thick "
        "double layer Hueckel describes"
    )
    huckel = 2.0 * point.zeta / 3.0
    error = abs(point.mobility / huckel - 1.0)
    assert error < HENRY_TOLERANCE, (
        f"at kappa a = {point.kappa_a:.2f} the measured mu~_e = {point.mobility:.4f} against "
        f"Hueckel's 2 zeta~/3 = {huckel:.4f}, a relative error of {error:.3g} beyond the stated "
        f"{HENRY_TOLERANCE:.0%}. Henry's correction at this kappa a is only "
        f"{henry_function(point.kappa_a) - 1.0:.1%}, so this is not the asymptotics"
    )


def test_ver21_the_mobility_climbs_towards_the_smoluchowski_limit(
    mobilities: tuple[Mobility, ...],
) -> None:
    """``mu~_e/zeta~`` rises monotonically towards 1 and reaches it within 15 %.

    The approach goes as ``1/kappa a``, so what a Tier-2 budget can assert is the
    direction and the size of the remaining gap, not the limit itself. The gap is
    checked against Henry's own gap: the measurement must not be further from
    ``eps zeta/eta`` than the closed form says it should be.
    """
    ratios = [point.mobility / point.zeta for point in mobilities]
    assert all(coarse < fine for coarse, fine in pairwise(ratios)), (
        f"mu~_e/zeta~ = {[round(r, 4) for r in ratios]} does not rise with kappa a "
        f"{[round(p.kappa_a, 2) for p in mobilities]}; the mobility must run from 2/3 at the "
        "Hueckel end to 1 at the Smoluchowski end"
    )
    thinnest = mobilities[-1]
    gap = 1.0 - ratios[-1]
    henry_gap = 1.0 - 2.0 * henry_function(thinnest.kappa_a) / 3.0
    assert gap < SMOLUCHOWSKI_TOLERANCE, (
        f"at kappa a = {thinnest.kappa_a:.2f} the measured mu~_e is {gap:.1%} below "
        f"Smoluchowski's eps zeta/eta, beyond the {SMOLUCHOWSKI_TOLERANCE:.0%} this test allows. "
        f"Henry's own shortfall at this kappa a is {henry_gap:.1%}"
    )
    assert gap < henry_gap + HENRY_TOLERANCE, (
        f"the measured shortfall from Smoluchowski is {gap:.1%} against Henry's {henry_gap:.1%}; "
        "the measurement is further from the limit than the closed form allows, which is a "
        "defect rather than the asymptotics"
    )


def test_ver21_the_zeta_potential_is_the_same_in_both_solves(
    mobilities: tuple[Mobility, ...],
) -> None:
    """The applied field does not move the mean surface potential.

    ``zeta`` is read from a solve that carries an applied field, and that is only
    legitimate because the field's perturbation is odd in ``z`` and averages out.
    The drag solve carries no field at all, so the two values agreeing is the
    evidence — and a disagreement would mean the double layer is being polarised
    and the low-zeta closed forms no longer apply.
    """
    for point in mobilities:
        assert point.zeta_drift < 1e-3, (
            f"at kappa a = {point.kappa_a:.2f} the mean surface potential differs by "
            f"{point.zeta_drift:.2e} V_T between the field and drag solves, against a zeta~ of "
            f"{point.zeta:.4f}. The applied field is polarising the double layer, so Henry's "
            "linear-response result is not the right target"
        )

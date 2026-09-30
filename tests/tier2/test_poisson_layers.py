"""VER-56, PHY-20: ``poisson`` on a three-layer capacitor, against its closed form.

``z in [0, L]`` with fluid on ``[0, a)`` and ``(b, L]`` and a membrane on
``[a, b]``, a uniform ``rho_0`` everywhere, ``phi(0) = 0`` and ``phi(L) = V``, and
natural conditions on the axis and on ``r = R``. The solution does not depend on
``r``. Gauss gives ``D(z) = D_0 + rho_0 z``, continuous across both interfaces,
and

    phi(z) = -[D_0 F1(z) + rho_0 F2(z)],   F1 = int_0^z ds/(eps_0 eps_r),
                                           F2 = int_0^z s ds/(eps_0 eps_r),

with ``D_0 = -(V + rho_0 I2)/I1`` from ``phi(L) = V`` (the WP26 plan's *Design*
section 3, [verified]). ``phi`` is piecewise quadratic in ``z``, so the P2 space
on a mesh whose element edges lie on ``z = a`` and ``z = b`` contains it exactly,
and the ``r``-weighted integrands are cubic. NGSolve's own estimate integrates them
at order 2, one short, because it does not count the ``r`` weight; ``poisson``
adds :data:`~nanopnp.physics.models.RADIAL_WEIGHT_ORDER` to both terms, so they
are integrated exactly (NUM-07 NOTE on the ``r`` weight) and the Galerkin solution
*is* the closed form up to the linear solve's round-off. Any larger error is a
scale, a sign or a permittivity defect, and each of the three moves the answer by
far more than the tolerance -- which is why this test localises an error the
whole-model comparison of VAL-06 could not.

The check values are the plan's, at ``L = 10``, ``a = 4``, ``b = 6`` nm,
``eps_f = 78.15`` (``eps_r,f^0``, Gavish 2016, ``data/corrections/
willems2020_nacl.yaml``), ``eps_s = 3.2`` (PHY-20), ``rho_0 = -1.0e7 C m^-3``,
``V = 0.05 V`` and 298.15 K.
"""

from __future__ import annotations

import pytest

from nanopnp.core.constants import VACUUM_PERMITTIVITY, thermal_voltage
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC

LENGTH_NM = 10.0
LOWER_NM = 4.0
UPPER_NM = 6.0
RADIUS_NM = 3.0
FLUID = 78.15
SOLID = 3.2
RHO_C_M3 = -1.0e7
BIAS_V = 0.05
TEMPERATURE_K = 298.15
NM = 1e-9


def _integrals(z_nm: float) -> tuple[float, float]:
    """Return ``F1(z)`` and ``F2(z)`` in SI, integrating ``1/eps`` and ``s/eps`` layer by layer."""
    first = second = 0.0
    for start, stop, relative in (
        (0.0, LOWER_NM, FLUID),
        (LOWER_NM, UPPER_NM, SOLID),
        (UPPER_NM, LENGTH_NM, FLUID),
    ):
        top = min(max(z_nm, start), stop)
        if top <= start:
            break
        permittivity = VACUUM_PERMITTIVITY * relative
        first += (top - start) * NM / permittivity
        second += ((top * NM) ** 2 - (start * NM) ** 2) / (2.0 * permittivity)
    return first, second


def displacement_at_zero() -> float:
    """Return ``D_0``, in C m^-2, from ``phi(L) = V``."""
    first, second = _integrals(LENGTH_NM)
    return -(BIAS_V + RHO_C_M3 * second) / first


def potential_V(z_nm: float) -> float:
    """Return the closed-form ``phi(z)``, in volts."""
    first, second = _integrals(z_nm)
    return -(displacement_at_zero() * first + RHO_C_M3 * second)


def test_ver56_the_closed_form_reproduces_the_plans_check_values() -> None:
    """The oracle first: the arithmetic of *Design* section 3, to its printed digits."""
    assert displacement_at_zero() == pytest.approx(0.049391, abs=5e-7)
    assert potential_V(4.0) == pytest.approx(-0.169903, abs=5e-7)
    assert potential_V(5.0) == pytest.approx(-0.324892, abs=5e-7)
    assert potential_V(6.0) == pytest.approx(-0.126940, abs=5e-7)
    assert potential_V(5.0) / thermal_voltage(TEMPERATURE_K) == pytest.approx(-12.6454, abs=5e-5)
    assert potential_V(LENGTH_NM) == pytest.approx(BIAS_V, rel=1e-12)


def _capacitor() -> object:
    """Return the three glued layers, meshed with element edges on ``z = a`` and ``z = b``."""
    import netgen.occ as occ
    import ngsolve as ngs

    layers = [
        occ.Rectangle(RADIUS_NM, LOWER_NM).Face(),
        occ.MoveTo(0.0, LOWER_NM).Rectangle(RADIUS_NM, UPPER_NM - LOWER_NM).Face(),
        occ.MoveTo(0.0, UPPER_NM).Rectangle(RADIUS_NM, LENGTH_NM - UPPER_NM).Face(),
    ]
    for layer, material in zip(layers, ("electrolyte", "membrane", "electrolyte"), strict=True):
        layer.name = material
    shape = occ.Glue(layers)
    for edge in shape.edges:
        r, z = edge.center[0], edge.center[1]
        if abs(z) < 1e-9:
            edge.name = "cis"
        elif abs(z - LENGTH_NM) < 1e-9:
            edge.name = "trans"
        elif abs(r) < 1e-9:
            edge.name = "axis"
        elif abs(r - RADIUS_NM) < 1e-9:
            edge.name = "wall"
        else:
            edge.name = "interface"
    return ngs.Mesh(occ.OCCGeometry(shape, dim=2).GenerateMesh(maxh=0.7))


def test_ver56_poisson_reproduces_the_three_layer_capacitor_to_round_off() -> None:
    """P2 contains the exact solution, so the error is the linear solve's round-off.

    Sampled along several verticals, including the axis and the outer wall, at
    points on and between the element edges; the tolerance is 1e-10 of
    ``max |phi~|``. The membrane is where a wrong ``eps_s/eps_r,f^0`` shows, and
    ``z = 5`` is its middle.
    """
    import ngsolve as ngs

    mesh = _capacitor()
    assert set(mesh.GetMaterials()) == {"electrolyte", "membrane"}
    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl")
    assert electrolyte.permittivity_0 == FLUID
    assert electrolyte.temperature_K == TEMPERATURE_K
    model = models.create(
        "poisson", electrolyte=electrolyte, solid_permittivities={"membrane": SOLID}
    )
    scales = model.scales
    thermal = scales.potential_V
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        potential_values=mesh.BoundaryCF({"cis": 0.0, "trans": BIAS_V / thermal}),
        fixed_charge=ngs.CF(RHO_C_M3 / scales.charge_density_C_m3),
    )

    points = [
        (r, LENGTH_NM * index / 200.0)
        for r in (0.0, 0.37, 1.5, 2.81, RADIUS_NM)
        for index in range(201)
    ]
    exact = [potential_V(z) / thermal for _, z in points]
    computed = [solution.state(mesh(r, z)) for r, z in points]
    scale = max(abs(value) for value in exact)
    error = max(abs(c - e) for c, e in zip(computed, exact, strict=True))
    assert solution.state(mesh(1.5, 5.0)) == pytest.approx(-12.6454, abs=5e-5)
    assert error <= 1e-10 * scale, f"max |phi~_h - phi~| = {error:.3e} against {scale:.4f}"


def test_ver56_the_capacitor_distinguishes_the_permittivity_it_was_given() -> None:
    """The benchmark measures something: the membrane at the fluid's ``eps`` misses by far more.

    Without an entry the membrane is ion-free water, ``eps_r,f^0`` (PHY-03), and the
    middle of the membrane moves by volts -- so a model that dropped
    ``solid_permittivities`` could not pass the test above by accident.
    """
    import ngsolve as ngs

    mesh = _capacitor()
    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl")
    model = models.create("poisson", electrolyte=electrolyte)
    scales = model.scales
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        potential_values=mesh.BoundaryCF({"cis": 0.0, "trans": BIAS_V / scales.potential_V}),
        fixed_charge=ngs.CF(RHO_C_M3 / scales.charge_density_C_m3),
    )
    middle = solution.state(mesh(1.0, 5.0)) * scales.potential_V
    assert abs(middle - potential_V(5.0)) > 0.1

"""VER-31: Gouy-Chapman-**Stern**, against the closed form the shell implies.

An ion-free layer of thickness ``lambda_S`` against a charged plane carries no
space charge, so ``phi`` is linear across it and ``E = sigma_s/(eps_0 eps_r)`` is
constant there. At its outer edge Gouy-Chapman applies unchanged, with the same
``sigma_s``. Hence

``phi_0 = phi_d + sigma_s lambda_S / (eps_0 eps_r)``,
``sigma_s = sqrt(8 eps R T c_0) sinh(zeta~_d/2)``  (Grahame, VER-12)

At the conditions VER-12 already uses — 0.1 M, ``zeta~_d = 2``, 298.15 K,
``eps_r = 78.15`` — and ``lambda_S = a_Na/2 = 0.25 nm`` from
``willems2020_nacl``, ``sigma_s = 0.0435342 C m^-2``, ``Delta phi_S = 15.7287 mV``
and the shell raises the wall potential from 51.3852 mV to 67.1139 mV: **30.6 %**.
That margin is the test. A shell that is silently fluid —
because nothing restricted the ion space to the electrolyte, or because the
material fell through to the fluid set — returns the Gouy-Chapman number and is
wrong by 24 %, which no tolerance forgives.

The second half is the one that keeps this honest: ``lambda_S = 0`` must
reproduce VER-12 on the same geometry, so the shell is an addition to the
validated model rather than a change of it.
"""

from __future__ import annotations

import math

import ngsolve as ngs
import numpy as np
import pytest

from nanopnp.core.constants import (
    GAS_CONSTANT,
    REFERENCE_TEMPERATURE_K,
    VACUUM_PERMITTIVITY,
    thermal_voltage,
)
from nanopnp.core.typing import GridFunction, Mesh
from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.numerics.measures import PLANAR
from nanopnp.physics.pb import (
    ELECTROLYTE_PERMITTIVITY,
    debye_length_nm,
    dimensionless_surface_charge,
    solve_pb,
)

CONCENTRATION_M = 0.1
DIFFUSE_ZETA = 2.0
"""``zeta~_d`` at the shell's outer edge: VER-12's own wall potential."""

STERN_THICKNESS_NM = 0.25
"""``a_Na / 2`` from ``willems2020_nacl``'s ``steric_diameter_nm: 0.5``.

The conventional outer-Helmholtz-plane distance: the closest a hydrated cation's
centre comes to the wall.
"""

PERMITTIVITY = VACUUM_PERMITTIVITY * ELECTROLYTE_PERMITTIVITY


def _surface_charge_C_m2(zeta: float) -> float:
    """Return Grahame's ``sigma_s`` for a diffuse-layer potential of ``zeta``."""
    return math.sqrt(
        8.0 * PERMITTIVITY * GAS_CONSTANT * REFERENCE_TEMPERATURE_K * CONCENTRATION_M * 1e3
    ) * math.sinh(0.5 * zeta)


def _solve(*, exclusion_nm: float, maxh_nm: float, sigma_C_m2: float) -> tuple[Mesh, GridFunction]:
    """Return the potential on a slab with an ion-free shell against the wall.

    The wall carries ``sigma_s`` as a Neumann datum rather than a potential: the
    whole point of the Stern layer is that it changes the wall potential a given
    surface charge produces, so prescribing the potential would assume the answer.
    """
    lam = debye_length_nm(CONCENTRATION_M)
    mesh = SlabGeometry(width_nm=20.0 * lam, height_nm=lam, exclusion_nm=exclusion_nm).generate(
        maxh_nm=maxh_nm
    )
    return mesh, solve_pb(
        mesh,
        PLANAR,
        debye_length_nm=lam,
        dirichlet="bulk",
        boundary_values=ngs.CF(0.0),
        # The mobile charge lives outside the shell and nowhere else; Poisson is
        # solved across the whole slab either way, at the fluid's own eps_r.
        ions="electrolyte" if exclusion_nm > 0.0 else None,
        surface_charge=dimensionless_surface_charge(
            sigma_C_m2, relative_permittivity=ELECTROLYTE_PERMITTIVITY
        ),
        surface_charge_boundary="wall",
        nonlinear=True,
    )


@pytest.fixture(scope="module")
def drawn_slab() -> tuple[Mesh, GridFunction]:
    """Return the solved drawn slab once for the module."""
    lam = debye_length_nm(CONCENTRATION_M)
    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    return _solve(exclusion_nm=STERN_THICKNESS_NM, maxh_nm=lam / 8.0, sigma_C_m2=sigma)


def test_ver31_the_stern_layer_raises_the_wall_potential_by_the_closed_form(
    drawn_slab: tuple[Mesh, GridFunction],
) -> None:
    """``phi_0 = phi_d + sigma_s lambda_S / (eps_0 eps_r)``, to better than 1 %.

    Every term of the closed form is computed here from constants, not read back
    from the solver: ``sigma_s`` from Grahame at ``zeta~_d = 2``, and the offset
    from Gauss's law across a charge-free layer. The solve is told only the
    surface charge and where the ions are.
    """
    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    offset_V = sigma * STERN_THICKNESS_NM * 1e-9 / PERMITTIVITY
    expected_V = DIFFUSE_ZETA * thermal_voltage() + offset_V

    lam = debye_length_nm(CONCENTRATION_M)
    mesh, solution = drawn_slab
    wall_V = float(solution(mesh(0.0, 0.5 * lam))) * thermal_voltage()
    diffuse_V = float(solution(mesh(STERN_THICKNESS_NM, 0.5 * lam))) * thermal_voltage()

    # VER-31 asks for 1 %. Measured on this mesh the agreement is 7.2e-7, and
    # it converges: 2.8e-5 at lambda/4, 7.2e-7 at lambda/8, 1.2e-9 at lambda/16
    # [tested]. The tighter assertion is what would notice a 1 % regression that
    # the specified budget would let through.
    assert wall_V == pytest.approx(expected_V, rel=1e-2)
    assert wall_V == pytest.approx(expected_V, rel=1e-5)
    assert diffuse_V == pytest.approx(DIFFUSE_ZETA * thermal_voltage(), rel=1e-4)
    # The margin the test lives on: the shell is a 30 % effect, not a correction.
    assert wall_V / diffuse_V == pytest.approx(1.30606, rel=1e-4)


def test_ver31_the_shell_potential_drop_is_linear_in_the_thickness(
    drawn_slab: tuple[Mesh, GridFunction],
) -> None:
    """``Delta phi_S = sigma_s lambda_S/(eps_0 eps_r)``: no space charge, so no curvature.

    The statement that the shell is genuinely ion-free. If the ions were merely
    *sparse* there — the failure a fluid-by-accident material produces — the
    profile across the shell would curve, and its midpoint would sit off the
    chord by more than the discretisation error.
    """
    lam = debye_length_nm(CONCENTRATION_M)
    mesh, solution = drawn_slab

    height = 0.5 * lam
    wall = float(solution(mesh(0.0, height)))
    outer = float(solution(mesh(STERN_THICKNESS_NM, height)))
    middle = float(solution(mesh(0.5 * STERN_THICKNESS_NM, height)))
    # 1e-4, not tighter: the profile is linear to the nonlinear solve's own
    # tolerance (measured 2.5e-6), and a shell holding ions would curve by
    # percent — the discriminating margin is four decades wide either way.
    assert middle == pytest.approx(0.5 * (wall + outer), rel=1e-4)


def test_ver31_a_zero_thickness_shell_reproduces_gouy_chapman() -> None:
    """``lambda_S = 0`` is VER-12 on the same geometry, to solver tolerance.

    Without this the test above would pass on a solver that had simply got the
    Grahame relation wrong by 30 %: the shell must be an addition to the
    validated model, recoverable by setting one number to zero.
    """
    lam = debye_length_nm(CONCENTRATION_M)
    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    mesh, solution = _solve(exclusion_nm=0.0, maxh_nm=lam / 8.0, sigma_C_m2=sigma)
    wall = float(solution(mesh(0.0, 0.5 * lam)))
    assert wall == pytest.approx(DIFFUSE_ZETA, rel=1e-3)


def test_ver31_a_shell_that_is_silently_fluid_fails_by_a_quarter(
    drawn_slab: tuple[Mesh, GridFunction],
) -> None:
    """The failure mode, measured: ignoring the shell loses 30 % of ``phi_0``.

    Not a hypothetical. ``exclusion`` is not in ``FLUID_MATERIALS`` and has no
    ``solid_permittivities`` entry, so it could plausibly have been given either
    treatment; this says which one the physics requires, in millivolts.
    """
    lam = debye_length_nm(CONCENTRATION_M)
    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    mesh, with_shell = drawn_slab
    stern_V = float(with_shell(mesh(0.0, 0.5 * lam))) * thermal_voltage()

    # The same geometry with the shell meshed but the ions left in it, which is
    # what "the material fell through to the fluid set" would produce.
    ignored_mesh, ignored = _solve(exclusion_nm=0.0, maxh_nm=lam / 8.0, sigma_C_m2=sigma)
    ignored_V = float(ignored(ignored_mesh(0.0, 0.5 * lam))) * thermal_voltage()

    assert (stern_V - ignored_V) / stern_V == pytest.approx(0.2344, rel=2e-2)


def test_ver59_the_slabs_shell_generated_by_stage_5_is_the_drawn_shell(
    drawn_slab: tuple[Mesh, GridFunction],
) -> None:
    """VER-31's slab with its shell from :func:`~nanopnp.geometry.region.exclusion_shell` (WP30).

    The wall is the right face of a solid body; its offset by ``lambda_S``,
    clipped to the slab, is the drawn ``[0, lambda_S] x [0, H]`` to 1e-12 nm,
    and the slab meshed with the generated width gives the drawn ``phi_0``. The
    body stands in ``x`` in ``[1, 3]``, clear of the axis clearance the
    construction gates, and taller than the slab so that its round corners fall
    outside the clip.
    """
    from shapely.geometry import MultiPoint, Point, Polygon, box

    from nanopnp.geometry.region import exclusion_shell

    lam = debye_length_nm(CONCENTRATION_M)
    wall_nm, height = 3.0, lam
    body = np.array([(1.0, -1.0), (wall_nm, -1.0), (wall_nm, height + 1.0), (1.0, height + 1.0)])
    shell = exclusion_shell(body, STERN_THICKNESS_NM, 0.05, reservoir_radius_nm=100.0)
    clipped = Polygon(shell.loop).intersection(box(wall_nm, 0.0, wall_nm + 20.0 * lam, height))
    drawn = box(wall_nm, 0.0, wall_nm + STERN_THICKNESS_NM, height)
    # The same set: no vertex off the drawn rectangle's boundary, and equal areas.
    # The resampled ring leaves collinear vertices along x = lambda_S, which the
    # rectangle does not need.
    vertices = np.asarray(clipped.exterior.coords)
    assert float(drawn.exterior.distance(MultiPoint(vertices))) == 0.0
    assert max(float(drawn.exterior.distance(Point(v))) for v in vertices) <= 1e-12
    assert abs(clipped.area - drawn.area) <= 1e-12
    width = float(vertices[:, 0].max()) - wall_nm
    assert abs(width - STERN_THICKNESS_NM) <= 1e-12

    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    drawn_mesh, drawn_solution = drawn_slab
    mesh, solution = _solve(exclusion_nm=width, maxh_nm=lam / 8.0, sigma_C_m2=sigma)
    drawn_wall = float(drawn_solution(drawn_mesh(0.0, 0.5 * lam)))
    assert float(solution(mesh(0.0, 0.5 * lam))) == pytest.approx(drawn_wall, rel=1e-10)

"""VER-31: Gouy-Chapman-Stern, against the closed form the shell implies."""

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
# zeta~_d: VER-12's own wall potential (SPECIFICATION.md VER-12).
DIFFUSE_ZETA = 2.0

# a_Na/2: steric_diameter_nm of willems2020_nacl (0.5 nm).
STERN_THICKNESS_NM = 0.25

PERMITTIVITY = VACUUM_PERMITTIVITY * ELECTROLYTE_PERMITTIVITY


def _surface_charge_C_m2(zeta: float) -> float:
    return math.sqrt(
        8.0 * PERMITTIVITY * GAS_CONSTANT * REFERENCE_TEMPERATURE_K * CONCENTRATION_M * 1e3
    ) * math.sinh(0.5 * zeta)


def _solve(*, exclusion_nm: float, maxh_nm: float, sigma_C_m2: float) -> tuple[Mesh, GridFunction]:
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
    lam = debye_length_nm(CONCENTRATION_M)
    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    return _solve(exclusion_nm=STERN_THICKNESS_NM, maxh_nm=lam / 8.0, sigma_C_m2=sigma)


def test_ver31_the_stern_layer_raises_the_wall_potential_by_the_closed_form(
    drawn_slab: tuple[Mesh, GridFunction],
) -> None:
    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    offset_V = sigma * STERN_THICKNESS_NM * 1e-9 / PERMITTIVITY
    expected_V = DIFFUSE_ZETA * thermal_voltage() + offset_V

    lam = debye_length_nm(CONCENTRATION_M)
    mesh, solution = drawn_slab
    wall_V = float(solution(mesh(0.0, 0.5 * lam))) * thermal_voltage()
    diffuse_V = float(solution(mesh(STERN_THICKNESS_NM, 0.5 * lam))) * thermal_voltage()

    # The tighter assertion would notice a 1 % regression that the specified budget lets through.
    assert wall_V == pytest.approx(expected_V, rel=1e-2)
    assert wall_V == pytest.approx(expected_V, rel=1e-5)
    assert diffuse_V == pytest.approx(DIFFUSE_ZETA * thermal_voltage(), rel=1e-4)
    # The margin the test lives on: the shell is a 30 % effect, not a correction.
    assert wall_V / diffuse_V == pytest.approx(1.30606, rel=1e-4)


def test_ver31_the_shell_potential_drop_is_linear_in_the_thickness(
    drawn_slab: tuple[Mesh, GridFunction],
) -> None:
    lam = debye_length_nm(CONCENTRATION_M)
    mesh, solution = drawn_slab

    height = 0.5 * lam
    wall = float(solution(mesh(0.0, height)))
    outer = float(solution(mesh(STERN_THICKNESS_NM, height)))
    middle = float(solution(mesh(0.5 * STERN_THICKNESS_NM, height)))
    # The profile is linear to the nonlinear solve's own tolerance; a shell holding ions would
    # curve well beyond it.
    assert middle == pytest.approx(0.5 * (wall + outer), rel=1e-4)


# VER-12
def test_ver31_a_zero_thickness_shell_reproduces_gouy_chapman() -> None:
    lam = debye_length_nm(CONCENTRATION_M)
    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    mesh, solution = _solve(exclusion_nm=0.0, maxh_nm=lam / 8.0, sigma_C_m2=sigma)
    wall = float(solution(mesh(0.0, 0.5 * lam)))
    assert wall == pytest.approx(DIFFUSE_ZETA, rel=1e-3)


def test_ver31_a_shell_that_is_silently_fluid_fails_by_a_quarter(
    drawn_slab: tuple[Mesh, GridFunction],
) -> None:
    lam = debye_length_nm(CONCENTRATION_M)
    sigma = _surface_charge_C_m2(DIFFUSE_ZETA)
    mesh, with_shell = drawn_slab
    stern_V = float(with_shell(mesh(0.0, 0.5 * lam))) * thermal_voltage()

    # The same geometry with the shell meshed but the ions left in it, which is
    # what "the material fell through to the fluid set" would produce.
    ignored_mesh, ignored = _solve(exclusion_nm=0.0, maxh_nm=lam / 8.0, sigma_C_m2=sigma)
    ignored_V = float(ignored(ignored_mesh(0.0, 0.5 * lam))) * thermal_voltage()

    assert (stern_V - ignored_V) / stern_V == pytest.approx(0.2344, rel=2e-2)


# VER-31
def test_ver59_the_slabs_shell_generated_by_stage_5_is_the_drawn_shell(
    drawn_slab: tuple[Mesh, GridFunction],
) -> None:
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

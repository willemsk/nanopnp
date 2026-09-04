"""VER-06: the wall-distance field is smooth, vanishes on the wall, and ignores the membrane."""

import numpy as np
import pytest

from nanopnp.io.case import loads_case, resolve
from nanopnp.mesh.adapter import from_ngsolve, write_msh41
from nanopnp.mesh.distance import gradient_jump, mollify, wall_distance
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry

ACCURACY_TOL_NM = 5e-3
"""Stated tolerance on d within the range where the wall corrections vary."""

JUMP_TOL = 1e-2
"""Stated C1 tolerance: the normalised facet jump of grad(d) (NUM-31)."""

WALL_ZERO_TOL_NM = 1e-9
"""Roundoff allowance on d evaluated on the wall itself.

The constrained degrees of freedom are zeroed exactly, and that is asserted
exactly below. Evaluating the field *at* a boundary point is a different thing:
the point is located inside an element, and the reference coordinate it maps to
is only zero to floating-point roundoff, so the interior shape functions
contribute a platform-dependent residue - order 1e-16 or smaller here. This
tolerance is five orders below the few times 1e-4 an unzeroed projection leaves
behind, which is the defect the test exists to catch.
"""


@pytest.fixture(scope="module")
def cylinder():
    """Return a cylinder mesh, where the exact distance is a - r."""
    return CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=0.1)


def test_ver06_distance_matches_the_exact_field_near_the_wall(cylinder) -> None:
    """The distance reproduces a - r, over the range where f^w actually varies."""
    distance = wall_distance(cylinder, "wall")
    # 0.5 nm is the innermost radius of the 1.5 nm band where f^w still varies.
    radii = np.linspace(0.5, 2.0, 61)
    errors = [abs(distance(cylinder(float(r), 2.0)) - (2.0 - r)) for r in radii]
    assert max(errors) < ACCURACY_TOL_NM


def test_ver06_distance_vanishes_on_the_wall_and_is_never_negative(cylinder) -> None:
    """PHY-02: the field vanishes on the pore boundary.

    A slightly negative d would shift the ion wall function at the wall by
    percent - f^w_D(0) = 0.0601 is itself only 6 % of its bulk value - so the
    constrained degrees of freedom are zeroed rather than left to the projection.
    """
    distance = wall_distance(cylinder, "wall")

    # The exact guarantee: every degree of freedom on the wall is zeroed.
    on_wall = distance.space.GetDofs(cylinder.Boundaries("wall"))
    coefficients = np.asarray(distance.vec.FV())
    wall_coefficients = coefficients[np.fromiter(on_wall, dtype=bool, count=len(coefficients))]
    assert wall_coefficients.size > 0
    assert np.all(wall_coefficients == 0.0)

    # And the field those degrees of freedom carry vanishes along the whole wall,
    # to the roundoff of evaluating at a point on it.
    on_the_wall = [distance(cylinder(2.0, float(z))) for z in np.linspace(0.0, 4.0, 41)]
    assert max(abs(value) for value in on_the_wall) < WALL_ZERO_TOL_NM

    sampled = [distance(cylinder(float(r), 2.0)) for r in np.linspace(0.0, 2.0, 81)]
    assert min(sampled) >= -WALL_ZERO_TOL_NM


def test_ver06_gradient_is_continuous_to_the_stated_tolerance(cylinder) -> None:
    """The mollified field has a small facet jump; a kinked d enters the Jacobian."""
    distance = wall_distance(cylinder, "wall")
    jump = gradient_jump(distance)
    assert jump < JUMP_TOL, f"normalised gradient jump {jump:.4f} exceeds {JUMP_TOL}"


def test_ver06_further_mollification_reduces_the_jump(cylinder) -> None:
    """The smoothing pass does what it claims, so it is worth having on a real mesh."""
    distance = wall_distance(cylinder, "wall", diffusion_length_nm=0.1)
    smoothed = mollify(distance, 0.2, sources="wall")
    assert gradient_jump(smoothed) < gradient_jump(distance)


def test_ver06_membrane_is_not_a_distance_source() -> None:
    """PHY-02: the bilayer is excluded from the source set, deliberately.

    Including it would be a model change, not an improvement: electrolyte
    properties near the membrane do not affect the pore's figures of merit, and
    the reference model measured from the pore boundaries only.
    """
    mesh = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=30.0
    ).generate(maxh_nm=2.0, wall_h_nm=0.15)
    distance = wall_distance(mesh, "wall")

    at_pore_wall = distance(mesh(1.9, 0.0))
    just_above_membrane = distance(mesh(10.0, 6.6))
    assert at_pore_wall == pytest.approx(0.1, abs=2e-2)
    assert just_above_membrane > 1.0, (
        "a point 0.1 nm above the membrane is far from the pore; a small distance "
        "there means the membrane leaked into the source set"
    )


def test_missing_source_boundary_fails_loudly(cylinder) -> None:
    with pytest.raises(ValueError, match="no boundary matching 'pore'"):
        wall_distance(cylinder, "pore")


INGESTED_CASE = """
schema: nanopnp/case/v1
name: ingested-distance
inputs:
  mesh: {{path: {path}, format: gmsh, groups: {{default: interface}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: none}}
"""
"""A case naming a mesh on disk, with the one group the vocabulary does not claim."""


@pytest.fixture(scope="module")
def ingested_pore(tmp_path_factory):
    """Return a pore mesh written to MSH 4.1 and read back through ingestion.

    Every other test in this file measures ``d`` on a mesh held in memory since
    netgen built it. Phase 1 solves on a mesh that came off disk, and the whole
    of PHY-02 rests on ``wall`` still meaning the pore boundary there. Round-
    tripping the geometry through :func:`~nanopnp.mesh.ingest.ingest` puts the
    file reader, the name mapping and the vocabulary gate between the geometry
    and the field.
    """
    geometry = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=30.0
    )
    built = geometry.generate(maxh_nm=2.0, wall_h_nm=0.15)
    path = write_msh41(from_ngsolve(built), tmp_path_factory.mktemp("mesh") / "pore.msh")
    resolved = resolve(loads_case(INGESTED_CASE.format(path=path)))
    return built, ingest(resolved.mesh, resolved)


def test_ver06_distance_on_an_ingested_mesh_still_vanishes_on_the_wall(ingested_pore) -> None:
    """The field vanishes on the wall and is never negative, on a mesh read from disk."""
    mesh = ingested_pore[1].mesh
    distance = wall_distance(mesh, "wall")

    on_wall = distance.space.GetDofs(mesh.Boundaries("wall"))
    coefficients = np.asarray(distance.vec.FV())
    wall_coefficients = coefficients[np.fromiter(on_wall, dtype=bool, count=len(coefficients))]
    assert wall_coefficients.size > 0
    assert np.all(wall_coefficients == 0.0)

    on_the_wall = [distance(mesh(2.0, float(z))) for z in np.linspace(-6.0, 6.0, 25)]
    assert max(abs(value) for value in on_the_wall) < WALL_ZERO_TOL_NM

    sampled = [distance(mesh(float(r), 0.0)) for r in np.linspace(0.0, 2.0, 41)]
    assert min(sampled) >= -WALL_ZERO_TOL_NM


def test_num31_the_gradient_jump_survives_the_file_round_trip(ingested_pore) -> None:
    """NUM-31's smoothness is a property of the mesh, and the round trip preserves it.

    The absolute figure here is not JUMP_TOL: that tolerance was measured on a
    cylinder at 0.1 nm resolving its wall, and this pore is a 30 nm reservoir at
    2 nm with a 0.15 nm wall, where the jump is 0.494. What the round trip has to
    guarantee is that ingesting the mesh changes nothing about the field, and
    equality to floating-point is a far sharper statement than any threshold: a
    reader that dropped a vertex, renumbered an element or lost the wall would
    not reproduce the number.
    """
    built, ingested = ingested_pore
    assert gradient_jump(wall_distance(ingested.mesh, "wall")) == pytest.approx(
        gradient_jump(wall_distance(built, "wall")), rel=1e-12
    )


def test_ver06_the_ingested_membrane_is_not_a_distance_source(ingested_pore) -> None:
    """PHY-02 on an ingested mesh: ``d`` measures from ``wall`` and not ``membrane``.

    The mesh carries a ``membrane`` group of its own, so this is the case the
    ingestion gate exists for: had the exporter's bilayer been mapped to
    ``wall``, everything below would still assemble and ``d`` would answer a
    different question. The separation asserted is geometric - a point 0.1 nm
    above the bilayer at ``r = 10`` is 8 nm from the pore wall.
    """
    mesh = ingested_pore[1].mesh
    assert "membrane" in ingested_pore[1].data.boundaries
    distance = wall_distance(mesh, "wall")
    at_pore_wall = distance(mesh(1.9, 0.0))
    just_above_membrane = distance(mesh(10.0, 6.6))
    assert at_pore_wall == pytest.approx(0.1, abs=2e-2)
    assert just_above_membrane > 1.0

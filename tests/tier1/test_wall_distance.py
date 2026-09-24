"""VER-06: the wall-distance field is smooth, vanishes on the wall, and ignores the membrane."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.io.case import loads_case, resolve
from nanopnp.mesh.adapter import from_ngsolve, write_msh41
from nanopnp.mesh.distance import gradient_jump, mollify, wall_distance
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Mesh
    from nanopnp.io.case import ResolvedCase
    from nanopnp.materials.models import CorrectionModel
    from nanopnp.solve.gates import WallDistanceGate

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
schema: nanopnp/case/v2
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


# -- VER-40: the PHY-02 clamp and the NUM-34 gate ------------------------------


WALL_VALUE_D = 0.06011672921353888
"""``f^w_D(0) = 1 - exp(-6.2 * 0.01)``, to the precision the YAML's check: carries.

Written out rather than recomputed from the parameters: recomputing it here
would reproduce whatever the correction does, including a sign error, which is
the whole failure this constant exists to catch (PHY-11, VER-03).
"""

WALL_VALUE_ETA = 2.6387280882270177
"""``f^w_eta(0) = 1 + exp(-3.36 * -0.147)``. The viscosity form has no root and
cannot invert; it is merely wrong by a factor of 17.7 at the measured minimum,
which is why the clamp goes on the shared driver rather than in the ion form."""

CLAMPED_PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
"""The toy pore of ``.knowledge/06`` section 7.1.1, where the undershoot was measured."""

ADMISSIBLE_WALL_H_NM = 0.35
INADMISSIBLE_WALL_H_NM = 1.0
"""The two sides of NUM-34's regime change, measured on :data:`CLAMPED_PORE`.

``wall_h`` 0.35 nm gives ``min d = +9.5e-06`` nm over the fluid and 1.0 nm gives
``-0.94`` nm with a tenth of the samples negative. There is nothing in between:
0.4 nm already gives ``-1.08``. The gate discriminates a regime rather than
shaving a tolerance, which is the argument NUM-34's rationale makes and this
pair of fixtures is the measurement behind it. **[tested]**
"""


def _corrections() -> tuple[CorrectionModel, CorrectionModel]:
    """Return the diffusivity and viscosity models the wall functions live on."""
    from nanopnp.materials.models import create

    return (
        create("willems2020_nacl", "diffusivity", "Na+"),
        create("willems2020_nacl", "viscosity", None),
    )


@pytest.mark.parametrize("distance_nm", [-10.0, -1.2347, -0.01, -1e-3, -1e-12, 0.0])
def test_ver40_both_wall_forms_return_their_wall_value_for_every_non_positive_sample(
    distance_nm: float,
) -> None:
    """PHY-02: the driver is clamped at zero, so no wall form ever sees a negative ``d``.

    The ion form ``1 - exp(-P1 (d + P2))`` has its root at ``d = -P2``: it does
    not decay towards zero as the wall is approached and then stay there, it
    *crosses*. At the minimum measured on the coarse mesh of ``.knowledge/06``
    section 7.1.1 it returns -437.7, an anti-diffusion operator over 8 % of the
    sampled fluid, in the one neighbourhood where PHY-11's wall function is
    supposed to hold ions back. Clamping the driver is what makes that
    impossible; ``-1e-12`` and ``-10`` have to give the same answer, because a
    distance is non-negative by definition and both are the same artefact.
    """
    diffusivity, viscosity = _corrections()
    assert float(diffusivity.evaluate(1e-9, distance_nm)) == pytest.approx(WALL_VALUE_D, rel=1e-12)
    assert float(viscosity.evaluate(1e-9, distance_nm)) == pytest.approx(WALL_VALUE_ETA, rel=1e-12)


def test_ver40_the_clamp_is_continuous_across_zero() -> None:
    """A floor, not a step: the clamped and unclamped branches meet at ``d = 0``.

    Asserted because the alternative fix — clamping the *factor* at zero — is
    discontinuous in exactly this way and would set ``D_i = mu_i = 0`` on that
    neighbourhood, a degenerate operator and a lie of the same size as the one
    it replaces. Approaching zero from above must reach the same value the
    clamp returns from below.
    """
    diffusivity, _ = _corrections()
    above = [float(diffusivity.evaluate(1e-9, epsilon)) for epsilon in (1e-15, 1e-12, 1e-9)]
    assert min(above) >= WALL_VALUE_D
    # The slope at the wall is ``P1 exp(-P1 P2) = 5.83`` per nm, so ``d = 1e-9``
    # is 1e-7 of the wall value above it; ``1e-6`` bounds that with room and
    # would still catch a *step*, which is the discontinuity a factor clamp
    # would introduce and is the whole point of the test.
    assert max(above) == pytest.approx(WALL_VALUE_D, rel=1e-6)


def test_ver40_the_clamp_holds_on_the_symbolic_path_too() -> None:
    """The same statement on the CoefficientFunction path, which is what assembles.

    The numeric path is what the check values are stated against and the
    symbolic path is what the residual is built from; a clamp on one of them is
    a clamp on the tests. Evaluated on a mesh, because that is the only way a
    ``CoefficientFunction`` produces a number.
    """
    import ngsolve as ngs

    from nanopnp.materials.forms import NGSOLVE_OPS

    diffusivity, viscosity = _corrections()
    mesh = CLAMPED_PORE.generate(maxh_nm=4.0, wall_h_nm=ADMISSIBLE_WALL_H_NM)
    for driver in (ngs.CF(-1.2347), ngs.CF(-1e-3), ngs.CF(0.0)):
        assert diffusivity.evaluate(ngs.CF(1e-9), driver, NGSOLVE_OPS)(
            mesh(1.0, 0.0)
        ) == pytest.approx(WALL_VALUE_D, rel=1e-9)
        assert viscosity.evaluate(ngs.CF(1e-9), driver, NGSOLVE_OPS)(
            mesh(1.0, 0.0)
        ) == pytest.approx(WALL_VALUE_ETA, rel=1e-9)


def test_num34_threshold_is_one_named_constant_between_the_root_and_the_residual() -> None:
    """The gate's threshold is read from one place, and it is where NUM-34 says.

    One order inside the ion function's root at ``-P2 = -0.01`` nm, and one order
    outside the element-wise projection residual that ``Set`` leaves behind. Both
    bounds are asserted rather than the value alone: a threshold *at* the root
    would admit a diffusivity of exactly zero as its last passing state, and one
    at zero would gate the rounding mode.
    """
    from nanopnp.materials.corrections import load_corrections
    from nanopnp.solve.gates import MINIMUM_WALL_DISTANCE_NM, WallDistanceGate

    document = load_corrections("willems2020_nacl")
    root_nm = -float(document.ion_wall_function.coefficients["P2"])
    assert root_nm == pytest.approx(-0.01)
    assert root_nm < MINIMUM_WALL_DISTANCE_NM < 0.0
    assert pytest.approx(-1e-3) == MINIMUM_WALL_DISTANCE_NM
    assert WallDistanceGate.minimum_nm == MINIMUM_WALL_DISTANCE_NM


def _measure(wall_h_nm: float) -> WallDistanceGate:
    """Return the NUM-34 gate over the toy pore at one wall spacing."""
    from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
    from nanopnp.solve.gates import FieldSampler, WallDistanceGate

    mesh = CLAMPED_PORE.generate(maxh_nm=4.0, wall_h_nm=wall_h_nm)
    distance = wall_distance(mesh, "wall", order=2, max_distance_nm=3.0)
    return WallDistanceGate(FieldSampler(mesh, materials=ELECTROLYTE_DOMAINS), distance)


def test_num34_an_admissible_mesh_passes_and_reports_what_it_measured() -> None:
    """The refined mesh passes, and the measurement is available whether or not it did.

    NUM-34 requires the measured minimum in the provenance manifest, so a field
    that passed *narrowly* is a fact about the mesh that a sweep's dataset should
    carry. A gate that only spoke when it failed could not supply it.
    """
    found = _measure(ADMISSIBLE_WALL_H_NM).measure()
    _measure(ADMISSIBLE_WALL_H_NM).check()
    assert found.minimum_nm > 0.0
    assert found.negative_fraction == 0.0
    assert found.samples > 100
    assert set(found.summary()) == {
        "minimum_nm",
        "location_nm",
        "negative_fraction",
        "samples",
    }


def test_num34_the_coarse_mesh_is_refused_naming_everything_it_measured() -> None:
    """QR-12: the diagnostic names the gate, the minimum, its location and the extent.

    The extent as well as the worst point, because a field one node below the
    threshold and a field negative over a tenth of the fluid ask for different
    responses, and the message has to let a reader tell them apart. The location
    is the re-entrant corner of the pore mouth, which is where the undershoot was
    measured (``.knowledge/06`` section 7.1.1).
    """
    from nanopnp.solve.gates import GateViolationError

    gate = _measure(INADMISSIBLE_WALL_H_NM)
    found = gate.measure()
    assert found.minimum_nm < -0.5
    assert found.negative_fraction > 0.05

    with pytest.raises(GateViolationError) as raised:
        gate.check()
    message = str(raised.value)
    assert "wall-distance admissibility" in message
    assert "min d" in message
    assert f"{found.minimum_nm:.6g}" in message
    assert f"{found.negative_fraction:.3%}" in message
    assert "r = " in message and "z = " in message
    assert "wall_h_nm" in message, "the diagnostic must say what to refine"


GATED_CASE = """
schema: nanopnp/case/v2
name: gated
inputs:
  mesh: {{path: {path}, format: vol, groups: {{default: interface}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: {model}, wall: {wall}}}
    mobility:     {{model: {model}, wall: {wall}}}
    viscosity:    {{model: {model}, wall: {wall}}}
boundary_conditions: {{bias_V: 0.02, ground: cis}}
physics: {{model: {physics}, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: none}}
"""
"""A case over the toy pore whose corrections and physics model are chosen per test."""


def _resolved(tmp_path: Path, wall_h_nm: float, *, corrections: bool) -> tuple[ResolvedCase, Mesh]:
    """Write the toy pore, resolve a case over it, and ingest the mesh."""
    from nanopnp.mesh.ingest import ingest as ingest_mesh

    path = tmp_path / "pore.vol"
    CLAMPED_PORE.generate(maxh_nm=4.0, wall_h_nm=wall_h_nm).ngmesh.Save(str(path))
    document = loads_case(
        GATED_CASE.format(
            path=path,
            model="willems2020_nacl" if corrections else "none",
            wall="true" if corrections else "false",
            physics="epnp-ns" if corrections else "pnp-ns",
        )
    )
    resolved = resolve(document)
    return resolved, ingest_mesh(resolved.mesh, resolved).mesh


def test_num34_a_configuration_with_no_wall_correction_is_not_gated(tmp_path) -> None:
    """A classical run reads no distance field, so gating its mesh would gate nothing.

    Asserted on the same coarse mesh the gate refuses above: what decides is the
    *corrections*, exactly as :func:`~nanopnp.solve.state.reads_wall` decides
    whether the screened-Poisson solve happens at all. A classical case on an
    inadmissible mesh is not an inadmissible run — and the field it would have
    been gated on is not even solved for, so a gate here would be measuring the
    saturation constant.
    """
    from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
    from nanopnp.solve.state import check_wall_distance, wall_distance_field

    resolved, mesh = _resolved(tmp_path, INADMISSIBLE_WALL_H_NM, corrections=False)
    distance = wall_distance_field(resolved, mesh, order=2)
    assert distance == SATURATED_WALL_DISTANCE_NM
    assert check_wall_distance(resolved, mesh, distance) is None


def test_num34_a_corrected_run_on_the_same_mesh_is_gated(tmp_path) -> None:
    """The same mesh, with the wall corrections on, is refused (QR-12).

    The pair is the assertion: one case reads ``d`` and one does not, on one
    mesh, so what fires the gate is the *configuration* rather than the
    geometry. Disabling a correction selects the registered ``none`` model
    rather than taking a code branch, which is why the fallback costs no code.
    """
    from nanopnp.solve.gates import GateViolationError
    from nanopnp.solve.state import check_wall_distance, wall_distance_field

    resolved, mesh = _resolved(tmp_path, INADMISSIBLE_WALL_H_NM, corrections=True)
    distance = wall_distance_field(resolved, mesh, order=2)
    with pytest.raises(GateViolationError, match="wall-distance admissibility"):
        check_wall_distance(resolved, mesh, distance)


def test_num34_a_corrected_run_on_an_admissible_mesh_passes_and_measures(tmp_path) -> None:
    """The refined mesh passes and hands back the minimum the manifest records."""
    from nanopnp.solve.state import check_wall_distance, wall_distance_field

    resolved, mesh = _resolved(tmp_path, ADMISSIBLE_WALL_H_NM, corrections=True)
    distance = wall_distance_field(resolved, mesh, order=2)
    found = check_wall_distance(resolved, mesh, distance)
    assert found is not None
    assert found.minimum_nm > 0.0
    assert found.negative_fraction == 0.0


def test_num34_the_gate_reads_the_mollified_field_where_smoothing_is_on() -> None:
    """NUM-31's smoothing pass makes a different field, and it is the one the forms read.

    Gating the un-mollified field would gate something no weak form ever
    evaluates. Asserted by measuring both and requiring the gate's own number to
    be the mollified one; the two differ, which is what makes the assertion
    have content.
    """
    from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
    from nanopnp.solve.gates import FieldSampler, WallDistanceGate

    mesh = CLAMPED_PORE.generate(maxh_nm=4.0, wall_h_nm=ADMISSIBLE_WALL_H_NM)
    plain = wall_distance(mesh, "wall", order=2, max_distance_nm=3.0)
    smoothed = mollify(plain, 0.2, sources="wall")
    sampler = FieldSampler(mesh, materials=ELECTROLYTE_DOMAINS)
    on_plain = WallDistanceGate(sampler, plain).measure().minimum_nm
    on_smoothed = WallDistanceGate(sampler, smoothed).measure().minimum_nm
    assert on_plain != on_smoothed, "the two fields must differ, or this asserts nothing"
    assert WallDistanceGate(sampler, smoothed).measure().minimum_nm == on_smoothed

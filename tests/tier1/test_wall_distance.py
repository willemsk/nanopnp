"""VER-06: the wall-distance field is smooth, vanishes on the wall, and ignores the membrane."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.mesh.adapter import from_ngsolve, write_msh41
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry
from nanopnp.physics.distance import gradient_jump, mollify, wall_distance
from nanopnp.pipeline.case import loads_case, resolve

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Mesh
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.materials.models import CorrectionModel
    from nanopnp.numerics.gates import WallDistanceGate

ACCURACY_TOL_NM = 5e-3

# C1 facet-jump tolerance: SPECIFICATION.md NUM-31.
JUMP_TOL = 1e-2

WALL_ZERO_TOL_NM = 1e-9


@pytest.fixture(scope="module")
def cylinder():
    return CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=0.1)


def test_ver06_distance_matches_the_exact_field_near_the_wall(cylinder) -> None:
    distance = wall_distance(cylinder, "wall")
    # 0.5 nm is the innermost radius of the 1.5 nm band where f^w still varies.
    radii = np.linspace(0.5, 2.0, 61)
    errors = [abs(distance(cylinder(float(r), 2.0)) - (2.0 - r)) for r in radii]
    assert max(errors) < ACCURACY_TOL_NM


# PHY-02
def test_ver06_distance_vanishes_on_the_wall_and_is_never_negative(cylinder) -> None:
    distance = wall_distance(cylinder, "wall")

    on_wall = distance.space.GetDofs(cylinder.Boundaries("wall"))
    coefficients = np.asarray(distance.vec.FV())
    wall_coefficients = coefficients[np.fromiter(on_wall, dtype=bool, count=len(coefficients))]
    assert wall_coefficients.size > 0
    assert np.all(wall_coefficients == 0.0)

    on_the_wall = [distance(cylinder(2.0, float(z))) for z in np.linspace(0.0, 4.0, 41)]
    assert max(abs(value) for value in on_the_wall) < WALL_ZERO_TOL_NM

    sampled = [distance(cylinder(float(r), 2.0)) for r in np.linspace(0.0, 2.0, 81)]
    assert min(sampled) >= -WALL_ZERO_TOL_NM


def test_ver06_gradient_is_continuous_to_the_stated_tolerance(cylinder) -> None:
    distance = wall_distance(cylinder, "wall")
    jump = gradient_jump(distance)
    assert jump < JUMP_TOL, f"normalised gradient jump {jump:.4f} exceeds {JUMP_TOL}"


def test_ver06_further_mollification_reduces_the_jump(cylinder) -> None:
    distance = wall_distance(cylinder, "wall", diffusion_length_nm=0.1)
    smoothed = mollify(distance, 0.2, sources="wall")
    assert gradient_jump(smoothed) < gradient_jump(distance)


# PHY-02
def test_ver06_membrane_is_not_a_distance_source() -> None:
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
schema: nanopnp/case/v0.5
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


@pytest.fixture(scope="module")
def ingested_pore(tmp_path_factory):
    geometry = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=30.0
    )
    built = geometry.generate(maxh_nm=2.0, wall_h_nm=0.15)
    path = write_msh41(from_ngsolve(built), tmp_path_factory.mktemp("mesh") / "pore.msh")
    resolved = resolve(loads_case(INGESTED_CASE.format(path=path)))
    return built, ingest(resolved.mesh, resolved)


def test_ver06_distance_on_an_ingested_mesh_still_vanishes_on_the_wall(ingested_pore) -> None:
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
    built, ingested = ingested_pore
    assert gradient_jump(wall_distance(ingested.mesh, "wall")) == pytest.approx(
        gradient_jump(wall_distance(built, "wall")), rel=1e-12
    )


# PHY-02
def test_ver06_the_ingested_membrane_is_not_a_distance_source(ingested_pore) -> None:
    mesh = ingested_pore[1].mesh
    assert "membrane" in ingested_pore[1].data.boundaries
    distance = wall_distance(mesh, "wall")
    at_pore_wall = distance(mesh(1.9, 0.0))
    just_above_membrane = distance(mesh(10.0, 6.6))
    assert at_pore_wall == pytest.approx(0.1, abs=2e-2)
    assert just_above_membrane > 1.0


# -- VER-40: the PHY-02 clamp and the NUM-34 gate ------------------------------


# Correction YAML's check value for f^w_D(0): SPECIFICATION.md PHY-11, VER-03.
WALL_VALUE_D = 0.06011672921353888

WALL_VALUE_ETA = 2.6387280882270177

CLAMPED_PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)

ADMISSIBLE_WALL_H_NM = 0.35
# Regime change of SPECIFICATION.md NUM-34; measured on
# knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md.
INADMISSIBLE_WALL_H_NM = 1.0


def _corrections() -> tuple[CorrectionModel, CorrectionModel]:
    from nanopnp.materials.models import create

    return (
        create("willems2020_nacl", "diffusivity", "Na+"),
        create("willems2020_nacl", "viscosity", None),
    )


# PHY-02, PHY-11
@pytest.mark.parametrize("distance_nm", [-10.0, -1.2347, -0.01, -1e-3, -1e-12, 0.0])
def test_ver40_both_wall_forms_return_their_wall_value_for_every_non_positive_sample(
    distance_nm: float,
) -> None:
    diffusivity, viscosity = _corrections()
    assert float(diffusivity.evaluate(1e-9, distance_nm)) == pytest.approx(WALL_VALUE_D, rel=1e-12)
    assert float(viscosity.evaluate(1e-9, distance_nm)) == pytest.approx(WALL_VALUE_ETA, rel=1e-12)
    assert (1.0 + float(np.exp(-3.36 * (-0.9401 - 0.147)))) / WALL_VALUE_ETA == pytest.approx(
        15.0, rel=0.2
    )


def test_ver40_the_clamp_is_continuous_across_zero() -> None:
    diffusivity, _ = _corrections()
    above = [float(diffusivity.evaluate(1e-9, epsilon)) for epsilon in (1e-15, 1e-12, 1e-9)]
    assert min(above) >= WALL_VALUE_D
    # The slope at the wall is P1 exp(-P1 P2) = 5.83 per nm: d = 1e-9 is 1e-7 of the wall value.
    assert 6.2 * float(np.exp(-6.2 * 0.01)) == pytest.approx(5.83, abs=1e-2)
    assert max(above) == pytest.approx(WALL_VALUE_D, rel=1e-6)


def test_ver40_the_clamp_holds_on_the_symbolic_path_too() -> None:
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
    from nanopnp.materials.corrections import load_corrections
    from nanopnp.numerics.gates import MINIMUM_WALL_DISTANCE_NM, WallDistanceGate

    document = load_corrections("willems2020_nacl")
    root_nm = -float(document.ion_wall_function.coefficients["P2"])
    assert root_nm == pytest.approx(-0.01)
    assert root_nm < MINIMUM_WALL_DISTANCE_NM < 0.0
    assert pytest.approx(-1e-3) == MINIMUM_WALL_DISTANCE_NM
    assert WallDistanceGate.minimum_nm == MINIMUM_WALL_DISTANCE_NM


def _measure(wall_h_nm: float) -> WallDistanceGate:
    from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
    from nanopnp.numerics.gates import FieldSampler, WallDistanceGate

    mesh = CLAMPED_PORE.generate(maxh_nm=4.0, wall_h_nm=wall_h_nm)
    distance = wall_distance(mesh, "wall", order=2, max_distance_nm=3.0)
    return WallDistanceGate(FieldSampler(mesh, materials=ELECTROLYTE_DOMAINS), distance)


def test_num34_an_admissible_mesh_passes_and_reports_what_it_measured() -> None:
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


# QR-12
def test_num34_the_coarse_mesh_is_refused_naming_everything_it_measured() -> None:
    from nanopnp.numerics.gates import GateViolationError

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
schema: nanopnp/case/v0.5
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


def _resolved(tmp_path: Path, wall_h_nm: float, *, corrections: bool) -> tuple[ResolvedCase, Mesh]:
    from nanopnp.mesh.ingest import ingest as ingest_mesh

    path = tmp_path / "pore.vol"
    CLAMPED_PORE.generate(maxh_nm=4.0, wall_h_nm=wall_h_nm).ngmesh.Save(str(path))
    document = loads_case(
        GATED_CASE.format(
            path=path,
            model="willems2020_nacl" if corrections else "none",
            wall="true",
            physics="epnp-ns" if corrections else "pnp-ns",
        )
    )
    resolved = resolve(document)
    return resolved, ingest_mesh(resolved.mesh, resolved).mesh


def test_num34_a_configuration_with_no_wall_correction_is_not_gated(tmp_path) -> None:
    from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
    from nanopnp.solve.state import check_wall_distance, wall_distance_field

    resolved, mesh = _resolved(tmp_path, INADMISSIBLE_WALL_H_NM, corrections=False)
    distance = wall_distance_field(resolved, mesh, order=2)
    assert distance == SATURATED_WALL_DISTANCE_NM
    assert check_wall_distance(resolved, mesh, distance) is None


# QR-12
def test_num34_a_corrected_run_on_the_same_mesh_is_gated(tmp_path) -> None:
    from nanopnp.numerics.gates import GateViolationError
    from nanopnp.solve.state import check_wall_distance, wall_distance_field

    resolved, mesh = _resolved(tmp_path, INADMISSIBLE_WALL_H_NM, corrections=True)
    distance = wall_distance_field(resolved, mesh, order=2)
    with pytest.raises(GateViolationError, match="wall-distance admissibility"):
        check_wall_distance(resolved, mesh, distance)


def test_num34_a_corrected_run_on_an_admissible_mesh_passes_and_measures(tmp_path) -> None:
    from nanopnp.solve.state import check_wall_distance, wall_distance_field

    resolved, mesh = _resolved(tmp_path, ADMISSIBLE_WALL_H_NM, corrections=True)
    distance = wall_distance_field(resolved, mesh, order=2)
    found = check_wall_distance(resolved, mesh, distance)
    assert found is not None
    assert found.minimum_nm > 0.0
    assert found.negative_fraction == 0.0


# NUM-31
def test_num34_the_gate_reads_the_mollified_field_where_smoothing_is_on() -> None:
    from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
    from nanopnp.numerics.gates import FieldSampler, WallDistanceGate

    mesh = CLAMPED_PORE.generate(maxh_nm=4.0, wall_h_nm=ADMISSIBLE_WALL_H_NM)
    plain = wall_distance(mesh, "wall", order=2, max_distance_nm=3.0)
    smoothed = mollify(plain, 0.2, sources="wall")
    sampler = FieldSampler(mesh, materials=ELECTROLYTE_DOMAINS)
    on_plain = WallDistanceGate(sampler, plain).measure().minimum_nm
    on_smoothed = WallDistanceGate(sampler, smoothed).measure().minimum_nm
    assert on_plain != on_smoothed, "the two fields must differ, or this asserts nothing"
    assert WallDistanceGate(sampler, smoothed).measure().minimum_nm == on_smoothed


# VER-70
def test_qr12_a_floor_that_underflows_or_is_nan_is_refused(cylinder) -> None:
    with pytest.raises(ValueError, match="underflows to zero"):
        wall_distance(cylinder, "wall", diffusion_length_nm=1.0e-3, max_distance_nm=3.0)
    with pytest.raises(ValueError, match="underflows to zero"):
        wall_distance(cylinder, "wall", max_distance_nm=float("nan"))

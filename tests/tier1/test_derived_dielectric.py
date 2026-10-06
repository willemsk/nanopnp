"""VER-59, the dielectric: the ``chi`` stage 7 derives from the stage-4 profile (FR-15, VER-30).

On the parallelogram body of ``tests/conftest.py``, which is convex, so that the
transition along the normal at the midpoint of each water-facing edge is planar
and the lattice's bilinear error is bounded by ``0.75 (h/delta)^2 = 1.9e-3``
(WP30 plan, *Design* section 1). The assertion's 4e-3 is twice that. Near the
vertices the bound does not hold, and the error there is recorded on 2WCD at
Tier 2 instead.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator

from nanopnp.charge.dielectric import (
    EXCLUSION_MEAN_CEILING,
    DerivedSolidFraction,
    MaterialMean,
    derive_solid_fraction,
    smooth_step,
    water_facing,
)
from nanopnp.charge.fields import ChargeFieldError
from nanopnp.charge.stage import check_water_facing, derive_fields
from nanopnp.density.grid import RadialGrid
from nanopnp.geometry.region import RegionRecord, RegionStage, read_region
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import CaseValidationError
from nanopnp.io.resolved import ResolvedCase
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, deployed_mesh
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.pipeline.case import loads_case, resolve

DELTA_NM = 0.15
"""``delta``: the middle of PHY-20's 1-2 Angstrom (WP30 D15)."""

TOLERANCE = 4e-3
"""Twice the bilinear bound at ``h = delta/20`` (*Design* section 1)."""

CASE = """\
schema: nanopnp/case/v2
name: chi
inputs:
  profile: {{path: {path}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: {scale}}}}}
charge: {{{charge}}}
"""


def case_text(profile: Path, charge: str, *, scale: float = 5.0) -> str:
    """Return the coarse profile case with the ``charge:`` keys given."""
    return CASE.format(path=profile, charge=charge, scale=scale)


def _membrane(record: RegionRecord) -> dict[str, float]:
    """Return the membrane keywords the derivation takes."""
    return {
        "half_thickness_nm": record.membrane.half_thickness_nm,
        "inner_trans_nm": record.membrane.inner_trans_nm,
        "inner_cis_nm": record.membrane.inner_cis_nm,
    }


def _walk(
    profile: Path, charge: str, directory: Path, *, scale: float = 5.0
) -> tuple[ResolvedCase, RegionRecord, IngestedMesh]:
    """Return the resolved case, its record and its deployed mesh."""
    case = loads_case(case_text(profile, charge, scale=scale))
    region = RegionStage(workspace=directory / "region").run(StageInputs(resolved=resolve(case)))
    mesh = MeshStage(workspace=directory / "mesh").run(
        StageInputs(resolved=resolve(case), upstream={"region": region})
    )
    resolved = resolve(case)
    return resolved, read_region(Path(region.payload["region"])), deployed_mesh(resolved, mesh)


@pytest.fixture(scope="module")
def derived(parallelogram_profile: Path, tmp_path_factory: pytest.TempPathFactory):
    """Return the case at ``delta`` = 0.15 nm: resolved, record, mesh, field and means."""
    resolved, record, ingested = _walk(
        parallelogram_profile,
        f"dielectric_transition_nm: {DELTA_NM}",
        tmp_path_factory.mktemp("chi"),
    )
    field, means = derive_fields(resolved, record, ingested.mesh, measures=AXISYMMETRIC)
    return resolved, record, ingested, field, means


def _interpolant(grid: RadialGrid) -> RegularGridInterpolator:
    """Return the lattice's bilinear interpolant, zero past its box as ``coefficient`` is."""
    return RegularGridInterpolator(
        (grid.z_nm, grid.r_nm), grid.values, bounds_error=False, fill_value=0.0
    )


# -- the profile of the step -------------------------------------------------------


def test_ver59_chi_along_each_water_facing_normal_is_the_cubic_step(derived) -> None:
    """``chi_h = S(s/delta + 1/2)`` to 4e-3 for ``|s| <= delta``: 1/2 on ``W``, width ``delta``."""
    _, record, _, field, _ = derived
    water, _ = water_facing(record.points(), **_membrane(record))
    assert len(water) == 7  # the four edges, split at the planes, less the one under the membrane
    interpolant = _interpolant(field.grid)
    s = np.linspace(-DELTA_NM, DELTA_NM, 61)
    worst = 0.0
    for start, end in water:
        midpoint = 0.5 * (start + end)
        span = end - start
        outward = np.array([span[1], -span[0]]) / np.hypot(*span)
        points = midpoint[None, :] - s[:, None] * outward[None, :]
        found = interpolant(points[:, ::-1])
        worst = max(worst, float(np.abs(found - smooth_step(s / DELTA_NM + 0.5)).max()))
        assert interpolant(midpoint[::-1])[0] == pytest.approx(0.5, abs=TOLERANCE)
    assert worst <= TOLERANCE, worst


def test_ver59_chi_is_one_in_the_membrane_and_the_protein_and_zero_on_the_box_edge(
    derived,
) -> None:
    """D3 and D4: the membrane and the deep body at 1, the lattice's boundary at 0."""
    _, _, _, field, means = derived
    values = field.grid.values
    for edge in (values[0], values[-1], values[:, -1]):
        assert float(np.abs(edge).max()) == 0.0
    # The box's r = 0 side is not clipped on this body, so it is a boundary too.
    assert field.grid.r_nm[0] > 0.0
    assert float(np.abs(values[:, 0]).max()) == 0.0
    by_material = {mean.material: mean.mean for mean in means}
    assert by_material["membrane"] == pytest.approx(1.0, abs=1e-12)
    # The body's middle, 0.5 nm from its slanted sides and far from its ends.
    interpolant = _interpolant(field.grid)
    assert interpolant([[0.0, 4.0]])[0] == pytest.approx(1.0, abs=1e-15)
    # Inside the body and at least 0.18 nm from its slanted sides, which are
    # r = 3.5 + z/2 and 4.5 + z/2: more than delta/2 from W, so exactly 1.
    r, z = np.meshgrid(field.grid.r_nm, field.grid.z_nm)
    deep = (np.abs(z) < 2.5) & (np.abs(r - (4.0 + z / 2.0)) < 0.3)
    assert float(values[deep].min()) == 1.0
    assert by_material["electrolyte"] == pytest.approx(0.0, abs=1e-3)


def test_ver59_w_is_the_regions_protein_to_water_boundary(derived) -> None:
    """D2's probe agrees with ``name_region``'s adjacency, and a frame slip is refused."""
    _, record, _, _, _ = derived
    water, membrane_facing = water_facing(record.points(), **_membrane(record))
    check_water_facing(record, water)
    shifted = water + np.array([0.0, 0.05])
    with pytest.raises(ChargeFieldError, match="midpoint"):
        check_water_facing(record, shifted)
    with pytest.raises(ChargeFieldError, match="nm long"):
        check_water_facing(record, np.concatenate([water, membrane_facing]))


# -- the gates -----------------------------------------------------------------------


def test_ver59_the_range_and_registration_gates_pass_and_an_inverted_chi_fails(
    derived,
) -> None:
    """VER-30's gates on a derived ``chi``: they pass, and its inverse fails registration."""
    resolved, _, ingested, field, means = derived
    assert all(mean.within for mean in means)
    by_material = {mean.material: mean.mean for mean in means}
    assert by_material["protein"] >= 0.9
    inverted = DerivedSolidFraction(
        grid=RadialGrid(
            origin_nm=field.grid.origin_nm,
            spacing_nm=field.grid.spacing_nm,
            values=1.0 - field.grid.values,
        ),
        transition_nm=field.transition_nm,
        held=(),
        mesh=ingested.mesh,
    )
    inverted.check_range()
    with pytest.raises(ChargeFieldError, match="'protein' averages chi"):
        inverted.check_materials(
            ingested.mesh, AXISYMMETRIC, solids=resolved.document.physics.solid_permittivities
        )


def test_ver59_the_shell_registers_below_one_half_on_a_thin_shell(
    parallelogram_profile: Path, tmp_path: Path
) -> None:
    """A 0.12 nm shell at ``delta`` = 0.2 nm averages ``3 delta/(32 a)``-ish, below 1/2 (D6)."""
    resolved, record, ingested = _walk(
        parallelogram_profile,
        "exclusion_offset_nm: 0.12, dielectric_transition_nm: 0.2",
        tmp_path,
        scale=2.0,
    )
    _, means = derive_fields(resolved, record, ingested.mesh, measures=AXISYMMETRIC)
    shell = next(mean for mean in means if mean.material == "exclusion")
    # The planar estimate is 0.156; the body's convex corners spread the step
    # over more shell, and its foot on the membrane less.
    assert 0.1 < shell.mean < EXCLUSION_MEAN_CEILING, shell.mean
    assert shell.within
    assert not MaterialMean(material="exclusion", mean=0.5, branch="fluid").within
    assert MaterialMean(material="exclusion", mean=0.49, branch="fluid").within
    assert not MaterialMean(material="electrolyte", mean=0.11, branch="fluid").within


def test_ver59_a_consumer_reads_stage_7s_chi_with_the_means_it_recorded(
    parallelogram_profile: Path, tmp_path: Path
) -> None:
    """D5: the solve's ``chi`` is stage 7's, and so are the means its record carries.

    Without them the solve's FR-25 record of the derived ``chi`` would list no
    material at all, as if nothing had been measured.
    """
    from nanopnp.charge.stage import FieldStage, case_fields

    case = loads_case(case_text(parallelogram_profile, f"dielectric_transition_nm: {DELTA_NM}"))
    region = RegionStage(workspace=tmp_path / "region").run(StageInputs(resolved=resolve(case)))
    mesh = MeshStage(workspace=tmp_path / "mesh").run(
        StageInputs(resolved=resolve(case), upstream={"region": region})
    )
    fields = FieldStage(workspace=tmp_path / "fields").run(
        StageInputs(resolved=resolve(case), upstream={"region": region, "mesh": mesh})
    )
    resolved = resolve(case)
    consumed = case_fields(resolved, None, fields, deployed_mesh(resolved, mesh).mesh)
    assert isinstance(consumed.eps_r, DerivedSolidFraction)
    assert consumed.eps_r.grid.digest() == fields.summary["eps_r"]["grid_digest"]  # type: ignore[index]
    recorded = fields.summary["eps_r"]["material_means"]  # type: ignore[index]
    assert recorded
    assert [mean.summary() for mean in consumed.material_means] == recorded
    assert consumed.summary()["eps_r"] == fields.summary["eps_r"]


def test_ver59_the_blend_takes_the_derived_chi_inside_the_protein_and_in_the_fluid(
    derived,
) -> None:
    """``eps = chi eps_p + (1 - chi) eps_w`` at one point in the body and one in the fluid."""
    from nanopnp.physics.models import relative_permittivity_field

    _, _, ingested, field, _ = derived
    mesh = ingested.mesh
    eps0 = 78.0
    eps = relative_permittivity_field(
        mesh,
        model_name="test",
        fluid="electrolyte",
        fluid_permittivity=1.0,
        permittivity_0=eps0,
        scale_permittivity=eps0,
        solid_permittivities={"protein": 20.0, "membrane": 3.2},
        solid_fraction=field.chi(),
    )
    # Deep in the body: chi = 1, the protein's own.
    assert eps(mesh(4.0, 0.0)) == pytest.approx(20.0 / eps0, rel=1e-12)
    # A quarter of delta outside the top edge z = 3, at r = 5.5: chi = S(1/4).
    chi = float(smooth_step(np.array(0.25)))
    expected = chi * 20.0 / eps0 + (1.0 - chi) * 1.0
    assert eps(mesh(5.5, 3.0 + 0.25 * DELTA_NM)) == pytest.approx(expected, abs=TOLERANCE)


# -- the case refusals -----------------------------------------------------------------


def test_ver59_a_transition_below_h_c_is_refused_naming_both_keys(
    parallelogram_profile: Path,
) -> None:
    """``0 < delta < h_c`` is finer than the grid the contour is placed on (D11)."""
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(case_text(parallelogram_profile, "dielectric_transition_nm: 0.04")))
    message = str(raised.value)
    assert "charge.dielectric_transition_nm" in message
    assert "geometry.density.grid_spacing_nm" in message


def test_ver59_a_transition_beside_inputs_eps_r_is_refused_naming_both(
    parallelogram_profile: Path,
) -> None:
    """One quantity supplied twice (D12)."""
    text = case_text(parallelogram_profile, f"dielectric_transition_nm: {DELTA_NM}").replace(
        "inputs:\n", "inputs:\n  eps_r: {path: chi.yaml, format: field1}\n", 1
    )
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    message = str(raised.value)
    assert "charge.dielectric_transition_nm" in message
    assert "inputs.eps_r" in message


def test_ver59_a_model_declaring_no_solid_fraction_refuses_the_transition(
    parallelogram_profile: Path,
) -> None:
    """Read from the declaration, as ``inputs.eps_r`` is refused (section 5.4.3)."""
    text = case_text(parallelogram_profile, f"dielectric_transition_nm: {DELTA_NM}").replace(
        "model: pnp-ns, solid_permittivities: {protein: 20.0, membrane: 3.2}",
        "model: pb, flow: false, variable_density: false, inertia: false",
    )
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    message = str(raised.value)
    assert "physics.model 'pb'" in message
    assert "charge.dielectric_transition_nm" in message


def test_ver59_the_lattice_spacing_and_box_follow_delta(derived) -> None:
    """D4: spacing ``delta/20``, box widened by ``delta`` about the body."""
    _, record, _, field, _ = derived
    assert field.grid.spacing_nm == pytest.approx((DELTA_NM / 20.0, DELTA_NM / 20.0))
    points = record.points()
    (r_low, r_high), (z_low, z_high) = field.grid.extent_nm
    assert r_low == pytest.approx(points[:, 0].min() - DELTA_NM, abs=1e-12)
    assert z_low == pytest.approx(points[:, 1].min() - DELTA_NM, abs=1e-12)
    assert r_high >= points[:, 0].max() + DELTA_NM - 1e-9
    assert z_high >= points[:, 1].max() + DELTA_NM - 1e-9
    again = derive_solid_fraction(points, transition_nm=DELTA_NM, **_membrane(record))
    assert again.digest() == field.grid.digest()

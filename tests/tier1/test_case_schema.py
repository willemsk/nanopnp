"""IF-03, FR-26 and VER-09: the case schema, its diagnostics and its round trip."""

import re
from pathlib import Path

import pytest

from nanopnp.io.artefact import CaseArtefact
from nanopnp.io.case import (
    CaseValidationError,
    UnsupportedCaseSection,
    dump_case,
)
from nanopnp.pipeline.case import (
    load_case,
    loads_case,
    resolve,
)

REFERENCE_CASE = """
schema: nanopnp/case/v0.5
name: clya-wt-1M-100mV

inputs:
  mesh: {path: clya.msh, format: msh41,
         groups: {pore: pore, membrane: membrane, reservoir: bulk}}

electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  temperature_K: 298.15
  parameters: willems2020_nacl
  driver: average
  corrections:
    diffusivity:  {model: willems2020_nacl, wall: true, concentration: true}
    mobility:     {model: willems2020_nacl, wall: true, concentration: true}
    viscosity:    {model: willems2020_nacl, wall: true, concentration: true}
    permittivity: {model: willems2020_nacl}
    density:      {model: willems2020_nacl}
    steric:       {model: borukhov, a_ion_nm: 0.50, a_water_nm: 0.311}

boundary_conditions:
  bias_V: 0.100
  ground: cis
  walls: {ion_flux: no_flux, slip: no_slip}

physics:
  model: epnp-ns
  flow: true
  variable_density: true
  inertia: true
  dielectric_gradient_forces: false

numerics:
  elements: {phi: P2, c: P2, u: P2, p: P1}
  mesh: {backend: netgen, wall_h_nm: auto, boundary_layer: false}
  nonlinear: {strategy: newton, damping: residual, max_iter: 100, rtol: 1e-6}
  continuation: default_ladder
  stabilisation: none
  wall_distance: {sources: wall, max_distance_nm: 3.0}
  linear: {solver: umfpack}

outputs: [current, transport_numbers, rectification, eof_rate, analyte_force, fields]
"""
"""The section 5.3.1 example, less the sections v0.3 and v0.4 own."""


@pytest.fixture
def case_file(tmp_path: Path) -> Path:
    path = tmp_path / "clya.yaml"
    path.write_text(REFERENCE_CASE, encoding="utf-8")
    return path


# FR-26
def test_ver09_round_trip_preserves_the_case_hash_and_the_resolved_run(
    case_file: Path, tmp_path: Path
) -> None:
    first = load_case(case_file)
    written = dump_case(first, tmp_path / "written.yaml")
    second = load_case(written)

    assert CaseArtefact(first).hash == CaseArtefact(second).hash
    assert resolve(first).provenance == resolve(second).provenance
    assert written.read_text(encoding="utf-8") != case_file.read_text(encoding="utf-8")


REFORMATTED_CASE = """
# The same run, written by a different hand: keys reordered, flow style where the
# reference uses block, `1` for `1.0`, quoted scalars, and a comment on every line
# that carries a decision. None of it changes the run.
name: clya-wt-1M-100mV
schema: 'nanopnp/case/v0.5'

outputs:
  - current
  - transport_numbers
  - rectification
  - eof_rate
  - analyte_force
  - fields

numerics:
  linear: {solver: umfpack}
  wall_distance: {max_distance_nm: 3, sources: 'wall'}   # PHY-02
  stabilisation: none
  continuation: default_ladder
  nonlinear:
    rtol: 0.000001
    max_iter: 100
    damping: residual
    strategy: newton
  mesh: {boundary_layer: false, wall_h_nm: auto, backend: netgen}
  elements: {p: P1, u: P2, c: P2, phi: P2}

physics: {dielectric_gradient_forces: false, inertia: true,
          variable_density: true, flow: true, model: 'epnp-ns'}

boundary_conditions:
  walls: {slip: no_slip, ion_flux: no_flux}
  ground: cis
  bias_V: 0.1

electrolyte:
  corrections:
    steric:       {a_water_nm: 0.311, a_ion_nm: 0.5, model: borukhov}
    density:      {model: willems2020_nacl}
    permittivity: {model: willems2020_nacl}
    viscosity:    {concentration: true, wall: true, model: willems2020_nacl}
    mobility:     {concentration: true, wall: true, model: willems2020_nacl}
    diffusivity:  {concentration: true, wall: true, model: willems2020_nacl}
  driver: average
  parameters: willems2020_nacl
  temperature_K: 298.15
  concentration_M: 1
  species:
    - {z: 1, name: 'Na+'}
    - {z: -1, name: 'Cl-'}

inputs:
  mesh:
    groups: {reservoir: bulk, membrane: membrane, pore: pore}
    format: msh41
    path: clya.msh
"""
"""The reference case as a different hand would write it. Same run, different text."""


def test_ver09_round_trip_survives_reformatting_that_does_not_change_the_run() -> None:
    reference = loads_case(REFERENCE_CASE)
    other = loads_case(REFORMATTED_CASE)

    assert REFORMATTED_CASE != REFERENCE_CASE
    assert CaseArtefact(reference).hash == CaseArtefact(other).hash
    assert resolve(reference).provenance == resolve(other).provenance


def test_ver09_a_change_that_changes_the_run_changes_the_hash() -> None:
    reference = CaseArtefact(loads_case(REFERENCE_CASE)).hash
    for edit, replacement in (
        ("bias_V: 0.100", "bias_V: 0.200"),
        ("concentration_M: 1.0", "concentration_M: 0.15"),
        ("model: epnp-ns", "model: pnp-ns"),
        (
            "viscosity:    {model: willems2020_nacl, wall: true",
            "viscosity:    {model: none, wall: true",
        ),
        ("sources: wall", "sources: wall|membrane"),
    ):
        assert edit in REFERENCE_CASE
        altered = loads_case(REFERENCE_CASE.replace(edit, replacement))
        assert CaseArtefact(altered).hash != reference, edit


# PHY-21
def test_if03_a_misspelt_correction_model_is_refused_rather_than_silently_disabled() -> None:
    text = REFERENCE_CASE.replace(
        "viscosity:    {model: willems2020_nacl", "viscosity:    {model: willems2020_kcl"
    )
    with pytest.raises(CaseValidationError, match="willems2020_kcl"):
        loads_case(text)


def test_ver24_a_pqr_beside_a_model_without_a_fixed_charge_is_refused_naming_it() -> None:
    text = REFERENCE_CASE.replace(
        "inputs:\n", "inputs:\n  pqr: {path: x.pqr, format: pqr}\n", 1
    ).replace(
        "model: epnp-ns\n  flow: true\n  variable_density: true\n  inertia: true",
        "model: pb\n  flow: false\n  variable_density: false\n  inertia: false",
    )
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    message = str(raised.value)
    assert "'pb'" in message
    assert "inputs.pqr" in message
    assert "poisson" in message


@pytest.mark.parametrize(
    ("walls", "named"),
    [
        ("{ion_flux: no_flux, slip: free}", "slip: free"),
        ("{ion_flux: no_flux, slip: navier}", "slip: navier"),
        ("{ion_flux: prescribed, slip: no_slip}", "ion_flux: prescribed"),
    ],
)
def test_fr25_a_wall_condition_the_forms_do_not_pose_is_refused_not_recorded(
    walls: str, named: str
) -> None:
    text = REFERENCE_CASE.replace("walls: {ion_flux: no_flux, slip: no_slip}", f"walls: {walls}")
    with pytest.raises(UnsupportedCaseSection, match=named):
        resolve(loads_case(text))


# FR-16
def test_phy16_case_steric_diameters_are_checked_against_the_parameter_file() -> None:
    text = REFERENCE_CASE.replace("a_ion_nm: 0.50", "a_ion_nm: 0.66")
    with pytest.raises(CaseValidationError, match="a_ion_nm"):
        resolve(loads_case(text))


def test_fr16_a_case_temperature_the_parameter_file_is_not_fitted_at_is_refused() -> None:
    text = REFERENCE_CASE.replace("temperature_K: 298.15", "temperature_K: 310.0")
    with pytest.raises(CaseValidationError, match=r"temperature_K is 310\.0 K.*298\.15 K"):
        resolve(loads_case(text))


def test_phy21_resolution_builds_the_named_model_s_configuration() -> None:
    resolved = resolve(loads_case(REFERENCE_CASE))
    assert resolved.model == "epnp-ns"
    assert resolved.electrolyte.parameter_file == "willems2020_nacl"
    assert resolved.electrolyte.switches.steric is True
    assert resolved.model_options["order"] == 2
    assert resolved.model_options["pressure_order"] == 1
    assert resolved.newton.max_iterations == 100
    assert resolved.newton.relative_tolerance == pytest.approx(1e-6)
    assert resolved.stabilisation == "none"
    assert resolved.wall_distance_sources == "wall"


def test_phy21_a_classical_case_resolves_to_every_correction_off() -> None:
    text = REFERENCE_CASE.replace("model: willems2020_nacl", "model: none").replace(
        "steric:       {model: borukhov", "steric:       {model: none"
    )
    assert "parameters: willems2020_nacl" in text
    resolved = resolve(loads_case(text))
    switches = resolved.electrolyte.switches
    assert switches.steric is False
    assert {choice.model for choice in (switches.diffusivity, switches.mobility)} == {"none"}
    assert resolved.electrolyte.viscosity_0 > 0.0


# NUM-18
def test_phy24_an_electrostatic_model_has_no_transport_to_continue() -> None:
    corrections_block = (
        "  corrections:\n"
        "    diffusivity:  {model: willems2020_nacl, wall: true, concentration: true}\n"
        "    mobility:     {model: willems2020_nacl, wall: true, concentration: true}\n"
        "    viscosity:    {model: willems2020_nacl, wall: true, concentration: true}\n"
        "    permittivity: {model: willems2020_nacl}\n"
        "    density:      {model: willems2020_nacl}\n"
        "    steric:       {model: borukhov, a_ion_nm: 0.50, a_water_nm: 0.311}\n"
    )
    text = (
        REFERENCE_CASE.replace("model: epnp-ns", "model: pb")
        .replace(corrections_block, "")
        .replace("flow: true", "flow: false")
        .replace("variable_density: true", "variable_density: false")
        .replace("inertia: true", "inertia: false")
    )
    with pytest.raises(CaseValidationError, match="continuation") as raised:
        resolve(loads_case(text))
    assert "'pb'" in str(raised.value) and "none" in str(raised.value)


# NUM-18
@pytest.mark.parametrize(
    ("switch", "given"),
    [
        ("flow", "false"),
        ("variable_density", "false"),
        ("inertia", "false"),
        ("dielectric_gradient_forces", "true"),
    ],
)
def test_fr25_a_switch_the_ladder_cannot_honour_is_refused_not_dropped(
    switch: str, given: str
) -> None:
    was = f"{switch}: " + ("true" if given == "false" else "false")
    text = REFERENCE_CASE.replace(was, f"{switch}: {given}")
    assert f"{switch}: {given}" in text
    with pytest.raises(CaseValidationError, match=re.escape(f"physics.{switch}")) as raised:
        resolve(loads_case(text))
    assert "numerics.continuation: none" in str(raised.value)


def test_fr25_the_same_switch_on_a_single_rung_resolves_and_is_carried() -> None:
    text = REFERENCE_CASE.replace("inertia: true", "inertia: false").replace(
        "continuation: default_ladder", "continuation: none"
    )
    resolved = resolve(loads_case(text))
    assert resolved.model_options["inertia"] is False


def test_phy21_pnp_with_flow_is_refused_by_the_model_check_not_the_ladder_check() -> None:
    text = REFERENCE_CASE.replace("model: epnp-ns", "model: pnp")
    with pytest.raises(CaseValidationError, match=re.escape("physics.flow must be false")):
        resolve(loads_case(text))


def test_num03_the_reference_element_set_resolves_to_three_independent_orders() -> None:
    text = REFERENCE_CASE.replace(
        "elements: {phi: P2, c: P2, u: P2, p: P1}", "elements: {phi: P2, c: P2, u: P1, p: P1}"
    ).replace("stabilisation: none", "stabilisation: reference")
    resolved = resolve(loads_case(text))

    assert resolved.model_options["order"] == 2
    assert resolved.model_options["velocity_order"] == 1
    assert resolved.model_options["pressure_order"] == 1
    assert resolved.stabilisation == "reference"


def test_num03_an_equal_order_pair_is_refused_in_a_mode_that_supplies_no_flow_term() -> None:
    text = REFERENCE_CASE.replace(
        "elements: {phi: P2, c: P2, u: P2, p: P1}", "elements: {phi: P2, c: P2, u: P1, p: P1}"
    )
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    message = str(raised.value)
    assert "inf-sup" in message
    assert "numerics.elements.u" in message
    assert "reference" in message


def test_num03_phi_and_c_must_still_agree_and_the_message_names_both() -> None:
    text = REFERENCE_CASE.replace(
        "elements: {phi: P2, c: P2, u: P2, p: P1}", "elements: {phi: P2, c: P1, u: P2, p: P1}"
    )
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    message = str(raised.value)
    assert "numerics.elements.c" in message
    assert "numerics.elements.phi" in message


INF_SUP_UNSTABLE = REFERENCE_CASE.replace(
    "elements: {phi: P2, c: P2, u: P2, p: P1}", "elements: {phi: P2, c: P2, u: P1, p: P1}"
)


def test_num03_an_unstable_pair_is_refused_at_load_naming_inf_sup() -> None:
    with pytest.raises(CaseValidationError, match="inf-sup"):
        loads_case(INF_SUP_UNSTABLE)
    accepted = loads_case(
        INF_SUP_UNSTABLE.replace("stabilisation: none", "stabilisation: reference")
    )
    assert accepted.numerics.elements.u == "P1"


def test_phy21_the_resolved_declaration_and_boundaries_are_the_registry_s() -> None:
    from nanopnp.mesh.primitives import DEFAULT_BOUNDARIES
    from nanopnp.physics.models import case_model, declaration

    resolved = resolve(loads_case(REFERENCE_CASE))
    assert resolved.declaration == declaration("epnp-ns")
    model = case_model(resolved)
    assert dict(resolved.essential_boundaries) == dict(
        model.essential_boundaries(DEFAULT_BOUNDARIES)
    )
    assert list(resolved.essential_boundaries) == list(
        model.essential_boundaries(DEFAULT_BOUNDARIES)
    )

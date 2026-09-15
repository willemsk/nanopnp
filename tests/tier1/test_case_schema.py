"""IF-03, FR-26 and VER-09: the case schema, its diagnostics and its round trip.

FR-26 asks that a case file write, read and resolve to a semantically identical
run. The assertion is on the content hash of the *validated* document and on
`ResolvedCase.provenance`, never on the YAML text: comments, key order, quoting
and `1` against `1.0` all vanish in validation, and none of them changes the run
(SPECIFICATION.md section 5.3.1 NOTE). Both halves are asserted, because they are
weaker in opposite directions -- two documents could share a provenance dict and
differ in a field nothing records, and the hash alone says nothing about whether
the document resolves at all.
"""

import re
from pathlib import Path

import pytest

from nanopnp.io.artefact import CaseArtefact
from nanopnp.io.case import (
    SCHEMA,
    CaseValidationError,
    UnsupportedCaseSection,
    dump_case,
    load_case,
    loads_case,
    resolve,
)

REFERENCE_CASE = """
schema: nanopnp/case/v1
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
"""The section 5.3.1 example, less the sections v0.9 owns."""


@pytest.fixture
def case_file(tmp_path: Path) -> Path:
    """Write the reference case to a file and return its path."""
    path = tmp_path / "clya.yaml"
    path.write_text(REFERENCE_CASE, encoding="utf-8")
    return path


def test_ver09_round_trip_preserves_the_case_hash_and_the_resolved_run(
    case_file: Path, tmp_path: Path
) -> None:
    """FR-26: write, read and resolve give back the same run."""
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
schema: 'nanopnp/case/v1'

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
    """Comments, key order, quoting and ``1`` against ``1.0`` are not differences.

    Asserted against a second hand-written spelling rather than against a
    programmatic edit of the first: a test that reformats by string substitution
    can only exercise the substitutions somebody thought of.
    """
    reference = loads_case(REFERENCE_CASE)
    other = loads_case(REFORMATTED_CASE)

    assert REFORMATTED_CASE != REFERENCE_CASE
    assert CaseArtefact(reference).hash == CaseArtefact(other).hash
    assert resolve(reference).provenance == resolve(other).provenance


def test_ver09_a_change_that_changes_the_run_changes_the_hash() -> None:
    """The negative half: the hash is not merely stable, it is discriminating."""
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


def test_if03_an_unknown_key_is_named_with_its_dotted_path_and_a_suggestion() -> None:
    """IF-03: pydantic carries the key in ``loc`` and not in the message, so we render it."""
    text = REFERENCE_CASE.replace("diffusivity:  {model", "diffusivty:  {model")
    with pytest.raises(CaseValidationError) as raised:
        loads_case(text)
    message = str(raised.value)
    assert "electrolyte.corrections.diffusivty" in message
    assert "unknown key" in message
    assert "did you mean 'diffusivity'?" in message


def test_if03_an_unknown_key_with_no_near_match_lists_the_block_s_keys() -> None:
    """A key nothing resembles still names what the block accepts."""
    text = REFERENCE_CASE.replace("  continuation: default_ladder", "  zzz_unrelated: 1")
    with pytest.raises(CaseValidationError, match=r"numerics\.zzz_unrelated") as raised:
        loads_case(text)
    assert "stabilisation" in str(raised.value)


def test_if03_a_future_schema_fails_naming_the_schema_before_any_field_error() -> None:
    """A file written to a later schema must not fail against a shape it never claimed."""
    text = REFERENCE_CASE.replace(SCHEMA, "nanopnp/case/v2").replace("bias_V: 0.100", "bias: 0.100")
    with pytest.raises(CaseValidationError) as raised:
        loads_case(text)
    message = str(raised.value)
    assert "nanopnp/case/v2" in message
    assert "bias" not in message


def test_if03_a_misspelt_correction_model_is_refused_rather_than_silently_disabled() -> None:
    """A typo that resolved to no correction would be exactly PHY-21's failure mode."""
    text = REFERENCE_CASE.replace(
        "viscosity:    {model: willems2020_nacl", "viscosity:    {model: willems2020_kcl"
    )
    with pytest.raises(CaseValidationError, match="willems2020_kcl"):
        loads_case(text)


def test_if03_an_output_that_is_not_selectable_is_refused() -> None:
    """An output nothing computes would be silently absent from the result."""
    with pytest.raises(CaseValidationError, match="conductance"):
        loads_case(REFERENCE_CASE.replace("outputs: [current", "outputs: [conductance, current"))


def test_if03_a_supplied_artefact_names_exactly_one_source() -> None:
    """``path`` and ``artefact`` are alternatives, and neither is not a source."""
    with pytest.raises(CaseValidationError, match="exactly one"):
        loads_case(REFERENCE_CASE.replace("{path: clya.msh, format: msh41,", "{format: msh41,"))


@pytest.mark.parametrize(
    ("section", "release"),
    [
        ("structure:\n  source: {pdb: 2WCD.pdb}\n  symmetry: {point_group: C12}\n", "v0.9"),
        ("geometry:\n  membrane: {thickness_nm: 2.8}\n", "v0.9"),
        ("charge:\n  ph: 7.5\n", "v0.9"),
    ],
)
def test_fr27_a_section_a_later_release_owns_names_the_section_and_the_release(
    section: str, release: str
) -> None:
    """A Phase-2 case must say which release runs it, not fail inside the solver."""
    with pytest.raises(UnsupportedCaseSection) as raised:
        resolve(loads_case(REFERENCE_CASE + section))
    message = str(raised.value)
    assert section.split(":")[0] in message
    assert release in message


def test_fr27_a_case_without_a_supplied_mesh_says_where_the_mesh_comes_from() -> None:
    """Phase 1 runs on a hand-substituted stage-6 artefact; there is no other mesh."""
    text = REFERENCE_CASE.replace(
        "inputs:\n  mesh: {path: clya.msh, format: msh41,\n"
        "         groups: {pore: pore, membrane: membrane, reservoir: bulk}}\n",
        "",
    )
    with pytest.raises(UnsupportedCaseSection, match=r"inputs\.mesh"):
        resolve(loads_case(text))


def test_fr27_the_num20_fallbacks_are_refused_by_name() -> None:
    """Accepting a strategy the solver does not run would put a false statement in the manifest."""
    text = REFERENCE_CASE.replace("strategy: newton", "strategy: hybrid")
    with pytest.raises(UnsupportedCaseSection, match="NUM-20"):
        resolve(loads_case(text))


def test_phy16_case_steric_diameters_are_checked_against_the_parameter_file() -> None:
    """FR-16: the diameters are fitted parameters, and the case file cannot override them."""
    text = REFERENCE_CASE.replace("a_ion_nm: 0.50", "a_ion_nm: 0.66")
    with pytest.raises(CaseValidationError, match="a_ion_nm"):
        resolve(loads_case(text))


def test_phy21_resolution_builds_the_named_model_s_configuration() -> None:
    """The resolved case carries what the solver is actually given."""
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
    """Classical PNP-NS is a configuration, not a branch: the switches carry it."""
    text = REFERENCE_CASE.replace("model: willems2020_nacl", "model: none").replace(
        "steric:       {model: borukhov", "steric:       {model: none"
    )
    assert "parameters: willems2020_nacl" in text  # the reference properties still resolve
    resolved = resolve(loads_case(text))
    switches = resolved.electrolyte.switches
    assert switches.steric is False
    assert {choice.model for choice in (switches.diffusivity, switches.mobility)} == {"none"}
    # The reference properties still come from the parameter file: a classical run
    # needs D_i^0, eta^0, rho^0 and eps_r,f^0 exactly as the corrected one does.
    assert resolved.electrolyte.viscosity_0 > 0.0


def test_phy24_an_electrostatic_model_has_no_transport_to_continue() -> None:
    """The NUM-18 ladder drives the coupled family; PB is a single solve (PHY-24)."""
    text = REFERENCE_CASE.replace("model: epnp-ns", "model: pb")
    with pytest.raises(CaseValidationError, match="continuation"):
        resolve(loads_case(text))


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
    """NUM-18 fixes the path, so a switch it never reads must not reach the manifest.

    ``default_ladder`` builds its own rungs and reads none of these four from the
    case. Left unchecked the solve would converge and the FR-25 Deviations group
    would record the switch as applied, which is the one thing section 5.3.3
    exists to make impossible: a manifest that cannot reconstruct the run.
    """
    was = f"{switch}: " + ("true" if given == "false" else "false")
    text = REFERENCE_CASE.replace(was, f"{switch}: {given}")
    assert f"{switch}: {given}" in text  # the substitution actually landed
    with pytest.raises(CaseValidationError, match=re.escape(f"physics.{switch}")) as raised:
        resolve(loads_case(text))
    assert "numerics.continuation: none" in str(raised.value)


def test_fr25_the_same_switch_on_a_single_rung_resolves_and_is_carried() -> None:
    """The refusal above is the ladder's, not the switch's: one rung honours it.

    Asserted on the resolved model options rather than on the absence of an
    exception, so that a future change making ``continuation: none`` drop the
    switch too fails here rather than passing as "no error raised".
    """
    text = REFERENCE_CASE.replace("inertia: true", "inertia: false").replace(
        "continuation: default_ladder", "continuation: none"
    )
    resolved = resolve(loads_case(text))
    assert resolved.model_options["inertia"] is False


def test_fr25_pnp_on_the_ladder_is_refused_with_advice_it_can_take() -> None:
    """'pnp' cannot match the ladder, so it must not be told to (PHY-21).

    Every rung from stage 6 carries the flow coupling, and ``physics.flow: false``
    is mandatory for 'pnp', so the generic "set them to match the ladder" advice
    is impossible by construction; the message has to name 'pnp-ns' instead.
    """
    text = REFERENCE_CASE.replace("model: epnp-ns", "model: pnp").replace(
        "flow: true", "flow: false"
    )
    with pytest.raises(CaseValidationError, match="pnp-ns") as raised:
        resolve(loads_case(text))
    message = str(raised.value)
    assert "match the ladder" not in message
    assert "numerics.continuation: none" in message


def test_phy21_pnp_with_flow_is_refused_by_the_model_check_not_the_ladder_check() -> None:
    """The precise diagnostic must win: an inconsistent case is not a ladder problem.

    'pnp' with ``flow: true`` violates PHY-21 whatever the continuation setting
    is, so ordering the two checks the other way round would answer a question
    the user did not ask.
    """
    text = REFERENCE_CASE.replace("model: epnp-ns", "model: pnp")
    with pytest.raises(CaseValidationError, match=re.escape("physics.flow must be false")):
        resolve(loads_case(text))


def test_num03_the_reference_element_set_resolves_to_three_independent_orders() -> None:
    """``{phi: P2, c: P2, u: P1, p: P1}`` is the reference mode's own pair (section 6.4).

    Not the Taylor-Hood pair of NUM-03 and not one order throughout: ``u`` is a
    third order, and the equal-order velocity-pressure pair is legal only because
    the flow stabilisation supplies the inf-sup stability it lacks.
    """
    text = REFERENCE_CASE.replace(
        "elements: {phi: P2, c: P2, u: P2, p: P1}", "elements: {phi: P2, c: P2, u: P1, p: P1}"
    ).replace("stabilisation: none", "stabilisation: reference")
    resolved = resolve(loads_case(text))

    assert resolved.model_options["order"] == 2
    assert resolved.model_options["velocity_order"] == 1
    assert resolved.model_options["pressure_order"] == 1
    assert resolved.stabilisation == "reference"


def test_num03_an_equal_order_pair_is_refused_in_a_mode_that_supplies_no_flow_term() -> None:
    """The same element set without the stabilisation names inf-sup and the remedy.

    Refused by :func:`resolve` rather than at solve time for the reason
    :meth:`CaseDocument._check_registries` gives for the registry checks: the
    continuation ladder is built before the first model is, so a case that cannot
    run must not survive resolution. The condition needs the resolved orders and
    the ``physics.flow`` switch together, which is why it sits there rather than
    in the document's own validators.
    """
    text = REFERENCE_CASE.replace(
        "elements: {phi: P2, c: P2, u: P2, p: P1}", "elements: {phi: P2, c: P2, u: P1, p: P1}"
    )
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    message = str(raised.value)
    assert "inf-sup" in message
    assert "numerics.elements.u" in message
    # Naming the mode that *would* permit it is the difference between a refusal
    # and a dead end.
    assert "reference" in message


def test_num03_phi_and_c_must_still_agree_and_the_message_names_both() -> None:
    """Splitting ``u`` out did not loosen the one equality the model does assume."""
    text = REFERENCE_CASE.replace(
        "elements: {phi: P2, c: P2, u: P2, p: P1}", "elements: {phi: P2, c: P1, u: P2, p: P1}"
    )
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    message = str(raised.value)
    assert "numerics.elements.c" in message
    assert "numerics.elements.phi" in message


@pytest.mark.parametrize("mode", ["none", "supg", "reference"])
def test_if03_every_registered_stabilisation_mode_validates(mode: str) -> None:
    """The schema literal and the registry agree, in both directions.

    Parametrised over the registry rather than over a list, so a mode added to
    ``physics.stabilisation`` and forgotten in the schema fails here instead of
    being refused by a case file that names it.
    """
    from nanopnp.physics.models import registered_stabilisations

    assert mode in registered_stabilisations()
    text = REFERENCE_CASE.replace("stabilisation: none", f"stabilisation: {mode}")
    assert resolve(loads_case(text)).stabilisation == mode


def test_if03_an_unregistered_stabilisation_mode_is_refused_naming_the_registry() -> None:
    """``streamline`` is what somebody would write for ``supg``; it is not a mode."""
    text = REFERENCE_CASE.replace("stabilisation: none", "stabilisation: streamline")
    with pytest.raises(CaseValidationError) as raised:
        loads_case(text)
    message = str(raised.value)
    assert "numerics.stabilisation" in message
    for mode in ("none", "supg", "reference"):
        assert mode in message


def test_ver09_the_widened_stabilisation_literal_left_the_schema_identifier_alone() -> None:
    """A new admissible value of an existing field is not a schema revision.

    ``supg`` and ``reference`` widen what ``numerics.stabilisation`` accepts; every
    v1 file remains a valid v1 file, so the identifier does not move (IF-03).
    """
    assert SCHEMA == "nanopnp/case/v1"
    assert loads_case(REFERENCE_CASE).schema_id == SCHEMA

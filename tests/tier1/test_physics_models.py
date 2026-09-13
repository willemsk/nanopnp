"""The physics-model registry (PHY-21, PHY-22, PHY-23, FR-20, NUM-01, NUM-03).

The claim this file defends is that ``pnp-ns`` is a *configuration* of
``epnp-ns`` and not a second code path. If a future change makes it a branch,
the class identity test below is what notices.
"""

from collections.abc import Iterator
from dataclasses import fields as dataclass_fields
from dataclasses import replace

import pytest

from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.physics import models
from nanopnp.physics.models import POTENTIAL, PRESSURE, VELOCITY, CoupledModel

SPECIFIED_MODELS = ("epnp-ns", "pnp-ns", "pnp", "pb", "pb-linear", "poisson")
"""The table of PHY-21, verbatim."""


def test_phy21_every_specified_model_is_registered() -> None:
    """The six models of PHY-21 are selectable by name."""
    assert set(SPECIFIED_MODELS) <= set(models.registered_models())


def test_create_rejects_an_unknown_model_and_lists_the_known_ones() -> None:
    """A typo in a case file names the alternatives rather than failing obscurely."""
    with pytest.raises(KeyError) as raised:
        models.create("epnpns")
    message = str(raised.value)
    assert "epnpns" in message
    for name in SPECIFIED_MODELS:
        assert name in message


def test_phy21_pnp_ns_is_epnp_ns_with_every_correction_off() -> None:
    """PNP-NS is the same class, configured; no separate code path is permitted.

    PHY-21 states the reduction exactly: ``beta_i = 0`` and every ``f^c`` and
    ``f^w`` equal to 1. Here that is the registered ``none`` model in each slot
    and ``steric`` off, and the *class* is the same object as ``epnp-ns``'s.
    """
    extended = models.create("epnp-ns")
    classical = models.create("pnp-ns")
    assert type(classical) is type(extended) is CoupledModel

    assert classical.steric is False
    assert all(model.name == "none" for model in classical.electrolyte.corrections.values()), (
        "PNP-NS must select the 'none' correction model, not branch around the correction"
    )

    assert extended.steric is True
    assert any(model.name != "none" for model in extended.electrolyte.corrections.values())
    assert [field.name for field in classical.fields] == [field.name for field in extended.fields]


def test_phy21_pnp_is_the_coupled_model_without_the_flow_block() -> None:
    """``pnp`` drops ``u`` and ``p`` and nothing else."""
    with_flow = models.create("epnp-ns")
    without = models.create("pnp")
    assert type(without) is CoupledModel
    assert without.flow is False
    names = [field.name for field in without.fields]
    assert VELOCITY not in names and PRESSURE not in names
    assert names == [field.name for field in with_flow.fields][: len(names)]


def test_num01_field_set_matches_the_specified_discretisation() -> None:
    """P2 for phi and c_i, P2 vector for u, P1 for p; phi on all of Omega."""
    model = models.create("epnp-ns")
    declared = {field.name: field for field in model.fields}
    assert declared[POTENTIAL].element == "h1"
    assert declared[POTENTIAL].order == 2
    assert declared[POTENTIAL].domain is None, "Poisson is solved over all of Omega (PHY-03)"
    for species in model.species:
        concentration = declared[f"c_{species}"]
        assert concentration.order == 2
        assert concentration.domain == ELECTROLYTE_DOMAINS
    assert declared[VELOCITY].element == "vector_h1"
    assert declared[VELOCITY].order == 2
    assert declared[PRESSURE].order == 1
    assert declared[VELOCITY].domain == declared[PRESSURE].domain == ELECTROLYTE_DOMAINS


def test_num03_equal_order_velocity_pressure_is_rejected_without_a_flow_stabilisation() -> None:
    """P1/P1 is refused in every mode that supplies no PSPG content (NUM-03).

    The refusal names both the reason and the mode that would lift it, because
    "not inf-sup stable" on its own leaves a user with a working configuration they
    cannot find. ``supg`` is refused as firmly as ``none``: it assembles the
    transport streamline term and no flow term at all.
    """
    electrolyte = Electrolyte.from_parameter_file()
    for mode in ("none", "supg"):
        with pytest.raises(ValueError, match="inf-sup") as raised:
            CoupledModel(electrolyte=electrolyte, order=2, pressure_order=2, stabilisation=mode)
        assert "reference" in str(raised.value), "the refusal must name the permitting mode"
        assert repr(mode) in str(raised.value)


def test_num03_equal_order_velocity_pressure_is_accepted_in_the_reference_mode() -> None:
    """``reference`` assembles the GLS pair, so P1/P1 is legal in it (NUM-03, NUM-14)."""
    electrolyte = Electrolyte.from_parameter_file()
    model = CoupledModel(
        electrolyte=electrolyte,
        order=2,
        velocity_order=1,
        pressure_order=1,
        stabilisation="reference",
    )
    declared = {field.name: field for field in model.fields}
    assert declared[POTENTIAL].order == 2
    assert declared[VELOCITY].order == 1
    assert declared[PRESSURE].order == 1
    # And the gate is on the *pair*, not on the mode: an equal-order pair is still
    # refused in ``none`` even when the velocity order is set explicitly.
    with pytest.raises(ValueError, match="inf-sup"):
        CoupledModel(electrolyte=electrolyte, order=2, velocity_order=1, pressure_order=1)


def test_num03_velocity_order_defaults_to_the_shared_element_order() -> None:
    """``velocity_order=None`` reproduces the two-order model exactly.

    Every case written before the third order existed leaves it unset, so the
    default has to be byte-identical in the field set *and* in the provenance —
    which is what makes widening the case schema a non-event for existing runs.
    """
    electrolyte = Electrolyte.from_parameter_file()
    implicit = CoupledModel(electrolyte=electrolyte, order=3, pressure_order=2)
    explicit = CoupledModel(electrolyte=electrolyte, order=3, velocity_order=3, pressure_order=2)
    assert implicit.resolved_velocity_order == 3
    assert implicit.provenance["fields"] == explicit.provenance["fields"]
    assert implicit.provenance["elements"] == explicit.provenance["elements"]


def test_num06_axis_carries_only_the_radial_velocity_condition() -> None:
    """``u_r = 0`` is essential on the axis; ``phi``, ``c_i`` and ``u_z`` are natural."""
    model = models.create("epnp-ns")
    vocabulary = model.boundary_conditions
    assert vocabulary[POTENTIAL]["axis"] == "natural"
    for species in model.species:
        assert vocabulary[f"c_{species}"]["axis"] == "natural"
    assert "u_r = 0" in vocabulary[VELOCITY]["axis"]
    assert "natural" in vocabulary[VELOCITY]["axis"]


def test_phy23_dielectric_gradient_forces_is_one_switch_and_defaults_off() -> None:
    """The two terms are enabled together or not at all (PHY-08, PHY-23).

    The guarantee is structural: the model offers exactly one switch, so there
    is no way to ask for the momentum term without the Nernst-Planck one. A
    future ``dielectric_gradient_momentum`` flag would fail here.
    """
    model = models.create("epnp-ns")
    assert model.dielectric_gradient_forces is False, "PHY-22 default is off"
    switches = [
        field.name for field in dataclass_fields(CoupledModel) if "dielectric" in field.name
    ]
    assert switches == ["dielectric_gradient_forces"]


def test_phy23_dielectric_gradient_forces_cannot_use_the_log_branch() -> None:
    """The permittivity sensitivity would be differentiated in the wrong variable."""
    electrolyte = Electrolyte.from_parameter_file()
    with pytest.raises(ValueError, match="log branch"):
        CoupledModel(electrolyte=electrolyte, dielectric_gradient_forces=True, log_variables=True)


def test_fr25_provenance_records_every_deviation_from_the_validated_default() -> None:
    """A run that turns a switch away from the reference says so in its manifest."""
    electrolyte = Electrolyte.from_parameter_file()
    default = CoupledModel(electrolyte=electrolyte)
    assert default.provenance["deviations_from_validated_default"] == []

    deviant = CoupledModel(electrolyte=electrolyte, dielectric_gradient_forces=True, inertia=False)
    recorded = deviant.provenance["deviations_from_validated_default"]
    # Named by case-file path, so the manifest's own diff (io/defaults.deviations)
    # and this one are comparable rather than merely both plausible.
    assert "physics.dielectric_gradient_forces" in recorded
    assert "physics.inertia" in recorded
    assert deviant.provenance["switches"]["steric"] is True


def test_fr25_provenance_records_the_stabilisation_mode() -> None:
    """A number recorded without its stabilisation mode is not comparable (§6.4).

    The reference COMSOL model ran stabilised, so the comparison of §7.4 must be
    able to attribute a discrepancy to the discretisation rather than to a bug —
    which a manifest that omits the mode cannot do. A mode that is not registered
    is refused rather than recorded, so the manifest never describes a run that did
    not happen.
    """
    electrolyte = Electrolyte.from_parameter_file()
    assert CoupledModel(electrolyte=electrolyte).provenance["stabilisation"] == "none"
    assert (
        CoupledModel(electrolyte=electrolyte, stabilisation="supg").provenance["stabilisation"]
        == "supg"
    )
    with pytest.raises(ValueError, match="'streamline' is not a registered mode") as raised:
        CoupledModel(electrolyte=electrolyte, stabilisation="streamline")
    for mode in ("none", "supg", "reference"):
        assert mode in str(raised.value)


@pytest.fixture
def retuned_mode() -> Iterator[str]:
    """Register a second ``reference`` entry with a different ``C_cw``, then remove it.

    The tuning constants are deliberately not case-file fields — a variant is a
    second registered entry — so this is the supported way to reach one. The
    registry is process-global, so the entry is removed again: leaving it behind
    would make ``test_stabilisation.py``'s "exactly three modes" assertion depend on
    file ordering, which is the fourth failure mode ``CLAUDE.md`` names.
    """
    from nanopnp.physics import stabilisation as stab

    name = "reference-cw035"
    stab.register(name, lambda: stab.ReferenceStabilisation(crosswind_coefficient=0.35))
    try:
        yield name
    finally:
        # No public counterpart to ``register``; the registry is process-global.
        del stab._REGISTRY[name]


def test_fr25_provenance_distinguishes_two_tunings_of_the_same_mode(retuned_mode: str) -> None:
    """The mode *name* is not the operator: its constants are in the digest too.

    ``reference`` with ``C_cw = 1`` and ``reference`` with ``C_cw = 0.35`` are
    different discretisations, so a provenance record carrying only the word
    ``reference`` would let two runs share a cache key and a manifest (FR-25,
    §5.3.2). The tuning constants are not case-file fields — a variant is a second
    registered entry — which is exactly the situation reproduced here.
    """
    from nanopnp.core.hashing import content_hash

    electrolyte = Electrolyte.from_parameter_file()
    baseline = CoupledModel(electrolyte=electrolyte, stabilisation="reference")
    retuned = CoupledModel(electrolyte=electrolyte, stabilisation=retuned_mode)
    assert baseline.provenance["stabilisation_parameters"]["crosswind_coefficient"] == 1.0
    assert retuned.provenance["stabilisation_parameters"]["crosswind_coefficient"] == 0.35
    schema = "test/model-provenance/v1"
    assert content_hash(schema, baseline.provenance) != content_hash(schema, retuned.provenance)


def test_fr25_provenance_records_the_three_element_orders() -> None:
    """``phi``/``c``, ``u`` and ``p`` are reported separately (NUM-03, §5.3.3)."""
    electrolyte = Electrolyte.from_parameter_file()
    model = CoupledModel(
        electrolyte=electrolyte,
        order=2,
        velocity_order=1,
        pressure_order=1,
        stabilisation="reference",
    )
    assert model.provenance["elements"] == {
        "potential": 2,
        "concentration": 2,
        "velocity": 1,
        "pressure": 1,
    }
    assert model.provenance["stabilisation_provenance"]["terms"] == (
        "streamline,crosswind,flow_gls,grad_div"
    )


def test_fr20_a_model_declares_fields_boundaries_and_a_solve_strategy() -> None:
    """Every registered model implements the section 5.4.3 interface."""
    for name in SPECIFIED_MODELS:
        model = models.create(name)
        assert model.name == name
        assert model.fields
        assert set(model.boundary_conditions) <= {field.name for field in model.fields}
        assert model.provenance["model"] == name
        assert callable(model.space)
        assert callable(model.cold_state)
        assert callable(model.residual_form)
        assert callable(model.solve)


def test_unknown_keywords_are_rejected_rather_than_dropped() -> None:
    """The protocol's ``**kwargs`` must not become silence."""
    model = models.create("pb")
    with pytest.raises(TypeError, match="unexpected keyword"):
        model.residual_form(None, None, debye_length_nm=1.0, tractions={})


def test_electrolyte_owns_the_steric_switch() -> None:
    """A model and its electrolyte cannot disagree about ``beta_i``."""
    electrolyte = Electrolyte.from_parameter_file(
        switches=replace(CorrectionSwitches.classical(), steric=True)
    )
    model = CoupledModel(electrolyte=electrolyte)
    assert model.steric is True
    assert model.provenance["switches"]["steric"] is True


def test_num18_cold_state_starts_the_ions_at_bulk_not_at_zero() -> None:
    """``c~_i = 1``, so the NUM-17 positivity gate passes on entry.

    Public because the ladder needs it: transferring a solution onto a larger
    field set fills the fields the previous rung did not solve for from a cold
    start, and only the model knows what admissible means for them.
    """
    import ngsolve as ngs

    from nanopnp.mesh.primitives import CylinderGeometry

    model = models.create("pnp", classical=True, fluid="electrolyte")
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=2.0)
    boundaries = models.CoupledBoundaries(potential="end", concentration="end")
    state = model.cold_state(mesh, boundaries)
    fields = {f.name: c for f, c in zip(model.fields, state.components, strict=True)}
    # Compared as *functions*, never coefficient by coefficient: the P2 basis is
    # hierarchical, so the constant 1 has vertex coefficients 1 and edge
    # coefficients 0 (see ``post/reaction_flux.py``).
    for species in model.species:
        concentration = fields[f"c_{species}"]
        assert ngs.Integrate((concentration - 1.0) ** 2, mesh) == pytest.approx(0.0, abs=1e-20)
    assert ngs.Integrate(fields[POTENTIAL] ** 2, mesh) == pytest.approx(0.0, abs=1e-20)


def test_cold_state_rejects_concentrations_on_a_model_that_solves_none() -> None:
    """A caller passing ion data to Poisson-Boltzmann has misunderstood it (PHY-24)."""
    from nanopnp.mesh.primitives import CylinderGeometry

    model = models.create("pb")
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=2.0)
    boundaries = models.CoupledBoundaries(potential="end")
    with pytest.raises(TypeError, match="initial_concentrations"):
        model.cold_state(mesh, boundaries, initial_concentrations={"Na": 1.0})


def test_num18_surface_charge_enters_poisson_as_its_boundary_term() -> None:
    """``-int_Gamma sigma~_s v r ds`` is exactly what the term adds to the residual.

    Rung 4 of the NUM-18 ladder ramps ``sigma_s`` and ``rho_pore`` together, so
    the surface term has to be assembled rather than left to the wall's natural
    condition. It carries no trial function, so the difference between the
    residual with and without it is a constant vector, and that vector is the
    load form of the same integrand — sign included. A flipped sign would put
    the double layer on the wrong side of the wall and still converge.
    """
    import ngsolve as ngs

    from nanopnp.mesh.primitives import CylinderGeometry
    from nanopnp.physics.measures import AXISYMMETRIC

    surface_density = 0.37
    model = models.create("pnp", classical=True, fluid="electrolyte")
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=1.0)
    boundaries = models.CoupledBoundaries(potential="end", concentration="end")
    state = model.cold_state(mesh, boundaries)
    space = state.space

    def applied(**extra: object) -> ngs.BaseVector:
        form = ngs.BilinearForm(space)
        form += model.residual_form(space, AXISYMMETRIC, **extra)
        out = state.vec.CreateVector()
        form.Apply(state.vec, out)
        return out

    difference = applied(surface_charge=surface_density) - applied()

    potential_test = space.TestFunction()[0]
    load = ngs.LinearForm(space)
    load += AXISYMMETRIC.surface(
        surface_density * potential_test, definedon=mesh.Boundaries("wall")
    )
    load.Assemble()
    residual_of_difference = (difference + load.vec).Norm()
    assert residual_of_difference == pytest.approx(0.0, abs=1e-12 * max(load.vec.Norm(), 1.0))
    assert load.vec.Norm() > 0.0, "the wall boundary must actually carry the term"


def test_fr23_a_solve_carries_its_residual_and_distance_field_on_the_solution() -> None:
    """``ModelSolution`` keeps what the NUM-25 reaction flux needs to be correct.

    Rebuilding the residual by hand is not merely wasteful: a coupled residual
    reassembled without the *same* ``wall_distance_nm`` is a different operator,
    and the flux taken against it is wrong with no diagnostic. So the form and
    the distance field travel with the solution.
    """
    import ngsolve as ngs

    from nanopnp.mesh.primitives import CylinderGeometry
    from nanopnp.physics.measures import AXISYMMETRIC

    distance = ngs.x + 0.25
    model = models.create("pnp", classical=True, fluid="electrolyte")
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=1.0)
    boundaries = models.CoupledBoundaries(potential="end", concentration="end")
    steps: list[object] = []
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        boundaries=boundaries,
        wall_distance_nm=distance,
        callback=steps.append,
        potential_values=mesh.BoundaryCF({"end": 0.0}),
    )
    assert solution.residual is not None
    assert solution.wall_distance_nm is distance
    assert len(steps) == solution.newton.iterations

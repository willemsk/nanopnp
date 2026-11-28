from __future__ import annotations

from itertools import product

import ngsolve as ngs
import pytest
from pydantic import BaseModel

from nanopnp.io.case import CaseDocument
from nanopnp.io.case_paths import schema_default
from nanopnp.io.defaults import VALIDATED_DEFAULT_CASE, deviations, value_at
from nanopnp.io.switches import SWITCHES, Switch, conflicts, in_force
from nanopnp.io.vocabulary import POTENTIAL, PRESSURE, VELOCITY
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.primitives import CoupledBoundaries, CylinderGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import kernel, models
from nanopnp.physics.coupled import COUPLED_TERMS
from nanopnp.physics.models import CoupledModel
from nanopnp.physics.terms import EPNP_NS_TERMS

PHY23 = ("Dielectric decrement", "Dielectric-gradient force")

# Written by hand from section 4: the switches each display term of epnp-ns is assembled under.
UNDER: dict[str, tuple[str, ...]] = {
    "Poisson": (),
    "Nernst\N{EN DASH}Planck": (),
    "Steric flux": (),
    "Advection": ("flow",),
    "Dielectric decrement": ("flow", "dielectric_gradient_forces"),
    "Momentum": ("flow",),
    "Inertia": ("flow", "inertia"),
    "Velocity continuity": ("flow",),
    "Variable density": ("flow", "variable_density"),
    "Body force": ("flow",),
    "Dielectric-gradient force": ("flow", "dielectric_gradient_forces"),
    "Corrections": (),
}


def _admitted() -> list[dict[str, bool]]:
    names = [record.name for record in SWITCHES]
    every = product((False, True), repeat=len(names))
    sets = [dict(zip(names, values, strict=True)) for values in every]
    return [values for values in sets if not conflicts(values)]


def test_ver82_phy23_both_terms_or_neither_in_every_admitted_set_of_switches() -> None:
    for record in SWITCHES:
        assert set(record.terms) & set(PHY23) in (set(), set(PHY23)), record.name
    assert [term.name for term in EPNP_NS_TERMS] == list(UNDER)
    admitted = _admitted()
    assert len(admitted) > len(SWITCHES), "the combinations must not be vacuous"
    for values in admitted:
        for name, under in UNDER.items():
            expected = all(values[switch] for switch in under)
            assert in_force(name, values) is expected, (name, values)
        assert in_force(PHY23[0], values) is in_force(PHY23[1], values), values


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    return CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=0.8)


def _state_context(mesh: ngs.Mesh, model: CoupledModel) -> kernel.Context:
    space = model.space(
        mesh,
        CoupledBoundaries(
            potential="wall|end",
            concentration="wall|end",
            velocity="wall|end",
            velocity_axis="axis",
        ),
    )
    state = ngs.GridFunction(space)
    r, z = ngs.x, ngs.y
    values = {
        POTENTIAL: 0.3 * ngs.sin(0.7 * z) * (1.0 + 0.1 * r * r),
        "c_Na+": 1.0 + 0.2 * ngs.cos(0.5 * z) * (1.0 - 0.05 * r * r),
        "c_Cl-": 1.0 - 0.15 * ngs.sin(0.4 * z) * (1.0 + 0.05 * r * r),
        VELOCITY: ngs.CF((0.02 * r * ngs.cos(0.3 * z), 0.04 * (1.0 - 0.1 * r * r))),
        PRESSURE: 0.01 * ngs.sin(0.6 * z) * (1.0 + 0.2 * r * r),
    }
    for field, component in zip(model.fields, state.components, strict=True):
        component.Set(values[field.name])
    functions = dict(zip((f.name for f in model.fields), state.components, strict=True))
    return model.context(mesh, AXISYMMETRIC, trial=functions)


def test_ver82_phy23_the_model_assembles_both_terms_with_the_switch_and_neither_without(
    mesh: ngs.Mesh,
) -> None:
    electrolyte = Electrolyte.from_parameter_file()
    on = CoupledModel(
        electrolyte=electrolyte,
        concentration_M=0.1,
        fluid="electrolyte",
        dielectric_gradient_forces=True,
    )
    assert {term.name for term in on.terms_in_force()} >= set(PHY23)
    context = _state_context(mesh, on)
    by_name = {term.name: term for term in COUPLED_TERMS}
    decrement, force = by_name[PHY23[0]], by_name[PHY23[1]]
    assert decrement.drift is not None and force.force is not None
    for species in on.species:
        assert decrement.drift(context, context.trial, species) is not None, species
    assert force.force(context, context.trial) is not None

    off = CoupledModel(electrolyte=electrolyte, concentration_M=0.1, fluid="electrolyte")
    assert not {term.name for term in off.terms_in_force()} & set(PHY23)

    with pytest.raises(ValueError, match="flow"):
        CoupledModel(electrolyte=electrolyte, flow=False, dielectric_gradient_forces=True)
    with pytest.raises(ValueError, match="log branch"):
        CoupledModel(electrolyte=electrolyte, dielectric_gradient_forces=True, log_variables=True)


def _assigned(document: CaseDocument, path: str, value: object) -> CaseDocument:
    def set_in(block: BaseModel, parts: list[str]) -> BaseModel:
        head, *rest = parts
        inner = value if not rest else set_in(getattr(block, head), rest)
        return block.model_copy(update={head: inner})

    result = set_in(document, path.split("."))
    assert isinstance(result, CaseDocument)
    return result


@pytest.mark.parametrize("record", SWITCHES, ids=lambda record: record.name)
def test_ver82_fr25_each_switch_off_its_default_is_a_deviation_of_the_case_and_the_model(
    record: Switch,
) -> None:
    flipped = not record.default
    document = _assigned(VALIDATED_DEFAULT_CASE, record.path, flipped)
    found = {deviation.path: deviation for deviation in deviations(document)}
    assert set(found) == {record.path}
    assert found[record.path].value is flipped
    assert found[record.path].validated is record.default

    electrolyte = Electrolyte.from_parameter_file()
    options = {record.name: flipped}
    if record.name == "dielectric_gradient_forces":
        options["flow"] = True
    model = CoupledModel(electrolyte=electrolyte, **options)  # type: ignore[arg-type]
    assert model.provenance["deviations_from_validated_default"] == [record.path]
    default = CoupledModel(electrolyte=electrolyte)
    assert default.provenance["deviations_from_validated_default"] == []


def test_ver82_the_records_are_the_schemas_and_every_declarations() -> None:
    names = [record.name for record in SWITCHES]
    assert len(set(names)) == len(names)
    terms = {term.name for term in COUPLED_TERMS}
    for record in SWITCHES:
        assert schema_default(record.path) == (True, record.default), record.path
        assert value_at(VALIDATED_DEFAULT_CASE, record.path) is record.default, record.path
        assert set(record.terms) <= terms, record.name
        for relation in (*record.requires, *record.excludes):
            assert relation.switch in names, (record.name, relation)
    assert deviations(VALIDATED_DEFAULT_CASE) == ()
    for model in models.registered_models():
        assert sorted(models.declaration(model).switches) == sorted(names), model

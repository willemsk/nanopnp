"""VER-71 (WP42 D3 to D8) — no case leaf is accepted and then ignored."""

from __future__ import annotations

import copy
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.solve.continuation import Rung

MODELS = ("epnp-ns", "pb", "pb-linear", "pnp", "pnp-ns", "poisson")
CORRECTIONS = ("diffusivity", "mobility", "viscosity", "permittivity", "density")
PARTS = ("model", "concentration", "wall")
WILLEMS = "willems2020_nacl"

CORRECTION_LEAVES = frozenset(
    {f"electrolyte.corrections.{p}.{k}" for p in CORRECTIONS for k in PARTS}
    | {"electrolyte.corrections.steric.model", "electrolyte.driver"}
)
WALL_DISTANCE = frozenset(
    {"numerics.wall_distance.sources", "numerics.wall_distance.max_distance_nm"}
)
VELOCITY_PRESSURE = frozenset({"numerics.elements.u", "numerics.elements.p"})
ELECTROSTATIC = CORRECTION_LEAVES | VELOCITY_PRESSURE | WALL_DISTANCE | {"numerics.stabilisation"}
LINEAR = frozenset({"numerics.nonlinear.max_iter", "numerics.nonlinear.rtol"})

UNREAD: dict[str, frozenset[str]] = {
    "epnp-ns": frozenset(),
    "pnp": frozenset(
        {f"electrolyte.corrections.{p}.{k}" for p in ("viscosity", "density") for k in PARTS}
        | VELOCITY_PRESSURE
    ),
    "pnp-ns": CORRECTION_LEAVES | WALL_DISTANCE,
    "pb": ELECTROSTATIC,
    "pb-linear": ELECTROSTATIC | LINEAR,
    "poisson": ELECTROSTATIC | LINEAR | {"electrolyte.concentration_M"},
}
"""WP42 D3: the leaves each shipped model declares it does not read."""

SOLVE_PROBES: tuple[tuple[str, tuple[Any, ...]], ...] = (
    ("electrolyte.concentration_M", (0.2,)),
    ("electrolyte.driver", ("ionic_strength",)),
    *((f"electrolyte.corrections.{p}.model", ("none", WILLEMS)) for p in CORRECTIONS),
    *(
        (f"electrolyte.corrections.{p}.{k}", (False,))
        for p in CORRECTIONS
        for k in ("concentration", "wall")
    ),
    ("electrolyte.corrections.steric.model", ("none", "borukhov")),
    ("boundary_conditions.bias_V", (0.1,)),
    ("boundary_conditions.ground", ("trans",)),
    ("physics.flow", (True, False)),
    ("physics.variable_density", (True, False)),
    ("physics.inertia", (True, False)),
    ("physics.dielectric_gradient_forces", (True,)),
    ("physics.solid_permittivities", ({"membrane": 4.0},)),
    ("numerics.elements.phi", ("P1", "P3")),
    ("numerics.elements.c", ("P1", "P3")),
    ("numerics.elements.u", ("P3",)),
    ("numerics.elements.p", ("P2",)),
    ("numerics.stabilisation", ("supg", "reference")),
    ("numerics.wall_distance.sources", ("wall|membrane",)),
    ("numerics.wall_distance.max_distance_nm", (2.5,)),
)
"""WP42 D7: each solve leaf and the values it is perturbed to; a base value is skipped."""


@pytest.fixture(scope="module")
def meshes(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    import netgen.occ as occ
    import ngsolve as ngs

    from nanopnp.mesh.adapter import from_ngsolve, write_msh41
    from nanopnp.mesh.primitives import CylindricalPoreGeometry

    directory = tmp_path_factory.mktemp("leaves")
    pore = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=0.35, check_quality=False)
    face = occ.Rectangle(2.0, 8.0).Face()
    face.name = "electrolyte"
    for edge in face.edges:
        r, z = edge.center[0], edge.center[1]
        if abs(r) < 1e-9:
            edge.name = "axis"
        elif abs(r - 2.0) < 1e-9:
            edge.name = "wall"
        else:
            edge.name = "cis" if abs(z) < 1e-9 else "trans"
    fluid = ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=1.0))
    return {
        "pore": write_msh41(from_ngsolve(pore), directory / "pore.msh"),
        "fluid": write_msh41(from_ngsolve(fluid), directory / "fluid.msh"),
    }


def base(model: str, meshes: dict[str, Path]) -> dict[str, Any]:
    electrostatic = model in ("pb", "pb-linear", "poisson")
    document: dict[str, Any] = {
        "schema": "nanopnp/case/v0.5",
        "name": "leaves",
        "inputs": {
            "mesh": {
                "path": str(meshes["pore"]),
                "format": "msh41",
                "groups": {"default": "interface"},
            }
        },
        "electrolyte": {
            "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
            "concentration_M": 0.1,
            "parameters": WILLEMS,
        },
        "boundary_conditions": {"bias_V": 0.05, "ground": "cis"},
        "physics": {"model": model, "solid_permittivities": {"membrane": 3.2}},
        "numerics": {"continuation": "none", "stabilisation": "none"},
        "outputs": [],
    }
    if model == "epnp-ns":
        document["electrolyte"]["corrections"] = {
            **{p: {"model": WILLEMS} for p in CORRECTIONS},
            "steric": {"model": "borukhov"},
        }
    if model == "pnp":
        document["electrolyte"]["corrections"] = {
            **{p: {"model": WILLEMS} for p in ("diffusivity", "mobility", "permittivity")},
            "steric": {"model": "borukhov"},
        }
        document["physics"].update(flow=False, variable_density=False, inertia=False)
    if electrostatic:
        document["physics"].update(flow=False, variable_density=False, inertia=False)
    if model in ("pb", "pb-linear"):
        del document["physics"]["solid_permittivities"]
        document["inputs"]["mesh"] = {"path": str(meshes["fluid"]), "format": "msh41"}
    return document


def put(document: dict[str, Any], path: str, value: object) -> dict[str, Any]:
    edited = copy.deepcopy(document)
    node = edited
    *parents, leaf = path.split(".")
    for key in parents:
        node = node.setdefault(key, {})
    node[leaf] = value
    return edited


def get(document: dict[str, Any], path: str) -> object:
    from nanopnp.io.case_paths import schema_default

    node: object = document
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return schema_default(path)[1]
        node = node[key]
    return node


def fingerprint(document: dict[str, Any]) -> tuple[object, ...]:
    from dataclasses import replace

    import ngsolve as ngs
    import numpy as np

    from nanopnp.charge.stage import case_fields
    from nanopnp.mesh.ingest import deployed_mesh
    from nanopnp.numerics.measures import AXISYMMETRIC
    from nanopnp.physics.models import solves_transport
    from nanopnp.pipeline.case import loads_case, resolve
    from nanopnp.solve.state import ladder, residual_keywords, wall_distance_field

    resolved = resolve(loads_case(yaml.safe_dump(document)))
    mesh = deployed_mesh(resolved, None).mesh
    order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
    measures = replace(AXISYMMETRIC, element_order=order)
    distance = wall_distance_field(resolved, mesh, order=order)
    fields = case_fields(resolved, None, None, mesh, measures=measures)
    rungs = ladder(resolved, mesh, measures, distance, fields)
    top = rungs[-1]
    model = top.model
    space = model.space(mesh, top.boundaries)
    state = ngs.GridFunction(space)
    components = state.components if len(model.fields) > 1 else (state,)
    for index, component in enumerate(components):
        if component.dim == 2:
            component.Set(ngs.CF((0.001 * ngs.x, 0.02 + 0.001 * ngs.y)))
        elif model.fields[index].name.startswith("c_"):
            # Distinct per species, so the state is not electroneutral (Design §3).
            component.Set(1.0 + (0.01 + 0.007 * index) * ngs.x + (0.005 - 0.003 * index) * ngs.y)
        else:
            component.Set(0.03 * ngs.y + 0.01 * ngs.x + 0.002 * index)
    extra = dict(residual_keywords(top))
    if resolved.stabilisation != "none" and solves_transport(model):
        extra["state"] = state
    form = ngs.BilinearForm(space)
    form += model.residual_form(space, top.measures, **extra)
    applied = state.vec.CreateVector()
    form.Apply(state.vec, applied)
    essential = ngs.GridFunction(ngs.H1(mesh, order=order))
    essential.Set(
        top.solve_kwargs["potential_values"], ngs.BND, definedon=mesh.Boundaries("cis|trans")
    )
    return (
        tuple((rung.name, rung.stage, rung.model.name) for rung in rungs),
        np.array(applied.FV()),
        np.array(essential.vec.FV()),
    )


def outcome(document: dict[str, Any], reference: tuple[object, ...]) -> str:
    import numpy as np

    from nanopnp.io.case import CaseValidationError, UnsupportedCaseSection

    try:
        found = fingerprint(document)
    except (CaseValidationError, UnsupportedCaseSection):
        return "refused"
    same = (
        found[0] == reference[0]
        and all(
            a.shape == b.shape and np.array_equal(a, b)  # type: ignore[union-attr]
            for a, b in zip(found[1:], reference[1:], strict=True)
        )
    )
    return "inert" if same else "live"


def probes(model: str, meshes: dict[str, Path]) -> Iterator[tuple[str, object, dict[str, Any]]]:
    document = base(model, meshes)
    for path, values in SOLVE_PROBES:
        for value in values:
            if get(document, path) != value:
                yield path, value, put(document, path, value)


def test_ver71_every_case_leaf_is_classified_once_in_both_directions() -> None:
    from nanopnp.core.stages import registered_stages
    from nanopnp.io.case_paths import case_fields
    from nanopnp.validation.case_leaves import KINDS, LEAVES

    walked = {reference.path for reference in case_fields()}
    assert set(LEAVES) == walked
    assert KINDS == ("solve", "solver", "stage", "post", "fixed", "checked", "provenance")
    for path, leaf in LEAVES.items():
        assert leaf.kind in KINDS, path
        assert leaf.reason.strip(), path
        if leaf.kind == "stage":
            assert leaf.consumer in {stage.name for stage in registered_stages()}, path
    solve = {path for path, leaf in LEAVES.items() if leaf.kind == "solve"}
    assert solve == {path for path, _ in SOLVE_PROBES} | {"physics.model"}
    assert {path for path, leaf in LEAVES.items() if leaf.kind == "solver"} == {
        "numerics.nonlinear.max_iter",
        "numerics.nonlinear.rtol",
        "numerics.linear.solver",
        "numerics.continuation",
    }
    assert {path for path, leaf in LEAVES.items() if leaf.kind == "provenance"} == {
        "schema",
        "name",
        "structure.source.variant",
    }
    assert {path for path, leaf in LEAVES.items() if leaf.kind == "checked"} == {
        "electrolyte.corrections.steric.a_ion_nm",
        "electrolyte.corrections.steric.a_water_nm",
    }
    assert {path for path, leaf in LEAVES.items() if leaf.kind == "post"} == {"outputs"}
    assert {path for path, leaf in LEAVES.items() if leaf.kind == "fixed"} == {
        "numerics.nonlinear.strategy",
        "numerics.nonlinear.damping",
        "boundary_conditions.walls.ion_flux",
        "boundary_conditions.walls.slip",
        "charge.smearing.axis_cutoff_nm",
        "electrolyte.temperature_K",
        "electrolyte.parameters",
        "electrolyte.species.0.name",
        "electrolyte.species.0.z",
        "inputs.mesh.artefact",
        "inputs.charge.artefact",
        "inputs.eps_r.artefact",
    }


def test_ver71_a_leaf_added_to_the_schema_and_classified_nowhere_fails() -> None:
    from nanopnp.io.case_paths import case_fields
    from nanopnp.validation.case_leaves import LEAVES, unclassified

    walked = [reference.path for reference in case_fields()]
    assert unclassified(walked, LEAVES) == ((), ())
    assert unclassified([*walked, "physics.extra_flag"], LEAVES) == (("physics.extra_flag",), ())
    stale = {**LEAVES, "physics.gone": LEAVES["name"]}
    assert unclassified(walked, stale) == ((), ("physics.gone",))


@pytest.mark.parametrize("model", MODELS)
def test_ver71_each_model_declares_the_leaves_it_does_not_read(model: str) -> None:
    from nanopnp.physics.models import declaration

    assert declaration(model).unread == UNREAD[model]


@pytest.mark.parametrize("model", MODELS)
def test_ver71_every_unread_path_is_a_schema_leaf(model: str) -> None:
    from nanopnp.io.case_paths import case_fields
    from nanopnp.physics.models import declaration

    walked = {reference.path for reference in case_fields()}
    unread = declaration(model).unread
    assert unread <= walked, f"{model}: not schema leaves: {sorted(unread - walked)}"


def test_ver71_the_shipped_models_are_the_ones_the_leaf_tests_cover() -> None:
    from nanopnp.physics.models import registered_models

    assert set(registered_models()) == set(MODELS)


def test_ver71_the_switch_sets_honour_only_what_changes_the_operator() -> None:
    from nanopnp.physics.models import declaration

    pnp = declaration("pnp").switches
    assert pnp["flow"] == (False,)
    assert pnp["variable_density"] == (False,)
    assert pnp["inertia"] == (False,)
    assert set(pnp["dielectric_gradient_forces"]) == {False, True}
    classical = declaration("pnp-ns").switches
    assert set(classical["flow"]) == {False, True}
    assert classical["variable_density"] == (True,)
    assert set(classical["inertia"]) == {False, True}
    assert classical["dielectric_gradient_forces"] == (False,)
    assert all(set(values) == {False, True} for values in declaration("epnp-ns").switches.values())


MODELS_D6 = (
    "epnp-ns",
    "pb",
    "pb-linear",
    "pnp",
    "pnp-ns",
    "poisson",
)


@pytest.mark.parametrize("model", MODELS_D6)
def test_ver71_no_solve_leaf_is_accepted_and_inert(model: str, meshes: dict[str, Path]) -> None:
    from nanopnp.io.case_paths import schema_default

    reference = fingerprint(base(model, meshes))
    inert = []
    for path, value, document in probes(model, meshes):
        if outcome(document, reference) == "inert" and not (
            path in UNREAD[model] and not schema_default(path)[0]
        ):
            inert.append(f"{path}: {value!r}")
    assert not inert, f"{model} accepts and ignores {inert}"


# PHY-22
@pytest.mark.parametrize(
    ("partner", "leaf", "value", "named"),
    [
        (
            ("electrolyte.corrections.density.model", "none"),
            "physics.variable_density",
            False,
            "physics.variable_density: false",
        ),
        (
            ("electrolyte.corrections.permittivity.concentration", False),
            "physics.dielectric_gradient_forces",
            True,
            "physics.dielectric_gradient_forces: true",
        ),
        (
            ("electrolyte.corrections.permittivity.model", "none"),
            "physics.dielectric_gradient_forces",
            True,
            "physics.dielectric_gradient_forces: true",
        ),
    ],
    ids=["variable density", "dielectric gradient, part off", "dielectric gradient, model none"],
)
def test_ver71_a_switch_beside_a_partner_that_leaves_it_nothing_to_switch_is_refused(
    partner: tuple[str, object], leaf: str, value: object, named: str, meshes: dict[str, Path]
) -> None:
    from nanopnp.io.case import CaseValidationError

    document = base("epnp-ns", meshes)
    live = put(document, leaf, value)
    assert outcome(live, fingerprint(document)) == "live"
    document = put(document, *partner)
    with pytest.raises(CaseValidationError, match="leaves it nothing to switch") as raised:
        fingerprint(put(document, leaf, value))
    assert named in str(raised.value)


# PHY-22
def test_ver71_every_wall_part_off_is_refused_so_the_wall_distance_has_nothing_to_go_inert(
    meshes: dict[str, Path],
) -> None:
    from nanopnp.io.case import CaseValidationError

    document = base("epnp-ns", meshes)
    for correction in CORRECTIONS:
        document = put(document, f"electrolyte.corrections.{correction}.wall", False)
    with pytest.raises(CaseValidationError, match="no correction model applies"):
        fingerprint(document)


@pytest.mark.parametrize("model", MODELS_D6)
def test_ver71_the_unread_leaves_are_inert_and_the_rest_are_not(
    model: str, meshes: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from nanopnp.pipeline import checks

    monkeypatch.setattr(checks, "_check_unread", lambda document: None)
    reference = fingerprint(base(model, meshes))
    wrong = []
    for path, value, document in probes(model, meshes):
        found = outcome(document, reference)
        if path in UNREAD[model] and found == "live":
            wrong.append(f"{path}: {value!r} is declared unread and moves the operator")
        if path not in UNREAD[model] and found == "inert":
            wrong.append(f"{path}: {value!r} is read but leaves the operator unchanged")
    assert not wrong, f"{model}: {wrong}"


# PHY-13
def test_ver71_the_driver_is_live_for_any_but_two_unit_valence_species(
    meshes: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from nanopnp.materials.electrolyte import Electrolyte
    from nanopnp.pipeline.case import loads_case, resolve

    averaged = Electrolyte.from_parameter_file(WILLEMS, driver="average")
    ionic = Electrolyte.from_parameter_file(WILLEMS, driver="ionic_strength")
    samples = [800.0, 1600.0]  # mol/m^3, ordered as the species: 0.8 M and 1.6 M
    assert ionic.average_concentration(samples) == averaged.average_concentration(samples)
    divalent = (replace(ionic.ion("Na+"), valence=2), ionic.ion("Cl-"))
    assert replace(ionic, species=divalent).average_concentration(samples) == pytest.approx(2.4)
    assert replace(averaged, species=divalent).average_concentration(samples) == pytest.approx(1.2)

    monkeypatch.setattr("nanopnp.pipeline.case.check_species", lambda *args: None)
    divalent_case = put(base("epnp-ns", meshes), "electrolyte.driver", "ionic_strength")
    divalent_case["electrolyte"]["species"][0]["z"] = 2
    assert resolve(loads_case(yaml.safe_dump(divalent_case))).electrolyte.driver == "ionic_strength"


# PHY-22
def test_ver71_applied_parts_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    from typing import TypeVar

    from pydantic import BaseModel

    T = TypeVar("T", bound=BaseModel)

    def replace(obj: T, **changes: object) -> T:
        return obj.model_copy(update=changes)

    from nanopnp.materials import models as materials_models
    from nanopnp.materials.models import applied_parts, applies_part

    assert applied_parts("none", "diffusivity") == frozenset()
    assert not applies_part("none", "diffusivity", "wall")
    assert applied_parts(WILLEMS, "diffusivity") == frozenset({"concentration", "wall"})
    assert applied_parts(WILLEMS, "density") == frozenset({"concentration"})

    doc = materials_models._document(WILLEMS)
    doc_no_wall = replace(doc, ion_wall_function=None)
    monkeypatch.setattr(materials_models, "_document", lambda name: doc_no_wall)
    assert "wall" not in applied_parts(WILLEMS, "diffusivity")

    doc_no_fc = replace(
        doc,
        solvent=replace(
            doc.solvent,
            density=replace(doc.solvent.density, fc=None),
        ),
        species={
            k: replace(v, diffusivity=replace(v.diffusivity, fc=None))
            for k, v in doc.species.items()
        },
    )
    monkeypatch.setattr(materials_models, "_document", lambda name: doc_no_fc)
    assert "concentration" not in applied_parts(WILLEMS, "density")
    assert "concentration" not in applied_parts(WILLEMS, "diffusivity")


class ReachedLinearProbeError(RuntimeError): ...


@pytest.fixture
def probe_solver() -> Iterator[str]:
    from nanopnp.numerics import linear

    name = "ver71-probe"

    class Probe:
        def solve(self, *args: object, **kwargs: object) -> None:
            raise ReachedLinearProbeError(name)

    linear.register_solver(name, Probe)
    try:
        yield name
    finally:
        del linear._REGISTRY[name]


@pytest.mark.parametrize("model", MODELS)
def test_ver71_the_newton_settings_reach_every_model_that_reads_them(
    model: str, meshes: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from nanopnp.physics import models as models_module
    from nanopnp.physics import pb as pb_module
    from nanopnp.pipeline.case import loads_case, resolve
    from nanopnp.solve.continuation import run_ladder

    class ReachedError(Exception):
        pass

    def stop(*args: object, settings: object, **kwargs: object) -> None:
        raise ReachedError(settings)

    monkeypatch.setattr(models_module, "damped_newton", stop)
    monkeypatch.setattr(pb_module, "damped_newton", stop)
    document = base(model, meshes)
    if model not in ("poisson", "pb-linear"):
        document = put(
            put(document, "numerics.nonlinear.max_iter", 37), "numerics.nonlinear.rtol", 1e-7
        )
    resolved = resolve(loads_case(yaml.safe_dump(document)))
    rung = _top_rung(resolved)
    prepared = replace(
        rung,
        solve_kwargs={
            **dict(rung.solve_kwargs),
            "settings": resolved.newton,
            "solver": resolved.linear_solver,
        },
    )
    if UNREAD[model] >= LINEAR:
        run_ladder((prepared,))
        return
    with pytest.raises(ReachedError) as reached:
        run_ladder((prepared,))
    settings = reached.value.args[0]
    assert settings.max_iterations == 37  # type: ignore[attr-defined]
    assert settings.relative_tolerance == 1e-7  # type: ignore[attr-defined]


@pytest.mark.parametrize("model", MODELS)
def test_ver71_the_linear_solver_reaches_every_model(
    model: str, meshes: dict[str, Path], probe_solver: str
) -> None:
    from dataclasses import replace

    from nanopnp.pipeline.case import loads_case, resolve
    from nanopnp.solve.continuation import run_ladder

    document = put(base(model, meshes), "numerics.linear.solver", probe_solver)
    resolved = resolve(loads_case(yaml.safe_dump(document)))
    rung = _top_rung(resolved)
    prepared = replace(
        rung,
        solve_kwargs={
            **dict(rung.solve_kwargs),
            "settings": resolved.newton,
            "solver": resolved.linear_solver,
        },
    )
    with pytest.raises(ReachedLinearProbeError):
        run_ladder((prepared,))


def _top_rung(resolved: ResolvedCase) -> Rung:
    from dataclasses import replace

    from nanopnp.charge.stage import case_fields
    from nanopnp.mesh.ingest import deployed_mesh
    from nanopnp.numerics.measures import AXISYMMETRIC
    from nanopnp.solve.state import ladder, wall_distance_field

    mesh = deployed_mesh(resolved, None).mesh
    order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
    measures = replace(AXISYMMETRIC, element_order=order)
    distance = wall_distance_field(resolved, mesh, order=order)
    fields = case_fields(resolved, None, None, mesh, measures=measures)
    return ladder(resolved, mesh, measures, distance, fields)[-1]


def _refused(document: dict[str, Any]) -> str:
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case, resolve

    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(yaml.safe_dump(document)))
    return str(raised.value)


def test_ver71_unread_leaves_are_refused_naming_each_key_its_default_and_its_readers(
    meshes: dict[str, Path],
) -> None:
    document = put(
        put(base("pnp-ns", meshes), "electrolyte.corrections.diffusivity.model", WILLEMS),
        "electrolyte.corrections.steric.model",
        "borukhov",
    )
    assert _refused(document) == (
        "physics.model 'pnp-ns' does not read 2 keys this case sets; each would be recorded "
        "in the manifest and never applied (PHY-21, section 5.4.3), so leave each at its "
        "default:\n"
        "  electrolyte.corrections.diffusivity.model: willems2020_nacl (default none; read by "
        "epnp-ns, pnp)\n"
        "  electrolyte.corrections.steric.model: borukhov (default none; read by epnp-ns, pnp)"
    )
    assert _refused(put(base("pb", meshes), "numerics.stabilisation", "supg")) == (
        "physics.model 'pb' does not read 1 key this case sets; it would be recorded in the "
        "manifest and never applied (PHY-21, section 5.4.3), so leave it at its default:\n"
        "  numerics.stabilisation: supg (default none; read by epnp-ns, pnp, pnp-ns)"
    )
    linear = put(
        put(base("poisson", meshes), "numerics.nonlinear.max_iter", 50),
        "numerics.nonlinear.rtol",
        1e-8,
    )
    assert _refused(linear) == (
        "physics.model 'poisson' does not read 2 keys this case sets; each would be recorded "
        "in the manifest and never applied (PHY-21, section 5.4.3), so leave each at its "
        "default:\n"
        "  numerics.nonlinear.max_iter: 50 (default 100; read by epnp-ns, pb, pnp, pnp-ns)\n"
        "  numerics.nonlinear.rtol: 1e-08 (default 1e-06; read by epnp-ns, pb, pnp, pnp-ns)"
    )


def test_ver71_a_correction_part_no_model_applies_is_refused(meshes: dict[str, Path]) -> None:
    document = put(
        put(base("epnp-ns", meshes), "electrolyte.corrections.permittivity.wall", False),
        "electrolyte.corrections.density.wall",
        False,
    )
    assert _refused(document) == (
        "electrolyte.corrections switches off 2 parts no correction model applies; each would "
        "be recorded in the manifest as a deviation and never applied (PHY-22), so leave each "
        "at its default, true:\n"
        "  electrolyte.corrections.permittivity.wall: false (permittivity model "
        "'willems2020_nacl' has no wall fit)\n"
        "  electrolyte.corrections.density.wall: false (density model 'willems2020_nacl' has "
        "no wall fit)"
    )
    none = put(
        put(base("epnp-ns", meshes), "electrolyte.corrections.mobility.model", "none"),
        "electrolyte.corrections.mobility.concentration",
        False,
    )
    assert _refused(none) == (
        "electrolyte.corrections switches off 1 part no correction model applies; it would be "
        "recorded in the manifest as a deviation and never applied (PHY-22), so leave it at "
        "its default, true:\n"
        "  electrolyte.corrections.mobility.concentration: false (mobility model 'none' has no "
        "concentration fit)"
    )


@pytest.mark.parametrize("model", ["epnp-ns", "pnp"])
def test_ver71_the_ionic_strength_driver_of_a_one_one_salt_is_refused(
    model: str, meshes: dict[str, Path]
) -> None:
    assert _refused(put(base(model, meshes), "electrolyte.driver", "ionic_strength")) == (
        "electrolyte.driver: ionic_strength drives the corrections with I = 1/2 sum z_i^2 c_i, "
        "which equals the average concentration (c_1 + c_2)/2 for two species of unit "
        "valence, so it would be recorded in the manifest as a deviation and never change a "
        "number (PHY-13); leave it at its default, average"
    )


def test_ver71_pnp_refuses_the_flow_switches_it_cannot_apply(meshes: dict[str, Path]) -> None:
    document = base("pnp", meshes)
    del document["physics"]["variable_density"]
    assert _refused(document) == (
        "physics.model 'pnp' honours physics.variable_density: false only (PHY-21), so "
        "physics.variable_density must be false; true would be recorded in the manifest and "
        "never applied. Models honouring true: epnp-ns, pnp-ns"
    )
    assert _refused(put(base("pnp", meshes), "physics.inertia", True)) == (
        "physics.model 'pnp' honours physics.inertia: false only (PHY-21), so physics.inertia "
        "must be false; true would be recorded in the manifest and never applied. Models "
        "honouring true: epnp-ns, pnp-ns"
    )
    classical = put(base("pnp-ns", meshes), "physics.dielectric_gradient_forces", True)
    assert _refused(classical) == (
        "physics.model 'pnp-ns' honours physics.dielectric_gradient_forces: false only "
        "(PHY-21), so physics.dielectric_gradient_forces must be false; true would be recorded "
        "in the manifest and never applied. Models honouring true: epnp-ns, pnp"
    )


def test_ver71_a_flowless_model_is_refused_on_its_flow_switch_first(
    meshes: dict[str, Path],
) -> None:
    from nanopnp.pipeline.case import loads_case

    document = base("pb", meshes)
    del document["physics"]["flow"]
    document = put(document, "numerics.elements.u", "P1")
    loads_case(yaml.safe_dump(document))
    assert _refused(document) == (
        "physics.model 'pb' honours physics.flow: false only (PHY-21), so physics.flow must be "
        "false; true would be recorded in the manifest and never applied. Models honouring "
        "true: epnp-ns, pnp-ns"
    )


def test_ver71_a_fixed_leaf_is_refused_away_from_its_default(meshes: dict[str, Path]) -> None:
    from nanopnp.io.case import CaseValidationError, UnsupportedCaseSection
    from nanopnp.pipeline.case import loads_case, resolve

    alternatives: dict[str, object] = {
        "numerics.nonlinear.strategy": "hybrid",
        "numerics.nonlinear.damping": "backtracking",
        "boundary_conditions.walls.ion_flux": "prescribed",
        "boundary_conditions.walls.slip": "navier",
        "electrolyte.temperature_K": 310.0,
        "electrolyte.parameters": "no_such_parameters",
    }
    for path, value in alternatives.items():
        document = put(base("epnp-ns", meshes), path, value)
        with pytest.raises((CaseValidationError, UnsupportedCaseSection)) as raised:
            resolve(loads_case(yaml.safe_dump(document)))
        assert path.rsplit(".", 1)[-1] in str(raised.value), path


def test_ver71_a_provenance_leaf_moves_no_solve_key(meshes: dict[str, Path]) -> None:
    from nanopnp.pipeline.case import loads_case, resolve
    from nanopnp.validation.case_leaves import LEAVES

    assert LEAVES["name"].kind == "provenance"
    left = resolve(loads_case(yaml.safe_dump(base("epnp-ns", meshes))))
    right = resolve(loads_case(yaml.safe_dump(put(base("epnp-ns", meshes), "name", "other"))))
    assert left.solve_provenance == right.solve_provenance


def test_ver71_stage_leaves_move_their_consumers_key(tmp_path: Path) -> None:
    from nanopnp.core.stages import create, describe
    from nanopnp.io.artefact import Artefact, ProfileArtefact, StageInputs
    from nanopnp.io.case import CaseValidationError, UnsupportedCaseSection
    from nanopnp.mesh.adapter import from_ngsolve, write_msh41
    from nanopnp.mesh.primitives import CylindricalPoreGeometry
    from nanopnp.pipeline.case import loads_case, resolve
    from nanopnp.validation.case_leaves import LEAVES

    def upstream_of(stage_name: str) -> set[str]:
        seen: set[str] = set()
        stack = [inp for inp in describe(stage_name).inputs if inp not in ("case", "case_path")]
        while stack:
            s = stack.pop()
            if s not in seen:
                seen.add(s)
                stack.extend(inp for inp in describe(s).inputs if inp not in ("case", "case_path"))
        return seen

    from nanopnp.geometry.profile import load_profile
    from nanopnp.geometry.region import derive_region, write_region
    from nanopnp.io.case import MembraneSpec, ReservoirSpec

    profile_yaml = Path("data/geometry/clya_reference_profile.yaml")
    region_yaml = tmp_path / "region.yaml"
    write_region(
        derive_region(load_profile(profile_yaml), MembraneSpec(), ReservoirSpec()), region_yaml
    )

    dummy = Artefact(schema="dummy/v1", parameters={}, inputs={})
    dummy_prof = ProfileArtefact(parameters={}, inputs={}, payload={"profile": profile_yaml})
    dummy_region = Artefact(
        schema="nanopnp/region/v0.5", parameters={}, inputs={}, payload={"region": region_yaml}
    )
    dummy_mesh = Artefact(schema="nanopnp/mesh/v0.5", parameters={}, inputs={})
    dummy_prot = Artefact(schema="nanopnp/protonation/v0.5", parameters={}, inputs={})

    def stage_key(stage_name: str, res: object) -> str:
        inputs_map = {
            "structure": StageInputs(resolved=res),
            "density": StageInputs(resolved=res, upstream={"structure": dummy}),
            "symmetry": StageInputs(resolved=res, upstream={"density": dummy}),
            "contour": StageInputs(resolved=res, upstream={"structure": dummy, "symmetry": dummy}),
            "region": StageInputs(resolved=res, upstream={"contour": dummy_prof}),
            "mesh": StageInputs(resolved=res, upstream={"region": dummy_region}),
            "protonation": StageInputs(resolved=res, upstream={"structure": dummy}),
            "charge": StageInputs(
                resolved=res,
                upstream={"mesh": dummy_mesh, "protonation": dummy_prot, "region": dummy_region},
            ),
        }
        if stage_name == "mesh" and getattr(res, "mesh", None) is not None:
            mesh_spec = res.mesh
            try:
                base_hash = create(stage_name).key(inputs_map[stage_name]).hash
            except Exception:
                base_hash = "unresolved"
            from nanopnp.core.hashing import content_hash

            return content_hash(
                "nanopnp/mesh/supplied/v0.5",
                (base_hash, str(mesh_spec.path), str(mesh_spec.format), dict(mesh_spec.groups)),
            )
        return create(stage_name).key(inputs_map[stage_name]).hash

    p1 = tmp_path / "test1.pdb"
    p1.write_text(
        "ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N\n"
    )
    p2 = tmp_path / "test2.pdb"
    p2.write_text(
        "ATOM      1  CA  ALA A   1       1.000   1.000   1.000  1.00  0.00           C\n"
    )
    traj = tmp_path / "test.xtc"
    traj.write_text("dummy trajectory content")

    pore = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=0.35, check_quality=False)
    m1 = write_msh41(from_ngsolve(pore), tmp_path / "m1.msh")

    pqr1 = tmp_path / "pqr1.pqr"
    pqr1.write_text("ATOM      1  N   ALA A   1       0.000   0.000   0.000  0.50  1.50\n")
    pqr2 = tmp_path / "pqr2.pqr"
    pqr2.write_text("ATOM      1  CA  ALA A   1       1.000   1.000   1.000 -0.50  1.70\n")

    prof1 = tmp_path / "prof1.yaml"
    prof1.write_text(profile_yaml.read_text())
    prof2 = tmp_path / "prof2.yaml"
    prof2_obj = load_profile(profile_yaml).model_copy(update={"name": "other_profile"})
    prof2.write_text(yaml.safe_dump(prof2_obj.model_dump(by_alias=True, mode="json")))

    import numpy as np

    from nanopnp.core.hashing import file_hash
    from nanopnp.density.grid import RadialGrid, write_grid

    r = np.linspace(0.0, 5.0, 21)
    z = np.linspace(-5.0, 5.0, 41)
    vals = np.zeros((41, 21))
    grid = RadialGrid.from_axes(r, z, vals)
    data_c = write_grid(grid, tmp_path / "charge.npz", format="npz")
    charge_yaml = tmp_path / "charge.yaml"
    charge_yaml.write_text(
        "schema: nanopnp/field/v0.5\nname: test_c\nquantity: volume_charge_density\nunits: C/m^3\n"
        "provenance: {source: analytic}\n"
        f"data: {{path: {data_c.name}, format: npz, sha256: {file_hash(data_c)}}}\n"
        f"grid: {{origin_nm: [{grid.origin_nm[0]!r}, {grid.origin_nm[1]!r}], "
        f"spacing_nm: [{grid.spacing_nm[0]!r}, {grid.spacing_nm[1]!r}], "
        f"shape: [{grid.shape[0]}, {grid.shape[1]}]}}\n",
        encoding="utf-8",
    )
    data_e = write_grid(grid, tmp_path / "eps_r.npz", format="npz")
    eps_yaml = tmp_path / "eps_r.yaml"
    eps_yaml.write_text(
        'schema: nanopnp/field/v0.5\nname: test_e\nquantity: solid_fraction\nunits: "1"\n'
        "provenance: {source: analytic}\n"
        f"data: {{path: {data_e.name}, format: npz, sha256: {file_hash(data_e)}}}\n"
        f"grid: {{origin_nm: [{grid.origin_nm[0]!r}, {grid.origin_nm[1]!r}], "
        f"spacing_nm: [{grid.spacing_nm[0]!r}, {grid.spacing_nm[1]!r}], "
        f"shape: [{grid.shape[0]}, {grid.shape[1]}]}}\n",
        encoding="utf-8",
    )

    pdb_base = {
        "schema": "nanopnp/case/v0.5",
        "name": "test",
        "structure": {"source": {"path": str(p1)}, "symmetry": {"point_group": "C12", "axis": "z"}},
        "geometry": {
            "density": {"grid_spacing_nm": 0.05, "kernel": "gaussian_vdw", "sharpness": 1.0},
            "contour": {"isolevel": 0.5, "smoothing": "taubin", "simplify_tol_nm": 0.02},
            "membrane": {"thickness_nm": 4.0, "centre_z_nm": 0.0},
            "reservoir": {"radius_nm": 10.0},
        },
        "charge": {
            "ph": 7.5,
            "forcefield": "CHARMM",
            "titration": "propka",
            "smearing": {"sharpness": 0.5, "grid_spacing_nm": 0.005},
            "dielectric_transition_nm": 0.0,
            "exclusion_offset_nm": 0.0,
        },
        "numerics": {
            "mesh": {
                "backend": "netgen",
                "wall_h_nm": 0.2,
                "size_scale": 1.0,
                "boundary_layer": False,
            }
        },
        "electrolyte": {
            "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
            "concentration_M": 0.1,
            "parameters": "willems2020_nacl",
        },
        "boundary_conditions": {"bias_V": 0.05, "ground": "cis"},
        "physics": {"model": "epnp-ns"},
    }

    res_base = resolve(loads_case(yaml.safe_dump(pdb_base)))

    live_pdb = {
        "structure.source.path": ("structure", str(p2)),
        "structure.source.chains": ("structure", "A,B,C,D,E,F,G,H,I,J,K,L"),
        "structure.source.selection": ("structure", "all"),
        "structure.ensemble.trajectory": ("structure", str(traj)),
        "structure.ensemble.frames.last_ns": ("structure", 10.0),
        "structure.ensemble.frames.count": ("structure", 5),
        "structure.symmetry.point_group": ("structure", "C6"),
        "structure.symmetry.axis": ("structure", "auto"),
        "geometry.density.grid_spacing_nm": ("density", 0.04),
        "geometry.density.sharpness": ("density", 1.2),
        "geometry.contour.isolevel": ("contour", 0.6),
        "geometry.contour.smoothing": ("contour", "none"),
        "geometry.contour.simplify_tol_nm": ("contour", 0.01),
        "geometry.membrane.thickness_nm": ("region", 5.0),
        "geometry.membrane.centre_z_nm": ("region", 0.5),
        "geometry.reservoir.radius_nm": ("region", 12.0),
        "charge.exclusion_offset_nm": ("region", 0.12),
        "numerics.mesh.backend": ("mesh", "gmsh"),
        "numerics.mesh.wall_h_nm": ("mesh", 0.3),
        "numerics.mesh.size_scale": ("mesh", 1.5),
        "charge.ph": ("protonation", 8.0),
        "charge.forcefield": ("protonation", "PEOEPB"),
        "charge.titration": ("protonation", "none"),
        "charge.smearing.sharpness": ("charge", 1.5),
        "charge.smearing.grid_spacing_nm": ("charge", 0.05),
        "charge.dielectric_transition_nm": ("charge", 0.06),
    }

    for path, (consumer, val) in live_pdb.items():
        doc = put(pdb_base, path, val)
        if path == "charge.titration" and val == "none":
            del doc["charge"]["ph"]
        res = resolve(loads_case(yaml.safe_dump(doc)))
        assert stage_key(consumer, res) != stage_key(consumer, res_base), (
            f"{path} did not move {consumer}"
        )
        for u in upstream_of(consumer):
            assert stage_key(u, res) == stage_key(u, res_base), f"{path} moved upstream {u}"

    refused = {
        "geometry.density.kernel": "other",
        "geometry.analyte.shape": "sphere",
        "geometry.analyte.a_nm": 1.0,
        "geometry.analyte.b_nm": 1.0,
        "geometry.analyte.z_nm": 0.0,
        "geometry.analyte.charge_e": 0.0,
        "numerics.mesh.boundary_layer": True,
        "inputs.profile.format": "other",
        "inputs.profile.groups": {"default": "interface"},
        "inputs.profile.artefact": "dummy",
        "inputs.pqr.format": "other",
        "inputs.pqr.groups": {"default": "interface"},
        "inputs.pqr.artefact": "dummy",
    }
    for path, val in refused.items():
        doc = put(pdb_base, path, val)
        with pytest.raises((CaseValidationError, UnsupportedCaseSection)):
            resolve(loads_case(yaml.safe_dump(doc)))

    prof_case1 = {
        "schema": "nanopnp/case/v0.5",
        "name": "prof",
        "inputs": {"profile": {"path": str(prof1), "format": "profile1"}},
        "geometry": {"membrane": {"thickness_nm": 4.0}, "reservoir": {"radius_nm": 10.0}},
        "electrolyte": {
            "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
            "concentration_M": 0.1,
            "parameters": "willems2020_nacl",
        },
        "boundary_conditions": {"bias_V": 0.05, "ground": "cis"},
        "physics": {"model": "epnp-ns"},
    }
    prof_case2 = dict(prof_case1, inputs={"profile": {"path": str(prof2), "format": "profile1"}})
    res_p1 = resolve(loads_case(yaml.safe_dump(prof_case1)))
    res_p2 = resolve(loads_case(yaml.safe_dump(prof_case2)))
    assert stage_key("region", res_p1) != stage_key("region", res_p2)

    pqr_case1 = {
        "schema": "nanopnp/case/v0.5",
        "name": "pqr",
        "inputs": {
            "mesh": {"path": str(m1), "format": "msh41"},
            "pqr": {"path": str(pqr1), "format": "pqr"},
        },
        "electrolyte": {
            "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
            "concentration_M": 0.1,
            "parameters": "willems2020_nacl",
        },
        "boundary_conditions": {"bias_V": 0.05, "ground": "cis"},
        "physics": {"model": "epnp-ns", "solid_permittivities": {"membrane": 3.2}},
    }
    pqr_case2 = dict(
        pqr_case1,
        inputs={
            "mesh": {"path": str(m1), "format": "msh41"},
            "pqr": {"path": str(pqr2), "format": "pqr"},
        },
    )
    res_q1 = resolve(loads_case(yaml.safe_dump(pqr_case1)))
    res_q2 = resolve(loads_case(yaml.safe_dump(pqr_case2)))
    assert stage_key("protonation", res_q1) != stage_key("protonation", res_q2)

    mesh_case = {
        "schema": "nanopnp/case/v0.5",
        "name": "mesh",
        "inputs": {
            "mesh": {"path": str(m1), "format": "msh41", "groups": {"default": "interface"}}
        },
        "electrolyte": {
            "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
            "concentration_M": 0.1,
            "parameters": "willems2020_nacl",
        },
        "boundary_conditions": {"bias_V": 0.05, "ground": "cis"},
        "physics": {"model": "epnp-ns", "solid_permittivities": {"membrane": 3.2}},
    }
    res_m = resolve(loads_case(yaml.safe_dump(mesh_case)))
    k_m = stage_key("mesh", res_m)
    for p, v in [
        ("inputs.mesh.path", str(m1) + ".moved"),
        ("inputs.mesh.format", "msh22"),
        ("inputs.mesh.groups", {"other": "interface"}),
    ]:
        doc = put(mesh_case, p, v)
        res_alt = resolve(loads_case(yaml.safe_dump(doc)))
        assert stage_key("mesh", res_alt) != k_m

    k_base_charge = stage_key("charge", res_base)
    doc_c = put(pdb_base, "inputs.charge.path", str(charge_yaml))
    assert stage_key("charge", resolve(loads_case(yaml.safe_dump(doc_c)))) != k_base_charge

    doc_e = put(pdb_base, "inputs.eps_r.path", str(eps_yaml))
    assert stage_key("charge", resolve(loads_case(yaml.safe_dump(doc_e)))) != k_base_charge

    for kind in ("charge", "eps_r"):
        for sub, v in [("format", "other"), ("groups", {"wall": "interface"})]:
            doc = put(pdb_base, f"inputs.{kind}.{sub}", v)
            with pytest.raises(CaseValidationError):
                resolve(loads_case(yaml.safe_dump(doc)))

    covered = (
        set(live_pdb)
        | set(refused)
        | {"inputs.profile.path", "inputs.pqr.path"}
        | {f"inputs.mesh.{k}" for k in ("path", "format", "groups")}
        | {f"inputs.charge.{k}" for k in ("path", "format", "groups")}
        | {f"inputs.eps_r.{k}" for k in ("path", "format", "groups")}
    )
    assert covered == set(p for p, leaf in LEAVES.items() if leaf.kind == "stage")

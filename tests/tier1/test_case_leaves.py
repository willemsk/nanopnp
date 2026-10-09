"""VER-71 (WP42 D3 to D8) — no case leaf is accepted and then ignored.

A key the solve never reads, written into a case, is recorded in the FR-25
manifest as though it applied (REV-12, REV-42). Every leaf of the case schema is
therefore classified by what reads it (:data:`nanopnp.validation.case_leaves.LEAVES`),
and a leaf the selected model does not read is refused away from its default,
from the model's declaration rather than its name (PHY-21, §5.4.3, VER-56).

The oracle for a leaf read by the solve is the operator itself: the top rung's
residual applied at a fixed state, with its essential potential data and its rung
sequence. The state is non-electroneutral and differs per species and per
component, because an electroneutral state hides every concentration
dependence of classical PNP-NS (WP42 *Design* §3): a probe that cannot see a
dependence would call a live leaf inert.
"""

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


# -- the probe -------------------------------------------------------------------


@pytest.fixture(scope="module")
def meshes(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Write the quick-start pore and a solid-free cylinder with ``cis`` and ``trans`` ends."""
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
    """Return ``model``'s base case: every leaf it does not read at its default (D7)."""
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
    """Return a copy of ``document`` with ``value`` written at the dotted ``path``."""
    edited = copy.deepcopy(document)
    node = edited
    *parents, leaf = path.split(".")
    for key in parents:
        node = node.setdefault(key, {})
    node[leaf] = value
    return edited


def get(document: dict[str, Any], path: str) -> object:
    """Return the value written at ``path``, or the schema's default where none is written."""
    from nanopnp.io.case_paths import schema_default

    node: object = document
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return schema_default(path)[1]
        node = node[key]
    return node


def fingerprint(document: dict[str, Any]) -> tuple[object, ...]:
    """Return the operator a case solves: rungs, residual at a fixed state, essential data.

    Built through the solve stage's own path (``ladder``, ``residual_keywords``),
    never by re-deriving a rung, so the probe sees what stage 10 assembles.
    """
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
    """Return ``refused``, ``live`` or ``inert`` for a perturbed document."""
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
    """Yield each solve leaf, its perturbed value and the perturbed document; skip a base value."""
    document = base(model, meshes)
    for path, values in SOLVE_PROBES:
        for value in values:
            if get(document, path) != value:
                yield path, value, put(document, path, value)


# -- the classification ----------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="planned: WP42 D4")
def test_ver71_every_case_leaf_is_classified_once_in_both_directions() -> None:
    """Every leaf of the schema has one kind, and every entry names a leaf (REV-12)."""
    from nanopnp.validation.case_leaves import KINDS, LEAVES

    from nanopnp.core.stages import registered_stages
    from nanopnp.io.case_paths import case_fields

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


@pytest.mark.xfail(strict=True, reason="planned: WP42 D4")
def test_ver71_a_leaf_added_to_the_schema_and_classified_nowhere_fails() -> None:
    """The oracle of the phase plan: a new path the table does not hold is named."""
    from nanopnp.validation.case_leaves import LEAVES, unclassified

    from nanopnp.io.case_paths import case_fields

    walked = [reference.path for reference in case_fields()]
    assert unclassified(walked, LEAVES) == ((), ())
    assert unclassified([*walked, "physics.extra_flag"], LEAVES) == (("physics.extra_flag",), ())
    stale = {**LEAVES, "physics.gone": LEAVES["name"]}
    assert unclassified(walked, stale) == ((), ("physics.gone",))


@pytest.mark.xfail(strict=True, reason="planned: WP42 D3")
@pytest.mark.parametrize("model", MODELS)
def test_ver71_each_model_declares_the_leaves_it_does_not_read(model: str) -> None:
    """The declaration states the unread leaves, read without building the model (§5.4.3)."""
    from nanopnp.physics.models import declaration

    assert declaration(model).unread == UNREAD[model]


@pytest.mark.xfail(strict=True, reason="planned: WP42 D5")
def test_ver71_the_switch_sets_honour_only_what_changes_the_operator() -> None:
    """REV-42 and its pnp-ns twins: a switch value that is an exact identity is not honoured."""
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


# -- the operator probe ----------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="planned: WP42 D3, D5, D6")
@pytest.mark.parametrize("model", MODELS)
def test_ver71_no_solve_leaf_is_accepted_and_inert(model: str, meshes: dict[str, Path]) -> None:
    """Each perturbation is refused or moves the operator; inert is allowed only unrefusable.

    The one allowance is a leaf the schema requires, so it has no default to be
    refused away from, and that the model declares unread: ``poisson``'s
    ``electrolyte.concentration_M``.
    """
    from nanopnp.io.case_paths import schema_default

    reference = fingerprint(base(model, meshes))
    inert = []
    for path, value, document in probes(model, meshes):
        if outcome(document, reference) == "inert" and not (
            path in UNREAD[model] and not schema_default(path)[0]
        ):
            inert.append(f"{path}: {value!r}")
    assert not inert, f"{model} accepts and ignores {inert}"


@pytest.mark.xfail(strict=True, reason="planned: WP42 D3")
@pytest.mark.parametrize("model", MODELS)
def test_ver71_the_unread_leaves_are_inert_and_the_rest_are_not(
    model: str, meshes: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With D3's refusal lifted, a declared-unread leaf leaves the operator bit-identical.

    The other direction: a solve leaf the model does not declare unread is live or
    refused by another check, so the declaration neither hides a live leaf nor
    misses an inert one.
    """
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


def test_ver71_the_driver_is_live_for_any_but_two_unit_valence_species() -> None:
    """``ionic_strength`` differs from ``average`` once a valence is not one (PHY-13).

    The evidence for D6, and true before WP42: the driver is not a leaf no model
    reads, so it is refused from the electrolyte, for the one salt where
    ``I = 1/2 (c_1 + c_2) = <c>`` exactly. No shipped parameter file is
    multivalent, so the cation is made divalent in place, as WP41's PHY-13 test does.
    """
    from dataclasses import replace

    from nanopnp.materials.electrolyte import Electrolyte

    averaged = Electrolyte.from_parameter_file(WILLEMS, driver="average")
    ionic = Electrolyte.from_parameter_file(WILLEMS, driver="ionic_strength")
    samples = [800.0, 1600.0]  # mol/m^3, ordered as the species: 0.8 M and 1.6 M
    assert ionic.average_concentration(samples) == averaged.average_concentration(samples)
    divalent = (replace(ionic.ion("Na+"), valence=2), ionic.ion("Cl-"))
    assert replace(ionic, species=divalent).average_concentration(samples) == pytest.approx(2.4)
    assert replace(averaged, species=divalent).average_concentration(samples) == pytest.approx(1.2)


@pytest.fixture
def probe_solver() -> Iterator[str]:
    """Register a linear solver that stops the solve when it is first used."""
    from nanopnp.numerics import linear

    name = "ver71-probe"

    class ReachedError(Exception):
        pass

    class Probe:
        def solve(self, *args: object, **kwargs: object) -> None:
            raise ReachedError(name)

    linear.register_solver(name, Probe)
    try:
        yield name
    finally:
        del linear._REGISTRY[name]


@pytest.mark.xfail(strict=True, reason="planned: WP42 D3, D7")
@pytest.mark.parametrize("model", MODELS)
def test_ver71_the_newton_settings_reach_every_model_that_reads_them(
    model: str, meshes: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """``max_iter`` and ``rtol`` reach ``damped_newton``, or the model declares them unread.

    ``poisson`` and ``pb-linear`` take ``settings`` and never use it (their solve
    is one linear system), so D3 declares both leaves unread there.
    """
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
        run_ladder((prepared,))  # completes: no Newton iteration is reached
        return
    with pytest.raises(ReachedError) as reached:
        run_ladder((prepared,))
    settings = reached.value.args[0]
    assert settings.max_iterations == 37  # type: ignore[attr-defined]
    assert settings.relative_tolerance == 1e-7  # type: ignore[attr-defined]


@pytest.mark.xfail(strict=True, reason="planned: WP42 D7")
@pytest.mark.parametrize("model", MODELS)
def test_ver71_the_linear_solver_reaches_every_model(
    model: str, meshes: dict[str, Path], probe_solver: str
) -> None:
    """``numerics.linear.solver`` is read by every model: the probe solver is reached."""
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
    with pytest.raises(Exception, match=probe_solver):
        run_ladder((prepared,))


def _top_rung(resolved: ResolvedCase) -> Rung:
    """Return the rung a resolved case's solve ends on, built as stage 10 builds it."""
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


# -- the refusals, verbatim ------------------------------------------------------


def _refused(document: dict[str, Any]) -> str:
    """Return the text a document is refused with at resolution."""
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case, resolve

    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(yaml.safe_dump(document)))
    return str(raised.value)


@pytest.mark.xfail(strict=True, reason="planned: WP42 D3")
def test_ver71_unread_leaves_are_refused_naming_each_key_its_default_and_its_readers(
    meshes: dict[str, Path],
) -> None:
    """One message names every unread key the case sets, in schema order (WP42 Design §4)."""
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


@pytest.mark.xfail(strict=True, reason="planned: WP42 D6")
def test_ver71_a_correction_part_no_model_applies_is_refused(meshes: dict[str, Path]) -> None:
    """``wall: false`` on a property whose correction has no wall fit changes nothing (PHY-22)."""
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


@pytest.mark.xfail(strict=True, reason="planned: WP42 D6")
@pytest.mark.parametrize("model", ["epnp-ns", "pnp"])
def test_ver71_the_ionic_strength_driver_of_a_one_one_salt_is_refused(
    model: str, meshes: dict[str, Path]
) -> None:
    """For Na+ and Cl- the two drivers are one number, so the deviation is never applied."""
    assert _refused(put(base(model, meshes), "electrolyte.driver", "ionic_strength")) == (
        "electrolyte.driver: ionic_strength drives the corrections with I = 1/2 sum z_i^2 c_i, "
        "which equals the average concentration (c_1 + c_2)/2 for two species of unit "
        "valence, so it would be recorded in the manifest as a deviation and never change a "
        "number (PHY-13); leave it at its default, average"
    )


@pytest.mark.xfail(strict=True, reason="planned: WP42 D5")
def test_ver71_pnp_refuses_the_flow_switches_it_cannot_apply(meshes: dict[str, Path]) -> None:
    """REV-42: ``pnp`` refuses ``variable_density`` and ``inertia`` true, as ``pb`` does."""
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


@pytest.mark.xfail(strict=True, reason="planned: WP42 D8")
def test_ver71_a_flowless_model_is_refused_on_its_flow_switch_first(
    meshes: dict[str, Path],
) -> None:
    """REV-66: ``pb`` with ``flow`` left true and ``u: P1`` loads, and resolution names the switch.

    The load-time inf-sup check runs only for a model that reads
    ``numerics.elements.u``, so it no longer speaks first about a velocity
    ``pb`` never solves.
    """
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


@pytest.mark.xfail(strict=True, reason="planned: WP42 D4")
def test_ver71_a_fixed_leaf_is_refused_away_from_its_default(meshes: dict[str, Path]) -> None:
    """Each ``fixed`` leaf's alternative is refused at resolution, naming the leaf."""
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


@pytest.mark.xfail(strict=True, reason="planned: WP42 D4")
def test_ver71_a_provenance_leaf_moves_no_solve_key(meshes: dict[str, Path]) -> None:
    """``name`` reaches the case key and nothing the solve is keyed on (§5.3.2)."""
    from nanopnp.validation.case_leaves import LEAVES

    from nanopnp.pipeline.case import loads_case, resolve

    assert LEAVES["name"].kind == "provenance"
    left = resolve(loads_case(yaml.safe_dump(base("epnp-ns", meshes))))
    right = resolve(loads_case(yaml.safe_dump(put(base("epnp-ns", meshes), "name", "other"))))
    assert left.solve_provenance == right.solve_provenance

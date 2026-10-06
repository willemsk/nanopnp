"""VER-56: the physics-model interface is the only route to a model (FR-20, QR-14).

Section 5.4.3's NOTE makes the declaration and the built model's own members the
only things a layer outside ``physics/`` may read, so a model added as one class
runs from a case file to stage 12 with no other edit. Four claims are tested here,
each against something other than the code under test:

- **The source walk.** No module outside ``physics/`` names a concrete model
  class or compares with a registered model name; ``default_ladder`` is the one
  exemption, because NUM-18 defines the ladder as a path through named models.
  The detector is shown to fire on the code that *should* trip it, so it is not a
  gate that can only pass.
- **Refusals from the declaration.** Every refusal names the model, the key and
  what is admitted, so a reader can act on it without reading the declaration.
- **Nothing moved.** The stage-10 keys of the five pre-existing models,
  and the model of every rung of both ladders, equal goldens recorded from
  ``main`` at ``e58b2bf`` before any of this package's code existed (WP26 D5, D14).
- **One class is enough.** A forwarding model defined *here*, subclassing no
  shipped model and registered at run time, runs stages 10 to 12 and reproduces
  ``pnp`` bit for bit; and the electrostatic models, run from case files, equal
  direct API solves whose Debye length comes from an independent route.
"""

from __future__ import annotations

import ast
import json
import math
import subprocess
import sys
from collections.abc import Iterator, Mapping
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import nanopnp
from nanopnp.charge.stage import ResolvedFields, read_fields
from nanopnp.core.constants import thermal_voltage
from nanopnp.core.hashing import content_hash
from nanopnp.io.artefact import SOLUTION_SCHEMA
from nanopnp.io.case import CaseValidationError, loads_case, resolve
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.materials.corrections import load_corrections
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.adapter import from_ngsolve, write_msh41
from nanopnp.mesh.ingest import MeshVocabularyError, deployed_mesh, ingest, required_names
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.mesh.sizing import case_debye_length_nm
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
from nanopnp.physics.models import ModelSolution, PhysicsModel
from nanopnp.solve.continuation import default_ladder
from nanopnp.solve.state import WALL_DISTANCE_ENTRY, ladder, restore

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.typing import Mesh, Option
    from nanopnp.io.case import ResolvedCase
    from nanopnp.io.run import RunResult
    from nanopnp.numerics.measures import Measures

PACKAGE = Path(nanopnp.__file__).parent
REPOSITORY = PACKAGE.parents[1]
QUICKSTART = REPOSITORY / "examples" / "01-quickstart" / "quickstart.case.yaml"

MODEL_CLASSES = frozenset({"CoupledModel", "ElectrostaticModel", "PoissonModel", "COUPLED_MODELS"})
"""Identifiers a layer outside ``physics/`` must not name (section 5.4.3 NOTE)."""

LADDER = ("solve/continuation.py", "default_ladder")
"""The one function outside ``physics/`` that names models (WP26 D14, section 6.5)."""

DECLARED_DEFAULTS = (
    ("io/case.py", "PhysicsSpec"),
    ("io/defaults.py", "_VALIDATED_DEFAULTS"),
)
"""Where the validated model is *written down* as the default, which is data rather
than dispatch: the schema's default ``physics.model`` and the validated default case
every deviation is measured against (FR-25). Exempt from the literal rule only;
neither may compare with a model name or name a model class."""

SOLVE_HASHES = {
    "epnp-ns": "7434504618fd58078a25abfe6970248d459cbac8d58b2361d3ce8f023d64816f",
    "pnp-ns": "ed85c659de724e0e6e3492a606b9f618076ce50d64a0ecaf25236ea2b1284fb6",
    "pnp": "1026fed484cb761653d6b9e1195b9d4d8f05f3404a237446d4d1e0448d44887c",
    "pb": "9529a45cdcdca7c750ac077079f48854250f519bf7bdd84bb5bb96d505d402d9",
    "pb-linear": "c1e0439324e17f490ef29e3705a632924260c75dc84e8ebed0d30e50820381be",
}
"""``content_hash(SOLUTION_SCHEMA, solve_provenance)`` of the quick-start variants, on ``main``.

The stage-10 key itself. Its inputs are the case's own values -- no float in it is
computed -- so the digest is the same on every platform."""

_PB = "a650c1711b06be0508d6e15305084d6b32292c493370267f976757a8b0280913"
_PB_SINH = "52d0125c2bc5c2708d64af9833ed279c5daa705bd177dee19843cc12a5152266"
_EQUILIBRIUM = "231f3402154b4fbf1fd77eea0d0979dd6e7cbd1a4b92c248e0e2cbbb19a7f904"
_FLOW = "134f4b057928097ddd272026eb34a84b873d5e58c11fdce08222908634c11ea2"
_STERIC = "b3173a4bcdb1c084a0e208479c964b0294d7c1c466cd99f378c490a38249179f"
_BIAS = tuple((f"5-ramp-bias-+{mV}mV", _EQUILIBRIUM) for mV in (10, 20, 30, 40, 50))
_SALT = ("9-salt-0.05946M", "9-salt-0.07071M", "9-salt-0.08409M", "9-salt-0.1M")
RUNG_HASHES: dict[str, tuple[tuple[str, str], ...]] = {
    "epnp-ns": (
        ("1-pb-linear", _PB),
        ("2-pb", _PB_SINH),
        ("3-equilibrium-pnp", _EQUILIBRIUM),
        *_BIAS,
        ("6-flow", _FLOW),
        ("7-corrections", "59ab8e92e3df72436498bb55960322e1ac53532ab90b14f98e82250f6aeee478"),
        ("8-steric", _STERIC),
        *((name, _STERIC) for name in _SALT),
    ),
    "pnp-ns": (
        ("1-pb-linear", _PB),
        ("2-pb", _PB_SINH),
        ("3-equilibrium-pnp", _EQUILIBRIUM),
        *_BIAS,
        ("6-flow", _FLOW),
        *((name, _FLOW) for name in _SALT),
    ),
}
"""Each rung's name and the digest of its model's provenance less ``scales``, on ``main``.

``scales`` is left out because it carries computed floats (``lambda_D``, ``Pe``,
``Re``) whose last bit is the platform's ``libm``; its concentration is asserted
separately. Recorded from a worktree of ``e58b2bf`` and confirmed equal on this
branch (WP26 Outcomes)."""


# -- the source walk -----------------------------------------------------------


def _registered_names() -> frozenset[str]:
    return frozenset(models.registered_models())


def _lines_of(tree: ast.Module, relative: str, scopes: tuple[tuple[str, str], ...]) -> set[int]:
    """Return the lines of every named function, class or assignment ``scopes`` exempts here."""
    wanted = {name for path, name in scopes if path == relative}
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            names = {node.name}
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {target.id for target in targets if isinstance(target, ast.Name)}
        else:
            continue
        if names & wanted:
            lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def _docstrings(tree: ast.Module) -> set[int]:
    """Return the ids of every bare string statement: docstrings, which dispatch nothing."""
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }


def _constants(node: ast.AST) -> Iterator[object]:
    """Yield the constants one comparison operand holds, looking inside a literal collection."""
    if isinstance(node, ast.Constant):
        yield node.value
    elif isinstance(node, ast.Tuple | ast.List | ast.Set):
        for element in node.elts:
            yield from _constants(element)


def model_dispatch(source: str, relative: str, *, exempt: bool = True) -> list[str]:
    """Return every place ``source`` names a model, its class, or compares with a model name.

    Three rules. No identifier of :data:`MODEL_CLASSES`, anywhere. No comparison
    or ``match`` against a registered model name. And no registered model name as
    a string literal at all, docstrings aside -- stricter than the comparison
    rule, because a name passed to ``create`` or kept in a table is dispatch one
    step removed. :data:`LADDER` is exempt from all three and
    :data:`DECLARED_DEFAULTS` from the third.
    """
    tree = ast.parse(source)
    ladder = _lines_of(tree, relative, (LADDER,)) if exempt else set()
    defaults = _lines_of(tree, relative, DECLARED_DEFAULTS) if exempt else set()
    documentation = _docstrings(tree)
    names = _registered_names()
    found: list[str] = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", None)
        if line in ladder:
            continue
        if isinstance(node, ast.Name) and node.id in MODEL_CLASSES:
            found.append(f"{relative}:{line}: names {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr in MODEL_CLASSES:
            found.append(f"{relative}:{line}: names {node.attr}")
        elif isinstance(node, ast.ImportFrom):
            found += [
                f"{relative}:{line}: imports {alias.name}"
                for alias in node.names
                if alias.name in MODEL_CLASSES
            ]
        elif isinstance(node, ast.Compare):
            for operand in (node.left, *node.comparators):
                hits = sorted({value for value in _constants(operand) if value in names})
                found += [f"{relative}:{line}: compares with {hit!r}" for hit in hits]
        elif isinstance(node, ast.MatchValue):
            found += [
                f"{relative}:{line}: matches {value!r}"
                for value in _constants(node.value)
                if value in names
            ]
        elif (
            isinstance(node, ast.Constant)
            and node.value in names
            and id(node) not in documentation
            and line not in defaults
        ):
            found.append(f"{relative}:{line}: spells the model name {node.value!r}")
    return found


def test_ver56_no_layer_outside_physics_names_a_model_or_its_class() -> None:
    """Section 5.4.3 NOTE: layers read declarations, never names or classes."""
    found: list[str] = []
    walked = 0
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE).as_posix()
        if relative.startswith("physics/"):
            continue
        walked += 1
        found += model_dispatch(path.read_text(encoding="utf-8"), relative)
    assert walked > 50, "the walk found too few modules to be walking the package"
    assert not found, "\n".join(found)


def test_ver56_the_source_walk_fires_where_it_should() -> None:
    """The detector is not a gate that can only pass.

    It fires on the registry itself, on each shape of dispatch it claims to catch,
    and on every exempt scope once the exemption is lifted -- which also shows
    each exemption is not vacuous.
    """
    registry = (PACKAGE / "physics" / "models.py").read_text(encoding="utf-8")
    assert model_dispatch(registry, "physics/models.py")
    for snippet in (
        'if resolved.model == "pnp":\n    pass',
        'if model in ("epnp-ns", "pnp-ns"):\n    pass',
        "isinstance(model, CoupledModel)",
        "from nanopnp.physics.models import ElectrostaticModel",
        "import nanopnp.physics.models as m\nm.PoissonModel",
        'match name:\n    case "pb":\n        pass',
        'model = create("poisson", order=2)',
    ):
        assert model_dispatch(snippet, "snippet.py"), snippet
    assert not model_dispatch('"""The pnp model."""\nx = 1', "snippet.py")
    for relative, _ in (LADDER, *DECLARED_DEFAULTS):
        source = (PACKAGE / relative).read_text(encoding="utf-8")
        assert model_dispatch(source, relative, exempt=False), relative
        assert not model_dispatch(source, relative), relative


# -- refusals from the declaration ----------------------------------------------


ELECTROSTATIC_PHYSICS = "{model: %s, flow: false, variable_density: false, inertia: false}"


def case_text(
    mesh: Path | str = "absent.msh",
    *,
    physics: str = "{model: epnp-ns, solid_permittivities: {membrane: 3.2}}",
    continuation: str = "none",
    outputs: str = "[current]",
    inputs: str = "",
    groups: str = "",
    name: str = "interface",
) -> str:
    """Return a case over ``mesh`` with the given physics, strategy and outputs."""
    mapping = f", groups: {groups}" if groups else ""
    return f"""
schema: nanopnp/case/v2
name: {name}
inputs:
  mesh: {{path: {mesh}, format: msh41{mapping}}}{inputs}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {physics}
numerics: {{continuation: {continuation}}}
outputs: {outputs}
"""


def _refusal(text: str) -> str:
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    return str(raised.value)


def test_ver56_an_unhonoured_switch_is_refused_naming_model_key_and_values() -> None:
    """``pnp`` honours ``flow: false`` only (PHY-21), and says who honours ``true``."""
    message = _refusal(case_text(physics="{model: pnp, solid_permittivities: {membrane: 3.2}}"))
    assert "'pnp'" in message and "physics.flow" in message
    assert "physics.flow must be false" in message
    assert "epnp-ns, pnp-ns" in message


def test_ver56_solids_beside_a_model_without_them_are_refused() -> None:
    """``pb`` carries no solids; ``poisson`` does, and the message says so (PHY-21 NOTE)."""
    physics = "{model: pb, flow: false, variable_density: false, inertia: false, "
    message = _refusal(
        case_text(physics=physics + "solid_permittivities: {membrane: 3.2}}", outputs="[]")
    )
    assert "'pb'" in message and "physics.solid_permittivities" in message
    assert "poisson" in message


@pytest.mark.parametrize(
    ("model", "supplied"),
    [("pb", "charge"), ("pb-linear", "charge"), ("pb", "eps_r"), ("pb-linear", "eps_r")],
)
def test_phy24_a_supplied_field_beside_poisson_boltzmann_is_refused(
    model: str, supplied: str
) -> None:
    """Poisson-Boltzmann takes no fixed charge and no permittivity field (PHY-24)."""
    inputs = f"\n  {supplied}: {{path: field.yaml, format: field1}}"
    message = _refusal(
        case_text(physics=ELECTROSTATIC_PHYSICS % model, outputs="[]", inputs=inputs)
    )
    assert f"'{model}'" in message and f"inputs.{supplied}" in message
    assert "poisson" in message and "epnp-ns" in message


def test_ver56_an_unadmitted_strategy_is_refused_naming_the_admitted_values() -> None:
    """``pnp`` admits ``continuation: none`` only, as section 6.5 already forces."""
    message = _refusal(
        case_text(
            physics="{model: pnp, flow: false, solid_permittivities: {membrane: 3.2}}",
            continuation="default_ladder",
        )
    )
    assert "'pnp'" in message and "numerics.continuation: none" in message
    assert "epnp-ns, pnp-ns" in message


@pytest.mark.parametrize(
    ("physics", "outputs", "named", "declared"),
    [
        (ELECTROSTATIC_PHYSICS % "poisson", "[current]", "current", "no quantity of interest"),
        (ELECTROSTATIC_PHYSICS % "pb", "[transport_numbers, fields]", "transport_numbers", "no"),
        (
            "{model: pnp, flow: false, solid_permittivities: {membrane: 3.2}}",
            "[current, eof_rate]",
            "eof_rate",
            "current, transport_numbers, rectification",
        ),
    ],
)
def test_ver56_an_undeclared_quantity_is_refused_when_the_case_is_resolved(
    physics: str, outputs: str, named: str, declared: str
) -> None:
    """Section 5.3.1 NOTE on ``outputs:``: refused at resolve time, not at stage 11."""
    message = _refusal(case_text(physics=physics, outputs=outputs))
    assert named in message and declared in message
    assert f"'{physics.split(',')[0].split(': ')[1].rstrip('}')}'" in message


def test_ver56_fields_is_admitted_for_every_model() -> None:
    """``fields`` is the IF-07 export, not a quantity (section 5.3.1 NOTE)."""
    for model in ("pb", "pb-linear", "poisson"):
        resolved = resolve(
            loads_case(case_text(physics=ELECTROSTATIC_PHYSICS % model, outputs="[fields]"))
        )
        assert resolved.outputs == ("fields",)


def test_ver56_a_builder_refusal_is_re_raised_naming_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WP26 D10: resolve builds the model once, and a builder's own refusal is a case error."""

    def refuse(**_: object) -> PhysicsModel:
        raise ValueError("this configuration is refused for a reason of its own")

    monkeypatch.setitem(
        models._REGISTRY,
        "refusing",
        models._Registration(builder=refuse, declaration=models.declaration("pb")),
    )
    message = _refusal(case_text(physics=ELECTROSTATIC_PHYSICS % "refusing", outputs="[]"))
    assert "physics.model 'refusing'" in message
    assert "for a reason of its own" in message


def _divalent() -> Electrolyte:
    """Return the NaCl parameter file's electrolyte with the cation made divalent."""
    salt = Electrolyte.from_parameter_file("willems2020_nacl")
    return replace(salt, species=(replace(salt.species[0], valence=2), salt.species[1]))


def test_fr19_poisson_boltzmann_refuses_a_salt_that_is_not_symmetric_monovalent() -> None:
    """``lambda_D`` with unit valence and ``sinh`` are exact for a 1:1 salt only (PHY-21 NOTE)."""
    divalent = _divalent()
    for name in ("pb", "pb-linear"):
        with pytest.raises(ValueError, match=r"symmetric monovalent.*z = \+2"):
            models.create(name, electrolyte=divalent)
    assert models.create("poisson", electrolyte=divalent).name == "poisson"


def test_fr19_the_ladder_initialisers_state_their_own_debye_length_for_any_salt() -> None:
    """NUM-18's stages 1 and 2 are initialisers with their own ``lambda_D``, not case models.

    Built through the registry they must take every electrolyte the ladder
    takes: the refusal is of the case's *default* ``lambda_D``, which a
    stated one replaces.
    """
    divalent = _divalent()
    stated = models.create("pb", electrolyte=divalent, debye_length_nm=0.5)
    assert isinstance(stated, models.ElectrostaticModel)
    assert stated.debye_length_nm == 0.5
    with pytest.raises(ValueError, match="finite and positive"):
        models.create("pb-linear", debye_length_nm=0.0)
    mesh = CylindricalPoreGeometry().generate(maxh_nm=4.0)
    rungs = default_ladder(mesh, electrolyte=divalent, solid_permittivities={"membrane": 3.2})
    assert [rung.model.name for rung in rungs[:2]] == ["pb-linear", "pb"]


def test_ver56_a_declaration_cannot_admit_a_ladder_that_does_not_end_at_it() -> None:
    """Section 6.5: the ladder ends at ``epnp-ns`` or ``pnp-ns``, so no other may admit it.

    Refused at registration, and nothing is registered: case validation would
    otherwise admit ``default_ladder`` and stage 10 refuse to build it.
    """
    with pytest.raises(ValueError, match="ends at epnp-ns or pnp-ns"):
        models.register_model(
            "laddered", lambda **_: models.create("pnp-ns"), models.declaration("epnp-ns")
        )
    assert "laddered" not in models.registered_models()


def test_ver56_a_builder_must_build_the_model_it_is_registered_as(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The declaration is found by the built model's name, so ``create`` insists they agree."""
    monkeypatch.setitem(
        models._REGISTRY,
        "misnamed",
        models._Registration(
            builder=lambda **options: models.create("pnp", **options),
            declaration=models.declaration("pnp"),
        ),
    )
    with pytest.raises(ValueError, match="built a model named 'pnp'"):
        models.create("misnamed")


def test_ver56_a_model_without_solids_is_refused_a_generated_mesh() -> None:
    """Every generated region carries a membrane and a protein (PHY-21 NOTE).

    So the refusal is the case's, made when it is resolved, and not the stage-6
    gate's after the mesh has been built.
    """
    text = case_text(physics=ELECTROSTATIC_PHYSICS % "pb", outputs="[]").replace(
        "mesh: {path: absent.msh, format: msh41}", "profile: {path: absent.yaml}"
    )
    message = _refusal(text)
    assert "'pb'" in message and "inputs.mesh" in message and "poisson" in message


def test_ver56_the_declared_switches_are_not_shared_between_declarations() -> None:
    """A declaration copies its switches, so one mapping cannot move two models."""
    shared = {name: (False,) for name in models.SWITCHES}
    first = models.ModelDeclaration(options=(), switches=shared, solids=False)
    shared["flow"] = (False, True)
    assert first.switches["flow"] == (False,)


def test_ver56_building_a_model_while_resolving_imports_no_backend() -> None:
    """WP26 D10: resolve builds every model, and the CLI's import budget must survive it."""
    script = f"""
import sys
from nanopnp.io.case import loads_case, resolve
texts = {[case_text(), case_text(physics=ELECTROSTATIC_PHYSICS % "pb", outputs="[]")]!r}
texts.append({case_text(physics=ELECTROSTATIC_PHYSICS % "poisson", outputs="[]")!r})
for text in texts:
    resolve(loads_case(text))
print(sorted(name for name in ("ngsolve", "netgen") if name in sys.modules))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert completed.stdout.strip() == "[]", completed.stderr


# -- nothing moved -------------------------------------------------------------


def _quickstart_variants() -> dict[str, str]:
    """Return the quick-start case as each of the five pre-existing models."""
    base = QUICKSTART.read_text(encoding="utf-8")
    electrostatic = (
        base.replace(
            "  solid_permittivities: {membrane: 3.2}\n",
            "  flow: false\n  variable_density: false\n  inertia: false\n",
        )
        .replace("continuation: default_ladder", "continuation: none")
        .replace("outputs: [current, transport_numbers, eof_rate]", "outputs: []")
    )
    return {
        "epnp-ns": base,
        "pnp-ns": base.replace("model: epnp-ns", "model: pnp-ns"),
        # ``outputs`` is outside the solve key, so the word ``pnp`` cannot provide
        # is replaced without moving the digest.
        "pnp": base.replace("model: epnp-ns", "model: pnp\n  flow: false")
        .replace("continuation: default_ladder", "continuation: none")
        .replace("eof_rate]", "rectification]"),
        "pb": electrostatic.replace("model: epnp-ns", "model: pb"),
        "pb-linear": electrostatic.replace("model: epnp-ns", "model: pb-linear"),
    }


@pytest.mark.parametrize("model", sorted(SOLVE_HASHES))
def test_ver56_the_stage_ten_key_of_each_model_is_the_one_main_recorded(model: str) -> None:
    """WP26 D5: ``model_options`` is filtered by the declaration and did not move."""
    resolved = resolve(loads_case(_quickstart_variants()[model]))
    assert content_hash(SOLUTION_SCHEMA, resolved.solve_provenance) == SOLVE_HASHES[model]


@pytest.mark.parametrize("model", sorted(RUNG_HASHES))
def test_ver56_every_ladder_rung_builds_the_model_main_built(model: str) -> None:
    """WP26 D14: the rungs are built through ``create`` and are the rungs of ``main``."""
    resolved = resolve(loads_case(_quickstart_variants()[model]))
    mesh = CylindricalPoreGeometry().generate(maxh_nm=4.0)
    empty = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
    rungs = ladder(resolved, mesh, AXISYMMETRIC, SATURATED_WALL_DISTANCE_NM, empty)
    found = tuple(
        (
            rung.name,
            content_hash(
                SOLUTION_SCHEMA,
                {key: value for key, value in rung.model.provenance.items() if key != "scales"},
            ),
        )
        for rung in rungs
    )
    assert found == RUNG_HASHES[model]
    # The top rung is the case's own model (D14), at the case's concentration.
    assert rungs[-1].model.name == model
    assert rungs[-1].model.scales.concentration_M == pytest.approx(0.1, rel=1e-12)


# -- one class is enough -------------------------------------------------------


class ForwardingModel:
    """``pnp``, reached through a class no shipped model shares.

    It subclasses nothing, forwards every member it does not define to the model
    it wraps, and answers to its own registered name, so every layer that reads it
    reads it through the section 5.4.3 interface -- a ``getattr`` is all it offers.
    """

    def __init__(self, inner: PhysicsModel) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        """The registered name, which is how the declaration is found."""
        return FORWARDING

    @property
    def provenance(self) -> Mapping[str, Any]:
        """The wrapped model's record, under this model's name."""
        return {**self._inner.provenance, "model": FORWARDING}

    def solve(self, mesh: Mesh, measures: Measures, **kwargs: Option) -> ModelSolution:
        """Solve the wrapped model and hand back a solution that names this one."""
        solution = self._inner.solve(mesh, measures, **kwargs)
        return replace(solution, model=self)

    def __getattr__(self, attribute: str) -> Option:
        """Forward every other member to the wrapped model."""
        return getattr(self._inner, attribute)


FORWARDING = "forwarding-pnp"


@pytest.fixture
def forwarding_model() -> Iterator[str]:
    """Register :class:`ForwardingModel` for one test, with ``pnp``'s declaration."""
    models.register_model(
        FORWARDING,
        lambda **options: ForwardingModel(models.create("pnp", **options)),
        models.declaration("pnp"),
    )
    try:
        yield FORWARDING
    finally:
        del models._REGISTRY[FORWARDING]


@pytest.fixture(scope="module")
def pore_mesh(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the quick-start pore, as ``nanopnp mesh cylinder`` writes it with its defaults."""
    generated = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=0.35, check_quality=False)
    return write_msh41(from_ngsolve(generated), tmp_path_factory.mktemp("pore") / "pore.msh")


def _run(text: str, directory: Path) -> RunResult:
    """Run a case file through stage 12 in its own store, and return the run."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "case.yaml"
    path.write_text(text, encoding="utf-8")
    return run_case(path, store=Store(directory / "store"), workspace=directory / "work")


def _state(result: RunResult) -> dict[str, np.ndarray]:
    """Return the stage-10 payload's arrays, by name."""
    import numpy as np

    with np.load(result.artefacts["solve"].payload["state"], allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files if name.startswith("field.")}


def test_ver56_a_model_defined_as_one_class_runs_from_a_case_file_to_stage_twelve(
    forwarding_model: str, pore_mesh: Path, tmp_path: Path
) -> None:
    """FR-20, QR-14: one class and a registration, and every layer serves it.

    The state and the stage-11 summary equal ``pnp``'s on the same case bit for
    bit, and the model stage 11 restores is the wrapper, not the model it wraps.
    """
    import numpy as np

    physics = "{model: %s, flow: false, solid_permittivities: {membrane: 3.2}}"
    texts = {
        name: case_text(
            pore_mesh,
            physics=physics % name,
            outputs="[current, transport_numbers, fields]",
            groups="{default: interface}",
            name=f"interface-{name}",
        )
        for name in ("pnp", forwarding_model)
    }
    runs = {name: _run(text, tmp_path / name) for name, text in texts.items()}

    reference, forwarded = runs["pnp"], runs[forwarding_model]
    assert [record.name for record in forwarded.stages][-3:] == ["solve", "qoi", "report"]
    assert forwarded.artefacts["qoi"].summary == reference.artefacts["qoi"].summary
    assert forwarded.artefacts["report"].summary["exports"] == ["fields"]
    states = {name: _state(run) for name, run in runs.items()}
    assert sorted(states["pnp"]) == sorted(states[forwarding_model])
    for field, values in states["pnp"].items():
        assert np.array_equal(values, states[forwarding_model][field]), field

    restored = restore(
        Path(forwarded.artefacts["solve"].payload["state"]),
        case=loads_case(texts[forwarding_model]),
    )
    assert type(restored.model) is ForwardingModel


def test_ver56_pnp_ns_beside_corrections_it_overrides_runs_and_restores(
    pore_mesh: Path, tmp_path: Path
) -> None:
    """VER-56: whether ``d`` is read is asked of the built model, not of the case.

    ``pnp-ns`` resolves every correction to ``none`` whatever the case gives, so
    the quick-start case as ``pnp-ns`` -- its corrections on, the schema default
    -- reads no distance field. Asked of the case's electrolyte, the solve then
    paid for a field no term evaluated, and ``save`` refused the converged state
    on the ladder and on the single rung alike. Now both run to stage 12, store
    no distance field, restore, and equal the same case with every correction
    written as ``none`` bit for bit.
    """
    import numpy as np

    quickstart = (
        QUICKSTART.read_text(encoding="utf-8")
        .replace("model: epnp-ns", "model: pnp-ns")
        .replace("path: pore.msh", f"path: {pore_mesh}")
    )
    classical = quickstart.replace("{model: willems2020_nacl}", "{model: none}").replace(
        "{model: borukhov}", "{model: none}"
    )
    assert classical.count("{model: none}") == 6
    texts = {
        "ladder": quickstart,
        "single": quickstart.replace("continuation: default_ladder", "continuation: none"),
        "classical": classical,
    }
    runs = {name: _run(text, tmp_path / name) for name, text in texts.items()}
    for name, result in runs.items():
        state = Path(result.artefacts["solve"].payload["state"])
        with np.load(state, allow_pickle=False) as archive:
            assert WALL_DISTANCE_ENTRY not in archive.files, name
        restore(state, case=loads_case(texts[name]))
    assert runs["ladder"].artefacts["qoi"].summary == runs["classical"].artefacts["qoi"].summary


# -- the electrostatic models from case files ---------------------------------


def _slab(path: Path, *, membrane: tuple[float, float] | None) -> Path:
    """Write ``r in [0, 4]``, ``z in [0, 10]`` nm, with a membrane band if one is asked for.

    ``cis`` at ``z = 10`` and ``trans`` at ``z = 0``, so the bias is applied across
    the slab; the membrane, where present, spans the whole radius, so its faces
    are seams of the glued faces and its rim is ``membrane_outer``.
    """
    import netgen.occ as occ
    import ngsolve as ngs

    radius, length = 4.0, 10.0
    if membrane is None:
        faces = [occ.Rectangle(radius, length).Face()]
        faces[0].name = "electrolyte"
    else:
        lower, upper = membrane
        faces = [
            occ.Rectangle(radius, lower).Face(),
            occ.MoveTo(0.0, lower).Rectangle(radius, upper - lower).Face(),
            occ.MoveTo(0.0, upper).Rectangle(radius, length - upper).Face(),
        ]
        for face, material in zip(faces, ("electrolyte", "membrane", "electrolyte"), strict=True):
            face.name = material
    shape = occ.Glue(faces) if len(faces) > 1 else faces[0]
    for edge in shape.edges:
        r, z = edge.center[0], edge.center[1]
        if abs(r) < 1e-9:
            edge.name = "axis"
        elif abs(z) < 1e-9:
            edge.name = "trans"
        elif abs(z - length) < 1e-9:
            edge.name = "cis"
        elif abs(r - radius) < 1e-9:
            inside = membrane is not None and membrane[0] < z < membrane[1]
            edge.name = "membrane_outer" if inside else "wall"
        else:
            edge.name = "interface"
    mesh = ngs.Mesh(occ.OCCGeometry(shape, dim=2).GenerateMesh(maxh=0.15))
    return write_msh41(from_ngsolve(mesh), path)


RING_CENTRE_NM = (2.0, 4.0)
RING_WIDTH_NM = 0.3
RING_CHARGE_E = -3.0e7
"""A ring of ``rho = q/(pi w^2) exp(-|x - x0|^2/w^2)`` read as a *volume* density.

``q`` is chosen so the peak, about 1.7e7 C m^-3, is of the order of the charge
scale ``eps_0 eps_r,f^0 V_T / a^2`` (1.8e7 C m^-3): large enough that the
solution with it differs from the one without it, which is asserted, so the
comparison below is not met by a vanishing source. Its radially weighted integral
is ``2 pi r0 q`` in the grid's metres, which ``q_net_e`` states."""


def _field_document(path: Path) -> Path:
    r0, z0 = RING_CENTRE_NM
    q_net_e = 2.0 * math.pi * r0 * 1e-9 * RING_CHARGE_E
    path.write_text(
        f"""
schema: nanopnp/field/v1
name: volume-ring
quantity: volume_charge_density
units: C/m^3
q_net_e: {q_net_e!r}
provenance: {{source: analytic}}
form:
  name: gaussian_ring
  parameters:
    {{centre_r_nm: {r0}, centre_z_nm: {z0}, width_nm: {RING_WIDTH_NM}, charge_e: {RING_CHARGE_E}}}
  origin_nm: [0.0, 0.0]
  spacing_nm: [0.01, 0.01]
  shape: [450, 900]
""",
        encoding="utf-8",
    )
    return path


def _direct(
    text: str,
    *,
    debye_length_nm: float | None = None,
    charged: bool = True,
) -> tuple[ResolvedCase, ModelSolution]:
    """Solve the case's model through the API alone, on the mesh the case deploys."""
    resolved = resolve(loads_case(text))
    mesh = deployed_mesh(resolved, None).mesh
    model = models.create(
        resolved.model,
        electrolyte=resolved.electrolyte,
        concentration_M=resolved.concentration_M,
        **resolved.model_options,
    )
    keywords: dict[str, Any] = {
        "potential_values": mesh.BoundaryCF(
            {"cis": 0.0, "trans": resolved.bias_V / thermal_voltage(resolved.temperature_K)}
        )
    }
    if debye_length_nm is not None:
        keywords["debye_length_nm"] = debye_length_nm
    if charged and resolved.charge is not None:
        charge = read_fields(resolved).charge
        assert charge is not None
        keywords["fixed_charge"] = charge.assemble(model.scales)
    return resolved, model.solve(mesh, AXISYMMETRIC, **keywords)


def _relative(case: np.ndarray, direct: np.ndarray) -> float:
    import numpy as np

    return float(np.max(np.abs(case - direct)) / np.max(np.abs(direct)))


def test_fr19_pb_linear_from_a_case_file_equals_the_api_solve(tmp_path: Path) -> None:
    """VER-56: ``pb-linear`` runs on a solid-free slab, with the case's ``lambda_D``.

    The API solve is handed ``lambda_D`` from :func:`~nanopnp.mesh.sizing.
    case_debye_length_nm` -- the ionic strength read off the case document -- which
    is a different route from the model's own scale set, so the two agreeing says
    the model's default is the case's Debye length and not merely itself.
    """
    import numpy as np

    mesh = _slab(tmp_path / "slab.msh", membrane=None)
    text = case_text(mesh, physics=ELECTROSTATIC_PHYSICS % "pb-linear", outputs="[fields]")
    run = _run(text, tmp_path / "run")
    assert run.artefacts["qoi"].summary == {"bias_V": 0.05}
    assert run.artefacts["report"].summary["exports"] == ["fields"]

    document = loads_case(text)
    eps_r0 = load_corrections(document.electrolyte.parameters).solvent.permittivity.eps_r0
    debye_nm = case_debye_length_nm(document, permittivity_0=eps_r0)
    _, direct = _direct(text, debye_length_nm=debye_nm)
    assert direct.model.scales.debye_length_nm == pytest.approx(debye_nm, rel=1e-12)
    case_state = _state(run)["field.potential"]
    assert _relative(case_state, np.asarray(direct.state.vec.FV().NumPy())) < 1e-12


def test_ver56_poisson_with_solids_and_a_supplied_charge_equals_the_api_solve(
    tmp_path: Path,
) -> None:
    """VER-56, PHY-20: ``poisson`` carries a membrane and ``inputs.charge`` from a case file.

    Equal to the API solve handed ``fields.charge.assemble(scales)`` to 1e-12, and
    measurably different from the uncharged solve, so the agreement is about the
    charge path and not about the bias alone.
    """
    import numpy as np

    mesh = _slab(tmp_path / "slab.msh", membrane=(6.5, 8.0))
    field = _field_document(tmp_path / "field.yaml")
    physics = (
        "{model: poisson, flow: false, variable_density: false, inertia: false, "
        "solid_permittivities: {membrane: 3.2}}"
    )
    inputs = f"\n  charge: {{path: {field}, format: field1}}"
    text = case_text(mesh, physics=physics, outputs="[fields]", inputs=inputs)
    run = _run(text, tmp_path / "run")
    assert run.artefacts["report"].summary["exports"] == ["fields"]

    _, direct = _direct(text)
    _, uncharged = _direct(text, charged=False)
    case_state = _state(run)["field.potential"]
    charged_state = np.asarray(direct.state.vec.FV().NumPy())
    assert _relative(case_state, charged_state) < 1e-12
    assert _relative(np.asarray(uncharged.state.vec.FV().NumPy()), charged_state) > 1e-3


def test_ver56_the_mesh_gate_refuses_a_solid_under_a_model_without_solids(
    pore_mesh: Path,
) -> None:
    """WP26 D12: the abort names the model and the domain, not a missing entry."""
    text = case_text(
        pore_mesh,
        physics=ELECTROSTATIC_PHYSICS % "pb",
        outputs="[]",
        groups="{default: interface}",
    )
    resolved = resolve(loads_case(text))
    assert resolved.mesh is not None
    with pytest.raises(
        MeshVocabularyError, match="cannot be posed on a mesh with a solid"
    ) as raised:
        ingest(resolved.mesh, resolved)
    assert "'pb'" in str(raised.value) and "'membrane'" in str(raised.value)


@pytest.mark.parametrize(
    ("physics", "concentration", "no_slip", "sources"),
    [
        ("{model: epnp-ns, solid_permittivities: {membrane: 3.2}}", True, True, True),
        ("{model: pnp, flow: false, solid_permittivities: {membrane: 3.2}}", True, False, True),
        (ELECTROSTATIC_PHYSICS % "poisson", False, False, False),
        (ELECTROSTATIC_PHYSICS % "pb", False, False, False),
    ],
)
def test_ver56_the_mesh_asks_for_what_the_model_declares(
    physics: str, concentration: bool, no_slip: bool, sources: bool
) -> None:
    """WP26 D12: essential sets from the built model, distance sources by declaration."""
    outputs = "[current]" if concentration else "[]"
    resolved = resolve(loads_case(case_text(physics=physics, outputs=outputs)))
    purposes = [requirement.purpose for requirement in required_names(resolved).boundaries]
    assert any("essential potential" in purpose for purpose in purposes)
    assert any("c_Na+" in purpose for purpose in purposes) is concentration
    assert any("no-slip" in purpose for purpose in purposes) is no_slip
    assert any("PHY-02" in purpose for purpose in purposes) is sources


def test_ver56_the_declarations_are_readable_without_building() -> None:
    """D1: one declaration per name, and ``pnp`` differs from its class-mates in it."""
    for name in models.registered_models():
        declared = models.declaration(name)
        assert json.dumps(sorted(declared.switches)) == json.dumps(sorted(models.SWITCHES))
    assert models.declaration("pnp").switches["flow"] == (False,)
    assert models.declaration("pnp").strategies == ("none",)
    assert models.declaration("epnp-ns").strategies == ("default_ladder", "none")
    assert models.declaration("poisson").coefficients == models.COEFFICIENTS
    assert not models.declaration("pb").solids
    with pytest.raises(KeyError, match="registered models are"):
        models.declaration("no-such-model")

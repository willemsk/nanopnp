"""VER-56: the physics-model interface is the only route to a model (FR-20, QR-14)."""

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
import yaml

import nanopnp
from nanopnp.charge.stage import ResolvedFields, read_fields
from nanopnp.core.constants import thermal_voltage
from nanopnp.core.hashing import content_hash
from nanopnp.io.artefact import SOLUTION_SCHEMA
from nanopnp.io.case import CaseValidationError
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
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.pipeline.run import run_case
from nanopnp.solve.continuation import default_ladder
from nanopnp.solve.state import WALL_DISTANCE_ENTRY, ladder, restore

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.typing import Mesh, Option
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.numerics.measures import Measures
    from nanopnp.pipeline.run import RunResult

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
    "epnp-ns": "06ca76fe4d784fee0b8807fe38463c48ef352cb56cd55f85cb8c588da458b49f",
    "pnp-ns": "8ddd174fa485c4a12ea62298a97f1d0dcc0f1a3553f94638c45a52e289c636bf",
    "pnp": "a64f5e0bfff5e8bab4e1a38eac38658a0c6fe06e911d94de032c0e2c7769a7c8",
    "pb": "87fc20a545d188b213399952244ef2202d2e51eeba9e3debf051d20a9a5401dc",
    "pb-linear": "45bbe8e49914417576c3d2fa45b06652f48e8bd0d3fff16e04722df81e417497",
}
"""``content_hash(SOLUTION_SCHEMA, solve_provenance)`` of the quick-start variants,
re-recorded in WP42, and again when the key gained
``field_floor_ratio`` and ``algorithm_revision`` (REV-71).

The stage-10 key itself. Its inputs are the case's own values -- no float in it is
computed -- so the digest is the same on every platform."""

_PB = "e3e283c19d22981885507c78f84d525e032b48b4da15203f26dc3c19ce713137"
_PB_SINH = "9b707ed86894cf206ce882d1f6dc10077c6ee97e908fae648f0078112f5a53e5"
_EQUILIBRIUM = "d99735b23fcb2acc60cec4dffff20ec44248868ef923d97a67286796f8f554d7"
_FLOW = "83e3acf8ea0d12adf072e82b6776c0b83fbcd8b00b9f53f92b53886c368d72de"
_STERIC = "341fc8f45a8f56c990cc03dc385973956a705b387a0a3e7ed67464028d464638"
_BIAS = tuple((f"5-ramp-bias-+{mV}mV", _EQUILIBRIUM) for mV in (10, 20, 30, 40, 50))
_SALT = ("9-salt-0.05946M", "9-salt-0.07071M", "9-salt-0.08409M", "9-salt-0.1M")
RUNG_HASHES: dict[str, tuple[tuple[str, str], ...]] = {
    "epnp-ns": (
        ("1-pb-linear", _PB),
        ("2-pb", _PB_SINH),
        ("3-equilibrium-pnp", _EQUILIBRIUM),
        *_BIAS,
        ("6-flow", _FLOW),
        ("7-corrections", "f8e0bceb65d611b2997a5fe1d576cab039870b38e5f655f5110670719f8b1031"),
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


def _registered_names() -> frozenset[str]:
    return frozenset(models.registered_models())


def _lines_of(tree: ast.Module, relative: str, scopes: tuple[tuple[str, str], ...]) -> set[int]:
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
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }


def _constants(node: ast.AST) -> Iterator[object]:
    if isinstance(node, ast.Constant):
        yield node.value
    elif isinstance(node, ast.Tuple | ast.List | ast.Set):
        for element in node.elts:
            yield from _constants(element)


def model_dispatch(source: str, relative: str, *, exempt: bool = True) -> list[str]:
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
    mapping = f", groups: {groups}" if groups else ""
    return f"""
schema: nanopnp/case/v0.5
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


# PHY-21
def test_ver56_an_unhonoured_switch_is_refused_naming_model_key_and_values() -> None:
    message = _refusal(
        case_text(physics="{model: pnp, flow: true, solid_permittivities: {membrane: 3.2}}")
    )
    assert "'pnp'" in message and "physics.flow" in message
    assert "physics.flow must be false" in message
    assert "epnp-ns, pnp-ns" in message


# PHY-21
def test_ver56_solids_beside_a_model_without_them_are_refused() -> None:
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
    inputs = f"\n  {supplied}: {{path: field.yaml, format: field1}}"
    message = _refusal(
        case_text(physics=ELECTROSTATIC_PHYSICS % model, outputs="[]", inputs=inputs)
    )
    assert f"'{model}'" in message and f"inputs.{supplied}" in message
    assert "poisson" in message and "epnp-ns" in message


def test_ver56_an_unadmitted_strategy_is_refused_naming_the_admitted_values() -> None:
    message = _refusal(
        case_text(
            physics=(
                "{model: pnp, flow: false, variable_density: false, "
                "inertia: false, solid_permittivities: {membrane: 3.2}}"
            ),
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
            (
                "{model: pnp, flow: false, variable_density: false, "
                "inertia: false, solid_permittivities: {membrane: 3.2}}"
            ),
            "[current, eof_rate]",
            "eof_rate",
            "current, transport_numbers, rectification",
        ),
    ],
)
def test_ver56_an_undeclared_quantity_is_refused_when_the_case_is_resolved(
    physics: str, outputs: str, named: str, declared: str
) -> None:
    message = _refusal(case_text(physics=physics, outputs=outputs))
    assert named in message and declared in message
    assert f"'{physics.split(',')[0].split(': ')[1].rstrip('}')}'" in message


def test_ver56_fields_is_admitted_for_every_model() -> None:
    for model in ("pb", "pb-linear", "poisson"):
        resolved = resolve(
            loads_case(case_text(physics=ELECTROSTATIC_PHYSICS % model, outputs="[fields]"))
        )
        assert resolved.outputs == ("fields",)


def test_ver56_a_builder_refusal_is_re_raised_naming_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    salt = Electrolyte.from_parameter_file("willems2020_nacl")
    return replace(salt, species=(replace(salt.species[0], valence=2), salt.species[1]))


# PHY-21
def test_fr19_poisson_boltzmann_refuses_a_salt_that_is_not_symmetric_monovalent() -> None:
    divalent = _divalent()
    for name in ("pb", "pb-linear"):
        with pytest.raises(ValueError, match=r"symmetric monovalent.*z = \+2"):
            models.create(name, electrolyte=divalent)
    assert models.create("poisson", electrolyte=divalent).name == "poisson"


# NUM-18
def test_fr19_the_ladder_initialisers_state_their_own_debye_length_for_any_salt() -> None:
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
    with pytest.raises(ValueError, match="ends at epnp-ns or pnp-ns"):
        models.register_model(
            "laddered", lambda **_: models.create("pnp-ns"), models.declaration("epnp-ns")
        )
    assert "laddered" not in models.registered_models()


def test_ver56_a_builder_must_build_the_model_it_is_registered_as(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


# PHY-21
def test_ver56_a_model_without_solids_is_refused_a_generated_mesh() -> None:
    text = case_text(physics=ELECTROSTATIC_PHYSICS % "pb", outputs="[]").replace(
        "mesh: {path: absent.msh, format: msh41}", "profile: {path: absent.yaml}"
    )
    message = _refusal(text)
    assert "'pb'" in message and "inputs.mesh" in message and "poisson" in message


def test_ver56_the_declared_switches_are_not_shared_between_declarations() -> None:
    shared = {name: (False,) for name in models.SWITCHES}
    first = models.ModelDeclaration(options=(), switches=shared, solids=False)
    shared["flow"] = (False, True)
    assert first.switches["flow"] == (False,)


def test_ver56_building_a_model_while_resolving_imports_no_backend() -> None:
    script = f"""
import sys
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.pipeline.case import resolve
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


def _quickstart_variants() -> dict[str, str]:
    base = QUICKSTART.read_text(encoding="utf-8")
    corrections_block = (
        "  corrections:\n"
        "    diffusivity:  {model: willems2020_nacl}\n"
        "    mobility:     {model: willems2020_nacl}\n"
        "    viscosity:    {model: willems2020_nacl}\n"
        "    permittivity: {model: willems2020_nacl}\n"
        "    density:      {model: willems2020_nacl}\n"
        "    steric:       {model: borukhov}\n"
    )
    pnp_base = base.replace("    viscosity:    {model: willems2020_nacl}\n", "").replace(
        "    density:      {model: willems2020_nacl}\n", ""
    )
    electrostatic = (
        base.replace(corrections_block, "")
        .replace(
            "  solid_permittivities: {membrane: 3.2}\n",
            "  flow: false\n"
            "  variable_density: false\n"
            "  inertia: false\n"
            "  dielectric_gradient_forces: false\n",
        )
        .replace("continuation: default_ladder", "continuation: none")
        .replace("outputs: [current, transport_numbers, eof_rate]", "outputs: []")
    )
    return {
        "epnp-ns": base,
        "pnp-ns": base.replace(corrections_block, "").replace("model: epnp-ns", "model: pnp-ns"),
        "pnp": (
            pnp_base.replace(
                "model: epnp-ns",
                "model: pnp\n  flow: false\n  variable_density: false\n  inertia: false",
            )
            .replace("continuation: default_ladder", "continuation: none")
            .replace("eof_rate]", "rectification]")
        ),
        "pb": electrostatic.replace("model: epnp-ns", "model: pb"),
        "pb-linear": electrostatic.replace("model: epnp-ns", "model: pb-linear"),
    }


@pytest.mark.parametrize("model", sorted(SOLVE_HASHES))
def test_ver56_the_stage_ten_key_of_each_model_is_the_one_main_recorded(model: str) -> None:
    resolved = resolve(loads_case(_quickstart_variants()[model]))
    assert content_hash(SOLUTION_SCHEMA, resolved.solve_provenance) == SOLVE_HASHES[model]


def test_ver56_the_stage_ten_key_moves_with_the_algorithm_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved = resolve(loads_case(_quickstart_variants()["epnp-ns"]))
    before = content_hash(SOLUTION_SCHEMA, resolved.solve_provenance)
    monkeypatch.setattr("nanopnp.io.resolved.SOLVE_ALGORITHM_REVISION", 2)
    assert content_hash(SOLUTION_SCHEMA, resolved.solve_provenance) != before
    assert resolved.provenance["algorithm_revision"] == 2


# NUM-16
def test_ver56_the_stage_ten_key_moves_with_the_field_floor() -> None:
    resolved = resolve(loads_case(_quickstart_variants()["epnp-ns"]))
    looser = replace(resolved, newton=replace(resolved.newton, field_floor_ratio=1.0e-3))
    assert looser.solve_provenance["newton"]["field_floor_ratio"] == 1.0e-3
    assert content_hash(SOLUTION_SCHEMA, looser.solve_provenance) != content_hash(
        SOLUTION_SCHEMA, resolved.solve_provenance
    )


@pytest.mark.parametrize("model", sorted(RUNG_HASHES))
def test_ver56_every_ladder_rung_builds_the_model_main_built(model: str) -> None:
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
    assert rungs[-1].model.name == model
    assert rungs[-1].model.scales.concentration_M == pytest.approx(0.1, rel=1e-12)


class ForwardingModel:
    def __init__(self, inner: PhysicsModel) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return FORWARDING

    @property
    def provenance(self) -> Mapping[str, Any]:
        return {**self._inner.provenance, "model": FORWARDING}

    def solve(self, mesh: Mesh, measures: Measures, **kwargs: Option) -> ModelSolution:
        solution = self._inner.solve(mesh, measures, **kwargs)
        return replace(solution, model=self)

    def __getattr__(self, attribute: str) -> Option:
        return getattr(self._inner, attribute)


FORWARDING = "forwarding-pnp"


@pytest.fixture
def forwarding_model() -> Iterator[str]:
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
    generated = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=0.35, check_quality=False)
    return write_msh41(from_ngsolve(generated), tmp_path_factory.mktemp("pore") / "pore.msh")


def _run(text: str, directory: Path) -> RunResult:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "case.yaml"
    path.write_text(text, encoding="utf-8")
    return run_case(path, store=Store(directory / "store"), workspace=directory / "work")


def _state(result: RunResult) -> dict[str, np.ndarray]:
    import numpy as np

    with np.load(result.artefacts["solve"].payload["state"], allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files if name.startswith("field.")}


# FR-20, QR-14
def test_ver56_a_model_defined_as_one_class_runs_from_a_case_file_to_stage_twelve(
    forwarding_model: str, pore_mesh: Path, tmp_path: Path
) -> None:
    import numpy as np

    physics = (
        "{model: %s, flow: false, variable_density: false, "
        "inertia: false, solid_permittivities: {membrane: 3.2}}"
    )
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
        resolved=resolve(loads_case(texts[forwarding_model])),
    )
    assert type(restored.model) is ForwardingModel


# VER-71
def test_ver56_pnp_ns_beside_corrections_it_overrides_runs_and_restores(
    pore_mesh: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import numpy as np

    quickstart = (
        QUICKSTART.read_text(encoding="utf-8")
        .replace("model: epnp-ns", "model: pnp-ns")
        .replace("path: pore.msh", f"path: {pore_mesh}")
    )
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(quickstart))
    message = str(raised.value)
    assert "physics.model 'pnp-ns' does not read 6 keys this case sets" in message
    for prop in ("diffusivity", "mobility", "viscosity", "permittivity", "density"):
        assert f"electrolyte.corrections.{prop}.model: willems2020_nacl" in message
    assert "electrolyte.corrections.steric.model: borukhov" in message

    classical = quickstart.replace("{model: willems2020_nacl}", "{model: none}").replace(
        "{model: borukhov}", "{model: none}"
    )
    assert classical.count("{model: none}") == 6
    monkeypatch.setattr("nanopnp.pipeline.checks._check_unread", lambda document, model=None: None)
    texts = {
        "ladder": quickstart,
        "classical": classical,
        "single": classical.replace("continuation: default_ladder", "continuation: none"),
    }
    runs = {name: _run(text, tmp_path / name) for name, text in texts.items()}
    for name, result in runs.items():
        state = Path(result.artefacts["solve"].payload["state"])
        with np.load(state, allow_pickle=False) as archive:
            assert WALL_DISTANCE_ENTRY not in archive.files, name
        restore(state, resolved=resolve(loads_case(texts[name])))
    assert runs["ladder"].artefacts["qoi"].summary == runs["classical"].artefacts["qoi"].summary
    ladder_qoi = runs["ladder"].artefacts["qoi"].summary
    single_qoi = runs["single"].artefacts["qoi"].summary
    assert ladder_qoi["current_A"] == pytest.approx(single_qoi["current_A"], rel=1e-12)


def test_ver56_rerecorded_models_have_bit_identical_fingerprints(
    pore_mesh: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import netgen.occ as occ
    import ngsolve as ngs
    import numpy as np
    from test_case_leaves import fingerprint

    def equal(a: tuple[object, ...], b: tuple[object, ...]) -> bool:
        return (
            a[0] == b[0]
            and all(
                x.shape == y.shape and np.array_equal(x, y)  # type: ignore[union-attr]
                for x, y in zip(a[1:], b[1:], strict=True)
            )
        )

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
    fluid_mesh = pore_mesh.parent / "fluid_for_pb.msh"
    write_msh41(from_ngsolve(fluid), fluid_mesh)

    monkeypatch.setattr("nanopnp.pipeline.checks._check_unread", lambda document, model=None: None)
    base_text = QUICKSTART.read_text(encoding="utf-8")
    base_pore = base_text.replace("path: pore.msh", f"path: {pore_mesh}")
    base_fluid = base_text.replace("path: pore.msh", f"path: {fluid_mesh}")
    variants_pore = {
        k: v.replace("path: pore.msh", f"path: {pore_mesh}")
        for k, v in _quickstart_variants().items()
    }
    variants_fluid = {
        k: v.replace("path: pore.msh", f"path: {fluid_mesh}")
        for k, v in _quickstart_variants().items()
    }

    u_pnp_ns = yaml.safe_load(base_pore.replace("model: epnp-ns", "model: pnp-ns"))
    e_pnp_ns = yaml.safe_load(variants_pore["pnp-ns"])
    assert equal(fingerprint(u_pnp_ns), fingerprint(e_pnp_ns))

    u_pnp = yaml.safe_load(
        base_pore.replace(
            "model: epnp-ns",
            "model: pnp\n  flow: false\n  variable_density: false\n  inertia: false",
        )
        .replace("continuation: default_ladder", "continuation: none")
        .replace("eof_rate]", "rectification]")
    )
    e_pnp = yaml.safe_load(variants_pore["pnp"])
    assert equal(fingerprint(u_pnp), fingerprint(e_pnp))

    pb_model_str = (
        "model: pb\n"
        "  flow: false\n"
        "  variable_density: false\n"
        "  inertia: false\n"
        "  dielectric_gradient_forces: false"
    )
    u_pb = yaml.safe_load(
        base_fluid.replace("model: epnp-ns", pb_model_str)
        .replace("  solid_permittivities: {membrane: 3.2}\n", "")
        .replace("continuation: default_ladder", "continuation: none")
        .replace("outputs: [current, transport_numbers, eof_rate]", "outputs: []")
    )
    u_pb["inputs"]["mesh"]["groups"] = {"wall": "interface"}
    e_pb = yaml.safe_load(variants_fluid["pb"])
    e_pb["inputs"]["mesh"]["groups"] = {"wall": "interface"}
    assert equal(fingerprint(u_pb), fingerprint(e_pb))

    pb_lin_model_str = (
        "model: pb-linear\n"
        "  flow: false\n"
        "  variable_density: false\n"
        "  inertia: false\n"
        "  dielectric_gradient_forces: false"
    )
    u_pb_lin = yaml.safe_load(
        base_fluid.replace("model: epnp-ns", pb_lin_model_str)
        .replace("  solid_permittivities: {membrane: 3.2}\n", "")
        .replace("continuation: default_ladder", "continuation: none")
        .replace("outputs: [current, transport_numbers, eof_rate]", "outputs: []")
    )
    u_pb_lin["inputs"]["mesh"]["groups"] = {"wall": "interface"}
    e_pb_lin = yaml.safe_load(variants_fluid["pb-linear"])
    e_pb_lin["inputs"]["mesh"]["groups"] = {"wall": "interface"}
    assert equal(fingerprint(u_pb_lin), fingerprint(e_pb_lin))


def _slab(path: Path, *, membrane: tuple[float, float] | None) -> Path:
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
schema: nanopnp/field/v0.5
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


# VER-56
def test_fr19_pb_linear_from_a_case_file_equals_the_api_solve(tmp_path: Path) -> None:
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


# PHY-20
def test_ver56_poisson_with_solids_and_a_supplied_charge_equals_the_api_solve(
    tmp_path: Path,
) -> None:
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
        (
            (
                "{model: pnp, flow: false, variable_density: false, "
                "inertia: false, solid_permittivities: {membrane: 3.2}}"
            ),
            True,
            False,
            True,
        ),
        (ELECTROSTATIC_PHYSICS % "poisson", False, False, False),
        (ELECTROSTATIC_PHYSICS % "pb", False, False, False),
    ],
)
def test_ver56_the_mesh_asks_for_what_the_model_declares(
    physics: str, concentration: bool, no_slip: bool, sources: bool
) -> None:
    outputs = "[current]" if concentration else "[]"
    resolved = resolve(loads_case(case_text(physics=physics, outputs=outputs)))
    purposes = [requirement.purpose for requirement in required_names(resolved).boundaries]
    assert any("essential potential" in purpose for purpose in purposes)
    assert any("c_Na+" in purpose for purpose in purposes) is concentration
    assert any("no-slip" in purpose for purpose in purposes) is no_slip
    assert any("PHY-02" in purpose for purpose in purposes) is sources


def test_ver56_the_declarations_are_readable_without_building() -> None:
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


# NUM-07
def test_num07_at_order_changes_only_the_element_order() -> None:
    raised = AXISYMMETRIC.at_order(3)
    assert raised == replace(AXISYMMETRIC, element_order=3)
    assert raised.symmetry == AXISYMMETRIC.symmetry
    assert AXISYMMETRIC.element_order == 2

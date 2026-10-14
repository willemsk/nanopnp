"""VER-64: stage conformance, the protocol every stage meets and the facts the walk reads."""

from __future__ import annotations

import importlib
import inspect
import math
from pathlib import Path

import pytest

from nanopnp.core import stages
from nanopnp.core.stages import (
    StageDescription,
    _catalogue,
    create,
    describe,
    register,
    walk_order,
)
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import CaseDocument
from nanopnp.io.case_paths import NEUTRAL_SECTIONS
from nanopnp.io.resolved import ResolvedCase
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import (
    UnknownStageError,
    offered,
    selected_stages,
)
from nanopnp.validation.modularity import (
    STAGE_KEY,
    STAGE_RUN,
    stage_conformance,
    stage_sets,
    undeclared_reads,
)

ROOT = Path(__file__).resolve().parents[2]

QUICKSTART = ROOT / "examples" / "01-quickstart" / "quickstart.case.yaml"

EXAMPLES = ROOT / "examples"


def _shipped_cases() -> dict[str, ResolvedCase]:
    profile = load_case(EXAMPLES / "06-pdb-to-mesh" / "from-profile.case.yaml")
    pqr = load_case(EXAMPLES / "07-pdb-to-charged-run" / "from-pqr.case.yaml")
    pqr_profile = profile.model_copy(
        update={"inputs": profile.inputs.model_copy(update={"pqr": pqr.inputs.pqr})}
    )
    return {
        "quickstart": resolve(load_case(QUICKSTART)),
        "supplied-charge": resolve(load_case(EXAMPLES / "02-charged-pore" / "classical.case.yaml")),
        "profile": resolve(profile),
        "pqr-profile": resolve(pqr_profile),
        "structure": resolve(pqr),
    }


WALK = (
    "case",
    "structure",
    "density",
    "symmetry",
    "contour",
    "region",
    "mesh",
    "protonation",
    "charge",
    "materials",
    "solve",
    "qoi",
    "report",
)


def _constructor(name: str) -> inspect.Signature:
    module_name, _, attribute = _catalogue()[name].target.partition(":")
    return inspect.signature(getattr(importlib.import_module(module_name), attribute))


def _description(**facts: object) -> StageDescription:
    fields: dict[str, object] = {
        "name": "external",
        "number": 13,
        "title": "External",
        "inputs": ("case", "solve"),
        "outputs": (),
        "artefact_schema": "external/v1",
        "takes_workspace": False,
        "takes_store": False,
        "key_is_artefact": False,
        "weight": 0.1,
        "needs_section": None,
        "optional_inputs": (),
    }
    fields.update(facts)
    return StageDescription(**fields)  # type: ignore[arg-type]


@pytest.fixture
def scratch_registry(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    copy = dict(stages._REGISTRY)
    monkeypatch.setattr(stages, "_REGISTRY", copy)
    return copy  # type: ignore[return-value]


# -- the protocol -------------------------------------------------------------


def test_ver64_every_registered_stage_conforms_to_the_protocol() -> None:
    measured = stage_conformance()
    assert {stage.name for stage in measured} == set(walk_order())
    for stage in measured:
        assert stage.conforms, stage
        assert stage.key_signature == STAGE_KEY
        assert stage.run_signature == STAGE_RUN
    for name in walk_order():
        assert create(name).name == name


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("", None),
        ("    def key(self, inputs, cancel) -> None: ...\n", "(inputs, cancel)"),
        ("    def key(self, inputs) -> None: ...\n", STAGE_KEY),
    ],
    ids=["no-key", "key-with-cancel", "conforming"],
)
def test_ver64_a_stage_without_the_protocols_key_does_not_conform(
    key: str, expected: str | None
) -> None:
    sources = {
        "__init__.py": "",
        "core/__init__.py": "",
        "core/stages.py": 'register(StageDescription(name="x"), "nanopnp.x.s:XStage")\n',
        "x/__init__.py": "",
        "x/s.py": (
            "class XStage:\n"
            "    def describe(self) -> None: ...\n"
            "    def run(self, inputs, *, progress, cancel) -> None: ...\n" + key
        ),
    }
    (stage,) = stage_conformance(sources=sources)
    assert stage.key_signature == expected
    assert stage.conforms is (expected == STAGE_KEY)


def test_ver64_the_walk_writes_no_stage_set_of_its_own() -> None:
    assert stage_sets() == ()


# -- the facts ----------------------------------------------------------------


# VER-32
def test_ver64_takes_workspace_is_the_constructors_signature() -> None:
    for name in walk_order():
        takes = "workspace" in _constructor(name).parameters
        assert describe(name).takes_workspace is takes, name


# VER-57
def test_ver64_takes_store_is_the_constructors_signature() -> None:
    for name in walk_order():
        takes = "store" in _constructor(name).parameters
        assert describe(name).takes_store is takes, name


def test_ver64_a_key_that_is_its_artefact_is_what_run_returns() -> None:
    document = load_case(QUICKSTART)
    declared = [name for name in walk_order() if describe(name).key_is_artefact]
    assert declared == ["case", "materials"]
    for name in declared:
        stage = create(name)
        inputs = StageInputs(resolved=resolve(document))
        keyed, ran = stage.key(inputs).meta(), stage.run(inputs).meta()
        keyed.pop("created_at")
        ran.pop("created_at")
        assert keyed == ran, name
        assert keyed["payload"] == {}, name
        assert keyed["summary"], name


def test_ver64_needs_section_names_an_optional_top_level_case_field() -> None:
    declared = {name: describe(name).needs_section for name in walk_order()}
    assert {name for name, section in declared.items() if section is not None} == {
        "structure",
        "density",
        "symmetry",
        "contour",
    }
    for name, section in declared.items():
        if section is None:
            continue
        field = CaseDocument.model_fields.get(section)
        assert field is not None, f"stage {name!r} needs {section!r}, which is no case field"
        assert not field.is_required() and field.default is None, (name, section)
        assert section not in NEUTRAL_SECTIONS, (name, section)


# VER-62
def test_ver64_each_optional_input_is_one_a_case_drops() -> None:
    walks = {name: selected_stages(case, None) for name, case in _shipped_cases().items()}
    tail = ("materials", "solve", "qoi", "report")
    assert walks == {
        "quickstart": ("case", "mesh", *tail),
        "supplied-charge": ("case", "mesh", "charge", *tail),
        "profile": ("case", "region", "mesh", *tail),
        "pqr-profile": ("case", "region", "mesh", "protonation", "charge", *tail),
        "structure": WALK,
    }
    declared = {
        (name, optional) for name in walk_order() for optional in describe(name).optional_inputs
    }
    assert declared == {
        ("region", "contour"),
        ("mesh", "region"),
        ("protonation", "structure"),
        ("charge", "protonation"),
        ("charge", "region"),
        # Stage 7's artefact, which a case with no field drops.
        ("solve", "charge"),
        ("qoi", "charge"),
        ("report", "charge"),
    }
    for name, optional in declared:
        assert optional in describe(name).inputs, (name, optional)
        assert any(name in walk and optional not in walk for walk in walks.values()), (
            f"no case walks {name!r} without {optional!r}"
        )


def test_ver64_a_stage_whose_case_drops_a_required_input_is_not_walked(
    scratch_registry: dict[str, object],
) -> None:
    register(_description(inputs=("case", "contour")), "nanopnp.external:ExternalStage")
    profile = _shipped_cases()["profile"]
    assert "external" not in selected_stages(profile, None)
    with pytest.raises(UnknownStageError, match=r"does not walk 'contour', an input it requires"):
        selected_stages(profile, "external")
    assert selected_stages(_shipped_cases()["structure"], None) == (*WALK, "external")


def test_ver64_a_stage_walks_without_an_optional_input_its_case_drops(
    scratch_registry: dict[str, object],
) -> None:
    register(
        _description(inputs=("case", "contour"), optional_inputs=("contour",)),
        "nanopnp.external:ExternalStage",
    )
    assert selected_stages(_shipped_cases()["profile"], None)[-1] == "external"


def test_ver64_register_refuses_an_optional_input_it_does_not_take(
    scratch_registry: dict[str, object],
) -> None:
    before = dict(scratch_registry)
    with pytest.raises(ValueError, match=r"optional input 'mesh', which is not one of its inputs"):
        register(_description(optional_inputs=("mesh",)), "nanopnp.external:ExternalStage")
    assert scratch_registry == before


def test_ver64_every_weight_is_finite_and_positive() -> None:
    for name in walk_order():
        weight = describe(name).weight
        assert math.isfinite(weight) and weight > 0, (name, weight)


# -- the registry's refusals and the walk's order -----------------------------


def test_ver64_the_walk_is_registration_order_with_the_case_first() -> None:
    assert walk_order() == WALK
    assert walk_order() != tuple(d.name for d in stages.registered_stages())


@pytest.mark.parametrize("weight", [0.0, -1.0, math.nan, math.inf])
def test_ver64_register_refuses_a_weight_that_is_not_finite_and_positive(
    scratch_registry: dict[str, object], weight: float
) -> None:
    before = dict(scratch_registry)
    with pytest.raises(ValueError, match="progress weight"):
        register(_description(weight=weight), "nanopnp.external:ExternalStage")
    assert scratch_registry == before


def test_ver64_register_refuses_an_input_not_registered_before_it(
    scratch_registry: dict[str, object],
) -> None:
    before = dict(scratch_registry)
    with pytest.raises(ValueError, match=r"'external' takes input 'later'"):
        register(_description(inputs=("case", "later")), "nanopnp.external:ExternalStage")
    assert scratch_registry == before


def test_ver64_a_description_missing_a_fact_is_a_type_error() -> None:
    with pytest.raises(TypeError, match="weight"):
        StageDescription(  # type: ignore[call-arg]
            name="external",
            number=13,
            title="External",
            inputs=("case",),
            outputs=(),
            artefact_schema="external/v1",
            takes_workspace=False,
            takes_store=False,
            key_is_artefact=False,
            needs_section=None,
            optional_inputs=(),
        )


def test_ver64_a_needs_section_naming_no_case_section_is_named_by_the_walk(
    scratch_registry: dict[str, object],
) -> None:
    register(_description(needs_section="structur"), "nanopnp.external:ExternalStage")
    with pytest.raises(ValueError, match=r"'external' declares needs_section 'structur'"):
        selected_stages(resolve(load_case(QUICKSTART)), None)


def test_ver64_a_stage_registered_later_is_walked_after_the_rest(
    scratch_registry: dict[str, object],
) -> None:
    register(_description(), "nanopnp.external:ExternalStage")
    assert walk_order() == (*WALK, "external")
    assert describe("external").summary()["weight"] == 0.1


# -- a stage reads what it declares, and a walk to it runs what it reads --


STAGES = Path(stages.__file__)
SOLVE = STAGES.parent.parent / "solve" / "stage.py"


# VER-25
def test_ver64_a_registration_is_read_by_its_enum_member_and_one_it_cannot_read_is_skipped() -> (
    None
):
    sources = {
        "__init__.py": "",
        "core/__init__.py": "",
        "core/stages.py": (
            'register(StageDescription(name=StageName.ALPHA, inputs=("case", other())), '
            '"nanopnp.x.s:XStage")\n'
            'register(StageDescription(name=computed()), "nanopnp.x.s:XStage")\n'
            'register(StageDescription(name="beta", inputs=computed()), "nanopnp.x.s:XStage")\n'
        ),
        "x/__init__.py": "",
        "x/s.py": (
            "class XStage:\n"
            "    def describe(self) -> None: ...\n"
            "    def key(self, inputs) -> None: ...\n"
            "    def run(self, inputs, *, progress, cancel) -> None: ...\n"
        ),
    }
    assert [stage.name for stage in stage_conformance(sources=sources)] == ["alpha", "beta"]
    assert undeclared_reads(sources=sources) == ()


def test_ver64_no_stage_reads_an_input_it_does_not_declare() -> None:
    assert [read.describe() for read in undeclared_reads()] == []


def test_ver64_an_undeclared_read_is_refused_naming_stage_input_and_line() -> None:
    text = STAGES.read_text(encoding="utf-8")
    current = 'inputs=("case", "charge", "materials", "mesh"),'
    assert text.count(current) == 1
    line = next(
        number
        for number, content in enumerate(SOLVE.read_text(encoding="utf-8").splitlines(), 1)
        if 'inputs.upstream.get("charge")' in content
    )
    sources = {"core/stages.py": text.replace(current, 'inputs=("case", "materials", "mesh"),')}
    found = undeclared_reads(sources=sources)
    assert [(read.stage, read.name, read.path, read.line) for read in found] == [
        ("solve", "charge", "solve/stage.py", line)
    ]
    message = found[0].describe()
    assert "stage 'solve' reads the 'charge' artefact" in message
    assert f"solve/stage.py:{line}" in message


def test_ver64_a_read_reached_through_a_module_function_is_seen() -> None:
    text = STAGES.read_text(encoding="utf-8")
    current = 'inputs=("case", "charge", "mesh", "solve"),'
    assert text.count(current) == 1
    sources = {"core/stages.py": text.replace(current, 'inputs=("case", "solve"),')}
    named = {(read.stage, read.name) for read in undeclared_reads(sources=sources)}
    assert named == {("qoi", "mesh"), ("qoi", "charge")}


def test_ver64_each_stage_is_handed_exactly_its_declared_inputs() -> None:
    produced = {name: object() for name in walk_order()}
    for name in walk_order():
        handed = offered(name, produced)  # type: ignore[arg-type]
        assert set(handed) == set(describe(name).inputs) - {"case_path"}, name
        assert set(offered(name, produced, own=True)) == {*handed, name}  # type: ignore[arg-type]


def test_ver64_a_walk_to_a_stage_runs_its_input_closure_in_walk_order() -> None:
    structure = _shipped_cases()["structure"]
    assert structure.deposits_charge
    assert selected_stages(structure, "protonation") == ("case", "structure", "protonation")
    assert selected_stages(structure, "materials") == ("case", "materials")
    assert "charge" in selected_stages(structure, "solve")
    assert selected_stages(structure, "contour") == WALK[: WALK.index("contour") + 1]
    assert selected_stages(structure, "mesh") == WALK[: WALK.index("mesh") + 1]
    assert selected_stages(structure, None) == WALK

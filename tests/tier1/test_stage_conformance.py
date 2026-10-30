"""VER-64: stage conformance, the protocol every stage meets and the facts the walk reads."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.core import stages
from nanopnp.core.stages import (
    StageDescription,
    create,
    describe,
    register,
    walk_order,
)
from nanopnp.io.artefact import StageInputs
from nanopnp.io.resolved import ResolvedCase
from nanopnp.pipeline.case import load_case, loads_case, resolve
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
    classical = EXAMPLES / "02-charged-pore" / "classical.case.yaml"
    supplied_charge = resolve(
        loads_case(_with_supplied_mesh(classical.read_text(encoding="utf-8")))
    )
    return {
        "quickstart": resolve(load_case(QUICKSTART)),
        "supplied-charge": supplied_charge,
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


def test_ver64_the_walk_writes_no_stage_set_of_its_own() -> None:
    assert stage_sets() == ()


# -- the facts ----------------------------------------------------------------


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


# VER-62
def test_ver64_each_optional_input_is_one_a_case_drops() -> None:
    walks = {name: selected_stages(case, None) for name, case in _shipped_cases().items()}
    tail = ("materials", "solve", "qoi", "report")
    assert walks == {
        "quickstart": ("case", "region", "mesh", *tail),
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


# -- the registry's refusals and the walk's order -----------------------------


def test_ver64_the_walk_is_registration_order_with_the_case_first() -> None:
    assert walk_order() == WALK
    assert walk_order() != tuple(d.name for d in stages.registered_stages())


def test_ver64_a_stage_registered_later_is_walked_after_the_rest(
    scratch_registry: dict[str, object],
) -> None:
    register(_description(), "nanopnp.external:ExternalStage")
    assert walk_order() == (*WALK, "external")
    assert describe("external").summary()["weight"] == 0.1


# -- a stage reads what it declares, and a walk to it runs what it reads --


STAGES = Path(stages.__file__)


def test_ver64_no_stage_reads_an_input_it_does_not_declare() -> None:
    assert [read.describe() for read in undeclared_reads()] == []


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


def _with_supplied_mesh(case: str) -> str:
    """Return an example case text with its declared pore replaced by a supplied mesh file."""
    declared = (
        "geometry:\n  pore: {shape: cylinder, radius_nm: 2}\n  membrane: {thickness_nm: 6}\n"
        "  reservoir: {radius_nm: 10}\n\n"
    )
    supplied = "  mesh:\n    path: pore.msh\n    format: msh41\n    groups: {default: interface}\n"
    assert declared in case, "the example no longer declares its pore this way"
    text = case.replace(declared, "").replace("  mesh: {maxh_nm: 4, wall_h_nm: 0.35}\n", "")
    if "\ninputs:\n" in text:
        return text.replace("\ninputs:\n", f"\ninputs:\n{supplied}", 1)
    return text.replace("\nelectrolyte:\n", f"\ninputs:\n{supplied}\nelectrolyte:\n", 1)

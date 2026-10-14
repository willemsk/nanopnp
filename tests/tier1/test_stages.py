"""VER-25: the stage protocol, the registry and the promises FR-27 makes."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys

import pytest

from nanopnp.core.stages import (
    CancelFlag,
    Cancelled,
    MissingExtraError,
    StageDescription,
    StageIdentifier,
    StageName,
    _catalogue,
    check_cancelled,
    create,
    describe,
    register,
    registered_stages,
    report,
    walk_order,
)
from nanopnp.io.artefact import StageInputs
from nanopnp.pipeline.case import loads_case, resolve

MINIMAL = """
schema: nanopnp/case/v0.5
name: minimal
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns}
"""


def _in_subprocess(script: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    result: dict[str, object] = json.loads(completed.stdout)
    return result


# -- introspection ------------------------------------------------------------


def test_ver25_every_stage_describes_itself_without_importing_it() -> None:
    script = (
        "import sys, json;"
        "from nanopnp.core.stages import registered_stages;"
        "names = [d.name for d in registered_stages()];"
        "facts = {d.name: [d.summary()[k] for k in ('takes_workspace', 'takes_store',"
        " 'key_is_artefact', 'weight', 'needs_section', 'optional_inputs')]"
        " for d in registered_stages()};"
        "print(json.dumps({'names': names, 'facts': facts,"
        " 'ngsolve': 'ngsolve' in sys.modules,"
        " 'solve': 'nanopnp.solve.stage' in sys.modules,"
        " 'materials': 'nanopnp.materials.stage' in sys.modules,"
        " 'charge': 'nanopnp.charge.stage' in sys.modules,"
        " 'mesh': 'nanopnp.mesh.ingest' in sys.modules,"
        " 'structure': 'nanopnp.structure.stage' in sys.modules,"
        " 'density': 'nanopnp.density.stage' in sys.modules,"
        " 'symmetry': 'nanopnp.symmetry.stage' in sys.modules,"
        " 'contour': 'nanopnp.geometry.contour' in sys.modules,"
        " 'region': 'nanopnp.geometry.region' in sys.modules,"
        " 'protonation': 'nanopnp.charge.protonation' in sys.modules,"
        " 'netgen': 'netgen' in sys.modules,"
        " 'numpy': 'numpy' in sys.modules,"
        " 'extras': sorted(m for m in ('MDAnalysis', 'gemmi', 'skimage', 'shapely',"
        " 'pdb2pqr', 'propka')"
        " if m in sys.modules),"
        " 'post': 'nanopnp.post.stage' in sys.modules}))"
    )
    reported = _in_subprocess(script)
    assert reported["names"] == [
        "structure",
        "density",
        "symmetry",
        "contour",
        "region",
        "mesh",
        "protonation",
        "charge",
        "materials",
        "case",
        "solve",
        "qoi",
        "report",
    ]
    assert reported["facts"]["solve"] == [True, False, False, 0.75, None, ["charge"]]
    assert reported["facts"]["structure"] == [True, False, False, 0.05, "structure", []]
    assert reported["facts"]["charge"][-1] == ["protonation", "region"]
    assert reported["ngsolve"] is False
    assert reported["structure"] is False
    assert reported["extras"] == []
    assert reported["density"] is False
    assert reported["symmetry"] is False
    assert reported["contour"] is False
    assert reported["region"] is False
    assert reported["netgen"] is False
    assert reported["numpy"] is False
    assert reported["solve"] is False
    assert reported["materials"] is False
    assert reported["charge"] is False
    assert reported["protonation"] is False
    assert reported["mesh"] is False
    assert reported["post"] is False


def test_ver25_a_stage_description_matches_the_stage_it_describes() -> None:
    for name, entry in _catalogue().items():
        module_name, _, attribute = entry.target.partition(":")
        stage = getattr(importlib.import_module(module_name), attribute)()
        assert stage.name == name
        assert stage.describe() == entry.description


def test_ver25_the_pipeline_numbers_match_section_5_2() -> None:
    numbered = {entry.name: entry.number for entry in registered_stages()}
    assert numbered == {
        "structure": 1,
        "density": 2,
        "symmetry": 3,
        "contour": 4,
        "region": 5,
        "mesh": 6,
        "protonation": 7,
        "charge": 7,
        "materials": 8,
        "case": 9,
        "solve": 10,
        "qoi": 11,
        "report": 12,
    }


def test_ver25_stage_descriptions_match_artefact_schemas() -> None:
    from nanopnp.io import artefact

    stage_to_schema = {
        "case": artefact.CASE_SCHEMA,
        "structure": artefact.STRUCTURE_SCHEMA,
        "density": artefact.DENSITY_SCHEMA,
        "symmetry": artefact.REDUCED_SCHEMA,
        "contour": artefact.PROFILE_ARTEFACT_SCHEMA,
        "region": artefact.REGION_SCHEMA,
        "mesh": artefact.MESH_ARTEFACT_SCHEMA,
        "protonation": artefact.PROTONATION_SCHEMA,
        "charge": artefact.FIELDS_SCHEMA,
        "materials": artefact.MATERIALS_SCHEMA,
        "solve": artefact.SOLUTION_SCHEMA,
        "qoi": artefact.QOI_SCHEMA,
        "report": artefact.REPORT_SCHEMA,
    }
    for stage_name, expected_schema in stage_to_schema.items():
        desc = describe(stage_name)
        assert desc.artefact_schema == expected_schema, (
            f"Stage {stage_name!r} artefact_schema {desc.artefact_schema!r} "
            f"differs from io.artefact constant {expected_schema!r}"
        )


def test_ver48_a_missing_extra_is_named_when_the_stage_is_created(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "gemmi", None)
    for module in ("nanopnp.structure.stage", "nanopnp.structure.read"):
        monkeypatch.delitem(sys.modules, module, raising=False)
    with pytest.raises(MissingExtraError) as raised:
        create("structure")
    message = str(raised.value)
    assert "'structure' extra" in message
    assert "nanopnp.structure.stage" in message
    assert "'gemmi'" in message
    assert "uv sync --all-extras" in message
    assert _catalogue()["structure"].extra == "structure"
    assert _catalogue()["solve"].extra is None


def test_ver51_contour_names_its_missing_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "skimage", None)
    monkeypatch.setitem(sys.modules, "skimage.measure", None)
    monkeypatch.delitem(sys.modules, "nanopnp.geometry.contour", raising=False)
    with pytest.raises(MissingExtraError) as raised:
        create("contour")
    message = str(raised.value)
    assert "'structure' extra" in message
    assert "nanopnp.geometry.contour" in message
    assert "'skimage" in message
    assert _catalogue()["contour"].extra == "structure"


def test_ver25_an_unknown_stage_is_refused_by_name() -> None:
    with pytest.raises(KeyError, match="materials"):
        describe("solver")
    with pytest.raises(KeyError, match="materials"):
        create("solver")


def test_ver25_a_stage_cannot_be_registered_twice() -> None:
    description = StageDescription(
        name="solve",
        number=10,
        title="Solve",
        inputs=(),
        outputs=(),
        artefact_schema="nanopnp/solution/v0.5",
        takes_workspace=False,
        takes_store=False,
        key_is_artefact=False,
        weight=1.0,
        needs_section=None,
        optional_inputs=(),
    )
    with pytest.raises(ValueError, match="already registered"):
        register(description, "nanopnp.solve.stage:SolveStage")


def test_ver25_a_malformed_target_is_refused() -> None:
    description = StageDescription(
        name="not-a-stage",
        number=99,
        title="",
        inputs=(),
        outputs=(),
        artefact_schema="x/v1",
        takes_workspace=False,
        takes_store=False,
        key_is_artefact=False,
        weight=1.0,
        needs_section=None,
        optional_inputs=(),
    )
    with pytest.raises(ValueError, match="module:attribute"):
        register(description, "nanopnp.solve.stage.SolveStage")


# -- progress and cancellation ------------------------------------------------


def test_ver25_progress_is_clamped_into_the_unit_interval() -> None:
    seen: list[float] = []
    report(lambda fraction, message: seen.append(fraction), 1.7, "over")
    report(lambda fraction, message: seen.append(fraction), -0.2, "under")
    assert seen == [1.0, 0.0]


def test_ver25_a_cancelled_token_raises_naming_where_it_stopped() -> None:
    flag = CancelFlag()
    check_cancelled(flag, "the solve")  # not set: nothing happens
    flag.cancel()
    with pytest.raises(Cancelled, match="the solve"):
        check_cancelled(flag, "the solve")


def test_ver25_cancellation_is_not_an_error_subclass_of_the_gates() -> None:
    from nanopnp.numerics.gates import GateViolationError

    assert not issubclass(Cancelled, GateViolationError)
    assert issubclass(Cancelled, RuntimeError)


# -- the materials stage, which needs no mesh ---------------------------------


def test_ver25_the_materials_stage_reports_progress_ending_at_one() -> None:
    seen: list[float] = []
    stage = create("materials")
    artefact = stage.run(
        StageInputs(resolved=resolve(loads_case(MINIMAL))),
        progress=lambda fraction, message: seen.append(fraction),
    )
    assert seen == sorted(seen)
    assert seen[-1] == 1.0
    assert artefact.schema == stage.describe().artefact_schema
    assert artefact.hash


def test_ver25_a_cancelled_stage_returns_no_artefact() -> None:
    flag = CancelFlag()
    flag.cancel()
    with pytest.raises(Cancelled):
        create("materials").run(StageInputs(resolved=resolve(loads_case(MINIMAL))), cancel=flag)


def test_ver25_a_stage_invoked_without_its_upstream_says_which_one() -> None:
    inputs = StageInputs(resolved=resolve(loads_case(MINIMAL)))
    with pytest.raises(KeyError, match="materials"):
        inputs.require("materials")


def test_ver25_stage_name_enum_matches_registered_stages() -> None:
    registered = {d.name for d in registered_stages()}
    enum_values = tuple(s.value for s in StageName)
    assert set(enum_values) == registered
    assert len(enum_values) == len(registered)
    assert enum_values == walk_order()
    for member in StageName:
        assert isinstance(member, str)
        assert isinstance(member, StageName)


def test_ver25_create_and_describe_accept_stage_name_enum() -> None:
    identifier: StageIdentifier = StageName.CASE
    assert describe(identifier) == describe("case")
    stage = create(StageName.MATERIALS)
    assert stage.name == StageName.MATERIALS
    with pytest.raises(KeyError):
        describe("not_a_stage")
    with pytest.raises(KeyError):
        create("not_a_stage")


def test_ver25_a_registered_name_is_a_plain_string_whatever_identifier_registered_it() -> None:
    for description in registered_stages():
        assert type(description.name) is str
        assert repr(description.name) == f"'{description.name}'"
        assert type(description.summary()["name"]) is str
    assert all(type(name) is str for name in walk_order())
    assert repr(describe(StageName.REGION).name) == "'region'"

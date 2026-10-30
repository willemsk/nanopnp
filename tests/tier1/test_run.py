"""VER-32: the pipeline driver: one case file to one run directory (FR-27, IF-01)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp import Case, Session
from nanopnp.charge.dielectric import SolidFractionField
from nanopnp.charge.fields import FieldDocument, FormSpec, create_form
from nanopnp.charge.stage import (
    FieldStage,
    ResolvedFields,
    gate_parameters,
    smoothed_dielectric_deviations,
)
from nanopnp.core import stages as stages_module
from nanopnp.core.hashing import file_hash
from nanopnp.core.stages import StageDescription, _catalogue, describe, register, walk_order
from nanopnp.io.artefact import CASE_SCHEMA, StageInputs
from nanopnp.io.manifest import CASE_FILENAME, MANIFEST_FILENAME, MANIFEST_SCHEMA
from nanopnp.io.resolved import ResolvedCase
from nanopnp.io.store import Store
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, exclusion_deviations
from nanopnp.pipeline import run as run_module
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.pipeline.run import (
    RUN_RECORD_FILENAME,
    RUN_SCHEMA,
    WORKSPACE_DIRNAME,
    MissingUpstreamError,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.mesh.adapter import MeshData


# -- the pipeline order --------------------------------------------------------


def test_ver32_the_pipeline_is_registered_and_in_dependency_order() -> None:
    produced = {"case_path"}
    for name in walk_order():
        description = describe(name)  # raises if it is not registered
        missing = sorted(set(description.inputs) - produced)
        assert not missing, f"stage {name!r} consumes {missing}, which nothing before it produces"
        produced.add(name)
    assert set(walk_order()) == {description.name for description in _catalogue_descriptions()}


def _catalogue_descriptions() -> tuple[object, ...]:
    return tuple(entry.description for entry in _catalogue().values())


# -- the deviations a stage reads off its own artefact -------------------


def _two_triangles(materials: tuple[str, ...]) -> MeshData:
    import numpy as np

    from nanopnp.mesh.adapter import MeshData

    count = len(materials)
    vertices = np.array(
        [[r, float(level)] for level in range(count + 1) for r in (0.0, 1.0)], dtype=np.float64
    )
    triangles = []
    material = []
    for index in range(count):
        base = 2 * index
        triangles += [[base, base + 1, base + 3], [base, base + 3, base + 2]]
        material += [index] * 2
    return MeshData(
        vertices=vertices,
        triangles=np.array(triangles, dtype=np.int64),
        triangle_material=np.array(material, dtype=np.int64),
        materials=materials,
        edges=np.array([[2 * i, 2 * i + 2] for i in range(count)], dtype=np.int64),
        edge_group=np.zeros(count, dtype=np.int64),
        boundaries=("axis",),
    )


def _ingested(materials: tuple[str, ...]) -> IngestedMesh:
    from nanopnp.mesh.quality import element_quality

    data = _two_triangles(materials)
    return IngestedMesh(
        data=data,
        quality=element_quality(data),
        source=Path(__file__),
        source_hash="0" * 64,
        applied={},
    )


@pytest.mark.parametrize(
    "materials",
    [("electrolyte", "membrane"), ("electrolyte", "membrane", "exclusion")],
    ids=["no-shell", "exclusion-shell"],
)
def test_ver32_the_mesh_stage_reads_the_exclusion_deviation_off_its_artefact(
    materials: tuple[str, ...],
) -> None:
    ingested = _ingested(materials)
    artefact = MeshStage().artefact(ingested)
    inputs = StageInputs(resolved=resolve(loads_case(_MINIMAL)), upstream={"mesh": artefact})

    assert MeshStage().deviations(inputs) == ingested.deviations()
    assert bool(ingested.deviations()) is ("exclusion" in materials)
    assert ingested.deviations() == exclusion_deviations(materials)


# PHY-20
def test_ver32_the_field_stage_reads_the_dielectric_deviation_off_its_artefact() -> None:
    fields = ResolvedFields(
        charge=None, conservation=None, eps_r=_solid_fraction_field(), material_means=()
    )
    assert fields.deviations(), "the fixture must carry a deviation, or this tests nothing"

    case = loads_case(_MINIMAL)
    artefact = FieldStage().artefact(fields, "0" * 64, resolved=resolve(case))
    inputs = StageInputs(resolved=resolve(case), upstream={"charge": artefact})
    assert FieldStage().deviations(inputs) == fields.deviations()
    assert smoothed_dielectric_deviations(smoothed=False) == ()


def test_ver29_the_field_key_carries_the_solid_set_only_with_a_dielectric_field() -> None:
    dielectric = ResolvedFields(
        charge=None, conservation=None, eps_r=_solid_fraction_field(), material_means=()
    )
    bare = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
    base = resolve(loads_case(_MINIMAL))
    protein = resolve(
        loads_case(
            _MINIMAL.replace(
                "physics: {model: pnp-ns}",
                "physics: {model: pnp-ns, solid_permittivities: {protein: 10.0}}",
            )
        )
    )
    softer = resolve(
        loads_case(
            _MINIMAL.replace(
                "physics: {model: pnp-ns}",
                "physics: {model: pnp-ns, solid_permittivities: {protein: 4.0}}",
            )
        )
    )

    def key(resolved: ResolvedCase, fields: ResolvedFields) -> str:
        return FieldStage().artefact(fields, "0" * 64, resolved=resolved).hash

    assert key(protein, dielectric) != key(base, dielectric)
    assert key(protein, dielectric) == key(softer, dielectric)
    assert key(protein, bare) == key(base, bare)
    assert gate_parameters(protein, dielectric)["solids"] == ["protein"]


def _solid_fraction_field() -> SolidFractionField:
    spec = FormSpec(
        name="uniform",
        parameters={"value": 1.0},
        origin_nm=(0.0, 0.0),
        spacing_nm=(1.0, 1.0),
        shape=(2, 2),
    )
    document = FieldDocument.model_validate(
        {
            "schema": "nanopnp/field/v0.5",
            "name": "chi",
            "quantity": "solid_fraction",
            "units": "1",
            "provenance": {"source": "analytic"},
            "form": spec.model_dump(),
        }
    )
    return SolidFractionField(document=document, grid=create_form(spec), source=Path(__file__))


# -- the walk itself -----------------------------------------------------------


def test_ver32_a_truncated_run_writes_its_directory_and_reports_monotone_progress(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    seen: list[tuple[float, str]] = []
    store = Store(tmp_path / "store")
    result = Session(store, workspace=tmp_path / "work").run(
        Case.load(cylindrical_pore_case),
        upto="mesh",
        progress=lambda fraction, message: seen.append((fraction, message)),
    )

    assert [record.name for record in result.stages] == ["case", "mesh"]
    assert [record.number for record in result.stages] == [9, 6]
    assert all(not record.cached for record in result.stages), "a fresh store cannot hit"
    assert result.quantities == {}, "no stage 11 ran, so there is no number to report"
    assert result.files == ()

    fractions = [fraction for fraction, _ in seen]
    assert fractions == sorted(fractions), "progress must be monotone (FR-27)"
    assert fractions[0] >= 0.0 and fractions[-1] == pytest.approx(1.0)

    for filename in (MANIFEST_FILENAME, CASE_FILENAME, RUN_RECORD_FILENAME):
        assert (result.directory / filename).is_file(), filename
    written_case = (result.directory / CASE_FILENAME).read_bytes().decode("utf-8")
    assert written_case == result.manifest.case_text

    record = result.record()
    assert record["schema"] == RUN_SCHEMA
    assert record["manifest"] == result.manifest.hash
    assert set(record["artefacts"]) == {"case", "mesh"}
    assert result.manifest.document()["schema"] == MANIFEST_SCHEMA


def test_qr08_a_truncated_walk_does_not_overwrite_the_record_of_the_full_run(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    store = Store(tmp_path / "store")
    full = Session(store, workspace=tmp_path / "work").run(Case.load(cylindrical_pore_case))
    assert full.quantities, "a full run records its quantities"
    recorded = (full.directory / RUN_RECORD_FILENAME).read_bytes()
    manifest = (full.directory / MANIFEST_FILENAME).read_bytes()

    truncated = Session(store, workspace=tmp_path / "work").run(
        Case.load(cylindrical_pore_case), upto="mesh"
    )
    assert truncated.directory != full.directory
    assert (full.directory / RUN_RECORD_FILENAME).read_bytes() == recorded
    assert (full.directory / MANIFEST_FILENAME).read_bytes() == manifest
    assert (truncated.directory / RUN_RECORD_FILENAME).is_file()


def test_qr08_a_complete_walk_is_complete_when_its_case_drops_the_last_registered_stage(
    cylindrical_pore_case: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stages_module, "_REGISTRY", dict(stages_module._REGISTRY))
    register(
        StageDescription(
            name="external",
            number=13,
            title="External",
            inputs=("case", "solve"),
            outputs=(),
            artefact_schema="external/v1",
            takes_workspace=False,
            takes_store=False,
            key_is_artefact=False,
            weight=0.1,
            needs_section="structure",
            optional_inputs=(),
        ),
        "nanopnp.external:ExternalStage",
    )
    result = Session(Store(tmp_path / "store"), workspace=tmp_path / "work", write=False).run(
        Case.load(cylindrical_pore_case)
    )
    assert result.stages[-1].name == "report"
    assert not result.directory.name.startswith("run-probe-upto-"), result.directory.name


@pytest.mark.parametrize("linesep", ["\n", "\r\n"])
def test_qr08_the_run_directory_case_hashes_to_the_recorded_case_input(
    cylindrical_pore_case: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, linesep: str
) -> None:
    monkeypatch.setattr(os, "linesep", linesep)
    source = tmp_path / "case.yaml"
    text = cylindrical_pore_case.read_text(encoding="utf-8").replace("\n", linesep)
    source.write_bytes(text.encode("utf-8"))

    result = Session(Store(tmp_path / "store")).run(Case.load(source), upto="mesh")

    recorded = result.manifest.document()["inputs"]["files"]["case"]["sha256"]  # type: ignore[index]
    assert file_hash(result.directory / CASE_FILENAME) == recorded == file_hash(source)


def test_ver32_a_run_writes_its_scratch_inside_the_store_it_was_given(
    cylindrical_pore_case: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.delenv("NANOPNP_STORE", raising=False)

    # The scratch is removed when the walk ends, so where it was made is
    # recorded as it is made.
    made: list[Path] = []
    original = run_module._scratch

    def watched(store: Store) -> Path:
        made.append(original(store))
        return made[-1]

    monkeypatch.setattr(run_module, "_scratch", watched)

    store = Store(tmp_path / "store")
    result = Session(store).run(Case.load(cylindrical_pore_case), upto="mesh")

    assert list(elsewhere.iterdir()) == [], "a run leaked files outside the store it was given"
    assert len(made) == 1, made
    assert made[0].parent == store.root / WORKSPACE_DIRNAME

    mesh = result.artefacts["mesh"]
    written = Path(str(mesh.payload["mesh"]))
    assert store.root in written.parents
    assert written.is_file()


def test_ver32_a_run_removes_its_scratch_once_the_store_holds_the_payloads(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    store = Store(tmp_path / "store")
    result = Session(store).run(Case.load(cylindrical_pore_case), upto="mesh")
    assert list((store.root / WORKSPACE_DIRNAME).glob("run-*")) == []
    assert Path(str(result.artefacts["mesh"].payload["mesh"])).is_file()

    named = tmp_path / "work"
    Session(Store(tmp_path / "other"), workspace=named).run(
        Case.load(cylindrical_pore_case), upto="mesh"
    )
    assert (named / "mesh" / "mesh.msh").is_file()


def test_ver32_a_second_run_through_the_same_store_is_served_from_it(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    store = Store(tmp_path / "store")
    first = Session(store, workspace=tmp_path / "work").run(
        Case.load(cylindrical_pore_case), upto="mesh"
    )
    second = Session(store, workspace=tmp_path / "work").run(
        Case.load(cylindrical_pore_case), upto="mesh"
    )

    assert all(record.cached for record in second.stages)
    assert [record.hash for record in second.stages] == [record.hash for record in first.stages]
    assert second.directory == first.directory, "the same case writes the same run directory"


def test_ver32_only_refuses_an_upstream_the_store_does_not_hold(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    with pytest.raises(MissingUpstreamError) as raised:
        Session(Store(tmp_path / "store"), workspace=tmp_path / "work").run(
            Case.load(cylindrical_pore_case), upto="solve", only=True
        )
    message = str(raised.value)
    assert "'mesh'" in message
    assert "nanopnp/mesh/v0.5" in message
    assert str(tmp_path / "store") in message


def test_ver32_upto_names_a_stage_this_case_does_not_walk(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    with pytest.raises(KeyError, match="nothing for it to read"):
        Session(Store(tmp_path / "store"), write=False).run(
            Case.load(cylindrical_pore_case), upto="charge"
        )
    with pytest.raises(KeyError, match="no stage 'sovle'"):
        Session(Store(tmp_path / "store"), write=False).run(
            Case.load(cylindrical_pore_case), upto="sovle"
        )


_MINIMAL = f"""
schema: {CASE_SCHEMA}
name: minimal
inputs: {{mesh: {{path: pore.vol, format: vol}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: pnp-ns}}
"""


# -- the protonation stage in the walk -----------------------

_PQR_LINES = """\
ATOM      1  N   GLU A  18      -2.661   5.770 -35.426 -0.3000 1.8500
ATOM      2  CA  GLU A  18      -1.598   4.789 -35.571  0.3000 2.2750
ATOM      3  C   GLU A  18      -2.071   3.395 -35.184  0.5100 2.0000
ATOM      4  O   GLU A  18      -1.657   2.404 -35.775 -1.5100 1.7000
"""


def _pqr_case(cylindrical_pore_case: Path, tmp_path: Path) -> Path:
    pqr = tmp_path / "supplied.pqr"
    pqr.write_text(_PQR_LINES, encoding="utf-8")
    text = cylindrical_pore_case.read_text(encoding="utf-8").replace(
        "inputs:\n", f"inputs:\n  pqr: {{path: {pqr}, format: pqr}}\n", 1
    )
    path = tmp_path / "pqr.case.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_ver57_protonation_runs_before_the_deposit_it_feeds(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    from nanopnp.pipeline.run import (
        UnknownStageError,
        selected_stages,
    )

    pqr_text = _pqr_case(cylindrical_pore_case, tmp_path).read_text(encoding="utf-8")
    supplied = resolve(loads_case(pqr_text))
    assert supplied.deposits_charge
    assert selected_stages(supplied, "solve") == (
        "case",
        "mesh",
        "protonation",
        "charge",
        "materials",
        "solve",
    )
    # A walk to a stage runs that stage's input closure; protonation reads the case alone.
    assert selected_stages(supplied, "protonation") == ("case", "protonation")
    assert selected_stages(supplied, "materials") == ("case", "materials")
    bare = resolve(loads_case(cylindrical_pore_case.read_text(encoding="utf-8")))
    assert "protonation" not in selected_stages(bare, None)
    assert "charge" not in selected_stages(bare, None)
    with pytest.raises(UnknownStageError, match="nothing for it to protonate"):
        selected_stages(bare, "protonation")


def test_ver57_a_walk_to_protonation_records_it_in_the_charge_group(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    case = _pqr_case(cylindrical_pore_case, tmp_path)
    store = Store(tmp_path / "store")
    result = Session(store, write=False).run(Case.load(case), upto="protonation")
    group = result.manifest.charge
    assert group["status"] == "not run"
    assert "stopped before stage 7" in str(group["reason"])
    record = group["protonation"]
    assert isinstance(record, dict)
    assert record["q_net_e"] == [-1]
    assert record["source"] == "inputs.pqr"
    assert record["pqr_sha256"] == file_hash(tmp_path / "supplied.pqr")
    assert "pqr" in result.manifest.inputs["files"]  # type: ignore[operator]
    truncated = Session(store, write=False).run(Case.load(case), upto="mesh")
    skipped = truncated.manifest.charge["protonation"]
    assert isinstance(skipped, dict)
    assert skipped["status"] == "not run"
    assert "stopped before stage 7" in str(skipped["reason"])


def test_ver64_a_walk_past_stage_7_that_skips_it_says_so_in_the_charge_group(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    case = _pqr_case(cylindrical_pore_case, tmp_path)
    result = Session(Store(tmp_path / "store"), write=False).run(Case.load(case), upto="materials")
    assert [record.name for record in result.stages] == ["case", "materials"]
    group = result.manifest.charge
    assert group["status"] == "not run"
    assert "stopped before stage 7" not in str(group["reason"])
    assert "the walk to 'materials' does not read stage 7" in str(group["reason"])
    skipped = group["protonation"]
    assert isinstance(skipped, dict)
    assert "the walk to 'materials' does not read stage 7" in str(skipped["reason"])


def test_run_result_current_and_conductance_in_nano_units(tmp_path: Path) -> None:
    from typing import Any, cast

    from nanopnp.io.artefact import Artefact
    from nanopnp.pipeline.run import RunResult

    def result(**summary: object) -> RunResult:
        qoi = Artefact(schema="nanopnp/qoi/v0.5", parameters={}, summary=summary)
        return RunResult(tmp_path, cast("Any", None), {"qoi": qoi})

    solved = result(current_A=2e-9, conductance_S=4e-8)
    assert solved.current_nA == pytest.approx(2.0, rel=1e-15)
    assert solved.conductance_nS == pytest.approx(40.0, rel=1e-15)
    unbiased = result(current_A=None, conductance_S=None)
    assert unbiased.current_nA is None
    assert unbiased.conductance_nS is None
    with pytest.raises(KeyError, match="qoi"):
        _ = RunResult(tmp_path, cast("Any", None), {}).current_nA


def test_ver32_reopen_refuses_a_run_whose_case_file_was_edited_after_the_run(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    from nanopnp.io.manifest import ManifestHashError
    from nanopnp.validation.runs import reopen

    result = Session(Store(tmp_path / "store")).run(Case.load(cylindrical_pore_case), upto="mesh")
    case_file = result.directory / CASE_FILENAME
    case_file.write_text(case_file.read_text(encoding="utf-8") + "# edited\n", encoding="utf-8")

    with pytest.raises(ManifestHashError, match="differs from the case text"):
        reopen(result.directory)

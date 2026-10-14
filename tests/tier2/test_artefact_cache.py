"""VER-26 (with FR-25, FR-27, NUM-11, NUM-18): the content-addressed cache around a solve."""

import logging
from dataclasses import dataclass
from pathlib import Path

import pytest

from nanopnp.core.hashing import file_hash
from nanopnp.core.stages import CancelFlag, Cancelled
from nanopnp.io import manifest as manifest_module
from nanopnp.io.artefact import CaseArtefact, SolutionArtefact, StageInputs
from nanopnp.io.case import CaseDocument
from nanopnp.io.store import Store
from nanopnp.materials.stage import MaterialsStage
from nanopnp.mesh.adapter import read, write_msh41
from nanopnp.mesh.ingest import MeshStage, MeshVocabularyError, ingest
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.solve.stage import SolveStage

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0
CONCENTRATION_M = 0.1
BIAS_V = 0.02


# PHY-02, PHY-20
def case_text(mesh_path: Path, *, bias_V: float = BIAS_V, mesh_format: str = "vol") -> str:
    return f"""
schema: nanopnp/case/v0.5
name: cache-probe
inputs:
  mesh:
    path: {mesh_path}
    format: {mesh_format}
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: {CONCENTRATION_M}
  temperature_K: 298.15
  parameters: willems2020_nacl
boundary_conditions:
  bias_V: {bias_V}
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [current]
"""


@dataclass
class Run:
    store: Store
    document: CaseDocument
    text: str
    mesh_path: Path
    key: SolutionArtefact
    artefact: SolutionArtefact
    computations: list[int]


@pytest.fixture(scope="module")
def solved(tmp_path_factory: pytest.TempPathFactory) -> Run:
    work = tmp_path_factory.mktemp("cache")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))

    text = case_text(mesh_path)
    document = loads_case(text)
    store = Store(work / "store")
    stage = SolveStage(workspace=work / "fields")
    inputs = StageInputs(resolved=resolve(document))

    computations: list[int] = []

    def compute() -> SolutionArtefact:
        computations.append(len(computations))
        return stage.run(inputs)

    key = stage.key(inputs)
    artefact = store.get_or_compute(key, compute)
    logger.info(
        "solve keyed %s: %d rungs, %d Newton iterations, stabilisation %s, mesh %s",
        artefact.short_hash,
        len(artefact.summary["rungs"]),
        artefact.summary["iterations"],
        artefact.summary["stabilisation"],
        artefact.summary["mesh"],
    )
    return Run(
        store=store,
        document=document,
        text=text,
        mesh_path=mesh_path,
        key=key,
        artefact=artefact,
        computations=computations,
    )


def test_ver26_the_key_computed_before_the_solve_is_the_one_it_produces(solved: Run) -> None:
    assert solved.key.hash == solved.artefact.hash
    assert solved.key.parameters == solved.artefact.parameters
    assert solved.key.inputs == solved.artefact.inputs
    assert solved.key.payload == {}, "the key must be computable without doing the work"


# FR-27
def test_ver26_the_key_is_the_same_whether_or_not_stage_8_was_supplied(solved: Run) -> None:
    inputs = StageInputs(resolved=resolve(solved.document))
    materials = MaterialsStage().run(inputs)
    with_upstream = SolveStage().key(
        StageInputs(resolved=resolve(solved.document), upstream={"materials": materials})
    )
    assert with_upstream.hash == solved.key.hash
    assert solved.key.inputs["materials"] == materials.hash


def test_ver26_solving_the_same_case_again_is_a_store_hit(solved: Run) -> None:
    stage = SolveStage()
    inputs = StageInputs(resolved=resolve(solved.document))

    before = len(solved.computations)
    hits, misses = solved.store.hits, solved.store.misses

    def compute() -> SolutionArtefact:
        solved.computations.append(len(solved.computations))
        return stage.run(inputs)

    again = solved.store.get_or_compute(stage.key(inputs), compute)

    assert len(solved.computations) == before, "the second solve re-entered Newton"
    assert solved.store.hits == hits + 1
    assert solved.store.misses == misses
    assert again.hash == solved.artefact.hash
    assert again.summary == solved.artefact.summary
    assert again.payload["state"].is_file()
    assert again.payload["state"].parent == solved.store.location(again.schema, again.hash)
    assert not again.hand_substituted


def test_ver26_changing_the_bias_misses_the_cache(solved: Run) -> None:
    other = loads_case(case_text(solved.mesh_path, bias_V=BIAS_V + 0.01))
    key = SolveStage().key(StageInputs(resolved=resolve(other)))

    assert key.hash != solved.key.hash
    assert key.inputs == solved.key.inputs, "only the case changed, not the inputs it consumed"
    assert solved.store.contains(solved.key)
    assert not solved.store.contains(key)


# FR-27
def test_ver26_the_mesh_enters_the_key_by_content_and_not_by_its_bytes(
    solved: Run, tmp_path: Path
) -> None:
    copied = tmp_path / "elsewhere.vol"
    copied.write_bytes(solved.mesh_path.read_bytes())
    same = SolveStage().key(StageInputs(resolved=resolve(loads_case(case_text(copied)))))
    assert same.hash == solved.key.hash

    rewritten = write_msh41(read(solved.mesh_path), tmp_path / "rewritten.msh")
    as_msh = SolveStage().key(
        StageInputs(resolved=resolve(loads_case(case_text(rewritten, mesh_format="gmsh"))))
    )
    assert as_msh.inputs["mesh"] == solved.key.inputs["mesh"]
    assert as_msh.hash == solved.key.hash

    finer_path = tmp_path / "finer.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM / 2).ngmesh.Save(str(finer_path))
    finer = SolveStage().key(StageInputs(resolved=resolve(loads_case(case_text(finer_path)))))
    assert finer.inputs["mesh"] != solved.key.inputs["mesh"]
    assert finer.hash != solved.key.hash


def test_ver27_a_boundary_the_run_selects_on_and_the_mesh_lacks_aborts(
    solved: Run, tmp_path: Path
) -> None:
    text = case_text(solved.mesh_path).replace(
        "groups: {default: interface}", "groups: {default: interface, wall: interface}"
    )
    with pytest.raises(MeshVocabularyError) as raised:
        SolveStage().key(StageInputs(resolved=resolve(loads_case(text))))
    message = str(raised.value)
    assert "wall" in message
    assert "NUM-06" in message


def test_ver26_cancelling_mid_ladder_leaves_no_artefact_in_the_store(
    solved: Run, tmp_path: Path
) -> None:
    flag = CancelFlag()
    seen: list[str] = []

    def progress(fraction: float, message: str) -> None:
        seen.append(message)
        if message.startswith("rung"):
            flag.cancel()

    stage = SolveStage(workspace=tmp_path / "fields")
    inputs = StageInputs(resolved=resolve(solved.document))
    key = stage.key(inputs)
    store = Store(tmp_path / "store")

    with pytest.raises(Cancelled) as raised:
        store.get_or_compute(key, lambda: stage.run(inputs, progress=progress, cancel=flag))

    logger.info("cancelled after %d progress reports: %s", len(seen), raised.value)
    assert "rung" in str(raised.value), "a cancelled solve must say where it stopped"
    assert any(message.startswith("rung") for message in seen)
    assert not store.contains(key)
    assert not store.location(key.schema, key.hash).exists()
    assert store.misses == 1 and store.hits == 0


def test_ver26_cancelling_inside_a_coupled_rung_stops_between_newton_iterations(
    solved: Run, tmp_path: Path
) -> None:
    flag = CancelFlag()
    seen: list[str] = []

    def progress(fraction: float, message: str) -> None:
        seen.append(message)
        if message.startswith("iteration"):
            flag.cancel()

    stage = SolveStage(workspace=tmp_path / "fields")
    inputs = StageInputs(resolved=resolve(solved.document))
    store = Store(tmp_path / "store")
    key = stage.key(inputs)

    with pytest.raises(Cancelled) as raised:
        store.get_or_compute(key, lambda: stage.run(inputs, progress=progress, cancel=flag))

    logger.info("cancelled after %d progress reports: %s", len(seen), raised.value)
    assert "Newton iteration" in str(raised.value)
    assert any(message.startswith("iteration") for message in seen), (
        "the Newton callback never fired, so this test cancelled between rungs instead"
    )
    assert not store.contains(key)


def test_ver26_the_manifest_names_every_input_hash_the_run_consumed(solved: Run) -> None:
    resolved = resolve(solved.document)
    ingested = ingest(resolved.mesh, resolved)
    mesh_artefact = MeshStage().artefact(ingested)
    materials = MaterialsStage().run(StageInputs(resolved=resolve(solved.document)))
    case_artefact = CaseArtefact(solved.document)

    record = manifest_module.build(
        solved.document,
        case_text=solved.text,
        case_hash=case_artefact.hash,
        input_files={"mesh": solved.mesh_path},
        upstream={
            "mesh": mesh_artefact,
            "materials": materials,
            "solution": solved.artefact,
        },
        mesh=ingested.summary(),
        electrolyte=resolved.electrolyte,
        ladder=solved.artefact.summary,
        stabilisation=str(solved.artefact.summary["stabilisation"]),
    )

    groups = record.groups()
    assert set(groups) == set(manifest_module.GROUPS)

    assert groups["inputs"]["artefacts"]["mesh"]["hash"] == solved.artefact.inputs["mesh"]
    assert groups["inputs"]["artefacts"]["materials"]["hash"] == solved.artefact.inputs["materials"]
    assert groups["inputs"]["artefacts"]["solution"]["hash"] == solved.artefact.hash
    assert groups["inputs"]["case"] == case_artefact.hash
    assert groups["inputs"]["files"]["mesh"]["sha256"] == file_hash(solved.mesh_path)
    assert groups["inputs"]["files"]["mesh"]["sha256"] != solved.artefact.inputs["mesh"]

    assert groups["solver"]["run"]["stages"] == solved.artefact.summary["stages"]
    assert groups["solver"]["run"]["iterations"] == solved.artefact.summary["iterations"]

    geometry = groups["geometry_and_mesh"]
    assert geometry["elements"] == ingested.data.element_count
    assert geometry["content_hash"] == ingested.content_hash
    assert geometry["groups"]["default"] == "interface"
    assert geometry["groups"]["wall"] == "wall"
    assert geometry["quality"]["min_sicn"] > 0.3
    assert geometry["quality"]["min_gamma"] > 0.3
    assert geometry["quality"]["inverted"] == 0

    assert groups["stabilisation"] == {
        "requested": "none",
        "mode": "none",
        "matches_requested": True,
        "parameters": None,
        "parameter_provenance": None,
        "stabilisation_current_A": None,
        "max_cell_peclet": None,
        "peclet": None,
    }

    assert groups["charge"]["status"] == "not run"
    assert groups["charge"]["reason"]


def test_ver26_the_manifest_written_beside_the_run_round_trips(solved: Run, tmp_path: Path) -> None:
    materials = MaterialsStage().run(StageInputs(resolved=resolve(solved.document)))
    case_artefact = CaseArtefact(solved.document)
    record = manifest_module.build(
        solved.document,
        case_text=solved.text,
        case_hash=case_artefact.hash,
        input_files={"mesh": solved.mesh_path},
        upstream={"materials": materials},
        electrolyte=resolve(solved.document).electrolyte,
        ladder=solved.artefact.summary,
        stabilisation=str(solved.artefact.summary["stabilisation"]),
    )

    directory = solved.store.run_directory(solved.document.name, solved.artefact.hash)
    path = record.write(directory)
    read_back = manifest_module.read(path)

    assert read_back["hash"] == record.hash
    assert read_back["case"]["text"] == solved.text
    assert (
        loads_case(str(read_back["case"]["text"])).model_dump() == solved.document.model_dump()
    ), "the embedded case must re-validate to the document that was run"
    assert (directory / manifest_module.CASE_FILENAME).read_text(encoding="utf-8") == solved.text

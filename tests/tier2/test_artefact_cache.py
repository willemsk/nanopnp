"""VER-26 — the content-addressed cache around a real solve (section 5.3.2, FR-25, FR-27).

Tier 1 tests the hash: that it moves when a leaf moves and does not move when
nothing did. What it cannot test is the property the cache actually rests on —
that the key a caller computes *before* the stage runs is the key the stage
produces after it. Those are two different code paths through
:class:`~nanopnp.solve.stage.SolveStage`, and if they ever disagree the store
raises rather than lying, but the run has already been paid for. So the
assertion belongs here, on a stage that really loads a mesh, really climbs the
NUM-18 ladder and really converges.

The solve is deliberately the validated ePNP-NS configuration on a coarse mesh:
a cheaper configuration would key on fewer of the switches the manifest records,
and the point of this file is the key, not the physics. One solve is shared by
the whole module; every other test here is either a hit, a key computation or a
cancellation, and none of them pays for Newton again.

Stabilisation is ``none`` throughout (NUM-11), and the manifest test asserts it
is recorded — a number whose mode is unrecorded is not comparable to the
reference COMSOL run (section 6.4).
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import pytest

from nanopnp.core.hashing import file_hash
from nanopnp.core.stages import CancelFlag, Cancelled
from nanopnp.io import manifest as manifest_module
from nanopnp.io.artefact import CaseArtefact, SolutionArtefact, StageInputs
from nanopnp.io.case import CaseDocument, loads_case, resolve
from nanopnp.io.store import Store
from nanopnp.materials.stage import MaterialsStage
from nanopnp.mesh.adapter import read, write_msh41
from nanopnp.mesh.ingest import MeshStage, MeshVocabularyError, ingest
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.solve.stage import SolveStage

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0
CONCENTRATION_M = 0.1
BIAS_V = 0.02


def case_text(mesh_path: Path, *, bias_V: float = BIAS_V, mesh_format: str = "vol") -> str:
    """Return a case naming ``mesh_path``, in the validated default configuration.

    Two entries are here because the section 5.2.2 ingestion gate now requires
    them, and both were latent errors before it did.
    :class:`~nanopnp.mesh.primitives.CylindricalPoreGeometry` leaves the two
    pore-mouth seams at NGSolve's ``default``, which is an interior fluid-to-fluid
    interface and no wall — mapping it to ``wall`` would put it in the PHY-02
    distance source set and impose no-slip across the middle of the electrolyte.
    And ``physics.solid_permittivities`` gives the membrane its PHY-20 value of
    3.2; without it Poisson carried the electrolyte's eps_r there, about 24 times
    too large, and the ladder converged on it without complaint.
    """
    return f"""
schema: nanopnp/case/v1
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
    """One solve, its store, and the count of times the stage actually ran."""

    store: Store
    document: CaseDocument
    text: str
    mesh_path: Path
    key: SolutionArtefact
    artefact: SolutionArtefact
    computations: list[int]


@pytest.fixture(scope="module")
def solved(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """Mesh a small pore, solve the case through the store, and share the result."""
    work = tmp_path_factory.mktemp("cache")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))

    text = case_text(mesh_path)
    document = loads_case(text)
    store = Store(work / "store")
    stage = SolveStage(workspace=work / "fields")
    inputs = StageInputs(case=document)

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
    """The cache is only a cache if the key is known before the work is done.

    ``get_or_compute`` decides on :meth:`SolveStage.key`, which resolves the
    case, hashes the mesh file and runs stage 8 — and never touches NGSolve. If
    that key disagreed with the artefact the solve emits, every entry in the
    store would be filed under a key nothing will ever ask for again, and the
    cache would silently never hit. The store raises on the mismatch, but only
    after the solve has been paid for, which is why this is asserted directly.
    """
    assert solved.key.hash == solved.artefact.hash
    assert solved.key.parameters == solved.artefact.parameters
    assert solved.key.inputs == solved.artefact.inputs
    assert solved.key.payload == {}, "the key must be computable without doing the work"


def test_ver26_the_key_is_the_same_whether_or_not_stage_8_was_supplied(solved: Run) -> None:
    """Running the solve alone and running it after stage 8 key the same entry.

    A stage that is independently invocable (FR-27) must not produce a different
    artefact because of *how* it was invoked. The materials artefact is a pure
    function of the case, so recomputing it inside the solve and receiving it
    from an earlier stage have to give the same hash — otherwise a pipeline run
    and a stage-alone run would fill the store with two entries for one answer.
    """
    inputs = StageInputs(case=solved.document)
    materials = MaterialsStage().run(inputs)
    with_upstream = SolveStage().key(
        StageInputs(case=solved.document, upstream={"materials": materials})
    )
    assert with_upstream.hash == solved.key.hash
    assert solved.key.inputs["materials"] == materials.hash


def test_ver26_solving_the_same_case_again_is_a_store_hit(solved: Run) -> None:
    """The second run returns the stored artefact and does not re-enter Newton.

    "Does not recompute" is asserted on the compute callable rather than on a
    timing: a solve that took a suspiciously short time is not evidence, and a
    call count is.
    """
    stage = SolveStage()
    inputs = StageInputs(case=solved.document)

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
    # And the payload came back out of the store, not out of the workspace the
    # first run wrote it to: an artefact whose payload is still in a temporary
    # directory is not stored, whatever meta.json says.
    assert again.payload["state"].is_file()
    assert again.payload["state"].parent == solved.store.location(again.schema, again.hash)
    assert not again.hand_substituted


def test_ver26_changing_the_bias_misses_the_cache(solved: Run) -> None:
    """A different operating point is a different key, and the store has nothing.

    Checked on ``contains`` rather than by solving: the assertion is about the
    key, and running the solve again to learn that it misses would double the
    cost of the file for no extra information.
    """
    other = loads_case(case_text(solved.mesh_path, bias_V=BIAS_V + 0.01))
    key = SolveStage().key(StageInputs(case=other))

    assert key.hash != solved.key.hash
    assert key.inputs == solved.key.inputs, "only the case changed, not the inputs it consumed"
    assert solved.store.contains(solved.key)
    assert not solved.store.contains(key)


def test_ver26_the_mesh_enters_the_key_by_content_and_not_by_its_bytes(
    solved: Run, tmp_path: Path
) -> None:
    """The same mesh keys one entry however it was written; a different mesh keys another.

    The mesh reaches the solve's digest as the stage-6 artefact's hash, and that
    artefact is keyed on :attr:`nanopnp.mesh.adapter.MeshData.content_hash` — the
    canonical vertices, connectivity and tag maps — rather than on the file's
    bytes (section 5.3.2). Three things follow, and all three are asserted here
    because each of them is a way the cache could be wrong.

    A mesh hashed by *path* would make a case reproducible only on the machine
    that wrote it. A mesh hashed by its bytes would file the same mesh twice for
    a rewritten header or a re-ordered entity block, which is what any tool that
    touches the file does. And a mesh not hashed at all would let a
    hand-substituted one (FR-27) return the previous mesh's answer out of the
    cache — so the last assertion is the one that has to hold whatever the first
    two cost.
    """
    copied = tmp_path / "elsewhere.vol"
    copied.write_bytes(solved.mesh_path.read_bytes())
    same = SolveStage().key(StageInputs(case=loads_case(case_text(copied))))
    assert same.hash == solved.key.hash

    # Rewritten by another tool, into another format: MSH 4.1 out of the same
    # MeshData the netgen reader produced. Bit-exact through the content hash
    # [tested], which is the claim content addressing is making.
    rewritten = write_msh41(read(solved.mesh_path), tmp_path / "rewritten.msh")
    as_msh = SolveStage().key(
        StageInputs(case=loads_case(case_text(rewritten, mesh_format="gmsh")))
    )
    assert as_msh.inputs["mesh"] == solved.key.inputs["mesh"]
    assert as_msh.hash == solved.key.hash

    # A genuinely different mesh of the same geometry: one boundary-layer height
    # finer, so the wall elements move and the vertex count changes.
    finer_path = tmp_path / "finer.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM / 2).ngmesh.Save(str(finer_path))
    finer = SolveStage().key(StageInputs(case=loads_case(case_text(finer_path))))
    assert finer.inputs["mesh"] != solved.key.inputs["mesh"]
    assert finer.hash != solved.key.hash


def test_ver27_a_boundary_the_run_selects_on_and_the_mesh_lacks_aborts(
    solved: Run, tmp_path: Path
) -> None:
    """VER-27: the same mesh under a mapping that loses ``wall`` is refused.

    The failure the stage-6 gate exists for, at the only place it is visible.
    Under the ``r``-weighted forms the natural condition is the free one
    (NUM-06), so a ``wall`` group nothing supplies imposes no no-slip and no
    no-flux, and the solve converges to a current that is wrong with no residual
    to show for it. The mesh here is the one the module already solved on, so the
    only difference between the run that converged and the run that aborts is the
    name.
    """
    text = case_text(solved.mesh_path).replace(
        "groups: {default: interface}", "groups: {default: interface, wall: interface}"
    )
    with pytest.raises(MeshVocabularyError) as raised:
        SolveStage().key(StageInputs(case=loads_case(text)))
    message = str(raised.value)
    assert "wall" in message
    assert "NUM-06" in message


def test_ver26_cancelling_mid_ladder_leaves_no_artefact_in_the_store(
    solved: Run, tmp_path: Path
) -> None:
    """A cancelled solve raises between rungs and the store holds nothing.

    Cancellation is armed from the progress callback rather than after a fixed
    number of token queries, so the stop lands *between rungs* by construction
    rather than by counting: the first ``rung`` message sets the flag, and the
    next check — the following rung, or a Newton step within this one — raises.
    Counting queries would make the test a function of how many times the stage
    happens to ask, which is a discretisation of the implementation, not of the
    behaviour.
    """
    flag = CancelFlag()
    seen: list[str] = []

    def progress(fraction: float, message: str) -> None:
        seen.append(message)
        if message.startswith("rung"):
            flag.cancel()

    stage = SolveStage(workspace=tmp_path / "fields")
    inputs = StageInputs(case=solved.document)
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
    """The second cancellation granularity: within a rung, not only between them.

    Between rungs is not enough on its own. A single rung of the bias ramp is
    seconds on this mesh and minutes on a production one, so a stage that could
    only be stopped at a rung boundary would appear to ignore the request for as
    long as the rung takes. The damped-Newton callback is the finer point, and it
    is reachable only on the coupled models — the two Poisson-Boltzmann rungs
    take no callback at all, which is why both granularities exist.

    Armed on the first ``iteration`` message, so the stop lands inside a coupled
    rung by construction.
    """
    flag = CancelFlag()
    seen: list[str] = []

    def progress(fraction: float, message: str) -> None:
        seen.append(message)
        if message.startswith("iteration"):
            flag.cancel()

    stage = SolveStage(workspace=tmp_path / "fields")
    inputs = StageInputs(case=solved.document)
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
    """A manifest written from this run reconstructs it (section 5.3.3, IF-08).

    The one assertion that needs a real run is the *agreement* between the
    artefact and the manifest: the manifest's Inputs group is assembled from the
    files and upstream artefacts a caller hands it, and nothing but a test
    checks that those are the same objects the solve actually consumed. A
    manifest naming a different mesh than the one that was solved on is a
    provenance record that cannot reconstruct the run, which section 5.3.3 says
    is not a result.
    """
    resolved = resolve(solved.document)
    ingested = ingest(resolved.mesh, resolved)
    mesh_artefact = MeshStage().artefact(ingested)
    materials = MaterialsStage().run(StageInputs(case=solved.document))
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

    # Every input hash the artefact was keyed on appears in the manifest, from
    # the same source: the mesh and the materials as upstream artefacts.
    assert groups["inputs"]["artefacts"]["mesh"]["hash"] == solved.artefact.inputs["mesh"]
    assert groups["inputs"]["artefacts"]["materials"]["hash"] == solved.artefact.inputs["materials"]
    assert groups["inputs"]["artefacts"]["solution"]["hash"] == solved.artefact.hash
    assert groups["inputs"]["case"] == case_artefact.hash
    # The file is recorded too, by its own bytes, and is deliberately *not* the
    # key: that is the difference content addressing makes (section 5.3.2).
    assert groups["inputs"]["files"]["mesh"]["sha256"] == file_hash(solved.mesh_path)
    assert groups["inputs"]["files"]["mesh"]["sha256"] != solved.artefact.inputs["mesh"]

    # The run really happened, and the record of it is the ladder's own.
    assert groups["solver"]["run"]["stages"] == solved.artefact.summary["stages"]
    assert groups["solver"]["run"]["iterations"] == solved.artefact.summary["iterations"]

    # FR-25: the mesh group carries what the section 5.2.2 gate measured, and
    # which of the file's groups became which vocabulary name. Neither is
    # recoverable from the solution, and a run whose 'wall' was the file's
    # 'default' is a different run from one whose 'wall' was the file's 'wall'.
    geometry = groups["geometry_and_mesh"]
    assert geometry["elements"] == ingested.data.element_count
    assert geometry["content_hash"] == ingested.content_hash
    assert geometry["groups"]["default"] == "interface"
    assert geometry["groups"]["wall"] == "wall"
    assert geometry["quality"]["min_sicn"] > 0.3
    assert geometry["quality"]["min_gamma"] > 0.3
    assert geometry["quality"]["inverted"] == 0

    # NUM-11: unstabilised, recorded, and agreeing with what was asked for.
    #
    # The five remaining entries are ``None`` and not absent, and not zero. This
    # manifest is assembled by hand from the artefact summary rather than by
    # ``io.run``, so nothing handed it the mode's constants, its per-species
    # stabilisation current or the NUM-12 measurement -- and "not measured" is a
    # different fact from "measured and found to be zero", which is what the
    # ``none`` mode genuinely contributes. Collapsing the two would make an
    # unextracted run indistinguishable from an unstabilised one (FR-25).
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

    # The two groups no Phase-1 stage produced say so, with a reason.
    assert groups["charge"]["status"] == "not run"
    assert groups["charge"]["reason"]


def test_ver26_the_manifest_written_beside_the_run_round_trips(solved: Run, tmp_path: Path) -> None:
    """Written and read back, the manifest is byte-identical in content and hash."""
    materials = MaterialsStage().run(StageInputs(case=solved.document))
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

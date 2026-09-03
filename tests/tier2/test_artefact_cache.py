"""The content-addressed cache around a real solve (section 5.3.2, FR-25, FR-27).

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
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.solve.continuation import mesh_report
from nanopnp.solve.stage import SolveStage

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0
CONCENTRATION_M = 0.1
BIAS_V = 0.02


def case_text(mesh_path: Path, *, bias_V: float = BIAS_V) -> str:
    """Return a case naming ``mesh_path``, in the validated default configuration."""
    return f"""
schema: nanopnp/case/v1
name: cache-probe
inputs:
  mesh: {{path: {mesh_path}, format: vol}}
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


def test_fr27_the_key_computed_before_the_solve_is_the_one_it_produces(solved: Run) -> None:
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


def test_fr27_the_key_is_the_same_whether_or_not_stage_8_was_supplied(solved: Run) -> None:
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


def test_fr27_solving_the_same_case_again_is_a_store_hit(solved: Run) -> None:
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


def test_fr27_changing_the_bias_misses_the_cache(solved: Run) -> None:
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


def test_fr27_a_substituted_mesh_is_a_changed_input(solved: Run, tmp_path: Path) -> None:
    """The mesh enters the key by content, so the same file under two names is one run.

    Both halves matter. A mesh hashed by *path* would make a case reproducible
    only on the machine that wrote it; a mesh not hashed at all would let a
    hand-substituted mesh (FR-27) return the previous mesh's answer out of the
    cache.
    """
    copied = tmp_path / "elsewhere.vol"
    copied.write_bytes(solved.mesh_path.read_bytes())
    same = SolveStage().key(StageInputs(case=loads_case(case_text(copied))))
    assert same.hash == solved.key.hash

    edited = tmp_path / "edited.vol"
    edited.write_bytes(solved.mesh_path.read_bytes() + b"\n")
    changed = SolveStage().key(StageInputs(case=loads_case(case_text(edited))))
    assert changed.inputs["mesh"] != solved.key.inputs["mesh"]
    assert changed.hash != solved.key.hash


def test_fr27_cancelling_mid_ladder_leaves_no_artefact_in_the_store(
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


def test_fr27_cancelling_inside_a_coupled_rung_stops_between_newton_iterations(
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


def test_fr25_the_manifest_names_every_input_hash_the_run_consumed(solved: Run) -> None:
    """A manifest written from this run reconstructs it (section 5.3.3, IF-08).

    The one assertion that needs a real run is the *agreement* between the
    artefact and the manifest: the manifest's Inputs group is assembled from the
    files and upstream artefacts a caller hands it, and nothing but a test
    checks that those are the same objects the solve actually consumed. A
    manifest naming a different mesh than the one that was solved on is a
    provenance record that cannot reconstruct the run, which section 5.3.3 says
    is not a result.
    """
    import ngsolve as ngs

    mesh = ngs.Mesh(str(solved.mesh_path))
    materials = MaterialsStage().run(StageInputs(case=solved.document))
    case_artefact = CaseArtefact(solved.document)

    record = manifest_module.build(
        solved.document,
        case_text=solved.text,
        case_hash=case_artefact.hash,
        input_files={"mesh": solved.mesh_path},
        upstream={"materials": materials, "solution": solved.artefact},
        mesh=mesh_report(mesh),
        electrolyte=resolve(solved.document).electrolyte,
        ladder=solved.artefact.summary,
        stabilisation=str(solved.artefact.summary["stabilisation"]),
    )

    groups = record.groups()
    assert set(groups) == set(manifest_module.GROUPS)

    # Every input hash the artefact was keyed on appears in the manifest, from
    # the same source: the mesh by content, the materials artefact by hash.
    assert groups["inputs"]["files"]["mesh"]["sha256"] == solved.artefact.inputs["mesh"]
    assert file_hash(solved.mesh_path) == solved.artefact.inputs["mesh"]
    assert groups["inputs"]["artefacts"]["materials"]["hash"] == solved.artefact.inputs["materials"]
    assert groups["inputs"]["artefacts"]["solution"]["hash"] == solved.artefact.hash
    assert groups["inputs"]["case"] == case_artefact.hash

    # The run really happened, and the record of it is the ladder's own.
    assert groups["solver"]["run"]["stages"] == solved.artefact.summary["stages"]
    assert groups["solver"]["run"]["iterations"] == solved.artefact.summary["iterations"]
    assert groups["geometry_and_mesh"]["elements"] == mesh.ne

    # NUM-11: unstabilised, recorded, and agreeing with what was asked for.
    assert groups["stabilisation"] == {
        "requested": "none",
        "mode": "none",
        "matches_requested": True,
    }

    # The two groups no Phase-1 stage produced say so, with a reason.
    assert groups["charge"]["status"] == "not run"
    assert groups["charge"]["reason"]


def test_fr26_the_manifest_written_beside_the_run_round_trips(solved: Run, tmp_path: Path) -> None:
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

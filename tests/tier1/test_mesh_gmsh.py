"""VER-54: the optional Gmsh backend meshes stage 5's region through netgen's gates (WP23).

On the coarse parallelogram region of ``test_mesh_generate.py`` at ``size_scale``
20, so each mesh is a fraction of a second. The reference-scale meshes, and the
solve on both backends' meshes, are Tier 2's (``tests/tier2/test_mesh_backends.py``).

The area oracle is independent of both meshers: a mesh's straight edges cut each
reservoir arc into chords, and a chord across an arc of angle ``theta`` removes
``R^2 (theta - sin theta) / 2`` from the domain it bounds. The record's areas,
measured by OCC when stage 5 assembled the region, less those segments, are each
domain's triangle area.

The tests that need ``gmsh`` take the ``gmsh_module`` fixture (D11); the refusals
of a missing extra, the default path's imports and the lock file run everywhere.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from nanopnp.core.errors import EXIT_CASE, EXIT_GATE, classify
from nanopnp.core.stages import MissingExtraError
from nanopnp.geometry.profile import (
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
    write_profile,
)
from nanopnp.geometry.region import (
    RegionRecord,
    RegionStage,
    build_region,
    read_region,
    region_graph,
)
from nanopnp.io.artefact import StageInputs
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.generate import generate
from nanopnp.mesh.ingest import MeshStage
from nanopnp.mesh.meshers import _gmsh_backend
from nanopnp.mesh.quality import QUALITY_FLOOR, inverted_elements
from nanopnp.mesh.sizing import SIZES
from nanopnp.pipeline.case import loads_case, resolve

REPOSITORY = Path(__file__).resolve().parents[2]

NETGEN_KEY = "afcc08339531817e4e820f7169753617b946ecadb749b2704fddfc75fc1a836e"
"""Netgen's stage-6 key for the coarse parallelogram case, recorded before WP23 (D8).

Computed on ``2bb1a34`` (the WP23 plan's commit, before any code changed) and on
this package's code alike: a netgen recipe is byte-identical, so no stored key
moved. The key is a hash of the region key and the sizing, whose only computed
float is lambda_D, from arithmetic and a square root, so it is the same on every
platform.
"""

ARC_DOMAINS = {"cis": "electrolyte", "trans": "electrolyte", "membrane_outer": "membrane"}
"""The domain each reservoir-arc boundary bounds."""


CASE = """\
schema: nanopnp/case/v2
name: coarse
inputs:
  profile: {{path: {path}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: 20.0, backend: {backend}}}}}
"""
"""The coarse case of ``test_mesh_generate.py``, with the backend named."""

PARALLELOGRAM = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
"""The slanted body of ``test_mesh_generate.py``, counter-clockwise."""


def _write_profile(path: Path, points: list[tuple[float, float]]) -> Path:
    """Write ``points`` as a profile document."""
    array = np.asarray(points, dtype=np.float64)
    profile = PoreProfile.model_validate(
        {
            "schema": PROFILE_SCHEMA,
            "name": path.stem,
            "provenance": ProfileProvenance(
                source="test",
                citation="tests/tier1/test_mesh_gmsh.py",
                sha256="0" * 64,
                vertex_count=len(points),
                min_vertex_spacing_nm=min_vertex_spacing(array),
                min_feature_size_nm=min_feature_size(array),
                signed_area_nm2=signed_area(array),
            ).model_dump(),
            "vertices": points,
        }
    )
    return write_profile(profile, path)


def _case_text(root: Path, backend: str, profile: str = "profile.yaml") -> str:
    """Return the coarse case over a synthetic profile, meshed by ``backend``."""
    return CASE.format(path=root / profile, backend=backend)


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a directory holding the parallelogram, counter-clockwise and clockwise."""
    root = tmp_path_factory.mktemp("gmsh")
    _write_profile(root / "profile.yaml", PARALLELOGRAM)
    _write_profile(root / "clockwise.yaml", PARALLELOGRAM[::-1])
    return root


@pytest.fixture(scope="module")
def region(workspace: Path):
    """Return the stage-5 artefact of the parallelogram; the backend does not key it (D1)."""
    case = loads_case(_case_text(workspace, "netgen"))
    return RegionStage(workspace=workspace / "region").run(StageInputs(resolved=resolve(case)))


def _chord_corrected_areas(record: RegionRecord, data: MeshData) -> dict[str, float]:
    """Return the record's domain areas less the arc segments the mesh's chords cut off."""
    expected = dict(record.face_areas_nm2)
    radius = record.reservoir_radius_nm
    for boundary, domain in ARC_DOMAINS.items():
        ends = data.vertices[data.edges_of(boundary)]
        a, b = ends[:, 0], ends[:, 1]
        theta = np.abs(np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], np.sum(a * b, axis=1)))
        expected[domain] -= float(np.sum(radius**2 * (theta - np.sin(theta)) / 2.0))
    return expected


def _triangle_areas(data: MeshData) -> dict[str, float]:
    """Return each material's summed signed triangle area."""
    corners = data.vertices[data.triangles]
    signed = 0.5 * (
        (corners[:, 1, 0] - corners[:, 0, 0]) * (corners[:, 2, 1] - corners[:, 0, 1])
        - (corners[:, 2, 0] - corners[:, 0, 0]) * (corners[:, 1, 1] - corners[:, 0, 1])
    )
    return {
        name: float(signed[data.triangle_material == index].sum())
        for index, name in enumerate(data.materials)
    }


@pytest.mark.parametrize("backend", ["netgen", "gmsh"])
def test_ver54_the_same_region_passes_the_same_gates_on_both_backends(
    request: pytest.FixtureRequest, workspace: Path, region, backend: str
) -> None:
    """VER-27, VER-10 and D9 on each backend, one vocabulary, the areas and vertices exact."""
    if backend == "gmsh":
        request.getfixturevalue("gmsh_module")
    case = loads_case(_case_text(workspace, backend))
    inputs = StageInputs(resolved=resolve(case), upstream={"region": region})
    stage = MeshStage(workspace=workspace / f"mesh-{backend}")
    artefact = stage.run(inputs)
    assert artefact.hash == stage.key(inputs).hash
    assert artefact.parameters["materials"] == ["electrolyte", "membrane", "protein"]
    record = read_region(region.payload["region"])
    assert artefact.parameters["boundaries"] == sorted(record.edge_counts)
    summary = artefact.summary
    assert summary["quality"]["min_sicn"] > QUALITY_FLOOR  # type: ignore[index]
    assert summary["quality"]["min_gamma"] > QUALITY_FLOOR  # type: ignore[index]
    sizing = summary["sizing"]
    assert sizing["backend"] == backend  # type: ignore[index]
    assert sizing["backend_version"]  # type: ignore[index]
    assert sizing["wall_statistics"]["mean_ratio"] <= 1.15  # type: ignore[index]

    data = _read(artefact.payload["mesh"])
    assert set(data.materials) == set(record.face_areas_nm2)
    assert set(data.boundaries) == set(record.edge_counts)
    found = _triangle_areas(data)
    for name, expected in _chord_corrected_areas(record, data).items():
        assert found[name] == pytest.approx(expected, rel=1e-10), name
    nodes = set(map(tuple, data.vertices.tolist()))
    graph = region_graph(build_region(record), record)
    assert set(graph.vertices) <= nodes


def _read(path: Path) -> MeshData:
    """Read a generated mesh back through the adapter."""
    from nanopnp.mesh.adapter import read

    return read(path, format="msh41")


def test_ver54_a_clockwise_profile_meshes_with_no_inverted_element(
    gmsh_module: ModuleType, workspace: Path
) -> None:
    """D2: the graph orients every loop counter-clockwise, and that is load-bearing.

    The profile listed clockwise meshes cleanly. Handing Gmsh the protein's loop
    reversed inverts every protein triangle, which is the failure the orientation
    rule exists to prevent.
    """
    import dataclasses

    from nanopnp.mesh import gmsh_backend as backend

    case = loads_case(_case_text(workspace, "gmsh", profile="clockwise.yaml"))
    region = RegionStage(workspace=workspace / "region-cw").run(StageInputs(resolved=resolve(case)))
    record = read_region(region.payload["region"])
    assert record.profile[0] == (5.0, 3.0)  # the profile as supplied, clockwise
    stage = MeshStage(workspace=workspace / "mesh-cw")
    stage.run(StageInputs(resolved=resolve(case), upstream={"region": region}))

    graph = region_graph(build_region(record), record)
    faces = dict(graph.faces)
    faces["protein"] = tuple(~signed for signed in reversed(faces["protein"]))
    reversed_graph = dataclasses.replace(graph, faces=faces)
    data = backend.mesh_region(
        reversed_graph,
        1.0,
        SIZES.scaled(20.0),
        membrane_thickness_nm=record.membrane.thickness_nm,
        axis_extent_nm=record.axis_split_nm,
    )
    protein = set(np.flatnonzero(data.triangle_material == data.materials.index("protein")))
    assert protein and set(inverted_elements(data)) == protein


MESH_IN_A_FRESH_PROCESS = """
import json, sys
from pathlib import Path
from nanopnp.geometry.region import RegionStage
from nanopnp.io.artefact import StageInputs
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.mesh.ingest import MeshStage

root = Path(sys.argv[1])
case = loads_case(Path(sys.argv[2]).read_text())
resolved = resolve(case)
region = RegionStage(workspace=root / "region").run(StageInputs(resolved=resolved))
mesh = MeshStage(workspace=root / "mesh").run(
    StageInputs(resolved=resolved, upstream={"region": region})
)
sys.stderr.write(json.dumps({"content_hash": mesh.summary["content_hash"], "key": mesh.hash}))
"""


def test_ver54_two_fresh_processes_give_one_mesh_and_write_nothing_to_stdout(
    gmsh_module: ModuleType, workspace: Path, tmp_path: Path
) -> None:
    """D5, D6: one thread makes the mesh a function of the recipe; IF-02 keeps stdout empty."""
    case = tmp_path / "case.yaml"
    case.write_text(_case_text(workspace, "gmsh"), encoding="utf-8")
    found = []
    for run in ("first", "second"):
        completed = subprocess.run(
            [sys.executable, "-c", MESH_IN_A_FRESH_PROCESS, str(tmp_path / run), str(case)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert completed.stdout == ""
        found.append(json.loads(completed.stderr.strip().splitlines()[-1]))
    assert found[0] == found[1]


def test_ver54_the_key_moves_with_the_backend_and_netgen_s_does_not_move(
    workspace: Path, region
) -> None:
    """D8: the recipe names the backend and its own settings; netgen's is the one WP21 keyed.

    Needs no ``gmsh``: a key is known without meshing.
    """
    keys = {}
    for backend in ("netgen", "gmsh"):
        case = loads_case(_case_text(workspace, backend))
        # D1: stage 5 is netgen.occ on either backend, so its key does not move.
        assert RegionStage().key(StageInputs(resolved=resolve(case))).hash == region.hash
        keys[backend] = MeshStage().key(
            StageInputs(resolved=resolve(case), upstream={"region": region})
        )
    assert keys["netgen"].hash == NETGEN_KEY
    assert keys["gmsh"].hash != NETGEN_KEY
    netgen = keys["netgen"].parameters["sizing"]
    gmsh = keys["gmsh"].parameters["sizing"]
    assert netgen["optsteps2d"] == 5  # type: ignore[index]
    assert "gmsh" not in netgen  # type: ignore[operator]
    assert "optsteps2d" not in gmsh  # type: ignore[operator]
    assert gmsh["gmsh"] == {  # type: ignore[index]
        "algorithm": 6,
        "smoothing": 5,
        "fields": [
            "boundary-sources-graded",
            "domain-boundary-sources-graded",
            "short-curve-vertices-below-target",
            "membrane-at-thickness-unscaled",
        ],
    }
    assert {k: v for k, v in gmsh.items() if k not in ("backend", "gmsh")} == {  # type: ignore[union-attr]
        k: v
        for k, v in netgen.items()
        if k not in ("backend", "optsteps2d")  # type: ignore[union-attr]
    }


def test_ver54_an_open_gmsh_session_keeps_its_model_and_its_options(
    gmsh_module: ModuleType, workspace: Path, region
) -> None:
    """D6: in a session already open, the adapter works in its own model and restores options.

    Every option the adapter sets is watched, and three are set away from both
    Gmsh's default and the adapter's value first.
    """
    from nanopnp.mesh import gmsh_backend as backend

    gmsh = gmsh_module
    watched = tuple(backend._options(SIZES.scaled(20.0)))
    gmsh.initialize(readConfigFiles=False, interruptible=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("theirs")
        gmsh.option.setNumber("Mesh.Algorithm", 1)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 3.5)
        gmsh.option.setNumber("Mesh.MinimumCurvePoints", 11)
        before = {name: gmsh.option.getNumber(name) for name in watched}
        models = gmsh.model.list()
        resolved = resolve(loads_case(_case_text(workspace, "gmsh")))
        generated = generate(read_region(region.payload["region"]), resolved, workspace / "open")
        assert generated.backend == "gmsh"
        assert gmsh.isInitialized()
        assert gmsh.model.getCurrent() == "theirs"
        assert gmsh.model.list() == models
        assert {name: gmsh.option.getNumber(name) for name in watched} == before
    finally:
        gmsh.finalize()


def test_ver54_the_adapter_writes_nothing_to_stdout_in_process(
    gmsh_module: ModuleType, workspace: Path, region, capfd: pytest.CaptureFixture[str]
) -> None:
    """IF-02 reserves standard output; Gmsh's terminal is off before it can print (D6)."""
    resolved = resolve(loads_case(_case_text(workspace, "gmsh")))
    generate(read_region(region.payload["region"]), resolved, workspace / "quiet")
    assert capfd.readouterr().out == ""


def test_ver54_a_gmsh_failure_is_named_with_its_log_and_leaves_no_session(
    gmsh_module: ModuleType, workspace: Path, region, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QR-12, D6: a mesher failure quotes Gmsh, classifies as a gate, and finalises the session."""
    from nanopnp.mesh import gmsh_backend as backend

    def refuse(dimension: int) -> None:
        raise Exception(f"meshing in dimension {dimension} refused by the test")

    monkeypatch.setattr(gmsh_module.model.mesh, "generate", refuse)
    resolved = resolve(loads_case(_case_text(workspace, "gmsh")))
    with pytest.raises(backend.GmshMeshingError) as caught:
        generate(read_region(region.payload["region"]), resolved, workspace / "refused")
    message = str(caught.value)
    assert f"gmsh {backend.version()} failed to mesh the region" in message
    assert "meshing in dimension 2 refused by the test" in message
    assert "Its log ends:" in message
    assert classify(caught.value) == EXIT_GATE
    assert not gmsh_module.isInitialized()


class _Refuse:
    """A meta-path finder that fails ``import gmsh`` as a bare container or a bare install does."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def find_spec(self, name: str, path: object, target: object = None) -> None:
        """Raise for ``gmsh``; defer everything else."""
        if name == "gmsh" or name.startswith("gmsh."):
            raise self.error


@pytest.mark.parametrize(
    "error",
    [
        ModuleNotFoundError("No module named 'gmsh'", name="gmsh"),
        OSError("libGLU.so.1: cannot open shared object file: No such file or directory"),
    ],
    ids=["missing", "native-library"],
)
def test_ver54_a_missing_extra_is_refused_naming_it(
    workspace: Path, region, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """CON-10, D9: the case resolves; stage 6 refuses it naming the extra and the error."""
    for name in ("gmsh", "nanopnp.mesh.gmsh_backend"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(sys, "meta_path", [_Refuse(error), *sys.meta_path])
    case = loads_case(_case_text(workspace, "gmsh"))
    resolve(case)  # a case refusal would fire here; there is none
    inputs = StageInputs(resolved=resolve(case), upstream={"region": region})
    with pytest.raises(MissingExtraError) as caught:
        MeshStage(workspace=workspace / "missing").run(inputs)
    message = str(caught.value)
    assert "'gmsh' extra" in message
    assert type(error).__name__ in message
    assert str(error).split(":")[0] in message
    assert classify(caught.value) == EXIT_CASE
    with pytest.raises(MissingExtraError):
        _gmsh_backend()


def test_ver54_an_import_error_of_another_module_is_not_blamed_on_gmsh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D9 names the extra only when it is ``gmsh`` that failed to import.

    ``gmsh`` is stubbed, so the test means the same with and without the extra.
    """
    monkeypatch.delitem(sys.modules, "nanopnp.mesh.gmsh_backend", raising=False)
    monkeypatch.setitem(sys.modules, "gmsh", ModuleType("gmsh"))
    monkeypatch.setitem(sys.modules, "nanopnp.mesh.adapter", None)
    with pytest.raises(ModuleNotFoundError) as caught:
        _gmsh_backend()
    assert not isinstance(caught.value, MissingExtraError)


def test_ver54_borrowed_session_preserves_callers_log(
    gmsh_module: ModuleType, workspace: Path, region
) -> None:
    """A borrowed session does not stop or clear the caller's logger (REV-36)."""
    gmsh_module.initialize(readConfigFiles=False, interruptible=False)
    try:
        gmsh_module.logger.start()
        gmsh_module.logger.write("caller custom log message")
        resolved = resolve(loads_case(_case_text(workspace, "gmsh")))
        generate(read_region(region.payload["region"]), resolved, workspace / "borrowed")
        messages = gmsh_module.logger.get()
        assert any("caller custom log message" in m for m in messages)
        gmsh_module.logger.stop()
    finally:
        if gmsh_module.isInitialized():
            gmsh_module.finalize()


def test_ver54_initialize_failure_gives_missing_extra_error(
    gmsh_module: ModuleType, workspace: Path, region, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure of gmsh.initialize raises MissingExtraError (REV-37)."""
    if gmsh_module.isInitialized():
        gmsh_module.finalize()

    def fail_init(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated initialize failure")

    monkeypatch.setattr(gmsh_module, "initialize", fail_init)
    resolved = resolve(loads_case(_case_text(workspace, "gmsh")))
    inputs = StageInputs(resolved=resolved, upstream={"region": region})
    with pytest.raises(MissingExtraError) as caught:
        MeshStage(workspace=workspace / "init_fail").run(inputs)
    message = str(caught.value)
    assert "'gmsh' extra" in message
    assert "simulated initialize failure" in message


def test_ver54_model_remove_failure_handled_in_failing_and_successful_mesh(
    gmsh_module: ModuleType, workspace: Path, region, monkeypatch: pytest.MonkeyPatch
) -> None:
    """model.remove failure is added as note on meshing error, or raised on success (REV-38)."""
    from nanopnp.mesh import gmsh_backend as backend

    def refuse(dimension: int) -> None:
        raise Exception("meshing failed by test")

    def fail_remove() -> None:
        raise RuntimeError("remove failed by test")

    monkeypatch.setattr(gmsh_module.model.mesh, "generate", refuse)
    monkeypatch.setattr(gmsh_module.model, "remove", fail_remove)

    resolved = resolve(loads_case(_case_text(workspace, "gmsh")))
    with pytest.raises(backend.GmshMeshingError) as caught:
        generate(read_region(region.payload["region"]), resolved, workspace / "fail1")
    assert "meshing failed by test" in str(caught.value)
    assert any("remove failed by test" in note for note in getattr(caught.value, "__notes__", []))
    assert not gmsh_module.isInitialized()

    monkeypatch.undo()
    monkeypatch.setattr(gmsh_module.model, "remove", fail_remove)
    with pytest.raises(RuntimeError, match="remove failed by test"):
        generate(read_region(region.payload["region"]), resolved, workspace / "fail2")
    assert not gmsh_module.isInitialized()


KEY_IN_A_FRESH_PROCESS = """
import sys
from pathlib import Path
from nanopnp.geometry.region import RegionStage
from nanopnp.io.artefact import StageInputs
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.mesh.ingest import MeshStage

root = Path(sys.argv[1])
case = loads_case(Path(sys.argv[2]).read_text())
resolve(case)
region = RegionStage(workspace=root / "region").run(StageInputs(resolved=resolve(case)))
MeshStage().key(StageInputs(resolved=resolve(case), upstream={"region": region}))
print("gmsh" in sys.modules)
"""


def test_ver54_a_gmsh_case_resolves_and_keys_without_importing_gmsh(
    workspace: Path, tmp_path: Path
) -> None:
    """CON-10: only meshing imports ``gmsh``; resolving, stage 5 and the key do not.

    The netgen walk's own check is ``test_ver53_two_fresh_processes_give_one_mesh_and_neither_
    imports_gmsh`` in ``test_mesh_generate.py``.
    """
    case = tmp_path / "case.yaml"
    case.write_text(_case_text(workspace, "gmsh"), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-c", KEY_IN_A_FRESH_PROCESS, str(tmp_path), str(case)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip().splitlines()[-1] == "False"


def test_con12_the_lock_names_no_forbidden_mesher() -> None:
    """CON-12: no Triangle, MeshPy, TetGen, nor the stale pygmsh and pygalmesh wrappers."""
    lock = tomllib.loads((REPOSITORY / "uv.lock").read_text(encoding="utf-8"))
    names = {package["name"].lower() for package in lock["package"]}
    assert "gmsh" in names
    assert not names & {"meshpy", "triangle", "tetgen", "pygmsh", "pygalmesh"}

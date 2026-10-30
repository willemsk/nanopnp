"""VER-53: stage 6 generates, gates and keys a mesh from stage 5 (FR-10, VER-10, CON-10)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from nanopnp import Case, Session
from nanopnp.geometry.profile import (
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
    write_profile,
)
from nanopnp.geometry.region import RegionStage, read_region
from nanopnp.io.artefact import StageInputs
from nanopnp.io.store import Store
from nanopnp.mesh.adapter import read
from nanopnp.mesh.generate import WallSizeGateError, generate
from nanopnp.mesh.ingest import MeshStage, MeshVocabularyError, deployed_mesh
from nanopnp.mesh.quality import QUALITY_FLOOR
from nanopnp.mesh.sizing import case_debye_record
from nanopnp.pipeline.case import loads_case, resolve

CASE = """\
schema: nanopnp/case/v0.5
name: coarse
inputs:
  profile: {{path: {path}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{{solids}}}}}
numerics: {{mesh: {{size_scale: 20.0}}}}
"""

SOLIDS = "protein: 20.0, membrane: 3.2"


def _write_parallelogram(path: Path) -> Path:
    points = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
    array = np.asarray(points, dtype=np.float64)
    profile = PoreProfile.model_validate(
        {
            "schema": PROFILE_SCHEMA,
            "name": "parallelogram",
            "provenance": ProfileProvenance(
                source="test",
                citation="tests/tier1/test_mesh_generate.py",
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


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("generate")
    _write_parallelogram(root / "profile.yaml")
    return root


def _case_text(workspace: Path, solids: str = SOLIDS) -> str:
    return CASE.format(path=workspace / "profile.yaml", solids=solids)


@pytest.fixture(scope="module")
def region(workspace: Path):
    case = loads_case(_case_text(workspace))
    return RegionStage(workspace=workspace / "region").run(StageInputs(resolved=resolve(case)))


# VER-10, VER-27
def test_ver53_a_generated_mesh_passes_the_gates_and_is_keyed_on_its_recipe(
    workspace: Path, region
) -> None:
    case = loads_case(_case_text(workspace))
    inputs = StageInputs(resolved=resolve(case), upstream={"region": region})
    stage = MeshStage(workspace=workspace / "mesh")
    key = stage.key(inputs)
    artefact = stage.run(inputs)
    assert artefact.hash == key.hash
    assert dict(artefact.inputs) == {"region": region.hash}
    assert artefact.parameters["groups"] == {}
    assert artefact.parameters["materials"] == ["electrolyte", "membrane", "protein"]
    sizing = artefact.parameters["sizing"]
    assert sizing["wall"]["wall_h_nm"] == pytest.approx(1.0)  # type: ignore[index]
    assert sizing["table"]["global_nm"] == pytest.approx(200.0)  # type: ignore[index]

    summary = artefact.summary
    assert summary["generated"] is True
    quality = summary["quality"]
    assert quality["min_sicn"] > QUALITY_FLOOR  # type: ignore[index]
    statistics = summary["sizing"]["wall_statistics"]  # type: ignore[index]
    assert statistics["mean_ratio"] <= 1.15
    assert statistics["max_ratio"] <= 2.0
    assert summary["sizing"]["wall"]["debye_length_nm"] > 0.0  # type: ignore[index]
    assert "debye_length_nm" not in sizing["wall"]  # type: ignore[operator]

    payload = artefact.payload["mesh"]
    assert read(payload, format="msh41").content_hash == summary["content_hash"]
    consumed = deployed_mesh(resolve(case), artefact)
    assert consumed.content_hash == summary["content_hash"]


def test_ver53_salt_below_ceiling_shares_stage6_key(workspace: Path, region) -> None:
    stage = MeshStage(workspace=workspace / "mesh-keys")

    def key_at(concentration_M: float) -> str:
        text = _case_text(workspace).replace(
            "concentration_M: 1.0", f"concentration_M: {concentration_M}"
        )
        inputs = StageInputs(resolved=resolve(loads_case(text)), upstream={"region": region})
        return stage.key(inputs).hash

    assert key_at(0.15) == key_at(1.0)
    assert key_at(2.0) != key_at(3.0)
    assert key_at(1.0) != key_at(2.0)


def test_ver53_a_shared_mesh_reports_each_run_its_own_debye_length(
    workspace: Path, tmp_path: Path
) -> None:
    store = Store(tmp_path / "store")
    meshes = {}
    targets = {}
    for concentration_M in (0.15, 1.0):
        text = _case_text(workspace).replace(
            "concentration_M: 1.0", f"concentration_M: {concentration_M}"
        )
        path = tmp_path / f"case-{concentration_M}.yaml"
        path.write_text(text, encoding="utf-8")
        result = Session(store, workspace=tmp_path / f"work-{concentration_M}", write=False).run(
            Case.load(path), upto="mesh"
        )
        sizing = result.manifest.geometry_and_mesh["sizing"]
        expected = case_debye_record(resolve(loads_case(text)))
        assert sizing["debye_target_nm"] == pytest.approx(expected["debye_target_nm"])  # type: ignore[index]
        assert sizing["num30_ratio"] == pytest.approx(expected["num30_ratio"])  # type: ignore[index]
        assert sizing["wall"] == expected["wall"]  # type: ignore[index]
        meshes[concentration_M] = result.artefacts["mesh"].hash
        targets[concentration_M] = sizing["debye_target_nm"]  # type: ignore[index]

    assert meshes[0.15] == meshes[1.0]
    assert targets[0.15] != targets[1.0]


def test_ver53_a_consumer_without_the_stage_6_artefact_is_refused(workspace: Path) -> None:
    resolved = resolve(loads_case(_case_text(workspace)))
    with pytest.raises(KeyError, match=r"run the pipeline through 'mesh' first"):
        deployed_mesh(resolved, None)


GENERATE_IN_A_FRESH_PROCESS = """
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
print(json.dumps({
    "content_hash": mesh.summary["content_hash"],
    "key": mesh.hash,
    "gmsh": "gmsh" in sys.modules,
}))
"""


# CON-10
def test_ver53_two_fresh_processes_give_one_mesh_and_neither_imports_gmsh(
    workspace: Path, tmp_path: Path
) -> None:
    case = tmp_path / "case.yaml"
    case.write_text(_case_text(workspace), encoding="utf-8")
    found = []
    for run in ("first", "second"):
        completed = subprocess.run(
            [sys.executable, "-c", GENERATE_IN_A_FRESH_PROCESS, str(tmp_path / run), str(case)],
            capture_output=True,
            text=True,
            check=True,
        )
        found.append(json.loads(completed.stdout.strip().splitlines()[-1]))
    assert found[0] == found[1]
    assert found[0]["gmsh"] is False


def test_ver53_the_wall_gate_fires_when_the_wall_field_is_withheld(
    workspace: Path, region, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nanopnp.mesh import meshers, sizing

    def without_wall(shape, *, wall_h_nm, axis_extent_nm, sizes, divide_wall) -> None:  # type: ignore[no-untyped-def]
        sizing.apply_sizes(
            shape,
            wall_h_nm=None,
            axis_extent_nm=axis_extent_nm,
            sizes=sizes,
            divide_wall=divide_wall,
        )

    monkeypatch.setattr(meshers, "apply_sizes", without_wall)
    record = read_region(region.payload["region"])
    resolved = resolve(loads_case(_case_text(workspace)))
    with pytest.raises(WallSizeGateError) as caught:
        generate(record, resolved, workspace / "withheld")
    message = str(caught.value)
    assert "mean wall segment length" in message
    assert "x the 1.00000 nm target" in message
    assert "midpoint (r, z) = (" in message
    assert caught.value.where.startswith("the longest being wall segment")


def test_ver53_a_generated_mesh_without_a_protein_permittivity_is_refused(
    workspace: Path, region
) -> None:
    case = loads_case(_case_text(workspace, solids="membrane: 3.2"))
    inputs = StageInputs(resolved=resolve(case), upstream={"region": region})
    with pytest.raises(
        MeshVocabularyError, match=r"'protein' with no physics\.solid_permittivities"
    ):
        MeshStage(workspace=workspace / "unpermitted").run(inputs)


def test_qr08_a_reproduced_mesh_with_another_content_hash_aborts_naming_both(
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace

    from nanopnp.api.reproduce import (
        InputMovedError,
        check_mesh,
    )

    manifest = {"geometry_and_mesh": {"generated": True, "content_hash": "a" * 64}}
    same = SimpleNamespace(artefacts={"mesh": SimpleNamespace(summary={"content_hash": "a" * 64})})
    moved = SimpleNamespace(artefacts={"mesh": SimpleNamespace(summary={"content_hash": "b" * 64})})
    check_mesh(manifest, same, where=tmp_path)  # type: ignore[arg-type]
    with pytest.raises(InputMovedError) as caught:
        check_mesh(manifest, moved, where=tmp_path)  # type: ignore[arg-type]
    message = str(caught.value)
    assert "generated mesh has moved" in message
    assert "a" * 64 in message
    assert "b" * 64 in message
    # A run that stopped before stage 6 has no mesh to compare, and is not refused for it.
    check_mesh({"geometry_and_mesh": {"not_run": "x"}}, same, where=tmp_path)  # type: ignore[arg-type]


WALK = """\
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics:
  model: pnp
  flow: false
  variable_density: false
  inertia: false
  solid_permittivities: {{{solids}}}
numerics: {{continuation: none, mesh: {{size_scale: 20.0}}}}
outputs: [current, fields]
"""


def test_ver53_every_consumer_reads_the_generated_mesh_through_to_the_export(
    workspace: Path, tmp_path: Path
) -> None:
    from nanopnp.io.store import Store

    head = _case_text(workspace).split("electrolyte:")[0].replace("name: coarse", "name: walk")
    case = tmp_path / "walk.case.yaml"
    case.write_text(head + WALK.format(solids=SOLIDS), encoding="utf-8")
    result = Session(Store(tmp_path / "store"), workspace=tmp_path / "work").run(Case.load(case))
    assert [record.name for record in result.stages][-4:] == ["materials", "solve", "qoi", "report"]
    assert result.quantities["currents_A"]
    assert result.artefacts["report"].summary["exports"] == ["fields"]
    content_hash = result.manifest.geometry_and_mesh["content_hash"]
    assert content_hash == result.artefacts["mesh"].summary["content_hash"]

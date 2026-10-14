"""Workspace locality: a stage that writes a payload is given its workspace (REV-25, REV-55)."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

from nanopnp.core import stages as registry
from nanopnp.core.paths import store_root
from nanopnp.io.artefact import QOI_SCHEMA, Artefact, StageInputs
from nanopnp.io.workspace import MissingWorkspaceError, scratch_directory
from nanopnp.mesh.ingest import MeshStage
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.post.stage import QoIStage, ReportStage
from nanopnp.solve.stage import SolveStage


def _workspace_stages() -> list[tuple[str, Path]]:
    found = []
    for description in registry.registered_stages():
        if not description.takes_workspace:
            continue
        module = registry._REGISTRY[description.name].target.partition(":")[0]
        origin = importlib.util.find_spec(module).origin  # type: ignore[union-attr]
        found.append((description.name, Path(str(origin))))
    return found


def test_ver25_scratch_directory_is_the_workspace_created(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b"
    assert scratch_directory(target, "mesh") == target
    assert target.is_dir()


def test_ver25_scratch_directory_without_a_workspace_names_the_argument() -> None:
    with pytest.raises(MissingWorkspaceError, match="workspace=<directory>"):
        scratch_directory(None, "mesh")


@pytest.mark.parametrize(("name", "origin"), _workspace_stages(), ids=lambda v: str(v))
def test_ver25_no_workspace_stage_picks_a_scratch_directory_of_its_own(
    name: str, origin: Path
) -> None:
    tree = ast.parse(origin.read_text(encoding="utf-8"))
    called = {
        node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert "scratch_directory" in called, f"stage {name!r} has no scratch_directory call"
    assert "mkdtemp" not in called, f"stage {name!r} makes a temporary directory of its own"
    assert "store_root" not in called, f"stage {name!r} reads the process-default store root"


def test_ver25_the_mesh_stage_without_a_workspace_refuses_scratch(
    cylindrical_pore_case: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NANOPNP_STORE", str(tmp_path / "default-store"))
    resolved = resolve(loads_case(cylindrical_pore_case.read_text(encoding="utf-8")))
    with pytest.raises(MissingWorkspaceError, match="workspace"):
        MeshStage().run(StageInputs(resolved=resolved))
    assert not store_root().exists() or not any(store_root().rglob("*.msh"))


class _ReachedError(Exception):
    pass


def _refuse_work(*arguments: object, **keywords: object) -> None:
    raise _ReachedError


def test_ver25_a_solve_stage_without_a_workspace_refuses_before_it_solves(
    cylindrical_pore_case: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(SolveStage, "_prepare", _refuse_work)
    resolved = resolve(loads_case(cylindrical_pore_case.read_text(encoding="utf-8")))
    with pytest.raises(MissingWorkspaceError, match="solve stage"):
        SolveStage().run(StageInputs(resolved=resolved))


def test_ver25_the_qoi_stage_given_no_solve_refuses_before_it_solves(
    cylindrical_pore_case: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(SolveStage, "_prepare", _refuse_work)
    resolved = resolve(loads_case(cylindrical_pore_case.read_text(encoding="utf-8")))
    with pytest.raises(MissingWorkspaceError, match="solve stage"):
        QoIStage().run(StageInputs(resolved=resolved))


def test_ver25_the_report_stage_hands_its_workspace_to_the_solve_it_runs(
    cylindrical_pore_case: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces: list[Path | None] = []

    def run(self: SolveStage, *arguments: object, **keywords: object) -> None:
        workspaces.append(self._workspace)
        raise _ReachedError

    monkeypatch.setattr(SolveStage, "run", run)
    text = cylindrical_pore_case.read_text(encoding="utf-8").replace(
        "outputs: [current, transport_numbers, eof_rate]", "outputs: [current, fields]"
    )
    inputs = StageInputs(
        resolved=resolve(loads_case(text)),
        upstream={"qoi": Artefact(schema=QOI_SCHEMA, parameters={})},
    )
    with pytest.raises(_ReachedError):
        ReportStage(workspace=tmp_path / "report").run(inputs)
    assert workspaces == [tmp_path / "report" / "solve"]

"""VER-44: the render child: a restored state, a scene on disk, named refusals (NUM-11)."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import math
import re
import tarfile
from pathlib import Path

import pytest

from nanopnp.gui.render import (
    CHI_RANGE,
    READY_FLAG,
    RENDERER_DIRECTORY,
    RENDERER_INTEGRITY,
    RENDERER_SOURCE,
    RENDERER_VERSION,
    VIEWER_DIRNAME,
    ChargeRequest,
    MeshRequest,
    Rendered,
    RenderedCharge,
    RenderedMesh,
    RenderFailed,
    RenderProcess,
    RenderRequest,
    deployed_coefficient,
    host_document,
    readiness_script,
    render,
    render_charge,
    render_mesh,
    renderer_source,
)
from nanopnp.io.store import Store
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import run_case
from nanopnp.post.export import (
    FIXED_CHARGE_ATTRIBUTE,
    attribute_name,
)
from nanopnp.solve.state import STATE_KEY, StateMismatchError

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0

CASE = """
schema: nanopnp/case/v0.5
name: viewer-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
boundary_conditions: {{bias_V: 0.02, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: default_ladder, stabilisation: none}}
outputs: [current]
"""


@pytest.fixture(scope="module")
def finished_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("viewer")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    path = work / "case.yaml"
    path.write_text(CASE.format(mesh_path=mesh_path), encoding="utf-8")
    return run_case(path, store=Store(work / "store")).directory


def _expected_fields(run: Path) -> tuple[str, ...]:
    from nanopnp.gui.render import _state_path
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.pipeline.case import load_case
    from nanopnp.solve.state import restore

    solution = restore(_state_path(run), resolved=resolve(load_case(run / CASE_FILENAME)))
    return tuple(
        attribute_name(declared.name)
        for declared in solution.model.fields
        if declared.element != "number"
    )


def test_ver44_the_child_writes_a_scene_and_reports_the_models_own_fields(
    finished_run: Path,
) -> None:
    rendered = render(RenderRequest(run=str(finished_run)))

    expected = _expected_fields(finished_run)
    assert rendered.fields == expected
    assert rendered.field == expected[0]
    assert rendered.elements > 0

    scene = Path(rendered.scene)
    document = Path(rendered.document)
    assert scene.parent == finished_run / VIEWER_DIRNAME
    assert document.parent == scene.parent
    payload = json.loads(scene.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload["Bezier_trig_points"]


def test_ver44_the_viewer_directory_is_not_an_artefact(finished_run: Path) -> None:
    rendered = render(RenderRequest(run=str(finished_run)))

    record = json.loads((finished_run / "run.json").read_text(encoding="utf-8"))
    written = {Path(name).name for name in record["files"]}
    assert Path(rendered.document).name not in written
    assert Path(rendered.scene).name not in written
    assert VIEWER_DIRNAME not in record["artefacts"]
    assert (finished_run / VIEWER_DIRNAME).is_dir()


def test_ver44_only_one_fields_scene_is_kept(finished_run: Path) -> None:
    expected = _expected_fields(finished_run)
    first = render(RenderRequest(run=str(finished_run), field=expected[0]))
    second = render(RenderRequest(run=str(finished_run), field=expected[-1]))

    assert second.field == expected[-1]
    present = sorted(path.name for path in (finished_run / VIEWER_DIRNAME).iterdir())
    assert present == sorted([Path(second.document).name, Path(second.scene).name])
    assert not Path(first.document).exists()


def test_ver44_a_field_the_solution_does_not_carry_is_refused_by_name(
    finished_run: Path,
) -> None:
    with pytest.raises(KeyError) as refused:
        render(RenderRequest(run=str(finished_run), field="not_a_field"))

    message = str(refused.value)
    assert "not_a_field" in message
    for name in _expected_fields(finished_run):
        assert name in message


def test_ver44_the_document_has_one_rendering_path_and_names_its_renderer() -> None:
    document = host_document('{"a": 1}', renderer="renderer.js", title="a field")

    assert document.count("<script src=") == 1
    assert 'src="renderer.js"' in document
    assert "cdn.jsdelivr.net" not in document
    assert READY_FLAG in document
    assert '{"a": 1}' in document
    assert document.index("renderer_loaded") < document.index("new webgui.Scene()")


def test_ver44_the_renderer_source_is_one_constant() -> None:
    assert renderer_source() == RENDERER_SOURCE
    assert render.__module__ == renderer_source.__module__
    assert RENDERER_SOURCE.startswith("file:")
    assert (RENDERER_DIRECTORY / "webgui.js").is_file()


VENDORED_TARBALL = Path(__file__).resolve().parents[2] / "third_party" / "webgui-0.2.39.tgz"


def test_ver44_vendored_renderer_matches_npm_integrity() -> None:
    assert VENDORED_TARBALL.name == f"webgui-{RENDERER_VERSION}.tgz"
    digest = hashlib.sha512(VENDORED_TARBALL.read_bytes()).digest()
    assert f"sha512-{base64.b64encode(digest).decode()}" == RENDERER_INTEGRITY

    with tarfile.open(VENDORED_TARBALL) as archive:

        def member(name: str) -> bytes:
            extracted = archive.extractfile(name)
            assert extracted is not None, name
            return extracted.read()

        assert member("package/dist/webgui.js") == (RENDERER_DIRECTORY / "webgui.js").read_bytes()
        assert member("package/LICENSE") == (RENDERER_DIRECTORY / "LICENSE.webgui").read_bytes()
        manifest = json.loads(member("package/package.json"))
    assert manifest["version"] == RENDERER_VERSION
    assert manifest["license"] == "LGPL-2.1-or-later"

    spec = importlib.util.find_spec("netgen")
    assert spec is not None and spec.origin is not None
    netgen_webgui = (Path(spec.origin).parent / "webgui.py").read_text(encoding="utf-8")
    pinned = set(re.findall(r"npm/webgui@([0-9.]+)/", netgen_webgui))
    assert pinned == {RENDERER_VERSION}, (
        f"netgen.webgui pins webgui {sorted(pinned)} but the package ships {RENDERER_VERSION}; "
        "refresh the renderer as src/nanopnp/gui/assets/webgui/NOTICE.md describes"
    )

    for text in ("NOTICE.md", "LICENSE.three", "LICENSE.dat-gui"):
        assert (RENDERER_DIRECTORY / text).is_file(), text
    assert RENDERER_INTEGRITY in (RENDERER_DIRECTORY / "NOTICE.md").read_text(encoding="utf-8")


# QR-12
def test_ver44_the_readiness_probe_asks_the_document_what_it_did() -> None:
    script = readiness_script()

    assert READY_FLAG in script
    assert script.startswith("JSON.stringify(")
    assert "||" in script, "the probe gives no answer for a page that never ran its script"
    assert "renderer_loaded" in script


def test_ver44_a_directory_with_no_run_record_is_named_not_guessed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as refused:
        render(RenderRequest(run=str(tmp_path)))

    assert str(tmp_path / "run.json") in str(refused.value)


def test_ver44_a_state_the_gate_refuses_is_reported_as_the_gate_wrote_it(
    finished_run: Path, tmp_path: Path
) -> None:
    from nanopnp.gui.render import _state_path
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.pipeline.case import load_case
    from nanopnp.solve.state import restore

    state = _state_path(finished_run)
    assert state.name.endswith(".npz")
    assert STATE_KEY == "state"

    moved = tmp_path / "moved"
    moved.mkdir()
    (moved / "run.json").write_text(
        (finished_run / "run.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    edited = (
        (finished_run / CASE_FILENAME)
        .read_text(encoding="utf-8")
        .replace("bias_V: 0.02", "bias_V: 0.2")
    )
    (moved / CASE_FILENAME).write_text(edited, encoding="utf-8")

    with pytest.raises(StateMismatchError) as refused:
        render(RenderRequest(run=str(moved)))

    with pytest.raises(StateMismatchError) as directly:
        restore(state, resolved=resolve(load_case(moved / CASE_FILENAME)))

    assert str(refused.value) == str(directly.value)


def test_ver44_the_render_runs_in_a_spawned_child_and_posts_plain_data(
    finished_run: Path,
) -> None:
    process = RenderProcess(RenderRequest(run=str(finished_run)))
    process.start()
    process.join(600.0)
    events = process.drain()

    assert len(events) == 1, events
    rendered = events[0]
    assert isinstance(rendered, Rendered)
    assert Path(rendered.document).is_file()
    assert Path(rendered.scene).is_file()


def test_ver44_a_render_child_killed_before_it_answers_is_not_called_answered(
    tmp_path: Path,
) -> None:
    process = RenderProcess(RenderRequest(run=str(tmp_path / "nowhere")))
    process.start()
    assert not process.answered
    process._process.kill()  # type: ignore[union-attr]
    process.join(300.0)
    assert not process.running
    assert process.drain() == ()
    assert not process.answered


def test_ver44_a_refusal_crosses_the_boundary_as_a_diagnostic(tmp_path: Path) -> None:
    process = RenderProcess(RenderRequest(run=str(tmp_path / "nowhere")))
    process.start()
    process.join(300.0)
    events = process.drain()

    assert len(events) == 1, events
    failed = events[0]
    assert isinstance(failed, RenderFailed)
    assert failed.error == "FileNotFoundError"
    assert "run.json" in failed.message
    assert process.answered


@pytest.mark.parametrize("domain", [None, "membrane", "electrolyte|cis|trans", "absent"])
def test_ver44_the_drawn_region_counts_its_elements_not_its_materials(domain: str | None) -> None:
    import ngsolve as ngs

    from nanopnp.gui.render import _element_count
    from nanopnp.mesh.primitives import CylindricalPoreGeometry

    mesh = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=2.0, wall_h_nm=0.5)
    if domain is None:
        expected = mesh.ne
    else:
        keep = mesh.Materials(domain).Mask()
        expected = sum(1 for element in mesh.Elements(ngs.VOL) if keep[element.index])
    assert _element_count(mesh, domain) == expected
    if domain == "membrane":
        assert 0 < expected < mesh.ne


PROFILE_CASE = """\
schema: nanopnp/case/v0.5
name: mesh-picture
inputs:
  profile: {{path: {path}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: 20.0}}}}
"""


@pytest.fixture(scope="module")
def built_mesh(tmp_path_factory: pytest.TempPathFactory) -> Path:
    import numpy as np

    from nanopnp.geometry.profile import (
        PROFILE_SCHEMA,
        PoreProfile,
        ProfileProvenance,
        min_feature_size,
        min_vertex_spacing,
        signed_area,
        write_profile,
    )

    work = tmp_path_factory.mktemp("mesh-picture")
    points = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
    array = np.asarray(points, dtype=np.float64)
    profile = write_profile(
        PoreProfile(
            schema=PROFILE_SCHEMA,
            name="parallelogram",
            provenance=ProfileProvenance(
                source="test",
                citation="tests/tier1/test_gui_render.py",
                sha256="0" * 64,
                vertex_count=len(points),
                min_vertex_spacing_nm=min_vertex_spacing(array),
                min_feature_size_nm=min_feature_size(array),
                signed_area_nm2=signed_area(array),
            ),
            vertices=points,
        ),
        work / "profile.yaml",
    )
    path = work / "case.yaml"
    path.write_text(PROFILE_CASE.format(path=profile), encoding="utf-8")
    return run_case(path, store=Store(work / "store"), upto="mesh").directory


def _stored_files(run: Path) -> set[Path]:
    record = json.loads((run / "run.json").read_text(encoding="utf-8"))
    root = Path(record["store"])
    return {path for path in root.rglob("*") if path.is_file() and not path.is_relative_to(run)}


def test_ver55_the_mesh_request_draws_the_stage_6_file_and_stores_nothing(
    built_mesh: Path,
) -> None:
    from nanopnp.mesh.adapter import read
    from nanopnp.mesh.quality import QUALITY_FLOOR, element_quality

    record = json.loads((built_mesh / "run.json").read_text(encoding="utf-8"))
    assert "solve" not in record["artefacts"]
    mesh = Store(Path(record["store"])).get(
        record["artefacts"]["mesh"]["schema"], record["artefacts"]["mesh"]["hash"]
    )
    assert mesh is not None
    msh = next(Path(str(value)) for value in mesh.payload.values() if str(value).endswith(".msh"))
    data = read(msh)
    before = _stored_files(built_mesh)

    rendered = render_mesh(MeshRequest(run=str(built_mesh)))

    assert rendered.elements == int(data.triangles.shape[0])
    scene = Path(rendered.scene)
    assert scene.parent == built_mesh / VIEWER_DIRNAME
    assert Path(rendered.document).parent == scene.parent
    assert json.loads(scene.read_text(encoding="utf-8"))["Bezier_trig_points"]
    assert {"protein", "membrane"} <= set(rendered.materials)

    report = element_quality(data)
    assert rendered.quality["min_sicn"] == report.min_sicn
    assert rendered.quality["min_gamma"] == report.min_gamma
    assert rendered.quality["floor"] == QUALITY_FLOOR
    assert rendered.quality["worst_sicn_at_nm"] == report.centroid(report.worst_sicn_element)
    assert rendered.wall == mesh.summary["sizing"]["wall_statistics"]
    assert rendered.wall

    after = json.loads((built_mesh / "run.json").read_text(encoding="utf-8"))
    assert after == record
    assert _stored_files(built_mesh) == before


def test_ver55_a_field_render_leaves_the_mesh_picture(finished_run: Path) -> None:
    drawn = render_mesh(MeshRequest(run=str(finished_run)))
    assert drawn.wall == {}
    render(RenderRequest(run=str(finished_run)))

    assert Path(drawn.document).is_file()
    assert Path(drawn.scene).is_file()


def test_ver55_the_mesh_request_crosses_the_boundary(built_mesh: Path, tmp_path: Path) -> None:
    process = RenderProcess(MeshRequest(run=str(built_mesh)))
    process.start()
    process.join(600.0)
    events = process.drain()
    assert len(events) == 1 and isinstance(events[0], RenderedMesh), events

    process = RenderProcess(MeshRequest(run=str(tmp_path)))
    process.start()
    process.join(300.0)
    events = process.drain()
    assert len(events) == 1 and isinstance(events[0], RenderFailed), events
    assert events[0].error == "FileNotFoundError"


DELTA_AND_SHELL = "{dielectric_transition_nm: 0.2, exclusion_offset_nm: 0.3}"


@pytest.fixture(scope="module")
def charged_run(tmp_path_factory: pytest.TempPathFactory, charged_tube) -> Path:
    work = tmp_path_factory.mktemp("charge-picture")
    case = charged_tube.write(work / "case", charge_block=DELTA_AND_SHELL)
    return run_case(case, store=Store(work / "store"), upto="charge").directory


def _charge_record(run: Path) -> dict[str, object]:
    record = json.loads((run / "run.json").read_text(encoding="utf-8"))
    entry = record["artefacts"]["charge"]
    artefact = Store(Path(record["store"])).get(entry["schema"], entry["hash"])
    assert artefact is not None
    return artefact.summary


def test_ver60_the_charge_request_draws_rho_on_a_zero_centred_range_and_stores_nothing(
    charged_run: Path,
) -> None:
    from ngsolve.webgui import Draw

    record = json.loads((charged_run / "run.json").read_text(encoding="utf-8"))
    before = _stored_files(charged_run)

    rendered = render_charge(ChargeRequest(run=str(charged_run)))

    assert rendered.quantity == "charge"
    assert rendered.name == FIXED_CHARGE_ATTRIBUTE
    assert rendered.units == "C/m^3"
    assert Path(rendered.scene) == charged_run / VIEWER_DIRNAME / "charge.json"
    assert Path(rendered.document) == charged_run / VIEWER_DIRNAME / "charge.html"
    assert json.loads((charged_run / "run.json").read_text(encoding="utf-8")) == record
    assert _stored_files(charged_run) == before

    deployed = deployed_coefficient(charged_run, "charge")
    free = Draw(
        deployed.coefficient, deployed.mesh, show=False, order=deployed.measures.element_order
    ).GetData()
    assert free["funcmin"] < 0.0 < free["funcmax"]
    assert rendered.limit == max(abs(free["funcmin"]), abs(free["funcmax"]))
    assert rendered.colour_range == (-rendered.limit, rendered.limit)
    assert rendered.elements == int(deployed.mesh.ne)

    scene = json.loads(Path(rendered.scene).read_text(encoding="utf-8"))
    assert (scene["funcmin"], scene["funcmax"]) == rendered.colour_range
    assert scene["autoscale"] is False
    assert scene["gui_settings"]["autoscale"] is False
    assert (
        scene["gui_settings"]["colormap_min"],
        scene["gui_settings"]["colormap_max"],
    ) == rendered.colour_range
    assert FIXED_CHARGE_ATTRIBUTE in Path(rendered.document).read_text(encoding="utf-8")


def test_ver60_the_drawn_rho_integrates_to_the_record_s_q_mesh(charged_run: Path) -> None:
    from scipy.constants import elementary_charge

    deployed = deployed_coefficient(charged_run, "charge")
    integral_C = (
        2.0
        * math.pi
        * 1e-27
        * deployed.measures.integrate(deployed.coefficient, deployed.mesh, what="the picture")
    )
    conservation = _charge_record(charged_run)["charge"]["conservation"]  # type: ignore[index]
    assert integral_C / elementary_charge == pytest.approx(conservation["q_mesh_e"], rel=1e-12)
    assert integral_C / elementary_charge == pytest.approx(
        conservation["q_net_e"], rel=conservation["consumer"]["tolerance"]
    )


def test_ver60_the_chi_scene_is_the_derived_chi_on_the_unit_range(charged_run: Path) -> None:
    import ngsolve as ngs

    render_charge(ChargeRequest(run=str(charged_run)))
    rendered = render_charge(ChargeRequest(run=str(charged_run), quantity="chi"))

    assert rendered.quantity == "chi"
    assert rendered.units == "1"
    assert rendered.colour_range == CHI_RANGE == (0.0, 1.0)
    assert 0.0 < rendered.limit <= 1.0
    assert Path(rendered.scene) == charged_run / VIEWER_DIRNAME / "chi.json"
    assert (charged_run / VIEWER_DIRNAME / "charge.json").is_file()

    deployed = deployed_coefficient(charged_run, "chi")
    protein = deployed.mesh.Materials("protein")
    mean = deployed.measures.integrate(
        deployed.coefficient, deployed.mesh, definedon=protein, what="chi over protein"
    ) / deployed.measures.integrate(ngs.CF(1.0), deployed.mesh, definedon=protein)
    recorded = {
        entry["material"]: entry["mean"]
        for entry in _charge_record(charged_run)["eps_r"]["material_means"]  # type: ignore[index]
    }
    assert mean == pytest.approx(recorded["protein"], rel=1e-12)
    assert 0.0 < recorded["protein"] < 1.0


def test_ver60_the_deployed_picture_names_a_generated_shell_s_material(
    charged_run: Path,
) -> None:
    rendered = render_charge(ChargeRequest(run=str(charged_run)))
    assert "exclusion" in rendered.materials
    assert set(rendered.materials) == set(render_mesh(MeshRequest(run=str(charged_run))).materials)


# IF-07
def test_ver60_a_run_with_no_charge_and_no_chi_is_refused_by_name(finished_run: Path) -> None:
    with pytest.raises(KeyError, match="carries no fixed charge"):
        render_charge(ChargeRequest(run=str(finished_run)))
    with pytest.raises(KeyError, match="no solid fraction"):
        render_charge(ChargeRequest(run=str(finished_run), quantity="chi"))
    assert not (finished_run / VIEWER_DIRNAME / "charge.json").exists()


def test_ver60_the_charge_request_crosses_the_boundary(charged_run: Path) -> None:
    process = RenderProcess(ChargeRequest(run=str(charged_run), quantity="chi"))
    process.start()
    process.join(600.0)
    events = process.drain()
    assert len(events) == 1 and isinstance(events[0], RenderedCharge), events
    assert events[0].colour_range == CHI_RANGE


class _DeafChild:
    def __init__(self) -> None:
        self.signals: list[str] = []
        self.alive = True

    def is_alive(self) -> bool:
        return self.alive

    def terminate(self) -> None:
        self.signals.append("terminate")

    def kill(self) -> None:
        self.signals.append("kill")
        self.alive = False

    def join(self, timeout: float | None = None) -> None:
        del timeout


def test_ver44_a_superseded_child_that_ignores_terminate_is_killed() -> None:
    child = _DeafChild()
    process = RenderProcess(RenderRequest(run="unused"), _process=child)  # type: ignore[arg-type]
    process.terminate(timeout=0.0)
    assert child.signals == ["terminate", "kill"]
    assert not process.running

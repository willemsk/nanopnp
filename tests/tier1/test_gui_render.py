"""VER-44 — the render child: a restored state, a scene on disk, and named refusals.

The viewer's whole claim is that the picture is of the operator that was solved,
and every way that claim can fail is on this side of the Qt boundary — which is
why this file runs on the push gate while ``tests/tier1/test_gui_widgets.py``
does not.

**The state comes through the stage-10 gate.** ``restore`` refuses a record that
does not describe this case, this mesh, this discretisation and this model, and
refuses it by name. A viewer that adapted a mismatched record would draw a
picture of an operator nobody solved and have nothing to say about it, so the two
refusals asserted here are the two ways a run directory can fail to yield one:
no record at all, and a record the gate rejects.

**The field vocabulary is the export's.** The names the render child reports are
:func:`nanopnp.io.fields.attribute_name` over the model's own declared fields —
the same function and the same order the IF-07 export writes — so the selector
cannot offer a name the file does not use, and the number under a name cannot be
in different units in the two places.

**The document has one rendering path.** ``netgen.webgui``'s own template
hard-codes a renderer address and ignores the ``template`` argument that looks
like it would redirect it, so the child builds the document itself. What is
asserted is that the document it builds references the renderer it was given and
carries no second script source, and that the renderer it is given by default is
the one shipped with the package, checked against npm's published integrity.

The case is the cheapest one that walks the whole pipeline, as
``tests/tier1/test_run.py`` uses. Stabilisation is ``none`` (NUM-11).
"""

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
from nanopnp.io.fields import FIXED_CHARGE_ATTRIBUTE, attribute_name
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.solve.state import STATE_KEY, StateMismatchError

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0

CASE = """
schema: nanopnp/case/v2
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
    """Run the case once for the module and return its run directory.

    One run for the whole file: what is under test is the render, and a second
    solve would buy nothing but seconds. The same reason
    ``test_gui_solver_process.py`` shares its case fixture.
    """
    work = tmp_path_factory.mktemp("viewer")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    path = work / "case.yaml"
    path.write_text(CASE.format(mesh_path=mesh_path), encoding="utf-8")
    return run_case(path, store=Store(work / "store")).directory


def _expected_fields(run: Path) -> tuple[str, ...]:
    """Return the attribute names this run's model declares, from the model itself.

    The oracle for the field list, taken through the same restore the child
    makes but with the naming done here from ``model.fields`` directly — so a
    child that hard-coded a list, reordered one or dropped the vector field
    fails against the model rather than against a copy of its own answer.
    """
    from nanopnp.gui.render import _state_path
    from nanopnp.io.case import load_case
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.solve.state import restore

    solution = restore(_state_path(run), case=load_case(run / CASE_FILENAME))
    return tuple(
        attribute_name(declared.name)
        for declared in solution.model.fields
        if declared.element != "number"
    )


# -- the scene ----------------------------------------------------------------


def test_ver44_the_child_writes_a_scene_and_reports_the_models_own_fields(
    finished_run: Path,
) -> None:
    """One field is drawn, the scene round-trips, and the vocabulary is the export's."""
    rendered = render(RenderRequest(run=str(finished_run)))

    expected = _expected_fields(finished_run)
    assert rendered.fields == expected
    assert rendered.field == expected[0]
    assert rendered.elements > 0

    scene = Path(rendered.scene)
    document = Path(rendered.document)
    assert scene.parent == finished_run / VIEWER_DIRNAME
    assert document.parent == scene.parent
    # Data, not a rendering of data: the file a reader could open is the scene
    # itself, and it is JSON with the geometry webgui draws in it.
    payload = json.loads(scene.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload["Bezier_trig_points"]


def test_ver44_the_viewer_directory_is_not_an_artefact(finished_run: Path) -> None:
    """The scene lands beside the run's record and is named in none of it.

    §5.3.2 keeps "a cancelled run writes no artefact" meaningful only while a
    picture is not one. Asserted on the run record, which is the file that would
    have to name it for it to be one.
    """
    rendered = render(RenderRequest(run=str(finished_run)))

    record = json.loads((finished_run / "run.json").read_text(encoding="utf-8"))
    written = {Path(name).name for name in record["files"]}
    assert Path(rendered.document).name not in written
    assert Path(rendered.scene).name not in written
    assert VIEWER_DIRNAME not in record["artefacts"]
    assert (finished_run / VIEWER_DIRNAME).is_dir()


def test_ver44_only_one_fields_scene_is_kept(finished_run: Path) -> None:
    """Rendering a second field removes the first one's pair.

    At the reference mesh size a scene is 23 to 39 MB and it is written twice —
    once as data and once inside the document — so five fields kept would be
    hundreds of megabytes of *display* beside a run. The child re-renders
    instead, which costs about a second.
    """
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
    """An unknown field lists the ones there are rather than drawing the first."""
    with pytest.raises(KeyError) as refused:
        render(RenderRequest(run=str(finished_run), field="not_a_field"))

    message = str(refused.value)
    assert "not_a_field" in message
    for name in _expected_fields(finished_run):
        assert name in message


# -- the document -------------------------------------------------------------


def test_ver44_the_document_has_one_rendering_path_and_names_its_renderer() -> None:
    """The built document references the renderer it was given, once, and no other.

    ``netgen.webgui.GenerateHTML`` assigns its ``template`` argument and then
    substitutes into the module global regardless, so a caller cannot redirect
    the renderer through it and this document is built here instead. Counting
    ``<script src=`` is the mechanical form of "one rendering path": a second
    would mean the page could draw with something other than the source the
    diagnostics name.
    """
    document = host_document('{"a": 1}', renderer="renderer.js", title="a field")

    assert document.count("<script src=") == 1
    assert 'src="renderer.js"' in document
    assert "cdn.jsdelivr.net" not in document
    assert READY_FLAG in document
    assert '{"a": 1}' in document
    # Recorded *before* the scene is built, and not derived from the exception:
    # a page whose renderer never arrived throws from the same line a broken
    # scene throws from, so the document has to answer which it was.
    assert document.index("renderer_loaded") < document.index("new webgui.Scene()")


def test_ver44_the_renderer_source_is_one_constant() -> None:
    """The address is read through one function, and it is the shipped file.

    WP15 OQ-1 was ruled on 22 September 2026: the renderer ships with the package,
    so the document needs no network. The source is a ``file:`` URL to a file
    that exists, and it is read through one function so that the viewer, the
    probe and these tests cannot disagree about it.
    """
    assert renderer_source() == RENDERER_SOURCE
    assert render.__module__ == renderer_source.__module__
    assert RENDERER_SOURCE.startswith("file:")
    assert (RENDERER_DIRECTORY / "webgui.js").is_file()


VENDORED_TARBALL = Path(__file__).resolve().parents[2] / "third_party" / "webgui-0.2.39.tgz"
"""The npm tarball kept verbatim as the renderer's corresponding source."""


def test_ver44_vendored_renderer_matches_npm_integrity() -> None:
    """What is drawn with is what npm published, for the version netgen pins.

    Three links, each checked offline:

    - the vendored tarball's SHA-512 is npm's published ``dist.integrity`` for it;
    - the shipped ``webgui.js`` is that tarball's ``package/dist/webgui.js``, byte
      for byte, and the shipped ``LICENSE.webgui`` is its ``package/LICENSE``;
    - :data:`RENDERER_VERSION` is the tarball's own version **and** the version
      the installed ``netgen/webgui.py`` pins, read from its source without
      importing it. The scene ``GetData`` emits is that renderer's input format,
      so an NGSolve upgrade that moves the pin must fail here and not draw
      nothing. ``NOTICE.md`` beside the renderer says how to refresh it.
    """
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


def test_ver44_the_readiness_probe_asks_the_document_what_it_did() -> None:
    """The probe returns an object, and answers even when the page never ran.

    ``loadFinished(True)`` is reached by a page whose renderer never arrived, so
    a probe that could only say "not ready" would leave the panel unable to tell
    a missing renderer from a scene that threw — and those want different
    diagnostics (QR-12). The fallback branch is what makes the probe answer at
    all on a page that never reached its own script.
    """
    script = readiness_script()

    assert READY_FLAG in script
    assert script.startswith("JSON.stringify(")
    assert "||" in script, "the probe gives no answer for a page that never ran its script"
    assert "renderer_loaded" in script


# -- the refusals -------------------------------------------------------------


def test_ver44_a_directory_with_no_run_record_is_named_not_guessed(tmp_path: Path) -> None:
    """A directory that records no run says so, with the path it looked for."""
    with pytest.raises(FileNotFoundError) as refused:
        render(RenderRequest(run=str(tmp_path)))

    assert str(tmp_path / "run.json") in str(refused.value)


def test_ver44_a_state_the_gate_refuses_is_reported_as_the_gate_wrote_it(
    finished_run: Path, tmp_path: Path
) -> None:
    """A payload that does not describe this case is refused, not adapted (QR-12).

    The mismatch is made the way a real one arises — the case is edited after
    the state was written — and the assertion is that the gate's own message
    reaches the caller. A viewer that restated it would be a second wording of
    one fact, and a viewer that adapted the state would draw an operator nobody
    solved.
    """
    from nanopnp.gui.render import _state_path
    from nanopnp.io.case import load_case
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.solve.state import restore

    state = _state_path(finished_run)
    assert state.name.endswith(".npz")
    assert STATE_KEY == "state"

    moved = tmp_path / "moved"
    moved.mkdir()
    (moved / "run.json").write_text(
        (finished_run / "run.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    # The same case at a different bias: a different operator, on the same mesh,
    # which is exactly the substitution the descriptor gate exists to catch.
    edited = (
        (finished_run / CASE_FILENAME)
        .read_text(encoding="utf-8")
        .replace("bias_V: 0.02", "bias_V: 0.2")
    )
    (moved / CASE_FILENAME).write_text(edited, encoding="utf-8")

    with pytest.raises(StateMismatchError) as refused:
        render(RenderRequest(run=str(moved)))

    with pytest.raises(StateMismatchError) as directly:
        restore(state, case=load_case(moved / CASE_FILENAME))

    assert str(refused.value) == str(directly.value)


# -- the process --------------------------------------------------------------


def test_ver44_the_render_runs_in_a_spawned_child_and_posts_plain_data(
    finished_run: Path,
) -> None:
    """The scene is built where NGSolve is, and a path is what crosses.

    Not a mock, for the reason ``test_gui_solver_process.py`` gives: a request
    that does not pickle, or a result that carries a live ``GridFunction``,
    fails here and nowhere else. The scene itself never crosses — at the
    reference mesh size it is tens of megabytes — so what comes back is where it
    was written.
    """
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
    """A render child that dies by signal posts nothing; ``answered`` says so (CR-7).

    The mesh pane reads it once the child has exited, so that "drawing the mesh" does not
    stay on screen for ever over a child that is gone (CODE_REVIEW_003 CR-7).
    """
    process = RenderProcess(RenderRequest(run=str(tmp_path / "nowhere")))
    process.start()
    assert not process.answered
    process._process.kill()  # type: ignore[union-attr]
    process.join(300.0)
    assert not process.running
    assert process.drain() == ()
    assert not process.answered


def test_ver44_a_refusal_crosses_the_boundary_as_a_diagnostic(tmp_path: Path) -> None:
    """The child never dies silently: a refusal comes back named.

    An exception that escaped the worker would leave the parent waiting on a
    queue that will never carry another event, and the panel would sit on
    "rendering" for ever with nothing to show.
    """
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
    """The material mask has one bit per material, so its ``NumSet()`` is not the count.

    The count is taken as an array lookup rather than a Python loop over every
    element on every render, and has to agree with that loop element for element.
    """
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


# -- the stage-6 mesh (WP24 D12) ----------------------------------------------

PROFILE_CASE = """\
schema: nanopnp/case/v2
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
    """Walk a supplied-profile case through stage 6 and return its run directory.

    The coarse slanted body of ``test_artefact_hook.py``: the geometry tab's
    build stops at stage 6 (``--upto mesh``), so the run records a mesh and no
    solve, which is the directory the mesh request is made against.
    """
    import numpy as np

    from nanopnp.mesh.profile import (
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
    """Return every file under the run's store outside the run directory, so an added one shows.

    The default run directory lies under the store root; its ``viewer/`` is where
    the picture belongs, and everything else is where an artefact would be.
    """
    record = json.loads((run / "run.json").read_text(encoding="utf-8"))
    root = Path(record["store"])
    return {path for path in root.rglob("*") if path.is_file() and not path.is_relative_to(run)}


def test_ver55_the_mesh_request_draws_the_stage_6_file_and_stores_nothing(
    built_mesh: Path,
) -> None:
    """The scene holds the MSH's own triangles, lives under ``viewer/`` and is no artefact.

    The oracle is the file stage 6 wrote, read by the adapter rather than by
    NGSolve, so a render that drew a regenerated mesh, or a different one, fails
    on the count. The gate figures are the report's on that same file, and the
    wall statistics the ones the artefact recorded.
    """
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
    """The two pictures share ``viewer/``, and neither sweep removes the other's pair.

    On the supplied-mesh run, which draws its ``inputs.mesh`` and records no wall
    gate because it generated nothing.
    """
    drawn = render_mesh(MeshRequest(run=str(finished_run)))
    assert drawn.wall == {}
    render(RenderRequest(run=str(finished_run)))

    assert Path(drawn.document).is_file()
    assert Path(drawn.scene).is_file()


def test_ver55_the_mesh_request_crosses_the_boundary(built_mesh: Path, tmp_path: Path) -> None:
    """Spawned, the mesh comes back as plain data, and a run with no mesh is refused."""
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


# -- VER-60: the deployed charge and chi ----------------------------------------

DELTA_AND_SHELL = "{dielectric_transition_nm: 0.2, exclusion_offset_nm: 0.3}"
"""A transition width and an ion-exclusion shell, so the walk derives a ``chi``
and generates the ``exclusion`` material. 0.3 nm, because the shell is refused at
or below twice the density grid spacing, 0.1 nm on this case."""


@pytest.fixture(scope="module")
def charged_run(tmp_path_factory: pytest.TempPathFactory, charged_tube) -> Path:
    """Walk the charged tube, with ``delta`` and a shell, through stage 7; return its run."""
    work = tmp_path_factory.mktemp("charge-picture")
    case = charged_tube.write(work / "case", charge_block=DELTA_AND_SHELL)
    return run_case(case, store=Store(work / "store"), upto="charge").directory


def _charge_record(run: Path) -> dict[str, object]:
    """Return the stage-7 artefact's summary the run recorded, read from the store."""
    record = json.loads((run / "run.json").read_text(encoding="utf-8"))
    entry = record["artefacts"]["charge"]
    artefact = Store(Path(record["store"])).get(entry["schema"], entry["hash"])
    assert artefact is not None
    return artefact.summary


def test_ver60_the_charge_request_draws_rho_on_a_zero_centred_range_and_stores_nothing(
    charged_run: Path,
) -> None:
    """``viewer/charge.*``, on ``[-L, L]`` with autoscale off, and no artefact (D7, D8).

    ``L`` is checked against a second draw of the same coefficient left to
    autoscale: the extremes it samples are what the picture shows, so the larger
    magnitude is the limit, and the two signs of the tube's atoms are both in it.
    """
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
    """``2 pi int rho r dA`` of the drawn coefficient, at the solve's order, is ``q_mesh_e`` (D7).

    To 1e-12 relative against the stage-7 record, and to the consumer leg's
    tolerance against the atoms' ``Q_net`` of -1 e: the first says the picture is
    the coefficient stage 7 measured, the second that the measurement is of the
    tube's own charge, units and ``2 pi`` included.
    """
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
    """``viewer/chi.*`` on [0, 1] fixed, its mean over ``protein`` the record's (D7, D8).

    The mean is the ``r``-weighted one stage 7 gated, taken here over the drawn
    coefficient on the deployed mesh, so a picture of a re-derived or
    differently-bound ``chi`` fails on the number. The charge pair from the test
    above is left in place: the two pictures do not sweep each other.
    """
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


def test_ver60_a_generated_shell_s_mesh_lists_exclusion(charged_run: Path) -> None:
    """The geometry tab's picture and the charge pictures both name the shell's material."""
    assert "exclusion" in render_mesh(MeshRequest(run=str(charged_run))).materials
    assert "exclusion" in render_charge(ChargeRequest(run=str(charged_run))).materials


def test_ver60_a_run_with_no_charge_and_no_chi_is_refused_by_name(finished_run: Path) -> None:
    """A run that carried neither is named, never drawn as a zero field (IF-07, QR-12).

    "There was no charge" and "there was one and it was zero" are different
    runs, and a colour map of zeros says the second.
    """
    with pytest.raises(KeyError, match="carries no fixed charge"):
        render_charge(ChargeRequest(run=str(finished_run)))
    with pytest.raises(KeyError, match="no solid fraction"):
        render_charge(ChargeRequest(run=str(finished_run), quantity="chi"))
    assert not (finished_run / VIEWER_DIRNAME / "charge.json").exists()


def test_ver60_the_charge_request_crosses_the_boundary(charged_run: Path) -> None:
    """Spawned, the charge picture comes back as plain data."""
    process = RenderProcess(ChargeRequest(run=str(charged_run), quantity="chi"))
    process.start()
    process.join(600.0)
    events = process.drain()
    assert len(events) == 1 and isinstance(events[0], RenderedCharge), events
    assert events[0].colour_range == CHI_RANGE


class _DeafChild:
    """A render child stuck where SIGTERM is not acted on, as in a long NGSolve call."""

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
    """Returning with the old child alive lets it race the new one in ``viewer/``.

    Each child removes the ``scene-*`` pair it did not write, so a superseded
    render still running can delete the document the panel was just told to load.
    """
    child = _DeafChild()
    process = RenderProcess(RenderRequest(run="unused"), _process=child)  # type: ignore[arg-type]
    process.terminate(timeout=0.0)
    assert child.signals == ["terminate", "kill"]
    assert not process.running

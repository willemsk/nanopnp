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
carries no second script source.

The case is the cheapest one that walks the whole pipeline, as
``tests/tier1/test_run.py`` uses. Stabilisation is ``none`` (NUM-11).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nanopnp.gui.render import (
    READY_FLAG,
    RENDERER_SOURCE,
    VIEWER_DIRNAME,
    Rendered,
    RenderFailed,
    RenderProcess,
    RenderRequest,
    host_document,
    readiness_script,
    render,
    renderer_source,
)
from nanopnp.io.fields import attribute_name
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
schema: nanopnp/case/v1
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
    """The address is read through one function, which is what OQ-1 would change.

    Shipping the renderer as package data so a bundle draws with no network is a
    redistribution question about an LGPL-2.1-or-later work and is the author's
    to answer. Until it is answered the document fetches, which is why the
    readiness probe below exists; what this asserts is that answering it is one
    edit and not a search.
    """
    assert renderer_source() == RENDERER_SOURCE
    assert render.__module__ == renderer_source.__module__


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

"""VER-43 and VER-44: the form binds the whole schema and the panels bind their models (CON-13)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pytest

from nanopnp.gui.case_model import CaseEditor
from nanopnp.gui.convergence import ConvergenceModel
from nanopnp.gui.geometry import MODEL_FRAME, STAGE_1_FRAME, ProfileEditor
from nanopnp.gui.render import Rendered, RenderFailed, RenderProcess
from nanopnp.gui.run_model import RunControl, RunModel
from nanopnp.gui.solver import Failed, Finished, Iteration, Progress, Rung, Started
from nanopnp.io.case_paths import case_fields
from nanopnp.pipeline.case import load_case

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")
os.environ.pop("DISPLAY", None)
os.environ.pop("WAYLAND_DISPLAY", None)

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtWebEngineWidgets import QWebEngineView

    from nanopnp.gui.app import MainWindow
    from nanopnp.gui.widgets import (
        CaseEditorWidget,
        ChargeWidget,
        ConvergenceWidget,
        GeometryWidget,
        RunControlWidget,
        ViewerWidget,
    )
    from nanopnp.gui.widgets.geometry import GeometryCanvas
except (ImportError, OSError) as error:  # pragma: no cover - platform dependent
    pytest.skip(f"PySide6 cannot be constructed here: {error}", allow_module_level=True)

CASE = """
schema: nanopnp/case/v0.5
name: widget-probe
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns, solid_permittivities: {membrane: 3.2}}
numerics: {continuation: default_ladder, stabilisation: none}
"""


@pytest.fixture(scope="module")
def application() -> QtWidgets.QApplication:
    existing = QtWidgets.QApplication.instance()
    if isinstance(existing, QtWidgets.QApplication):
        return existing
    return QtWidgets.QApplication([])


@pytest.fixture
def editor(tmp_path: Path) -> CaseEditor:
    path = tmp_path / "case.yaml"
    path.write_text(CASE, encoding="utf-8")
    return CaseEditor.open(path)


def test_if09_the_form_binds_every_schema_field(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    widget = CaseEditorWidget(editor)
    assert widget.bound_paths() == tuple(reference.path for reference in case_fields())


def test_if09_editing_a_widget_moves_the_document(
    application: QtWidgets.QApplication, editor: CaseEditor, tmp_path: Path
) -> None:
    widget = CaseEditorWidget(editor)
    line = widget.widget_at("boundary_conditions.bias_V")
    assert isinstance(line, QtWidgets.QLineEdit)
    line.setText("0.2")
    line.editingFinished.emit()

    assert editor.staged == {"boundary_conditions.bias_V": 0.2}
    assert widget.commit()
    assert editor.document.boundary_conditions.bias_V == pytest.approx(0.2)
    assert load_case(editor.save()).boundary_conditions.bias_V == pytest.approx(0.2)


def test_if09_a_widget_refuses_what_the_schema_refuses(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    widget = CaseEditorWidget(editor)
    line = widget.widget_at("boundary_conditions.bias_V")
    assert isinstance(line, QtWidgets.QLineEdit)
    line.setText("lots")
    line.editingFinished.emit()

    assert editor.staged == {}
    assert "boundary_conditions.bias_V" in widget.status()
    assert "float" in widget.status()


def test_if09_a_field_the_case_does_not_carry_is_shown_disabled(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    widget = CaseEditorWidget(editor)
    assert not widget.widget_at("structure.source.path").isEnabled()
    assert widget.widget_at("boundary_conditions.bias_V").isEnabled()


def test_if09_a_choice_offers_exactly_the_registered_values(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    widget = CaseEditorWidget(editor)
    combo = widget.widget_at("physics.model")
    assert isinstance(combo, QtWidgets.QComboBox)
    offered = tuple(combo.itemText(index) for index in range(combo.count()))
    assert offered == editor.state("physics.model").options


# QR-11
def test_if09_the_window_assembles_its_seven_panels(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    window = MainWindow(editor)
    tabs = window.centralWidget()
    assert isinstance(tabs, QtWidgets.QTabWidget)
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Case",
        "Geometry",
        "Charge",
        "Run",
        "Convergence",
        "Result",
        "Fields",
    ]
    assert window.windowTitle().endswith("case.yaml")

    charge = tabs.widget(2)
    assert isinstance(charge, ChargeWidget)
    assert charge.control is tabs.widget(1).control
    assert not charge.build_button.isEnabled()
    assert charge.reason()

    run = tabs.widget(3)
    model = run.refresh()
    assert model.state == "idle"
    assert model.fraction == 0.0


# QR-12
def test_if09_the_run_log_shows_every_entry_including_a_multi_line_one(
    application: QtWidgets.QApplication,
) -> None:
    panel = RunControlWidget(RunControl())
    model = panel.control.model
    model.consume([Started(case="case.yaml", store=None)])
    panel.refresh()
    model.consume(
        [
            Failed(
                exit_code=4,
                error="MeshQualityError",
                message="mesh quality gate failed:\n  min SICN 0.12 at (1.0, 2.0)\n  minimum 0.3",
            )
        ]
    )
    panel.refresh()
    model.consume([Progress(fraction=1.0, message="the line after the diagnostic")])
    panel.refresh()

    shown = panel.log_text()
    assert "min SICN 0.12" in shown
    assert "the line after the diagnostic" in shown


def test_if09_run_is_disabled_and_cancel_enabled_from_the_moment_a_run_begins(
    application: QtWidgets.QApplication,
) -> None:
    panel = RunControlWidget(RunControl())
    assert panel.can_start
    assert not panel.can_cancel

    panel.began()
    assert panel.control.model.state == "idle"
    assert not panel.can_start
    assert panel.can_cancel

    panel.control.model.consume(
        [Started(case="case.yaml", store=None), Finished(directory="runs/probe")]
    )
    panel.refresh()
    assert panel.can_start
    assert not panel.can_cancel


def _ladder() -> ConvergenceModel:
    model = RunModel()
    model.consume(
        [
            Started(case="case.yaml", store=None),
            Rung(name="1-pb-linear", stage=1, index=0, total=3, reporting=False, tolerance=1e-6),
            Rung(name="3-equilibrium", stage=3, index=1, total=3, reporting=True, tolerance=1e-6),
            Rung(name="9-salt", stage=9, index=2, total=3, reporting=True, tolerance=1e-6),
            Iteration(iteration=1, residual=1e-2, update=2e-1, damping=0.2, trials=3, forced=False),
            Iteration(iteration=2, residual=1e-8, update=1e-5, damping=1.0, trials=1, forced=False),
            Finished(directory="runs/probe"),
        ]
    )
    return model.convergence


def test_ver44_the_plot_paints_a_real_ladder_without_raising(
    application: QtWidgets.QApplication,
) -> None:
    from PySide6 import QtGui

    panel = ConvergenceWidget(_ladder())
    panel.resize(800, 400)
    panel.refresh()

    pixmap = QtGui.QPixmap(panel.size())
    panel.render(pixmap)
    assert not pixmap.isNull()

    empty = ConvergenceWidget(ConvergenceModel())
    empty.resize(400, 200)
    empty.render(QtGui.QPixmap(empty.size()))


def test_ver44_the_panel_prints_every_bands_note(
    application: QtWidgets.QApplication,
) -> None:
    model = _ladder()
    panel = ConvergenceWidget(model)

    shown = panel.notes_text()
    for band in model.bands:
        assert band.note() in shown
        assert band.name in shown
    assert panel.refresh() is model


def test_ver44_the_viewer_loads_a_file_url_and_never_sets_html(
    application: QtWidgets.QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded: list[QtCore.QUrl] = []
    monkeypatch.setattr(QWebEngineView, "load", lambda _self, url: loaded.append(url))
    monkeypatch.setattr(
        QWebEngineView,
        "setHtml",
        lambda *_args, **_kwargs: pytest.fail("the viewer called setHtml"),
    )

    document = tmp_path / "viewer" / "scene.html"
    document.parent.mkdir()
    document.write_text("<html></html>", encoding="utf-8")

    panel = ViewerWidget()
    panel.model.request(tmp_path)
    panel.apply(
        [
            Rendered(
                document=str(document),
                scene=str(document.with_suffix(".json")),
                field="a_field",
                fields=("a_field", "another_field"),
                elements=124,
            )
        ]
    )

    assert len(loaded) == 1
    assert loaded[0].isLocalFile()
    assert Path(loaded[0].toLocalFile()) == document
    assert panel.offered_fields() == ("a_field", "another_field")
    assert not panel.showing_diagnostic


def test_ver44_a_document_that_drew_nothing_replaces_the_view_with_a_diagnostic(
    application: QtWidgets.QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(QWebEngineView, "load", lambda *_args, **_kwargs: None)

    document = tmp_path / "scene.html"
    document.write_text("<html></html>", encoding="utf-8")
    panel = ViewerWidget()
    panel.model.request(tmp_path)
    panel.apply(
        [
            Rendered(
                document=str(document),
                scene=str(tmp_path / "scene.json"),
                field="a_field",
                fields=("a_field",),
                elements=8,
            )
        ]
    )
    assert not panel.showing_diagnostic

    panel.probed(
        '{"ready": false, "renderer_loaded": false, '
        '"error": "ReferenceError: webgui is not defined", "renderer": "somewhere"}'
    )
    assert panel.showing_diagnostic
    assert panel.model.renderer in panel.diagnostic_text()

    panel.probed('{"ready": true, "renderer_loaded": true, "error": "", "renderer": "somewhere"}')
    assert not panel.showing_diagnostic


def test_ver44_a_refused_render_is_shown_as_the_gate_wrote_it(
    application: QtWidgets.QApplication,
) -> None:
    panel = ViewerWidget()
    panel.model.request("runs/probe")
    panel.apply([RenderFailed(error="StateMismatchError", message="solve.bias_V differs")])

    assert panel.showing_diagnostic
    assert panel.diagnostic_text() == "solve.bias_V differs"
    assert panel.offered_fields() == ()


def test_ver44_clearing_the_viewer_detaches_the_render_in_flight(
    application: QtWidgets.QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stopped: list[str] = []
    monkeypatch.setattr(QWebEngineView, "load", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(RenderProcess, "start", lambda _self: None)
    monkeypatch.setattr(
        RenderProcess, "terminate", lambda self, timeout=1.0: stopped.append(str(self.request.run))
    )
    monkeypatch.setattr(
        RenderProcess,
        "drain",
        lambda self: (
            Rendered(
                document=str(tmp_path / "scene.html"),
                scene=str(tmp_path / "scene.json"),
                field="a_field",
                fields=("a_field",),
                elements=8,
            ),
        ),
    )

    panel = ViewerWidget()
    panel.show_run(tmp_path)
    assert panel.model.state == "rendering"

    panel.show_run(None)
    assert stopped == [str(tmp_path)]
    assert panel.model.state == "idle"
    assert panel.refresh().state == "idle", "the cleared panel drained the previous run's render"


# CON-09
def test_ver44_the_shipped_renderer_reaches_a_document_with_no_network(
    application: QtWidgets.QApplication, tmp_path: Path
) -> None:
    import json

    from PySide6 import QtCore

    from nanopnp.gui.render import host_document, readiness_script, renderer_source

    document = tmp_path / "viewer" / "scene.html"
    document.parent.mkdir()
    document.write_text(
        host_document("{}", renderer=renderer_source(), title="a field"), encoding="utf-8"
    )

    view = QWebEngineView()
    loop = QtCore.QEventLoop()
    loaded: list[bool] = []
    answers: list[object] = []

    def answered(answer: object) -> None:
        answers.append(answer)
        loop.quit()

    def finished(ok: bool) -> None:
        loaded.append(bool(ok))
        view.page().runJavaScript(readiness_script(), answered)

    view.loadFinished.connect(finished)
    QtCore.QTimer.singleShot(60_000, loop.quit)
    view.load(QtCore.QUrl.fromLocalFile(str(document)))
    loop.exec()

    assert loaded == [True], "the document did not finish loading within 60 s"
    assert answers and isinstance(answers[0], str), "the readiness probe returned nothing"
    report = json.loads(answers[0])
    assert report["renderer_loaded"] is True, report
    assert report["renderer"] == renderer_source()


PROFILE_CASE = """\
schema: nanopnp/case/v0.5
name: geometry-probe
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

PARALLELOGRAM = ((2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0))


def _mouse(
    kind: QtCore.QEvent.Type, point: tuple[float, float], *, held: bool
) -> QtGui.QMouseEvent:
    position = QtCore.QPointF(*point)
    button = QtCore.Qt.MouseButton.LeftButton
    return QtGui.QMouseEvent(
        kind,
        position,
        position,
        button if kind != QtCore.QEvent.Type.MouseMove else QtCore.Qt.MouseButton.NoButton,
        button if held else QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )


def test_ver55_a_drag_in_the_editor_moves_the_view_models_vertex(
    application: QtWidgets.QApplication,
) -> None:
    editor = ProfileEditor.from_seed(PARALLELOGRAM, digest="0" * 64, name="parallelogram")
    canvas = GeometryCanvas()
    canvas.resize(400, 400)
    canvas.clear("the contour")
    canvas.attach(editor)
    transform = canvas.transform()
    start = transform.to_screen(*PARALLELOGRAM[1])
    middle = (start[0] + 10.0, start[1] - 5.0)
    end = (start[0] + 20.0, start[1] - 12.0)

    send = QtWidgets.QApplication.sendEvent
    send(canvas, _mouse(QtCore.QEvent.Type.MouseButtonPress, start, held=True))
    send(canvas, _mouse(QtCore.QEvent.Type.MouseMove, middle, held=True))
    assert editor.vertices[1] == PARALLELOGRAM[1], "a drag in progress edited the loop"
    send(canvas, _mouse(QtCore.QEvent.Type.MouseButtonRelease, end, held=False))

    assert canvas.selected == 1
    assert editor.vertices[1] == pytest.approx(transform.to_data(*end))
    assert [vertex for index, vertex in enumerate(editor.vertices) if index != 1] == [
        vertex for index, vertex in enumerate(PARALLELOGRAM) if index != 1
    ]
    assert editor.undo()
    assert tuple(editor.vertices) == PARALLELOGRAM
    assert not editor.can_undo
    assert canvas.caption.endswith(STAGE_1_FRAME)


def test_ver55_the_tab_builds_through_stage_6_and_draws_the_mesh(
    application: QtWidgets.QApplication, tmp_path: Path
) -> None:
    import json

    from nanopnp.geometry.profile import (
        PROFILE_SCHEMA,
        PoreProfile,
        ProfileProvenance,
        min_feature_size,
        min_vertex_spacing,
        signed_area,
        write_profile,
    )

    points = np.asarray(PARALLELOGRAM, dtype=np.float64)
    profile = write_profile(
        PoreProfile(
            schema=PROFILE_SCHEMA,
            name="parallelogram",
            provenance=ProfileProvenance(
                source="test",
                citation="tests/tier1/test_gui_widgets.py",
                sha256="0" * 64,
                vertex_count=len(points),
                min_vertex_spacing_nm=min_vertex_spacing(points),
                min_feature_size_nm=min_feature_size(points),
                signed_area_nm2=signed_area(points),
            ),
            vertices=list(PARALLELOGRAM),
        ),
        tmp_path / "profile.yaml",
    )
    path = tmp_path / "case.yaml"
    path.write_text(PROFILE_CASE.format(path=profile), encoding="utf-8")
    tab = GeometryWidget(CaseEditor.open(path), store=tmp_path / "store")

    tab.build(path)
    deadline = time.monotonic() + BUILD_TIMEOUT_S
    while time.monotonic() < deadline:
        application.processEvents()
        model = tab.refresh()
        if model.settled and (model.state != "finished" or _mesh_shown(tab)):
            break
        time.sleep(0.05)
    model = tab.control.model
    assert model.state == "finished", model.log

    record = json.loads((model.directory / "run.json").read_text(encoding="utf-8"))
    assert [row.name for row in tab.rows] == ["region", "mesh"]
    for row in tab.rows:
        assert row.status == "stored"
        assert row.hash == record["artefacts"][row.name]["hash"]

    tab._select("region")
    assert tab.canvas.caption.endswith(MODEL_FRAME)
    assert _mesh_shown(tab), tab.details()
    tab.shutdown()


BUILD_TIMEOUT_S = 300.0


def _mesh_shown(tab: GeometryWidget) -> bool:
    tab._select("mesh")
    return "minimum SICN" in tab.details()


STRUCTURE_CASE = """\
schema: nanopnp/case/v0.5
name: fragment
structure:
  source: {{path: {path}}}
  symmetry: {{point_group: C1, axis: z}}
{charge}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""


def _structure_case(tmp_path: Path, charge: str) -> Path:
    path = tmp_path / "case.yaml"
    path.write_text(
        STRUCTURE_CASE.format(path=tmp_path / "fragment.pdb", charge=charge), encoding="utf-8"
    )
    return path


@pytest.mark.parametrize(("written", "shown"), [("7.25", 7.25), ("7.1234", 7.123)])
def test_ver60_a_loaded_ph_is_shown_and_not_rewritten(
    application: QtWidgets.QApplication, tmp_path: Path, written: str, shown: float
) -> None:
    path = _structure_case(tmp_path, f"charge: {{ph: {written}}}")
    before = path.read_bytes()
    editor = CaseEditor.open(path)
    widget = CaseEditorWidget(editor)
    spin = widget.widget_at("charge.ph")
    assert isinstance(spin, QtWidgets.QDoubleSpinBox)
    assert (spin.minimum(), spin.maximum()) == editor.state("charge.ph").bounds == (0.0, 14.0)
    assert spin.isEnabled()
    assert spin.value() == pytest.approx(shown, abs=1e-12)

    spin.editingFinished.emit()
    application.processEvents()
    assert editor.staged == {}
    assert not editor.dirty
    assert editor.ensure_saved() == path
    assert path.read_bytes() == before
    assert load_case(path).charge.ph == float(written)  # type: ignore[union-attr]

    spin.setValue(6.5)
    assert editor.staged == {"charge.ph": 6.5}
    assert widget.commit()
    assert editor.document.charge.ph == 6.5  # type: ignore[union-attr]


def test_ver60_add_section_creates_charge_and_enables_the_ph(
    application: QtWidgets.QApplication, tmp_path: Path
) -> None:
    from nanopnp.io.case import Charge

    path = _structure_case(tmp_path, "")
    editor = CaseEditor.open(path)
    widget = CaseEditorWidget(editor)
    spin = widget.widget_at("charge.ph")
    assert isinstance(spin, QtWidgets.QDoubleSpinBox)
    assert not spin.isEnabled()
    assert widget.addable() == ("charge",)

    assert widget.add_section("charge")
    assert spin.isEnabled()
    assert spin.value() == Charge().ph
    assert widget.widget_at("charge.forcefield").isEnabled()
    assert widget.addable() == ()
    assert editor.staged == {}
    assert editor.dirty
    assert editor.ensure_saved() == path
    assert load_case(path).charge == Charge()


@pytest.mark.parametrize(
    ("annotation", "spin_type", "bounds", "step"),
    [(int, "QSpinBox", (1, 9), 1), (float, "QDoubleSpinBox", (0.0, 14.0), 0.1)],
    ids=["int", "float"],
)
def test_ver60_a_bounded_integer_steps_by_whole_numbers(
    application: QtWidgets.QApplication,
    tmp_path: Path,
    annotation: type,
    spin_type: str,
    bounds: tuple[float, float],
    step: float,
) -> None:
    from nanopnp.gui.case_model import FieldState
    from nanopnp.io.case_paths import FieldReference

    editor = CaseEditor.open(_structure_case(tmp_path, "charge: {ph: 7.0}"))
    widget = CaseEditorWidget(editor)
    state = FieldState(
        reference=FieldReference(path="charge.synthetic", annotation=annotation),  # type: ignore[arg-type]
        value=bounds[0],
        options=None,
        kind="bounded",
        bounds=(float(bounds[0]), float(bounds[1])),
    )
    built = widget._build(state)
    assert type(built).__name__ == spin_type
    assert isinstance(built, QtWidgets.QSpinBox | QtWidgets.QDoubleSpinBox)
    assert (built.minimum(), built.maximum()) == bounds
    assert built.singleStep() == step
    assert editor.staged == {}


def test_ver60_an_integer_range_a_spin_box_cannot_hold_is_a_numeric_entry(
    application: QtWidgets.QApplication, tmp_path: Path
) -> None:
    from nanopnp.gui.case_model import FieldState
    from nanopnp.io.case_paths import FieldReference

    editor = CaseEditor.open(_structure_case(tmp_path, "charge: {ph: 7.0}"))
    widget = CaseEditorWidget(editor)
    state = FieldState(
        reference=FieldReference(path="charge.synthetic", annotation=int),  # type: ignore[arg-type]
        value=1,
        options=None,
        kind="bounded",
        bounds=(0.0, 1e10),
    )
    built = widget._build(state)
    assert isinstance(built, QtWidgets.QLineEdit)
    assert built.text() == "1"
    assert editor.staged == {}


def test_ver60_the_charge_tab_starts_no_walk_of_its_own() -> None:
    assert not hasattr(ChargeWidget, "build")
    assert hasattr(ChargeWidget, "follow")
    assert hasattr(MainWindow, "build_charge")


def test_ver60_the_charge_tab_builds_stage_7_and_shows_its_panes(
    application: QtWidgets.QApplication, tmp_path: Path, charged_tube
) -> None:
    import json

    from nanopnp.post.export import FIXED_CHARGE_ATTRIBUTE

    case = charged_tube.write(tmp_path / "case", charge_block="{dielectric_transition_nm: 0.2}")
    window = MainWindow(CaseEditor.open(case), store=tmp_path / "store")
    tabs = window.centralWidget()
    assert isinstance(tabs, QtWidgets.QTabWidget)
    geometry, charge = tabs.widget(1), tabs.widget(2)
    assert isinstance(geometry, GeometryWidget) and isinstance(charge, ChargeWidget)
    assert charge.build_button.isEnabled(), charge.reason()

    window.build_charge()
    deadline = time.monotonic() + BUILD_TIMEOUT_S
    while time.monotonic() < deadline:
        application.processEvents()
        geometry.refresh()
        model = charge.refresh()
        if (
            model is not None
            and model.settled
            and (model.state != "finished" or charge.drawn is not None)
        ):
            break
        time.sleep(0.05)
    model = charge.control.model
    assert model.state == "finished", model.log
    assert charge.drawn is not None, charge.notes("Deployed field")

    record = json.loads((model.directory / "run.json").read_text(encoding="utf-8"))
    assert [row.name for row in geometry.rows] == ["region", "mesh"]
    assert [row.name for row in charge.rows] == ["protonation", "charge"]
    for row in (*geometry.rows, *charge.rows):
        assert row.status == "stored"
        assert row.hash == record["artefacts"][row.name]["hash"]

    table = charge.protonation_table
    q_net_e = sum(atom[4] for atom in charged_tube.atoms)
    assert table.rowCount() == 1
    assert [table.item(0, column).text() for column in (0, 1, 3, 4)] == [
        "A",
        "GLU 18",
        f"{q_net_e:+.4g}",
        "not computed",
    ]
    assert len(charge.canvas.planes) == 2
    assert charge.canvas.caption.endswith(MODEL_FRAME)
    assert charge.conservation_table.rowCount() == 5
    assert charge.drawn.name == FIXED_CHARGE_ATTRIBUTE
    assert MODEL_FRAME in charge.notes("Deployed field")
    assert "transition_nm" in charge.notes("Deployed field")
    window.close()

"""VER-43 and VER-44 — the form binds the whole schema, and the panels bind their models.

The only file in the suite that constructs a Qt object, and the reason the rest
of them do not. ``PySide6.QtWidgets`` raises ``ImportError: libEGL.so.1`` in the
development container and on ``ubuntu-latest`` (`.knowledge/07-software-stack.md`
§5) — the package imports and a GL-dependent payload then fails to ``dlopen``,
which is the same failure class the gmsh wheel has at
``tests/tier1/test_mesh_quality.py``. So the skip idiom is
``except (ImportError, OSError)`` and never ``pytest.importorskip``, and the
coverage this file provides is made on ``windows-latest`` and ``macos-latest``,
where Qt's platform plugin works unaided — two of the three platforms CON-13
names, which is a better claim than a Linux job with hand-installed system
packages could make.

Nothing here asserts a pixel. What is asserted is the binding: that every field
of the schema has a widget, that a widget's edit reaches the document, that a
value the schema refuses is refused at the field with the message the command
line gives, that the convergence plot paints a real ladder without raising, and
that the field viewer loads a **file** URL and never ``setHtml``.

That last one is a size claim rather than a style one. ``setHtml``
percent-encodes its argument into a data URL and a scene of the reference mesh is
23 to 39 MB (`.knowledge/07-software-stack.md` §5), so the call that must never
happen is asserted to never happen rather than merely not written.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nanopnp.gui.case_model import CaseEditor
from nanopnp.gui.convergence import ConvergenceModel
from nanopnp.gui.render import Rendered, RenderFailed, RenderProcess
from nanopnp.gui.run_model import RunControl, RunModel
from nanopnp.gui.solver import Failed, Finished, Iteration, Progress, Rung, Started
from nanopnp.io.case import case_fields, load_case

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtWidgets
    from PySide6.QtWebEngineWidgets import QWebEngineView

    from nanopnp.gui.app import MainWindow
    from nanopnp.gui.widgets import (
        CaseEditorWidget,
        ConvergenceWidget,
        RunControlWidget,
        ViewerWidget,
    )
except (ImportError, OSError) as error:  # pragma: no cover - platform dependent
    pytest.skip(f"PySide6 cannot be constructed here: {error}", allow_module_level=True)

CASE = """
schema: nanopnp/case/v1
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
    """One ``QApplication`` for the module; Qt allows no second one."""
    existing = QtWidgets.QApplication.instance()
    if isinstance(existing, QtWidgets.QApplication):
        return existing
    return QtWidgets.QApplication([])


@pytest.fixture
def editor(tmp_path: Path) -> CaseEditor:
    """Return a case file open for editing."""
    path = tmp_path / "case.yaml"
    path.write_text(CASE, encoding="utf-8")
    return CaseEditor.open(path)


def test_if09_the_form_binds_every_schema_field(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    """Every field of ``nanopnp/case/v1`` has a widget, in declaration order.

    A form that bound a subset would leave part of the schema uneditable with
    nothing to say so — which is the same failure
    :func:`~nanopnp.io.case.case_fields` exists to prevent one level down, and
    the reason the two are asserted equal rather than merely overlapping.
    """
    widget = CaseEditorWidget(editor)
    assert widget.bound_paths() == tuple(reference.path for reference in case_fields())


def test_if09_editing_a_widget_moves_the_document(
    application: QtWidgets.QApplication, editor: CaseEditor, tmp_path: Path
) -> None:
    """A typed value is staged, committed and saved, and the file carries it.

    The whole chain in one assertion, because each link is where it could break
    silently: a widget that never staged, a commit that never substituted, or a
    save that wrote the document the editor started from.
    """
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
    """A value the field cannot hold is reported at the field, not at the commit.

    And the message is the one :meth:`~nanopnp.io.case.FieldReference.validate`
    writes, which is what the sweep planner prints for the same mistake — one
    error vocabulary rather than one per shell.
    """
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
    """A field of a block this case omits is visible and not editable.

    :func:`~nanopnp.io.case.substitute` refuses to write into a section that is
    not there — "give the base case that section first" — so the form shows the
    refusal rather than hiding the field and making it look unimplemented.
    """
    widget = CaseEditorWidget(editor)
    assert not widget.widget_at("structure.source.pdb").isEnabled()
    assert widget.widget_at("boundary_conditions.bias_V").isEnabled()


def test_if09_a_choice_offers_exactly_the_registered_values(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    """A combo box's items are the view-model's options and nothing else."""
    widget = CaseEditorWidget(editor)
    combo = widget.widget_at("physics.model")
    assert isinstance(combo, QtWidgets.QComboBox)
    offered = tuple(combo.itemText(index) for index in range(combo.count()))
    assert offered == editor.state("physics.model").options


def test_if09_the_window_assembles_its_five_panels(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    """The whole window builds offscreen: all five panels of the QR-11 increment.

    Constructed rather than merely imported, because the failures this catches
    are construction-time ones — a signal connected to a slot that does not take
    its arguments, a layout given a widget twice, a panel reading a view-model
    attribute that has been renamed. None of them shows up until a
    ``QApplication`` exists, which is why this test runs where one can.
    """
    window = MainWindow(editor)
    tabs = window.centralWidget()
    assert isinstance(tabs, QtWidgets.QTabWidget)
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Case",
        "Run",
        "Convergence",
        "Result",
        "Fields",
    ]
    assert window.windowTitle().endswith("case.yaml")

    # The run panel polls a control that has never been started: it must read as
    # idle rather than raise, because that is its state for as long as the user
    # is editing.
    run = tabs.widget(1)
    model = run.refresh()
    assert model.state == "idle"
    assert model.fraction == 0.0


def test_if09_the_run_log_shows_every_entry_including_a_multi_line_one(
    application: QtWidgets.QApplication,
) -> None:
    """A QR-12 diagnostic spanning four lines does not stop the log.

    The panel counts log *entries*, not the rendered lines of its own widget. A
    gate abort names the gate, the offending quantity and its location, so one
    entry routinely renders as several; counting rendered lines would leave the
    panel permanently ahead of the model and drop every line after the first
    multi-line one — with nothing to say it had.
    """
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
    """The buttons follow the panel, not the model's state.

    ``RunControl.start`` spawns the child and returns; the model reads ``idle``
    until the child posts its first event, which is a ``spawn`` re-import of
    NGSolve away. A panel keyed on ``state == "running"`` would leave "Run"
    enabled across that window — a second click reaching a control that already
    has a run in flight, which raises — and leave "Cancel" disabled exactly
    while the slowest part of starting up is happening.
    """
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


# -- the convergence plot ------------------------------------------------------


def _ladder() -> ConvergenceModel:
    """Return a model carrying the three kinds of band the real ladder produces."""
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
    """The panel renders into a pixmap, which is the only way its painter runs.

    Constructed *and painted*, because every failure this catches is a paint-time
    one: a zero-width frame divided into, a band extent read from a model that
    has none, a polyline built from an empty point list. None of them shows up
    until something asks the widget to draw.
    """
    from PySide6 import QtGui

    panel = ConvergenceWidget(_ladder())
    panel.resize(800, 400)
    panel.refresh()

    pixmap = QtGui.QPixmap(panel.size())
    panel.render(pixmap)
    assert not pixmap.isNull()

    # An empty model paints too: that is the panel's state before any run, and
    # the axis has to survive a zero span rather than divide by it.
    empty = ConvergenceWidget(ConvergenceModel())
    empty.resize(400, 200)
    empty.render(QtGui.QPixmap(empty.size()))


def test_ver44_the_panel_prints_every_bands_note(
    application: QtWidgets.QApplication,
) -> None:
    """The reasons a band is empty are on screen, not only in the model.

    The plot cannot draw "this rung takes no Newton callback"; the note is where
    that is said, and a panel that computed its own summary would be a second
    reading of the same numbers.
    """
    model = _ladder()
    panel = ConvergenceWidget(model)

    shown = panel.notes_text()
    for band in model.bands:
        assert band.note() in shown
        assert band.name in shown
    assert panel.refresh() is model


# -- the field viewer ----------------------------------------------------------


def test_ver44_the_viewer_loads_a_file_url_and_never_sets_html(
    application: QtWidgets.QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A rendered scene arrives as ``QUrl.fromLocalFile`` and ``setHtml`` is not called.

    Asserted by replacing both methods, because "we never call it" is a claim
    about code that is easy to break by accident and impossible to see in a
    screenshot: a data URL of a 23 MB scene fails somewhere inside Qt, not here.
    """
    from PySide6 import QtCore

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
    """The probe's verdict decides what the panel shows, and the panel says the source.

    The diagnostic *replaces* the view rather than sitting under it: a blank
    rectangle with a warning below still reads as a picture that happens to be
    empty, which is the reading QR-12 refuses.
    """
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
    """A refusal replaces the view and carries the diagnostic verbatim."""
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
    """A cleared panel stops draining the render it was showing, and stops it.

    The window clears the viewer before every new run, for the reason it clears
    the result panel: the previous run's picture beside this run's numbers would
    be two runs presented as one. A render already in flight defeats that unless
    the child is *forgotten* as well — it posts seconds later, the 200 ms poll
    drains it, and the panel loads the previous run's document into the pane it
    was just told to empty. It is stopped as well as forgotten because two
    children of one run each sweep the other's ``scene-*`` pair out of
    ``viewer/``.
    """
    stopped: list[str] = []
    monkeypatch.setattr(QWebEngineView, "load", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(RenderProcess, "start", lambda _self: None)
    monkeypatch.setattr(
        RenderProcess, "terminate", lambda self, timeout=1.0: stopped.append(str(self.request.run))
    )
    # A child that answers the moment it is asked, which is what makes the
    # clear's effect visible: without the detach the drain below would arrive.
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

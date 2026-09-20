"""VER-43 — the form binds the whole schema, and editing it moves the document.

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
of the schema has a widget, that a widget's edit reaches the document, and that
a value the schema refuses is refused at the field with the message the command
line gives.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nanopnp.gui.case_model import CaseEditor
from nanopnp.io.case import case_fields, load_case

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtWidgets

    from nanopnp.gui.app import MainWindow
    from nanopnp.gui.widgets import CaseEditorWidget
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


def test_if09_the_window_assembles_its_three_panels(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    """The whole window builds offscreen: the case, the run panel and the result.

    Constructed rather than merely imported, because the failures this catches
    are construction-time ones — a signal connected to a slot that does not take
    its arguments, a layout given a widget twice, a panel reading a view-model
    attribute that has been renamed. None of them shows up until a
    ``QApplication`` exists, which is why this test runs where one can.
    """
    window = MainWindow(editor)
    tabs = window.centralWidget()
    assert isinstance(tabs, QtWidgets.QTabWidget)
    assert [tabs.tabText(index) for index in range(tabs.count())] == ["Case", "Run", "Result"]
    assert window.windowTitle().endswith("case.yaml")

    # The run panel polls a control that has never been started: it must read as
    # idle rather than raise, because that is its state for as long as the user
    # is editing.
    run = tabs.widget(1)
    model = run.refresh()
    assert model.state == "idle"
    assert model.fraction == 0.0

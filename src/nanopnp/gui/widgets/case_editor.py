"""The case form, built from the schema at run time (IF-09).

One row per field :func:`~nanopnp.io.case.case_fields` yields, in declaration
order, grouped by the block it lives in. The widget chosen for a row comes from
:attr:`~nanopnp.gui.case_model.FieldState.kind` and its contents from
:attr:`~nanopnp.gui.case_model.FieldState.options`; no option list, no default
and no unit is written here.

**A free line holds YAML, because a case file does.** ``1e-3``, ``auto``,
``{membrane: 3.2}`` and an empty line meaning "nothing" are all values a reader
already writes in the case file, so the line edits parse with the same loader
rather than with a second syntax. What the parse produces is then validated at
the field by the schema's declared type, which is the diagnostic the command
line gives for the same mistake.

**A field the document does not carry is shown and disabled**, not hidden. A
Phase-1 case has no ``structure:`` block, and
:func:`~nanopnp.io.case.substitute` refuses to write into one that is absent —
"give the base case that section first". Hiding the field would make that
refusal look like a missing feature.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from PySide6 import QtCore, QtWidgets

from nanopnp.gui.case_model import Absent, CaseEditor, FieldState
from nanopnp.io.case import CaseValidationError, FieldValue

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Callable

__all__ = ["CaseEditorWidget"]


def _display(value: FieldValue | Absent) -> str:
    """Render a case value as the text a reader would have typed for it."""
    if isinstance(value, Absent) or value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, (dict, list, tuple)):
        return str(yaml.safe_dump(value, default_flow_style=True, sort_keys=False)).strip()
    return str(value)


def _parse(text: str) -> FieldValue:
    """Parse a line of a form the way a case file would be parsed.

    An empty line is ``None`` rather than ``""``: a reader clearing an optional
    field means "nothing here", and the schema says whether that is admissible.
    """
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return yaml.safe_load(stripped)
    except yaml.YAMLError:
        # Not YAML at all: hand the raw text on, so the field's own type says
        # what is wrong with it rather than the parser.
        return text


class CaseEditorWidget(QtWidgets.QWidget):
    """A form over one :class:`~nanopnp.gui.case_model.CaseEditor`."""

    changed = QtCore.Signal()
    """Emitted when a field is edited, whether or not the value was accepted."""

    def __init__(self, editor: CaseEditor, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._editor = editor
        self._rows: dict[str, QtWidgets.QWidget] = {}
        self._labels: dict[str, QtWidgets.QLabel] = {}

        layout = QtWidgets.QVBoxLayout(self)
        self._status = QtWidgets.QLabel()
        self._status.setWordWrap(True)
        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(inner)
        block = ""
        for state in editor.states():
            head = state.path.split(".")[0]
            if head != block:
                block = head
                heading = QtWidgets.QLabel(f"<b>{head}</b>")
                form.addRow(heading)
            label = QtWidgets.QLabel(state.path)
            widget = self._build(state)
            self._rows[state.path] = widget
            self._labels[state.path] = label
            form.addRow(label, widget)
        area.setWidget(inner)
        layout.addWidget(area)
        layout.addWidget(self._status)

    # -- construction -------------------------------------------------------

    def _build(self, state: FieldState) -> QtWidgets.QWidget:
        """Return the widget one field is edited through."""
        absent = isinstance(state.value, Absent)
        widget: QtWidgets.QWidget
        if state.kind == "flag":
            box = QtWidgets.QCheckBox()
            box.setChecked(bool(state.value) if not absent else False)
            box.toggled.connect(self._setter(state.path, box.isChecked))
            widget = box
        elif state.kind == "choice":
            combo = QtWidgets.QComboBox()
            combo.addItems(list(state.options or ()))
            combo.setCurrentText(_display(state.value))
            combo.currentTextChanged.connect(self._setter(state.path, combo.currentText))
            widget = combo
        elif state.kind == "selection":
            listing = QtWidgets.QListWidget()
            listing.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
            chosen = set(state.value) if isinstance(state.value, list) else set()
            for option in state.options or ():
                item = QtWidgets.QListWidgetItem(option, listing)
                item.setSelected(option in chosen)
            listing.setMaximumHeight(120)
            listing.itemSelectionChanged.connect(
                self._setter(
                    state.path,
                    lambda: [item.text() for item in listing.selectedItems()],
                )
            )
            widget = listing
        else:
            line = QtWidgets.QLineEdit(_display(state.value))
            if state.options:
                # Enumerated values beside a free one (``wall_h_nm``): offered as
                # a completion rather than as the only choice, which is what
                # makes the number still settable.
                line.setCompleter(QtWidgets.QCompleter(list(state.options), line))
            line.editingFinished.connect(self._setter(state.path, lambda: _parse(line.text())))
            widget = line
        if absent:
            widget.setEnabled(False)
            widget.setToolTip(
                f"{state.path.rsplit('.', 1)[0]} is not in this case file, so there is no block "
                "to substitute into; add that section to the file first"
            )
        return widget

    def _setter(self, path: str, read: Callable[[], FieldValue]) -> Callable[..., None]:
        """Return a slot staging what ``read`` returns at ``path``."""

        def stage(*_: object) -> None:
            try:
                self._editor.stage(path, read())
            except CaseValidationError as error:
                self._mark(path, bad=True)
                self._status.setText(str(error))
            else:
                self._mark(path, bad=False)
                self._status.setText(f"{path} staged; commit to validate the whole case")
            self.changed.emit()

        return stage

    def _mark(self, path: str, *, bad: bool) -> None:
        """Colour one row's label according to whether its value was accepted."""
        self._labels[path].setStyleSheet("color: red" if bad else "")

    # -- the editor ---------------------------------------------------------

    @property
    def editor(self) -> CaseEditor:
        """The view-model this form edits."""
        return self._editor

    def bound_paths(self) -> tuple[str, ...]:
        """Return every path the form binds, in the order it shows them.

        Equal to :func:`~nanopnp.io.case.case_fields`, which
        ``tests/tier1/test_gui_widgets.py`` asserts: a form that bound a subset
        would leave part of the schema uneditable with nothing to say so.
        """
        return tuple(self._rows)

    def widget_at(self, path: str) -> QtWidgets.QWidget:
        """Return the widget bound to one path."""
        return self._rows[path]

    def commit(self) -> bool:
        """Commit the staged edits, showing the whole-document diagnostic on failure.

        Returns
        -------
        bool
            Whether the document now carries the edits.
        """
        try:
            self._editor.commit()
        except CaseValidationError:
            self._status.setText(self._editor.problems() or "the case was refused")
            return False
        self._status.setText("committed")
        return True

    def status(self) -> str:
        """Return the message the form is currently showing."""
        return str(self._status.text())

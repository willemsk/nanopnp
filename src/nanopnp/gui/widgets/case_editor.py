"""The case form, built from the schema at run time (IF-09)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import yaml
from PySide6 import QtCore, QtWidgets

from nanopnp.gui.case_model import Absent, CaseEditor, FieldState
from nanopnp.io.case import CaseValidationError, FieldValue

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Callable

__all__ = ["CaseEditorWidget"]

SPIN_DECIMALS = 3

# What a QSpinBox holds, a C int: a bounded integer that does not fit is a numeric entry, since
# narrowing the schema's range would misstate it.
SPIN_INT_RANGE = (-(2**31), 2**31 - 1)


def _display(value: FieldValue | Absent) -> str:
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
    changed = QtCore.Signal()

    def __init__(self, editor: CaseEditor, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._editor = editor
        self._rows: dict[str, QtWidgets.QWidget] = {}
        self._labels: dict[str, QtWidgets.QLabel] = {}
        self._adders: dict[str, QtWidgets.QPushButton] = {}

        layout = QtWidgets.QVBoxLayout(self)
        self._status = QtWidgets.QLabel()
        self._status.setWordWrap(True)
        sections = QtWidgets.QHBoxLayout()
        for name in editor.addable():
            button = QtWidgets.QPushButton(f"Add section: {name}")
            button.setToolTip(
                f"write an empty {name}: block, which resolves exactly as its absence, so its "
                "fields can be edited"
            )
            button.clicked.connect(lambda *_, section=name: self.add_section(section))
            self._adders[name] = button
            sections.addWidget(button)
        sections.addStretch(1)
        layout.addLayout(sections)
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

    def _build(self, state: FieldState) -> QtWidgets.QWidget:
        widget: QtWidgets.QWidget
        if state.kind == "flag":
            box = QtWidgets.QCheckBox()
            box.toggled.connect(self._setter(state.path, box.isChecked))
            widget = box
        elif state.kind == "choice":
            combo = QtWidgets.QComboBox()
            combo.addItems(list(state.options or ()))
            combo.currentTextChanged.connect(self._setter(state.path, combo.currentText))
            widget = combo
        elif state.kind == "selection":
            listing = QtWidgets.QListWidget()
            listing.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
            for option in state.options or ():
                QtWidgets.QListWidgetItem(option, listing)
            listing.setMaximumHeight(120)
            listing.itemSelectionChanged.connect(
                self._setter(
                    state.path,
                    lambda: [item.text() for item in listing.selectedItems()],
                )
            )
            widget = listing
        elif (
            state.kind == "bounded"
            and state.bounds is not None
            and state.integral
            and SPIN_INT_RANGE[0] <= state.bounds[0]
            and state.bounds[1] <= SPIN_INT_RANGE[1]
        ):
            whole = QtWidgets.QSpinBox()
            lower, upper = state.bounds
            whole.setRange(math.ceil(lower), math.floor(upper))
            whole.setSingleStep(1)
            whole.setKeyboardTracking(False)
            whole.valueChanged.connect(self._setter(state.path, whole.value))
            widget = whole
        elif state.kind == "bounded" and state.bounds is not None and not state.integral:
            spin = QtWidgets.QDoubleSpinBox()
            lower, upper = state.bounds
            spin.setDecimals(SPIN_DECIMALS)
            spin.setRange(lower, upper)
            span = upper - lower
            spin.setSingleStep(10.0 ** math.floor(math.log10(span / 100.0)) if span > 0 else 1.0)
            spin.setKeyboardTracking(False)
            # ``valueChanged`` and not ``editingFinished``: the latter fires on a
            # focus change with nothing edited, and would stage the rounded display.
            spin.valueChanged.connect(self._setter(state.path, spin.value))
            widget = spin
        else:
            line = QtWidgets.QLineEdit()
            if state.options:
                # Enumerated values beside a free one (wall_h_nm): offered as a completion, not the
                # only choice, so the number stays settable.
                line.setCompleter(QtWidgets.QCompleter(list(state.options), line))
            line.editingFinished.connect(self._setter(state.path, lambda: _parse(line.text())))
            widget = line
        self._present(widget, state)
        return widget

    def _present(self, widget: QtWidgets.QWidget, state: FieldState) -> None:
        absent = isinstance(state.value, Absent)
        widget.blockSignals(True)
        try:
            if isinstance(widget, QtWidgets.QCheckBox):
                widget.setChecked(bool(state.value) if not absent else False)
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.setCurrentText(_display(state.value))
            elif isinstance(widget, QtWidgets.QListWidget):
                chosen = set(state.value) if isinstance(state.value, list) else set()
                for index in range(widget.count()):
                    item = widget.item(index)
                    item.setSelected(item.text() in chosen)
            elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                # Nothing to show for a field the document lacks: the minimum,
                # labelled as absent rather than read as a value.
                widget.setSpecialValueText("absent" if absent else "")
                if isinstance(state.value, int | float) and not isinstance(state.value, bool):
                    widget.setValue(float(state.value))
                else:
                    widget.setValue(widget.minimum())
            elif isinstance(widget, QtWidgets.QSpinBox):
                widget.setSpecialValueText("absent" if absent else "")
                if isinstance(state.value, int) and not isinstance(state.value, bool):
                    widget.setValue(state.value)
                else:
                    widget.setValue(widget.minimum())
            elif isinstance(widget, QtWidgets.QLineEdit):
                widget.setText(_display(state.value))
        finally:
            widget.blockSignals(False)
        widget.setEnabled(not absent)
        widget.setToolTip(
            f"{state.path.rsplit('.', 1)[0]} is not in this case file, so there is no block "
            "to substitute into; add that section first"
            if absent
            else ""
        )

    def _setter(self, path: str, read: Callable[[], FieldValue]) -> Callable[..., None]:
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
        self._labels[path].setStyleSheet("color: red" if bad else "")

    @property
    def editor(self) -> CaseEditor:
        return self._editor

    def bound_paths(self) -> tuple[str, ...]:
        return tuple(self._rows)

    def widget_at(self, path: str) -> QtWidgets.QWidget:
        return self._rows[path]

    def addable(self) -> tuple[str, ...]:
        return tuple(name for name, button in self._adders.items() if button.isEnabled())

    def add_section(self, name: str) -> bool:
        try:
            self._editor.add_section(name)
        except ValueError as error:
            self._status.setText(str(error))
            return False
        prefix = f"{name}."
        for path, widget in self._rows.items():
            if path.startswith(prefix):
                self._present(widget, self._editor.state(path))
        button = self._adders.get(name)
        if button is not None:
            button.setEnabled(False)
        self._status.setText(
            f"{name}: added as an empty section, which resolves as its absence; its fields can "
            "now be edited"
        )
        self.changed.emit()
        return True

    def commit(self) -> bool:
        try:
            self._editor.commit()
        except CaseValidationError:
            self._status.setText(self._editor.problems() or "the case was refused")
            return False
        self._status.setText("committed")
        return True

    def status(self) -> str:
        return str(self._status.text())

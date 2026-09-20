"""The result panel: the scalars, and the deviations they were produced under.

The two are shown together on purpose. FR-25 records "every switch set away from
the validated default" because a number obtained with a correction disabled is
not the validated model's number, and a panel showing the conductance without
the deviations would be presenting one as the other (§5.3.3).

Everything here is read out of the run directory by
:func:`~nanopnp.gui.run_model.run_outcome` — the manifest, the case and the run
record are the run's own record, and a panel reading anything else would show
something the QR-08 reproduction check could not reconstruct.
"""

from __future__ import annotations

from PySide6 import QtWidgets

from nanopnp.gui.run_model import RunOutcome

__all__ = ["ResultWidget"]


class ResultWidget(QtWidgets.QWidget):
    """What a finished run produced, and under what configuration."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._directory = QtWidgets.QLabel("no run yet")
        self._directory.setWordWrap(True)
        self._quantities = QtWidgets.QTableWidget(0, 2)
        self._quantities.setHorizontalHeaderLabels(["quantity", "value"])
        self._quantities.horizontalHeader().setStretchLastSection(True)
        self._deviations = QtWidgets.QPlainTextEdit()
        self._deviations.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._directory)
        layout.addWidget(QtWidgets.QLabel("Quantities of interest"))
        layout.addWidget(self._quantities, 2)
        layout.addWidget(QtWidgets.QLabel("Deviations from the validated default (FR-25)"))
        layout.addWidget(self._deviations, 1)

    def show_outcome(self, outcome: RunOutcome | None) -> None:
        """Show one run's result, or clear the panel when there is none."""
        if outcome is None:
            self._directory.setText("no run yet")
            self._quantities.setRowCount(0)
            self._deviations.setPlainText("")
            return
        self._directory.setText(str(outcome.directory))
        self._quantities.setRowCount(len(outcome.quantities))
        for row, (name, value) in enumerate(sorted(outcome.quantities.items())):
            self._quantities.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self._quantities.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{value}"))
        self._deviations.setPlainText(_render_deviations(outcome))

    def quantity_names(self) -> tuple[str, ...]:
        """Return the quantities the panel is showing, for a test."""
        return tuple(
            item.text()
            for row in range(self._quantities.rowCount())
            for item in [self._quantities.item(row, 0)]
            if item is not None
        )


def _render_deviations(outcome: RunOutcome) -> str:
    """Render the manifest's Deviations group as the lines a reader wants.

    Its shape is the manifest's, not this panel's: a ``switches`` list of
    ``{path, value, validated_default}`` and a ``contributed`` list of
    ``{source, description}`` — departures no switch selects (a smoothed
    dielectric field, an ion-exclusion material on a supplied mesh), which the
    diff cannot see and the stage that read them reported.
    """
    deviations = outcome.deviations
    switches = deviations.get("switches") or []
    sources = deviations.get("contributed") or []
    if not switches and not sources:
        return "none: this run used the validated default configuration"
    lines = [
        f"{entry.get('path')}: {entry.get('value')!r}, "
        f"validated default {entry.get('validated_default')!r}"
        for entry in switches
    ]
    lines += [f"{entry.get('source')}: {entry.get('description')}" for entry in sources]
    return "\n".join(lines)

"""The run panel: start, cancel, progress and the log, over the run-control view-model."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from nanopnp.gui.run_model import RunControl, RunModel

__all__ = ["RunControlWidget"]

POLL_INTERVAL_MS = 100


class RunControlWidget(QtWidgets.QWidget):
    """The run panel: two buttons, a bar and a log."""

    startRequested = QtCore.Signal()

    settled = QtCore.Signal()

    def __init__(self, control: RunControl, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._control = control
        self._settled = True
        self._shown = 0

        self._start = QtWidgets.QPushButton("Run")
        self._cancel = QtWidgets.QPushButton("Cancel")
        self._cancel.setEnabled(False)
        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 1000)
        self._stage = QtWidgets.QLabel("idle")
        self._log = QtWidgets.QPlainTextEdit()
        self._log.setReadOnly(True)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self._start)
        buttons.addWidget(self._cancel)
        buttons.addStretch(1)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self._bar)
        layout.addWidget(self._stage)
        layout.addWidget(self._log, 1)

        self._start.clicked.connect(self._ask)
        self._cancel.clicked.connect(self._stop)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def _ask(self) -> None:
        self.startRequested.emit()

    def _stop(self) -> None:
        self._control.cancel()

    def began(self) -> None:
        """Tell the panel a run has just been started, before the child has posted anything."""
        self._settled = False
        self._log.clear()
        self._shown = 0
        self.refresh()

    def refresh(self) -> RunModel:
        """Drain the child's events, show the model and return it."""
        model = self._control.poll()
        self._bar.setValue(round(model.fraction * 1000))
        stage = model.stage
        self._stage.setText(
            model.state
            if stage is None
            else f"{model.state}: stage {stage.index + 1} of {stage.total}, {stage.name}"
        )
        self._show_log(model)
        if model.settled and not self._settled:
            self._settled = True
            self.settled.emit()
        # In flight from the panel's own point of view: from the moment the window says so until the
        # model settles, and neither edge coincides with an event.
        in_flight = not self._settled
        self._start.setEnabled(not in_flight)
        self._cancel.setEnabled(in_flight)
        return model

    def _show_log(self, model: RunModel) -> None:
        if len(model.log) < self._shown:  # a fresh model: a new run's log
            self._log.clear()
            self._shown = 0
        for line in model.log[self._shown :]:
            self._log.appendPlainText(line)
        self._shown = len(model.log)

    @property
    def control(self) -> RunControl:
        """The view-model this panel drives."""
        return self._control

    def log_text(self) -> str:
        """Return the log the panel is showing."""
        return str(self._log.toPlainText())

    @property
    def can_start(self) -> bool:
        """Whether the panel is currently offering to start a run."""
        return bool(self._start.isEnabled())

    @property
    def can_cancel(self) -> bool:
        """Whether the panel is currently offering to cancel one."""
        return bool(self._cancel.isEnabled())

"""Start, cancel, progress and the log — a projection of :class:`~nanopnp.gui.run_model.RunControl`.

The widget holds no state. It polls :meth:`~nanopnp.gui.run_model.RunControl.poll`
on a timer, reads the model, and shows it; the state machine, the monotone
fraction and the §3.1 exit class all live on the far side of the Qt boundary
where a test can reach them without a display.

Starting is a *request*, not an action: the window saves the case file first,
because §5.3.1 makes the file the unit of reproducibility and a run of an unsaved
document would emit a manifest naming an input that does not exist.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from nanopnp.gui.run_model import RunControl, RunModel

__all__ = ["RunControlWidget"]

POLL_INTERVAL_MS = 100
"""How often the child's event queue is drained. Fast enough that a progress bar
looks continuous, slow enough to cost nothing beside a solve."""


class RunControlWidget(QtWidgets.QWidget):
    """The run panel: two buttons, a bar and a log."""

    startRequested = QtCore.Signal()
    """Emitted when the user asks to run. The window decides what that means."""

    settled = QtCore.Signal()
    """Emitted once when a run reaches ``finished``, ``failed`` or ``cancelled``."""

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
        """Relay the button press as :attr:`startRequested`.

        A method rather than a signal-to-signal connection: ``clicked`` carries
        a ``bool`` that ``startRequested`` does not, and relying on Qt to drop
        it is relying on an arity rule rather than stating one.
        """
        self.startRequested.emit()

    def _stop(self) -> None:
        """Relay the button press as a cancellation, for the same reason."""
        self._control.cancel()

    def began(self) -> None:
        """Tell the panel a run has just been started.

        Called by the window once :meth:`~nanopnp.gui.run_model.RunControl.start`
        has spawned the child, which is *before* the child has posted anything.
        The buttons follow this flag rather than the model's state for exactly
        that reason: between the spawn and the first :class:`Started` the model
        still reads ``idle``, and a panel that enabled "Run" there would let a
        second click reach a control that already has a run in flight.
        """
        self._settled = False
        self._log.clear()
        self._shown = 0
        self.refresh()

    def refresh(self) -> RunModel:
        """Drain the child's events and show the model.

        Returns
        -------
        RunModel
            The model as it now stands, so a test can drive the panel without a
            timer.
        """
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
        # In flight from the panel's own point of view, which is what the user
        # is acting on: a run is in flight from the moment the window says so
        # until the model settles, and neither edge coincides with an event.
        in_flight = not self._settled
        self._start.setEnabled(not in_flight)
        self._cancel.setEnabled(in_flight)
        return model

    def _show_log(self, model: RunModel) -> None:
        """Append the log lines the panel has not shown yet.

        Counted in *entries* and not in the widget's own physical lines: a QR-12
        gate diagnostic names the gate, the quantity and its location and is
        several lines long, so one entry can add four to the widget. Counting
        rendered lines would then leave the panel permanently ahead of the model
        and silently drop every line after the first multi-line one.
        """
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
        """Return the log the panel is showing, for a test."""
        return str(self._log.toPlainText())

    @property
    def can_start(self) -> bool:
        """Whether the panel is currently offering to start a run."""
        return bool(self._start.isEnabled())

    @property
    def can_cancel(self) -> bool:
        """Whether the panel is currently offering to cancel one."""
        return bool(self._cancel.isEnabled())

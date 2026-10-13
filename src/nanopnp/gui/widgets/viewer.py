"""The field viewer: a web view over a scene file, and a probe that says whether it drew."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets
from PySide6.QtWebEngineWidgets import QWebEngineView

from nanopnp.gui.render import RenderProcess, readiness_script
from nanopnp.gui.scene import SceneModel

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Iterable

    from nanopnp.gui.render import RenderEvent

__all__ = ["ViewerWidget"]

POLL_INTERVAL_MS = 200


class ViewerWidget(QtWidgets.QWidget):
    """The viewer panel: a field selector, a web view and a diagnostic pane."""

    def __init__(
        self, model: SceneModel | None = None, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._model = model if model is not None else SceneModel()
        self._process: RenderProcess | None = None
        self._run: Path | None = None

        self._fields = QtWidgets.QComboBox()
        self._fields.setEnabled(False)
        self._summary = QtWidgets.QLabel()
        self._summary.setWordWrap(True)
        self._view = QWebEngineView()
        self._diagnostic = QtWidgets.QPlainTextEdit()
        self._diagnostic.setReadOnly(True)
        self._stack = QtWidgets.QStackedWidget()
        self._stack.addWidget(self._view)
        self._stack.addWidget(self._diagnostic)

        selector = QtWidgets.QHBoxLayout()
        selector.addWidget(QtWidgets.QLabel("Field"))
        selector.addWidget(self._fields, 1)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(selector)
        layout.addWidget(self._summary)
        layout.addWidget(self._stack, 1)

        self._fields.activated.connect(self._reselect)
        self._view.loadFinished.connect(self._loaded)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self._show_model()

    def show_run(self, directory: str | Path | None, *, field: str = "") -> None:
        # Drop the render in flight first: a child left attached would load the previous run's
        # document into the cleared panel, and two renders of one run sweep each other's scene-*
        # pair out of viewer/.
        """Render one field of a finished run, or clear the panel when given no run."""
        self._stop_render()
        if directory is None:
            self._run = None
            self._model.reset()
            self._show_model()
            return
        self._run = Path(directory)
        request = self._model.request(self._run, field=field)
        self._process = RenderProcess(request)
        self._process.start()
        self._show_model()

    def _stop_render(self) -> None:
        process = self._process
        self._process = None
        if process is not None:
            process.terminate()

    def _reselect(self, index: int) -> None:
        if self._run is None or index < 0:
            return
        self.show_run(self._run, field=self._fields.itemText(index))

    def refresh(self) -> SceneModel:
        """Drain the render child into :meth:`apply` and return the model."""
        if self._process is None:
            return self._model
        model = self.apply(self._process.drain())
        if not self._process.running:
            self._process.join(0.0)
        return model

    def apply(self, events: Iterable[RenderEvent]) -> SceneModel:
        """Apply render events and load the document one produced, if any; return the model."""
        before = self._model.state
        self._model.consume(events)
        if self._model.state != before:
            self._show_model()
            if self._model.state == "loading" and self._model.document is not None:
                # A file URL, never setHtml, which percent-encodes the tens-of-megabytes scene into
                # a data URL.
                self._view.load(QtCore.QUrl.fromLocalFile(str(self._model.document)))
        return self._model

    def _loaded(self, ok: bool) -> None:
        self._model.loaded(ok)
        if not ok:
            self._show_model()
            return
        self._view.page().runJavaScript(readiness_script(), self._answered)

    def _answered(self, answer: object) -> None:
        self.probed(answer if isinstance(answer, str) else None)

    def probed(self, answer: str | None) -> None:
        """Apply the readiness probe's answer and show what it said."""
        self._model.probed(answer)
        self._show_model()

    def _show_model(self) -> None:
        self._summary.setText(self._model.summary)
        offered = tuple(self._fields.itemText(index) for index in range(self._fields.count()))
        if offered != self._model.fields:
            self._fields.clear()
            self._fields.addItems(list(self._model.fields))
        self._fields.setEnabled(bool(self._model.fields))
        if self._model.field in self._model.fields:
            self._fields.setCurrentIndex(self._model.fields.index(self._model.field))
        # The diagnostic replaces the view rather than sitting beside it: a
        # blank rectangle with a warning underneath still reads as a picture
        # that is simply empty.
        if self._model.state in ("failed", "blank"):
            self._diagnostic.setPlainText(self._model.diagnosis)
            self._stack.setCurrentWidget(self._diagnostic)
        else:
            self._stack.setCurrentWidget(self._view)

    @property
    def model(self) -> SceneModel:
        """The view-model this panel drives."""
        return self._model

    @property
    def showing_diagnostic(self) -> bool:
        """Whether the panel has replaced the view with a diagnostic."""
        return self._stack.currentWidget() is self._diagnostic

    def diagnostic_text(self) -> str:
        """Return the diagnostic the panel is showing."""
        return str(self._diagnostic.toPlainText())

    def offered_fields(self) -> tuple[str, ...]:
        """Return the field names the selector offers."""
        return tuple(self._fields.itemText(index) for index in range(self._fields.count()))

"""The field viewer: a web view over a scene file, and a probe that says whether it drew.

Three things this panel does that a naive one would not, each of them a
correctness question rather than a presentation one.

**It loads a file URL, never ``setHtml``.** ``QWebEngineView.setHtml``
percent-encodes its argument into a data URL, and a scene of the reference mesh
is 23 to 39 MB (`.knowledge/07-software-stack.md` §5). The render child writes
the document to disk and this loads it with ``QUrl.fromLocalFile``.

**It probes the document after ``loadFinished``.** Qt reaches
``loadFinished(True)`` on a page whose renderer never arrived and leaves
``webgui is not defined`` in a console nobody sees, so a panel that trusted the
signal would show an empty rectangle and report success — the failure QR-12 is
written against. One ``runJavaScript`` of
:func:`~nanopnp.gui.render.readiness_script` answers the question the signal
does not, and the panel is replaced by the diagnostic
:class:`~nanopnp.gui.scene.SceneModel` writes, which names the renderer source
it tried.

**It never enumerates a field.** The selector is filled from the render child's
report, which names the model's own declared fields through
:func:`nanopnp.io.fields.attribute_name` — the vocabulary the IF-07 export
writes. A list here would be a second source of truth about what a number means.

The picture itself is the meshed half-plane exactly as it was computed: no
mirroring, no deformation warp, no streamlines (N3, N4, §6.3). A mirrored
half-plane is a picture of something the solve never discretised.
"""

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
"""How often the render child's queue is drained. Slower than the run panel's:
a render posts one event and the wait is dominated by the restore."""


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

    # -- driving ---------------------------------------------------------------

    def show_run(self, directory: str | Path | None, *, field: str = "") -> None:
        """Render one field of a finished run, or clear the panel.

        Parameters
        ----------
        directory
            The run directory, or ``None`` to clear. Cleared before every new
            run for the reason the result panel is: the previous run's picture
            beside this run's numbers would be two runs presented as one.
        field
            An attribute name the solution offers, or ``""`` for the first.
        """
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

    def _reselect(self, index: int) -> None:
        """Re-render for the field the user chose."""
        if self._run is None or index < 0:
            return
        self.show_run(self._run, field=self._fields.itemText(index))

    def refresh(self) -> SceneModel:
        """Drain the render child into :meth:`apply` and return the model.

        A child that has posted and exited is joined here. It is spawned and
        daemonic, so nothing keeps it alive; joining is what stops a session
        that rendered a dozen fields accumulating a dozen unreaped children.
        """
        if self._process is None:
            return self._model
        model = self.apply(self._process.drain())
        if not self._process.running:
            self._process.join(0.0)
        return model

    def apply(self, events: Iterable[RenderEvent]) -> SceneModel:
        """Apply render events and load the document one produced, if any.

        The seam the timer drives and a test drives: a panel whose only entry
        point drained a live child could be asserted on a real render or not at
        all, and the rule under test here — that the document arrives as a
        **file** URL — has nothing to do with where the events came from.

        Returns
        -------
        SceneModel
            The model as it now stands, so a test needs no timer.
        """
        before = self._model.state
        self._model.consume(events)
        if self._model.state != before:
            self._show_model()
            if self._model.state == "loading" and self._model.document is not None:
                # ``load`` of a file URL, never ``setHtml``: that percent-encodes
                # its argument into a data URL, and the scene is tens of
                # megabytes at the reference mesh size.
                self._view.load(QtCore.QUrl.fromLocalFile(str(self._model.document)))
        return self._model

    def _loaded(self, ok: bool) -> None:
        """Record the document load and then ask the document what it did."""
        self._model.loaded(ok)
        if not ok:
            self._show_model()
            return
        self._view.page().runJavaScript(readiness_script(), self._answered)

    def _answered(self, answer: object) -> None:
        """Relay ``runJavaScript``'s answer, which Qt types as anything."""
        self.probed(answer if isinstance(answer, str) else None)

    def probed(self, answer: str | None) -> None:
        """Apply the readiness probe's answer and show what it said.

        Public because it is the whole of D12: the panel's answer to "did the
        picture draw" is a pure function of this string, and asserting it needs
        no renderer, no network and no event loop.
        """
        self._model.probed(answer)
        self._show_model()

    # -- showing ---------------------------------------------------------------

    def _show_model(self) -> None:
        """Bring the selector, the summary and the stacked pane up to date."""
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

    # -- for tests -------------------------------------------------------------

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

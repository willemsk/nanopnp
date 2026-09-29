"""The Geometry tab: stages 1 to 6 as they land, and a hand edit of the contour (WP24).

A projection of :mod:`nanopnp.gui.geometry`, :mod:`nanopnp.gui.assess` and the
render child's mesh request, and nothing more. What a stage produced, where a
pixel sits, what an edit writes and whether a loop meets the §5.2.1 criteria are
all answered on the far side of the Qt boundary, where
``tests/tier1/test_gui_geometry.py`` reaches them without a display.

**Four children, none of them this widget.** The build is the same spawned
walk the Run tab starts, stopped at stage 6 (``upto="mesh"``, WP24 D3); the
payloads it reports are read by a worker thread, because a stage-2 map is a
hundred megabytes of compressed ``float32`` (D11); the criteria and the B9
seed are measured in the assess child against the stored stages (D8, D10); and
the mesh is drawn by the render child into the run's ``viewer/`` (D12). The tab
polls all four on one timer.

**Every view names its frame.** Stages 1 to 4 and the editor are in the stage-1
frame, the profile document's; stages 5 and 6 are in the model frame, after
``z ← z - centre_z_nm``. The caption under every picture says which (D4): an
edit written back in the wrong one is shifted twice on the next run.

**Drawn by hand** with ``QPainter`` over :class:`~nanopnp.gui.geometry.ViewTransform`,
as the convergence plot is (D13). An image is a ``QImage`` over the RGBA bytes
the view-model built, drawn unsmoothed into the rectangle its pixel centres
define, so a pixel is seen where its node is.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineWidgets import QWebEngineView

from nanopnp.gui.assess import (
    Assessed,
    AssessFailed,
    Assessment,
    AssessProcess,
    AssessRequest,
    Seeded,
)
from nanopnp.gui.geometry import (
    BUILD_UPTO,
    MODEL_FRAME,
    STAGE_1_FRAME,
    ImageModel,
    ImageView,
    OutlineView,
    ProfileEditor,
    StageList,
    StageRow,
    StageView,
    SummaryView,
    ViewTransform,
    can_build,
    load_structure,
    load_view,
    nearest_edge,
    nearest_vertex,
    planned_stages,
)
from nanopnp.gui.render import (
    MeshRequest,
    RenderedMesh,
    RenderFailed,
    RenderProcess,
    readiness_script,
)
from nanopnp.gui.run_model import RunControl, RunModel
from nanopnp.io.case import CaseValidationError, UnknownCasePathError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.gui.case_model import CaseEditor
    from nanopnp.gui.solver import Produced
    from nanopnp.io.case import CaseDocument

logger = logging.getLogger(__name__)

__all__ = ["GeometryCanvas", "GeometryWidget"]

POLL_INTERVAL_MS = 100
"""How often the build, the view loads and the two helper children are polled."""

Point = tuple[float, float]


class GeometryCanvas(QtWidgets.QWidget):
    """One picture of a stage: an image, outlines, and the editor's loop over them.

    The canvas decides nothing. The image's bytes and extent, the loop, the slab
    and the transform all come from :mod:`nanopnp.gui.geometry`; the canvas maps
    a drag through :meth:`ViewTransform.to_data` and hands the result to
    :meth:`ProfileEditor.move`, one undoable step per drag.
    """

    edited = QtCore.Signal()
    """Emitted after a drag, an insertion or a deletion changed the editor's loop."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(360, 360)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self._image: ImageModel | None = None
        self._qimage: QtGui.QImage | None = None
        self._loop: tuple[Point, ...] = ()
        self._slab: tuple[float, float] | None = None
        self._chord: tuple[Point, Point] | None = None
        self._marker: Point | None = None
        self._title = ""
        self._x_label = "r (nm)"
        self._frame = STAGE_1_FRAME
        self._editor: ProfileEditor | None = None
        self._selected: int | None = None
        self._drag: int | None = None
        self._drag_transform: ViewTransform | None = None
        self._preview: Point | None = None

    # -- what is shown -----------------------------------------------------------

    def clear(self, title: str = "", *, frame: str = STAGE_1_FRAME) -> None:
        """Show nothing but a caption."""
        self._image = None
        self._qimage = None
        self._loop = ()
        self._slab = None
        self._chord = None
        self._marker = None
        self._title = title
        self._frame = frame
        self._editor = None
        self._selected = None
        self.update()

    def show_image(
        self,
        image: ImageModel,
        *,
        loop: tuple[Point, ...] = (),
        slab: tuple[float, float] | None = None,
    ) -> None:
        """Show an image, the loop drawn over it and the membrane slab, in the image's frame."""
        self.clear(image.title, frame=image.frame)
        self._image = image
        # ``copy`` detaches the image from the bytes object, which Python may
        # free once this frame returns.
        self._qimage = QtGui.QImage(
            image.rgba(),
            image.width,
            image.height,
            4 * image.width,
            QtGui.QImage.Format.Format_RGBA8888,
        ).copy()
        self._x_label = image.x_label
        self._loop = loop
        self._slab = slab
        self.update()

    def show_outline(self, view: OutlineView) -> None:
        """Show stage 5's region: the model-frame profile, the slab and the membrane chord."""
        self.clear(f"stage 5: region, reservoir radius {view.reservoir_nm:g} nm", frame=view.frame)
        self._x_label = "r (nm)"
        self._loop = view.loop
        self._slab = view.slab
        self._chord = view.chord
        self.update()

    def attach(self, editor: ProfileEditor | None, *, selected: int | None = None) -> None:
        """Draw ``editor``'s loop with handles and let the mouse edit it, or stop."""
        self._editor = editor
        in_loop = editor is not None and selected is not None and selected < len(editor.vertices)
        self._selected = selected if in_loop else None
        self._drag = None
        self._preview = None
        if editor is not None:
            self._loop = ()
            self._title = f"{self._title} — editing {editor.name}" if self._title else editor.name
        self.update()

    def mark(self, location_nm: Point | None) -> None:
        """Mark the ``(r, z)`` a refusal names, or remove the mark."""
        self._marker = location_nm
        self.update()

    # -- the transform ---------------------------------------------------------------

    def _vertices(self) -> list[Point]:
        """Return the loop being drawn: the editor's, with a drag in progress applied."""
        if self._editor is None:
            return list(self._loop)
        shown = list(self._editor.vertices)
        if self._drag is not None and self._preview is not None:
            shown[self._drag] = self._preview
        return shown

    def transform(self) -> ViewTransform:
        """Return the transform the canvas draws with at its current size.

        Fitted to the image's outer edges, the loop, the membrane chord and the
        mark, whichever are shown. While a vertex is dragged it is the transform
        the drag began under, so the picture does not rescale under the pointer.
        """
        if self._drag_transform is not None:
            return self._drag_transform
        xs: list[float] = []
        zs: list[float] = []
        if self._image is not None:
            x_low, x_high, z_low, z_high = self._image.extent_nm
            xs += [x_low, x_high]
            zs += [z_low, z_high]
        points = list(self._editor.vertices if self._editor is not None else self._loop)
        if self._chord is not None:
            points += list(self._chord)
        if self._marker is not None:
            points.append(self._marker)
        xs += [point[0] for point in points]
        zs += [point[1] for point in points]
        if self._slab is not None:
            zs += list(self._slab)
        if not xs:
            xs, zs = [0.0, 1.0], [0.0, 1.0]
        return ViewTransform(
            x_range=(min(xs), max(xs)),
            z_range=(min(zs), max(zs)),
            width=float(self.width()),
            height=float(self.height()),
        )

    # -- painting --------------------------------------------------------------------

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Draw the image, the slab, the outlines, the editor's handles and the captions."""
        del event
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("white"))
        transform = self.transform()
        if self._image is not None and self._qimage is not None:
            left, top, width, height = transform.rectangle(*self._image.extent_nm)
            # Unsmoothed: a pixel is drawn as the value at its node, not blended
            # into its neighbours' (Design §2).
            painter.drawImage(QtCore.QRectF(left, top, width, height), self._qimage)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        if self._slab is not None:
            x_low, x_high = transform.x_range
            left, top, width, height = transform.rectangle(x_low, x_high, *self._slab)
            painter.fillRect(
                QtCore.QRectF(left, top, width, height), QtGui.QColor(128, 128, 128, 60)
            )
        if self._chord is not None:
            painter.setPen(QtGui.QPen(QtGui.QColor("black"), 1.5, QtCore.Qt.PenStyle.DashLine))
            (a, b) = self._chord
            painter.drawLine(
                QtCore.QPointF(*transform.to_screen(*a)), QtCore.QPointF(*transform.to_screen(*b))
            )
        vertices = self._vertices()
        if vertices:
            polygon = QtGui.QPolygonF(
                [QtCore.QPointF(*transform.to_screen(r, z)) for r, z in vertices]
            )
            painter.setPen(QtGui.QPen(QtGui.QColor("black"), 2.0))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawPolygon(polygon)
            painter.setPen(QtGui.QPen(QtGui.QColor("white"), 1.0))
            painter.drawPolygon(polygon)
        if self._editor is not None:
            for index, (r, z) in enumerate(vertices):
                x, y = transform.to_screen(r, z)
                colour = "red" if index == self._selected else "orange"
                painter.setPen(QtGui.QPen(QtGui.QColor("black"), 1.0))
                painter.setBrush(QtGui.QColor(colour))
                painter.drawRect(QtCore.QRectF(x - 3.5, y - 3.5, 7.0, 7.0))
        if self._marker is not None:
            x, y = transform.to_screen(*self._marker)
            painter.setPen(QtGui.QPen(QtGui.QColor("red"), 2.0))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QtCore.QPointF(x, y), 8.0, 8.0)
        painter.setPen(QtGui.QColor("black"))
        metrics = painter.fontMetrics()
        painter.drawText(QtCore.QPointF(6.0, float(metrics.ascent() + 4)), self._title)
        painter.drawText(QtCore.QPointF(6.0, float(self.height() - 6)), self.caption)
        painter.end()

    @property
    def caption(self) -> str:
        """The axis caption, naming the frame (WP24 D4)."""
        x_low, x_high = self.transform().x_range
        z_low, z_high = self.transform().z_range
        return (
            f"{self._x_label} {x_low:.3g} to {x_high:.3g} across, z (nm) {z_low:.3g} to "
            f"{z_high:.3g} up; {self._frame}"
        )

    # -- editing ---------------------------------------------------------------------

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Pick the vertex under the pointer, if the canvas is editing."""
        if self._editor is None or event.button() != QtCore.Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        position = event.position()
        transform = self.transform()
        index = nearest_vertex(self._editor.vertices, transform, position.x(), position.y())
        self._selected = index
        if index is not None:
            self._drag = index
            self._drag_transform = transform
            self._preview = None
        self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Follow the pointer with the dragged vertex, without editing yet."""
        if self._drag is None or self._drag_transform is None:
            super().mouseMoveEvent(event)
            return
        position = event.position()
        self._preview = self._drag_transform.to_data(position.x(), position.y())
        self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Commit the drag as one move: one undoable step, however far it went."""
        if self._drag is None or self._drag_transform is None or self._editor is None:
            super().mouseReleaseEvent(event)
            return
        position = event.position()
        r, z = self._drag_transform.to_data(position.x(), position.y())
        index = self._drag
        moved = self._preview is not None or (r, z) != self._editor.vertices[index]
        self._drag = None
        self._drag_transform = None
        self._preview = None
        if moved:
            self._editor.move(index, r, z)
            self.edited.emit()
        self.update()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Insert a vertex at the midpoint of the edge under the pointer."""
        if self._editor is None:
            super().mouseDoubleClickEvent(event)
            return
        position = event.position()
        transform = self.transform()
        if nearest_vertex(self._editor.vertices, transform, position.x(), position.y()) is not None:
            return
        edge = nearest_edge(self._editor.vertices, transform, position.x(), position.y())
        if edge is not None:
            self._selected = self._editor.insert(edge)
            self.edited.emit()
            self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Delete the selected vertex on Delete or Backspace."""
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            self.delete_selected()
            return
        super().keyPressEvent(event)

    def delete_selected(self) -> str | None:
        """Delete the selected vertex; return the refusal if the loop is at three."""
        if self._editor is None or self._selected is None:
            return None
        try:
            self._editor.delete(self._selected)
        except ValueError as error:
            return str(error)
        self._selected = None
        self.edited.emit()
        self.update()
        return None

    @property
    def selected(self) -> int | None:
        """The vertex last picked, if any."""
        return self._selected

    @property
    def editor(self) -> ProfileEditor | None:
        """The editor the canvas is driving, if any."""
        return self._editor


class GeometryWidget(QtWidgets.QWidget):
    """The Geometry tab: a stage list, one pane per stage, and the contour editor.

    Parameters
    ----------
    editor
        The case open for editing; the tab reads its document and stages the
        structure path into it.
    store
        The artefact store's root, or ``None`` for the process default.
    """

    buildRequested = QtCore.Signal()
    """Emitted when the user asks to build. The window commits and saves the case first."""

    structureLoaded = QtCore.Signal(str)
    """Emitted with the path staged at ``structure.source.path``, for the Case tab to show."""

    def __init__(
        self,
        editor: CaseEditor,
        *,
        store: Path | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._case_editor = editor
        self._store = store
        self._control = RunControl()
        self._settled = True
        self._case_path: Path | None = None
        self._document: CaseDocument | None = None
        self._stages = StageList(())
        self._rows: tuple[StageRow, ...] = ()
        self._views: dict[str, StageView] = {}
        self._view_errors: dict[str, str] = {}
        self._loading: dict[str, Future[StageView]] = {}
        self._requested: set[str] = set()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nanopnp-views")
        self._editor: ProfileEditor | None = None
        self._assess: AssessProcess | None = None
        self._assessment: Assessment | None = None
        self._render: RenderProcess | None = None
        self._mesh: RenderedMesh | None = None
        self._mesh_problem = ""

        self._load = QtWidgets.QPushButton("Load structure…")
        self._build = QtWidgets.QPushButton("Build geometry")
        self._cancel = QtWidgets.QPushButton("Cancel")
        self._measure = QtWidgets.QPushButton("Measure criteria")
        self._seed = QtWidgets.QPushButton("Seed from refusal")
        self._delete = QtWidgets.QPushButton("Delete vertex")
        self._undo = QtWidgets.QPushButton("Undo")
        self._redo = QtWidgets.QPushButton("Redo")
        self._save = QtWidgets.QPushButton("Save edit")
        self._list = QtWidgets.QListWidget()
        self._list.setMinimumWidth(260)
        self._quantity = QtWidgets.QComboBox()
        self._canvas = GeometryCanvas()
        self._web = QWebEngineView()
        self._pictures = QtWidgets.QStackedWidget()
        self._pictures.addWidget(self._canvas)
        self._pictures.addWidget(self._web)
        self._details = QtWidgets.QPlainTextEdit()
        self._details.setReadOnly(True)
        self._details.setMaximumHeight(180)
        self._status = QtWidgets.QLabel("no build yet")
        self._status.setWordWrap(True)

        build = QtWidgets.QHBoxLayout()
        for button in (self._load, self._build, self._cancel):
            build.addWidget(button)
        build.addStretch(1)
        edit = QtWidgets.QHBoxLayout()
        for button in (
            self._measure,
            self._seed,
            self._delete,
            self._undo,
            self._redo,
            self._save,
        ):
            edit.addWidget(button)
        edit.addStretch(1)
        pane = QtWidgets.QVBoxLayout()
        pane.addWidget(self._quantity)
        pane.addWidget(self._pictures, 1)
        pane.addWidget(self._details)
        right = QtWidgets.QWidget()
        right.setLayout(pane)
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self._list)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(build)
        layout.addLayout(edit)
        layout.addWidget(splitter, 1)
        layout.addWidget(self._status)

        self._load.clicked.connect(self._pick_structure)
        self._build.clicked.connect(self._ask_build)
        self._cancel.clicked.connect(self._stop)
        self._measure.clicked.connect(self.measure)
        self._seed.clicked.connect(self.seed)
        self._delete.clicked.connect(self._delete_vertex)
        self._undo.clicked.connect(self._step_back)
        self._redo.clicked.connect(self._step_forward)
        self._save.clicked.connect(self._save_edit)
        self._list.currentRowChanged.connect(self._show_row)
        self._quantity.activated.connect(self._requantity)
        self._canvas.edited.connect(self._after_edit)
        self._web.loadFinished.connect(self._mesh_loaded)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self._show_buttons()

    # -- building --------------------------------------------------------------------

    def _pick_structure(self) -> None:
        """Ask for a structure file and stage its absolute path (WP24 D7)."""
        chosen, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load a structure",
            "",
            "Structures (*.pdb *.cif *.mmcif *.pqr);;All files (*)",
        )
        if chosen:
            self.load_structure(chosen)

    def load_structure(self, path: str | Path) -> Path | None:
        """Stage ``structure.source.path`` as ``path``, or show why it was refused."""
        try:
            staged = load_structure(self._case_editor, path)
        except (UnknownCasePathError, CaseValidationError) as error:
            self._status.setText(str(error))
            return None
        self._status.setText(f"structure.source.path staged: {staged}; build to see it")
        self.structureLoaded.emit(str(staged))
        return staged

    def _ask_build(self) -> None:
        """Relay the button press; the window saves the case before :meth:`build`."""
        self.buildRequested.emit()

    def build(self, case_path: str | Path) -> None:
        """Walk the saved case through stage 6 in the spawned child (WP24 D3).

        Parameters
        ----------
        case_path
            The case file as saved, which is what the child reads and what a
            hand edit's derived case is written beside.
        """
        self._stop_children()
        self._case_path = Path(case_path)
        self._document = self._case_editor.document
        self._stages = StageList(planned_stages(self._document))
        self._views.clear()
        self._view_errors.clear()
        self._loading.clear()
        self._requested.clear()
        self._editor = None
        self._assessment = None
        self._mesh = None
        self._mesh_problem = ""
        self._control.start(self._case_path, store=self._store, upto=BUILD_UPTO)
        self._settled = False
        self._status.setText(f"building {self._case_path} through stage 6")
        self.refresh()

    def _stop(self) -> None:
        """Cancel the build; a cancelled walk writes no artefact (§5.3.2)."""
        self._control.cancel()

    def _stop_children(self) -> None:
        """Stop the assess and render children, whose answers no longer apply."""
        for process in (self._assess, self._render):
            if process is not None:
                process.terminate()
        self._assess = None
        self._render = None

    def shutdown(self) -> None:
        """Stop everything this tab started: the build, the children and the view loads."""
        self._timer.stop()
        self._control.cancel()
        self._stop_children()
        self._executor.shutdown(wait=False, cancel_futures=True)

    # -- polling ---------------------------------------------------------------------

    def refresh(self) -> RunModel:
        """Poll the build, the view loads and the two children, and show where they are."""
        model = self._control.poll()
        produced = {event.name: event for event in model.produced}
        document = self._document
        if document is not None:
            for event in model.produced:
                if event.name not in self._requested:
                    self._requested.add(event.name)
                    self._loading[event.name] = self._executor.submit(
                        load_view, event, dict(produced), document
                    )
        for name, future in list(self._loading.items()):
            if future.done():
                del self._loading[name]
                self._landed(name, future)
        self._drain_assess()
        self._drain_render()
        if model.settled and not self._settled:
            self._settled = True
            self._built(model, produced)
        self._rows = self._stages.rows(model)
        self._show_rows()
        self._show_buttons()
        return model

    def _landed(self, name: str, future: Future[StageView]) -> None:
        """Keep a loaded view, and start the editor from stage 4's profile."""
        try:
            view = future.result()
        except Exception as error:  # the pane shows it; the tab stays usable
            self._view_errors[name] = f"{type(error).__name__}: {error}"
            return
        self._views[name] = view
        if isinstance(view, ImageView) and view.profile is not None and self._editor is None:
            self._editor = ProfileEditor.from_profile(view.profile)
        if self._selected_name() == name:
            self._show_row(self._list.currentRow())

    def _built(self, model: RunModel, produced: dict[str, Produced]) -> None:
        """Say how the build settled; draw the mesh if it reached stage 6."""
        if model.state == "finished" and "mesh" in produced and model.directory is not None:
            self._render = RenderProcess(MeshRequest(run=str(model.directory)))
            self._render.start()
        last = model.log[-1] if model.log else model.state
        self._status.setText(last)

    def _drain_assess(self) -> None:
        """Apply what the assess child posted."""
        if self._assess is None:
            return
        events = self._assess.drain()
        for event in events:
            if isinstance(event, Assessed):
                self._assessment = event.assessment
                self._status.setText(
                    "the edit meets every section 5.2.1 criterion"
                    if event.assessment.passed
                    else f"the edit fails {len(event.assessment.failures)} section 5.2.1 "
                    "criterion(s); recorded, not enforced"
                )
            elif isinstance(event, Seeded):
                seed = event.seed
                self._editor = ProfileEditor.from_seed(
                    seed.vertices, digest=seed.digest, name=seed.name
                )
                self._assessment = seed.assessment
                self._status.setText(
                    f"seeded from the refused contour: {len(seed.vertices)} vertices"
                )
                self._select("contour")
            elif isinstance(event, AssessFailed):
                self._status.setText(f"{event.error}: {event.message}")
        finished = not self._assess.running
        if finished:
            self._assess.join(0.0)
            self._assess = None
        if events or finished:
            self._show_row(self._list.currentRow())

    def _drain_render(self) -> None:
        """Load the mesh picture the render child wrote, or keep its refusal."""
        if self._render is None:
            return
        for event in self._render.drain():
            if isinstance(event, RenderedMesh):
                self._mesh = event
                # A file URL, never ``setHtml``: the scene is megabytes (WP15 D8).
                self._web.load(QtCore.QUrl.fromLocalFile(event.document))
            elif isinstance(event, RenderFailed):
                self._mesh_problem = f"{event.error}: {event.message}"
        if not self._render.running:
            self._render.join(0.0)
            self._render = None
            if self._selected_name() == "mesh":
                self._show_row(self._list.currentRow())

    def _mesh_loaded(self, ok: bool) -> None:
        """Ask the document whether it drew, as the Fields panel does."""
        if not ok:
            self._mesh_problem = "the mesh document did not load"
            return
        self._web.page().runJavaScript(readiness_script(), self._mesh_answered)

    def _mesh_answered(self, answer: object) -> None:
        """Keep the document's own account of a picture that did not draw."""
        try:
            state = json.loads(answer) if isinstance(answer, str) else {}
        except json.JSONDecodeError:
            state = {}
        if not state.get("ready"):
            self._mesh_problem = (
                f"the mesh picture did not draw: {state.get('error') or 'no answer'} "
                f"(renderer loaded: {bool(state.get('renderer_loaded'))})"
            )
        if self._selected_name() == "mesh":
            self._show_row(self._list.currentRow())

    # -- the stage list --------------------------------------------------------------

    def _show_rows(self) -> None:
        """Bring the list up to date with the rows, keeping the selection."""
        texts = [_row_text(row) for row in self._rows]
        current = [self._list.item(index).text() for index in range(self._list.count())]
        if texts == current:
            return
        selected = self._list.currentRow()
        self._list.blockSignals(True)
        self._list.clear()
        self._list.addItems(texts)
        self._list.blockSignals(False)
        if 0 <= selected < len(texts):
            self._list.setCurrentRow(selected)

    def _selected_name(self) -> str | None:
        """Return the stage whose pane is showing."""
        index = self._list.currentRow()
        return self._rows[index].name if 0 <= index < len(self._rows) else None

    def _select(self, name: str) -> None:
        """Show one stage's pane."""
        for index, row in enumerate(self._rows):
            if row.name == name:
                self._list.setCurrentRow(index)
                self._show_row(index)
                return

    def _show_row(self, index: int) -> None:
        """Show the pane of the stage at ``index``."""
        if not 0 <= index < len(self._rows):
            return
        row = self._rows[index]
        name = row.name
        self._pictures.setCurrentWidget(self._canvas)
        self._quantity.clear()
        self._quantity.setEnabled(False)
        view = self._views.get(name)
        lines: list[str] = [_row_text(row)]
        if name == "contour" and self._editor is not None:
            self._show_editor()
            lines += list(view.lines) if view is not None else []
            lines += self._editor_lines()
        elif isinstance(view, ImageView):
            self._quantity.addItems(list(view.images))
            self._quantity.setEnabled(len(view.images) > 1)
            self._show_image(view, next(iter(view.images)))
            lines += list(view.lines)
        elif isinstance(view, OutlineView):
            self._canvas.show_outline(view)
            lines += list(view.lines)
        elif isinstance(view, SummaryView) and name == "mesh":
            lines += self._mesh_lines()
            lines += list(view.lines)
            if self._mesh is not None and not self._mesh_problem:
                self._pictures.setCurrentWidget(self._web)
            else:
                self._canvas.clear(
                    self._mesh_problem or "stage 6: drawing the mesh…", frame=MODEL_FRAME
                )
        elif isinstance(view, SummaryView):
            self._canvas.clear(f"stage {row.number}: {row.title}", frame=view.frame)
            lines += list(view.lines)
        else:
            self._canvas.clear(f"stage {row.number}: {row.title}")
            if name in self._view_errors:
                lines.append(self._view_errors[name])
        self._details.setPlainText("\n".join(lines))

    def _requantity(self, index: int) -> None:
        """Show another of a view's images: the mean or one of the variances."""
        view = self._views.get(self._selected_name() or "")
        if isinstance(view, ImageView) and index >= 0:
            self._show_image(view, self._quantity.itemText(index))

    def _show_image(self, view: ImageView, quantity: str) -> None:
        """Show one of a view's images, with its loop and slab."""
        self._canvas.show_image(view.images[quantity], loop=view.loop, slab=view.slab)

    # -- the editor ------------------------------------------------------------------

    def _backdrop(self) -> ImageView | None:
        """Return the stage-3 mean the editor is drawn over: stage 4's view, or stage 3's."""
        for name in ("contour", "symmetry"):
            view = self._views.get(name)
            if isinstance(view, ImageView) and "mean" in view.images:
                return view
        return None

    def _show_editor(self) -> None:
        """Show the editor's loop over the stage-3 mean, in the stage-1 frame."""
        selected = self._canvas.selected if self._canvas.editor is self._editor else None
        backdrop = self._backdrop()
        if backdrop is not None:
            self._canvas.show_image(backdrop.images["mean"], slab=backdrop.slab)
        else:
            self._canvas.clear("the contour, in the stage-1 frame", frame=STAGE_1_FRAME)
        self._canvas.attach(self._editor, selected=selected)
        first = self._assessment.failures[0] if self._assessment is not None else None
        self._canvas.mark(first.location_nm if first is not None else None)

    def edit(self, editor: ProfileEditor) -> None:
        """Edit ``editor``'s loop on the contour pane."""
        self._editor = editor
        self._assessment = None
        self._select("contour")
        self._show_buttons()

    def _editor_lines(self) -> list[str]:
        """Return what the editor has to say: the loader's refusal, and the last measurement."""
        if self._editor is None:
            return []
        lines = [f"editing {self._editor.name}: {len(self._editor.vertices)} vertices"]
        problem = self._editor.problem
        lines.append(f"cannot be saved: {problem}" if problem else "loads as a profile document")
        if self._assessment is not None:
            if self._assessment.passed:
                lines.append("section 5.2.1: every criterion met")
            for failure in self._assessment.failures:
                lines.append(f"section 5.2.1, recorded not enforced: {failure.message}")
        return lines

    def _after_edit(self) -> None:
        """Drop the last measurement, which the edit invalidated, and show the loader's verdict."""
        self._assessment = None
        self._canvas.mark(None)
        self._show_row(self._list.currentRow())
        self._show_buttons()

    def _delete_vertex(self) -> None:
        """Delete the selected vertex, or say why not."""
        refusal = self._canvas.delete_selected()
        if refusal is not None:
            self._status.setText(refusal)

    def _step_back(self) -> None:
        """Undo the last edit."""
        if self._editor is not None and self._editor.undo():
            self._after_edit()

    def _step_forward(self) -> None:
        """Redo the last undone edit."""
        if self._editor is not None and self._editor.redo():
            self._after_edit()

    def measure(self) -> None:
        """Measure the §5.2.1 criteria on the edit, against the stored stages (WP24 D8)."""
        if self._editor is None or self._case_path is None or self._assess is not None:
            return
        self._start_assess(vertices=tuple(self._editor.vertices))
        self._status.setText("measuring the section 5.2.1 criteria against the stored stages")

    def seed(self) -> None:
        """Recompute the refused contour from the stored stage-3 map (§8.2.2 B9, WP24 D10)."""
        if self._case_path is None or self._assess is not None:
            return
        self._start_assess(vertices=None)
        self._status.setText("recomputing the refused contour from the stored stage-3 map")

    def _start_assess(self, *, vertices: tuple[Point, ...] | None) -> None:
        """Spawn the assess child for this case."""
        assert self._case_path is not None
        self._assess = AssessProcess(
            AssessRequest(
                case=str(self._case_path),
                store=None if self._store is None else str(self._store),
                vertices=vertices,
            )
        )
        self._assess.start()
        self._show_buttons()

    def _save_edit(self) -> None:
        """Write the edit and a derived case beside the original (WP24 D5, D6)."""
        if self._editor is None or self._case_path is None or self._document is None:
            return
        try:
            profile, derived = self._editor.save_case(self._document, self._case_path)
        except (ValueError, OSError) as error:
            self._status.setText(f"not saved: {error}")
            return
        self._status.setText(
            f"wrote {profile} and the derived case {derived}; the original is unchanged. Open "
            "the derived case to build the edit"
        )

    # -- showing ---------------------------------------------------------------------

    def _mesh_lines(self) -> list[str]:
        """Return the stage-6 gate figures shown beside the picture (WP24 D12)."""
        if self._mesh is None:
            return [self._mesh_problem] if self._mesh_problem else []
        quality = self._mesh.quality
        lines = [
            f"{self._mesh.elements} triangles; materials {', '.join(self._mesh.materials)}",
            f"minimum SICN {_number(quality['min_sicn'])} at (r, z) = "
            f"{_point(quality['worst_sicn_at_nm'])} nm, {MODEL_FRAME}",
            f"minimum gamma {_number(quality['min_gamma'])} at (r, z) = "
            f"{_point(quality['worst_gamma_at_nm'])} nm; floor {_number(quality['floor'])}",
        ]
        if self._mesh.wall:
            wall = ", ".join(f"{key} {_number(value)}" for key, value in self._mesh.wall.items())
            lines.append(f"wall-size gate: {wall}")
        if self._mesh_problem:
            lines.append(self._mesh_problem)
        return lines

    def _show_buttons(self) -> None:
        """Offer exactly what applies now."""
        in_flight = not self._settled
        rows = {row.name: row for row in self._rows}
        contour = rows.get("contour")
        stored_upstream = "symmetry" in self._views or any(
            row.name == "symmetry" and row.produced is not None for row in self._rows
        )
        idle = self._assess is None
        self._load.setEnabled(not in_flight)
        self._build.setEnabled(not in_flight and can_build(self._case_editor.document))
        self._cancel.setEnabled(in_flight)
        self._measure.setEnabled(self._editor is not None and stored_upstream and idle)
        self._seed.setEnabled(
            contour is not None and contour.status == "failed" and stored_upstream and idle
        )
        self._delete.setEnabled(self._editor is not None)
        self._undo.setEnabled(self._editor is not None and self._editor.can_undo)
        self._redo.setEnabled(self._editor is not None and self._editor.can_redo)
        self._save.setEnabled(self._editor is not None and self._case_path is not None)

    # -- for tests -------------------------------------------------------------------

    @property
    def canvas(self) -> GeometryCanvas:
        """The picture pane."""
        return self._canvas

    @property
    def control(self) -> RunControl:
        """The build's view-model."""
        return self._control

    @property
    def rows(self) -> tuple[StageRow, ...]:
        """The stage list as last shown."""
        return self._rows

    def status(self) -> str:
        """Return the message the tab is showing."""
        return str(self._status.text())

    def details(self) -> str:
        """Return the text beside the picture."""
        return str(self._details.toPlainText())


def _row_text(row: StageRow) -> str:
    """One line of the stage list: number, title, status and the hash's head."""
    status = "from the store" if row.status == "cached" else row.status
    head = f" {row.hash[:12]}" if row.hash else ""
    return f"{row.number}. {row.title} — {status}{head}"


def _number(value: object) -> str:
    """Format a gate figure to four significant figures."""
    return f"{value:.4g}" if isinstance(value, float) else str(value)


def _point(value: object) -> str:
    """Format an ``(r, z)`` pair to four significant figures."""
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return f"({_number(float(value[0]))}, {_number(float(value[1]))})"
    return str(value)

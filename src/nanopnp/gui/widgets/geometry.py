"""The Geometry tab: stages 1 to 6 as they land, and a hand edit of the contour (WP24)."""

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
from nanopnp.io.case import CaseValidationError
from nanopnp.io.case_paths import UnknownCasePathError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.gui.case_model import CaseEditor
    from nanopnp.gui.solver import Produced
    from nanopnp.io.case import CaseDocument

logger = logging.getLogger(__name__)

__all__ = ["GeometryCanvas", "GeometryWidget"]

POLL_INTERVAL_MS = 100

Point = tuple[float, float]


class GeometryCanvas(QtWidgets.QWidget):
    edited = QtCore.Signal()

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

    def clear(self, title: str = "", *, frame: str = STAGE_1_FRAME) -> None:
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
        # A pane re-shown mid-drag abandons the drag, and the frozen transform with it:
        # left set, transform() would return it for every picture shown afterwards.
        self._drag = None
        self._drag_transform = None
        self._preview = None
        self.update()

    def show_image(
        self,
        image: ImageModel,
        *,
        loop: tuple[Point, ...] = (),
        slab: tuple[float, float] | None = None,
    ) -> None:
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
        self.clear(f"stage 5: region, reservoir radius {view.reservoir_nm:g} nm", frame=view.frame)
        self._x_label = "r (nm)"
        self._loop = view.loop
        self._slab = view.slab
        self._chord = view.chord
        self.update()

    def attach(self, editor: ProfileEditor | None, *, selected: int | None = None) -> None:
        self._editor = editor
        in_loop = editor is not None and selected is not None and selected < len(editor.vertices)
        self._selected = selected if in_loop else None
        self._drag = None
        self._drag_transform = None
        self._preview = None
        if editor is not None:
            self._loop = ()
            self._title = f"{self._title} — editing {editor.name}" if self._title else editor.name
        self.update()

    def mark(self, location_nm: Point | None) -> None:
        self._marker = location_nm
        self.update()

    def _vertices(self) -> list[Point]:
        if self._editor is None:
            return list(self._loop)
        shown = list(self._editor.vertices)
        if self._drag is not None and self._preview is not None:
            shown[self._drag] = self._preview
        return shown

    def transform(self) -> ViewTransform:
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

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("white"))
        transform = self.transform()
        if self._image is not None and self._qimage is not None:
            left, top, width, height = transform.rectangle(*self._image.extent_nm)
            # Unsmoothed: a pixel is the value at its node, not blended into its neighbours'.
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
        x_low, x_high = self.transform().x_range
        z_low, z_high = self.transform().z_range
        return (
            f"{self._x_label} {x_low:.3g} to {x_high:.3g} across, z (nm) {z_low:.3g} to "
            f"{z_high:.3g} up; {self._frame}"
        )

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
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
        if self._drag is None or self._drag_transform is None:
            super().mouseMoveEvent(event)
            return
        position = event.position()
        self._preview = self._drag_transform.to_data(position.x(), position.y())
        self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag is None or self._drag_transform is None or self._editor is None:
            super().mouseReleaseEvent(event)
            return
        position = event.position()
        r, z = self._drag_transform.to_data(position.x(), position.y())
        index = self._drag
        moved = self._preview is not None
        self._drag = None
        self._drag_transform = None
        self._preview = None
        if moved:
            self._editor.move(index, r, z)
            self.edited.emit()
        self.update()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
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
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            self.delete_selected()
            return
        super().keyPressEvent(event)

    def delete_selected(self) -> str | None:
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
        return self._selected

    @property
    def editor(self) -> ProfileEditor | None:
        return self._editor


class GeometryWidget(QtWidgets.QWidget):
    buildRequested = QtCore.Signal()

    structureLoaded = QtCore.Signal(str)

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
        self._buildable: tuple[CaseDocument, bool] | None = None

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

    def _pick_structure(self) -> None:
        chosen, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load a structure",
            "",
            "Structures (*.pdb *.cif *.mmcif *.pqr);;All files (*)",
        )
        if chosen:
            self.load_structure(chosen)

    def load_structure(self, path: str | Path) -> Path | None:
        try:
            staged = load_structure(self._case_editor, path)
        except (UnknownCasePathError, CaseValidationError) as error:
            self._status.setText(str(error))
            return None
        self._status.setText(f"structure.source.path staged: {staged}; build to see it")
        self.structureLoaded.emit(str(staged))
        return staged

    def _ask_build(self) -> None:
        self.buildRequested.emit()

    def build(self, case_path: str | Path, *, upto: str = BUILD_UPTO) -> bool:
        document = self._case_editor.document
        try:
            planned = planned_stages(document)
        except (ValueError, NotImplementedError) as error:
            self._status.setText(f"not built: {error}")
            return False
        try:
            self._control.start(case_path, store=self._store, upto=upto)
        except RuntimeError as error:
            self._status.setText(f"not built: {error}")
            return False
        self._stop_children()
        self._case_path = Path(case_path)
        self._document = document
        self._stages = StageList(planned)
        self._views.clear()
        self._view_errors.clear()
        # The previous build's pending loads are dropped rather than left to
        # read their maps on the one worker ahead of this build's.
        for future in self._loading.values():
            future.cancel()
        self._loading.clear()
        self._requested.clear()
        self._editor = None
        self._assessment = None
        self._mesh = None
        self._mesh_problem = ""
        self._settled = False
        self._status.setText(f"building {self._case_path} through {upto!r}")
        self.refresh()
        return True

    def _stop(self) -> None:
        self._control.cancel()

    def _stop_children(self) -> None:
        for process in (self._assess, self._render):
            if process is not None:
                process.terminate()
        self._assess = None
        self._render = None

    def shutdown(self) -> None:
        self._timer.stop()
        self._control.cancel()
        self._stop_children()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def refresh(self) -> RunModel:
        model = self._control.poll()
        produced = {event.name: event for event in model.produced}
        document = self._document
        if document is not None:
            for event in model.produced:
                # Only the stages the list shows: the walk also reports ``case``,
                # which has no pane and which ``load_view`` would refuse.
                if event.name in self._stages.planned and event.name not in self._requested:
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
        try:
            view = future.result()
        except Exception as error:  # the pane shows it; the tab stays usable
            self._view_errors[name] = f"{type(error).__name__}: {error}"
        else:
            self._views[name] = view
            if isinstance(view, ImageView) and view.profile is not None and self._editor is None:
                self._editor = ProfileEditor.from_profile(view.profile)
        if self._selected_name() == name:
            self._show_row(self._list.currentRow())

    def _built(self, model: RunModel, produced: dict[str, Produced]) -> None:
        if model.state == "finished" and "mesh" in produced and model.directory is not None:
            self._render = RenderProcess(MeshRequest(run=str(model.directory)))
            self._render.start()
        last = model.log[-1] if model.log else model.state
        self._status.setText(last)

    def _drain_assess(self) -> None:
        if self._assess is None:
            return
        # Liveness first, then the queue: a child that posts and exits between a
        # drain and the check would otherwise be forgotten with its answer unread.
        finished = not self._assess.running
        measured = self._assess.request.vertices
        events = self._assess.drain()
        for event in events:
            if isinstance(event, Assessed):
                if self._editor is None or tuple(self._editor.vertices) != measured:
                    # The loop was edited while it was measured: the verdict is
                    # another loop's, and showing it here would attribute it to
                    # this one.
                    self._status.setText(
                        "the edit changed while it was being measured; measure it again"
                    )
                    continue
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
        if finished:
            self._assess.join(0.0)
            if not self._assess.answered:
                logger.error("the assess child exited without answering")
                self._status.setText(
                    "the measuring process exited without an answer (killed or crashed)"
                )
            self._assess = None
        if events or finished:
            self._show_row(self._list.currentRow())

    def _drain_render(self) -> None:
        if self._render is None:
            return
        # Liveness before the queue, as :meth:`_drain_assess` does and for the same reason.
        finished = not self._render.running
        for event in self._render.drain():
            if isinstance(event, RenderedMesh):
                self._mesh = event
                # A file URL, never setHtml: the scene is megabytes.
                self._web.load(QtCore.QUrl.fromLocalFile(event.document))
            elif isinstance(event, RenderFailed):
                self._mesh_problem = f"{event.error}: {event.message}"
        if finished:
            self._render.join(0.0)
            if not self._render.answered:
                logger.error("the render child exited without answering")
                self._mesh_problem = (
                    "the render process exited without drawing the mesh (killed or crashed)"
                )
            self._render = None
            if self._selected_name() == "mesh":
                self._show_row(self._list.currentRow())

    def _mesh_loaded(self, ok: bool) -> None:
        if not ok:
            self._mesh_problem = "the mesh document did not load"
            if self._selected_name() == "mesh":
                self._show_row(self._list.currentRow())
            return
        self._web.page().runJavaScript(readiness_script(), self._mesh_answered)

    def _mesh_answered(self, answer: object) -> None:
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

    def _show_rows(self) -> None:
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
        index = self._list.currentRow()
        return self._rows[index].name if 0 <= index < len(self._rows) else None

    def _select(self, name: str) -> None:
        for index, row in enumerate(self._rows):
            if row.name == name:
                self._list.setCurrentRow(index)
                self._show_row(index)
                return

    def _show_row(self, index: int) -> None:
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
        view = self._views.get(self._selected_name() or "")
        if isinstance(view, ImageView) and index >= 0:
            self._show_image(view, self._quantity.itemText(index))

    def _show_image(self, view: ImageView, quantity: str) -> None:
        self._canvas.show_image(view.images[quantity], loop=view.loop, slab=view.slab)

    def _backdrop(self) -> ImageView | None:
        for name in ("contour", "symmetry"):
            view = self._views.get(name)
            if isinstance(view, ImageView) and "mean" in view.images:
                return view
        return None

    def _show_editor(self) -> None:
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
        self._editor = editor
        self._assessment = None
        self._select("contour")
        self._show_buttons()

    def _editor_lines(self) -> list[str]:
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
        self._assessment = None
        self._canvas.mark(None)
        self._show_row(self._list.currentRow())
        self._show_buttons()

    def _delete_vertex(self) -> None:
        refusal = self._canvas.delete_selected()
        if refusal is not None:
            self._status.setText(refusal)

    def _step_back(self) -> None:
        if self._editor is not None and self._editor.undo():
            self._after_edit()

    def _step_forward(self) -> None:
        if self._editor is not None and self._editor.redo():
            self._after_edit()

    def measure(self) -> None:
        if self._editor is None or self._case_path is None or self._assess is not None:
            return
        self._start_assess(vertices=tuple(self._editor.vertices))
        self._status.setText("measuring the section 5.2.1 criteria against the stored stages")

    def seed(self) -> None:
        if self._case_path is None or self._assess is not None:
            return
        self._start_assess(vertices=None)
        self._status.setText("recomputing the refused contour from the stored stage-3 map")

    def _start_assess(self, *, vertices: tuple[Point, ...] | None) -> None:
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

    def _mesh_lines(self) -> list[str]:
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
        in_flight = not self._settled
        rows = {row.name: row for row in self._rows}
        contour = rows.get("contour")
        stored_upstream = "symmetry" in self._views or any(
            row.name == "symmetry" and row.produced is not None for row in self._rows
        )
        idle = self._assess is None
        self._load.setEnabled(not in_flight)
        self._build.setEnabled(not in_flight and self._can_build())
        self._cancel.setEnabled(in_flight)
        self._measure.setEnabled(self._editor is not None and stored_upstream and idle)
        self._seed.setEnabled(
            contour is not None and contour.status == "failed" and stored_upstream and idle
        )
        self._delete.setEnabled(self._editor is not None)
        self._undo.setEnabled(self._editor is not None and self._editor.can_undo)
        self._redo.setEnabled(self._editor is not None and self._editor.can_redo)
        self._save.setEnabled(self._editor is not None and self._case_path is not None)

    def _can_build(self) -> bool:
        document = self._case_editor.document
        if self._buildable is None or self._buildable[0] is not document:
            self._buildable = (document, can_build(document))
        return self._buildable[1]

    @property
    def canvas(self) -> GeometryCanvas:
        return self._canvas

    @property
    def control(self) -> RunControl:
        return self._control

    @property
    def rows(self) -> tuple[StageRow, ...]:
        return self._rows

    def status(self) -> str:
        return str(self._status.text())

    def details(self) -> str:
        return str(self._details.toPlainText())


def _row_text(row: StageRow) -> str:
    status = "from the store" if row.status == "cached" else row.status
    head = f" {row.hash[:12]}" if row.hash else ""
    return f"{row.number}. {row.title} — {status}{head}"


def _number(value: object) -> str:
    return f"{value:.4g}" if isinstance(value, float) else str(value)


def _point(value: object) -> str:
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return f"({_number(float(value[0]))}, {_number(float(value[1]))})"
    return str(value)

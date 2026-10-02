"""The Charge tab: stage 7 as it lands, its pictures and its records (WP31).

A projection of :mod:`nanopnp.gui.charge` and the render child's charge request,
and nothing more. What a stage produced, what a pixel holds, what a leg's margin
is and which residue is flagged are all answered on the far side of the Qt
boundary, where ``tests/tier1/test_gui_charge.py`` reaches them without a display.

**One build, shared with the Geometry tab** (D2). **Build charge** is the
Geometry tab's walk taken on to ``upto="charge"``: the same spawned child and
the same cancel token, so the Geometry tab still shows stages 1 to 6 as they
land and this tab shows stage 7's two halves. The payloads are read on a worker
thread, because the reference lattice is about fifteen million nodes (WP24 D11).

**Four panes** (D3). *Protonation*: a frame selector and one row per PROPKA
group, read from the stored table (D11). *Charge map*: the export lattice as
stored, on a diverging scale centred on zero, with the recorded worst planes
marked (D5, D6, D8, D9). *Deployed field*: the coefficient the solve assembles,
drawn by the render child (D7). *Conservation*: each leg against the tolerance
its own record carries (D10). Every picture is in the model frame and says so
(D4).
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, get_args

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineWidgets import QWebEngineView

from nanopnp.gui.charge import (
    BUILD_UPTO,
    CHARGE_STAGES,
    ChargeMap,
    ChargeView,
    ProtonationView,
    build_offer,
    charge_stages,
    load_charge,
    load_protonation,
)
from nanopnp.gui.geometry import MODEL_FRAME, StageList, StageRow
from nanopnp.gui.render import (
    ChargeQuantity,
    ChargeRequest,
    RenderedCharge,
    RenderFailed,
    RenderProcess,
    readiness_script,
)
from nanopnp.gui.run_model import RunControl, RunModel
from nanopnp.gui.widgets.geometry import GeometryCanvas

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.gui.case_model import CaseEditor
    from nanopnp.io.case import CaseDocument

logger = logging.getLogger(__name__)

__all__ = ["ChargeCanvas", "ChargeWidget"]

POLL_INTERVAL_MS = 100
"""How often the build, the view loads and the render child are polled."""

PANES = ("Protonation", "Charge map", "Deployed field", "Conservation")
"""The tab's panes, in order (D3)."""


class ChargeCanvas(GeometryCanvas):
    """The charge map: the lattice's picture, with the recorded worst planes across it (D9).

    A :class:`GeometryCanvas` showing one image and no editor, plus a dashed
    horizontal line at each plane's ``z``, labelled as the record names it.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._planes: tuple[tuple[str, float], ...] = ()

    def show_charge(self, picture: ChargeMap) -> None:
        """Show the map and mark its planes."""
        self.show_image(picture.image)
        self._planes = picture.planes
        self.update()

    def clear(self, title: str = "", *, frame: str = MODEL_FRAME) -> None:
        """Show nothing but a caption, and no planes."""
        self._planes = ()
        super().clear(title, frame=frame)

    @property
    def planes(self) -> tuple[tuple[str, float], ...]:
        """The planes marked, ``(label, z_nm)``."""
        return self._planes

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Draw the picture, then each plane as a dashed line across it."""
        super().paintEvent(event)
        if not self._planes:
            return
        transform = self.transform()
        x_low, x_high = transform.x_range
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(QtGui.QColor("black"), 1.5, QtCore.Qt.PenStyle.DashLine))
        for label, z_nm in self._planes:
            left = QtCore.QPointF(*transform.to_screen(x_low, z_nm))
            right = QtCore.QPointF(*transform.to_screen(x_high, z_nm))
            painter.drawLine(left, right)
            painter.drawText(left + QtCore.QPointF(4.0, -3.0), f"{label}, z = {z_nm:.4g} nm")
        painter.end()


class ChargeWidget(QtWidgets.QWidget):
    """The Charge tab: a stage list and four panes over stage 7's artefacts.

    Parameters
    ----------
    editor
        The case open for editing; whether a build is offered is read from it.
    control
        The build's view-model. The window passes the Geometry tab's, so the
        two tabs share one walk (D2); a test may pass a fresh one.
    store
        The artefact store's root, or ``None`` for the process default.
    """

    buildRequested = QtCore.Signal()
    """Emitted when the user asks to build. The window commits and saves the case first."""

    def __init__(
        self,
        editor: CaseEditor,
        control: RunControl,
        *,
        store: Path | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._case_editor = editor
        self._control = control
        self._store = store
        self._model: RunModel | None = None
        self._settled = True
        self._stages = StageList(())
        self._rows: tuple[StageRow, ...] = ()
        self._protonation: ProtonationView | None = None
        self._charge: ChargeView | None = None
        self._errors: dict[str, str] = {}
        self._loading: dict[str, Future[ProtonationView | ChargeView]] = {}
        self._requested: set[str] = set()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nanopnp-charge")
        self._render: RenderProcess | None = None
        self._drawn: RenderedCharge | None = None
        self._draw_problem = ""
        self._offer: tuple[CaseDocument, bool, str] | None = None

        self._build = QtWidgets.QPushButton("Build charge")
        self._cancel = QtWidgets.QPushButton("Cancel")
        self._reason = QtWidgets.QLabel()
        self._reason.setWordWrap(True)
        self._list = QtWidgets.QListWidget()
        self._list.setMinimumWidth(240)
        self._panes = QtWidgets.QTabWidget()

        # Protonation (D11).
        self._frame = QtWidgets.QComboBox()
        self._table = QtWidgets.QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["chain", "residue", "group", "applied (e)", "pKa", "expected (e)", "unapplied"]
        )
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._protonation_notes = _notes()
        protonation = _pane(self._frame, self._table, self._protonation_notes)

        # Charge map (D5, D6, D8, D9).
        self._canvas = ChargeCanvas()
        self._map_notes = _notes()
        charge_map = _pane(self._canvas, self._map_notes)

        # Deployed field (D7).
        self._quantity = QtWidgets.QComboBox()
        self._web = QWebEngineView()
        self._web_message = QtWidgets.QLabel("no deployed field yet")
        self._web_message.setWordWrap(True)
        self._web_message.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._pictures = QtWidgets.QStackedWidget()
        self._pictures.addWidget(self._web_message)
        self._pictures.addWidget(self._web)
        self._field_notes = _notes()
        deployed = _pane(self._quantity, self._pictures, self._field_notes)

        # Conservation (D10).
        self._legs = QtWidgets.QTableWidget(0, 5)
        self._legs.setHorizontalHeaderLabels(["leg", "value", "tolerance", "ratio", "where / why"])
        self._legs.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._figures = _notes()
        conservation = _pane(self._legs, self._figures)

        for widget, title in zip(
            (protonation, charge_map, deployed, conservation), PANES, strict=True
        ):
            self._panes.addTab(widget, title)

        self._status = QtWidgets.QLabel("no build yet")
        self._status.setWordWrap(True)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self._build)
        buttons.addWidget(self._cancel)
        buttons.addWidget(self._reason, 1)
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self._list)
        splitter.addWidget(self._panes)
        splitter.setStretchFactor(1, 1)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(splitter, 1)
        layout.addWidget(self._status)

        self._build.clicked.connect(self.buildRequested.emit)
        self._cancel.clicked.connect(self._control_cancel)
        self._frame.activated.connect(self._show_frame)
        self._quantity.activated.connect(self._requantity)
        self._web.loadFinished.connect(self._field_loaded)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self._show_panes()
        self._show_buttons()

    # -- building --------------------------------------------------------------------

    def build(self, case_path: str | Path) -> bool:
        """Start a walk through ``charge`` on this tab's control, and follow it.

        The window starts the walk through the Geometry tab instead, so that
        tab shows stages 1 to 6, and calls :meth:`follow`; this is the same
        walk for a tab that stands alone.

        Returns
        -------
        bool
            Whether the build started.
        """
        offer = build_offer(self._case_editor.document)
        if not offer.offered:
            self._status.setText(f"not built: {offer.reason}")
            return False
        try:
            self._control.start(case_path, store=self._store, upto=BUILD_UPTO)
        except RuntimeError as error:
            self._status.setText(f"not built: {error}")
            return False
        return self.follow(case_path)

    def follow(self, case_path: str | Path) -> bool:
        """Show the walk the control has just started as this tab's build (D2).

        Returns
        -------
        bool
            Whether the case walks stage 7; if not, the tab says why and
            follows nothing.
        """
        document = self._case_editor.document
        try:
            planned = charge_stages(document)
        except (ValueError, NotImplementedError, KeyError) as error:
            self._status.setText(f"not built: {error}")
            return False
        self._stop_render()
        for future in self._loading.values():
            future.cancel()
        self._loading.clear()
        self._requested.clear()
        self._errors.clear()
        self._protonation = None
        self._charge = None
        self._drawn = None
        self._draw_problem = ""
        self._model = self._control.model
        self._stages = planned
        self._settled = False
        self._status.setText(f"building {case_path} through {BUILD_UPTO!r}")
        self._show_panes()
        self.refresh()
        return True

    def _control_cancel(self) -> None:
        """Cancel the build; a cancelled walk writes no artefact (§5.3.2)."""
        self._control.cancel()

    def _stop_render(self) -> None:
        """Stop the render child, whose answer no longer applies."""
        if self._render is not None:
            self._render.terminate()
        self._render = None

    def shutdown(self) -> None:
        """Stop everything this tab started: the render child and the view loads.

        The walk is the Geometry tab's to stop when the window shares it; a tab
        standing alone cancels its own.
        """
        self._timer.stop()
        self._control.cancel()
        self._stop_render()
        self._executor.shutdown(wait=False, cancel_futures=True)

    # -- polling ---------------------------------------------------------------------

    def refresh(self) -> RunModel | None:
        """Poll the build, the view loads and the render child, and show where they are."""
        model = self._control.poll()
        if self._model is None:
            self._show_buttons()
            return None
        if model is not self._model:
            # Another build has started on the shared control (Build geometry):
            # what is shown belongs to a walk that is no longer the current one.
            self._model = None
            self._stages = StageList(())
            self._rows = ()
            self._protonation = None
            self._charge = None
            self._stop_render()
            self._status.setText("a later build replaced this one; build charge to see stage 7")
            self._show_rows()
            self._show_panes()
            self._show_buttons()
            return None
        for event in model.produced:
            if event.name in self._stages.planned and event.name not in self._requested:
                self._requested.add(event.name)
                loader = load_protonation if event.name == CHARGE_STAGES[0] else load_charge
                self._loading[event.name] = self._executor.submit(loader, event)
        for name, future in list(self._loading.items()):
            if future.done():
                del self._loading[name]
                self._landed(name, future)
        if model.settled and not self._settled:
            self._settled = True
            self._status.setText(model.log[-1] if model.log else model.state)
        self._maybe_draw(model)
        self._drain_render()
        self._rows = self._stages.rows(model)
        self._show_rows()
        self._show_buttons()
        return model

    def _landed(self, name: str, future: Future[ProtonationView | ChargeView]) -> None:
        """Keep a loaded view and show it."""
        try:
            view = future.result()
        except Exception as error:  # the pane shows it; the tab stays usable
            self._errors[name] = f"{type(error).__name__}: {error}"
        else:
            if isinstance(view, ProtonationView):
                self._protonation = view
            else:
                self._charge = view
        self._show_panes()

    def _maybe_draw(self, model: RunModel) -> None:
        """Ask for the deployed field once the walk has finished and stage 7 is read."""
        if (
            self._render is not None
            or self._drawn is not None
            or self._draw_problem
            or model.state != "finished"
            or model.directory is None
            or self._charge is None
            or not self._charge.quantities
        ):
            return
        self._draw(self._charge.quantities[0])

    def _draw(self, quantity: ChargeQuantity) -> None:
        """Start the render child on one deployed quantity."""
        directory = self._model.directory if self._model is not None else None
        if directory is None:
            return
        self._stop_render()
        self._drawn = None
        self._draw_problem = ""
        self._render = RenderProcess(ChargeRequest(run=str(directory), quantity=quantity))
        self._render.start()
        self._pictures.setCurrentWidget(self._web_message)
        self._web_message.setText(f"drawing the deployed {quantity}…")

    def _requantity(self, index: int) -> None:
        """Draw the other deployed quantity."""
        text = self._quantity.itemText(index)
        for quantity in get_args(ChargeQuantity):
            if quantity == text:
                self._draw(quantity)

    def _drain_render(self) -> None:
        """Load the picture the render child wrote, or keep its refusal."""
        if self._render is None:
            return
        # Liveness before the queue, as the Geometry tab drains its children.
        finished = not self._render.running
        events = self._render.drain()
        for event in events:
            if isinstance(event, RenderedCharge):
                self._drawn = event
                # A file URL, never ``setHtml``: the scene is megabytes (WP15 D8).
                self._web.load(QtCore.QUrl.fromLocalFile(event.document))
                self._pictures.setCurrentWidget(self._web)
            elif isinstance(event, RenderFailed):
                self._draw_problem = f"{event.error}: {event.message}"
        if finished:
            self._render.join(0.0)
            if not self._render.answered:
                logger.error("the render child exited without answering")
                self._draw_problem = (
                    "the render process exited without drawing the field (killed or crashed)"
                )
            self._render = None
        if events or finished:
            # The answer can land while the child is still exiting: shown now,
            # not on the poll that sees it gone.
            self._show_field()

    def _field_loaded(self, ok: bool) -> None:
        """Ask the document whether it drew, as the Fields panel does."""
        if not ok:
            self._draw_problem = "the deployed-field document did not load"
            self._show_field()
            return
        self._web.page().runJavaScript(readiness_script(), self._field_answered)

    def _field_answered(self, answer: object) -> None:
        """Keep the document's own account of a picture that did not draw."""
        try:
            state = json.loads(answer) if isinstance(answer, str) else {}
        except json.JSONDecodeError:
            state = {}
        if not state.get("ready"):
            self._draw_problem = (
                f"the deployed field did not draw: {state.get('error') or 'no answer'} "
                f"(renderer loaded: {bool(state.get('renderer_loaded'))})"
            )
        self._show_field()

    # -- showing ---------------------------------------------------------------------

    def _show_rows(self) -> None:
        """Bring the stage list up to date with the rows."""
        texts = [_row_text(row) for row in self._rows]
        current = [self._list.item(index).text() for index in range(self._list.count())]
        if texts != current:
            self._list.clear()
            self._list.addItems(texts)

    def _show_panes(self) -> None:
        """Show every pane from the views loaded so far."""
        self._show_protonation()
        self._show_map()
        self._show_field()
        self._show_conservation()

    def _show_protonation(self) -> None:
        """Fill the protonation pane, or say why it is empty (D3, D11)."""
        index = PANES.index("Protonation")
        walks = CHARGE_STAGES[0] in self._stages.planned or self._model is None
        self._panes.setTabEnabled(index, walks)
        self._panes.setTabToolTip(
            index,
            ""
            if walks
            else "this case supplies its charge through inputs.charge, so nothing is protonated",
        )
        view = self._protonation
        self._frame.blockSignals(True)
        self._frame.clear()
        if view is not None:
            self._frame.addItems(
                [f"frame {index}: Q_net {q:+.4g} e" for index, q in enumerate(view.q_net_e)]
            )
        self._frame.blockSignals(False)
        self._frame.setEnabled(view is not None and view.frames > 1)
        if view is None:
            self._table.setRowCount(0)
            self._protonation_notes.setPlainText(self._errors.get(CHARGE_STAGES[0], ""))
            return
        self._show_frame(0)

    def _show_frame(self, index: int) -> None:
        """Show one frame's rows (D11)."""
        view = self._protonation
        if view is None or not 0 <= index < view.frames:
            return
        frame = view.frame(index)
        self._table.setRowCount(len(frame.rows))
        for row, entry in enumerate(frame.rows):
            cells = (
                entry.chain,
                entry.residue,
                entry.group,
                f"{entry.applied_e:+.4g}",
                "not computed" if entry.pka is None else f"{entry.pka:.2f}",
                "" if entry.expected_e is None else f"{entry.expected_e:+.4g}",
                "unapplied" if entry.unapplied else "",
            )
            for column, text in enumerate(cells):
                self._table.setItem(row, column, QtWidgets.QTableWidgetItem(text))
        lines = [f"frame {frame.index}: Q_net {frame.q_net_e:+.6g} e", *view.settings]
        lines.append(f"pKa: {view.pka_status}")
        differences = view.chain_differences
        lines.append(
            f"chain differences: {len(differences)}" if differences else "chain differences: none"
        )
        lines += [f"  {entry}" for entry in differences]
        for message, count in view.warnings:
            lines.append(f"warning ({count}x): {message}")
        self._protonation_notes.setPlainText("\n".join(lines))

    def _show_map(self) -> None:
        """Fill the charge-map pane (D5, D6, D8, D9)."""
        view = self._charge
        if view is None or view.charge is None:
            reason = self._errors.get(BUILD_UPTO, "")
            if view is not None:
                reason = "stage 7 recorded no export lattice: the case supplies its charge"
            self._canvas.clear(reason or "stage 7: the charge map", frame=MODEL_FRAME)
            self._map_notes.setPlainText(reason)
            return
        picture = view.charge
        self._canvas.show_charge(picture)
        figures = view.conservation.figures if view.conservation is not None else {}
        self._map_notes.setPlainText(
            "\n".join(
                [
                    f"{picture.quantity} in {picture.units}, {view.frame}",
                    f"scale: -{picture.limit:.4g} to {picture.limit:.4g} {picture.units}, zero "
                    "at the centre",
                    f"block: {picture.block} x {picture.block} lattice nodes per pixel, "
                    "trapezoid-weighted means",
                    f"charge of the picture: {picture.integral_e:+.12g} e; q_grid_e recorded "
                    f"{figures.get('q_grid_e')}, q_net_e {figures.get('q_net_e')}",
                    *(f"{label}: z = {z:.6g} nm" for label, z in picture.planes),
                ]
            )
        )

    def _show_field(self) -> None:
        """Fill the deployed-field pane (D7, D8)."""
        view = self._charge
        offered = view.quantities if view is not None else ()
        current = tuple(self._quantity.itemText(index) for index in range(self._quantity.count()))
        if current != offered:
            self._quantity.blockSignals(True)
            self._quantity.clear()
            self._quantity.addItems(list(offered))
            self._quantity.blockSignals(False)
        if self._drawn is not None:
            self._quantity.setCurrentText(self._drawn.quantity)
        self._quantity.setEnabled(len(offered) > 1 and self._render is None)
        lines: list[str] = []
        if self._drawn is not None:
            drawn = self._drawn
            low, high = drawn.colour_range
            lines += [
                f"{drawn.name} in {drawn.units}, {MODEL_FRAME}",
                f"colour range {low:.4g} to {high:.4g}, fixed; largest drawn {drawn.limit:.4g}",
                f"{drawn.elements} triangles; materials {', '.join(drawn.materials)}",
            ]
        if self._draw_problem:
            lines.append(self._draw_problem)
            self._pictures.setCurrentWidget(self._web_message)
            self._web_message.setText(self._draw_problem)
        if view is not None:
            lines += ["dielectric:", *(f"  {line}" for line in view.dielectric)]
        self._field_notes.setPlainText("\n".join(lines))

    def _show_conservation(self) -> None:
        """Fill the conservation pane (D10)."""
        view = self._charge.conservation if self._charge is not None else None
        if view is None:
            self._legs.setRowCount(0)
            self._figures.setPlainText(self._errors.get(BUILD_UPTO, ""))
            return
        self._legs.setRowCount(len(view.legs))
        for row, leg in enumerate(view.legs):
            ratio = leg.ratio
            cells = (
                leg.name,
                "not run" if leg.value is None else f"{leg.value:.4g}",
                "" if leg.tolerance is None else f"{leg.tolerance:.4g}",
                "" if ratio is None else f"{ratio:.3g}",
                leg.location if leg.run else leg.reason,
            )
            for column, text in enumerate(cells):
                self._legs.setItem(row, column, QtWidgets.QTableWidgetItem(text))
        self._figures.setPlainText(
            "\n".join(
                [f"source: {view.source}"]
                + [f"{key}: {value}" for key, value in view.figures.items() if value is not None]
            )
        )

    def _show_buttons(self) -> None:
        """Offer exactly what applies now (D2)."""
        model = self._control.model
        in_flight = self._control.process is not None and not model.settled
        offered, reason = self._offered()
        self._build.setEnabled(not in_flight and offered)
        self._cancel.setEnabled(in_flight and self._model is model)
        self._reason.setText("" if offered else reason)

    def _offered(self) -> tuple[bool, str]:
        """:func:`build_offer` of the editor's document, resolved once per document."""
        document = self._case_editor.document
        if self._offer is None or self._offer[0] is not document:
            offer = build_offer(document)
            self._offer = (document, offer.offered, offer.reason)
        return self._offer[1], self._offer[2]

    # -- for tests -------------------------------------------------------------------

    @property
    def control(self) -> RunControl:
        """The build's view-model."""
        return self._control

    @property
    def rows(self) -> tuple[StageRow, ...]:
        """The stage list as last shown."""
        return self._rows

    @property
    def canvas(self) -> ChargeCanvas:
        """The charge map."""
        return self._canvas

    @property
    def panes(self) -> QtWidgets.QTabWidget:
        """The four panes."""
        return self._panes

    @property
    def protonation_table(self) -> QtWidgets.QTableWidget:
        """The protonation pane's table."""
        return self._table

    @property
    def conservation_table(self) -> QtWidgets.QTableWidget:
        """The conservation pane's legs."""
        return self._legs

    @property
    def drawn(self) -> RenderedCharge | None:
        """The deployed field last drawn."""
        return self._drawn

    @property
    def build_button(self) -> QtWidgets.QPushButton:
        """**Build charge**."""
        return self._build

    def reason(self) -> str:
        """Return why **Build charge** is not offered, or ``""``."""
        return str(self._reason.text())

    def status(self) -> str:
        """Return the message the tab is showing."""
        return str(self._status.text())

    def notes(self, pane: str) -> str:
        """Return the text under one pane, by its title."""
        widget = {
            "Protonation": self._protonation_notes,
            "Charge map": self._map_notes,
            "Deployed field": self._field_notes,
            "Conservation": self._figures,
        }[pane]
        return str(widget.toPlainText())


def _notes() -> QtWidgets.QPlainTextEdit:
    """Return a read-only text area for a pane's figures."""
    notes = QtWidgets.QPlainTextEdit()
    notes.setReadOnly(True)
    notes.setMaximumHeight(200)
    return notes


def _pane(*widgets: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Return a pane stacking ``widgets`` top to bottom, the last but one stretching.

    The last is always the pane's notes; the one above it is the picture or table.
    """
    pane = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(pane)
    stretching = len(widgets) - 2
    for index, widget in enumerate(widgets):
        layout.addWidget(widget, 1 if index == stretching else 0)
    return pane


def _row_text(row: StageRow) -> str:
    """One line of the stage list: title, status and the hash's head."""
    status = "from the store" if row.status == "cached" else row.status
    head = f" {row.hash[:12]}" if row.hash else ""
    return f"{row.number}. {row.title} — {status}{head}"

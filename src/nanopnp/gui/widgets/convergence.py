"""The live convergence panel: two hand-stroked polylines, banded by rung.

Hand-stroked with :class:`QtGui.QPainter` rather than drawn by a charting
library, and the reason is the bundle. ADR-004 packages the shell one-dir with
PyInstaller and CON-07 forbids anything on the user path that needs a compiler or
a source build; a plotting dependency is a second payload for PyInstaller to find
and a second licence in ``LICENSES-BUNDLE.md``, bought for four polylines and a
set of decade ticks. The shapes it would draw are the shapes below.

Nothing here decides anything. The log mapping, the banding, the decimation, the
axis range and the tick selection all live in
:mod:`nanopnp.gui.convergence`, which imports no Qt and is therefore asserted on
the push gate, where ``PySide6.QtWidgets`` does not import at all
(`.knowledge/07-software-stack.md` §5). This widget maps that model's
coordinates onto pixels and strokes them.

**No threshold line is drawn**, because NUM-16's criterion is per rung and
disjunctive — the residual relative to its value on entry, *or* the relative
update on the undamped direction — and one horizontal rule would claim a
criterion the solver does not use. What the panel says instead is
:meth:`~nanopnp.gui.convergence.Band.note`, one line per band under the plot:
how many steps the rung took, which test the recorded numbers show closed it,
how far the damping fell, and how many steps NUM-16 forced.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from nanopnp.gui.convergence import RESIDUAL, UPDATE, Band, ConvergenceModel, Series

__all__ = ["ConvergenceWidget"]

MARGIN = QtCore.QMargins(64, 16, 16, 40)
"""Room for the decade labels on the left and the rung labels underneath."""

_COLOURS: dict[Series, QtGui.QColor] = {
    RESIDUAL: QtGui.QColor(31, 78, 140),
    UPDATE: QtGui.QColor(176, 84, 20),
}
"""One colour per series. Chosen to differ in lightness as well as in hue, so
the two curves stay distinguishable in a greyscale screenshot of a bug report."""

_SILENT = QtGui.QColor(246, 246, 246)
"""Fill of a band that reported no Newton step. Shaded rather than left blank:
an unshaded gap reads as missing data, and the band's note says which of the two
reasons applies."""


class ConvergencePlot(QtWidgets.QWidget):
    """The plotting surface itself: axes, bands and two polylines."""

    def __init__(self, model: ConvergenceModel, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self.setMinimumHeight(260)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )

    def set_model(self, model: ConvergenceModel) -> None:
        """Point the plot at another model and redraw."""
        self._model = model
        self.update()

    def _frame(self) -> QtCore.QRect:
        """Return the rectangle the curves are drawn inside."""
        return self.rect().marginsRemoved(MARGIN)

    def _map(self, frame: QtCore.QRect, x: float, y: float) -> QtCore.QPointF:
        """Map one model coordinate onto a pixel inside ``frame``.

        ``y`` is already a base-10 logarithm when it comes from
        :meth:`~nanopnp.gui.convergence.ConvergenceModel.points`; this only
        flips it, because a smaller residual is a better one and screens count
        downwards.
        """
        x_low, x_high = self._model.x_range
        y_low, y_high = self._model.y_range
        across = (x - x_low) / (x_high - x_low) if x_high > x_low else 0.0
        up = (y - y_low) / (y_high - y_low) if y_high > y_low else 0.5
        return QtCore.QPointF(
            frame.left() + across * frame.width(), frame.bottom() - up * frame.height()
        )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Draw the axes, the bands and the two series."""
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().base())
        frame = self._frame()
        if frame.width() <= 0 or frame.height() <= 0:
            painter.end()
            return
        self._paint_axes(painter, frame)
        self._paint_bands(painter, frame)
        for series in (RESIDUAL, UPDATE):
            self._paint_series(painter, frame, series)
        painter.end()

    def _paint_axes(self, painter: QtGui.QPainter, frame: QtCore.QRect) -> None:
        """Draw the decade ticks and their labels, and the frame."""
        pen = QtGui.QPen(self.palette().mid().color())
        painter.setPen(pen)
        painter.drawRect(frame)
        metrics = painter.fontMetrics()
        for decade in self._model.ticks():
            point = self._map(frame, self._model.x_range[0], decade)
            painter.setPen(QtGui.QPen(self.palette().alternateBase().color()))
            painter.drawLine(frame.left(), int(point.y()), frame.right(), int(point.y()))
            painter.setPen(pen)
            label = f"1e{int(decade)}"
            painter.drawText(
                frame.left() - metrics.horizontalAdvance(label) - 6,
                int(point.y()) + metrics.ascent() // 2,
                label,
            )

    def _paint_bands(self, painter: QtGui.QPainter, frame: QtCore.QRect) -> None:
        """Shade and label one region per continuation rung."""
        metrics = painter.fontMetrics()
        for band in self._model.bands:
            start, end = self._model.extent(band)
            left = self._map(frame, start, 0.0).x()
            right = self._map(frame, end, 0.0).x()
            region = QtCore.QRectF(left, float(frame.top()), right - left, float(frame.height()))
            if not band.steps:
                painter.fillRect(region, _SILENT)
            painter.setPen(QtGui.QPen(self.palette().mid().color(), 1, QtCore.Qt.PenStyle.DotLine))
            painter.drawLine(
                QtCore.QPointF(right, float(frame.top())),
                QtCore.QPointF(right, float(frame.bottom())),
            )
            painter.setPen(QtGui.QPen(self.palette().text().color()))
            label = metrics.elidedText(
                band.name, QtCore.Qt.TextElideMode.ElideRight, max(int(right - left) - 4, 8)
            )
            painter.drawText(
                QtCore.QPointF(left + 2, frame.bottom() + metrics.height() + 2.0), label
            )

    def _paint_series(self, painter: QtGui.QPainter, frame: QtCore.QRect, series: Series) -> None:
        """Stroke one series, one polyline per band.

        One polyline *per band* and never one across the ladder: a segment
        joining the last step of one rung to the first of the next would draw a
        line between two different operators.
        """
        painter.setPen(QtGui.QPen(_COLOURS[series], 2))
        for band in self._model.bands:
            points = [self._map(frame, x, y) for x, y in self._model.points(band, series)]
            if len(points) > 1:
                painter.drawPolyline(QtGui.QPolygonF(points))
            for point in points:
                painter.drawEllipse(point, 2.0, 2.0)


class ConvergenceWidget(QtWidgets.QWidget):
    """The convergence panel: a summary line, the plot, and the bands' notes."""

    def __init__(self, model: ConvergenceModel, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._summary = QtWidgets.QLabel()
        self._summary.setWordWrap(True)
        self._plot = ConvergencePlot(model)
        self._legend = QtWidgets.QLabel(
            "blue: residual after the step; orange: relative update on the undamped direction. "
            "No threshold is drawn: NUM-16 accepts either test, per rung."
        )
        self._legend.setWordWrap(True)
        self._notes = QtWidgets.QPlainTextEdit()
        self._notes.setReadOnly(True)
        self._notes.setMaximumHeight(140)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._summary)
        layout.addWidget(self._plot, 1)
        layout.addWidget(self._legend)
        layout.addWidget(self._notes)
        self.refresh()

    def set_model(self, model: ConvergenceModel) -> None:
        """Point the panel at another run's model."""
        self._model = model
        self._plot.set_model(model)
        self.refresh()

    def refresh(self) -> ConvergenceModel:
        """Redraw from the model and return it, so a test needs no timer."""
        self._summary.setText(self._model.summary)
        self._notes.setPlainText(self.notes_text())
        self._plot.update()
        return self._model

    def notes_text(self) -> str:
        """Return the per-band notes the panel is showing."""
        return "\n".join(
            f"{band.index + 1}. {band.name} (stage {band.stage}): {band.note()}"
            for band in self._model.bands
        )

    @property
    def model(self) -> ConvergenceModel:
        """The view-model this panel draws."""
        return self._model

    def band_at(self, index: int) -> Band:
        """Return one band, for a test."""
        return self._model.bands[index]

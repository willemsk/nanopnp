"""The live convergence panel: two hand-stroked polylines, banded by rung."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from nanopnp.gui.convergence import RESIDUAL, UPDATE, ConvergenceModel, Series

__all__ = ["ConvergenceWidget"]

MARGIN = QtCore.QMargins(64, 16, 16, 40)

# Chosen to differ in lightness as well as hue, so the curves stay distinct in greyscale.
_COLOURS: dict[Series, QtGui.QColor] = {
    RESIDUAL: QtGui.QColor(31, 78, 140),
    UPDATE: QtGui.QColor(176, 84, 20),
}


class ConvergencePlot(QtWidgets.QWidget):
    def __init__(self, model: ConvergenceModel, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        # Axis ranges read once per paint: they are whole-model scans, and reading them per point
        # makes a repaint quadratic in the Newton steps. Set in paintEvent before anything is
        # mapped.
        self._x = (0.0, 1.0)
        self._y = (-1.0, 1.0)
        self.setMinimumHeight(260)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )

    def _silent(self) -> QtGui.QColor:
        return QtGui.QColor(self.palette().window().color())

    def set_model(self, model: ConvergenceModel) -> None:
        self._model = model
        self.update()

    def _frame(self) -> QtCore.QRect:
        return self.rect().marginsRemoved(MARGIN)

    def _map(self, frame: QtCore.QRect, x: float, y: float) -> QtCore.QPointF:
        x_low, x_high = self._x
        y_low, y_high = self._y
        across = (x - x_low) / (x_high - x_low) if x_high > x_low else 0.0
        up = (y - y_low) / (y_high - y_low) if y_high > y_low else 0.5
        return QtCore.QPointF(
            frame.left() + across * frame.width(), frame.bottom() - up * frame.height()
        )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().base())
        frame = self._frame()
        if frame.width() <= 0 or frame.height() <= 0:
            painter.end()
            return
        self._x = self._model.x_range
        self._y = self._model.y_range
        self._paint_axes(painter, frame)
        self._paint_bands(painter, frame)
        for series in (RESIDUAL, UPDATE):
            self._paint_series(painter, frame, series)
        painter.end()

    def _paint_axes(self, painter: QtGui.QPainter, frame: QtCore.QRect) -> None:
        pen = QtGui.QPen(self.palette().mid().color())
        painter.setPen(pen)
        painter.drawRect(frame)
        metrics = painter.fontMetrics()
        for decade in self._model.ticks():
            point = self._map(frame, self._x[0], decade)
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
        metrics = painter.fontMetrics()
        silent = self._silent()
        # Offsets accumulated as the bands are walked: asking the model per band would be a linear
        # scan each.
        start = self._x[0]
        for band in self._model.bands:
            end = start + band.width
            left = self._map(frame, start, 0.0).x()
            right = self._map(frame, end, 0.0).x()
            start = end
            region = QtCore.QRectF(left, float(frame.top()), right - left, float(frame.height()))
            if not band.steps:
                painter.fillRect(region, silent)
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
        painter.setPen(QtGui.QPen(_COLOURS[series], 2))
        for band in self._model.bands:
            points = [self._map(frame, x, y) for x, y in self._model.points(band, series)]
            if len(points) > 1:
                painter.drawPolyline(QtGui.QPolygonF(points))
            for point in points:
                painter.drawEllipse(point, 2.0, 2.0)


class ConvergenceWidget(QtWidgets.QWidget):
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
        self._model = model
        self._plot.set_model(model)
        self.refresh()

    def refresh(self) -> ConvergenceModel:
        summary = self._model.summary
        if summary != self._summary.text():
            self._summary.setText(summary)
        notes = self.notes_text()
        if notes != self._notes.toPlainText():
            self._notes.setPlainText(notes)
        self._plot.update()
        return self._model

    def notes_text(self) -> str:
        return "\n".join(
            f"{band.index + 1}. {band.name} (stage {band.stage}): {band.note()}"
            for band in self._model.bands
        )

    @property
    def model(self) -> ConvergenceModel:
        return self._model

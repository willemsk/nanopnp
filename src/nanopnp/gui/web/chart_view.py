"""A chart's host in a page, and under it a field per axis for its scale and range."""

from __future__ import annotations

import json
import math
from dataclasses import replace

from nicegui import ui
from nicegui.awaitable_response import AwaitableResponse

from nanopnp.gui.web.chart import SCALES, Axis, Chart, Panel, Scale

__all__ = ["SCALE_NAMES", "ChartView"]

SCALE_NAMES: dict[Scale, str] = {"linear": "Linear", "log": "Logarithmic", "sqrt": "Square root"}
"""Each axis scale as its field names it."""

_Set = tuple[Scale, tuple[float, float] | None]


class ChartView:
    """A chart's host and its axis fields; what the user sets holds across the chart's updates.

    Parameters
    ----------
    host_id
        The id of the element ``nano.chart`` draws into.
    control
        The host's ``data-control`` name; the fold of its fields is ``<control>-axes``, and each
        field's ``<control>-<panel>-<axis>-<part>``.
    marks
        Whether a drawing marks the screen ready, as the frame's view does.
    """

    def __init__(
        self, host_id: str, control: str, *, classes: str = "", marks: bool = False
    ) -> None:
        self.host_id = host_id
        self.control = control
        self.marks = marks
        self.chart: Chart | None = None
        self.set: dict[tuple[int, str], _Set] = {}
        self.shape: tuple[tuple[str, str], ...] = ()
        with ui.element("div").classes(f"chart-view {classes}".strip()) as self.element:
            self.host = ui.element("div").props(f"id={host_id} data-control={control} role=figure")
            # Folded until asked for, so that the chart keeps the height.
            with (
                ui.expansion("Axes", value=False)
                .classes("chart-axes-fold")
                .props(f"dense data-control={control}-axes")
            ):
                self.axes = ui.element("div").classes("chart-axes")

    def show(self, chart: Chart) -> AwaitableResponse:
        """Draw a chart with the axes the user set; its fields are built again for other axes."""
        self.chart = chart
        shape = tuple((panel.x.label, panel.y.label) for panel in chart.panels)
        if shape != self.shape:
            self.shape = shape
            self.set = {}
            self._fields(chart)
        return self._draw()

    def shown(self, chart: Chart) -> Chart:
        """Return the chart with each axis the user set in place of its own.

        A scale changed without a typed range fits the samples, as the chart's own range may not
        stand on it; a typed range is the user's. Ticks are the chart's only on its own axis.
        """
        panels: list[Panel] = []
        for index, panel in enumerate(chart.panels):
            axes: list[Axis] = []
            for name, axis in (("x", panel.x), ("y", panel.y)):
                if (index, name) in self.set:
                    scale, typed = self.set[(index, name)]
                    own = scale == axis.scale
                    axis = replace(
                        axis,
                        scale=scale,
                        range=typed if typed is not None else axis.range if own else None,
                        ticks=axis.ticks if own and typed is None else (),
                    )
                axes.append(axis)
            panels.append(Panel(axes[0], axes[1]))
        return replace(chart, panels=tuple(panels))

    def _draw(self) -> AwaitableResponse:
        assert self.chart is not None
        spec = json.dumps(self.shown(self.chart).json())
        return ui.run_javascript(
            f"nano.chart({json.dumps(self.host_id)}, {spec}, {json.dumps(self.marks)})",
            timeout=60,
        )

    def _fields(self, chart: Chart) -> None:
        self.axes.clear()
        with self.axes:
            for index, panel in enumerate(chart.panels):
                for name, axis in (("x", panel.x), ("y", panel.y)):
                    self._axis_fields(index, name, axis)
            ui.button("Reset axes", on_click=self._reset).props(
                f"flat dense no-caps data-control={self.control}-reset"
            )

    def _axis_fields(self, index: int, name: str, axis: Axis) -> None:
        stem = f"{self.control}-{index}-{name}"
        # The axis named as the chart labels it; its scale and range as the user types them.
        with ui.element("div").classes("chart-axis").props(f'role=group aria-label="{axis.label}"'):
            ui.label(axis.label).classes("chart-axis-name")
            scale = ui.select(
                {key: SCALE_NAMES[key] for key in SCALES}, value=axis.scale, label="Scale"
            ).props(f"dense options-dense data-control={stem}-scale")
            low = ui.number(label="From", placeholder="fit").props(
                f"dense debounce=600 data-control={stem}-from"
            )
            high = ui.number(label="To", placeholder="fit").props(
                f"dense debounce=600 data-control={stem}-to"
            )
            hint = ui.label("").classes("field-hint chart-axis-hint")

        def changed() -> None:
            chosen: Scale = scale.value if scale.value in SCALES else axis.scale
            typed, problem = _typed(low.value, high.value, chosen)
            hint.text = problem
            self.set[(index, name)] = (chosen, typed)
            if self.chart is not None:
                self._draw()

        scale.on_value_change(changed)
        low.on_value_change(changed)
        high.on_value_change(changed)

    def _reset(self) -> None:
        if self.chart is None:
            return
        self.shape = ()
        self.show(self.chart)


def _typed(
    low: float | None, high: float | None, scale: Scale
) -> tuple[tuple[float, float] | None, str]:
    # A range is typed once both ends are; one end alone fits the samples.
    if low is None or high is None:
        return None, ""
    low, high = float(low), float(high)
    if not (math.isfinite(low) and math.isfinite(high)) or low >= high:
        return None, "From must be below To; the axis fits the samples until it is."
    if scale == "log" and low <= 0.0:
        return None, "A logarithmic axis starts above 0; the axis fits the samples until it does."
    return (low, high), ""

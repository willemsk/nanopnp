"""A plot of y against x as the vendored chart library draws it: panels, series, bands and rules."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

__all__ = [
    "SCALES",
    "Axis",
    "Band",
    "Chart",
    "Panel",
    "Rule",
    "Scale",
    "Series",
    "placeable",
]

Scale: TypeAlias = Literal["linear", "log", "sqrt"]

SCALES: tuple[Scale, ...] = ("linear", "log", "sqrt")
"""The scales an axis takes, as its control offers them."""


def placeable(value: float | None, scale: Scale) -> bool:
    """Return whether an axis of ``scale`` places ``value``: finite, and positive if logarithmic."""
    if value is None or not math.isfinite(value):
        return False
    return value > 0.0 or scale != "log"


@dataclass(frozen=True)
class Axis:
    """One axis of a panel.

    Parameters
    ----------
    range
        The ``(low, high)`` the axis opens on, in its values; None fits the data.
    ticks
        The values ticked, in place of the chart's own choice; kept only while the axis keeps
        its scale and range.
    """

    label: str
    scale: Scale = "linear"
    range: tuple[float, float] | None = None
    ticks: tuple[float, ...] = ()

    def json(self) -> dict[str, Any]:
        """Return the axis as the chart reads it."""
        return {
            "label": self.label,
            "scale": self.scale,
            "range": None if self.range is None else list(self.range),
            "ticks": list(self.ticks),
        }


@dataclass(frozen=True)
class Panel:
    """One graph of a chart; a chart's panels stand one above the other."""

    x: Axis
    y: Axis

    def json(self) -> dict[str, Any]:
        """Return the panel's two axes."""
        return {"x": self.x.json(), "y": self.y.json()}


@dataclass(frozen=True)
class Series:
    """One curve: its samples, and a None where it breaks.

    Parameters
    ----------
    y
        One value per ``x``; None is a gap the curve is not drawn across.
    marks
        Whether each sample is drawn as a point as well as joined.
    """

    id: str
    label: str
    x: tuple[float, ...]
    y: tuple[float | None, ...]
    colour: str
    dash: tuple[float, ...] = ()
    marks: bool = False
    panel: int = 0

    def __post_init__(self) -> None:
        if len(self.x) != len(self.y):
            raise ValueError(
                f"series {self.id!r} has {len(self.x)} x values and {len(self.y)} y values; a "
                "series takes one y per x"
            )

    def json(self) -> dict[str, Any]:
        """Return the series with each sample that is not a finite number as None."""
        return {
            "id": self.id,
            "label": self.label,
            "x": list(self.x),
            "y": [
                value if value is not None and math.isfinite(value) else None for value in self.y
            ],
            "colour": self.colour,
            "dash": list(self.dash),
            "marks": self.marks,
            "panel": self.panel,
        }


@dataclass(frozen=True)
class Band:
    """A span of x shaded behind a panel's curves, as a rung of the ladder or a fitted range.

    Parameters
    ----------
    label
        Written inside the band, at its top; ``short`` where the label does not fit.
    note
        Written under the label, as what a band without curves holds.
    title
        The band's row in the chart's key; a band labelled inside needs none.
    """

    id: str
    x: tuple[float, float]
    label: str = ""
    short: str = ""
    note: str = ""
    title: str = ""
    shaded: bool = True
    panel: int = 0

    def json(self) -> dict[str, Any]:
        """Return the band as the chart's draw hook reads it."""
        return {
            "id": self.id,
            "x": list(self.x),
            "label": self.label,
            "short": self.short,
            "note": self.note,
            "title": self.title,
            "shaded": self.shaded,
            "panel": self.panel,
        }


@dataclass(frozen=True)
class Rule:
    """A dashed vertical line at one x, keyed by its title, as an operating value."""

    id: str
    x: float
    title: str
    panel: int = 0

    def json(self) -> dict[str, Any]:
        """Return the rule."""
        return {"id": self.id, "x": self.x, "title": self.title, "panel": self.panel}


@dataclass(frozen=True)
class Chart:
    """A chart of one or more panels, each axis linear, logarithmic or square-root.

    Parameters
    ----------
    notes
        What is not drawn, and why, said under the chart.
    label
        What the chart shows, for a reader that cannot see it.
    """

    panels: tuple[Panel, ...]
    series: tuple[Series, ...] = ()
    bands: tuple[Band, ...] = ()
    rules: tuple[Rule, ...] = ()
    notes: tuple[str, ...] = ()
    label: str = ""

    def __post_init__(self) -> None:
        if not self.panels:
            raise ValueError("a chart has at least one panel")
        named = [
            *(series.panel for series in self.series),
            *(band.panel for band in self.bands),
            *(rule.panel for rule in self.rules),
        ]
        outside = sorted(set(named) - set(range(len(self.panels))))
        if outside:
            raise ValueError(
                f"the chart has {len(self.panels)} panel(s) and an item names panel(s) "
                f"{', '.join(map(str, outside))}"
            )

    def omitted(self) -> int:
        """Count the finite samples a logarithmic axis of their panel cannot place."""
        count = 0
        for series in self.series:
            panel = self.panels[series.panel]
            for x, y in zip(series.x, series.y, strict=True):
                if y is None or not math.isfinite(y) or not math.isfinite(x):
                    continue
                if not (placeable(x, panel.x.scale) and placeable(y, panel.y.scale)):
                    count += 1
        return count

    def json(self) -> dict[str, Any]:
        """Return the chart as ``chart.js`` reads it, which counts again on a change of scale."""
        return {
            "panels": [panel.json() for panel in self.panels],
            "series": [series.json() for series in self.series],
            "bands": [band.json() for band in self.bands],
            "rules": [rule.json() for rule in self.rules],
            "notes": list(self.notes),
            "omitted": self.omitted(),
            "label": self.label,
        }

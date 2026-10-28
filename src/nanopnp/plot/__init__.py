"""Figures of the pipeline's artefacts, drawn from the stored results alone."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from nanopnp.core.stages import draw

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from matplotlib.figure import Figure

    from nanopnp.io.artefact import Artefact, StageInputs
    from nanopnp.plot.panels import plot_axial_cutline as plot_axial_cutline
    from nanopnp.plot.panels import plot_field as plot_field
    from nanopnp.plot.panels import plot_iv as plot_iv
    from nanopnp.plot.panels import plot_mesh as plot_mesh
    from nanopnp.plot.panels import plot_radial_cutline as plot_radial_cutline

__all__ = [
    "figure",
    "plot_axial_cutline",
    "plot_field",
    "plot_iv",
    "plot_mesh",
    "plot_radial_cutline",
]

_PANELS = frozenset(__all__) - {"figure"}


def __getattr__(name: str) -> object:
    if name not in _PANELS:
        raise AttributeError(f"module 'nanopnp.plot' has no attribute {name!r}")
    value = getattr(importlib.import_module("nanopnp.plot.panels"), name)
    globals()[name] = value
    return value


def figure(artefact: Artefact, *, inputs: StageInputs | None = None, scale: float = 1.0) -> Figure:
    """Return the figure of ``artefact``; ``inputs`` adds what the artefact alone cannot show.

    ``scale`` multiplies the figure's width and height.

    Raises
    ------
    MissingExtraError
        Matplotlib is not installed.
    """
    drawn = draw(artefact, inputs, scale=scale)
    if drawn is None:
        from nanopnp.plot.figures import text_figure

        return text_figure(f"{artefact.schema} has no figure")
    return drawn

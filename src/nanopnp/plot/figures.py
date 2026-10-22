"""One figure per stage artefact, and the sweep's, each built without pyplot."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from matplotlib.figure import Figure

    from nanopnp.io.artefact import Artefact, StageInputs


def text_figure(message: str) -> Figure:
    """Return a figure holding only ``message``, for an artefact with nothing to draw."""
    from matplotlib.figure import Figure

    figure = Figure(figsize=(6.0, 1.6))
    figure.text(0.5, 0.5, message, ha="center", va="center", wrap=True)
    return figure


def _pending(artefact: Artefact) -> Figure:
    return text_figure(f"{artefact.schema}: no figure yet")


def structure_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 1."""
    return _pending(artefact)


def density_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 2."""
    return _pending(artefact)


def symmetry_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 3."""
    return _pending(artefact)


def contour_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 4."""
    return _pending(artefact)


def region_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 5."""
    return _pending(artefact)


def mesh_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 6."""
    return _pending(artefact)


def protonation_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 7's protonation."""
    return _pending(artefact)


def charge_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 7's fields."""
    return _pending(artefact)


def materials_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 8."""
    return _pending(artefact)


def solve_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 10."""
    return _pending(artefact)


def qoi_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 11."""
    return _pending(artefact)


def sweep_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw a sweep's dataset."""
    return _pending(artefact)

"""Figures of the pipeline's artefacts, drawn from the stored results alone."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nanopnp.core.stages import draw

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from matplotlib.figure import Figure

    from nanopnp.io.artefact import Artefact, StageInputs

__all__ = ["figure"]


def figure(artefact: Artefact, *, inputs: StageInputs | None = None) -> Figure:
    """Return the figure of ``artefact``; ``inputs`` adds what the artefact alone cannot show.

    Raises
    ------
    MissingExtraError
        Matplotlib is not installed.
    """
    drawn = draw(artefact, inputs)
    if drawn is None:
        from nanopnp.plot.figures import text_figure

        return text_figure(f"{artefact.schema} has no figure")
    return drawn

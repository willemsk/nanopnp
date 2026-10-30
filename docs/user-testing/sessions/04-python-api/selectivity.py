"""A stage of one's own: which ion carries most of the current, from the quantities of interest."""

from __future__ import annotations

from nanopnp import Artefact


def selectivity(qoi: Artefact) -> dict[str, object]:
    """Read the cation's transport number and name the ion that carries more than half."""
    recorded = qoi.summary["transport_number"]
    t_plus = None if recorded is None else float(recorded)
    if t_plus is None:
        # At zero bias the extraction reports no transport number: there is no current to share.
        verdict = "undefined"
    elif t_plus > 0.5:
        verdict = "cations"
    elif t_plus < 0.5:
        verdict = "anions"
    else:
        verdict = "neither"
    return {"transport_number": t_plus, "verdict": verdict}

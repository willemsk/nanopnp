"""A stage of one's own: which ion carries most of the current, from the quantities of interest."""

from __future__ import annotations

from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import Artefact, StageInputs

SCHEMA = "nanopnp/selectivity-notebook/v1"


class SelectivityStage:
    """Stage 13 of the notebook: which ion carries the larger share of the current."""

    name = "selectivity"

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> Artefact:
        """Return the artefact this stage will produce: its key is the quantities it reads."""
        quantities = inputs.require("qoi")
        return Artefact(SCHEMA, parameters={}, inputs={"qoi": quantities.hash})

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> Artefact:
        """Read the cation's transport number and name the ion that carries more than half."""
        check_cancelled(cancel, "the selectivity verdict")
        report(progress, 0.0, "reading the transport number")
        quantities = inputs.require("qoi")
        recorded = quantities.summary["transport_number"]
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
        report(progress, 1.0, f"the majority carrier: {verdict}")
        return Artefact(
            SCHEMA,
            parameters={},
            inputs={"qoi": quantities.hash},
            summary={"transport_number": t_plus, "verdict": verdict},
        )

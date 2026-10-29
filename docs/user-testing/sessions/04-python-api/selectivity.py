"""A stage of one's own: which ion the pore passes, read from the quantities of interest."""

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
    """Stage 13 of the notebook: whether the pore favours cations, anions or neither."""

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
        """Read the cation's transport number and say which ion the pore passes."""
        check_cancelled(cancel, "the selectivity verdict")
        report(progress, 0.0, "reading the transport number")
        quantities = inputs.require("qoi")
        t_plus = float(quantities.summary["transport_number"])
        verdict = "cation" if t_plus > 0.5 else "anion"
        report(progress, 1.0, f"the pore passes the {verdict}")
        return Artefact(
            SCHEMA,
            parameters={},
            inputs={"qoi": quantities.hash},
            summary={"transport_number": t_plus, "verdict": verdict},
        )

"""Stage 8 of section 5.2: the resolved material coefficient set (IF-01, FR-27).

The work is :func:`nanopnp.io.case.resolve`'s already — the electrolyte, its
species and every correction switch come out of the case. What this stage adds is
the artefact: a content hash over the electrolyte's provenance *and* over the
digest of the ``data/corrections/*.yaml`` it resolved through, so that editing a
parameter file is a cache miss rather than a silent change of physics (FR-16,
section 5.3.2).

Nothing here imports NGSolve. The coefficient set is symbolic only once a mesh
exists, and stage 10 is where that happens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nanopnp.core.hashing import file_hash
from nanopnp.core.paths import correction_file
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import MaterialsArtefact
from nanopnp.io.case import resolve

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.artefact import StageInputs


class MaterialsStage:
    """Stage 8: electrolyte specification to a resolved, hashed coefficient set."""

    name = "materials"

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> MaterialsArtefact:
        """Resolve the electrolyte and emit the stage-8 artefact.

        Parameters
        ----------
        inputs
            Carries the case; this stage consumes no upstream artefact.
        progress
            Called with a fraction in [0, 1] and a message.
        cancel
            Checked on entry. Resolution reads one YAML file and evaluates no
            fit, so there is nothing longer-running to interrupt.

        Returns
        -------
        MaterialsArtefact
            Hashed over the electrolyte's provenance, the reference
            concentration, and the digest of the correction file.

        Raises
        ------
        Cancelled
            If ``cancel`` is already set.
        """
        check_cancelled(cancel, "materials")
        report(progress, 0.0, "resolving the electrolyte")
        resolved = resolve(inputs.case)
        electrolyte = resolved.electrolyte
        parameter_file = electrolyte.parameter_file
        # The correction file's content hash is its version (FR-25): the
        # documents carry no version field, and a hash cannot be forgotten.
        digest = file_hash(correction_file(parameter_file)) if parameter_file else ""
        report(progress, 1.0, f"electrolyte resolved from {parameter_file!r}")
        return MaterialsArtefact(
            electrolyte,
            concentration_M=resolved.concentration_M,
            correction_file_hash=digest,
            summary={
                "species": [ion.name for ion in electrolyte.species],
                "concentration_M": resolved.concentration_M,
                "temperature_K": resolved.temperature_K,
                "parameter_file": parameter_file,
                "corrections": {
                    key: model.name for key, model in sorted(electrolyte.corrections.items())
                },
                "steric": electrolyte.switches.steric,
            },
        )

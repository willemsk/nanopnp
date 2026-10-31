"""Stage 8 of section 5.2: the resolved material coefficient set (IF-01, FR-27)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nanopnp.core.hashing import file_hash
from nanopnp.core.paths import correction_identity, correction_source, reads_a_file
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import MaterialsArtefact

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.artefact import StageInputs


class MaterialsStage:
    """Stage 8: electrolyte specification to a resolved, hashed coefficient set."""

    name = "materials"

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> MaterialsArtefact:
        """Resolve the electrolyte and emit the stage-8 artefact; Cancelled if already cancelled."""
        check_cancelled(cancel, "materials")
        report(progress, 0.0, "resolving the electrolyte")
        artefact = self.key(inputs)
        report(progress, 1.0, f"electrolyte resolved from {artefact.summary['parameter_file']!r}")
        return artefact

    def key(self, inputs: StageInputs) -> MaterialsArtefact:
        """Return the stage-8 artefact, which is its own key."""
        resolved = inputs.resolved
        electrolyte = resolved.electrolyte
        parameter_file = electrolyte.parameter_file
        # the documents carry no version field, so the content hash is the version
        digest = file_hash(correction_source(parameter_file)) if parameter_file else ""
        # a model may name a file other than the reference one; it is an input too
        named = {model.name for model in electrolyte.corrections.values()}
        read = {name for name in named if reads_a_file(name)} - {parameter_file}
        others: dict[str, str] = {}
        for name in sorted(read):
            # By identity, so the same two files beside two copies of one case key one artefact.
            identity = correction_identity(name)
            if identity in others:
                raise ValueError(
                    f"this case names two correction files called {identity!r} by different "
                    "paths, which the materials key cannot tell apart; give them distinct file "
                    "names, or install them and name them without a path (FR-16, QR-12)"
                )
            others[identity] = file_hash(correction_source(name))
        return MaterialsArtefact(
            electrolyte,
            concentration_M=resolved.concentration_M,
            correction_file_hash=digest,
            other_correction_file_hashes=others,
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

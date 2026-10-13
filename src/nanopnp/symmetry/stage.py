"""Stage 3 of section 5.2: symmetry reduction to (r, z)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.io.artefact import ReducedArtefact
from nanopnp.io.case import UnsupportedCaseSection
from nanopnp.symmetry.reduce import DETREND, HARMONICS, PAYLOAD_NAME, reduce_map

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.artefact import StageInputs

logger = logging.getLogger(__name__)

WORKSPACE_DIRNAME = "tmp"


def reduction_parameters(inputs: StageInputs) -> dict[str, Canonicalisable]:
    """Return the stage-3 key's parameters, or refuse a case without ``structure:``."""
    resolved = inputs.resolved
    if resolved.structure is None or resolved.density is None:
        raise UnsupportedCaseSection(
            f"case {inputs.resolved.name!r} carries no structure: section, so stage 3 has no point "
            "group to reduce by"
        )
    return {
        "n": resolved.structure.n,
        "bin_width_nm": resolved.density.grid_spacing_nm,
        "detrend": DETREND,
        "harmonics": HARMONICS,
    }


class SymmetryStage:
    """Stage 3: a density map to its (r, z) mean and azimuthal variances."""

    name = "symmetry"

    def __init__(self, *, workspace: Path | None = None) -> None:
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> ReducedArtefact:
        """Return the artefact key from n, the bin width, the methods and stage 2's hash."""
        return ReducedArtefact(
            parameters=reduction_parameters(inputs),
            inputs={"density": inputs.require("density").hash},
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> ReducedArtefact:
        """Reduce the map and emit the stage-3 artefact.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true.
        """
        parameters = reduction_parameters(inputs)
        density = inputs.require("density")
        check_cancelled(cancel, "reading the density map")
        report(progress, 0.0, "reading the density map")
        source = DensityMap.read(density.payload[DENSITY_PAYLOAD])
        n = int(parameters["n"])
        reduced = reduce_map(source, n, progress=progress, cancel=cancel)
        maximum = reduced.header["maximum"]
        logger.info("reduction: C%d over %d bins; maxima %s", n, len(reduced.r_nm), maximum)
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="symmetry-", dir=root))
        path = reduced.write(directory / f"{PAYLOAD_NAME}.npz")
        report(progress, 1.0, "reduction written")
        return ReducedArtefact(
            parameters=parameters,
            inputs={"density": density.hash},
            payload={PAYLOAD_NAME: path},
            summary={**reduced.header, "payload_digest": reduced.digest()},
        )

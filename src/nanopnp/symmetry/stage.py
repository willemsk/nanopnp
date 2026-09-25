"""Stage 3 of section 5.2: symmetry reduction to (r, z) (FR-05, FR-06, CON-04).

The stage reads stage 2's map and reduces it over exact cell-annulus overlaps to
the azimuthal mean, the Cₙ-averaged variance and the raw variance, all on the
``RadialGrid`` axes stage 4 reads (WP19 D7-D10). Its contract is the section 5.3.1
NOTE on ``geometry.density``.

**The key is n, the bin width, the two method names and stage 2's hash** (D11). The
detrending rule and the harmonic truncation are named in it because each moves a
variance. The payload's digest is recorded in the summary and re-checked on load
(VER-23).
"""

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
from nanopnp.io.case import UnsupportedCaseSection, resolve
from nanopnp.symmetry.reduce import DETREND, HARMONICS, PAYLOAD_NAME, reduce_map

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.artefact import StageInputs

logger = logging.getLogger(__name__)

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to when no workspace is given."""


def reduction_parameters(inputs: StageInputs) -> dict[str, Canonicalisable]:
    """Return the stage-3 key's parameters (WP19 D11), or refuse a case without ``structure:``."""
    resolved = resolve(inputs.case)
    if resolved.structure is None or resolved.density is None:
        raise UnsupportedCaseSection(
            f"case {inputs.case.name!r} carries no structure: section, so stage 3 has no point "
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
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory the ``.npz`` payload is written to before the store copies it
            in. Defaults to a fresh directory under the store root.
        """
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
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
            If ``cancel`` turns true. No artefact is written.
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

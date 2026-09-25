"""Stage 2 of section 5.2: the density map (FR-04, IF-05).

The stage reads stage 1's aligned ensemble, gives every atom its CHARMM radius
(WP19 D3), and deposits the ensemble mean of the per-frame union densities on the
canonical grid (D4-D6). Its contract is the section 5.3.1 NOTE on
``geometry.density``; the decisions are the WP19 plan's.

**The key is ``geometry.density``, the radius set and stage 1's hash** (D11): the
block, the set's name and the digest of its shipped file, and ε and the
logarithm's floor, which are constants of the code that move a number. Nothing
about the result enters it. The payload's digest is recorded in the summary and
re-checked on load (VER-23).
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
from nanopnp.density.map import PAYLOAD_NAME, DensityMap
from nanopnp.density.radii import KERNEL_RADII, radius_set_digest, resolve_radii
from nanopnp.density.union import (
    EPSILON,
    LOG_FLOOR,
    canonical_grid,
    check_positions,
    deposit,
)
from nanopnp.io.artefact import DensityArtefact
from nanopnp.io.case import DensitySpec, UnsupportedCaseSection, resolve
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.artefact import StageInputs

logger = logging.getLogger(__name__)

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to when no workspace is given."""


def _density(inputs: StageInputs) -> DensitySpec:
    """Return the case's resolved ``geometry.density``, or refuse a case without ``structure:``."""
    resolved = resolve(inputs.case)
    if resolved.density is None:
        raise UnsupportedCaseSection(
            f"case {inputs.case.name!r} carries no structure: section, so stage 2 has no "
            "ensemble to deposit"
        )
    return resolved.density


def density_parameters(spec: DensitySpec) -> dict[str, Canonicalisable]:
    """Return the stage-2 key's parameters (WP19 D11)."""
    name = KERNEL_RADII[spec.kernel]
    return {
        "density": spec.model_dump(mode="json"),
        "radius_set": {"name": name, "sha256": radius_set_digest(name)},
        "epsilon": EPSILON,
        "log_floor": LOG_FLOOR,
    }


class DensityStage:
    """Stage 2: an aligned ensemble to its ensemble-mean union density on a canonical grid."""

    name = "density"

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

    def key(self, inputs: StageInputs) -> DensityArtefact:
        """Return the artefact key from the block, the radius set and stage 1's hash."""
        return DensityArtefact(
            parameters=density_parameters(_density(inputs)),
            inputs={"structure": inputs.require("structure").hash},
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> DensityArtefact:
        """Deposit the density and emit the stage-2 artefact.

        Raises
        ------
        nanopnp.density.radii.DensityInputError
            For an atom the radius set does not resolve, or a non-finite
            coordinate.
        nanopnp.density.union.DensityGateError
            If the map is not finite or leaves [0, 1].
        Cancelled
            If ``cancel`` turns true. No artefact is written.
        """
        import numpy as np

        spec = _density(inputs)
        parameters = density_parameters(spec)
        structure = inputs.require("structure")
        check_cancelled(cancel, "reading the aligned ensemble")
        report(progress, 0.0, "reading the aligned ensemble")
        ensemble = AlignedEnsemble.read(structure.payload[ENSEMBLE_PAYLOAD])
        radii = resolve_radii(
            KERNEL_RADII[spec.kernel],
            resname=ensemble.resname,
            atom=ensemble.name,
            chain=ensemble.chain,
            resid=ensemble.resid,
            icode=ensemble.icode,
        )
        check_positions(ensemble.positions_nm)
        widths = spec.sharpness * radii.radii_nm
        grid = canonical_grid(ensemble.positions_nm, widths, spec.grid_spacing_nm)
        logger.info(
            "density: %d atoms x %d frames on a %s grid (z, y, x) at %.3f nm",
            ensemble.atoms,
            ensemble.frames,
            "x".join(str(size) for size in grid.shape),
            grid.spacing_nm,
        )

        def scaled(fraction: float, message: str) -> None:
            report(progress, 0.05 + 0.9 * fraction, message)

        values = deposit(ensemble.positions_nm, widths, grid, progress=scaled, cancel=cancel)

        elements, counts = np.unique(ensemble.element.astype(str), return_counts=True)
        by_element = {str(e): int(c) for e, c in zip(elements, counts, strict=True)}
        frames = ensemble.header.get("frames")
        header: dict[str, Canonicalisable] = {
            "grid": grid.summary(),
            "kernel": spec.kernel,
            "radius_set": {"name": radii.name, "sha256": radii.sha256},
            "sharpness": spec.sharpness,
            "epsilon": EPSILON,
            "log_floor": LOG_FLOOR,
            "frames": {
                "count": ensemble.frames,
                "indices": frames.get("indices") if isinstance(frames, dict) else None,
            },
            "atoms": {"total": ensemble.atoms, "by_element": by_element},
            "hydrogens": by_element.get("H", 0),
            "radius_range_nm": [float(radii.radii_nm.min()), float(radii.radii_nm.max())],
            "structure_payload_digest": structure.summary.get("payload_digest"),
        }
        density = DensityMap(values=values, grid=grid, header=header)
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="density-", dir=root))
        path = density.write(directory / f"{PAYLOAD_NAME}.npz")
        report(progress, 1.0, f"density on {grid.nz} z planes written")
        return DensityArtefact(
            parameters=parameters,
            inputs={"structure": structure.hash},
            payload={PAYLOAD_NAME: path},
            summary={**header, "payload_digest": density.digest()},
        )

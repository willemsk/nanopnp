"""Stage 2 of section 5.2: the density map (FR-04, IF-05)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.density.map import PAYLOAD_NAME, DensityMap
from nanopnp.density.radii import (
    KERNEL_RADII,
    DensityInputError,
    radius_set_digest,
    resolve_protonated_radii,
    resolve_radii,
)
from nanopnp.density.union import (
    EPSILON,
    LOG_FLOOR,
    Frames,
    Widths,
    canonical_grid,
    check_positions,
    deposit,
)
from nanopnp.io.artefact import DensityArtefact
from nanopnp.io.case import (
    Density,
    UnsupportedCaseSection,
)
from nanopnp.io.workspace import scratch_directory
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.structure.protonated import PAYLOAD_NAME as PROTONATION_PAYLOAD
from nanopnp.structure.protonated import ProtonationTable

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.artefact import StageInputs

logger = logging.getLogger(__name__)


def _density(inputs: StageInputs) -> Density:
    resolved = inputs.resolved
    if resolved.density is None:
        raise UnsupportedCaseSection(
            f"case {inputs.resolved.name!r} carries no structure: section, so stage 2 has no "
            "ensemble to deposit"
        )
    return resolved.density


def density_parameters(spec: Density) -> dict[str, Canonicalisable]:
    """Return the stage-2 key's parameters.

    ``atoms`` enters the key only under ``protonated``.
    """
    name = KERNEL_RADII[spec.kernel]
    block = spec.model_dump(mode="json", exclude={"atoms"})
    parameters: dict[str, Canonicalisable] = {
        "density": block,
        "radius_set": {"name": name, "sha256": radius_set_digest(name)},
        "epsilon": EPSILON,
        "log_floor": LOG_FLOOR,
    }
    if spec.atoms == "protonated":
        parameters["atoms"] = "protonated"
    return parameters


def _upstream(inputs: StageInputs, spec: Density) -> dict[str, str]:
    keyed = {"structure": inputs.require("structure").hash}
    if spec.atoms == "protonated":
        keyed["protonation"] = inputs.require("protonation").hash
    return keyed


class DensityStage:
    """Stage 2: an aligned ensemble to its ensemble-mean union density on a canonical grid."""

    name = "density"

    def __init__(self, *, workspace: Path | None = None, overwrite_workspace: bool = False) -> None:
        self._workspace = Path(workspace) if workspace is not None else None
        self._overwrite = overwrite_workspace

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> DensityArtefact:
        """Return the artefact key from the block, the radius set and stage 1's hash."""
        return DensityArtefact(
            parameters=density_parameters(_density(inputs)),
            inputs=_upstream(inputs, _density(inputs)),
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
        Cancelled
            If ``cancel`` turns true.
        """
        import numpy as np

        spec = _density(inputs)
        parameters = density_parameters(spec)
        structure = inputs.require("structure")
        directory = scratch_directory(self._workspace, self.name, overwrite=self._overwrite)
        check_cancelled(cancel, "reading the aligned ensemble")
        report(progress, 0.0, "reading the aligned ensemble")
        ensemble = AlignedEnsemble.read(structure.payload[ENSEMBLE_PAYLOAD])
        table: ProtonationTable | None = None
        if spec.atoms == "protonated":
            protonation = inputs.require("protonation")
            table = ProtonationTable.read(Path(protonation.payload[PROTONATION_PAYLOAD]))
            if table.frames != ensemble.frames:
                raise DensityInputError(
                    f"the protonation table holds {table.frames} frames and the aligned "
                    f"ensemble {ensemble.frames}, so stage 2 cannot pair them"
                )
            radii = resolve_protonated_radii(KERNEL_RADII[spec.kernel], table)
            positions: Frames = [
                table.positions_nm[table.frame_slice(f)] for f in range(table.frames)
            ]
            widths: Widths = [
                spec.sharpness * radii.radii_nm[table.frame_slice(f)] for f in range(table.frames)
            ]
            first = table.frame_slice(0)
            atom_total = first.stop - first.start
        else:
            radii = resolve_radii(
                KERNEL_RADII[spec.kernel],
                resname=ensemble.resname,
                atom=ensemble.name,
                chain=ensemble.chain,
                resid=ensemble.resid,
                icode=ensemble.icode,
            )
            positions = ensemble.positions_nm
            widths = spec.sharpness * radii.radii_nm
            atom_total = ensemble.atoms
        check_positions(positions)
        grid = canonical_grid(positions, widths, spec.grid_spacing_nm)
        logger.info(
            "density: %d atoms x %d frames on a %s grid (z, y, x) at %.3f nm",
            atom_total,
            ensemble.frames,
            "x".join(str(size) for size in grid.shape),
            grid.spacing_nm,
        )

        def scaled(fraction: float, message: str) -> None:
            report(progress, 0.05 + 0.9 * fraction, message)

        values = deposit(positions, widths, grid, progress=scaled, cancel=cancel)

        # A PDB2PQR atom name carries its element first, as stage 1's element column does.
        symbols = (
            np.array([name.lstrip("0123456789")[:1].upper() for name in table.name[first].tolist()])
            if table is not None
            else ensemble.element.astype(str)
        )
        elements, counts = np.unique(symbols, return_counts=True)
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
            "atoms": {"total": atom_total, "by_element": by_element},
            "hydrogens": by_element.get("H", 0),
            "radius_range_nm": [float(radii.radii_nm.min()), float(radii.radii_nm.max())],
            "structure_payload_digest": structure.summary.get("payload_digest"),
        }
        if table is not None:
            header["atom_source"] = {"atoms": "protonated", "table_digest": table.digest()}
        density = DensityMap(values=values, grid=grid, header=header)
        path = density.write(directory / f"{PAYLOAD_NAME}.npz")
        report(progress, 1.0, f"density on {grid.nz} z planes written")
        return DensityArtefact(
            parameters=parameters,
            inputs=_upstream(inputs, spec),
            payload={PAYLOAD_NAME: path},
            summary={**header, "payload_digest": density.digest()},
        )

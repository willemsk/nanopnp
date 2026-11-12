"""Stage 1: structure ingestion, alignment and the Cₙ axis (FR-01 to FR-03)."""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, file_hash
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import StructureArtefact
from nanopnp.io.case import UnsupportedCaseSection
from nanopnp.io.resolved import ResolvedStructure, parse_chains
from nanopnp.io.workspace import scratch_directory
from nanopnp.structure.axis import (
    ANGLE_TOLERANCE_DEG,
    ORIENTATION_LIMIT_DEG,
    SPACING_FRACTION,
    AxisRecord,
    Displacement,
    check_z_axis,
    cyclic_fit,
    detect_axis,
    frame_rotation,
    gate_axis,
    kabsch,
    measure_axis,
)
from nanopnp.structure.cavity import (
    COVERAGE_FRACTION,
    HYDROGENS,
    STRAIGHTNESS_NM,
    ChannelRecord,
    channel_axis,
    check_z_channel,
    detect_channel,
    refit,
    straightness_warning,
)
from nanopnp.structure.ensemble import ORIENTATION_RULE, PAYLOAD_NAME, AlignedEnsemble
from nanopnp.structure.read import (
    StructureInputError,
    check_chains_whole,
    frame_times,
    load_universe,
    positions_nm,
    select,
    select_frames,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.io.artefact import StageInputs

logger = logging.getLogger(__name__)


def _structure(inputs: StageInputs) -> ResolvedStructure:
    resolved = inputs.resolved
    if resolved.structure is None:
        raise UnsupportedCaseSection(
            f"case {inputs.resolved.name!r} carries no structure: section, so stage 1 has nothing "
            "to read"
        )
    return resolved.structure


def structure_parameters(structure: ResolvedStructure) -> dict[str, Canonicalisable]:
    """Return the stage-1 key's parameters: the block, each file replaced by its digest."""
    parameters: dict[str, Canonicalisable] = structure.spec.model_dump(mode="json")
    # ``variant`` is a label: keeping it in the key would re-align and re-key stages 2 to 6,
    # and in the header a cache hit would return a stale label.
    del parameters["source"]["variant"]
    source = structure.spec.source.path
    if not source.is_file():
        raise StructureInputError(
            f"structure.source.path {str(source)!r} does not exist or is not a file"
        )
    parameters["source"]["path"] = {"sha256": file_hash(source)}
    trajectory = structure.spec.ensemble.trajectory
    if trajectory is not None:
        if not trajectory.is_file():
            raise StructureInputError(
                f"structure.ensemble.trajectory {str(trajectory)!r} does not exist or is not a file"
            )
        parameters["ensemble"]["trajectory"] = {"sha256": file_hash(trajectory)}
    return parameters


def _digest(parameters: Mapping[str, Canonicalisable], section: str, key: str) -> str:
    entry = parameters[section]
    assert isinstance(entry, Mapping)  # structure_parameters built it so
    digest = entry[key]
    assert isinstance(digest, Mapping)
    return str(digest["sha256"])


@dataclass(frozen=True)
class Alignment:
    """What :func:`align` produced: the ensemble, and the record its header is made from."""

    ensemble: AlignedEnsemble
    record: AxisRecord | ChannelRecord


def _angle_deg(first: np.ndarray, second: np.ndarray) -> float:
    import numpy as np

    return math.degrees(
        math.atan2(float(np.linalg.norm(np.cross(first, second))), float(first @ second))
    )


def align(
    structure: ResolvedStructure,
    *,
    parameters: Mapping[str, Canonicalisable] | None = None,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
) -> Alignment:
    """Read, select, superpose, find the axis and transform to the model frame.

    Raises
    ------
    nanopnp.structure.read.StructureInputError
        For a refused file, element, alternate location, chain set or frame window.
    nanopnp.structure.axis.SymmetryGateError
        For a refused spacing, rotation angle, channel, orientation or ``axis: z`` displacement.
    """
    import numpy as np

    spec = structure.spec
    n = structure.n
    if parameters is None:
        parameters = structure_parameters(structure)
    check_cancelled(cancel, "reading the structure")
    report(progress, 0.0, f"reading {spec.source.path.name}")
    universe = load_universe(spec.source.path, spec.ensemble.trajectory)
    axis_mode = spec.symmetry.axis
    # The channel gives the axis where it is asked for, and under C1, which has no ring.
    channel = axis_mode == "cavity" or n == 1
    chosen = select(
        universe,
        selection=spec.source.selection,
        chains=spec.source.chains,
        n=n,
        channel=channel,
    )
    times, interval = frame_times(universe)
    window = select_frames(
        times, interval, last_ns=spec.ensemble.frames.last_ns, count=spec.ensemble.frames.count
    )
    logger.info(
        "structure: %d atoms, %d units by %s, %d common C-alpha; frames %d of %d",
        len(chosen.atoms),
        n,
        chosen.chain_key,
        chosen.common_index.shape[1],
        len(window.indices),
        window.available,
    )

    check_cancelled(cancel, "reading the frames")
    report(progress, 0.2, f"reading {len(window.indices)} frames")
    positions = positions_nm(chosen.group, window.indices)
    check_chains_whole(chosen, positions, window.indices)

    report(progress, 0.5, "superposing the frames on the earliest")
    fit_index = chosen.fit_index
    reference = positions[0][fit_index]
    rmsd: list[float] = []
    for frame in range(positions.shape[0]):
        check_cancelled(cancel, f"superposing frame {window.indices[frame]}")
        fit = kabsch(positions[frame][fit_index], reference)
        positions[frame] = fit.apply(positions[frame])
        rmsd.append(fit.rmsd_nm)

    report(progress, 0.7, "finding the axis")
    mean = positions.mean(axis=0)
    chains = mean[chosen.common_index]
    fit_z = mean[fit_index][:, 2]
    extent = (float(fit_z.min()), float(fit_z.max()))
    record: AxisRecord | ChannelRecord
    displacement: Displacement | None = None
    heavy = ~np.isin(np.char.upper(chosen.atoms.element.astype(str)), sorted(HYDROGENS))
    if channel:
        record = detect_channel(mean[heavy])
        listed = parse_chains(spec.source.chains)
        first = chosen.chains[0] if listed is None else listed[0]
        own = chosen.atoms.chain == first
        calpha = fit_index[own[fit_index]]
        # The channel takes chains of any kind: one without a C-alpha places by its own atoms.
        first_centroid = mean[calpha if calpha.size else np.flatnonzero(own)].mean(axis=0)
    elif axis_mode == "auto":
        record = detect_axis(chains, n)
        first_centroid = chains[0].mean(axis=0)
    else:
        record = gate_axis(measure_axis(chains, n))
    if axis_mode == "z":
        displacement = (
            check_z_channel(record, extent)
            if isinstance(record, ChannelRecord)
            else check_z_axis(record, extent)
        )
        foot = np.zeros(3)
        rotation = np.eye(3)
    else:
        foot = record.foot_nm
        rotation = frame_rotation(record, first_centroid)

    warnings: list[Canonicalisable] = []
    if isinstance(record, ChannelRecord) and (bent := straightness_warning(record)) is not None:
        logger.warning("%s", bent)
        warnings.append(bent)

    drift: list[float] = []
    for frame in range(positions.shape[0]):
        frame_axis = (
            refit(record, mean[heavy], positions[frame][heavy])
            if isinstance(record, ChannelRecord)
            else cyclic_fit(positions[frame][chosen.common_index], record.order).axis
        )
        drift.append(_angle_deg(frame_axis, record.axis))

    check_cancelled(cancel, "transforming to the model frame")
    report(progress, 0.9, "transforming to the model frame")
    # In place per frame: the whole-ensemble expression would hold two more float64 copies.
    for frame in range(positions.shape[0]):
        positions[frame] = (positions[frame] - foot) @ rotation.T
    aligned = positions

    # Recorded, not gated: a threshold here would be one more constant the specification omits.
    aligned_mean = aligned.mean(axis=0)
    again: AxisRecord | ChannelRecord = (
        channel_axis(aligned_mean[heavy])
        if isinstance(record, ChannelRecord)
        else measure_axis(aligned_mean[chosen.common_index], n)
    )
    frame_check: dict[str, Canonicalisable] = {
        "tilt_deg": again.tilt_deg,
        "offset_nm": float(np.hypot(*again.foot_nm[:2])),
    }

    header: dict[str, Canonicalisable] = {
        "source": {
            "file": spec.source.path.name,
            "sha256": _digest(parameters, "source", "path"),
        },
        "trajectory": (
            None
            if spec.ensemble.trajectory is None
            else {
                "file": spec.ensemble.trajectory.name,
                "sha256": _digest(parameters, "ensemble", "trajectory"),
            }
        ),
        "selection": spec.source.selection,
        "point_group": f"C{n}",
        "n": n,
        "chain_key": chosen.chain_key,
        "chains_file_order": list(chosen.chains),
        "chains_cyclic_order": (
            [chosen.units[index] for index in record.order]
            if isinstance(record, AxisRecord)
            else list(chosen.units)
        ),
        "atoms": len(chosen.atoms),
        "common_ca": int(chosen.common_index.shape[1]),
        "fit_ca": len(fit_index),
        "frames": window.summary(),
        "superposition": {
            "reference_frame": window.indices[0],
            "weights": "unweighted",
            "rmsd_nm": rmsd,
        },
        "axis": {
            "mode": axis_mode,
            "method": "channel" if isinstance(record, ChannelRecord) else "permutation",
            "file_frame": record.summary(),
            "foot_nm": [float(value) for value in foot],
            "rotation": [[float(value) for value in row] for row in rotation],
            "checked": True,
            "groups": None if chosen.groups is None else [list(g) for g in chosen.groups],
        },
        "gates": _gates(record, displacement, axis_mode),
        "drift_deg": drift,
        "frame_check": frame_check,
        "orientation_rule": ORIENTATION_RULE,
    }
    if warnings:
        # Present only when one fired, so the header of a straight channel keeps its digest.
        header["warnings"] = warnings
    ensemble = AlignedEnsemble(
        positions_nm=np.asarray(aligned, dtype=np.float32),
        element=chosen.atoms.element,
        name=chosen.atoms.name,
        resname=chosen.atoms.resname,
        resid=chosen.atoms.resid,
        icode=chosen.atoms.icode,
        chain=chosen.atoms.chain,
        header=header,
    )
    report(progress, 1.0, f"axis found; {ensemble.frames} frames aligned")
    return Alignment(ensemble=ensemble, record=record)


def _gates(
    record: AxisRecord | ChannelRecord, displacement: Displacement | None, axis_mode: str
) -> dict[str, Canonicalisable]:
    gates: dict[str, Canonicalisable]
    if isinstance(record, ChannelRecord):
        gates = {
            "coverage": {"measured": record.coverage, "limit": COVERAGE_FRACTION},
            "straightness": {
                "measured_nm": record.straightness_nm,
                "limit_nm": STRAIGHTNESS_NM,
            },
        }
    else:
        nominal = 360.0 / record.n
        gates = {
            "spacing": {
                "measured_deg": record.spacing_error_deg,
                "limit_deg": SPACING_FRACTION * nominal,
            },
            "angle": {
                "measured_deg": abs(record.angle_deg - nominal),
                "limit_deg": ANGLE_TOLERANCE_DEG,
            },
        }
    gates["orientation"] = {"measured_deg": record.tilt_deg, "limit_deg": ORIENTATION_LIMIT_DEG}
    if axis_mode == "z" and displacement is not None:
        gates["displacement"] = displacement.summary()
    return gates


class StructureStage:
    """Stage 1: a structure and its ensemble to an aligned, content-addressed ensemble."""

    name = "structure"

    def __init__(self, *, workspace: Path | None = None, overwrite_workspace: bool = False) -> None:
        self._workspace = Path(workspace) if workspace is not None else None
        self._overwrite = overwrite_workspace

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> StructureArtefact:
        """Return the artefact key, from the block and its files' digests, without reading them."""
        return StructureArtefact(parameters=structure_parameters(_structure(inputs)))

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> StructureArtefact:
        """Align the ensemble and emit the stage-1 artefact.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true.
        """
        structure = _structure(inputs)
        parameters = structure_parameters(structure)
        directory = scratch_directory(self._workspace, self.name, overwrite=self._overwrite)
        alignment = align(structure, parameters=parameters, progress=progress, cancel=cancel)
        path = alignment.ensemble.write(directory / f"{PAYLOAD_NAME}.npz")
        summary = {**alignment.ensemble.header, "payload_digest": alignment.ensemble.digest()}
        return StructureArtefact(
            parameters=parameters, payload={PAYLOAD_NAME: path}, summary=summary
        )

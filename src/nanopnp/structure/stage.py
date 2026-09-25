"""Stage 1 of section 5.2: structure ingestion, alignment and the Cₙ axis (FR-01 to FR-03).

The stage reads a structure and its ensemble (IF-04), superposes every selected
frame on the C-alpha set of the earliest one (FR-01), finds the Cₙ axis of the
ensemble-mean structure by chain-permutation superposition and puts it on z at
r = 0 (FR-02), and checks the oligomeric state on the way (FR-03). Its contract
is the section 5.3.1 NOTE on ``structure:``; the decisions behind it are the
WP18 plan's.

**The key is the ``structure:`` block with each file replaced by its content
digest** (WP18 D11): a moved file is the same input, an edited one a different
key, and nothing about the result — which comes out of an SVD whose last bits
LAPACK may vary — enters it. The payload's own digest is recorded in the summary
and re-checked on load (VER-23).

**The frame is fixed here and inherited by every later stage** (WP18 D8): the
axis on z through r = 0, signed to the file's +z, which the file is required to
point to *cis*; ``z = â·x``, so the file's axial coordinate is kept and
``geometry.membrane.centre_z_nm`` reads in the frame it is written in; the first
chain in file order on +x. Stage 5 applies ``centre_z_nm``, not this one.
"""

from __future__ import annotations

import logging
import math
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, file_hash
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import StructureArtefact
from nanopnp.io.case import ResolvedStructure, UnsupportedCaseSection, resolve
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
from nanopnp.structure.ensemble import ORIENTATION_RULE, PAYLOAD_NAME, AlignedEnsemble
from nanopnp.structure.read import (
    StructureInputError,
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

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to when no workspace is given."""


def _structure(inputs: StageInputs) -> ResolvedStructure:
    """Return the case's resolved ``structure:`` block, or refuse a case without one."""
    resolved = resolve(inputs.case)
    if resolved.structure is None:
        raise UnsupportedCaseSection(
            f"case {inputs.case.name!r} carries no structure: section, so stage 1 has nothing "
            "to read"
        )
    return resolved.structure


def structure_parameters(structure: ResolvedStructure) -> dict[str, Canonicalisable]:
    """Return the stage-1 key's parameters: the block, each file replaced by its digest.

    Raises
    ------
    nanopnp.structure.read.StructureInputError
        If a named file is missing, naming the key.
    """
    parameters: dict[str, Canonicalisable] = structure.spec.model_dump(mode="json")
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
    """Return the sha256 :func:`structure_parameters` put in place of a file path."""
    entry = parameters[section]
    assert isinstance(entry, Mapping)  # structure_parameters built it so
    digest = entry[key]
    assert isinstance(digest, Mapping)
    return str(digest["sha256"])


@dataclass(frozen=True)
class Alignment:
    """What :func:`align` produced: the ensemble, and the record its header is made from."""

    ensemble: AlignedEnsemble
    record: AxisRecord | None


def _angle_deg(first: np.ndarray, second: np.ndarray) -> float:
    """Return the angle between two unit vectors, in degrees, robust near zero."""
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

    Parameters
    ----------
    structure
        The resolved ``structure:`` block.
    parameters
        Its key's parameters, as :func:`structure_parameters` returns them; the
        header takes the file digests from here rather than reading each file a
        second time. Computed when omitted.
    progress, cancel
        As the stage protocol gives them.

    Returns
    -------
    Alignment
        The aligned ensemble, with its header, and the axis record (``None`` for
        C1 under ``axis: z``, which is unchecked).

    Raises
    ------
    nanopnp.structure.read.StructureInputError
        For a refused file, element, alternate location, chain set or frame
        window.
    nanopnp.structure.axis.SymmetryGateError
        For a refused spacing, rotation angle, orientation or ``axis: z``
        displacement.
    """
    import numpy as np

    spec = structure.spec
    n = structure.n
    if parameters is None:
        parameters = structure_parameters(structure)
    check_cancelled(cancel, "reading the structure")
    report(progress, 0.0, f"reading {spec.source.path.name}")
    universe = load_universe(spec.source.path, spec.ensemble.trajectory)
    chosen = select(universe, selection=spec.source.selection, chains=spec.source.chains, n=n)
    times, interval = frame_times(universe)
    window = select_frames(
        times, interval, last_ns=spec.ensemble.frames.last_ns, count=spec.ensemble.frames.count
    )
    logger.info(
        "structure: %d atoms, %d chains by %s, %d common C-alpha; frames %d of %d",
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
    axis_mode = spec.symmetry.axis
    record: AxisRecord | None = None
    displacement: Displacement | None = None
    if axis_mode == "auto":
        record = detect_axis(chains, n)
        foot = record.foot_nm
        rotation = frame_rotation(record, chains[0].mean(axis=0))
    else:
        if n >= 2:
            record = gate_axis(measure_axis(chains, n))
            displacement = check_z_axis(record, extent)
        foot = np.zeros(3)
        rotation = np.eye(3)

    drift: list[float] = []
    if record is not None:
        for frame in range(positions.shape[0]):
            frame_axis = cyclic_fit(positions[frame][chosen.common_index], record.order).axis
            drift.append(_angle_deg(frame_axis, record.axis))

    check_cancelled(cancel, "transforming to the model frame")
    report(progress, 0.9, "transforming to the model frame")
    aligned = (positions - foot) @ rotation.T

    # The transformed ensemble should carry its own axis on z through r = 0. It
    # is recorded, not gated: the tests hold it to round-off, and a threshold
    # here would be a fifth constant the specification does not name.
    frame_check: dict[str, Canonicalisable] | None = None
    if record is not None:
        again = measure_axis(aligned.mean(axis=0)[chosen.common_index], n)
        frame_check = {
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
        "variant": spec.source.variant,
        "selection": spec.source.selection,
        "point_group": f"C{n}",
        "n": n,
        "chain_key": chosen.chain_key,
        "chains_file_order": list(chosen.chains),
        "chains_cyclic_order": (
            [chosen.chains[index] for index in record.order]
            if record is not None
            else list(chosen.chains)
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
            "file_frame": None if record is None else record.summary(),
            "foot_nm": [float(value) for value in foot],
            "rotation": [[float(value) for value in row] for row in rotation],
            "checked": record is not None,
        },
        "gates": _gates(record, displacement, axis_mode),
        "drift_deg": drift,
        "frame_check": frame_check,
        "orientation_rule": ORIENTATION_RULE,
    }
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
    report(progress, 1.0, f"C{n} axis found; {ensemble.frames} frames aligned")
    return Alignment(ensemble=ensemble, record=record)


def _gates(
    record: AxisRecord | None, displacement: Displacement | None, axis_mode: str
) -> dict[str, Canonicalisable]:
    """Return every gate measurement beside its threshold (QR-12, WP18 D10)."""
    if record is None:
        return {"status": "unchecked: C1 under axis: z has no permutation to measure"}
    nominal = 360.0 / record.n
    gates: dict[str, Canonicalisable] = {
        "spacing": {
            "measured_deg": record.spacing_error_deg,
            "limit_deg": SPACING_FRACTION * nominal,
        },
        "angle": {
            "measured_deg": abs(record.angle_deg - nominal),
            "limit_deg": ANGLE_TOLERANCE_DEG,
        },
        "orientation": {"measured_deg": record.tilt_deg, "limit_deg": ORIENTATION_LIMIT_DEG},
    }
    if axis_mode == "z" and displacement is not None:
        gates["displacement"] = displacement.summary()
    return gates


class StructureStage:
    """Stage 1: a structure and its ensemble to an aligned, content-addressed ensemble."""

    name = "structure"

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
            If ``cancel`` turns true. No artefact is written.
        """
        structure = _structure(inputs)
        parameters = structure_parameters(structure)
        alignment = align(structure, parameters=parameters, progress=progress, cancel=cancel)
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="structure-", dir=root))
        path = alignment.ensemble.write(directory / f"{PAYLOAD_NAME}.npz")
        summary = {**alignment.ensemble.header, "payload_digest": alignment.ensemble.digest()}
        return StructureArtefact(
            parameters=parameters, payload={PAYLOAD_NAME: path}, summary=summary
        )

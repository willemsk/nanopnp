"""Structure preparation: the pore axis onto z, the named end *cis*, a centroid placed (FR-37)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from nanopnp.core.stages import MissingExtraError
from nanopnp.io.resolved import parse_chains
from nanopnp.structure import cavity
from nanopnp.structure.axis import SymmetryGateError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

__all__ = [
    "DEGENERACY",
    "OFF_AXIS_WARNING_NM",
    "PreparationRecord",
    "SourceFile",
    "orient_pore",
    "prepared_pore",
]

logger = logging.getLogger(__name__)

DEGENERACY = 0.25
"""The largest ratio of the closest eigenvalue gap to the spread for which an axis is distinct."""

END_FRACTION = 0.2
"""The fraction of the C-alpha heights at each end whose mean radius tells the wider end."""

OFF_AXIS_WARNING_NM = 0.1
"""The registration centroid's distance from the axis, in nm, above which a warning is logged."""

_ANGSTROM_PER_NM = 10.0


class SourceFile(BaseModel):
    """The structure file a preparation read."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="The file's name, without its directory.")
    sha256: str = Field(description="The SHA-256 of the file's bytes, as read, gzip included.")


class PreparationRecord(BaseModel):
    """What ``orient_pore`` chose and found, written beside the file it wrote."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: SourceFile
    chains: str
    cis_end: Literal["wider", "narrower"]
    registration_residues: tuple[int, int] | None
    centroid_z_nm: float
    axis: tuple[float, float, float] = Field(
        description="The unit axis used, in the source file's frame, signed to point to cis."
    )
    tilt_deg: float = Field(
        description="The angle in degrees, 0 to 90, between the axis line and the file's z, "
        "before the structure is oriented."
    )
    method: Literal["covariance", "channel", "typed"] = Field(
        description="How the axis was found: the C-alpha covariance, the channel's cavity, or "
        "the axis the caller gave."
    )
    off_axis_nm: float = Field(
        description="How far the registration centroid lies from the axis line used, in nm; the "
        "pore axis sits that far from r = 0 once the structure is placed."
    )
    warnings: tuple[str, ...] = Field(
        default=(),
        description="What the preparation went on despite: the channel's straightness where "
        "over its limit; empty when nothing was.",
    )


def _covariance(calpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np

    values, vectors = np.linalg.eigh(np.cov(calpha.T))
    return np.asarray(values), np.asarray(vectors)


def _distinct_axis(values: np.ndarray, vectors: np.ndarray) -> np.ndarray | None:
    import numpy as np

    # A ring of n >= 3 like chains leaves the covariance unchanged under the 2 pi / n turn,
    # so two eigenvalues are equal and the axis is the eigenvector of the third.
    low, high = values[1] - values[0], values[2] - values[1]
    spread = values[2] - values[0]
    if spread <= 0.0 or min(low, high) / spread > DEGENERACY:
        return None
    axis = vectors[:, 2] if low < high else vectors[:, 0]
    return np.asarray(axis)


def _channel_line(
    heavy: np.ndarray, vectors: np.ndarray, values: np.ndarray
) -> tuple[np.ndarray, np.ndarray, str | None]:
    # The channel's line, in the file's ångströms, from the start whose planes' centres lie
    # straightest among those that converge and cover the structure, with the straightness
    # warning where even that start is over the limit; the orientation gate does not apply,
    # since the file is not oriented yet.
    import numpy as np

    atoms_nm = heavy / _ANGSTROM_PER_NM
    start = atoms_nm.mean(axis=0)
    best: cavity.ChannelRecord | None = None
    tried = []
    for index in range(3):
        try:
            record = cavity.channel_axis(
                atoms_nm, start_axis=vectors[:, index], start_point_nm=start
            )
        except SymmetryGateError as error:
            tried.append(f"start {index}: {error}")
            continue
        passes = record.converged and record.coverage >= cavity.COVERAGE_FRACTION
        tried.append(
            f"start {index}: converged {record.converged}, coverage {record.coverage:.2f}, "
            f"straightness {record.straightness_nm:.3f} nm"
        )
        if passes and (best is None or record.straightness_nm < best.straightness_nm):
            best = record
    if best is None:
        raise ValueError(
            f"the C-alpha covariance has eigenvalues {np.round(values / 100.0, 3).tolist()} nm²; "
            "none stands apart from the other two, and the channel's axis found from each of "
            "the three covariance axes fails the convergence or coverage gate "
            f"({'; '.join(tried)}); give the axis"
        )
    return (
        np.asarray(best.axis),
        np.asarray(best.centroid_nm) * _ANGSTROM_PER_NM,
        cavity.straightness_warning(best),
    )


def _signed(calpha: np.ndarray, axis: np.ndarray, cis_end: str) -> np.ndarray:
    import numpy as np

    centred = calpha - calpha.mean(axis=0)
    height = centred @ axis
    radius = np.linalg.norm(centred - np.outer(height, axis), axis=1)
    top = float(radius[height > np.quantile(height, 1.0 - END_FRACTION)].mean())
    bottom = float(radius[height < np.quantile(height, END_FRACTION)].mean())
    logger.info(
        "mean C-alpha radius %.2f nm at +axis, %.2f nm at -axis",
        top / _ANGSTROM_PER_NM,
        bottom / _ANGSTROM_PER_NM,
    )
    top_is_cis = (top > bottom) == (cis_end == "wider")
    return axis if top_is_cis else -axis


def _onto_z(axis: np.ndarray) -> np.ndarray:
    # Rodrigues' formula; a vector already on -z turns by pi about x.
    import numpy as np

    z = np.array([0.0, 0.0, 1.0])
    cross = np.cross(axis, z)
    sine, cosine = float(np.linalg.norm(cross)), float(axis @ z)
    if sine < 1e-12:
        return np.eye(3) if cosine > 0 else np.diag([1.0, -1.0, -1.0])
    k = cross / sine
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.asarray(np.eye(3) + sine * skew + (1.0 - cosine) * (skew @ skew))


def orient_pore(
    source: str | Path,
    *,
    chains: str = "all",
    cis_end: Literal["wider", "narrower"],
    registration_residues: tuple[int, int] | None = None,
    centroid_z_nm: float = 0.0,
    axis: tuple[float, float, float] | None = None,
    out: str | Path,
) -> Path:
    """Write a structure's protein chains with the pore axis on z and the named end *cis*.

    The axis is the one given, else the C-alpha covariance's where one eigenvalue stands apart
    from the other two, else the channel's, found from the heavy atoms' empty space; it needs only
    to fall inside stage 1's gate, which then finds the axis itself. The structure is centred
    laterally on the registration residues' centroid, which lies on the axis for a full ring; a
    warning is logged where it is more than :data:`OFF_AXIS_WARNING_NM` off, as when a chain
    lacks some of those residues. A :class:`PreparationRecord` is written beside ``out``, at
    ``out.with_suffix(".prepare.json")``. Returns ``out``.

    Parameters
    ----------
    source
        A PDB or mmCIF file, optionally gzipped.
    chains
        The chains kept, comma-separated, or ``all``.
    cis_end
        Which end of the pore, by the mean C-alpha radius of its last fifth, faces *cis* (+z).
    registration_residues
        The ``(first, last)`` residues whose C-alpha centroid is placed on the axis at
        ``centroid_z_nm``; every kept C-alpha when ``None``.
    axis
        The pore axis in the file's frame, any length and sign; the sign is set by ``cis_end``.
        It passes through the kept C-alpha centroid. Estimated when ``None``.
    out
        The PDB file written.

    Raises
    ------
    MissingExtraError
        MDAnalysis is not installed; the message names the ``structure`` extra.
    ValueError
        A chain is not in the file, no C-alpha is selected, the axis is a zero vector, or no axis
        can be estimated.
    """
    try:
        import MDAnalysis  # noqa: F401 - imported for its error only

        from nanopnp.structure import read
    except ImportError as error:
        missing = error.name or "MDAnalysis"
        raise MissingExtraError(
            f"orient_pore reads a structure with MDAnalysis and needs the 'structure' extra: "
            f"importing {missing!r} failed. Install the extras with `uv sync --all-extras`",
            name=missing,
        ) from error
    import numpy as np

    if cis_end not in ("wider", "narrower"):
        raise ValueError(f"cis_end is 'wider' or 'narrower', got {cis_end!r}")
    typed: np.ndarray | None = None
    if axis is not None:
        typed = np.asarray(axis, dtype=np.float64)
        length = float(np.linalg.norm(typed)) if typed.shape == (3,) else float("nan")
        if not 0.0 < length < float("inf"):
            raise ValueError(f"axis is three finite numbers, not all zero, got {axis!r}")
        typed = typed / length
    universe = read.load_universe(Path(source))
    protein = universe.select_atoms("protein")
    keys, chain_key = read.chain_keys(protein)
    listed = parse_chains(chains)
    if listed is not None:
        present = tuple(dict.fromkeys(keys))
        missing_chains = [chain for chain in listed if chain not in present]
        if missing_chains:
            raise ValueError(
                f"chains {', '.join(missing_chains)} are not in {Path(source).name}; its protein "
                f"holds chains {', '.join(present)} by {chain_key}"
            )
        protein = protein[np.isin(np.asarray(keys), np.asarray(listed))]
    calpha_atoms = protein.select_atoms("name CA")
    if len(calpha_atoms) < 3:
        raise ValueError(f"the chains kept hold {len(calpha_atoms)} C-alpha atoms; at least 3")
    calpha = calpha_atoms.positions.astype(np.float64)
    method: Literal["covariance", "channel", "typed"]
    point = calpha.mean(axis=0)
    notes: list[str] = []
    if typed is not None:
        found, method = typed, "typed"
    else:
        values, vectors = _covariance(calpha)
        distinct = _distinct_axis(values, vectors)
        if distinct is not None:
            found, method = distinct, "covariance"
        else:
            elements = np.char.upper(np.asarray(protein.elements, dtype=str))
            heavy = protein.positions.astype(np.float64)[
                ~np.isin(elements, sorted(cavity.HYDROGENS))
            ]
            found, point, bent = _channel_line(heavy, vectors, values)
            method = "channel"
            if bent is not None:
                logger.warning("%s", bent)
                notes.append(bent)
    axis_used = _signed(calpha, found, cis_end)
    tilt = float(np.degrees(np.arccos(min(1.0, abs(float(axis_used[2]))))))
    logger.info(
        "pore axis %s by %s, %.2f° from the file's z", np.round(axis_used, 4).tolist(), method, tilt
    )

    anchor = calpha_atoms
    if registration_residues is not None:
        first, last = registration_residues
        anchor = calpha_atoms.select_atoms(f"resid {first}:{last}")
        if len(anchor) == 0:
            raise ValueError(f"no kept C-alpha lies in residues {first} to {last}")
    centroid = anchor.positions.astype(np.float64).mean(axis=0)
    offset = centroid - point
    off_axis = float(np.linalg.norm(offset - (offset @ axis_used) * axis_used)) / _ANGSTROM_PER_NM
    if off_axis > OFF_AXIS_WARNING_NM:
        logger.warning(
            "the registration centroid is %.2f nm off the pore axis, so the pore axis "
            "will sit that far from r = 0; a chain may lack some of the registration residues",
            off_axis,
        )
    target = np.array([0.0, 0.0, centroid_z_nm * _ANGSTROM_PER_NM])
    moved = (protein.positions.astype(np.float64) - centroid) @ _onto_z(axis_used).T + target
    protein.positions = moved.astype(np.float32)
    destination = Path(out)
    with warnings.catch_warnings():
        # The writer warns of the defaults it fills in; none of it concerns the coordinates.
        warnings.simplefilter("ignore")
        protein.write(str(destination))
    record = PreparationRecord(
        source=SourceFile(
            name=Path(source).name, sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest()
        ),
        chains=chains,
        cis_end=cis_end,
        registration_residues=registration_residues,
        centroid_z_nm=centroid_z_nm,
        axis=(float(axis_used[0]), float(axis_used[1]), float(axis_used[2])),
        tilt_deg=tilt,
        method=method,
        off_axis_nm=off_axis,
        warnings=tuple(notes),
    )
    destination.with_suffix(".prepare.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    logger.info("wrote %s: %d atoms", destination, len(protein))
    return destination


def prepared_pore(
    source: str | Path,
    *,
    directory: str | Path,
    chains: str = "all",
    cis_end: Literal["wider", "narrower"],
    registration_residues: tuple[int, int] | None = None,
    centroid_z_nm: float = 0.0,
    axis: tuple[float, float, float] | None = None,
) -> Path:
    """Return ``orient_pore``'s file for these choices, written under ``directory`` once.

    The file is named by a digest of the source file's bytes, the choices and the code of this
    module, of the channel's axis and of the reader, so a changed source or preparation is a new
    file; it is written whole or not at all, with its ``.prepare.json`` beside it.
    """
    origin = Path(source)
    choices = {
        "chains": chains,
        "cis_end": cis_end,
        "registration_residues": registration_residues,
        "centroid_z_nm": centroid_z_nm,
        "axis": None if axis is None else [float(value) for value in axis],
    }
    digest = hashlib.sha256(origin.read_bytes())
    digest.update(json.dumps(choices, sort_keys=True).encode())
    here = Path(__file__)
    for code in (here, here.with_name("cavity.py"), here.with_name("read.py")):
        digest.update(code.read_bytes())
    prepared = Path(directory) / f"{origin.name.split('.')[0]}-{digest.hexdigest()[:12]}.pdb"
    if not prepared.is_file():
        prepared.parent.mkdir(parents=True, exist_ok=True)
        staged = prepared.with_name(f".{prepared.stem}.{os.getpid()}.partial.pdb")
        staged_record = staged.with_suffix(".prepare.json")
        try:
            orient_pore(
                origin,
                chains=chains,
                cis_end=cis_end,
                registration_residues=registration_residues,
                centroid_z_nm=centroid_z_nm,
                axis=axis,
                out=staged,
            )
            # The record goes first: the file's presence marks a whole pair.
            staged_record.replace(prepared.with_suffix(".prepare.json"))
            staged.replace(prepared)
        finally:
            staged.unlink(missing_ok=True)
            staged_record.unlink(missing_ok=True)
    return prepared

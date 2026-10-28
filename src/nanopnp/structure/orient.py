"""Structure preparation: the pore axis onto z, the named end *cis*, a centroid placed (FR-37)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from nanopnp.core.stages import MissingExtraError
from nanopnp.io.resolved import parse_chains

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

__all__ = ["DEGENERACY", "OFF_AXIS_WARNING_NM", "orient_pore", "prepared_pore"]

logger = logging.getLogger(__name__)

DEGENERACY = 0.25
"""The largest ratio of the closest eigenvalue gap to the spread for which an axis is distinct."""

END_FRACTION = 0.2
"""The fraction of the C-alpha heights at each end whose mean radius tells the wider end."""

OFF_AXIS_WARNING_NM = 0.1
"""The registration centroid's distance from the axis, in nm, above which a warning is logged."""

_ANGSTROM_PER_NM = 10.0


def _pore_axis(calpha: np.ndarray) -> np.ndarray:
    # A ring of n >= 3 like chains leaves the covariance unchanged under the 2 pi / n turn,
    # so two eigenvalues are equal and the axis is the eigenvector of the third.
    import numpy as np

    values, vectors = np.linalg.eigh(np.cov(calpha.T))
    low, high = values[1] - values[0], values[2] - values[1]
    spread = values[2] - values[0]
    if spread <= 0.0 or min(low, high) / spread > DEGENERACY:
        raise ValueError(
            f"the C-alpha covariance has eigenvalues {np.round(values / 100.0, 3).tolist()} nm²; "
            "none stands apart from the other two, so there is no pore axis to estimate"
        )
    axis = vectors[:, 2] if low < high else vectors[:, 0]
    return np.asarray(axis / np.linalg.norm(axis))


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
    out: str | Path,
) -> Path:
    """Write a structure's protein chains with the pore axis on z and the named end *cis*.

    The axis is estimated from the C-alpha covariance, so it needs only to fall inside stage 1's
    gate, which then finds the axis itself. The structure is centred laterally on the registration
    residues' centroid, which lies on the axis for a full ring; a warning is logged where it is
    more than :data:`OFF_AXIS_WARNING_NM` off, as when a chain lacks some of those residues.
    Returns ``out``.

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
    out
        The PDB file written.

    Raises
    ------
    MissingExtraError
        MDAnalysis is not installed; the message names the ``structure`` extra.
    ValueError
        A chain is not in the file, no C-alpha is selected, or no axis stands out of the covariance.
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
    axis = _signed(calpha, _pore_axis(calpha), cis_end)
    tilt = float(np.degrees(np.arccos(min(1.0, abs(float(axis[2]))))))
    logger.info("estimated pore axis %s, %.2f° from the file's z", np.round(axis, 4).tolist(), tilt)

    anchor = calpha_atoms
    if registration_residues is not None:
        first, last = registration_residues
        anchor = calpha_atoms.select_atoms(f"resid {first}:{last}")
        if len(anchor) == 0:
            raise ValueError(f"no kept C-alpha lies in residues {first} to {last}")
    centroid = anchor.positions.astype(np.float64).mean(axis=0)
    offset = centroid - calpha.mean(axis=0)
    off_axis = float(np.linalg.norm(offset - (offset @ axis) * axis)) / _ANGSTROM_PER_NM
    if off_axis > OFF_AXIS_WARNING_NM:
        logger.warning(
            "the registration centroid is %.2f nm off the estimated pore axis, so the pore axis "
            "will sit that far from r = 0; a chain may lack some of the registration residues",
            off_axis,
        )
    target = np.array([0.0, 0.0, centroid_z_nm * _ANGSTROM_PER_NM])
    moved = (protein.positions.astype(np.float64) - centroid) @ _onto_z(axis).T + target
    protein.positions = moved.astype(np.float32)
    destination = Path(out)
    with warnings.catch_warnings():
        # The writer warns of the defaults it fills in; none of it concerns the coordinates.
        warnings.simplefilter("ignore")
        protein.write(str(destination))
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
) -> Path:
    """Return ``orient_pore``'s file for these choices, written under ``directory`` once.

    The file is named by a digest of the source file's bytes, the choices and this module's
    code, so a changed source or preparation is a new file; it is written whole or not at all.
    """
    origin = Path(source)
    choices = {
        "chains": chains,
        "cis_end": cis_end,
        "registration_residues": registration_residues,
        "centroid_z_nm": centroid_z_nm,
    }
    digest = hashlib.sha256(origin.read_bytes())
    digest.update(json.dumps(choices, sort_keys=True).encode())
    digest.update(Path(__file__).read_bytes())
    prepared = Path(directory) / f"{origin.name.split('.')[0]}-{digest.hexdigest()[:12]}.pdb"
    if not prepared.is_file():
        prepared.parent.mkdir(parents=True, exist_ok=True)
        staged = prepared.with_name(f".{prepared.stem}.{os.getpid()}.partial.pdb")
        try:
            orient_pore(
                origin,
                chains=chains,
                cis_end=cis_end,
                registration_residues=registration_residues,
                centroid_z_nm=centroid_z_nm,
                out=staged,
            )
            staged.replace(prepared)
        finally:
            staged.unlink(missing_ok=True)
    return prepared

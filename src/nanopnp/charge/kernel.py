"""PHY-16 steps 4-6 on the export lattice: the closed-form azimuthal kernel, summed."""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.charge.fields import PLANE_SMOOTHING_NM, ChargeFieldError
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.stages import CancelToken, Progress, check_cancelled, report
from nanopnp.density.grid import RadialGrid, trapezium_factor

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.charge.protonation import ProtonationTable

__all__ = [
    "KERNEL_ID",
    "LATTICE_RECORD",
    "PATCH_HALF_WIDTHS",
    "PLANE_COUNT",
    "PLANE_SMOOTHING_NM",
    "KernelLattice",
    "SourceAtoms",
    "areal_density",
    "atom_lattice_sum",
    "check_charged",
    "check_spacing",
    "kernel_parameters",
    "lattice_axes",
    "source_atoms",
    "sum_kernel",
    "volume_density",
]

logger = logging.getLogger(__name__)

KERNEL_ID = "azimuthal-mean-3d-gaussian/v1"
"""The kernel of PHY-16 step 5, named in the charge-grid key.

A different kernel -- the reference's 2D ``(r, z)`` Gaussian divided by ``2 pi r``,
which PHY-17 forbids -- would be a different identifier, never a different number
under this one.
"""

LATTICE_RECORD = "origin-and-spacing/v1"
"""What the stored ``.npz`` holds of its lattice; an entry without it is not served."""


PATCH_HALF_WIDTHS = 6.0
"""Each atom's patch half-width, in units of its ``w_i`` (PHY-16 NOTE on the deposition).

``1 - erf(6)^2 = 4.3e-17`` of the atom lies outside the square, below the
round-off of its own renormalisation.
"""

TILE_NM = 0.5
"""Edge of the ``(z, r)`` tiles atoms are binned into for the dense products, in nm.

A cost choice and not a number-changing one beyond summation order: the window a
tile covers is ``TILE_NM + 12 w_max`` on a side, so smaller tiles shrink the
products until the patches dominate.
"""

PLANE_COUNT = 12
"""Planes the per-plane check is evaluated at, spanning the atoms' z-extent."""

NM_TO_M = 1e-9
"""Metres per nanometre."""


@dataclass(frozen=True)
class SourceAtoms:
    """Every charged atom of every frame, in the model frame, as the kernel sums it.

    Parameters
    ----------
    weight_e
        Charge per row, q_i / n_frames, in e.
    """

    r_nm: np.ndarray
    z_nm: np.ndarray
    width_nm: np.ndarray
    weight_e: np.ndarray
    frame: np.ndarray
    atom: np.ndarray
    frames: int
    shift_z_nm: float
    table: ProtonationTable | None = None

    @property
    def count(self) -> int:
        """Return the number of charged atoms over every frame."""
        return int(self.r_nm.size)

    def q_net_e(self) -> float:
        """Return the net charge, the mean over frames of the summed charge, in e."""
        return math.fsum(self.weight_e.tolist())

    def absolute_charge_e(self) -> float:
        """Return the mean over frames of the summed absolute charge, in e."""
        return math.fsum(abs(value) for value in self.weight_e.tolist())

    def label(self, row: int) -> str:
        """Return one row as a diagnostic names it: frame, residue, chain and atom."""
        frame = int(self.frame[row])
        if self.table is None:
            return f"atom {int(self.atom[row])} of frame {frame}"
        index = int(self.atom[row])
        table = self.table
        icode = str(table.icode[index]).strip()
        return (
            f"atom {str(table.name[index]).strip()} of {str(table.resname[index]).strip()} "
            f"{int(table.resid[index])}{icode} in chain {str(table.chain[index])!r}, frame {frame}"
        )

    def z_extent_nm(self) -> tuple[float, float]:
        """Return the smallest and largest atom-centre z, in nm."""
        return float(self.z_nm.min()), float(self.z_nm.max())

    def planes_nm(self, count: int = PLANE_COUNT) -> tuple[float, ...]:
        """Return count planes spanning the atoms' z-extent, ends excluded, in nm."""
        low, high = self.z_extent_nm()
        step = (high - low) / (count + 1)
        return tuple(low + step * (index + 1) for index in range(count))

    def cumulative_e(
        self, planes_nm: tuple[float, ...], *, smoothing_nm: float = PLANE_SMOOTHING_NM
    ) -> tuple[float, ...]:
        """Return each plane's charge under a smoothed step, in closed form, in e."""
        import numpy as np
        from scipy.special import erfc

        spread = np.sqrt(smoothing_nm**2 + self.width_nm**2)
        return tuple(
            float(np.sum(self.weight_e * 0.5 * erfc((self.z_nm - plane) / spread)))
            for plane in planes_nm
        )


def source_atoms(
    table: ProtonationTable, *, sharpness: float, shift_z_nm: float = 0.0
) -> SourceAtoms:
    """Return the protonation table's charged atoms in the model frame."""
    import numpy as np

    charged = np.flatnonzero(table.charge_e != 0.0)
    frame = np.searchsorted(table.frame_offsets, charged, side="right") - 1
    positions = np.asarray(table.positions_nm, dtype=np.float64)[charged]
    return SourceAtoms(
        r_nm=np.hypot(positions[:, 0], positions[:, 1]),
        z_nm=positions[:, 2] - shift_z_nm,
        width_nm=sharpness * np.asarray(table.radius_nm, dtype=np.float64)[charged],
        weight_e=np.asarray(table.charge_e, dtype=np.float64)[charged] / table.frames,
        frame=frame.astype(np.int64),
        atom=charged.astype(np.int64),
        frames=table.frames,
        shift_z_nm=shift_z_nm,
        table=table,
    )


def check_charged(atoms: SourceAtoms) -> None:
    """Refuse a protonation artefact with no charged atom."""
    if atoms.count == 0:
        raise ChargeFieldError(
            "the protonation artefact carries no charged atom (PHY-16 step 4)",
            "every atom has q_i = 0, so there is no fixed charge to deposit",
        )


def check_spacing(atoms: SourceAtoms, spacing_nm: float) -> None:
    """Refuse a lattice spacing above half the smallest kernel width."""
    import numpy as np

    if not 0.0 < spacing_nm < math.inf:
        raise ChargeFieldError(
            "the export lattice spacing is not positive (charge.smearing.grid_spacing_nm)",
            f"{spacing_nm} nm",
        )
    if atoms.count == 0:
        return
    narrowest = int(np.argmin(atoms.width_nm))
    width = float(atoms.width_nm[narrowest])
    if not width > 0.0:
        raise ChargeFieldError(
            "a charged atom has no kernel width (PHY-16 step 4)",
            f"{atoms.label(narrowest)} has w = {width} nm; its radius must be positive",
        )
    if not spacing_nm <= 0.5 * width:
        raise ChargeFieldError(
            "the export lattice does not resolve the narrowest kernel "
            "(charge.smearing.grid_spacing_nm, PHY-16 NOTE on the deposition)",
            f"the spacing is {spacing_nm:g} nm and {atoms.label(narrowest)} has "
            f"w = {width:.6g} nm; the spacing must be at most w/2 = {0.5 * width:.6g} nm",
        )


def lattice_axes(
    atoms: SourceAtoms, spacing_nm: float, *, half_widths: float = PATCH_HALF_WIDTHS
) -> tuple[int, int, int]:
    """Return the lattice as (n_r, k0, n_z), in nm."""
    import numpy as np

    reach = half_widths * float(np.max(atoms.width_nm))
    h = spacing_nm
    n_r = math.ceil(float(np.max(atoms.r_nm) + reach) / h) + 1
    k0 = math.floor(float(np.min(atoms.z_nm) - reach) / h)
    k1 = math.ceil(float(np.max(atoms.z_nm) + reach) / h)
    return n_r, k0, k1 - k0 + 1


def _patches(
    centre_nm: np.ndarray,
    width_nm: np.ndarray,
    spacing_nm: float,
    origin: int,
    count: int,
    half_widths: float,
) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np

    reach = half_widths * width_nm
    first = np.ceil((centre_nm - reach) / spacing_nm).astype(np.int64) - origin
    last = np.floor((centre_nm + reach) / spacing_nm).astype(np.int64) - origin
    first = np.clip(first, 0, count - 1)
    last = np.clip(last, 0, count - 1)
    return first, last - first + 1


def _factors(
    atoms: SourceAtoms,
    rows: np.ndarray,
    spacing_nm: float,
    n_r: int,
    k0: int,
    n_z: int,
    half_widths: float,
) -> tuple[
    tuple[np.ndarray, np.ndarray, np.ndarray],
    tuple[np.ndarray, np.ndarray, np.ndarray],
]:
    import numpy as np
    from scipy.special import i0e

    h = spacing_nm
    r_i = atoms.r_nm[rows]
    z_i = atoms.z_nm[rows]
    w = atoms.width_nm[rows]

    z_first, z_count = _patches(z_i, w, h, k0, n_z, half_widths)
    span_z = int(z_count.max())
    z_index = z_first[:, None] + np.arange(span_z)[None, :]
    z_inside = np.arange(span_z)[None, :] < z_count[:, None]
    z_nodes = (k0 + z_index) * h
    z_values = np.where(z_inside, np.exp(-(((z_nodes - z_i[:, None]) / w[:, None]) ** 2)), 0.0)
    z_sum = np.sum(z_values * trapezium_factor(z_index, n_z), axis=1)

    r_first, r_count = _patches(r_i, w, h, 0, n_r, half_widths)
    span_r = int(r_count.max())
    r_index = r_first[:, None] + np.arange(span_r)[None, :]
    r_inside = np.arange(span_r)[None, :] < r_count[:, None]
    r_nodes = r_index * h
    gaussian = np.exp(-(((r_nodes - r_i[:, None]) / w[:, None]) ** 2))
    bessel = i0e(2.0 * r_nodes * r_i[:, None] / w[:, None] ** 2)
    r_values = np.where(r_inside, 2.0 * math.pi * r_nodes * gaussian * bessel, 0.0)
    r_sum = np.sum(r_values * trapezium_factor(r_index, n_r), axis=1)
    return (z_first, z_values, z_sum), (r_first, r_values, r_sum)


def volume_density(
    r_nm: np.ndarray, z_nm: np.ndarray, r_i: float, z_i: float, width_nm: float
) -> np.ndarray:
    """Return the closed form of one unit atom's charge density, in nm^-3."""
    import numpy as np
    from scipy.special import i0e

    radius = np.abs(np.asarray(r_nm, dtype=np.float64))
    axial = np.asarray(z_nm, dtype=np.float64) - z_i
    return np.asarray(
        math.pi**-1.5
        * width_nm**-3
        * np.exp(-(((radius - r_i) ** 2) + axial**2) / width_nm**2)
        * i0e(2.0 * radius * r_i / width_nm**2)
    )


def areal_density(
    r_nm: np.ndarray, z_nm: np.ndarray, r_i: float, z_i: float, width_nm: float
) -> np.ndarray:
    """Return 2 pi r times volume_density, in nm^-2: what the lattice samples."""
    import numpy as np

    radius = np.asarray(r_nm, dtype=np.float64)
    return np.asarray(2.0 * math.pi * radius * volume_density(radius, z_nm, r_i, z_i, width_nm))


def atom_lattice_sum(
    r_nm: float,
    z_nm: float,
    width_nm: float,
    spacing_nm: float,
    *,
    half_widths: float = PATCH_HALF_WIDTHS,
) -> float:
    """Return one unit atom's trapezoid sum on the lattice, before renormalisation."""
    import numpy as np

    atoms = SourceAtoms(
        r_nm=np.array([r_nm]),
        z_nm=np.array([z_nm]),
        width_nm=np.array([width_nm]),
        weight_e=np.array([1.0]),
        frame=np.zeros(1, dtype=np.int64),
        atom=np.zeros(1, dtype=np.int64),
        frames=1,
        shift_z_nm=0.0,
    )
    n_r, k0, n_z = lattice_axes(atoms, spacing_nm, half_widths=half_widths)
    (_, _, z_sum), (_, _, r_sum) = _factors(
        atoms, np.arange(1), spacing_nm, n_r, k0, n_z, half_widths
    )
    return float(math.pi**-1.5 * width_nm**-3 * z_sum[0] * r_sum[0] * spacing_nm**2)


@dataclass(frozen=True)
class KernelLattice:
    """The summed kernel on the export lattice, and what the sum measured.

    Parameters
    ----------
    raw_deviation
        The largest deviation of an atom's unrenormalised lattice sum from 1, and its atom.
    """

    grid: RadialGrid
    atoms: SourceAtoms
    spacing_nm: float
    half_widths: float
    renormalised: bool
    raw_deviation: tuple[float, int]

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the charge-grid artefact's record of the sum."""
        deviation, row = self.raw_deviation
        return {
            "kernel": KERNEL_ID,
            "grid": self.grid.descriptor(),
            "grid_digest": self.grid.digest(),
            "atoms": self.atoms.count,
            "frames": self.atoms.frames,
            "q_net_e": self.atoms.q_net_e(),
            "absolute_charge_e": self.atoms.absolute_charge_e(),
            "frame_shift_nm": self.atoms.shift_z_nm,
            "patch_half_widths": self.half_widths,
            "renormalisation": {
                "largest_correction": deviation,
                "atom": self.atoms.label(row) if self.atoms.count else None,
            },
        }


def kernel_parameters(
    *, sharpness: float, spacing_nm: float, shift_z_nm: float
) -> dict[str, Canonicalisable]:
    """Return the charge-grid key's parameters: everything that moves a lattice value."""
    return {
        "kernel": KERNEL_ID,
        "sharpness": sharpness,
        "grid_spacing_nm": spacing_nm,
        "patch_half_widths": PATCH_HALF_WIDTHS,
        "frame_shift_nm": shift_z_nm,
        "lattice_record": LATTICE_RECORD,
    }


def sum_kernel(
    atoms: SourceAtoms,
    spacing_nm: float,
    *,
    half_widths: float = PATCH_HALF_WIDTHS,
    renormalise: bool = True,
    cancel: CancelToken | None = None,
    progress: Progress | None = None,
) -> KernelLattice:
    """Sum the closed-form kernel of every atom on the export lattice.

    Parameters
    ----------
    renormalise
        Scale each atom's sum to its charge; False only for a broken construction under test.
    """
    import numpy as np

    started = time.perf_counter()
    check_charged(atoms)
    check_spacing(atoms, spacing_nm)
    h = spacing_nm
    # The box is 6 w_max beyond the atoms whatever the patch: a narrower patch
    # is a broken construction under test, not a smaller lattice.
    n_r, k0, n_z = lattice_axes(atoms, h)
    values = np.zeros((n_z, n_r), dtype=np.float64)
    worst = (0.0, 0)
    normalisation = math.pi**-1.5 * atoms.width_nm**-3 * h**2
    for frame in range(atoms.frames):
        check_cancelled(cancel, f"summing the kernel of frame {frame}")
        report(progress, frame / atoms.frames, f"summing frame {frame + 1} of {atoms.frames}")
        rows = np.flatnonzero(atoms.frame == frame)
        if rows.size == 0:
            continue
        tile_z = np.floor(atoms.z_nm[rows] / TILE_NM).astype(np.int64)
        tile_r = np.floor(atoms.r_nm[rows] / TILE_NM).astype(np.int64)
        order = np.lexsort((tile_r, tile_z))
        keys = np.stack([tile_z[order], tile_r[order]], axis=1)
        breaks = np.flatnonzero(np.any(np.diff(keys, axis=0) != 0, axis=1)) + 1
        for tile in np.split(rows[order], breaks):
            (z_first, z_values, z_sum), (r_first, r_values, r_sum) = _factors(
                atoms, tile, h, n_r, k0, n_z, half_widths
            )
            raw = normalisation[tile] * z_sum * r_sum
            deviation = np.abs(raw - 1.0)
            at = int(np.argmax(deviation))
            if float(deviation[at]) > worst[0]:
                worst = (float(deviation[at]), int(tile[at]))
            # C m^-2 per unit Z R: the atom's charge over its lattice sum, whose
            # h^2 is in m^2; or the analytic constant pi^-3/2 w^-3 in m^-3 times
            # the r in m that R carries.
            charge_C = atoms.weight_e[tile] * ELEMENTARY_CHARGE
            if renormalise:
                scale = charge_C / (z_sum * r_sum * (h * NM_TO_M) ** 2)
            else:
                scale = charge_C * math.pi**-1.5 * (atoms.width_nm[tile] * NM_TO_M) ** -3 * NM_TO_M
            _accumulate(values, z_first, z_values * scale[:, None], r_first, r_values)
    grid = RadialGrid(origin_nm=(0.0, k0 * h), spacing_nm=(h, h), values=values)
    seconds = time.perf_counter() - started
    report(progress, 1.0, f"{atoms.count} charged atoms summed in {seconds:.1f} s")
    logger.info(
        "kernel sum: %d charged atoms over %d frames in %.3f s", atoms.count, atoms.frames, seconds
    )
    return KernelLattice(
        grid=grid,
        atoms=atoms,
        spacing_nm=h,
        half_widths=half_widths,
        renormalised=renormalise,
        raw_deviation=worst,
    )


def _accumulate(
    values: np.ndarray,
    z_first: np.ndarray,
    z_values: np.ndarray,
    r_first: np.ndarray,
    r_values: np.ndarray,
) -> None:
    n_z, n_r = values.shape
    z_low = int(z_first.min())
    z_high = int((z_first + z_values.shape[1]).max())
    r_low = int(r_first.min())
    r_high = int((r_first + r_values.shape[1]).max())
    z_window = _scatter(z_first - z_low, z_values, z_high - z_low)
    r_window = _scatter(r_first - r_low, r_values, r_high - r_low)
    z_end, r_end = min(z_high, n_z), min(r_high, n_r)
    product = z_window.T @ r_window
    values[z_low:z_end, r_low:r_end] += product[: z_end - z_low, : r_end - r_low]


def _scatter(first: np.ndarray, values: np.ndarray, length: int) -> np.ndarray:
    import numpy as np

    atoms, span = values.shape
    window = np.zeros((atoms, length + span), dtype=np.float64)
    columns = first[:, None] + np.arange(span)[None, :]
    window[np.arange(atoms)[:, None], columns] = values
    return window[:, :length]

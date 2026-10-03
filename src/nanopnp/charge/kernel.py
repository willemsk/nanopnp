"""PHY-16 steps 4-6 on the export lattice: the closed-form azimuthal kernel, summed (FR-13, WP28).

Each atom's normalised 3D Cartesian Gaussian of width ``w_i = sharpness * R_i``,
averaged over the azimuth in closed form (PHY-16 step 5, §8.2.4 D2), is

``rho_i(r, z) = q_i e pi^(-3/2) w_i^-3 exp(-((r - r_i)^2 + (z - z_i)^2)/w_i^2) I0e(2 r r_i/w_i^2)``,

and it factorises: ``2 pi r rho_i = c_i Z_i(z) R_i(r)`` with
``Z_i = exp(-(z - z_i)^2/w^2)`` and ``R_i = 2 pi r exp(-(r - r_i)^2/w^2) I0e(...)``.
Neither factor overflows, even at ``2 r r_i/w^2 ~ 1e6``: ``I0e`` carries the
``e^-x`` that ``exp(-(r - r_i)^2/w^2)`` would otherwise have to cancel
(WP28 *Design* §1). No 3D grid is built (PHY-17 is kept because the smearing *is*
3D; the closed form is its exact limit).

**The lattice is the export and the producer leg's grid** (PHY-16 step 6). It is
uniform at ``charge.smearing.grid_spacing_nm``, carries a node on ``r = 0``, puts
its ``z`` nodes on integer multiples of the spacing, and extends ``6 w_max``
beyond the atoms, snapped outward. Its values are the areal density
``2 pi r rho_pore`` in C m^-2, the quantity a supplied ``rhoq_pore`` carries, so
the lattice reads back through ``inputs.charge`` (D11).

**Each atom is renormalised on the lattice** to ``q_i e / n_frames`` (PHY-18's
renormalisation, the PHY-16 NOTE on the deposition). Its patch is a square of
half-width ``6 w_i``, which leaves out ``1 - erf(6)^2 = 4.3e-17`` of it, and its
trapezoid sum is the product of two 1D sums because the kernel is separable.
Off the axis the trapezoid rule is exact to 1e-15; within a few ``w`` of the axis
it is short by ``h^2/(6 w^2)`` (`.knowledge/04` §3.3), which is what the
renormalisation removes and what VER-01's producer leg guards.

**A frame is a sum of rank-one patches**, ``Z_i (x) R_i``, accumulated tile by
tile: atoms are binned into ``(z, r)`` tiles of :data:`TILE_NM`, and each tile is
one dense product of its patches' factors into the window they cover, so the
cost is about ``(tile + 12 w)^2 / h^2`` multiply-adds per atom rather than the
whole lattice per atom (*Design* §6).
"""

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
from nanopnp.density.grid import RadialGrid

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.charge.protonation import ProtonationTable

__all__ = [
    "KERNEL_ID",
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
"""The kernel of PHY-16 step 5, named in the charge-grid key (D7).

A different kernel -- the reference's 2D ``(r, z)`` Gaussian divided by ``2 pi r``,
which PHY-17 forbids -- would be a different identifier, never a different number
under this one.
"""

PATCH_HALF_WIDTHS = 6.0
"""Each atom's patch half-width, in units of its ``w_i`` (PHY-16 NOTE on the deposition).

``1 - erf(6)^2 = 4.3e-17`` of the atom lies outside the square, below the
round-off of its own renormalisation.
"""

TILE_NM = 0.5
"""Edge of the ``(z, r)`` tiles atoms are binned into for the dense products, in nm.

A cost choice and not a number-changing one beyond summation order: the window a
tile covers is ``TILE_NM + 12 w_max`` on a side, so smaller tiles shrink the
products until the patches dominate (*Design* §6).
"""

PLANE_COUNT = 12
"""Planes the per-plane check is evaluated at, spanning the atoms' z-extent (D6)."""

NM_TO_M = 1e-9
"""Metres per nanometre."""


# -- the source atoms -----------------------------------------------------------


@dataclass(frozen=True)
class SourceAtoms:
    """Every charged atom of every frame, in the model frame, as the kernel sums it.

    Atoms of zero charge are left out (PHY-16 NOTE on the deposition). Each atom
    carries ``q_i / n_frames``, so the frames' mean is a plain sum over the rows.

    Parameters
    ----------
    r_nm, z_nm
        ``r_i = (x_i^2 + y_i^2)^(1/2)`` and ``z_i`` shifted into the model frame.
    width_nm
        ``w_i = sharpness * R_i``.
    weight_e
        ``q_i / n_frames``, in e.
    frame, atom
        The frame each row came from, and its index into the protonation table's
        concatenated atom arrays, so that a diagnostic can name it.
    frames
        ``n_frames``.
    shift_z_nm
        The ``centre_z_nm`` subtracted from every ``z`` (0 beside a supplied mesh).
    table
        The protonation table the rows were read from.
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
        """Number of charged atoms over every frame."""
        return int(self.r_nm.size)

    def q_net_e(self) -> float:
        """Return ``Q_net``, the mean over frames of ``sum q_i``, in e."""
        return math.fsum(self.weight_e.tolist())

    def absolute_charge_e(self) -> float:
        """Return the mean over frames of ``sum |q_i|``, in e."""
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
        """Return the smallest and largest atom-centre ``z``, in nm."""
        return float(self.z_nm.min()), float(self.z_nm.max())

    def planes_nm(self, count: int = PLANE_COUNT) -> tuple[float, ...]:
        """Return ``count`` planes spanning the atoms' z-extent, ends excluded (D6)."""
        low, high = self.z_extent_nm()
        step = (high - low) / (count + 1)
        return tuple(low + step * (index + 1) for index in range(count))

    def cumulative_e(
        self, planes_nm: tuple[float, ...], *, smoothing_nm: float = PLANE_SMOOTHING_NM
    ) -> tuple[float, ...]:
        """Return each plane's charge under ``1/2 erfc((z - p)/s)``, in closed form, in e.

        Azimuthal averaging keeps each atom's z-marginal, a Gaussian of variance
        ``w_i^2/2``, so atom ``i`` contributes ``q_i 1/2 erfc((z_i - p)/sqrt(s^2 + w_i^2))``
        exactly (§4.4 NOTE on the producer path). No discretisation enters: this
        is PHY-19's reference, the source atoms.
        """
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
    """Return the protonation table's charged atoms in the model frame (PHY-16 steps 4-5).

    Parameters
    ----------
    table
        The ``protonation`` artefact's payload, in stage 1's frame.
    sharpness
        ``charge.smearing.sharpness``: ``w_i = sharpness * R_i``.
    shift_z_nm
        ``geometry.membrane.centre_z_nm`` on a case that generates its mesh, as
        stage 5 moves the profile; 0 beside a supplied mesh (D2).
    """
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
    """Refuse a protonation artefact with no charged atom (PHY-16 step 4).

    Raises
    ------
    ChargeFieldError
        If every atom has ``q_i = 0``: there is no fixed charge to deposit, and
        every later gate would name a consequence rather than this cause.
    """
    if atoms.count == 0:
        raise ChargeFieldError(
            "the protonation artefact carries no charged atom (PHY-16 step 4)",
            "every atom has q_i = 0, so there is no fixed charge to deposit",
        )


def check_spacing(atoms: SourceAtoms, spacing_nm: float) -> None:
    """Refuse a lattice spacing above half the smallest kernel width (PHY-16 NOTE, D2).

    ``h <= w/2`` keeps the trapezoid rule's aliasing below ``exp(-4 pi^2) = 7e-18``;
    the default passes at ``w/h = 2.24`` on the CHARMM polar hydrogen.

    Raises
    ------
    ChargeFieldError
        Naming the atom with the smallest width, its width and the spacing.
    """
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
    if spacing_nm > 0.5 * width:
        raise ChargeFieldError(
            "the export lattice does not resolve the narrowest kernel "
            "(charge.smearing.grid_spacing_nm, PHY-16 NOTE on the deposition)",
            f"the spacing is {spacing_nm:g} nm and {atoms.label(narrowest)} has "
            f"w = {width:.6g} nm; the spacing must be at most w/2 = {0.5 * width:.6g} nm",
        )


# -- the lattice ------------------------------------------------------------------


def lattice_axes(
    atoms: SourceAtoms, spacing_nm: float, *, half_widths: float = PATCH_HALF_WIDTHS
) -> tuple[int, int, int]:
    """Return the lattice as ``(n_r, k0, n_z)``: ``r_j = j h`` and ``z_k = (k0 + k) h``.

    ``r`` runs from the axis; both axes reach ``half_widths * w_max`` beyond the
    atoms, snapped outward to the lattice (D2).
    """
    import numpy as np

    reach = half_widths * float(np.max(atoms.width_nm))
    h = spacing_nm
    n_r = math.ceil(float(np.max(atoms.r_nm) + reach) / h) + 1
    k0 = math.floor(float(np.min(atoms.z_nm) - reach) / h)
    k1 = math.ceil(float(np.max(atoms.z_nm) + reach) / h)
    return n_r, k0, k1 - k0 + 1


def _trapezoid(indices: np.ndarray, count: int) -> np.ndarray:
    """Return the trapezoid weight, in units of the spacing, at each lattice index."""
    import numpy as np

    return np.where((indices == 0) | (indices == count - 1), 0.5, 1.0)


def _patches(
    centre_nm: np.ndarray,
    width_nm: np.ndarray,
    spacing_nm: float,
    origin: int,
    count: int,
    half_widths: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return each atom's patch as ``(first index, node count)`` along one axis."""
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
    """Return the ``Z`` and ``R`` factors of the given atoms on their patches.

    Each factor is ``(first index, values[atoms, nodes], trapezoid sums)``, with the
    values zero beyond each atom's own patch and the sums taken with the
    lattice's trapezoid weights in units of ``h``.
    """
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
    z_sum = np.sum(z_values * _trapezoid(z_index, n_z), axis=1)

    r_first, r_count = _patches(r_i, w, h, 0, n_r, half_widths)
    span_r = int(r_count.max())
    r_index = r_first[:, None] + np.arange(span_r)[None, :]
    r_inside = np.arange(span_r)[None, :] < r_count[:, None]
    r_nodes = r_index * h
    gaussian = np.exp(-(((r_nodes - r_i[:, None]) / w[:, None]) ** 2))
    bessel = i0e(2.0 * r_nodes * r_i[:, None] / w[:, None] ** 2)
    r_values = np.where(r_inside, 2.0 * math.pi * r_nodes * gaussian * bessel, 0.0)
    r_sum = np.sum(r_values * _trapezoid(r_index, n_r), axis=1)
    return (z_first, z_values, z_sum), (r_first, r_values, r_sum)


def volume_density(
    r_nm: np.ndarray, z_nm: np.ndarray, r_i: float, z_i: float, width_nm: float
) -> np.ndarray:
    """Return the closed form of PHY-16 step 5 for one unit charge, in nm^-3.

    Evaluated through ``|r|``, which makes it the even extension across the axis
    that the azimuthal mean is: ``exp(-(r^2 + r_i^2)/w^2) I0(2 r r_i/w^2)`` is even
    in ``r``, and ``exp(-(|r| - r_i)^2/w^2) I0e(2 |r| r_i/w^2)`` is the same number
    written so that neither factor overflows.
    """
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
    """Return ``2 pi r`` times :func:`volume_density`, in nm^-2: what the lattice samples."""
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
    """Return one unit atom's trapezoid sum on the lattice, *before* renormalisation.

    ``pi^(-3/2) w^-3 (sum_z tau Z h)(sum_r tau R h)``: 1 to round-off off the
    axis, and short by ``h^2/(6 w^2)`` beside it (`.knowledge/04` §3.3). The
    renormalisation divides by exactly this.
    """
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
    grid
        The areal density ``2 pi r rho_pore`` in C m^-2 on the lattice.
    atoms
        The source atoms it was summed from.
    spacing_nm, half_widths, renormalised
        How it was built.
    raw_deviation
        The largest ``|S_i - 1|`` of the atoms' unrenormalised lattice sums, and
        the atom it belongs to: what the renormalisation removed.

    No wall-clock time is held, so the charge-grid summary is the same for the
    same sum (VER-23, WP32 D15); the time goes to the log.
    """

    grid: RadialGrid
    atoms: SourceAtoms
    spacing_nm: float
    half_widths: float
    renormalised: bool
    raw_deviation: tuple[float, int]

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the charge-grid artefact's record of the sum (FR-25)."""
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
    """Return the charge-grid key's parameters (D7): everything that moves a lattice value."""
    return {
        "kernel": KERNEL_ID,
        "sharpness": sharpness,
        "grid_spacing_nm": spacing_nm,
        "patch_half_widths": PATCH_HALF_WIDTHS,
        "frame_shift_nm": shift_z_nm,
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
    """Sum the closed-form kernel of every atom on the export lattice (PHY-16 steps 5-6).

    Parameters
    ----------
    atoms
        The source atoms, in the model frame.
    spacing_nm
        The lattice spacing; :func:`check_spacing` is applied first.
    half_widths
        The patch half-width in units of ``w_i``.
    renormalise
        Scale each atom's lattice sum to ``q_i e / n_frames``. Off only to build
        the broken construction VER-01's producer leg must fail (*Design* §5).
    cancel, progress
        Checked and reported between frames (D12).

    Raises
    ------
    ChargeFieldError
        From :func:`check_spacing`, or for a case with no charged atom.
    nanopnp.core.stages.Cancelled
        If ``cancel`` turns true between frames.
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
    """Add the rank-one patches ``sum_i Z_i (x) R_i`` into ``values[z, r]``, in place.

    One dense product over the window the patches cover, clipped to the lattice,
    beyond which every factor is zero. Each factor is ``(first index, values[atoms,
    nodes])`` along its axis, as :func:`_factors` returns it.
    """
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
    """Return ``values[atoms, nodes]`` placed at ``first + node`` in an ``(atoms, length)`` array.

    The nodes beyond a patch hold zeros and may fall past ``length``, where they
    are dropped.
    """
    import numpy as np

    atoms, span = values.shape
    window = np.zeros((atoms, length + span), dtype=np.float64)
    columns = first[:, None] + np.arange(span)[None, :]
    window[np.arange(atoms)[:, None], columns] = values
    return window[:, :length]

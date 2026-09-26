"""The probe-radius profile that stage 4's radius band is gated against (§8.2.2 B5, WP20 D11).

At a height z on the axis, the largest sphere centred at ``(0, 0, z)`` that clears
every atom's radius has radius

    R_p(z) = min_i ( |x_i - (0, 0, z)| - R_i ),

taken over every atom of one frame. The stage-3 map is the mean of the per-frame
maps (WP19 D4), so the profile gated against it is the mean of the per-frame
profiles, not the profile of a mean structure. ``R_i`` is the radius the density
kernel gave the same atom, so the two quantities describe one set of spheres.

This is HOLE's radius on a fixed, straight path, the Cₙ axis, and it needs
nothing but NumPy; ``mdahole2`` stays an optional cross-check (§8.2.2 B5). A
negative value means an atom's sphere reaches the axis, which is a closed lumen.

The cost is frames x atoms x planes distances, batched per frame and bounded in
memory by :data:`CHUNK_ELEMENTS`: 7.8e8 for the 50-frame ClyA-AS ensemble, a few
seconds (WP20 plan, Design §5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nanopnp.core.stages import CancelToken, Progress, check_cancelled, report

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

CHUNK_ELEMENTS = 4_000_000
"""Planes x atoms held at once: 32 MB of float64, whatever the ensemble's size."""


def probe_radius_profile(
    positions_nm: np.ndarray,
    radii_nm: np.ndarray,
    z_nm: np.ndarray,
    *,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
) -> np.ndarray:
    """Return the frame-mean probe radius ``R_p`` at each height, in nm.

    Parameters
    ----------
    positions_nm
        ``(frames, atoms, 3)``, in the stage-1 frame: the Cₙ axis on z at r = 0.
    radii_nm
        One radius per atom, the density kernel's.
    z_nm
        The heights to evaluate at, along the axis.
    progress, cancel
        Reported and checked once per frame.

    Returns
    -------
    numpy.ndarray
        ``R_p`` at each entry of ``z_nm``, averaged over the frames.

    Raises
    ------
    ValueError
        If the radii do not match the atoms, or there is no frame or no atom.
    nanopnp.core.stages.Cancelled
        If ``cancel`` turns true between frames.
    """
    import numpy as np

    positions = np.asarray(positions_nm)
    radii = np.asarray(radii_nm, dtype=np.float64)
    planes = np.asarray(z_nm, dtype=np.float64).reshape(-1)
    if positions.ndim != 3 or positions.shape[2] != 3:
        raise ValueError(f"positions have shape {positions.shape}, not (frames, atoms, 3)")
    frames, atoms, _ = positions.shape
    if frames == 0 or atoms == 0:
        raise ValueError(f"the probe needs at least one frame and one atom, got {positions.shape}")
    if radii.shape != (atoms,):
        raise ValueError(f"{radii.size} radii for {atoms} atoms")
    step = max(1, CHUNK_ELEMENTS // atoms)
    total = np.zeros(planes.size)
    for frame in range(frames):
        check_cancelled(cancel, f"the probe profile of frame {frame + 1} of {frames}")
        coordinates = positions[frame].astype(np.float64)
        radial = coordinates[:, 0] ** 2 + coordinates[:, 1] ** 2
        axial = coordinates[:, 2]
        for first in range(0, planes.size, step):
            window = planes[first : first + step]
            gap = window[:, None] - axial[None, :]
            clearance = np.sqrt(radial[None, :] + gap * gap) - radii[None, :]
            total[first : first + step] += clearance.min(axis=1)
        report(progress, (frame + 1) / frames, f"probe profile of frame {frame + 1} of {frames}")
    profile: np.ndarray = total / frames
    return profile

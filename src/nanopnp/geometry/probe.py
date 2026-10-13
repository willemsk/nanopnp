"""The probe-radius profile that stage 4's radius band is gated against."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nanopnp.core.stages import CancelToken, Progress, check_cancelled, report

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

CHUNK_ELEMENTS = 4_000_000


def probe_radius_profile(
    positions_nm: np.ndarray,
    radii_nm: np.ndarray,
    z_nm: np.ndarray,
    *,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
) -> np.ndarray:
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

"""The dielectric field: a solid fraction, supplied or derived, for the blend to drive."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.fields import (
    ChargeFieldError,
    FieldDocument,
    FieldDocumentError,
    load_document,
    load_grid,
)
from nanopnp.core.typing import Expression, Mesh
from nanopnp.density.grid import RadialGrid, coefficient
from nanopnp.geometry.profile import signed_area

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Iterable, Sequence

    import numpy as np

    from nanopnp.numerics.measures import Measures

SOLID_FRACTION = "solid_fraction"
"""The one quantity an ``inputs.eps_r`` field may declare (§5.3.1 NOTE)."""

SOLID_MEAN_FLOOR = 0.9
"""Least mean ``chi`` over a material the blend sends to ``eps_p``."""

FLUID_MEAN_CEILING = 0.1
"""Greatest mean ``chi`` over a material the blend sends to ``eps_r,f(<c>)``.

An inverted or grossly misregistered field fails these two by construction,
while a 1-2 Angstrom transition moves neither mean by more than a per cent: the
transition is a shell a couple of element widths thick around a body many
nanometres across.
"""

EXCLUSION_MEAN_CEILING = 0.5
"""The mean ``chi`` over ``exclusion`` must be below this, for every ``chi`` (WP30 D6).

The shell lies wholly on the water side of the dielectric contour, so ``chi`` is
below 1/2 throughout it and so is its mean, while an inverted field puts it above.
:data:`FLUID_MEAN_CEILING` does not apply: a 1-2 Angstrom transition into a shell
a few Angstroms wide exceeds it, since a planar shell of width ``a`` averages
``3 delta / (32 a)``, 0.156 at ``delta`` = 0.2 and ``a`` = 0.12 nm (section 4.4
NOTE on the derived solid fraction).
"""

EXCLUSION_MATERIAL = "exclusion"
"""The ion-exclusion shell's material (section 5.3.1 NOTE)."""

DERIVED_SOURCE = "derived"
"""What the stage-7 key and the manifest name a ``chi`` stage 7 derived (WP30 D5)."""

TRANSITION_ID = "cubic-step-over-signed-distance/v1"
"""The derived ``chi``'s construction: ``S(s/delta + 1/2)``, ``S = 3x^2 - 2x^3`` (WP30 D1)."""

LATTICE_DIVISIONS = 20
"""The derived ``chi``'s lattice spacing is ``delta`` over this (WP30 D4).

The bilinear error off the profile's vertices is then at most ``0.75 (h/delta)^2
= 1.9e-3`` (WP30 plan, *Design* section 1, [verified]).
"""

BOX_WIDENING = 1.0
"""The lattice covers the body's bounding box widened by this many ``delta`` (WP30 D4).

``chi`` reaches only ``delta/2`` past the profile, so the box's boundary samples
are 0, as the padding ring is.
"""

PROBE_NM = 1e-6
"""How far outward of a profile piece's midpoint its side is probed, in nm (WP30 D2)."""

MEMBRANE_HOLD_CELLS = 2.0
"""Lattice nodes in the membrane within this many spacings of the body are held at 1 (WP30 D3).

They are the nodes a protein element beside the membrane interpolates from
(WP30 Outcomes, D3).
"""

DERIVED_CONSTANTS: dict[str, object] = {
    "transition": TRANSITION_ID,
    "lattice": f"delta/{LATTICE_DIVISIONS}",
    "widening": f"{BOX_WIDENING:g}delta",
    "probe_nm": PROBE_NM,
    "membrane_hold": f"{MEMBRANE_HOLD_CELLS:g}h",
}
"""Every code constant that moves a sample of the derived ``chi``, as the stage-7 key records it."""


@dataclass(frozen=True)
class MaterialMean:
    material: str
    mean: float
    branch: str
    """``"solid"`` or ``"fluid"``: which side of the blend this material takes."""

    @property
    def within(self) -> bool:
        if self.branch == "solid":
            return self.mean >= SOLID_MEAN_FLOOR
        if self.material == EXCLUSION_MATERIAL:
            return self.mean < EXCLUSION_MEAN_CEILING
        return self.mean <= FLUID_MEAN_CEILING

    @property
    def needs(self) -> str:
        if self.branch == "solid":
            return f">= {SOLID_MEAN_FLOOR:g}"
        if self.material == EXCLUSION_MATERIAL:
            return f"< {EXCLUSION_MEAN_CEILING:g}"
        return f"<= {FLUID_MEAN_CEILING:g}"

    def summary(self) -> dict[str, object]:
        return {"material": self.material, "mean": self.mean, "branch": self.branch}


@dataclass(frozen=True)
class SolidFractionField:
    document: FieldDocument
    grid: RadialGrid
    source: Path

    def __post_init__(self) -> None:
        if self.document.quantity != SOLID_FRACTION:
            raise FieldDocumentError(
                f"inputs.eps_r names quantity {self.document.quantity!r}; a dielectric field "
                f"supplies {SOLID_FRACTION!r}, a fraction in [0, 1] the solver blends as "
                "eps_r = chi * eps_p + (1 - chi) * eps_r,f(<c>) (§4.4 NOTE)"
            )

    def chi(self) -> Expression:
        return coefficient(self.grid)

    def check_range(self) -> None:
        check_range(self.grid, what="the supplied solid fraction")

    def material_means(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        return material_means(self.chi(), mesh, measures, solids=solids)

    def check_materials(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        return check_registration(
            self.material_means(mesh, measures, solids=solids),
            what="the supplied solid fraction",
        )


def check_range(grid: RadialGrid, *, what: str) -> None:
    import numpy as np

    values = grid.values
    # Written so that a NaN sample is outside: ``nan < 0.0`` and ``nan > 1.0``
    # are both False, and it would otherwise pass as a blend weight. It is
    # also ranked worst, so the diagnostic names it rather than a finite one.
    outside = ~((values >= 0.0) & (values <= 1.0))
    if not bool(outside.any()):
        return
    distance = np.where(np.isnan(values), np.inf, np.abs(values - 0.5))
    flat = np.where(outside, distance, -1.0)
    i_z, i_r = np.unravel_index(int(np.argmax(flat)), values.shape)
    raise ChargeFieldError(
        f"{what} leaves [0, 1]",
        f"chi = {float(values[i_z, i_r]):.6g} at the worst of "
        f"{int(outside.sum())} samples. A solid fraction is a blend weight, so a value "
        "outside [0, 1] extrapolates the permittivity beyond both branches (§4.4 NOTE)",
        f"(r, z) = ({float(grid.r_nm[i_r]):.4g}, {float(grid.z_nm[i_z]):.4g}) nm",
    )


def material_means(
    chi: Expression, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
) -> tuple[MaterialMean, ...]:
    import ngsolve as ngs

    solid_set = set(solids)
    means: list[MaterialMean] = []
    for material in sorted(set(mesh.GetMaterials())):
        region = mesh.Materials(material)
        volume = measures.integrate(
            ngs.CF(1.0), mesh, definedon=region, what=f"the volume of {material!r}"
        )
        if volume <= 0.0:  # pragma: no cover - an empty material cannot be selected
            continue
        total = measures.integrate(
            chi, mesh, definedon=region, what=f"the solid fraction over {material!r}"
        )
        means.append(
            MaterialMean(
                material=material,
                mean=total / volume,
                branch="solid" if material in solid_set else "fluid",
            )
        )
    return tuple(means)


def check_registration(means: tuple[MaterialMean, ...], *, what: str) -> tuple[MaterialMean, ...]:
    failed = [mean for mean in means if not mean.within]
    if not failed:
        return means
    rendered = ", ".join(
        f"{mean.material!r} averages chi = {mean.mean:.4g} and takes the {mean.branch} "
        f"branch, which needs {mean.needs}"
        for mean in failed
    )
    raise ChargeFieldError(
        f"{what} does not register with the mesh's materials",
        f"{rendered}. A field written with r and z transposed, or with its sense inverted, "
        "fails this by construction; a 1-2 Angstrom transition moves no mean by a per cent",
    )


def load_solid_fraction(path: str | Path) -> SolidFractionField:
    source = Path(path)
    document = load_document(source)
    return SolidFractionField(
        document=document, grid=load_grid(document, base=source.parent), source=source
    )


def summary(field: SolidFractionField, means: Sequence[MaterialMean]) -> dict[str, object]:
    return {
        **field.document.summary(),
        "grid": field.grid.descriptor(),
        "grid_digest": field.grid.digest(),
        "material_means": [mean.summary() for mean in means],
        "interpolation": "bilinear",
    }


def smooth_step(x: np.ndarray) -> np.ndarray:
    import numpy as np

    clipped = np.clip(x, 0.0, 1.0)
    result: np.ndarray = clipped * clipped * (3.0 - 2.0 * clipped)
    return result


def _in_membrane(
    r_nm: np.ndarray,
    z_nm: np.ndarray,
    *,
    half_thickness_nm: float,
    inner_trans_nm: float,
    inner_cis_nm: float,
) -> np.ndarray:
    import numpy as np

    fraction = (z_nm + half_thickness_nm) / (2.0 * half_thickness_nm)
    chord = inner_trans_nm + (inner_cis_nm - inner_trans_nm) * fraction
    inside: np.ndarray = (np.abs(z_nm) < half_thickness_nm) & (r_nm > chord)
    return inside


def water_facing(
    points: np.ndarray,
    *,
    half_thickness_nm: float,
    inner_trans_nm: float,
    inner_cis_nm: float,
) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np

    loop = np.asarray(points, dtype=np.float64)
    if signed_area(loop) < 0.0:
        loop = loop[::-1]
    pieces: list[tuple[np.ndarray, np.ndarray]] = []
    for start, end in zip(loop, np.roll(loop, -1, axis=0), strict=True):
        cuts = [0.0, 1.0]
        dz = end[1] - start[1]
        if dz != 0.0:
            for plane in (-half_thickness_nm, half_thickness_nm):
                t = (plane - start[1]) / dz
                if 0.0 < t < 1.0:
                    cuts.append(float(t))
        cuts.sort()
        for t0, t1 in pairwise(cuts):
            pieces.append((start + t0 * (end - start), start + t1 * (end - start)))
    segments = np.asarray([[a, b] for a, b in pieces], dtype=np.float64)
    span = segments[:, 1] - segments[:, 0]
    length = np.hypot(span[:, 0], span[:, 1])
    # Counter-clockwise, so the body is on the left and outward is the right normal.
    outward = np.stack([span[:, 1], -span[:, 0]], axis=1) / length[:, None]
    probe = 0.5 * (segments[:, 0] + segments[:, 1]) + PROBE_NM * outward
    membrane = _in_membrane(
        probe[:, 0],
        probe[:, 1],
        half_thickness_nm=half_thickness_nm,
        inner_trans_nm=inner_trans_nm,
        inner_cis_nm=inner_cis_nm,
    )
    return segments[~membrane], segments[membrane]


def _inside(loop: np.ndarray, r_nm: np.ndarray, z_nm: np.ndarray) -> np.ndarray:
    import numpy as np

    starts, ends = loop, np.roll(loop, -1, axis=0)
    low = np.minimum(starts[:, 1], ends[:, 1])
    high = np.maximum(starts[:, 1], ends[:, 1])
    inside = np.zeros((z_nm.size, r_nm.size), dtype=bool)
    for row, z in enumerate(z_nm):
        crossing = (low <= z) & (z < high)
        if not bool(crossing.any()):
            continue
        s0, s1 = starts[crossing], ends[crossing]
        at = s0[:, 0] + (z - s0[:, 1]) * (s1[:, 0] - s0[:, 0]) / (s1[:, 1] - s0[:, 1])
        count = np.searchsorted(np.sort(at), r_nm, side="left")
        inside[row] = count % 2 == 1
    return inside


def _band_distance(
    segments: np.ndarray,
    r_nm: np.ndarray,
    z_nm: np.ndarray,
    band_nm: float,
) -> np.ndarray:
    import numpy as np

    distance = np.full((z_nm.size, r_nm.size), np.inf)
    r0, h_r = float(r_nm[0]), float(r_nm[1] - r_nm[0])
    z0, h_z = float(z_nm[0]), float(z_nm[1] - z_nm[0])
    for a, b in segments:
        i0 = max(0, int(np.floor((min(a[0], b[0]) - band_nm - r0) / h_r)))
        i1 = min(r_nm.size, int(np.ceil((max(a[0], b[0]) + band_nm - r0) / h_r)) + 1)
        j0 = max(0, int(np.floor((min(a[1], b[1]) - band_nm - z0) / h_z)))
        j1 = min(z_nm.size, int(np.ceil((max(a[1], b[1]) + band_nm - z0) / h_z)) + 1)
        if i0 >= i1 or j0 >= j1:
            continue
        rr, zz = np.meshgrid(r_nm[i0:i1], z_nm[j0:j1])
        span = b - a
        length_squared = float(span @ span)
        t = ((rr - a[0]) * span[0] + (zz - a[1]) * span[1]) / max(length_squared, 1e-300)
        t = np.clip(t, 0.0, 1.0)
        found = np.hypot(rr - (a[0] + t * span[0]), zz - (a[1] + t * span[1]))
        window = distance[j0:j1, i0:i1]
        np.minimum(window, found, out=window)
    return distance


def derive_solid_fraction(
    points: np.ndarray,
    *,
    half_thickness_nm: float,
    inner_trans_nm: float,
    inner_cis_nm: float,
    transition_nm: float,
) -> RadialGrid:
    import numpy as np

    loop = np.asarray(points, dtype=np.float64)
    spacing = transition_nm / LATTICE_DIVISIONS
    widening = BOX_WIDENING * transition_nm
    r_low = max(0.0, float(loop[:, 0].min()) - widening)
    r_high = float(loop[:, 0].max()) + widening
    z_low = float(loop[:, 1].min()) - widening
    z_high = float(loop[:, 1].max()) + widening
    r_nm = r_low + spacing * np.arange(int(np.ceil((r_high - r_low) / spacing)) + 1)
    z_nm = z_low + spacing * np.arange(int(np.ceil((z_high - z_low) / spacing)) + 1)

    water, membrane_facing = water_facing(
        loop,
        half_thickness_nm=half_thickness_nm,
        inner_trans_nm=inner_trans_nm,
        inner_cis_nm=inner_cis_nm,
    )
    inside = _inside(loop, r_nm, z_nm)
    distance = _band_distance(water, r_nm, z_nm, 0.5 * transition_nm + 2.0 * spacing)
    # In place, so that the lattice-sized temporaries are the distance, the sign
    # and the values (76 MB each at delta = h_c on 2WCD). The step is
    # :func:`smooth_step`'s ``x^2 (3 - 2x)``, operation for operation, so the samples are its bits.
    np.negative(distance, out=distance, where=~inside)
    distance /= transition_nm
    distance += 0.5
    np.clip(distance, 0.0, 1.0, out=distance)
    values = distance * distance
    distance *= -2.0
    distance += 3.0
    values *= distance
    del distance

    hold = MEMBRANE_HOLD_CELLS * spacing
    near = _band_distance(membrane_facing, r_nm, z_nm, hold) <= hold
    near &= ~inside
    near &= _in_membrane(
        r_nm[None, :],
        z_nm[:, None],
        half_thickness_nm=half_thickness_nm,
        inner_trans_nm=inner_trans_nm,
        inner_cis_nm=inner_cis_nm,
    )
    values[near] = 1.0
    return RadialGrid.from_axes(r_nm, z_nm, values)


@dataclass(frozen=True)
class DerivedSolidFraction:
    grid: RadialGrid
    transition_nm: float
    held: tuple[str, ...]
    mesh: Mesh

    def chi(self) -> Expression:
        present = [name for name in self.held if name in set(self.mesh.GetMaterials())]
        lattice = coefficient(self.grid)
        if not present:
            return lattice
        indicator = self.mesh.MaterialCF(dict.fromkeys(present, 1.0), default=0.0)
        return indicator + (1.0 - indicator) * lattice

    def check_range(self) -> None:
        check_range(self.grid, what="the derived solid fraction")

    def material_means(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        return material_means(self.chi(), mesh, measures, solids=solids)

    def check_materials(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        return check_registration(
            self.material_means(mesh, measures, solids=solids),
            what="the derived solid fraction",
        )


def derived_summary(
    field: DerivedSolidFraction, means: Sequence[MaterialMean]
) -> dict[str, object]:
    return {
        "source": DERIVED_SOURCE,
        "transition_nm": field.transition_nm,
        "held_at_one": list(field.held),
        **DERIVED_CONSTANTS,
        "grid": field.grid.descriptor(),
        "grid_digest": field.grid.digest(),
        "material_means": [mean.summary() for mean in means],
        "interpolation": "bilinear",
    }

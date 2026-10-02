"""The supplied dielectric field: a solid fraction, and the blend it drives.

§4.4's NOTE settles what an ``inputs.eps_r`` field is. PHY-20 requires the
transition **to** ``eps_w``, and ``eps_w = eps_r,f0 * eps_r,f^c(<c>)`` is a
function of the solved concentration, so a static ``eps_r`` field cannot express
it: accepting one would silently disable the permittivity correction while the
run continued to report ePNP-NS. A supplied field is therefore a solid fraction
``chi in [0, 1]`` and the permittivity is

``eps_r = chi * eps_p + (1 - chi) * eps_r,f(<c>)``

with the 1-2 Angstrom transition carried by ``chi`` alone. Setting ``chi`` to the
sharp material indicator reproduces PHY-20's piecewise assignment exactly, which
is what makes the smoothed field a refinement of the validated model rather than
a replacement for it — and is the Tier-1 assertion of VER-30.

The header document is :class:`~nanopnp.charge.fields.FieldDocument`, imported
rather than duplicated: one header shape for every quantity keeps the units, the
grid descriptor and the unknown-key rejection in one place, and a second schema
for the dielectric would be a second place for them to drift.

Two gates, both aimed at the failure that actually happens — a field written with
``r`` and ``z`` transposed, or with its sense inverted. Neither is a sampled
check: the range gate is taken on the grid, where it *proves* the mesh statement
rather than testing it at chosen points (see :meth:`SolidFractionField.check_range`).
"""

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

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Iterable, Mapping, Sequence

    import numpy as np

    from nanopnp.physics.measures import Measures

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

DERIVED_CONSTANTS: dict[str, object] = {
    "transition": TRANSITION_ID,
    "lattice": f"delta/{LATTICE_DIVISIONS}",
    "widening": f"{BOX_WIDENING:g}delta",
    "probe_nm": PROBE_NM,
}
"""Every code constant that moves a sample of the derived ``chi``, as the stage-7 key records it."""


@dataclass(frozen=True)
class MaterialMean:
    """The mean of ``chi`` over one material, and which branch it should take."""

    material: str
    mean: float
    branch: str
    """``"solid"`` or ``"fluid"``: which side of the blend this material takes."""

    @property
    def within(self) -> bool:
        """Whether the mean is on the side of the threshold its branch requires.

        ``exclusion`` takes the fluid branch and its own ceiling: below 1/2,
        where the electrolyte's is 0.1 (:data:`EXCLUSION_MEAN_CEILING`).
        """
        if self.branch == "solid":
            return self.mean >= SOLID_MEAN_FLOOR
        if self.material == EXCLUSION_MATERIAL:
            return self.mean < EXCLUSION_MEAN_CEILING
        return self.mean <= FLUID_MEAN_CEILING

    @property
    def needs(self) -> str:
        """The threshold this material's mean is held to, as prose."""
        if self.branch == "solid":
            return f">= {SOLID_MEAN_FLOOR:g}"
        if self.material == EXCLUSION_MATERIAL:
            return f"< {EXCLUSION_MEAN_CEILING:g}"
        return f"<= {FLUID_MEAN_CEILING:g}"

    def summary(self) -> dict[str, object]:
        """Return this mean as plain data, for the FR-25 manifest."""
        return {"material": self.material, "mean": self.mean, "branch": self.branch}


@dataclass(frozen=True)
class SolidFractionField:
    """A supplied solid fraction, ready to blend onto a mesh.

    Parameters
    ----------
    document
        The validated header.
    grid
        Its grid: dimensionless values in ``[0, 1]``.
    source
        The header document's path, for provenance.
    """

    document: FieldDocument
    grid: RadialGrid
    source: Path

    def __post_init__(self) -> None:
        """Refuse a quantity that is not a solid fraction.

        Raises
        ------
        FieldDocumentError
            Naming §4.4's NOTE. An absolute ``eps_r`` never reaches here — the
            header document refuses that quantity by name — so what this catches
            is a *charge* field supplied under ``inputs.eps_r``, which would put
            C m^-2 where a dimensionless fraction belongs.
        """
        if self.document.quantity != SOLID_FRACTION:
            raise FieldDocumentError(
                f"inputs.eps_r names quantity {self.document.quantity!r}; a dielectric field "
                f"supplies {SOLID_FRACTION!r}, a fraction in [0, 1] the solver blends as "
                "eps_r = chi * eps_p + (1 - chi) * eps_r,f(<c>) (§4.4 NOTE)"
            )

    def chi(self) -> Expression:
        """Return the solid fraction as a coefficient function of the mesh.

        Zero outside the grid box, which is the fluid branch: a mesh reaching
        beyond the supplied field is electrolyte there, and continuing by the
        box's edge value would paint a 250 nm reservoir with whatever the grid
        happened to end on (§5.3.1 NOTE).
        """
        return coefficient(self.grid)

    def check_range(self) -> None:
        """Abort unless ``0 <= chi <= 1`` everywhere on the deployed mesh (VER-30).

        Taken on the grid samples, and that is stronger than sampling the mesh:
        bilinear interpolation is a convex combination of the four surrounding
        samples and the padding ring is zero, so an interpolant whose samples all
        lie in ``[0, 1]`` lies in ``[0, 1]`` at every point of every element
        [verified]. A gate evaluated at quadrature points could only ever miss.

        Raises
        ------
        ChargeFieldError
            Naming the offending value and its ``(r, z)`` (QR-12).
        """
        check_range(self.grid, what="the supplied solid fraction")

    def material_means(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        """Return the mean of ``chi`` over every material of ``mesh``.

        Parameters
        ----------
        mesh
            The deployed mesh.
        measures
            The quadrature policy; the mean carries the same ``r`` weight the
            forms do, so it is a volume average and not an area one.
        solids
            The materials the blend sends to ``eps_p`` — the keys of
            ``physics.solid_permittivities``. Everything else takes the fluid
            branch, ``exclusion`` included: it is a solid for Nernst-Planck and
            the flow and ion-free water for Poisson (§5.3.1 NOTE), so a
            water-filled shell with ``chi`` near zero is exactly right there.
        """
        return material_means(self.chi(), mesh, measures, solids=solids)

    def check_materials(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        """Abort unless every material's mean ``chi`` matches its branch (VER-30).

        Returns
        -------
        tuple of MaterialMean
            Every mean, so a caller can record them whether or not they passed.

        Raises
        ------
        ChargeFieldError
            Reporting both numbers — the mean found and the threshold its branch
            requires — for every material that failed. An inverted field fails
            this on every material at once, which is what the message should say.
        """
        return check_registration(
            self.material_means(mesh, measures, solids=solids),
            what="the supplied solid fraction",
        )


# -- the gates, shared by a supplied and a derived chi ----------------------------


def check_range(grid: RadialGrid, *, what: str) -> None:
    """Abort unless every sample of ``grid`` lies in ``[0, 1]`` (VER-30, QR-12).

    See :meth:`SolidFractionField.check_range` for why the samples prove the
    statement about the mesh.

    Raises
    ------
    ChargeFieldError
        Naming ``what``, the offending value and its ``(r, z)``.
    """
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
    """Return the ``r``-weighted mean of ``chi`` over every material of ``mesh``.

    See :meth:`SolidFractionField.material_means` for the branches.
    """
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
    """Abort unless every material's mean ``chi`` matches its branch (VER-30).

    Raises
    ------
    ChargeFieldError
        Reporting the mean found and the threshold for every material that
        failed, naming ``what``.
    """
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
    """Read a field document and its grid, and return the dielectric field.

    Raises
    ------
    FieldDocumentError
        If the document is invalid, disagrees with its data, or names a quantity
        that is not a solid fraction — an absolute ``eps_r`` field among them,
        refused by the header document with §4.4's reasoning.
    """
    source = Path(path)
    document = load_document(source)
    return SolidFractionField(
        document=document, grid=load_grid(document, base=source.parent), source=source
    )


def blend(
    chi: Expression, solid_permittivity: Expression, fluid_permittivity: Expression
) -> Expression:
    """Return §4.4's dielectric blend, ``chi * eps_p + (1 - chi) * eps_r,f(<c>)``.

    Parameters
    ----------
    chi
        The solid fraction, in ``[0, 1]``.
    solid_permittivity
        The piecewise solid branch — the whole ``MaterialCF`` of
        :meth:`nanopnp.physics.models.CoupledModel.permittivity`, not one
        material's constant, so that a mesh with a protein *and* a membrane
        blends each towards its own ``eps_p``. Where ``chi`` is zero its value
        is irrelevant, which is why its fluid default costs nothing.
    fluid_permittivity
        The corrected ``eps_r,f(<c>)/eps_r,f0`` of PHY-11 and PHY-12.

    Returns
    -------
    Expression
        The blended relative permittivity, nondimensionalised exactly as its two
        arguments are. With the sharp material indicator for ``chi`` this is
        identically the piecewise assignment of PHY-20.
    """
    return chi * solid_permittivity + (1.0 - chi) * fluid_permittivity


_NEAREST_SOLID_CACHE = "_nanopnp_nearest_solid_permittivity"
"""Attribute on an NGSolve mesh holding :func:`nearest_solid_permittivity`'s cache."""


def nearest_solid_permittivity(mesh: Mesh, permittivities: Mapping[str, float]) -> Expression:
    """Return the ``eps_p`` the blend goes towards: each solid's own, elsewhere the nearest's.

    §4.4's blend needs an ``eps_p`` wherever ``chi > 0``, and the 1-2 Angstrom
    transition reaches past the mesh boundary into fluid and exclusion elements,
    which carry none of their own. The ``chi`` there is the nearest solid's, so
    its ``eps_p`` is the one the blend goes to; taking any single value instead
    would blend the fluid beside the membrane towards the protein. Nearest by
    element centroid in the meridional plane, which is where the nearest point of
    an axisymmetric body lies. Two solids can tie only where both are within an
    element of the point, and ``chi`` is then the sum of both, so either value is
    within the transition's own resolution.

    Piecewise constant, an ``L2`` order-0 field, because it is a statement about
    which element a point is in. Kept on the mesh, as
    :meth:`nanopnp.solve.gates.FieldSampler.shared` keeps its samplers, so every
    rung's residual reads one field and the cache dies with the mesh.

    Parameters
    ----------
    mesh
        The deployed mesh, in nm.
    permittivities
        Each solid material's nondimensional ``eps_p``, by material name.

    Raises
    ------
    ValueError
        If no material of the mesh is named in ``permittivities``, so that there
        is no solid for a solid fraction to be a fraction of, or if the mesh
        holds a cell that is not a triangle.
    """
    key = tuple(sorted(permittivities.items()))
    cache: dict[tuple[tuple[str, float], ...], Expression] | None = getattr(
        mesh, _NEAREST_SOLID_CACHE, None
    )
    if cache is None:
        cache = {}
        setattr(mesh, _NEAREST_SOLID_CACHE, cache)
    found = cache.get(key)
    if found is not None:
        return found

    import ngsolve as ngs
    import numpy as np
    from scipy.spatial import cKDTree

    names = mesh.GetMaterials()
    elements = mesh.ngmesh.Elements2D().NumPy()
    if not bool(np.all(np.asarray(elements["np"]) == 3)):
        raise ValueError("the nearest-solid permittivity is taken over triangles only")
    # Netgen numbers vertices and face descriptors from one; NGSolve's element
    # order is the Elements2D order, so row i is element i and dof i of L2(0).
    vertices = np.asarray(elements["nodes"])[:, :3] - 1
    coordinates = np.asarray(mesh.ngmesh.Coordinates(), dtype=np.float64)[:, :2]
    centroids = coordinates[vertices].mean(axis=1)
    by_material = np.array([permittivities.get(name, np.nan) for name in names])
    own = by_material[np.asarray(elements["index"]) - 1]
    solid = np.isfinite(own)
    if not bool(solid.any()):
        raise ValueError(
            f"no material of this mesh ({', '.join(sorted(set(names)))}) has a solid "
            "permittivity, so a solid fraction has no eps_p to blend towards (§4.4)"
        )
    values = own.copy()
    if not bool(solid.all()):
        _, nearest = cKDTree(centroids[solid]).query(centroids[~solid])
        values[~solid] = own[solid][nearest]
    field = ngs.GridFunction(ngs.L2(mesh, order=0), name="nearest_solid_permittivity")
    field.vec.FV().NumPy()[:] = values
    cache[key] = field
    return field


def summary(field: SolidFractionField, means: Sequence[MaterialMean]) -> dict[str, object]:
    """Return the FR-25 record of a supplied dielectric field.

    The one place this record is written. :meth:`nanopnp.charge.stage.ResolvedFields.summary`
    adds the header document's own name and digest around it and changes nothing
    inside, so the manifest and the VER-30 assertion read the same dict.
    """
    return {
        **field.document.summary(),
        "grid": field.grid.descriptor(),
        "grid_digest": field.grid.digest(),
        "material_means": [mean.summary() for mean in means],
        "interpolation": "bilinear",
    }


# -- the derived chi (WP30) --------------------------------------------------------


def smooth_step(x: np.ndarray) -> np.ndarray:
    """Return ``S(x) = 3x^2 - 2x^3`` on ``[0, 1]``, 0 below and 1 above (section 4.4 NOTE).

    C1, with ``S(1/2) = 1/2`` and ``|S''| <= 6``.
    """
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
    """Return whether each point is in the membrane quadrilateral's slab, outward of its chord."""
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
    """Return ``W``, the profile's water-facing part, and the rest, as ``(k, 2, 2)`` segments.

    The profile's edges are split at the bilayer planes ``z = +/- t/2``, and a
    piece is water-facing when a point :data:`PROBE_NM` outward of its midpoint
    is not in the membrane (WP30 D2). The membrane is ``M - P``, so off the
    profile a point is membrane exactly when it lies in the quadrilateral.

    Parameters
    ----------
    points
        The model-frame profile, either orientation.
    half_thickness_nm, inner_trans_nm, inner_cis_nm
        The membrane: ``t/2`` and its inner edge's radii on ``z = -t/2`` and
        ``z = +t/2``.

    Returns
    -------
    tuple of numpy.ndarray
        The water-facing pieces and the membrane-facing ones.
    """
    import numpy as np

    from nanopnp.mesh.profile import signed_area

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
    """Return ``[i_z, i_r]``: whether each lattice node is inside the polygon, by scanline.

    Even-odd on each row: an edge crosses the row at ``z`` when
    ``min(z0, z1) <= z < max(z0, z1)``, the half-open rule that counts a vertex on
    the row once, and a node is inside when an odd number of crossings lie at a
    smaller ``r``.
    """
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
    """Return each node's distance to the nearest segment, exact below ``band_nm``, else inf.

    Segment by segment over the window of nodes within ``band_nm`` of its
    bounding box, so the cost is the band's area and not the box's.
    """
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
    """Return the derived ``chi`` sampled on its lattice (section 4.4 NOTE, WP30 D1-D4).

    ``chi = S(s/delta + 1/2)``, with ``s`` the distance to ``W``
    (:func:`water_facing`), positive inside the body. The lattice has spacing
    ``delta/20`` over the body's bounding box widened by ``delta`` and clipped
    at ``r = 0``. Distances are taken only in the band ``|s| < delta/2 + 2h``,
    outside which ``chi`` is 1 inside the body and 0 outside it.

    Nodes outside the body but in the membrane, within ``2h`` of the body, are 1:
    the membrane is held at 1 (D3), and those are the nodes a protein element
    beside the membrane interpolates from. On the mesh the membrane is held at 1
    by its material (:class:`DerivedSolidFraction`), past the box as well.

    Parameters
    ----------
    points
        The model-frame profile.
    half_thickness_nm, inner_trans_nm, inner_cis_nm
        The membrane, as stage 5 recorded it.
    transition_nm
        ``delta``, positive.
    """
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
    signed = np.where(inside, distance, -distance)
    values = smooth_step(signed / transition_nm + 0.5)

    rr, zz = np.meshgrid(r_nm, z_nm)
    held = (
        ~inside
        & _in_membrane(
            rr,
            zz,
            half_thickness_nm=half_thickness_nm,
            inner_trans_nm=inner_trans_nm,
            inner_cis_nm=inner_cis_nm,
        )
        & (_band_distance(membrane_facing, r_nm, z_nm, 2.0 * spacing) <= 2.0 * spacing)
    )
    values[held] = 1.0
    return RadialGrid.from_axes(r_nm, z_nm, values)


@dataclass(frozen=True)
class DerivedSolidFraction:
    """A ``chi`` stage 7 derived from the stage-4 profile, bound to a mesh (WP30 D1-D6).

    Parameters
    ----------
    grid
        The lattice of :func:`derive_solid_fraction`.
    transition_nm
        ``delta``.
    held
        The solid materials held at ``chi = 1``: every one but ``protein`` (D3).
    mesh
        The deployed mesh the material indicator is built on.
    """

    grid: RadialGrid
    transition_nm: float
    held: tuple[str, ...]
    mesh: Mesh

    def chi(self) -> Expression:
        """Return ``chi`` on the mesh: the lattice's, and 1 on every held solid.

        The lattice covers the body's box, and the membrane runs on to the
        reservoir's edge, so the held solids are set by their material rather
        than by the lattice, which is zero past its box.
        """
        present = [name for name in self.held if name in set(self.mesh.GetMaterials())]
        lattice = coefficient(self.grid)
        if not present:
            return lattice
        indicator = self.mesh.MaterialCF(dict.fromkeys(present, 1.0), default=0.0)
        return indicator + (1.0 - indicator) * lattice

    def check_range(self) -> None:
        """Abort unless every lattice sample lies in ``[0, 1]`` (VER-30, QR-12)."""
        check_range(self.grid, what="the derived solid fraction")

    def material_means(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        """Return the mean of ``chi`` over every material of ``mesh``."""
        return material_means(self.chi(), mesh, measures, solids=solids)

    def check_materials(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        """Abort unless every material's mean ``chi`` matches its branch (VER-30, D6)."""
        return check_registration(
            self.material_means(mesh, measures, solids=solids),
            what="the derived solid fraction",
        )


def derived_summary(
    field: DerivedSolidFraction, means: Sequence[MaterialMean]
) -> dict[str, object]:
    """Return the FR-25 record of a derived ``chi``: its construction, its lattice, its means."""
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

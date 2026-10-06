"""VAL-05: a generated pore polygon against the delivered reference polygon (WP22 D1-D8).

One implementation of the comparison serves both legs of section 8.2.2 B2 and the
end-of-phase report, so every number VAL-05 records is computed here once. The
normative contract is the section 7.4 NOTE on VAL-05; the argument is the WP22
plan's Design §1-§4.

**The surface (D2).** Both polygons are in the model frame. The comparison runs on
the mid-planes ``z_k = z_lo + (k + 1/2) h`` over the reference's z extent, 282 of
them for the delivered table at ``h = 0.05`` nm. On each plane the lumen radius is
a polygon's innermost crossing (:func:`~nanopnp.geometry.contour.innermost_crossings`)
and its outer surface is the second crossing
(:func:`~nanopnp.geometry.profile.plane_crossings`). The generated polygon must cross
every plane except within 2h of the reference's tips, where a rounded end one
plane short is admitted; anywhere else a missing plane is refused naming z (QR-12).

**The metric (D3).** With ``Δ = r_ours - r_ref`` and ``r = r_ref`` on the
compared planes, a pore of lumen radius ``r(z)`` in bulk electrolyte has the
series resistance ``∫ dz / (sigma π r²)``, so to first order

    ε_G = 2 Σ (Δ/r) r⁻² / Σ r⁻²

is the relative conductance change on replacing the reference lumen by ours
(Design §1) [verified]. Gated beside it: the rms of Δ, and ``Δr_c``, the
difference of each polygon's own minimum lumen radius over the *trans*
constriction window ``z ∈ [-1.85, 1.6]`` nm (``.knowledge/04`` §2).

**The registration (D6).** The ensemble is already in the MD frame, whose bilayer
centre is z = 0 (G9). Any other structure is placed there by its C-alpha centroid:
``centre_z_nm = z̄_CA - Z_MD``, over residues 8-292 of chains A-L, which both
structures share. Nothing is fitted; :func:`rms_optimal_offset` is a diagnostic.

**The attribution (D7).** The reference was binned by ``pqr2grid`` at a 15 nm
half-extent, whose index-to-radius map writes a feature at radius r at
``r_a = (r/w - 1/2) h`` with ``w/h = (2L + 1)/(2L + h)``, and then hand-edited
(``.knowledge/04`` §1.2, author ruling 14). :func:`attribute_to_construction`
maps our polygon through that erratum and assigns the remainder to the edit.

NumPy is imported inside the functions that use it (``CLAUDE.md``), and so is
stage 4's module, whose scikit-image and shapely import NumPy with them.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from nanopnp.geometry.profile import PoreProfile, load_profile, plane_crossings
from nanopnp.geometry.region import to_model_frame
from nanopnp.io.case import Geometry, load_case
from nanopnp.io.run import run_case
from nanopnp.io.store import Store

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

logger = logging.getLogger(__name__)

Leg = Literal["ensemble", "2wcd"]
"""The two inputs of section 8.2.2 B2."""

PLANE_SPACING_NM = 0.05
"""The comparison planes' spacing: the density grid's h, WP20 Design §7's surface (D2)."""

TIP_BAND_NM = 0.1
"""2h: a plane this close to a reference tip may go uncrossed by the generated polygon (D2)."""

CONSTRICTION_WINDOW_NM = (-1.85, 1.6)
"""The *trans* constriction, in the model frame (``.knowledge/04`` §2), over which r_c is taken."""

Z_MD_NM = 5.655
"""The MD structure's C-alpha centroid z, residues 8-292, over DCD frames 48-97, in the MD frame.

The Tier-3 leg measures it on the 50-frame ensemble mean and asserts it within
:data:`Z_MD_TOLERANCE_NM` (D6). It measures 5.6553 nm. The
5.63 nm first pinned from ``.knowledge/04`` §1.1 was the centroid with residue 7
included (5.6293 nm), and was corrected as D6 provides (``SPECIFICATION.md`` §8.2.4 D7).
"""

Z_MD_TOLERANCE_NM = 0.01
"""How far the measured MD centroid may lie from :data:`Z_MD_NM` before the constant is wrong."""

REGISTRATION_RESIDUES = (8, 292)
"""The residues 2WCD and the MD structure share; the MD's residue 7 is excluded (Design §3)."""

REGISTRATION_CHAINS = tuple("ABCDEFGHIJKL")
"""The dodecamer's chains."""

PQR2GRID_HALF_EXTENT_NM = 15.0
"""The half-extent L the reference was binned at (author ruling 14; ``.knowledge/04`` §1.2)."""

PQR2GRID_SPACING_NM = 0.05
"""The grid spacing h at which the reference was binned (``.knowledge/04`` §1.2)."""

ISOLEVELS = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50)
"""The isolevel sweep of D8, recorded and never used to select (G2)."""


class GeometryComparisonError(ValueError):
    """A VAL-05 comparison could not be made, or failed its leg's tolerance (QR-12)."""


class MissingPlaneError(GeometryComparisonError):
    """The generated polygon does not cross a comparison plane outside the tip band (D2)."""


class GeometryToleranceError(GeometryComparisonError):
    """A gated quantity exceeds its leg's tolerance: names the leg, quantity, value and z."""

    def __init__(self, leg: str, quantity: str, value: str, threshold: str, location: str) -> None:
        self.leg = leg
        self.quantity = quantity
        super().__init__(
            f"VAL-05 ({leg} leg): {quantity} is {value}, above the tolerance {threshold}, "
            f"{location}"
        )


class _Strict(BaseModel):
    """Base for the records here: frozen, and unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class LocatedLength(_Strict):
    """A length and the plane it sits on."""

    value_nm: float
    z_nm: float


class LocatedFraction(_Strict):
    """A dimensionless fraction and the plane it sits on."""

    value: float
    z_nm: float


class Tolerance(_Strict):
    """One leg's gated bounds (section 7.4 NOTE on VAL-05; author ruling 14)."""

    conductance_deviation: float
    """Bound on ``|ε_G|``, as a fraction."""
    constriction_nm: float
    """Bound on ``|Δr_c|``."""
    rms_nm: float
    """Bound on the rms lumen deviation."""


TOLERANCES: Mapping[str, Tolerance] = {
    # Author ruling 14 (SPECIFICATION.md section 7.4 NOTE on VAL-05).
    "ensemble": Tolerance(conductance_deviation=0.05, constriction_nm=0.1, rms_nm=0.1),
    "2wcd": Tolerance(conductance_deviation=0.10, constriction_nm=0.1, rms_nm=0.2),
}
"""Each leg's tolerance: the ensemble's is the Phase 2 gate, 2WCD's is looser (B2)."""


class ProfileComparison(_Strict):
    """One polygon against the reference on the D2 planes: the D3 metric and what is recorded.

    Lengths are in nm. Deviations are ``ours - reference``, so a negative value is
    a narrower lumen, or an outer surface further in.
    """

    planes: int
    """Planes over the reference's extent."""
    compared_planes: int
    """Planes both polygons cross: the sums run over these."""
    uncrossed_planes_nm: list[float]
    """Planes the generated polygon does not cross: only in the tip band, unless not strict."""
    plane_spacing_nm: float

    conductance_deviation: float
    """``ε_G``: the first-order relative bulk-resistor conductance change (gated)."""
    conductance_largest_term: LocatedFraction
    """The plane whose term contributes most to ``ε_G``, and its contribution."""
    conductance_ratio_exact: float
    """``Σ r_ref⁻² / Σ r_ours⁻² - 1``: the exact series value beside the first-order one."""
    rms_nm: float
    """The rms lumen deviation (gated)."""
    mean_nm: float
    max_abs: LocatedLength
    """The largest ``|Δ|`` of the lumen, signed, and where."""

    constriction_ours: LocatedLength
    constriction_reference: LocatedLength
    constriction_difference_nm: float
    """``Δr_c``: each polygon's own minimum over the window, ours minus the reference's (gated)."""
    constriction_window_mean_nm: float
    """The mean lumen Δ over the *trans* constriction window."""
    cis_lumen_mean_nm: float
    """The mean lumen Δ above the window."""

    outer_planes: int
    outer_mean_nm: float
    outer_rms_nm: float
    """The outer surface, each polygon's second crossing, where both have one."""

    tips_ours_nm: tuple[float, float]
    tips_reference_nm: tuple[float, float]

    def check(self, leg: Leg) -> None:
        """Refuse a comparison outside ``leg``'s tolerance, naming the first quantity that is.

        Raises
        ------
        GeometryToleranceError
            Naming the leg, the quantity, its value, the threshold and where it
            sits: the largest contributing plane for ``ε_G``, the two
            constrictions for ``Δr_c``, the largest deviation for the rms.
        """
        bounds = TOLERANCES[leg]
        if not abs(self.conductance_deviation) <= bounds.conductance_deviation:
            term = self.conductance_largest_term
            raise GeometryToleranceError(
                leg,
                "|ε_G|",
                f"{abs(self.conductance_deviation):.2%} (ε_G = {self.conductance_deviation:+.2%})",
                f"{bounds.conductance_deviation:.0%}",
                f"its largest term {term.value:+.3%} at z = {term.z_nm:.3f} nm",
            )
        if not abs(self.constriction_difference_nm) <= bounds.constriction_nm:
            ours, ref = self.constriction_ours, self.constriction_reference
            raise GeometryToleranceError(
                leg,
                "|Δr_c|",
                f"{abs(self.constriction_difference_nm):.4f} nm",
                f"{bounds.constriction_nm:g} nm",
                f"ours {ours.value_nm:.4f} nm at z = {ours.z_nm:.3f} nm against the reference's "
                f"{ref.value_nm:.4f} nm at z = {ref.z_nm:.3f} nm",
            )
        if not self.rms_nm <= bounds.rms_nm:
            worst = self.max_abs
            raise GeometryToleranceError(
                leg,
                "the rms lumen deviation",
                f"{self.rms_nm:.4f} nm",
                f"{bounds.rms_nm:g} nm",
                f"the largest |Δ| {abs(worst.value_nm):.4f} nm at z = {worst.z_nm:.3f} nm",
            )


def _points(polygon: PoreProfile | np.ndarray) -> np.ndarray:
    """Return a polygon's vertices as an ``(n, 2)`` float64 array."""
    import numpy as np

    points = polygon.as_array() if isinstance(polygon, PoreProfile) else polygon
    return np.asarray(points, dtype=np.float64).reshape(-1, 2)


def comparison_planes(
    reference: PoreProfile | np.ndarray, spacing_nm: float = PLANE_SPACING_NM
) -> np.ndarray:
    """Return the D2 mid-planes over the reference's z extent.

    ``z_k = z_lo + (k + 1/2) h`` for ``k = 0 … n - 1``, with ``n`` the extent over
    h, rounded: 282 for the delivered table, from -1.825 to 12.225 nm.
    """
    import numpy as np

    points = _points(reference)
    low, high = float(points[:, 1].min()), float(points[:, 1].max())
    count = round((high - low) / spacing_nm)
    planes: np.ndarray = low + (np.arange(count) + 0.5) * spacing_nm
    # An extent of an odd number of half-spacings rounds up onto the top tip, which
    # the half-open crossing test never counts: keep every plane strictly inside.
    inside: np.ndarray = planes[planes < high]
    return inside


def _in_tip_band(planes: np.ndarray, low: float, high: float, tip_band_nm: float) -> np.ndarray:
    """Return which planes lie within ``tip_band_nm`` of the reference's tips (D2)."""
    band: np.ndarray = (planes - low <= tip_band_nm) | (high - planes <= tip_band_nm)
    return band


def _reference_lumen(reference_points: np.ndarray, planes: np.ndarray) -> np.ndarray:
    """Return the reference's lumen radius on each plane, refusing a plane it does not cross."""
    import numpy as np

    from nanopnp.geometry.contour import innermost_crossings

    r_ref = innermost_crossings([reference_points], planes)
    if not np.all(np.isfinite(r_ref)):
        missing = planes[~np.isfinite(r_ref)]
        raise MissingPlaneError(
            f"the reference polygon does not cross {missing.size} of its own comparison planes, "
            f"the first at z = {missing[0]:.4f} nm"
        )
    return r_ref


def _second_crossings(points: np.ndarray, planes: np.ndarray) -> np.ndarray:
    """Return each plane's second crossing, the outer surface; ``nan`` where there is none."""
    import numpy as np

    values = []
    for z in planes:
        crossings = plane_crossings(points, float(z))
        values.append(crossings[1] if len(crossings) >= 2 else math.nan)
    return np.asarray(values, dtype=np.float64)


def _window_minimum(
    radii: np.ndarray, planes: np.ndarray, window: tuple[float, float]
) -> LocatedLength:
    """Return the minimum of the finite ``radii`` on planes inside ``window``, and where."""
    import numpy as np

    inside = (planes >= window[0]) & (planes <= window[1]) & np.isfinite(radii)
    if not np.any(inside):
        raise GeometryComparisonError(
            f"no crossed plane in the constriction window z ∈ [{window[0]}, {window[1]}] nm"
        )
    index = int(np.argmin(np.where(inside, radii, np.inf)))
    return LocatedLength(value_nm=float(radii[index]), z_nm=float(planes[index]))


def compare_profiles(
    ours: PoreProfile | np.ndarray,
    reference: PoreProfile | np.ndarray,
    *,
    spacing_nm: float = PLANE_SPACING_NM,
    tip_band_nm: float = TIP_BAND_NM,
    constriction_window_nm: tuple[float, float] = CONSTRICTION_WINDOW_NM,
    strict: bool = True,
) -> ProfileComparison:
    """Compare a model-frame polygon with the reference on the D2 planes (D3).

    Parameters
    ----------
    ours
        The generated polygon, in the model frame.
    reference
        The reference polygon, in the model frame; it defines the planes.
    spacing_nm, tip_band_nm, constriction_window_nm
        The plane spacing, the band beside each reference tip in which an
        uncrossed plane is admitted, and the constriction window.
    strict
        D2's rule. ``False`` admits an uncrossed plane anywhere and compares on
        the planes both polygons cross, for a record that is never gated: the
        isolevel sweep, whose high levels shorten the body at both tips (D8).

    Returns
    -------
    ProfileComparison
        The gated quantities and everything recorded beside them.

    Raises
    ------
    MissingPlaneError
        If ``strict`` and ``ours`` leaves a plane outside the tip band
        uncrossed, naming the lowest such z; if ``ours`` crosses no plane at
        all, strict or not; or if the reference itself leaves one uncrossed.
    GeometryComparisonError
        If ``ours`` crosses no plane inside the constriction window, which only
        a comparison that is not ``strict`` can reach.
    """
    import numpy as np

    from nanopnp.geometry.contour import innermost_crossings

    ours_points, reference_points = _points(ours), _points(reference)
    planes = comparison_planes(reference_points, spacing_nm)
    r_ref = _reference_lumen(reference_points, planes)
    r_ours = innermost_crossings([ours_points], planes)
    low, high = float(reference_points[:, 1].min()), float(reference_points[:, 1].max())
    in_band = _in_tip_band(planes, low, high, tip_band_nm)
    uncrossed = ~np.isfinite(r_ours)
    if strict and np.any(uncrossed & ~in_band):
        missing = planes[uncrossed & ~in_band]
        raise MissingPlaneError(
            f"the generated polygon does not cross {missing.size} comparison plane(s) outside the "
            f"{tip_band_nm:g} nm tip band, the first at z = {missing[0]:.4f} nm; it spans "
            f"z = [{ours_points[:, 1].min():.4f}, {ours_points[:, 1].max():.4f}] nm against the "
            f"reference's [{low:.4f}, {high:.4f}] nm in the model frame"
        )

    both = np.isfinite(r_ours)
    if not np.any(both):
        raise MissingPlaneError(
            f"the generated polygon, spanning z = [{ours_points[:, 1].min():.4f}, "
            f"{ours_points[:, 1].max():.4f}] nm, crosses none of the {planes.size} comparison "
            "planes"
        )
    z, r, delta = planes[both], r_ref[both], r_ours[both] - r_ref[both]
    weights = r**-2.0
    terms = 2.0 * (delta / r) * weights / weights.sum()
    largest = int(np.argmax(np.abs(terms)))
    worst = int(np.argmax(np.abs(delta)))
    window = (z >= constriction_window_nm[0]) & (z <= constriction_window_nm[1])
    cis = z > constriction_window_nm[1]

    ours_c = _window_minimum(r_ours, planes, constriction_window_nm)
    reference_c = _window_minimum(r_ref, planes, constriction_window_nm)

    outer_ours = _second_crossings(ours_points, planes)
    outer_ref = _second_crossings(reference_points, planes)
    outer = np.isfinite(outer_ours) & np.isfinite(outer_ref)
    outer_delta = outer_ours[outer] - outer_ref[outer]

    def mean(values: np.ndarray) -> float:
        return float(values.mean()) if values.size else math.nan

    return ProfileComparison(
        planes=int(planes.size),
        compared_planes=int(both.sum()),
        uncrossed_planes_nm=[float(value) for value in planes[uncrossed]],
        plane_spacing_nm=spacing_nm,
        conductance_deviation=float(terms.sum()),
        conductance_largest_term=LocatedFraction(
            value=float(terms[largest]), z_nm=float(z[largest])
        ),
        conductance_ratio_exact=float(weights.sum() / (r_ours[both] ** -2.0).sum() - 1.0),
        rms_nm=float(math.sqrt(float(np.mean(delta * delta)))),
        mean_nm=float(delta.mean()),
        max_abs=LocatedLength(value_nm=float(delta[worst]), z_nm=float(z[worst])),
        constriction_ours=ours_c,
        constriction_reference=reference_c,
        constriction_difference_nm=ours_c.value_nm - reference_c.value_nm,
        constriction_window_mean_nm=mean(delta[window]),
        cis_lumen_mean_nm=mean(delta[cis]),
        outer_planes=int(outer.sum()),
        outer_mean_nm=mean(outer_delta),
        outer_rms_nm=float(math.sqrt(float(np.mean(outer_delta**2)))) if outer.any() else math.nan,
        tips_ours_nm=(float(ours_points[:, 1].min()), float(ours_points[:, 1].max())),
        tips_reference_nm=(low, high),
    )


# -- the registration (D6) -----------------------------------------------------------


def calpha_centroid_z_nm(
    positions_nm: np.ndarray,
    *,
    name: Sequence[str] | np.ndarray,
    resid: Sequence[int] | np.ndarray,
    chain: Sequence[str] | np.ndarray,
    residues: tuple[int, int] = REGISTRATION_RESIDUES,
    chains: Sequence[str] = REGISTRATION_CHAINS,
) -> float:
    """Return the z of the C-alpha centroid over ``residues`` of ``chains``, averaged over frames.

    Parameters
    ----------
    positions_nm
        ``(atoms, 3)`` or ``(frames, atoms, 3)``, in the stage-1 frame. The
        centroid is linear in the positions, so the mean over frames is the
        centroid of the frame-mean structure.
    name, resid, chain
        One entry per atom.
    residues, chains
        The inclusive residue range and the chains that take part.

    Raises
    ------
    GeometryComparisonError
        If no atom is selected, or a chain in ``chains`` carries none.
    """
    import numpy as np

    positions = np.asarray(positions_nm)
    if positions.ndim == 2:
        positions = positions[None]
    names, ids, owners = np.asarray(name), np.asarray(resid), np.asarray(chain)
    selected = (
        (names == "CA") & (ids >= residues[0]) & (ids <= residues[1]) & np.isin(owners, chains)
    )
    if not np.any(selected):
        raise GeometryComparisonError(
            f"the C-alpha registration selects no atom over residues {residues[0]}-{residues[1]} "
            f"of chain(s) {', '.join(chains) or 'none named'}"
        )
    present = set(owners[selected].tolist())
    absent = [label for label in chains if label not in present]
    if absent:
        raise GeometryComparisonError(
            f"the C-alpha registration selects no atom of chain(s) {', '.join(absent)} over "
            f"residues {residues[0]}-{residues[1]}"
        )
    # Select before widening: the ensemble is float32, (frames, atoms, 3), and only
    # the C-alpha z column is averaged.
    return float(positions[:, selected, 2].astype(np.float64).mean())


def register_by_centroid(
    positions_nm: np.ndarray,
    *,
    name: Sequence[str] | np.ndarray,
    resid: Sequence[int] | np.ndarray,
    chain: Sequence[str] | np.ndarray,
    z_md_nm: float = Z_MD_NM,
    residues: tuple[int, int] = REGISTRATION_RESIDUES,
    chains: Sequence[str] = REGISTRATION_CHAINS,
) -> float:
    """Return ``centre_z_nm`` placing a structure's C-alpha centroid at the MD structure's (D6).

    ``centre_z_nm = z̄_CA - Z_MD``: stage 5 subtracts it, so the centroid lands at
    ``Z_MD`` in the model frame, where the MD structure's sits. Nothing is fitted.
    """
    centroid = calpha_centroid_z_nm(
        positions_nm, name=name, resid=resid, chain=chain, residues=residues, chains=chains
    )
    return centroid - z_md_nm


def rms_optimal_offset(
    stage1_points: PoreProfile | np.ndarray,
    reference: PoreProfile | np.ndarray,
    *,
    centre_nm: float,
    half_width_nm: float = 0.4,
    step_nm: float = 0.005,
) -> float:
    """Return the ``centre_z_nm`` minimising the rms lumen deviation, a diagnostic never used (D6).

    Offsets from ``centre_nm - half_width_nm`` to ``centre_nm + half_width_nm`` at
    ``step_nm``; an offset whose shifted polygon leaves a plane outside the tip
    band uncrossed is skipped, as :func:`compare_profiles` would refuse it. The
    rms is :func:`compare_profiles`'s, but only the lumen is computed per offset:
    the reference's crossings are taken once, and nothing else is recorded.

    Raises
    ------
    MissingPlaneError
        If the reference does not cross its own comparison planes.
    """
    import numpy as np

    from nanopnp.geometry.contour import innermost_crossings

    points, reference_points = _points(stage1_points), _points(reference)
    planes = comparison_planes(reference_points)
    r_ref = _reference_lumen(reference_points, planes)
    low, high = float(reference_points[:, 1].min()), float(reference_points[:, 1].max())
    in_band = _in_tip_band(planes, low, high, TIP_BAND_NM)
    steps = round(half_width_nm / step_nm)
    best, best_rms = math.nan, math.inf
    for offset in centre_nm + np.arange(-steps, steps + 1) * step_nm:
        r_ours = innermost_crossings([to_model_frame(points, float(offset))], planes)
        crossed = np.isfinite(r_ours)
        if np.any(~crossed & ~in_band) or not np.any(crossed):
            continue
        delta = r_ours[crossed] - r_ref[crossed]
        rms = math.sqrt(float(np.mean(delta * delta)))
        if rms < best_rms:
            best, best_rms = float(offset), rms
    return best


# -- the attribution to the reference's construction (D7) ----------------------------


def pqr2grid_radius(
    r_nm: float,
    half_extent_nm: float = PQR2GRID_HALF_EXTENT_NM,
    spacing_nm: float = PQR2GRID_SPACING_NM,
) -> float:
    """Return where ``pqr2grid``'s radial binning writes a feature at true radius ``r_nm``.

    Bin j's centre is ``(j + 1/2) w`` with ``w = h (2L + 1)/(2L + h)``, and the
    script writes bin j at ``j h``, so ``r_a = (r/w - 1/2) h``
    (``.knowledge/04`` §1.2). At L = 15 nm, 1.65 nm reads 1.5744 nm and 5.66 nm
    reads 5.4615 nm [verified].
    """
    return float(_pqr2grid_map(r_nm, half_extent_nm, spacing_nm))


def _pqr2grid_map(
    r_nm: float | np.ndarray, half_extent_nm: float, spacing_nm: float
) -> float | np.ndarray:
    """Return ``r_a = (r/w - 1/2) h``, ``w = h (2L + 1)/(2L + h)`` the bin width, the ``+1`` in nm.

    The one statement of the erratum, for a radius or an array of them.
    """
    width = spacing_nm * (2.0 * half_extent_nm + 1.0) / (2.0 * half_extent_nm + spacing_nm)
    return (r_nm / width - 0.5) * spacing_nm


def pqr2grid_polygon(
    points: PoreProfile | np.ndarray,
    half_extent_nm: float = PQR2GRID_HALF_EXTENT_NM,
    spacing_nm: float = PQR2GRID_SPACING_NM,
) -> np.ndarray:
    """Return ``points`` with every radius mapped through :func:`pqr2grid_radius`; z is kept.

    The script's z comes from the Cartesian grid's own axis, so only r is in error.
    """
    mapped = _points(points).copy()
    mapped[:, 0] = _pqr2grid_map(mapped[:, 0], half_extent_nm, spacing_nm)
    return mapped


class Attribution(_Strict):
    """D7: the pipeline's offset split into the binning erratum and the hand edit.

    ``ours - reference = (ours - binned) + (binned - reference)``: the first term
    is minus the erratum's shift, the second minus the hand edit's.
    """

    binned: ProfileComparison
    """Our polygon, binned as ``pqr2grid`` would have, against the reference."""
    erratum_lumen_mean_nm: float
    """The mean lumen shift the erratum applies to our polygon (negative: inward)."""
    erratum_outer_mean_nm: float
    hand_edit_lumen_mean_nm: float
    """The mean lumen shift the hand edit left: reference minus binned (positive: outward)."""
    hand_edit_outer_mean_nm: float


def attribute_to_construction(
    ours: PoreProfile | np.ndarray,
    reference: PoreProfile | np.ndarray,
    comparison: ProfileComparison | None = None,
) -> Attribution:
    """Attribute the offset between ``ours`` and the reference to its construction (D7).

    Parameters
    ----------
    ours, reference
        Both in the model frame.
    comparison
        :func:`compare_profiles` of the two, if already in hand.

    Raises
    ------
    GeometryComparisonError
        If ``comparison`` was not made on the planes this binned comparison
        uses: the map keeps z, so the two cross the same planes, and the
        differences of their means are only a split of one offset if they do.
    """
    direct = comparison if comparison is not None else compare_profiles(ours, reference)
    binned = compare_profiles(pqr2grid_polygon(ours), reference)
    supplied = (direct.planes, direct.plane_spacing_nm, direct.uncrossed_planes_nm)
    if supplied != (binned.planes, binned.plane_spacing_nm, binned.uncrossed_planes_nm):
        raise GeometryComparisonError(
            f"the comparison supplied ran on {direct.planes} planes at {direct.plane_spacing_nm:g} "
            f"nm with {len(direct.uncrossed_planes_nm)} uncrossed; the binned polygon's runs on "
            f"{binned.planes} at {binned.plane_spacing_nm:g} nm with "
            f"{len(binned.uncrossed_planes_nm)} uncrossed, so their means do not split one offset"
        )
    return Attribution(
        binned=binned,
        erratum_lumen_mean_nm=binned.mean_nm - direct.mean_nm,
        erratum_outer_mean_nm=binned.outer_mean_nm - direct.outer_mean_nm,
        hand_edit_lumen_mean_nm=-binned.mean_nm,
        hand_edit_outer_mean_nm=-binned.outer_mean_nm,
    )


# -- the isolevel sweep (D8) ---------------------------------------------------------


class IsolevelPoint(_Strict):
    """One isolevel of the sweep: its comparison, or the refusal, stage 4's or the comparison's."""

    isolevel: float
    vertices: int | None = None
    comparison: ProfileComparison | None = None
    refusal: str | None = None


def _with_isolevel(document: Mapping[str, object], isolevel: float) -> dict[str, object]:
    """Return a copy of a case document with ``geometry.contour.isolevel`` set."""
    case = dict(document)
    geometry = dict(case.get("geometry") or {})  # type: ignore[call-overload]
    contour = dict(geometry.get("contour") or {})
    contour["isolevel"] = isolevel
    geometry["contour"] = contour
    case["geometry"] = geometry
    return case


def sweep_isolevels(
    case: Path,
    *,
    store: Store,
    reference: PoreProfile | np.ndarray,
    workspace: Path,
    isolevels: Sequence[float] = ISOLEVELS,
) -> list[IsolevelPoint]:
    """Re-run stage 4 at each isolevel on ``store``'s cached map, and compare each (D8).

    Stages 1 to 3 are keyed on nothing the isolevel touches, so every level after
    the first reads them from ``store``. A level whose stage-4 gate refuses, or
    whose contour the comparison cannot be made on, is recorded with the refusal
    and not raised; the default is never changed. Each contour is moved into the
    model frame by the case's own ``geometry.membrane.centre_z_nm``, as stage 5
    would move it.

    Parameters
    ----------
    case
        A case with a ``structure:`` section, and the registration in its
        ``geometry.membrane.centre_z_nm``.
    store
        The store holding, or to hold, stages 1 to 3.
    reference
        The reference polygon, in the model frame.
    workspace
        Where the per-level case files are written.
    isolevels
        The levels, :data:`ISOLEVELS` by default.
    """
    from nanopnp.geometry.contour import PAYLOAD_NAME, ContourGateError

    centre_z_nm = (load_case(case).geometry or Geometry()).membrane.centre_z_nm
    document = yaml.safe_load(case.read_text(encoding="utf-8"))
    workspace.mkdir(parents=True, exist_ok=True)
    points: list[IsolevelPoint] = []
    for isolevel in isolevels:
        path = workspace / f"isolevel-{isolevel:g}.case.yaml"
        text = yaml.safe_dump(_with_isolevel(document, isolevel), sort_keys=False)
        path.write_text(text, encoding="utf-8")
        try:
            result = run_case(path, store=store, upto="contour", write=False)
        except ContourGateError as refusal:
            logger.info("isolevel %g: stage 4 refused: %s", isolevel, refusal)
            points.append(IsolevelPoint(isolevel=isolevel, refusal=str(refusal)))
            continue
        profile = load_profile(result.artefacts["contour"].payload[PAYLOAD_NAME])
        model = to_model_frame(profile.as_array(), centre_z_nm)
        try:
            comparison = compare_profiles(model, reference, strict=False)
        except GeometryComparisonError as refusal:
            logger.info("isolevel %g: the comparison refused: %s", isolevel, refusal)
            points.append(
                IsolevelPoint(isolevel=isolevel, vertices=len(model), refusal=str(refusal))
            )
            continue
        points.append(IsolevelPoint(isolevel=isolevel, vertices=len(model), comparison=comparison))
    return points


def zero_crossing(points: Sequence[IsolevelPoint]) -> float | None:
    """Return the isolevel at which ``ε_G`` crosses zero, linearly between passing levels.

    A diagnostic (D8), never a selection. ``None`` if ``ε_G`` does not change
    sign over the levels that passed.
    """
    passing = [
        (point.isolevel, point.comparison.conductance_deviation)
        for point in points
        if point.comparison is not None
    ]
    for (x0, y0), (x1, y1) in pairwise(passing):
        if y0 == 0.0:
            return x0
        if y0 * y1 < 0.0:
            return x0 + (x1 - x0) * (-y0) / (y1 - y0)
    # The pairs test each level but the last as y0; a zero there is a crossing too.
    if passing and passing[-1][1] == 0.0:
        return passing[-1][0]
    return None

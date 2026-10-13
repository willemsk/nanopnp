"""VAL-05: a generated pore polygon against the delivered reference polygon (WP22 D1-D8)."""

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
from nanopnp.io.case import Geometry
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case
from nanopnp.pipeline.run import run_case

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

logger = logging.getLogger(__name__)

Leg = Literal["ensemble", "2wcd"]

PLANE_SPACING_NM = 0.05

TIP_BAND_NM = 0.1

CONSTRICTION_WINDOW_NM = (-1.85, 1.6)

Z_MD_NM = 5.655

Z_MD_TOLERANCE_NM = 0.01

REGISTRATION_RESIDUES = (8, 292)

REGISTRATION_CHAINS = tuple("ABCDEFGHIJKL")

PQR2GRID_HALF_EXTENT_NM = 15.0

PQR2GRID_SPACING_NM = 0.05

ISOLEVELS = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50)


class GeometryComparisonError(ValueError): ...


class MissingPlaneError(GeometryComparisonError): ...


class GeometryToleranceError(GeometryComparisonError):
    def __init__(self, leg: str, quantity: str, value: str, threshold: str, location: str) -> None:
        self.leg = leg
        self.quantity = quantity
        super().__init__(
            f"VAL-05 ({leg} leg): {quantity} is {value}, above the tolerance {threshold}, "
            f"{location}"
        )


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocatedLength(_Strict):
    value_nm: float
    z_nm: float


class LocatedFraction(_Strict):
    value: float
    z_nm: float


class Tolerance(_Strict):
    conductance_deviation: float
    constriction_nm: float
    rms_nm: float


TOLERANCES: Mapping[str, Tolerance] = {
    "ensemble": Tolerance(conductance_deviation=0.05, constriction_nm=0.1, rms_nm=0.1),
    "2wcd": Tolerance(conductance_deviation=0.10, constriction_nm=0.1, rms_nm=0.2),
}


class ProfileComparison(_Strict):
    planes: int
    compared_planes: int
    uncrossed_planes_nm: list[float]
    plane_spacing_nm: float

    conductance_deviation: float
    conductance_largest_term: LocatedFraction
    conductance_ratio_exact: float
    rms_nm: float
    mean_nm: float
    max_abs: LocatedLength

    constriction_ours: LocatedLength
    constriction_reference: LocatedLength
    constriction_difference_nm: float
    constriction_window_mean_nm: float
    cis_lumen_mean_nm: float

    outer_planes: int
    outer_mean_nm: float
    outer_rms_nm: float

    tips_ours_nm: tuple[float, float]
    tips_reference_nm: tuple[float, float]

    def check(self, leg: Leg) -> None:
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
    import numpy as np

    points = polygon.as_array() if isinstance(polygon, PoreProfile) else polygon
    return np.asarray(points, dtype=np.float64).reshape(-1, 2)


def comparison_planes(
    reference: PoreProfile | np.ndarray, spacing_nm: float = PLANE_SPACING_NM
) -> np.ndarray:
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
    band: np.ndarray = (planes - low <= tip_band_nm) | (high - planes <= tip_band_nm)
    return band


def _reference_lumen(reference_points: np.ndarray, planes: np.ndarray) -> np.ndarray:
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
    import numpy as np

    values = []
    for z in planes:
        crossings = plane_crossings(points, float(z))
        values.append(crossings[1] if len(crossings) >= 2 else math.nan)
    return np.asarray(values, dtype=np.float64)


def _window_minimum(
    radii: np.ndarray, planes: np.ndarray, window: tuple[float, float]
) -> LocatedLength:
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


def calpha_centroid_z_nm(
    positions_nm: np.ndarray,
    *,
    name: Sequence[str] | np.ndarray,
    resid: Sequence[int] | np.ndarray,
    chain: Sequence[str] | np.ndarray,
    residues: tuple[int, int] = REGISTRATION_RESIDUES,
    chains: Sequence[str] = REGISTRATION_CHAINS,
) -> float:
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


def pqr2grid_radius(
    r_nm: float,
    half_extent_nm: float = PQR2GRID_HALF_EXTENT_NM,
    spacing_nm: float = PQR2GRID_SPACING_NM,
) -> float:
    return float(_pqr2grid_map(r_nm, half_extent_nm, spacing_nm))


def _pqr2grid_map(
    r_nm: float | np.ndarray, half_extent_nm: float, spacing_nm: float
) -> float | np.ndarray:
    width = spacing_nm * (2.0 * half_extent_nm + 1.0) / (2.0 * half_extent_nm + spacing_nm)
    return (r_nm / width - 0.5) * spacing_nm


def pqr2grid_polygon(
    points: PoreProfile | np.ndarray,
    half_extent_nm: float = PQR2GRID_HALF_EXTENT_NM,
    spacing_nm: float = PQR2GRID_SPACING_NM,
) -> np.ndarray:
    mapped = _points(points).copy()
    mapped[:, 0] = _pqr2grid_map(mapped[:, 0], half_extent_nm, spacing_nm)
    return mapped


class Attribution(_Strict):
    binned: ProfileComparison
    erratum_lumen_mean_nm: float
    erratum_outer_mean_nm: float
    hand_edit_lumen_mean_nm: float
    hand_edit_outer_mean_nm: float


def attribute_to_construction(
    ours: PoreProfile | np.ndarray,
    reference: PoreProfile | np.ndarray,
    comparison: ProfileComparison | None = None,
) -> Attribution:
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


class IsolevelPoint(_Strict):
    isolevel: float
    vertices: int | None = None
    comparison: ProfileComparison | None = None
    refusal: str | None = None


def _with_isolevel(document: Mapping[str, object], isolevel: float) -> dict[str, object]:
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

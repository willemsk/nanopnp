"""VER-48: the Cₙ axis by permutation superposition, on synthetic assemblies (FR-01, FR-02)."""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path

import numpy as np
import pytest

from nanopnp.structure.axis import (
    DISPLACEMENT_BUDGET_NM,
    AxisRecord,
    SymmetryGateError,
    check_z_axis,
    detect_axis,
    frame_rotation,
    kabsch,
    measure_axis,
    z_displacement,
)

logger = logging.getLogger(__name__)

ATOMS_PER_CHAIN = 285


def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    k = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * (skew @ skew)


def _protomer(n: int, rng: np.random.Generator, *, isotropic: bool) -> np.ndarray:
    rho = rng.uniform(2.0, 5.0, ATOMS_PER_CHAIN)
    half_wedge = 0.8 * math.pi / n
    phi = rng.uniform(-half_wedge, half_wedge, ATOMS_PER_CHAIN)
    z = rng.uniform(-4.4, 4.4, ATOMS_PER_CHAIN)
    if isotropic:
        z = z - z.mean()
        z *= math.sqrt(np.mean(rho**2) / 2.0 / np.mean(z**2))
    return np.column_stack([rho * np.cos(phi), rho * np.sin(phi), z])


def _assembly(n: int, protomer: np.ndarray) -> np.ndarray:
    return np.stack(
        [protomer @ _rotation(np.array([0, 0, 1.0]), 2 * math.pi * k / n).T for k in range(n)]
    )


def _move(chains: np.ndarray, rotation: np.ndarray, shift: np.ndarray) -> np.ndarray:
    return np.asarray(chains @ rotation.T + shift, dtype=np.float64)


TILT = _rotation(np.array([1.0, 2.0, 0.0]), math.radians(35.0))

OFFSET_NM = np.array([3.0, -1.5, 40.0])


def _line_distance(record: AxisRecord, axis: np.ndarray, point: np.ndarray) -> float:
    offset = point - record.centroid_nm
    return float(np.linalg.norm(offset - (offset @ record.axis) * record.axis))


# FR-02
@pytest.mark.parametrize("n", [7, 8, 12])
def test_ver48_exact_cn_assembly_recovers_its_axis(n: int) -> None:
    rng = np.random.default_rng(48)
    chains = _move(_assembly(n, _protomer(n, rng, isotropic=False)), TILT, OFFSET_NM)
    shuffled = chains[rng.permutation(n)]
    true_axis = TILT @ np.array([0.0, 0.0, 1.0])

    record = measure_axis(shuffled, n)

    assert np.linalg.norm(np.cross(record.axis, true_axis)) <= 1e-9
    assert record.axis @ true_axis > 0.0, "the axis is signed to the file's +z"
    assert _line_distance(record, true_axis, OFFSET_NM) <= 1e-9
    assert abs(record.angle_deg - 360.0 / n) <= 1e-9
    assert record.spacing_error_deg <= 1e-9
    assert abs(record.tilt_deg - 35.0) <= 1e-9
    logger.info(
        "C%d: axis error %.2e deg, offset %.2e nm",
        n,
        math.degrees(math.asin(min(1.0, float(np.linalg.norm(np.cross(record.axis, true_axis)))))),
        _line_distance(record, true_axis, OFFSET_NM),
    )


def _principal_axis_nearest(
    points: np.ndarray, target: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    centroid = points.mean(axis=0)
    _, vectors = np.linalg.eigh(np.cov((points - centroid).T))
    best = vectors[:, int(np.argmax(np.abs(vectors.T @ target)))]
    return (best if best @ target >= 0 else -best), centroid


def test_ver48_permutation_meets_the_budget_where_principal_axes_do_not() -> None:
    n = 12
    rng = np.random.default_rng(20260925)
    ideal = _assembly(n, _protomer(n, rng, isotropic=True))
    noisy = ideal + rng.normal(0.0, 0.02, ideal.shape)
    moved = _move(noisy, TILT, OFFSET_NM)

    record = measure_axis(moved, n)
    axis = TILT.T @ record.axis
    point = TILT.T @ (record.centroid_nm - OFFSET_NM)
    extent = (float(noisy[..., 2].min()), float(noisy[..., 2].max()))
    permutation = z_displacement(axis, point, extent)

    flat = moved.reshape(-1, 3)
    principal, centroid = _principal_axis_nearest(flat, TILT @ np.array([0.0, 0.0, 1.0]))
    principal_axes = z_displacement(TILT.T @ principal, TILT.T @ (centroid - OFFSET_NM), extent)

    logger.info(
        "sigma 0.02 nm: permutation %.4f nm (tilt %.4f deg, offset %.4f nm); principal axes "
        "%.4f nm (tilt %.3f deg)",
        permutation.displacement_nm,
        permutation.tilt_deg,
        permutation.offset_nm,
        principal_axes.displacement_nm,
        principal_axes.tilt_deg,
    )
    assert permutation.displacement_nm <= DISPLACEMENT_BUDGET_NM
    assert principal_axes.displacement_nm > DISPLACEMENT_BUDGET_NM


def _six_by_two() -> np.ndarray:
    rng = np.random.default_rng(6)
    base = _protomer(12, rng, isotropic=False)
    upper = base + np.array([0.0, 0.0, 2.5])
    lower = base - np.array([0.0, 0.0, 2.5])
    pair = [upper, lower]
    turn = _rotation(np.array([0.0, 0.0, 1.0]), math.pi / 3)
    return np.stack([pair[k % 2] @ np.linalg.matrix_power(turn, k // 2).T for k in range(12)])


def _dihedral() -> np.ndarray:
    rng = np.random.default_rng(12)
    base = _protomer(12, rng, isotropic=False) + np.array([0.0, 0.0, 1.5])
    z = np.array([0.0, 0.0, 1.0])
    chains = []
    for k in range(12):
        azimuth = 2 * math.pi * k / 12
        chain = base @ _rotation(z, azimuth).T
        if k % 2:
            chain = (
                chain @ _rotation(np.array([math.cos(azimuth), math.sin(azimuth), 0.0]), math.pi).T
            )
        chains.append(chain)
    return np.stack(chains)


def _unturned_ring() -> np.ndarray:
    rng = np.random.default_rng(12)
    base = _protomer(12, rng, isotropic=False)
    centre = base.mean(axis=0)
    z = np.array([0.0, 0.0, 1.0])
    return np.stack(
        [
            (base - centre) @ _rotation(z, 0.25 * 2 * math.pi * k / 12).T
            + _rotation(z, 2 * math.pi * k / 12) @ centre
            for k in range(12)
        ]
    )


def _cn(n: int, rotation: np.ndarray | None = None, shift: np.ndarray | None = None) -> np.ndarray:
    chains = _assembly(n, _protomer(n, np.random.default_rng(n), isotropic=False))
    return _move(
        chains,
        np.eye(3) if rotation is None else rotation,
        np.zeros(3) if shift is None else shift,
    )


# QR-12
@pytest.mark.parametrize(
    ("build", "n", "measured", "low", "high"),
    [
        # A 6 x 2 arrangement has azimuth gaps of 0 and 60 degrees, far outside 7.5 degrees.
        pytest.param(
            _six_by_two,
            12,
            r"azimuthal spacing gate: .* (\d+\.\d+) degrees from nominal",
            7.5,
            360.0,
            id="six-by-two-spacing",
        ),
        pytest.param(
            _dihedral,
            12,
            r"azimuthal spacing gate: .* (\d+\.\d+) degrees from nominal",
            7.5,
            360.0,
            id="dihedral-spacing",
        ),
        pytest.param(
            _unturned_ring,
            12,
            r"rotation-angle gate: .* turn of (\d+\.\d+) degrees",
            27.0,
            29.0,
            id="unturned-ring-angle",
        ),
        pytest.param(lambda: _cn(12)[:1], 1, r"(C1) has none", 0.0, 0.0, id="c1-auto"),
        pytest.param(
            lambda: _cn(12, _rotation(np.array([1.0, 0.0, 0.0]), math.radians(30.0))),
            12,
            r"orientation gate: the detected axis is (\d+\.\d+) degrees from the file's z",
            29.995,
            30.005,
            id="tilted-30-orientation",
        ),
    ],
)
def test_ver48_gates_fire(build: object, n: int, measured: str, low: float, high: float) -> None:
    chains = build()  # type: ignore[operator]
    with pytest.raises(SymmetryGateError) as raised:
        detect_axis(chains, n)
    message = str(raised.value)
    logger.info("%s", message)
    found = re.search(measured, message)
    assert found is not None, message
    if low or high:
        assert low <= float(found.group(1)) <= high, message


def test_ver48_axis_z_beyond_the_budget_is_refused() -> None:
    outside = _cn(12, shift=np.array([0.02, 0.0, 0.0]))
    record = detect_axis(outside, 12)
    extent = (float(outside[..., 2].min()), float(outside[..., 2].max()))
    with pytest.raises(SymmetryGateError) as raised:
        check_z_axis(record, extent)
    message = str(raised.value)
    assert "displacement gate" in message
    assert "0.0200 nm" in message
    assert "tilt 0.000 degrees" in message
    assert "offset 0.0200 nm" in message

    inside = _cn(12, shift=np.array([0.0, 0.005, 0.0]))
    found = check_z_axis(detect_axis(inside, 12), extent)
    assert abs(found.displacement_nm - 0.005) <= 1e-12


# FR-01
def test_ver48_kabsch_matches_mdanalysis() -> None:
    from MDAnalysis.analysis.align import rotation_matrix

    rng = np.random.default_rng(1)
    reference = rng.normal(0.0, 2.0, (285, 3))
    rotation = _rotation(rng.normal(size=3), 1.234)
    mobile = (reference - reference.mean(axis=0)) @ rotation.T + np.array([4.0, -2.0, 9.0])
    mobile += rng.normal(0.0, 0.05, mobile.shape)

    fit = kabsch(mobile, reference)
    theirs, _ = rotation_matrix(mobile - mobile.mean(axis=0), reference - reference.mean(axis=0))

    assert np.max(np.abs(fit.rotation - np.asarray(theirs))) <= 1e-12
    assert np.linalg.det(fit.rotation) == pytest.approx(1.0, abs=1e-12)


def test_ver48_kabsch_never_returns_a_reflection() -> None:
    rng = np.random.default_rng(2)
    reference = rng.normal(size=(50, 3))
    mirrored = reference * np.array([1.0, 1.0, -1.0])
    assert np.linalg.det(kabsch(mirrored, reference).rotation) == pytest.approx(1.0, abs=1e-12)


def test_ver48_the_frame_puts_the_axis_on_z_and_keeps_the_axial_coordinate() -> None:
    rotation = _rotation(np.array([1.0, -1.0, 0.0]), math.radians(6.0))
    chains = _cn(12, rotation, np.array([0.7, -0.4, 3.0]))[
        np.array([3, 0, 7, 1, 11, 2, 5, 4, 6, 10, 9, 8])
    ]
    record = detect_axis(chains, 12)
    q = frame_rotation(record, chains[0].mean(axis=0))
    moved = (chains - record.foot_nm) @ q.T

    assert np.allclose(q @ record.axis, [0.0, 0.0, 1.0], atol=1e-14)
    assert np.allclose(moved[..., 2], chains @ record.axis, atol=1e-12)
    first = moved[0].mean(axis=0)
    assert abs(first[1]) <= 1e-12
    assert first[0] > 0.0
    again = detect_axis(moved, 12)
    assert np.linalg.norm(np.cross(again.axis, [0.0, 0.0, 1.0])) <= 1e-12
    assert np.hypot(*again.foot_nm[:2]) <= 1e-12
    phi = np.degrees(np.arctan2(moved[..., 1].mean(axis=1), moved[..., 0].mean(axis=1)))
    assert np.allclose(np.mod(np.diff(phi[list(record.order)]), 360.0), 30.0, atol=1e-9)


def _tilted_ring_pdb(path: Path, *, n: int = 8, residues: int = 40) -> None:
    # A C_n ring of C-alpha, wider at its +z end, then turned 160 degrees so the file's +z
    # points at the narrow end, and moved off the origin.
    height = np.linspace(-60.0, 60.0, residues)
    radius = 30.0 + 0.25 * height
    wobble = 0.3 * np.sin(np.arange(residues))
    tilt = _rotation(np.array([1.0, 1.0, 0.0]), math.radians(160.0))
    lines = []
    for chain in range(n):
        phi = 2.0 * math.pi * chain / n + wobble
        ring = np.column_stack([radius * np.cos(phi), radius * np.sin(phi), height])
        for residue, (x, y, z) in enumerate(ring @ tilt.T + [5.0, -3.0, 12.0], start=1):
            serial = chain * residues + residue
            lines.append(
                f"ATOM  {serial:5d}  CA  ALA {chr(65 + chain)}{residue:4d}    "
                f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           C"
            )
    path.write_text("\n".join([*lines, "END", ""]))


@pytest.mark.parametrize("cis_end", ["wider", "narrower"])
def test_orient_pore_puts_a_tilted_ring_on_z_with_the_named_end_cis(
    cis_end: str, tmp_path: Path
) -> None:
    # FR-37: a sign lost would put the wrong mouth cis, and stage 1's gate would not see it.
    pytest.importorskip("MDAnalysis")
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents

    from nanopnp.structure import orient_pore

    source = tmp_path / "ring.pdb"
    _tilted_ring_pdb(source)
    kwargs = {"cis_end": cis_end, "registration_residues": (5, 30), "centroid_z_nm": 5.655}
    first = orient_pore(source, **kwargs, out=tmp_path / "first.pdb")  # type: ignore[arg-type]
    second = orient_pore(source, **kwargs, out=tmp_path / "second.pdb")  # type: ignore[arg-type]
    assert first.read_bytes() == second.read_bytes()

    calpha = mda.Universe(str(first)).select_atoms("name CA")
    positions = calpha.positions.astype(np.float64) / 10.0
    _, vectors = np.linalg.eigh(np.cov(positions.T))
    axis = vectors[:, 2]
    assert math.degrees(math.acos(min(1.0, abs(axis[2])))) < 0.5
    radius = np.hypot(positions[:, 0], positions[:, 1])
    top = radius[positions[:, 2] > np.quantile(positions[:, 2], 0.8)].mean()
    bottom = radius[positions[:, 2] < np.quantile(positions[:, 2], 0.2)].mean()
    assert (top > bottom) == (cis_end == "wider")
    anchor = calpha.select_atoms("resid 5:30").positions.astype(np.float64).mean(axis=0) / 10.0
    np.testing.assert_allclose(anchor, [0.0, 0.0, 5.655], atol=1e-3)

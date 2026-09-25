"""VER-48: the Cₙ axis by chain-permutation superposition, on synthetic assemblies (FR-01, FR-02).

Every oracle here is a closed form: an assembly built about a known axis, a
rigid move applied with a known rotation. None of it reads a file, so an error
found here is in :mod:`nanopnp.structure.axis` and nowhere else (§7.1).
"""

from __future__ import annotations

import logging
import math
import re

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
"""The ClyA common-C-alpha count, so the synthetic has the real one's statistics."""


def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    """Return the rotation by ``angle`` (radians) about the unit ``axis`` (Rodrigues)."""
    k = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * (skew @ skew)


def _protomer(n: int, rng: np.random.Generator, *, isotropic: bool) -> np.ndarray:
    """Return one chain of the Design §5 synthetic, about z through the origin.

    ``rho ~ U(2, 5)`` nm, ``φ`` inside ±80 % of the chain's wedge, ``z`` uniform and
    then — when ``isotropic`` — centred and rescaled so that ``⟨z²⟩ = ⟨rho²⟩/2``
    exactly. Replicated ``n`` times, that makes the assembly's second moments
    isotropic, so its principal axes are undetermined before noise is added.
    """
    rho = rng.uniform(2.0, 5.0, ATOMS_PER_CHAIN)
    half_wedge = 0.8 * math.pi / n
    phi = rng.uniform(-half_wedge, half_wedge, ATOMS_PER_CHAIN)
    z = rng.uniform(-4.4, 4.4, ATOMS_PER_CHAIN)
    if isotropic:
        z = z - z.mean()
        z *= math.sqrt(np.mean(rho**2) / 2.0 / np.mean(z**2))
    return np.column_stack([rho * np.cos(phi), rho * np.sin(phi), z])


def _assembly(n: int, protomer: np.ndarray) -> np.ndarray:
    """Return ``(n, m, 3)``: ``protomer`` turned by ``2πk/n`` about z, k = 0 … n - 1."""
    return np.stack(
        [protomer @ _rotation(np.array([0, 0, 1.0]), 2 * math.pi * k / n).T for k in range(n)]
    )


def _move(chains: np.ndarray, rotation: np.ndarray, shift: np.ndarray) -> np.ndarray:
    """Return ``chains`` moved rigidly: ``R x + t``."""
    return np.asarray(chains @ rotation.T + shift, dtype=np.float64)


TILT = _rotation(np.array([1.0, 2.0, 0.0]), math.radians(35.0))
"""A 35° tilt about a direction in the xy-plane: the known axis is ``TILT @ ẑ``."""

OFFSET_NM = np.array([3.0, -1.5, 40.0])


def _line_distance(record: AxisRecord, axis: np.ndarray, point: np.ndarray) -> float:
    """Return the distance from ``point`` to the line ``record`` describes, in nm."""
    offset = point - record.centroid_nm
    return float(np.linalg.norm(offset - (offset @ record.axis) * record.axis))


@pytest.mark.parametrize("n", [7, 8, 12])
def test_ver48_exact_cn_assembly_recovers_its_axis(n: int) -> None:
    """An exact Cₙ about a tilted, offset axis recovers that axis to round-off (FR-02).

    The chains are lettered in a shuffled order, so the test also holds the
    ordering to not trusting the labels (WP18 Design §1).
    """
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
    """Return the principal axis of ``points`` closest to ``target``, through their centroid.

    The most favourable choice a principal-axes method could make: in the
    isotropic synthetic the eigenvalues carry no information about which
    eigenvector is the axis, so the one nearest the truth is taken.
    """
    centroid = points.mean(axis=0)
    _, vectors = np.linalg.eigh(np.cov((points - centroid).T))
    best = vectors[:, int(np.argmax(np.abs(vectors.T @ target)))]
    return (best if best @ target >= 0 else -best), centroid


def test_ver48_permutation_meets_the_budget_where_principal_axes_do_not() -> None:
    """Per-atom noise of 0.02 nm: the permutation axis stays inside 0.01 nm; principal axes do not.

    The isotropic-moment synthetic of WP18 Design §5, C12, one fixed seed. Both
    estimates are measured the same way — the lateral displacement from the true
    axis over the axial extent — after the known move is undone.
    """
    n = 12
    rng = np.random.default_rng(20260925)
    ideal = _assembly(n, _protomer(n, rng, isotropic=True))
    noisy = ideal + rng.normal(0.0, 0.02, ideal.shape)
    moved = _move(noisy, TILT, OFFSET_NM)

    record = measure_axis(moved, n)
    # Back into the frame in which the true axis is z through the origin.
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
    """Twelve chains in six pairs: a C6 of dimers claimed as C12 (azimuth gaps 0° and 60°)."""
    rng = np.random.default_rng(6)
    base = _protomer(12, rng, isotropic=False)
    upper = base + np.array([0.0, 0.0, 2.5])
    lower = base - np.array([0.0, 0.0, 2.5])
    pair = [upper, lower]
    turn = _rotation(np.array([0.0, 0.0, 1.0]), math.pi / 3)
    return np.stack([pair[k % 2] @ np.linalg.matrix_power(turn, k // 2).T for k in range(12)])


def _dihedral() -> np.ndarray:
    """Return a D6 assembly: six chains up, six turned over about the two-fold axes between.

    Azimuths exactly 30° apart, alternating up and down, every chain congruent.
    What is missing is a single 30° rotation carrying each chain to its
    neighbour. The rotations from chain 0 onto the others sum to zero here — six
    turns about z give ``6 ẑẑᵀ`` and six two-folds perpendicular to it give
    ``-6 ẑẑᵀ`` — so the ordering axis is undetermined and the chains are ordered
    about an arbitrary direction, which the spacing gate then refuses.
    """
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
    """Twelve chains 30° apart whose own orientation turns at a quarter of the ring's rate.

    The centroids are an exact C12 ring, so the spacing gate passes, but the
    chains are not rotational copies: the rotation carrying the assembly onto its
    cyclic permutation is a 28.07° turn, not 30°. This is the angle gate's case —
    a ring of the right count and spacing that is not Cₙ.
    """
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
    """Return an exact Cₙ about z through the origin, optionally moved rigidly."""
    chains = _assembly(n, _protomer(n, np.random.default_rng(n), isotropic=False))
    return _move(
        chains,
        np.eye(3) if rotation is None else rotation,
        np.zeros(3) if shift is None else shift,
    )


@pytest.mark.parametrize(
    ("build", "n", "measured", "low", "high"),
    [
        # A 6 x 2 arrangement has gaps of 0 and 60 degrees, and two chains at
        # one azimuth order either way round, so the worst gap can read as a
        # near-full turn: either way it is far outside 7.5 degrees.
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
    """Each symmetry gate refuses its constructed input, naming the gate and the value (QR-12)."""
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
    """``axis: z`` on an exact C12 offset 0.02 nm from the file's z is refused, naming all three.

    And the same assembly offset by 0.005 nm, inside the 0.01 nm budget, passes
    with the displacement measured to round-off.
    """
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


def test_ver48_kabsch_matches_mdanalysis() -> None:
    """The in-project Kabsch rotation equals MDAnalysis ``rotation_matrix`` (FR-01)."""
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
    """A mirrored point set is fitted by a proper rotation; the determinant sign is fixed (D6)."""
    rng = np.random.default_rng(2)
    reference = rng.normal(size=(50, 3))
    mirrored = reference * np.array([1.0, 1.0, -1.0])
    assert np.linalg.det(kabsch(mirrored, reference).rotation) == pytest.approx(1.0, abs=1e-12)


def test_ver48_the_frame_puts_the_axis_on_z_and_keeps_the_axial_coordinate() -> None:
    """``x' = Q(x - p)`` maps the axis to z through r = 0, keeps ``z = â·x``, chain 0 on +x (D8).

    Re-detecting the axis on the transformed assembly gives ẑ through the origin.
    """
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
    # Counter-clockwise from chain 0, in the order the record gives.
    phi = np.degrees(np.arctan2(moved[..., 1].mean(axis=1), moved[..., 0].mean(axis=1)))
    assert np.allclose(np.mod(np.diff(phi[list(record.order)]), 360.0), 30.0, atol=1e-9)

"""VER-01, VER-02, VER-58, QR-12 at Tier 1: the deposit, its transfer, and the gates it must fail.

The producer path's two legs are exact by construction (§4.4 NOTE on the
producer path), so each is shown to fail on the broken construction WP28's
*Design* §5 names for it, and the discriminating per-plane check on the one that
passes both legs. The Galerkin property is checked through NGSolve's own
integration of the transferred field, which is not the route the projection
takes.
"""

from __future__ import annotations

import logging
import math
from dataclasses import replace

import ngsolve as ngs
import numpy as np
import pytest
from netgen.geom2d import SplineGeometry

from nanopnp.charge.deposit import (
    SOLID_SHARE_MIN,
    Deposit,
    DepositedCharge,
    basis_exponents,
    check_solid_share,
    deposit,
    geometry_digest,
    gridfunction,
    lattice_masses,
    locate,
    triangle_rule,
)
from nanopnp.charge.fields import (
    CONSERVATION_TOL,
    ChargeFieldError,
    DepositConservation,
    check_deposit_conservation,
    deposit_conservation,
)
from nanopnp.charge.kernel import SourceAtoms, sum_kernel
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.density.grid import RadialGrid
from nanopnp.mesh.adapter import MeshData, from_ngsolve, to_ngsolve
from nanopnp.numerics.measures import AXISYMMETRIC

logger = logging.getLogger(__name__)

H = 0.005


def _mesh(*, maxh: float = 0.12, r_max: float = 5.0, protein: bool = True) -> MeshData:
    """Return a box ``[0, r_max] x [-2.5, 2.5]`` nm of water, with a protein block inside."""
    geometry = SplineGeometry()
    geometry.AddRectangle((0.0, -2.5), (r_max, 2.5), bcs=["trans", "wall", "cis", "axis"])
    geometry.SetMaterial(1, "water")
    if protein:
        geometry.AddRectangle(
            (0.5, -1.5), (min(4.5, r_max - 0.2), 1.5), leftdomain=2, rightdomain=1, bc="interface"
        )
        geometry.SetMaterial(2, "protein")
    return from_ngsolve(ngs.Mesh(geometry.GenerateMesh(maxh=maxh)))


def _atoms(
    r_nm: list[float],
    z_nm: list[float],
    width_nm: list[float],
    charge_e: list[float],
    *,
    shift_z_nm: float = 0.0,
) -> SourceAtoms:
    """Return one frame of source atoms given directly."""
    count = len(r_nm)
    return SourceAtoms(
        r_nm=np.asarray(r_nm, dtype=np.float64),
        z_nm=np.asarray(z_nm, dtype=np.float64) - shift_z_nm,
        width_nm=np.asarray(width_nm, dtype=np.float64),
        weight_e=np.asarray(charge_e, dtype=np.float64),
        frame=np.zeros(count, dtype=np.int64),
        atom=np.arange(count, dtype=np.int64),
        frames=1,
        shift_z_nm=shift_z_nm,
    )


@pytest.fixture(scope="module")
def mesh_data() -> MeshData:
    """Return the two-material box, once per module."""
    return _mesh()


@pytest.fixture(scope="module")
def several() -> SourceAtoms:
    """Atoms on and near the axis, and of every CHARMM-like width, in the protein block."""
    return _atoms(
        [0.0, 0.6, 1.5, 2.2, 3.9],
        [0.1, -0.4, 0.3, 1.1, -1.2],
        [0.05, 0.1, 0.0112, 0.085, 0.11],
        [1.0, -2.0, 0.5, -1.0, 0.25],
    )


def _report(
    atoms: SourceAtoms, grid: RadialGrid, found: Deposit, data: MeshData
) -> DepositConservation:
    """Return the producer-path report of ``found`` on ``data``'s NGSolve mesh."""
    mesh = to_ngsolve(data)
    field = gridfunction(found, mesh)
    measures = replace(AXISYMMETRIC, element_order=max(found.order, 1))
    return deposit_conservation(atoms, grid, field, mesh, measures)


# -- the reference element -----------------------------------------------------------


@pytest.mark.parametrize("degree", [0, 1, 3, 5, 7])
def test_ver58_triangle_rule_is_exact_to_its_degree(degree: int) -> None:
    """The collapsed Gauss rule integrates every monomial of its degree exactly on the reference."""
    barycentric, weights = triangle_rule(degree)
    xi, eta = barycentric[:, 1], barycentric[:, 2]
    for a in range(degree + 1):
        for b in range(degree + 1 - a):
            exact = math.factorial(a) * math.factorial(b) / math.factorial(a + b + 2)
            assert 0.5 * float(weights @ (xi**a * eta**b)) == pytest.approx(exact, rel=1e-13)


def test_ver58_locate_counts_every_node_once_and_lowest_index_wins(mesh_data: MeshData) -> None:
    """Every lattice node is in exactly one element; a shared edge goes to the lower index."""
    grid = RadialGrid.from_axes(
        np.arange(0, 1001) * H, np.arange(-500, 501) * H, np.ones((1001, 1001))
    )
    nodes, _ = lattice_masses(grid)
    owner = locate(mesh_data, nodes, cell_nm=H)
    assert np.all(owner >= 0)
    # Brute force on a sample: the lowest index among the elements containing each node.
    corners = mesh_data.vertices[mesh_data.triangles]
    rng = np.random.default_rng(1)
    for node in rng.choice(nodes.shape[0], 200, replace=False):
        p = nodes[node]
        a, b, c = corners[:, 0], corners[:, 1], corners[:, 2]

        def cross(u: np.ndarray, v: np.ndarray, p: np.ndarray = p) -> np.ndarray:
            return (v[:, 0] - u[:, 0]) * (p[1] - u[:, 1]) - (v[:, 1] - u[:, 1]) * (p[0] - u[:, 0])

        signs = np.stack([cross(a, b), cross(b, c), cross(c, a)], axis=1)
        inside = np.flatnonzero(np.all(signs >= -1e-12, axis=1))
        assert owner[node] == inside.min()


# -- the Galerkin property and the transfer -------------------------------------------


@pytest.mark.parametrize("order", [1, 2, 3])
def test_ver58_deposit_moments_equal_the_lattice_against_every_monomial(
    mesh_data: MeshData, several: SourceAtoms, order: int
) -> None:
    """``int rho_h r^a z^b r`` over the mesh, by NGSolve, equals the lattice's sum to 1e-12."""
    grid = sum_kernel(several, H).grid
    found = deposit(grid, mesh_data, order)
    mesh = to_ngsolve(mesh_data)
    field = gridfunction(found, mesh)
    nodes, masses = lattice_masses(grid)
    scale = float(np.sum(np.abs(masses)))
    for a, b in basis_exponents(order):
        lattice = float(np.sum(masses * nodes[:, 0] ** a * nodes[:, 1] ** b))
        integrated = ngs.Integrate(field * ngs.x ** (a + 1) * ngs.y**b, mesh, order=2 * order + 4)
        assert abs(integrated - lattice) <= 1e-12 * scale * 5.0 ** (a + b), (a, b)
    # Element by element too, for the charge: each element carries its lattice charge.
    per_element = ngs.Integrate(field * ngs.x, mesh, order=order + 3, element_wise=True)
    charges = 2.0 * math.pi * 1e-27 * per_element.NumPy()
    assert np.max(np.abs(charges - found.element_charge_C)) <= 1e-12 * scale * 2 * math.pi * 1e-27


def test_ver58_p0_misses_the_first_moment_that_p1_keeps(
    mesh_data: MeshData, several: SourceAtoms
) -> None:
    """A deposit at P0 conserves charge but fails the Galerkin moment test (*Design* §5)."""
    grid = sum_kernel(several, H).grid
    mesh = to_ngsolve(mesh_data)
    lattice = grid.integral(z_weight=grid.z_nm)
    errors = {}
    for order in (0, 1):
        found = deposit(grid, mesh_data, order)
        field = gridfunction(found, mesh)
        moment = 2.0 * math.pi * 1e-27 * ngs.Integrate(field * ngs.x * ngs.y, mesh, order=6)
        errors[order] = abs(moment - lattice) / abs(grid.planar_integral())
        assert found.charge_C() == pytest.approx(grid.planar_integral(), rel=1e-12)
    logger.info("first z-moment error relative to Q: P0 %.3e, P1 %.3e", errors[0], errors[1])
    assert errors[1] < 1e-12
    assert errors[0] > 1e-4


def test_ver58_ngsolve_field_equals_the_payload(
    mesh_data: MeshData, several: SourceAtoms, tmp_path
) -> None:
    """The ``L2(order=k)`` field equals the payload's polynomials, and its order is ``k`` (D5)."""
    grid = sum_kernel(several, H).grid
    found = Deposit.read(deposit(grid, mesh_data, 2).write(tmp_path / "deposit.npz"))
    mesh = to_ngsolve(mesh_data)
    field = gridfunction(found, mesh)
    assert field.space.globalorder == found.order == 2
    rng = np.random.default_rng(3)
    elements = rng.choice(mesh_data.element_count, 300, replace=False)
    corners = mesh_data.vertices[mesh_data.triangles[elements]]
    weights = rng.dirichlet(np.ones(3), size=elements.size)
    points = np.einsum("mv,mvd->md", weights, corners)
    located = mesh(points[:, 0], points[:, 1])
    assert np.array_equal(located["nr"], elements)
    ngsolve_values = field(located).reshape(-1)
    payload = found.evaluate(points, elements)
    assert np.max(np.abs(ngsolve_values - payload)) <= 1e-10 * np.max(np.abs(payload))
    charge = DepositedCharge(deposit=found, field=field)
    assert charge.volume_density_C_m3() is field
    assert not charge.is_areal


# -- the broken constructions of Design §5 --------------------------------------------


def test_ver01_dropped_renormalisation_fails_the_producer_leg_only(mesh_data: MeshData) -> None:
    """An atom on the axis, unrenormalised: the producer leg fails at -1.67e-3, not the consumer."""
    atoms = _atoms([0.0], [0.0], [0.05], [1.0])
    grid = sum_kernel(atoms, H, renormalise=False).grid
    report = _report(atoms, grid, deposit(grid, mesh_data, 2), mesh_data)
    logger.info(
        "unrenormalised: producer %.3e, consumer %.3e", report.producer_error, report.consumer_error
    )
    assert report.producer_error == pytest.approx(-(H**2) / (6 * 0.05**2), rel=0.1)
    assert abs(report.consumer_error) <= 1e-12
    with pytest.raises(ChargeFieldError, match="producer leg"):
        check_deposit_conservation(report)


def test_ver01_truncated_patch_fails_the_producer_leg(mesh_data: MeshData) -> None:
    """Patches cut at 2 w and not renormalised lose ``1 - erf(2)^2 = 0.93 %``: the producer leg."""
    atoms = _atoms([2.0], [0.0], [0.1], [1.0])
    grid = sum_kernel(atoms, H, half_widths=2.0, renormalise=False).grid
    report = _report(atoms, grid, deposit(grid, mesh_data, 2), mesh_data)
    # The continuous loss is 1 - erf(2)^2 = 0.93 %. The patch's last nodes, at
    # exactly +-2 w, keep their full trapezoid weight, which gives back
    # h exp(-4)/(w sqrt(pi)) = 5e-4 on each axis: 0.83 % on the lattice.
    continuous = 1 - math.erf(2.0) ** 2
    returned = 2 * H * math.exp(-4.0) / (0.1 * math.sqrt(math.pi))
    assert report.producer_error == pytest.approx(-(continuous - returned), rel=0.01)
    with pytest.raises(ChargeFieldError, match="producer leg"):
        check_deposit_conservation(report)


def test_ver01_unweighted_gram_fails_the_consumer_leg_only(mesh_data: MeshData) -> None:
    """The projection without its ``r`` weight, beside the axis: the consumer leg fails."""
    atoms = _atoms([0.05], [0.0], [0.08], [1.0])
    grid = sum_kernel(atoms, H).grid
    report = _report(atoms, grid, deposit(grid, mesh_data, 2, weighted=False), mesh_data)
    logger.info("unweighted Gram: consumer %.3e", report.consumer_error)
    assert abs(report.producer_error) <= 1e-12
    assert abs(report.consumer_error) > CONSERVATION_TOL
    with pytest.raises(ChargeFieldError, match="consumer leg"):
        check_deposit_conservation(report)


def test_ver02_dropped_jacobian_renormalised_globally_fails_the_planes_only(
    mesh_data: MeshData,
) -> None:
    """``2 pi r`` dropped, rescaled to ``Q_net``: both legs pass, the planes fail (1.6 for 1.0)."""
    atoms = _atoms([1.0, 4.0], [-1.0, 1.0], [0.1, 0.1], [1.0, 1.0])
    good = sum_kernel(atoms, H).grid
    radius = good.r_nm[None, :]
    values = np.divide(
        good.values, 2.0 * math.pi * radius, out=np.zeros_like(good.values), where=radius > 0
    )
    broken = RadialGrid(origin_nm=good.origin_nm, spacing_nm=good.spacing_nm, values=values)
    broken = replace(
        broken, values=broken.values * good.planar_integral() / broken.planar_integral()
    )
    report = _report(atoms, broken, deposit(broken, mesh_data, 2), mesh_data)
    assert abs(report.producer_error) <= 1e-12
    assert abs(report.consumer_error) <= 1e-12
    middle = report.planes_nm.index(min(report.planes_nm, key=abs))
    below = report.grid_cumulative_C[middle] / ELEMENTARY_CHARGE
    logger.info(
        "dropped Jacobian: %.4f e below z = %.3f nm where the atoms put %.4f e",
        below,
        report.planes_nm[middle],
        report.source_cumulative_C[middle] / ELEMENTARY_CHARGE,
    )
    assert below == pytest.approx(1.6, abs=0.02)
    with pytest.raises(ChargeFieldError, match="export lattice disagrees with the source atoms"):
        check_deposit_conservation(report)
    # The correct construction passes every gate, the planes included.
    check_deposit_conservation(_report(atoms, good, deposit(good, mesh_data, 2), mesh_data))


def test_ver01_ver02_correct_deposit_passes_every_gate(
    mesh_data: MeshData, several: SourceAtoms
) -> None:
    """The construction as specified passes both legs and every plane at 1e-3."""
    grid = sum_kernel(several, H).grid
    report = check_deposit_conservation(
        _report(several, grid, deposit(grid, mesh_data, 2), mesh_data)
    )
    summary = report.summary()
    logger.info("correct deposit: %s", summary)
    assert abs(report.producer_error) < 1e-12
    assert abs(report.consumer_error) < 1e-12
    assert report.worst_plane("grid")[1] < 1e-12
    assert report.worst_plane("mesh")[1] < CONSERVATION_TOL
    assert summary["per_plane"]["count"] == 12  # type: ignore[index]


# -- the frame -----------------------------------------------------------------------


def test_ver58_first_z_moment_is_the_source_moment_less_the_shift(mesh_data: MeshData) -> None:
    """With ``centre_z_nm`` applied, the deposit's first z-moment is the source's minus it (D2)."""
    centre = 0.37
    z_source = [0.4, -0.2, 1.1]
    charges = [1.0, -2.0, 0.5]
    atoms = _atoms([1.0, 2.0, 3.0], z_source, [0.1, 0.085, 0.0112], charges, shift_z_nm=centre)
    grid = sum_kernel(atoms, H).grid
    found = deposit(grid, mesh_data, 2)
    mesh = to_ngsolve(mesh_data)
    field = gridfunction(found, mesh)
    moment = 2.0 * math.pi * 1e-27 * ngs.Integrate(field * ngs.x * ngs.y, mesh, order=6)
    expected = sum(q * (z - centre) for q, z in zip(charges, z_source, strict=True))
    assert moment / ELEMENTARY_CHARGE == pytest.approx(expected, abs=1e-9)
    unshifted = _atoms([1.0, 2.0, 3.0], z_source, [0.1, 0.085, 0.0112], charges)
    plain = sum_kernel(unshifted, H).grid.integral(z_weight=sum_kernel(unshifted, H).grid.z_nm)
    assert plain / ELEMENTARY_CHARGE != pytest.approx(expected, abs=1e-3)


def test_qr12_solid_share_gate_names_the_share_and_the_shift(mesh_data: MeshData) -> None:
    """Atoms in the protein pass; the same atoms 5 nm off their frame are refused (D4)."""
    r, z = [1.0, 2.0, 3.0], [0.2, -0.5, 0.9]
    passed = check_solid_share(
        _atoms(r, z, [0.1] * 3, [1.0, -1.0, 2.0]), mesh_data, ("protein",), cell_nm=H
    )
    assert passed.share == pytest.approx(1.0)
    assert passed.by_material["protein"] == pytest.approx(4.0)
    shifted = _atoms(r, z, [0.1] * 3, [1.0, -1.0, 2.0], shift_z_nm=5.0)
    with pytest.raises(ChargeFieldError) as raised:
        check_solid_share(shifted, mesh_data, ("protein",), cell_nm=H)
    message = str(raised.value)
    assert f"{SOLID_SHARE_MIN:g}" in message
    assert "z - 5 nm" in message
    assert "0 of sum |q_i|" in message


def test_qr12_charge_on_no_element_is_refused_naming_its_location() -> None:
    """A mesh that stops short of the structure is refused, naming the (r, z) of the charge (D4)."""
    small = _mesh(r_max=1.2, protein=False)
    atoms = _atoms([1.5], [0.3], [0.1], [1.0])
    grid = sum_kernel(atoms, H).grid
    with pytest.raises(ChargeFieldError) as raised:
        deposit(grid, small, 2)
    message = str(raised.value)
    assert "falls on no element" in message
    assert "(r, z) = (1.5, 0.3) nm" in message


def test_qr12_deposit_on_a_permuted_mesh_is_refused_naming_both_digests(
    mesh_data: MeshData, several: SourceAtoms
) -> None:
    """A payload is read only on its own mesh in its own element order (D5)."""
    found = deposit(sum_kernel(several, H).grid, mesh_data, 2)
    permutation = np.random.default_rng(7).permutation(mesh_data.element_count)
    permuted = MeshData(
        vertices=mesh_data.vertices,
        triangles=mesh_data.triangles[permutation],
        triangle_material=mesh_data.triangle_material[permutation],
        materials=mesh_data.materials,
        edges=mesh_data.edges,
        edge_group=mesh_data.edge_group,
        boundaries=mesh_data.boundaries,
    )
    with pytest.raises(ChargeFieldError) as raised:
        gridfunction(found, to_ngsolve(permuted))
    message = str(raised.value)
    assert found.geometry_digest in message
    assert geometry_digest(permuted) in message

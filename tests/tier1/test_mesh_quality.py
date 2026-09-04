"""VER-10, QR-12: the element-quality gates, against the values that calibrated them."""

import numpy as np
import pytest
from scipy.optimize import brentq

from nanopnp.mesh.adapter import MeshData, from_ngsolve
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry, SlabGeometry
from nanopnp.mesh.quality import (
    QUALITY_FLOOR,
    MeshQualityError,
    check_quality,
    check_radii,
    element_quality,
    inverted_elements,
)

CHECK_TOL = 1e-12
"""Tolerance on the check values.

They are exact rationals and surds and agreed with gmsh to every digit it
printed, so this is round-off and not a physical tolerance.
"""

ROOT_THREE_HALF = np.sqrt(3.0) / 2.0
"""Height of the unit equilateral triangle."""


def isoceles_sicn(height: float) -> float:
    """SICN of an isoceles triangle on a unit base, in closed form.

    A second route to the check values: specialising the general 2x2 expression
    by hand for this family gives ``4 sqrt(3) h / (3 + 4 h^2)``, which shares no
    arithmetic with the vectorised implementation beyond the definition itself.
    """
    return 4.0 * np.sqrt(3.0) * height / (3.0 + 4.0 * height**2)


def isoceles_gamma(height: float) -> float:
    """Gamma of an isoceles triangle on a unit base: ``4h^2/((1+2b)(1/4+h^2))``."""
    leg = np.sqrt(0.25 + height**2)
    return 4.0 * height**2 / ((1.0 + 2.0 * leg) * (0.25 + height**2))


def triangle_mesh(*corners: tuple[float, float]) -> MeshData:
    """Return a one-element mesh on the three corners, in the order given."""
    return MeshData(
        vertices=np.array(corners, dtype=float),
        triangles=np.array([[0, 1, 2]]),
        triangle_material=np.array([0]),
        materials=("electrolyte",),
        edges=np.array([[0, 1]]),
        edge_group=np.array([0]),
        boundaries=("wall",),
    )


@pytest.mark.parametrize(
    ("label", "corners", "sicn", "gamma"),
    [
        ("equilateral", ((0.0, 0.0), (1.0, 0.0), (0.5, ROOT_THREE_HALF)), 1.0, 1.0),
        (
            "right isoceles",
            ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
            np.sqrt(3.0) / 2.0,
            2 * np.sqrt(2.0) - 2.0,
        ),
        (
            "sliver h=0.2",
            ((0.0, 0.0), (1.0, 0.0), (0.5, 0.2)),
            isoceles_sicn(0.2),
            isoceles_gamma(0.2),
        ),
        (
            "sliver h=0.05",
            ((0.0, 0.0), (1.0, 0.0), (0.5, 0.05)),
            isoceles_sicn(0.05),
            isoceles_gamma(0.05),
        ),
        (
            "equilateral x1000",
            ((0.0, 0.0), (1000.0, 0.0), (500.0, 1000.0 * ROOT_THREE_HALF)),
            1.0,
            1.0,
        ),
        ("clockwise equilateral", ((0.0, 0.0), (0.5, ROOT_THREE_HALF), (1.0, 0.0)), -1.0, 1.0),
    ],
)
def test_ver10_sicn_and_gamma_check_values(label, corners, sicn, gamma) -> None:
    """Both measures reproduce the six calibration triangles of the WP8 plan."""
    report = element_quality(triangle_mesh(*corners))
    assert report.sicn[0] == pytest.approx(sicn, abs=CHECK_TOL), label
    assert report.gamma[0] == pytest.approx(gamma, abs=CHECK_TOL), label


def test_ver10_gamma_is_blind_to_inversion_and_sicn_is_not() -> None:
    """The clockwise equilateral scores gamma +1: only SICN sees the winding."""
    clockwise = triangle_mesh((0.0, 0.0), (0.5, ROOT_THREE_HALF), (1.0, 0.0))
    report = element_quality(clockwise)
    assert report.gamma[0] == pytest.approx(1.0, abs=CHECK_TOL)
    assert report.sicn[0] == pytest.approx(-1.0, abs=CHECK_TOL)
    assert inverted_elements(clockwise) == (0,)


def test_ver10_the_two_measures_are_not_interchangeable() -> None:
    """At SICN = 0.3 gamma is 0.1298, and at gamma = 0.3 SICN is 0.4687.

    The arithmetic behind reading section 5.2.2's gate as a conjunction: the two
    thresholds differ by a factor of 1.56 in the height of an isoceles element on
    a unit base, so gating either measure alone admits meshes the other rejects.
    """
    height_at_sicn_floor = brentq(lambda h: isoceles_sicn(h) - QUALITY_FLOOR, 0.01, 0.5)
    height_at_gamma_floor = brentq(lambda h: isoceles_gamma(h) - QUALITY_FLOOR, 0.01, 0.6)
    assert height_at_sicn_floor == pytest.approx(0.1329661, abs=1e-6)
    assert height_at_gamma_floor == pytest.approx(0.2155084, abs=1e-6)

    at_sicn_floor = element_quality(
        triangle_mesh((0.0, 0.0), (1.0, 0.0), (0.5, height_at_sicn_floor))
    )
    at_gamma_floor = element_quality(
        triangle_mesh((0.0, 0.0), (1.0, 0.0), (0.5, height_at_gamma_floor))
    )
    assert at_sicn_floor.sicn[0] == pytest.approx(QUALITY_FLOOR, abs=1e-9)
    assert at_sicn_floor.gamma[0] == pytest.approx(0.1298415, abs=1e-6)
    assert at_gamma_floor.gamma[0] == pytest.approx(QUALITY_FLOOR, abs=1e-9)
    assert at_gamma_floor.sicn[0] == pytest.approx(0.4686726, abs=1e-6)
    assert height_at_gamma_floor / height_at_sicn_floor == pytest.approx(1.6208, abs=1e-4)


def test_qr12_a_sliver_aborts_naming_the_element_and_its_centroid() -> None:
    """QR-12: the gate, the offending quantity and the location are all in the message."""
    sliver = triangle_mesh((1.0, 0.0), (2.0, 0.0), (1.5, 0.05))
    with pytest.raises(MeshQualityError) as raised:
        check_quality(sliver, where="the sliver fixture")
    error = raised.value
    assert error.gate == "minimum SICN"
    assert "0.115086" in error.quantity
    assert "element 0" in error.location
    assert "1.5" in error.location and "0.0166" in error.location
    assert "the sliver fixture" in str(error)


def test_qr12_an_inverted_element_aborts_under_its_own_name() -> None:
    """Inversion is reported as inversion, not as a low quality number."""
    with pytest.raises(MeshQualityError) as raised:
        check_quality(triangle_mesh((0.0, 0.0), (0.5, ROOT_THREE_HALF), (1.0, 0.0)))
    assert raised.value.gate == "inverted element"
    assert "SICN <= 0" in raised.value.quantity


def test_qr12_a_negative_radius_aborts_naming_the_vertex() -> None:
    """An (r, z) mesh crossing the axis integrates to negative volume (CON-04)."""
    with pytest.raises(MeshQualityError) as raised:
        check_radii(triangle_mesh((-0.5, 0.0), (1.0, 0.0), (0.5, 1.0)))
    assert raised.value.gate == "negative radius"
    assert "-0.5" in raised.value.quantity
    assert "vertex 0" in raised.value.location


@pytest.mark.parametrize(
    ("geometry", "options", "elements", "min_sicn", "min_gamma"),
    [
        (SlabGeometry(3.0), {"maxh_nm": 0.5, "wall_h_nm": 0.05}, 192, 0.7860, 0.7489),
        (CylinderGeometry(2.0, 4.0), {"maxh_nm": 0.5, "wall_h_nm": 0.05}, 811, 0.6473, 0.5510),
        (
            CylindricalPoreGeometry(2.0, 6.0, 10.0),
            {"maxh_nm": 4.0, "wall_h_nm": 1.0},
            124,
            0.7138,
            0.6860,
        ),
        (
            CylindricalPoreGeometry(2.0, 13.0, 50.0),
            {"maxh_nm": 2.0, "wall_h_nm": 0.05},
            8141,
            0.7008,
            0.6384,
        ),
    ],
)
def test_ver10_phase_zero_geometries_clear_the_gate(
    geometry, options, elements, min_sicn, min_gamma
) -> None:
    """Netgen's graded free meshing is already in the reference model's quality band.

    The reference COMSOL mesh reports minimum element quality 0.6378 over 120,917
    triangles (section 5.2.2); these are the same band at a fortieth of the size,
    which is what makes the 0.3 gate unconditional rather than opt-in.
    """
    data = from_ngsolve(geometry.generate(**options))
    report = check_quality(data)
    assert report.element_count == elements
    assert report.min_sicn == pytest.approx(min_sicn, abs=5e-4)
    assert report.min_gamma == pytest.approx(min_gamma, abs=5e-4)
    assert not report.inverted


def test_ver10_gmsh_agrees_on_the_magnitude_of_both_measures() -> None:
    """Optional calibration against the implementation that set the 0.3 threshold.

    Skipped when gmsh is absent — and on ``OSError`` as well as ``ImportError``,
    because the gmsh wheel dlopens X and GL at import and raises ``OSError:
    libGLU.so.1`` in a bare container, which a bare ``importorskip`` turns into
    an error rather than a skip [tested]. Magnitudes only: gmsh returns +1 for a
    clockwise 2-D element in a discrete entity, so the sign is ours (CON-10 keeps
    gmsh off every other path).
    """
    try:
        import gmsh
    except (ImportError, OSError) as error:  # pragma: no cover - environment-dependent
        pytest.skip(f"gmsh unavailable: {error}")

    corners = [
        ((0.0, 0.0), (1.0, 0.0), (0.5, ROOT_THREE_HALF)),
        ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
        ((0.0, 0.0), (1.0, 0.0), (0.5, 0.2)),
        ((0.0, 0.0), (1.0, 0.0), (0.5, 0.05)),
        ((0.0, 0.0), (0.5, ROOT_THREE_HALF), (1.0, 0.0)),
    ]
    gmsh.initialize()
    try:
        for index, triangle in enumerate(corners):
            gmsh.model.add(f"triangle-{index}")
            surface = gmsh.model.addDiscreteEntity(2)
            tags = [
                gmsh.model.mesh.addNodes(
                    2, surface, [1, 2, 3], [c for p in triangle for c in (*p, 0.0)]
                )
            ]
            del tags
            gmsh.model.mesh.addElementsByType(surface, 2, [1], [1, 2, 3])
            elements = gmsh.model.mesh.getElementsByType(2)[0]
            ours = element_quality(triangle_mesh(*triangle))
            for name, mine in (("minSICN", ours.sicn[0]), ("gamma", ours.gamma[0])):
                theirs = gmsh.model.mesh.getElementQualities(elements, name)[0]
                assert abs(mine) == pytest.approx(theirs, abs=1e-9)
            gmsh.model.remove()
    finally:
        gmsh.finalize()

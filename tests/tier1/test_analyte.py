"""The analyte bodies and the geometries that embed them (FR-21, CON-02).

Every one of VER-19 to VER-22 is a force on an embedded body, so these tests are
about the two things that would make such a force quietly wrong: a domain the
fluid regular expression accidentally includes, and a surface the pore's own
boundary classifier accidentally swallows. Both are silent when they fail — the
solve converges, the integral returns a number — so both are pinned here rather
than left to a benchmark to notice.
"""

import math

import pytest

from nanopnp.geometry.analyte import (
    ANALYTE_BOUNDARY,
    ANALYTE_DOMAIN,
    AnalyteGeometryError,
    AnalyteInBoxGeometry,
    PoreWithAnalyte,
    SphereBody,
    SpheroidBody,
)
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS, CylindricalPoreGeometry

PORE = CylindricalPoreGeometry(
    pore_radius_nm=3.0, membrane_thickness_nm=8.0, reservoir_radius_nm=12.0
)
"""A pore roomy enough to hold the test body with fluid to spare."""


def _measure(mesh: object, region: object) -> float:
    """Return the meridian area or arc length of a mesh region, unweighted by ``r``.

    Unweighted deliberately: these tests are about which elements a name selects,
    not about an axisymmetric integral, and ``pi a^2 / 2`` is a number a reader
    can check by eye where ``2 pi int r`` is not.
    """
    import ngsolve as ngs

    return float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=region))


def test_fr21_sphere_volume_is_the_closed_form() -> None:
    """``4/3 pi a^3``; it is the denominator of ``rho_part = q/V`` and so load-bearing."""
    assert SphereBody(radius_nm=2.5).volume_nm3 == pytest.approx(4.0 / 3.0 * math.pi * 2.5**3)


@pytest.mark.parametrize(
    ("semi_radial_nm", "semi_axial_nm"),
    [(2.9, 3.35), (3.35, 2.9), (2.0, 2.0)],
    ids=["prolate", "oblate", "sphere"],
)
def test_fr21_spheroid_volume_is_the_closed_form(
    semi_radial_nm: float, semi_axial_nm: float
) -> None:
    """``4/3 pi b^2 c``, prolate and oblate alike.

    The prolate case is the haemoglobin idealisation of ``.knowledge/05``
    section 10, 6.7 nm by 5.8 nm, and is the one whose profile ``Ellipse``
    refuses to draw directly.
    """
    body = SpheroidBody(semi_radial_nm=semi_radial_nm, semi_axial_nm=semi_axial_nm)
    assert body.volume_nm3 == pytest.approx(4.0 / 3.0 * math.pi * semi_radial_nm**2 * semi_axial_nm)


def test_fr21_charge_density_is_the_net_charge_over_the_volume() -> None:
    """``rho_part = q/V`` in C/m^3 (``.knowledge/05`` section 10.3).

    Checked as a charge rather than as a density: integrating the density back
    over the body's own volume must return the charge it was built from, which
    is the only thing the sign and the nm-to-m conversion can both get wrong.
    """
    from nanopnp.core.constants import ELEMENTARY_CHARGE

    body = SphereBody(radius_nm=2.7)
    volume_m3 = body.volume_nm3 * 1e-27
    assert body.charge_density_C_m3(-4.0) * volume_m3 == pytest.approx(-4.0 * ELEMENTARY_CHARGE)


def test_fr21_a_degenerate_body_raises_at_construction() -> None:
    """A zero or negative semi-axis is a mesher crash deferred, so it is refused here."""
    with pytest.raises(AnalyteGeometryError, match="must be positive"):
        SphereBody(radius_nm=0.0)
    with pytest.raises(AnalyteGeometryError, match="semi_axial_nm"):
        SpheroidBody(semi_radial_nm=1.0, semi_axial_nm=-1.0)


class TestAnalyteInBox:
    """The benchmark domain of VER-19 to VER-22."""

    BODY = SphereBody(radius_nm=1.0)
    GEOMETRY = AnalyteInBoxGeometry(body=BODY, outer_radius_nm=10.0)

    @pytest.fixture(scope="class")
    @classmethod
    def mesh(cls) -> object:
        """Return the meshed box, built once for the whole class."""
        return cls.GEOMETRY.generate(maxh_nm=2.0, wall_h_nm=0.2)

    def test_fr21_the_box_carries_an_analyte_domain_and_an_analyte_boundary(
        self, mesh: object
    ) -> None:
        """The body is a named domain glued in, not a hole cut out.

        That is what makes the PHY-09 dielectric jump a material entry rather
        than a boundary condition, and what leaves ``n.J_i = 0`` natural.
        """
        assert set(mesh.GetMaterials()) == {"electrolyte", ANALYTE_DOMAIN}
        assert set(mesh.GetBoundaries()) == {"axis", ANALYTE_BOUNDARY, "outer"}

    def test_fr21_the_fluid_regex_selects_the_fluid_and_not_the_body(self, mesh: object) -> None:
        """``ELECTROLYTE_DOMAINS`` matches a material name in full, so it excludes it.

        If it did not, every domain integral in ``post/`` — the currents, the
        indicator forms, the force extension band — would run over the solid as
        well, and none of them would say so. Asserted as a partition, which is
        exact on the meshed geometry: the two regions cover the whole of it and
        overlap nowhere.
        """
        fluid = _measure(mesh, mesh.Materials(ELECTROLYTE_DOMAINS))
        body = _measure(mesh, mesh.Materials(ANALYTE_DOMAIN))
        whole = _measure(mesh, mesh.Materials(".*"))
        assert body > 0.0, "the fluid regex has swallowed the body"
        assert fluid + body == pytest.approx(whole, rel=1e-12)

    def test_fr21_the_body_is_a_half_disc_of_the_right_size(self, mesh: object) -> None:
        """The meridian area against ``pi a^2 / 2``, inscribed.

        One-sided, because a straight-edged mesh can only cut the corner off a
        curved body: an area *above* the exact one would mean the domain is
        picking up fluid rather than approximating the body.
        """
        exact = 0.5 * math.pi * self.BODY.radius_nm**2
        measured = _measure(mesh, mesh.Materials(ANALYTE_DOMAIN))
        assert exact * 0.98 < measured <= exact

    def test_fr21_the_bodys_own_segment_of_the_axis_is_named_axis(self, mesh: object) -> None:
        """The body must not take its diameter out of the axis region.

        NUM-06 imposes ``u_r = 0`` and the natural symmetry conditions on
        ``axis``; naming the whole of the body's profile ``analyte`` would leave
        the segment through its centre out of that region, and the solve would
        be posed on a domain that is not the half-plane it is meant to be.
        Measured as a length: the axis runs the full diameter of the box.
        """
        assert _measure(mesh, mesh.Boundaries("axis")) == pytest.approx(
            2.0 * self.GEOMETRY.outer_radius_nm, rel=1e-6
        )

    def test_fr21_the_analyte_boundary_is_the_bodys_meridian_arc(self, mesh: object) -> None:
        """Half a circle's circumference, short by the polygonal approximation.

        A one-sided tolerance, because a straight-edged mesh can only cut the
        corner: an arc length *above* the exact one would mean the boundary is
        picking up something that is not the body.
        """
        exact = math.pi * self.BODY.radius_nm
        measured = _measure(mesh, mesh.Boundaries(ANALYTE_BOUNDARY))
        assert exact * 0.99 < measured <= exact

    def test_fr21_a_body_reaching_the_outer_boundary_raises(self) -> None:
        """Rather than leaving the mesher to answer it with slivers (QR-12)."""
        with pytest.raises(AnalyteGeometryError, match="reaches"):
            AnalyteInBoxGeometry(body=SphereBody(radius_nm=9.0), outer_radius_nm=10.0)


class TestPoreWithAnalyte:
    """The reference-shaped case RSK-04 is stated on."""

    BODY = SpheroidBody(semi_radial_nm=1.45, semi_axial_nm=1.675)
    GEOMETRY = PoreWithAnalyte(pore=PORE, body=BODY, analyte_h_nm=0.3)

    @pytest.fixture(scope="class")
    @classmethod
    def mesh(cls) -> object:
        """Return the meshed pore-with-analyte, built once for the whole class."""
        return cls.GEOMETRY.generate(maxh_nm=2.0)

    def test_fr21_the_pore_keeps_every_domain_and_boundary_name(self, mesh: object) -> None:
        """Only ``analyte`` is new.

        ``lumen_band``, ``axial_indicator`` and the default
        ``CoupledBoundaries`` are all written against these names, so a body in
        the lumen must add to the vocabulary and never subtract from it.
        """
        assert set(mesh.GetMaterials()) == {
            "electrolyte",
            "membrane",
            "cis",
            "trans",
            ANALYTE_DOMAIN,
        }
        assert set(mesh.GetBoundaries()) >= {
            "axis",
            "wall",
            "membrane",
            "membrane_outer",
            "cis",
            "trans",
            ANALYTE_BOUNDARY,
        }

    def test_fr21_the_body_does_not_eat_the_pore_wall(self, mesh: object) -> None:
        """The wall is still the full length of the lumen, exactly.

        The classifier that names the pore's edges matches on position, so the
        failure this guards against is the body's surface being swept into
        ``wall`` — after which the VER-22 force integral would be taken over the
        wall and the body together, and would still return a plausible number.
        """
        assert _measure(mesh, mesh.Boundaries("wall")) == pytest.approx(
            PORE.membrane_thickness_nm, rel=1e-9
        )
        assert _measure(mesh, mesh.Boundaries(ANALYTE_BOUNDARY)) == pytest.approx(
            _analytic_ellipse_perimeter(self.BODY) * 0.5, rel=2e-2
        )

    def test_fr21_the_lumen_lost_exactly_the_bodys_area(self, mesh: object) -> None:
        """The body was cut from the lumen and glued back, so the total is unchanged."""
        body = _measure(mesh, mesh.Materials(ANALYTE_DOMAIN))
        exact = 0.5 * math.pi * self.BODY.semi_radial_nm * self.BODY.semi_axial_nm
        # Inscribed, for the reason given on the box's own area test.
        assert exact * 0.98 < body <= exact
        fluid = _measure(mesh, mesh.Materials(ELECTROLYTE_DOMAINS))
        whole = _measure(mesh, mesh.Materials(".*"))
        assert fluid + body == pytest.approx(whole - _measure(mesh, mesh.Materials("membrane")))

    def test_fr21_a_body_wider_than_the_lumen_raises(self) -> None:
        """Not a degenerate mesh: an error naming the radius and the wall (QR-12)."""
        with pytest.raises(AnalyteGeometryError, match="lumen ends"):
            PoreWithAnalyte(pore=PORE, body=SphereBody(radius_nm=3.5))

    def test_fr21_a_body_crossing_a_pore_mouth_raises(self) -> None:
        """The same for the axial extent; the lumen is a rectangle, so both are exact."""
        with pytest.raises(AnalyteGeometryError, match="pore mouth"):
            PoreWithAnalyte(pore=PORE, body=SphereBody(radius_nm=2.0, z_nm=3.0))


def _analytic_ellipse_perimeter(body: SpheroidBody) -> float:
    """Return Ramanujan's approximation to the ellipse perimeter, in nm.

    Only a scale reference for the meshed arc length — the tolerance around it
    is 2 %, an order of magnitude looser than the approximation's own error.
    """
    a = body.semi_radial_nm
    b = body.semi_axial_nm
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1.0 + 3.0 * h / (10.0 + math.sqrt(4.0 - 3.0 * h)))

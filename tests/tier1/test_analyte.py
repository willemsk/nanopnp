"""The analyte bodies and the geometries that embed them (FR-21, CON-02)."""

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
    import ngsolve as ngs

    return float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=region))


def test_fr21_sphere_volume_is_the_closed_form() -> None:
    assert SphereBody(radius_nm=2.5).volume_nm3 == pytest.approx(4.0 / 3.0 * math.pi * 2.5**3)


@pytest.mark.parametrize(
    ("semi_radial_nm", "semi_axial_nm"),
    [(2.9, 3.35), (3.35, 2.9), (2.0, 2.0)],
    ids=["prolate", "oblate", "sphere"],
)
def test_fr21_spheroid_volume_is_the_closed_form(
    semi_radial_nm: float, semi_axial_nm: float
) -> None:
    body = SpheroidBody(semi_radial_nm=semi_radial_nm, semi_axial_nm=semi_axial_nm)
    assert body.volume_nm3 == pytest.approx(4.0 / 3.0 * math.pi * semi_radial_nm**2 * semi_axial_nm)


def test_fr21_charge_density_is_the_net_charge_over_the_volume() -> None:
    from nanopnp.core.constants import ELEMENTARY_CHARGE

    body = SphereBody(radius_nm=2.7)
    volume_m3 = body.volume_nm3 * 1e-27
    assert body.charge_density_C_m3(-4.0) * volume_m3 == pytest.approx(-4.0 * ELEMENTARY_CHARGE)


def test_fr21_a_degenerate_body_raises_at_construction() -> None:
    with pytest.raises(AnalyteGeometryError, match="must be positive"):
        SphereBody(radius_nm=0.0)
    with pytest.raises(AnalyteGeometryError, match="semi_axial_nm"):
        SpheroidBody(semi_radial_nm=1.0, semi_axial_nm=-1.0)


# VER-19, VER-22
class TestAnalyteInBox:
    BODY = SphereBody(radius_nm=1.0)
    GEOMETRY = AnalyteInBoxGeometry(body=BODY, outer_radius_nm=10.0)

    @pytest.fixture(scope="class")
    @classmethod
    def mesh(cls) -> object:
        return cls.GEOMETRY.generate(maxh_nm=2.0, wall_h_nm=0.2)

    # PHY-09
    def test_fr21_the_box_carries_an_analyte_domain_and_an_analyte_boundary(
        self, mesh: object
    ) -> None:
        assert set(mesh.GetMaterials()) == {"electrolyte", ANALYTE_DOMAIN}
        assert set(mesh.GetBoundaries()) == {"axis", ANALYTE_BOUNDARY, "outer"}

    def test_fr21_the_fluid_regex_selects_the_fluid_and_not_the_body(self, mesh: object) -> None:
        fluid = _measure(mesh, mesh.Materials(ELECTROLYTE_DOMAINS))
        body = _measure(mesh, mesh.Materials(ANALYTE_DOMAIN))
        whole = _measure(mesh, mesh.Materials(".*"))
        assert body > 0.0, "the fluid regex has swallowed the body"
        assert fluid + body == pytest.approx(whole, rel=1e-12)

    def test_fr21_the_body_is_a_half_disc_of_the_right_size(self, mesh: object) -> None:
        exact = 0.5 * math.pi * self.BODY.radius_nm**2
        measured = _measure(mesh, mesh.Materials(ANALYTE_DOMAIN))
        assert exact * 0.98 < measured <= exact

    # NUM-06
    def test_fr21_the_bodys_own_segment_of_the_axis_is_named_axis(self, mesh: object) -> None:
        assert _measure(mesh, mesh.Boundaries("axis")) == pytest.approx(
            2.0 * self.GEOMETRY.outer_radius_nm, rel=1e-6
        )

    def test_fr21_the_analyte_boundary_is_the_bodys_meridian_arc(self, mesh: object) -> None:
        exact = math.pi * self.BODY.radius_nm
        measured = _measure(mesh, mesh.Boundaries(ANALYTE_BOUNDARY))
        assert exact * 0.99 < measured <= exact

    # QR-12
    def test_fr21_a_body_reaching_the_outer_boundary_raises(self) -> None:
        with pytest.raises(AnalyteGeometryError, match="reaches"):
            AnalyteInBoxGeometry(body=SphereBody(radius_nm=9.0), outer_radius_nm=10.0)


class TestPoreWithAnalyte:
    BODY = SpheroidBody(semi_radial_nm=1.45, semi_axial_nm=1.675)
    GEOMETRY = PoreWithAnalyte(pore=PORE, body=BODY, analyte_h_nm=0.3)

    @pytest.fixture(scope="class")
    @classmethod
    def mesh(cls) -> object:
        return cls.GEOMETRY.generate(maxh_nm=2.0)

    def test_fr21_the_pore_keeps_every_domain_and_boundary_name(self, mesh: object) -> None:
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

    # VER-22
    def test_fr21_the_body_does_not_eat_the_pore_wall(self, mesh: object) -> None:
        assert _measure(mesh, mesh.Boundaries("wall")) == pytest.approx(
            PORE.membrane_thickness_nm, rel=1e-9
        )
        assert _measure(mesh, mesh.Boundaries(ANALYTE_BOUNDARY)) == pytest.approx(
            _analytic_ellipse_perimeter(self.BODY) * 0.5, rel=2e-2
        )

    def test_fr21_the_lumen_lost_exactly_the_bodys_area(self, mesh: object) -> None:
        body = _measure(mesh, mesh.Materials(ANALYTE_DOMAIN))
        exact = 0.5 * math.pi * self.BODY.semi_radial_nm * self.BODY.semi_axial_nm
        assert exact * 0.98 < body <= exact
        fluid = _measure(mesh, mesh.Materials(ELECTROLYTE_DOMAINS))
        whole = _measure(mesh, mesh.Materials(".*"))
        assert fluid + body == pytest.approx(whole - _measure(mesh, mesh.Materials("membrane")))

    # QR-12
    def test_fr21_a_body_wider_than_the_lumen_raises(self) -> None:
        with pytest.raises(AnalyteGeometryError, match="lumen ends"):
            PoreWithAnalyte(pore=PORE, body=SphereBody(radius_nm=3.5))

    def test_fr21_a_body_crossing_a_pore_mouth_raises(self) -> None:
        with pytest.raises(AnalyteGeometryError, match="pore mouth"):
            PoreWithAnalyte(pore=PORE, body=SphereBody(radius_nm=2.0, z_nm=3.0))


def _analytic_ellipse_perimeter(body: SpheroidBody) -> float:
    a = body.semi_radial_nm
    b = body.semi_axial_nm
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1.0 + 3.0 * h / (10.0 + math.sqrt(4.0 - 3.0 * h)))

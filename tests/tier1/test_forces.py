"""The NUM-28 axial force on an analyte: w, the tensors and the route record (VER-22)."""

import math

import numpy as np
import pytest

from nanopnp.core.scaling import Scales
from nanopnp.geometry.analyte import AnalyteInBoxGeometry, PoreWithAnalyte, SphereBody
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS, CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.physics.models import ModelSolution
from nanopnp.post import qoi
from nanopnp.post.forces import (
    FORCE_ROUTE_TOLERANCE_N,
    AnalyteForces,
    ExtensionError,
    ForceAgreement,
    ForceComponents,
    ForceDisagreementError,
    ForceSurfaceError,
    axial_extension,
    check_extension,
    check_force_surface,
    hydrodynamic_stress,
    maxwell_stress,
    reaction_force,
)

BODY_RADIUS_NM = 1.0


class TestAxialExtension:
    @pytest.fixture(scope="class")
    @classmethod
    def mesh(cls) -> object:
        geometry = AnalyteInBoxGeometry(SphereBody(radius_nm=BODY_RADIUS_NM), outer_radius_nm=10.0)
        return geometry.generate(maxh_nm=1.5, wall_h_nm=0.2)

    @pytest.fixture(scope="class")
    @classmethod
    def extension(cls, mesh: object) -> object:
        return axial_extension(mesh, inner_nm=1.0, outer_nm=3.0)

    def test_num28_extension_is_ez_on_the_body_and_zero_on_the_outer_boundary(
        self, extension: object, mesh: object
    ) -> None:
        check_extension(extension, mesh)

    def test_num28_check_extension_rejects_an_inverted_band(
        self, extension: object, mesh: object
    ) -> None:
        import ngsolve as ngs

        inverted = ngs.GridFunction(extension.space, name="w_inverted")
        inverted.Set(ngs.CF((0.0, 1.0)) - extension)
        with pytest.raises(ExtensionError) as raised:
            check_extension(inverted, mesh)
        assert "inverted" in str(raised.value)

    # QR-12
    def test_num28_check_extension_names_a_boundary_the_mesh_does_not_have(
        self, extension: object, mesh: object
    ) -> None:
        with pytest.raises(ExtensionError, match="no boundary matching 'no_such_body'"):
            check_extension(extension, mesh, body="no_such_body")

    def test_num28_domain_form_is_invariant_to_the_pressure_datum(
        self, extension: object, mesh: object
    ) -> None:
        import ngsolve as ngs

        fluid = mesh.Materials(ELECTROLYTE_DOMAINS)
        gradient = ngs.grad(extension)
        divergence = AXISYMMETRIC.integrate(
            gradient[0, 0] + gradient[1, 1], mesh, definedon=fluid, what="the divergence of w"
        )
        scale = AXISYMMETRIC.integrate(
            ngs.sqrt(ngs.InnerProduct(gradient, gradient)),
            mesh,
            definedon=fluid,
            what="the magnitude of grad(w)",
        )
        assert abs(divergence) < 1e-10 * scale, (
            f"int div(w) r dr dz = {divergence:.3e} against a gradient scale of {scale:.3e}; "
            "the domain force then depends on the pressure datum, which VER-19 and VER-21 do "
            "not fix"
        )

    @pytest.mark.parametrize(
        ("inner_nm", "outer_nm"),
        [(2.0, 2.0), (3.0, 1.0), (-1.0, 2.0)],
        ids=["no width", "inverted ends", "negative inner"],
    )
    def test_num28_extension_rejects_a_shell_that_is_not_a_shell(
        self, mesh: object, inner_nm: float, outer_nm: float
    ) -> None:
        with pytest.raises(ExtensionError):
            axial_extension(mesh, inner_nm=inner_nm, outer_nm=outer_nm)


def test_num28_the_shell_may_cross_a_pore_mouth() -> None:
    import ngsolve as ngs

    pore = CylindricalPoreGeometry(
        pore_radius_nm=6.0, membrane_thickness_nm=13.0, reservoir_radius_nm=12.0
    )
    body = SphereBody(radius_nm=BODY_RADIUS_NM, z_nm=4.5)
    mesh = PoreWithAnalyte(pore, body, analyte_h_nm=0.3).generate(maxh_nm=2.0)
    assert "default" in mesh.GetBoundaries()

    extension = axial_extension(mesh, inner_nm=1.0, outer_nm=3.0)
    mouth = mesh.Boundaries("default")
    crossing = float(ngs.Integrate(ngs.InnerProduct(extension, extension), mesh, definedon=mouth))
    assert crossing > 1e-6, "the shell does not reach a mouth, so this pins nothing"


def test_num28_maxwell_stress_check_values() -> None:
    import ngsolve as ngs

    stress = maxwell_stress(ngs.CF((0.0, 1.0)), 2.0)
    mesh = ngs.Mesh(_unit_square())
    values = [float(ngs.Integrate(stress[i, j], mesh)) for i in range(2) for j in range(2)]
    assert values == pytest.approx([-1.0, 0.0, 0.0, 1.0], abs=1e-12)


def test_num28_hydrodynamic_stress_check_values() -> None:
    import ngsolve as ngs

    stress = hydrodynamic_stress(ngs.CF((0.0, 1.0, 0.0, 0.0), dims=(2, 2)), 5.0, 3.0)
    mesh = ngs.Mesh(_unit_square())
    values = [float(ngs.Integrate(stress[i, j], mesh)) for i in range(2) for j in range(2)]
    assert values == pytest.approx([-5.0, 3.0, 3.0, -5.0], abs=1e-12)


def _unit_square() -> object:
    from netgen.occ import OCCGeometry, Rectangle

    return OCCGeometry(Rectangle(1.0, 1.0).Face(), dim=2).GenerateMesh(maxh=2.0)


def test_num28_force_scale_is_eps_vt_squared_and_carries_no_length() -> None:
    small = Scales(length_nm=1.0, concentration_M=0.3)
    large = Scales(length_nm=10.0, concentration_M=0.3)
    assert small.force_N == pytest.approx(small.pressure_Pa * small.length_m**2, rel=1e-12)
    assert large.force_N == pytest.approx(small.force_N, rel=1e-12)
    assert small.force_N == pytest.approx(4.568e-13, rel=1e-3)
    assert small.summary()["force_N"] == small.force_N


def test_num27_the_azimuthal_factor_is_defined_in_one_place() -> None:
    from nanopnp.post import forces

    assert forces.TWO_PI is qoi.TWO_PI
    assert math.isclose(qoi.TWO_PI, 2.0 * math.pi, rel_tol=1e-15)


def test_num29_the_route_tolerance_is_a_fifth_of_a_force_unit() -> None:
    tolerance_N = FORCE_ROUTE_TOLERANCE_N
    assert tolerance_N == pytest.approx(1e-13)
    scales = Scales(length_nm=2.0, concentration_M=0.3)
    assert tolerance_N / scales.force_N == pytest.approx(0.219, abs=5e-4)


class TestForceAgreement:
    def test_num29_agreement_is_absolute_and_not_relative(self) -> None:
        agreement = ForceAgreement(
            domain=ForceComponents(em_N=10e-12, hd_N=-10.02e-12),
            surface=ForceComponents(em_N=10.05e-12, hd_N=-10.02e-12),
        )
        assert agreement.total_difference_N == pytest.approx(0.05e-12)
        agreement.check()

    def test_num29_a_disagreement_beyond_the_tolerance_raises(self) -> None:
        agreement = ForceAgreement(
            domain=ForceComponents(em_N=10e-12, hd_N=-10e-12),
            surface=ForceComponents(em_N=10.2e-12, hd_N=-10e-12),
        )
        with pytest.raises(ForceDisagreementError):
            agreement.check()

    def test_num29_the_message_names_all_three_routes(self) -> None:
        agreement = ForceAgreement(
            domain=ForceComponents(em_N=11e-12, hd_N=-10e-12),
            surface=ForceComponents(em_N=12e-12, hd_N=-10e-12),
            reaction_hd_N=-10e-12,
        )
        with pytest.raises(ForceDisagreementError) as raised:
            agreement.check()
        message = str(raised.value)
        for label in ("Domain (A)", "Surface (B)", "Reaction (C)"):
            assert label in message
        for value in ("+11.0000", "+12.0000", "-10.0000"):
            assert value in message
        assert "RSK-04" in message

    def test_num29_route_c_is_the_oracle_of_the_hydrodynamic_split(self) -> None:
        agreement = ForceAgreement(
            domain=ForceComponents(em_N=15e-12, hd_N=-15e-12),
            surface=ForceComponents(em_N=15e-12, hd_N=-15e-12),
            reaction_hd_N=-10e-12,
        )
        assert agreement.total_difference_N == pytest.approx(0.0, abs=1e-18)
        assert agreement.hydrodynamic_difference_N == pytest.approx(5e-12)
        with pytest.raises(ForceDisagreementError):
            agreement.check()

    def test_num29_without_route_c_the_split_is_unchecked_and_says_so(self) -> None:
        agreement = ForceAgreement(
            domain=ForceComponents(em_N=15e-12, hd_N=-15e-12),
            surface=ForceComponents(em_N=16e-12, hd_N=-15e-12),
        )
        assert agreement.hydrodynamic_difference_N == 0.0
        with pytest.raises(ForceDisagreementError) as raised:
            agreement.check()
        assert "not taken" in str(raised.value)


# NUM-27
def test_fr25_the_summary_records_the_convention_and_the_routes() -> None:
    forces = AnalyteForces(
        forces=ForceComponents(em_N=10e-12, hd_N=-9e-12),
        dielectric_gradient_N=0.0,
        agreement=None,
    )
    record = forces.summary()
    assert record["two_pi_included"] is True
    assert record["routes_checked"] is False
    assert record["total_N"] == pytest.approx(1e-12)
    assert forces.total_N == pytest.approx(1e-12)
    assert "route_agreement" not in record

    checked = AnalyteForces(
        forces=forces.forces,
        dielectric_gradient_N=0.0,
        agreement=ForceAgreement(domain=forces.forces, surface=forces.forces),
    )
    assert checked.summary()["routes_checked"] is True
    assert "route_agreement" in checked.summary()


def test_num28_a_model_without_a_flow_block_has_no_hydrodynamic_force() -> None:
    solution = ModelSolution(model=models.create("pnp"), space=None, state=None)
    with pytest.raises(TypeError) as raised:
        reaction_force(solution)
    assert "no flow block" in str(raised.value)


# NUM-25
def test_num28_the_reaction_route_needs_the_residual_the_solve_assembled() -> None:
    solution = ModelSolution(model=models.create("pnp-ns"), space=None, state=None)
    with pytest.raises(ValueError, match="no residual form"):
        reaction_force(solution)


# VER-70
def test_qr12_the_boundary_checks_of_the_force_routes_refuse_what_a_nan_would_pass() -> None:
    import ngsolve as ngs

    from nanopnp.post.forces import _boundary_region, _check_fluid_side, _oriented_normal

    mesh = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=1.0)
    with pytest.raises(ValueError, match="no boundary matching"):
        _boundary_region(mesh, "no-such-boundary")
    region, arc = _boundary_region(mesh, "wall")
    assert arc > 0.0
    with pytest.raises(ValueError, match="cannot orient the normal"):
        _oriented_normal(mesh, region, float("nan"))
    with pytest.raises(ValueError, match="solid side"):
        _check_fluid_side(mesh, ngs.CF(1.0), ngs.CF(1.0), region, float("nan"))


def _body_in(*neighbours: str) -> MeshData:
    # A square body of two triangles whose bottom, right, top and left edges each meet one triangle.
    vertices = [(1, 1), (2, 1), (2, 2), (1, 2), (1.5, 0), (3, 1.5), (1.5, 3), (0.5, 1.5)]
    triangles = [(0, 1, 2), (0, 2, 3), (0, 4, 1), (1, 5, 2), (2, 6, 3), (3, 7, 0)]
    names = sorted({"analyte", *neighbours})
    material = [names.index("analyte")] * 2 + [names.index(n) for n in neighbours]
    return MeshData(
        vertices=np.array(vertices, dtype=float),
        triangles=np.array(triangles),
        triangle_material=np.array(material),
        materials=tuple(names),
        edges=np.array([(0, 1), (1, 2), (2, 3), (3, 0)]),
        edge_group=np.zeros(4, dtype=int),
        boundaries=("analyte",),
    )


def test_num29_a_force_surface_meeting_two_materials_is_refused() -> None:
    one_fluid = _body_in("electrolyte", "electrolyte", "electrolyte", "electrolyte")
    assert check_force_surface(one_fluid) == ("analyte", "electrolyte")
    # The fluid's three domain names are one material, so a body straddling the seam between
    # the lumen and a reservoir is orientable and is not refused.
    straddling = _body_in("cis", "electrolyte", "trans", "electrolyte")
    assert check_force_surface(straddling) == ("analyte", "electrolyte")
    # A fluid on one side and a solid on the other is the pair the gate is for.
    with pytest.raises(ForceSurfaceError) as raised:
        check_force_surface(_body_in("membrane", "electrolyte", "electrolyte", "electrolyte"))
    message = str(raised.value)
    assert "analyte | membrane" in message and "analyte | electrolyte" in message
    with pytest.raises(ForceSurfaceError, match="no boundary matching"):
        check_force_surface(one_fluid, "wall")

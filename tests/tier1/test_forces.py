"""The NUM-28 axial force on an analyte: ``w``, the tensors and the route record.

Nothing here solves anything. The benchmarks of VER-19 to VER-22 measure whether
the force is *right*; these tests pin the three things that would make it quietly
wrong before any physics is involved — an extension that is not exactly ``e_z``
on the body, a stress tensor with a flipped sign, and a route-agreement check
whose tolerance measures the cancellation instead of the discretisation.
"""

import math

import pytest

from nanopnp.core.scaling import Scales
from nanopnp.geometry.analyte import AnalyteInBoxGeometry, SphereBody
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import ModelSolution
from nanopnp.post import qoi
from nanopnp.post.forces import (
    FORCE_ROUTE_TOLERANCE_N,
    AnalyteForces,
    ExtensionError,
    ForceAgreement,
    ForceComponents,
    ForceDisagreementError,
    axial_extension,
    check_extension,
    hydrodynamic_stress,
    maxwell_stress,
    reaction_force,
)

BODY_RADIUS_NM = 1.0
"""The benchmark sphere of ``AnalyteInBoxGeometry``, in nm."""


class TestAxialExtension:
    """``w`` must be exactly ``e_z`` on the body and exactly zero elsewhere.

    "Exactly" is the whole content of NUM-28: the domain form is a surface
    traction rewritten by the divergence theorem, and the rewriting holds only
    for those two boundary values. A band that leaks returns the force on the
    reservoir instead, and reports it with no other symptom.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def mesh(cls) -> object:
        """Return a 1 nm sphere in a 10 nm half-disc, graded on the body."""
        geometry = AnalyteInBoxGeometry(SphereBody(radius_nm=BODY_RADIUS_NM), outer_radius_nm=10.0)
        return geometry.generate(maxh_nm=1.5, wall_h_nm=0.2)

    @pytest.fixture(scope="class")
    @classmethod
    def extension(cls, mesh: object) -> object:
        """``w`` over a shell from 1 nm to 3 nm from the body's surface."""
        return axial_extension(mesh, inner_nm=1.0, outer_nm=3.0)

    def test_num28_extension_is_ez_on_the_body_and_zero_on_the_outer_boundary(
        self, extension: object, mesh: object
    ) -> None:
        """The two boundary values NUM-28's derivation assumes, measured.

        ``axial_extension`` already runs this check; asserting it again here is
        deliberate, because a future change that weakens the built-in check would
        otherwise remove the only place the property is stated.
        """
        check_extension(extension, mesh)

    def test_num28_check_extension_rejects_an_inverted_band(
        self, extension: object, mesh: object
    ) -> None:
        """``e_z`` on the reservoir and zero on the body is the silent failure.

        It integrates, converges and returns a force — of the wrong body. The
        check is what turns it into an error.
        """
        import ngsolve as ngs

        inverted = ngs.GridFunction(extension.space, name="w_inverted")
        inverted.Set(ngs.CF((0.0, 1.0)) - extension)
        with pytest.raises(ExtensionError) as raised:
            check_extension(inverted, mesh)
        assert "inverted" in str(raised.value)

    def test_num28_domain_form_is_invariant_to_the_pressure_datum(
        self, extension: object, mesh: object
    ) -> None:
        """``int_Omega div(w) dV = 0``, so a constant added to ``p`` moves nothing.

        The hydrodynamic stress carries ``-p I``, whose contraction with
        ``grad(w)`` is ``-p div(w)``. VER-19 and VER-21 impose a Dirichlet
        velocity on every boundary, which leaves the pressure determined only up
        to a constant, so the force would be arbitrary unless that integral
        vanished. It does, and exactly: by the divergence theorem it equals
        ``-int_{dB} n_z dS`` over the closed surface of a body of revolution.

        Asserted against the scale of ``grad(w)`` rather than against an absolute
        number, so that the test says "cancels" and not "is small".
        """
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
        """A degenerate shell is refused before a distance field is solved for."""
        with pytest.raises(ExtensionError):
            axial_extension(mesh, inner_nm=inner_nm, outer_nm=outer_nm)


def test_num28_maxwell_stress_check_values() -> None:
    """``eps (E .x. E - 1/2 |E|^2 I)`` on a field a reader can check by eye.

    With ``grad(phi) = (0, 1)`` and ``eps~_r = 2`` the tensor is
    ``2 [[0, 0], [0, 1]] - [[1, 0], [0, 1]] = [[-1, 0], [0, 1]]``: tension along
    the field, pressure across it. A sign error in either term flips one of those
    and the electromagnetic force with it.
    """
    import ngsolve as ngs

    stress = maxwell_stress(ngs.CF((0.0, 1.0)), 2.0)
    mesh = ngs.Mesh(_unit_square())
    values = [float(ngs.Integrate(stress[i, j], mesh)) for i in range(2) for j in range(2)]
    assert values == pytest.approx([-1.0, 0.0, 0.0, 1.0], abs=1e-12)


def test_num28_hydrodynamic_stress_check_values() -> None:
    """``-p I + 2 eta sym grad(u)``, in NUM-28's sign convention.

    Shear ``grad(u) = [[0, 1], [0, 0]]`` at ``eta~ = 3`` gives an off-diagonal
    traction of ``2 * 3 * 1/2 = 3``, and a pressure of 5 subtracts 5 from each
    diagonal. ``.knowledge/05`` section 4 writes the same tensor with the
    opposite overall sign; mixing the two negates the drag, which is why the
    convention is pinned by a number rather than by a comment.
    """
    import ngsolve as ngs

    stress = hydrodynamic_stress(ngs.CF((0.0, 1.0, 0.0, 0.0), dims=(2, 2)), 5.0, 3.0)
    mesh = ngs.Mesh(_unit_square())
    values = [float(ngs.Integrate(stress[i, j], mesh)) for i in range(2) for j in range(2)]
    assert values == pytest.approx([-5.0, 3.0, 3.0, -5.0], abs=1e-12)


def _unit_square() -> object:
    """Return a one-element mesh of the unit square, to evaluate constants on."""
    from netgen.occ import OCCGeometry, Rectangle

    return OCCGeometry(Rectangle(1.0, 1.0).Face(), dim=2).GenerateMesh(maxh=2.0)


def test_num28_force_scale_is_eps_vt_squared_and_carries_no_length() -> None:
    """``force_N = pressure_Pa * length_m^2``, and the reference length cancels.

    The pressure scale is ``eps V_T^2 / a^2`` and a force is a pressure over an
    area, so the force unit is ``eps V_T^2`` whatever ``a`` is. Two scale sets a
    decade apart in reference length must therefore report the same force unit —
    if they do not, the ``2 pi int (...) r dr dz`` of a domain form has picked up
    a stray ``a``.
    """
    small = Scales(length_nm=1.0, concentration_M=0.3)
    large = Scales(length_nm=10.0, concentration_M=0.3)
    assert small.force_N == pytest.approx(small.pressure_Pa * small.length_m**2, rel=1e-12)
    assert large.force_N == pytest.approx(small.force_N, rel=1e-12)
    assert small.force_N == pytest.approx(4.568e-13, rel=1e-3)
    assert small.summary()["force_N"] == small.force_N


def test_num27_the_azimuthal_factor_is_defined_in_one_place() -> None:
    """``post.forces`` restores ``2 pi`` through ``post.qoi``'s own constant.

    NUM-27's NOTE turns on the factor being applied exactly once, at exactly one
    boundary. Two modules each holding their own literal is how it comes to be
    applied twice.
    """
    from nanopnp.post import forces

    assert forces.TWO_PI is qoi.TWO_PI
    assert math.isclose(qoi.TWO_PI, 2.0 * math.pi, rel_tol=1e-15)


def test_num29_the_route_tolerance_is_a_fifth_of_a_force_unit() -> None:
    """0.1 pN is 0.219 in the nondimensional scaling, whatever the pore radius.

    The number the plan sizes the benchmark meshes against. Recomputed here so
    that a change to ``FORCE_ROUTE_TOLERANCE_N`` or to the force scale restates
    it rather than silently moving the bar the discretisation has to clear.
    """
    tolerance_N = FORCE_ROUTE_TOLERANCE_N
    assert tolerance_N == pytest.approx(1e-13)
    scales = Scales(length_nm=2.0, concentration_M=0.3)
    assert tolerance_N / scales.force_N == pytest.approx(0.219, abs=5e-4)


class TestForceAgreement:
    """The route record, and why its tolerance is absolute."""

    def test_num29_agreement_is_absolute_and_not_relative(self) -> None:
        """A near-cancelling total must not be allowed to pass on its smallness.

        Two components of +10 pN and -10.02 pN sum to -0.02 pN. A relative test
        on that sum passes anything within a few per cent of *it* — thousandths
        of a piconewton — or fails everything, depending on which way the
        cancellation fell; either way it measures the cancellation and not the
        discretisation. Here the routes differ by 0.05 pN on components of 10 pN,
        which is 0.5 % relative and half the absolute tolerance, and it passes.
        """
        agreement = ForceAgreement(
            domain=ForceComponents(em_N=10e-12, hd_N=-10.02e-12),
            surface=ForceComponents(em_N=10.05e-12, hd_N=-10.02e-12),
        )
        assert agreement.total_difference_N == pytest.approx(0.05e-12)
        agreement.check()

    def test_num29_a_disagreement_beyond_the_tolerance_raises(self) -> None:
        """0.2 pN apart on the total is a failure however small the total is."""
        agreement = ForceAgreement(
            domain=ForceComponents(em_N=10e-12, hd_N=-10e-12),
            surface=ForceComponents(em_N=10.2e-12, hd_N=-10e-12),
        )
        with pytest.raises(ForceDisagreementError):
            agreement.check()

    def test_num29_the_message_names_all_three_routes(self) -> None:
        """A failure must say which route said what, in piconewtons.

        RSK-04's failure mode is a wrong *split* of a right total, so a message
        reporting only a difference leaves the reader unable to tell which half
        moved.
        """
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
        """A split that is wrong while the total is right must still fail.

        Route A's ``F^em`` and ``F^hd`` here are each 5 pN away from the truth in
        opposite directions, so the total agrees with route B exactly and only
        the reaction force notices. That is the reason route C is in the package.
        """
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
        """No oracle means no hydrodynamic difference, and the message says so."""
        agreement = ForceAgreement(
            domain=ForceComponents(em_N=15e-12, hd_N=-15e-12),
            surface=ForceComponents(em_N=16e-12, hd_N=-15e-12),
        )
        assert agreement.hydrodynamic_difference_N == 0.0
        with pytest.raises(ForceDisagreementError) as raised:
            agreement.check()
        assert "not taken" in str(raised.value)


def test_fr25_the_summary_records_the_convention_and_the_routes() -> None:
    """The manifest must say that ``2 pi`` is in and whether the routes were checked.

    A force reported without either is not reproducible: the reader cannot tell
    an unchecked split from a checked one, nor a per-radian force from a whole
    one (FR-25, NUM-27).
    """
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
    """``pnp`` reports no force rather than reporting the hydrodynamic half as zero.

    Zero is a *result*; it would claim the flow was computed and found to vanish.
    """
    solution = ModelSolution(model=models.create("pnp"), space=None, state=None)
    with pytest.raises(TypeError) as raised:
        reaction_force(solution)
    assert "no flow block" in str(raised.value)


def test_num28_the_reaction_route_needs_the_residual_the_solve_assembled() -> None:
    """Route C without a residual form fails loudly rather than rebuilding one.

    A coupled residual reassembled without the same ``wall_distance_nm`` is a
    different operator, and the reaction taken against it is wrong with no
    diagnostic at all (NUM-25).
    """
    solution = ModelSolution(model=models.create("pnp-ns"), space=None, state=None)
    with pytest.raises(ValueError, match="no residual form"):
        reaction_force(solution)

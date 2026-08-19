"""The electrolyte layer: the correction driver, ablation switches, and both math paths."""

import numpy as np
import pytest

from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.materials.forms import NGSolveOps, NumpyOps


@pytest.fixture(scope="module")
def epnpns() -> Electrolyte:
    return Electrolyte.from_parameter_file("willems2020_nacl")


def test_phy01_driver_is_the_arithmetic_mean_in_molar_units(epnpns: Electrolyte) -> None:
    """<c> is the mean of the ion concentrations, converted mol/m^3 -> mol/L."""
    assert epnpns.average_concentration([1000.0, 1000.0]) == pytest.approx(1.0)
    assert epnpns.average_concentration([2000.0, 1000.0]) == pytest.approx(1.5)


def test_phy01_driver_clamps_each_species_before_averaging(epnpns: Electrolyte) -> None:
    """Clamping is per species and to [1e-6 M, 5.3 M], not applied to the average."""
    # 10 M and 0 M average to 5 M unclamped; clamped they average to 2.65 M.
    assert epnpns.average_concentration([10_000.0, 0.0]) == pytest.approx(2.65, abs=1e-6)
    assert epnpns.average_concentration([0.0, 0.0]) == pytest.approx(1e-6)


def test_ionic_strength_is_available_as_a_named_option(epnpns: Electrolyte) -> None:
    """The two drivers coincide for a symmetric 1:1 salt, which is why the source is ambiguous."""
    ionic = Electrolyte.from_parameter_file("willems2020_nacl", driver="ionic_strength")
    assert ionic.average_concentration([1000.0, 1000.0]) == pytest.approx(
        epnpns.average_concentration([1000.0, 1000.0])
    )
    # They diverge as soon as the electrolyte is not symmetric.
    assert ionic.average_concentration([2000.0, 1000.0]) == pytest.approx(1.5)
    with pytest.raises(ValueError, match="unknown correction driver"):
        Electrolyte.from_parameter_file("willems2020_nacl", driver="ionic-strength")


def test_driver_accepts_arrays(epnpns: Electrolyte) -> None:
    """The same call serves a sampled field, for diagnostics and clamp reporting."""
    driver = epnpns.average_concentration([np.array([1000.0, 3000.0]), np.array([1000.0, 3000.0])])
    assert np.allclose(driver, [1.0, 3.0])


def test_wrong_species_count_is_rejected(epnpns: Electrolyte) -> None:
    with pytest.raises(ValueError, match="expected 2 concentrations"):
        epnpns.average_concentration([1000.0])


def test_single_correction_can_be_ablated(epnpns: Electrolyte) -> None:
    """An ablation study is a configuration, not a rebuild (section 7.4)."""
    switches = CorrectionSwitches.for_model("willems2020_nacl").without("viscosity")
    ablated = Electrolyte.from_parameter_file("willems2020_nacl", switches=switches)
    assert ablated.viscosity(3.0, 0.1) == ablated.viscosity_0
    assert ablated.diffusivity("Na+", 3.0, 0.1) == pytest.approx(
        epnpns.diffusivity("Na+", 3.0, 0.1)
    )
    assert ablated.provenance["corrections"]["viscosity"]["model"] == "none"


def test_symbolic_and_numeric_paths_agree(epnpns: Electrolyte) -> None:
    """The NGSolve path must evaluate the same expression as the NumPy one.

    The forms are written once and dispatched over an operation namespace
    precisely so that assembly and verification cannot drift apart; this is the
    test that holds them together.
    """
    import ngsolve as ngs
    from netgen.occ import OCCGeometry, Rectangle

    geometry = OCCGeometry(Rectangle(1, 1).Face(), dim=2)
    mesh = ngs.Mesh(geometry.GenerateMesh(maxh=0.5))
    point = mesh(0.5, 0.5)

    for c, d in ((0.1, 0.05), (1.0, 0.3), (3.0, 2.0), (7.0, 0.0)):
        # x and y stand in for the driver and the wall distance, so the symbolic
        # path builds the full CoefficientFunction tree rather than folding
        # constants.
        c_cf = ngs.CF(c) * ngs.x / ngs.x
        d_cf = ngs.CF(d) * ngs.y / ngs.y
        for prop, numeric, symbolic in (
            (
                "D_Na",
                epnpns.diffusivity("Na+", c, d, NumpyOps()),
                epnpns.diffusivity("Na+", c_cf, d_cf, NGSolveOps()),
            ),
            (
                "mu_Cl",
                epnpns.mobility("Cl-", c, d, NumpyOps()),
                epnpns.mobility("Cl-", c_cf, d_cf, NGSolveOps()),
            ),
            (
                "eta",
                epnpns.viscosity(c, d, NumpyOps()),
                epnpns.viscosity(c_cf, d_cf, NGSolveOps()),
            ),
            (
                "rho",
                epnpns.mass_density(c, d, NumpyOps()),
                epnpns.mass_density(c_cf, d_cf, NGSolveOps()),
            ),
            (
                "eps_r",
                epnpns.relative_permittivity(c, d, NumpyOps()),
                epnpns.relative_permittivity(c_cf, d_cf, NGSolveOps()),
            ),
        ):
            assert symbolic(point) == pytest.approx(float(numeric), rel=1e-12), (
                f"{prop} disagrees between the numeric and symbolic paths at c={c}, d={d}"
            )


def test_langevin_limit_is_finite_at_zero_concentration(epnpns: Electrolyte) -> None:
    """The permittivity form has a removable singularity at c = 0; it must not divide by zero."""
    assert epnpns.relative_permittivity(0.0) == pytest.approx(78.15)
    assert np.isfinite(epnpns.relative_permittivity(np.array([0.0, 1e-12, 1.0]))).all()

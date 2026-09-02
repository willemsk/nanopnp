"""The electrolyte layer: the correction driver, ablation switches, and both math paths."""

from dataclasses import replace

import numpy as np
import pytest

from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte, IonSpecies
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
    # For a 1:1 salt they agree at *any* concentrations, symmetric or not ...
    assert ionic.average_concentration([2000.0, 1000.0]) == pytest.approx(1.5)
    assert epnpns.average_concentration([2000.0, 1000.0]) == pytest.approx(1.5)
    # ... so only a multivalent species separates them: I = 0.5 * (4*2 + 1*1) M.
    divalent = replace(ionic, species=(replace(ionic.species[0], valence=2), ionic.species[1]))
    assert divalent.average_concentration([2000.0, 1000.0]) == pytest.approx(4.5)
    assert replace(divalent, driver="average").average_concentration(
        [2000.0, 1000.0]
    ) == pytest.approx(1.5)
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


def test_langevin_is_accurate_across_the_series_cutoff() -> None:
    """Neither branch may fall into the cancellation of `coth(x) - 1/x`.

    The difference is of size `x/3` between two terms of size `1/x`, so a cutoff
    chosen too small hands the coth branch an argument at which it has no
    significant digits left: at 1e-8 the function returned exactly zero.
    """
    from nanopnp.materials.forms import langevin

    x = np.geomspace(1e-9, 1e-1, 400)
    series = x / 3.0 - x**3 / 45.0 + 2.0 * x**5 / 945.0
    assert np.allclose(langevin(x), series, rtol=1e-7)


def test_species_temperature_must_match_the_electrolyte(epnpns: Electrolyte) -> None:
    """A species at a different temperature would silently mis-derive mu_i^0."""
    warm = IonSpecies(name="Na+", valence=1, diffusivity_0=1.334e-9, steric_diameter=0.5e-9)
    with pytest.raises(ValueError, match="different from the electrolyte"):
        replace(epnpns, temperature_K=310.0, species=(warm, epnpns.species[1]))


def test_a_parameter_file_becomes_selectable_without_a_code_change() -> None:
    """FR-16: the selectable models are whatever is installed under data/corrections."""
    from nanopnp.core.paths import available_corrections
    from nanopnp.materials import models

    assert "willems2020_nacl" in available_corrections()
    for name in available_corrections():
        assert name in models.registered_models()


def test_phy21_switches_and_corrections_cannot_disagree() -> None:
    """``replace(..., switches=...)`` is refused; ``with_switches`` is the way.

    The corrections are resolved once, at construction, and every property
    accessor reads the resolved model; ``switches`` is never consulted again. So
    swapping the switches alone produces an electrolyte that *reports* one
    configuration in its FR-25 provenance and *evaluates* another — and a run
    that calls itself PNP-NS, converges, and is ePNP-NS makes the PHY-21
    ablation compare a configuration against itself.
    """
    full = Electrolyte.from_parameter_file()
    with pytest.raises(ValueError, match="switches and its resolved corrections disagree"):
        replace(full, switches=CorrectionSwitches.classical())


def test_phy21_with_switches_changes_the_behaviour_not_only_the_record() -> None:
    """The classical reduction is a real reduction: every factor becomes 1.

    At 3 M the reference mobility correction is a factor of about 0.5, so a
    classical electrolyte that still evaluated the fitted model would be caught
    here by a wide margin — which is exactly what a switches-only swap did.
    """
    full = Electrolyte.from_parameter_file()
    classical = full.with_switches(CorrectionSwitches.classical())

    assert classical.switches == CorrectionSwitches.classical()
    for ion in classical.species:
        assert classical.correction("mobility", ion.name).name == "none"
        assert classical.mobility(ion.name, 3.0, 3.0) == pytest.approx(ion.mobility_0)
        assert classical.diffusivity(ion.name, 3.0, 3.0) == pytest.approx(ion.diffusivity_0)
        # ... and the full configuration really does correct it, so the test
        # above is not passing because both are 1.
        assert full.mobility(ion.name, 3.0, 3.0) < 0.6 * ion.mobility_0
    assert classical.viscosity(3.0, 3.0) == pytest.approx(classical.viscosity_0)
    assert full.viscosity(3.0, 3.0) > 1.1 * full.viscosity_0


def test_phy21_with_switches_round_trips_back_to_the_full_configuration() -> None:
    """Turning the corrections off and on again restores the validated model."""
    full = Electrolyte.from_parameter_file()
    there_and_back = full.with_switches(CorrectionSwitches.classical()).with_switches(full.switches)
    for ion in full.species:
        assert there_and_back.mobility(ion.name, 3.0, 3.0) == pytest.approx(
            full.mobility(ion.name, 3.0, 3.0)
        )


def test_phy21_an_ablated_sub_switch_is_caught_too() -> None:
    """Turning off only the wall part is as silent as turning off the model."""
    full = Electrolyte.from_parameter_file()
    ablated = replace(full.switches, mobility=replace(full.switches.mobility, wall=False))
    with pytest.raises(ValueError, match="wall="):
        replace(full, switches=ablated)

    honest = full.with_switches(ablated)
    for ion in honest.species:
        assert honest.correction("mobility", ion.name).use_wall is False
        assert honest.correction("diffusivity", ion.name).use_wall is True

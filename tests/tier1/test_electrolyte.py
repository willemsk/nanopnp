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
    assert epnpns.average_concentration([1000.0, 1000.0]) == pytest.approx(1.0)
    assert epnpns.average_concentration([2000.0, 1000.0]) == pytest.approx(1.5)


def test_phy01_driver_clamps_each_species_before_averaging(epnpns: Electrolyte) -> None:
    assert epnpns.average_concentration([10_000.0, 0.0]) == pytest.approx(2.65, abs=1e-6)
    assert epnpns.average_concentration([0.0, 0.0]) == pytest.approx(1e-6)


def test_ionic_strength_is_available_as_a_named_option(epnpns: Electrolyte) -> None:
    ionic = Electrolyte.from_parameter_file("willems2020_nacl", driver="ionic_strength")
    assert ionic.average_concentration([1000.0, 1000.0]) == pytest.approx(
        epnpns.average_concentration([1000.0, 1000.0])
    )
    assert ionic.average_concentration([2000.0, 1000.0]) == pytest.approx(1.5)
    assert epnpns.average_concentration([2000.0, 1000.0]) == pytest.approx(1.5)
    divalent = replace(ionic, species=(replace(ionic.species[0], valence=2), ionic.species[1]))
    assert divalent.average_concentration([2000.0, 1000.0]) == pytest.approx(4.5)
    assert replace(divalent, driver="average").average_concentration(
        [2000.0, 1000.0]
    ) == pytest.approx(1.5)
    with pytest.raises(ValueError, match="unknown correction driver"):
        Electrolyte.from_parameter_file("willems2020_nacl", driver="ionic-strength")


def test_driver_accepts_arrays(epnpns: Electrolyte) -> None:
    driver = epnpns.average_concentration([np.array([1000.0, 3000.0]), np.array([1000.0, 3000.0])])
    assert np.allclose(driver, [1.0, 3.0])


def test_wrong_species_count_is_rejected(epnpns: Electrolyte) -> None:
    with pytest.raises(ValueError, match="expected 2 concentrations"):
        epnpns.average_concentration([1000.0])


def test_single_correction_can_be_ablated(epnpns: Electrolyte) -> None:
    switches = CorrectionSwitches.for_model("willems2020_nacl").without("viscosity")
    ablated = Electrolyte.from_parameter_file("willems2020_nacl", switches=switches)
    assert ablated.viscosity(3.0, 0.1) == ablated.viscosity_0
    assert ablated.diffusivity("Na+", 3.0, 0.1) == pytest.approx(
        epnpns.diffusivity("Na+", 3.0, 0.1)
    )
    assert ablated.provenance["corrections"]["viscosity"]["model"] == "none"


def test_symbolic_and_numeric_paths_agree(epnpns: Electrolyte) -> None:
    import ngsolve as ngs
    from netgen.occ import OCCGeometry, Rectangle

    geometry = OCCGeometry(Rectangle(1, 1).Face(), dim=2)
    mesh = ngs.Mesh(geometry.GenerateMesh(maxh=0.5))
    point = mesh(0.5, 0.5)

    for c, d in ((0.1, 0.05), (1.0, 0.3), (3.0, 2.0), (7.0, 0.0)):
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
    assert epnpns.relative_permittivity(0.0) == pytest.approx(78.15)
    assert np.isfinite(epnpns.relative_permittivity(np.array([0.0, 1e-12, 1.0]))).all()


def test_langevin_is_accurate_across_the_series_cutoff() -> None:
    from nanopnp.materials.forms import _LANGEVIN_SERIES_CUTOFF, langevin

    assert _LANGEVIN_SERIES_CUTOFF == 3e-4
    assert langevin(1.1e-8) == pytest.approx(1.1e-8 / 3.0, rel=1e-12)
    assert 1.0 / np.tanh(1.1e-8) - 1.0 / 1.1e-8 == 0.0

    x = np.geomspace(1e-9, 1e-1, 400)
    series = x / 3.0 - x**3 / 45.0 + 2.0 * x**5 / 945.0
    assert np.allclose(langevin(x), series, rtol=1e-7)


def test_species_temperature_must_match_the_electrolyte(epnpns: Electrolyte) -> None:
    warm = IonSpecies(name="Na+", valence=1, diffusivity_0=1.334e-9, steric_diameter=0.5e-9)
    with pytest.raises(ValueError, match="different from the electrolyte"):
        replace(epnpns, temperature_K=310.0, species=(warm, epnpns.species[1]))


# FR-16
def test_a_parameter_file_becomes_selectable_without_a_code_change() -> None:
    from nanopnp.core.paths import available_corrections
    from nanopnp.materials import models

    assert "willems2020_nacl" in available_corrections()
    for name in available_corrections():
        assert name in models.registered_models()


# FR-25
def test_phy21_switches_and_corrections_cannot_disagree() -> None:
    full = Electrolyte.from_parameter_file()
    with pytest.raises(ValueError, match="switches and its resolved corrections disagree"):
        replace(full, switches=CorrectionSwitches.classical())


def test_phy21_with_switches_changes_the_behaviour_not_only_the_record() -> None:
    full = Electrolyte.from_parameter_file()
    classical = full.with_switches(CorrectionSwitches.classical())

    assert classical.switches == CorrectionSwitches.classical()
    for ion in classical.species:
        assert classical.correction("mobility", ion.name).name == "none"
        assert classical.mobility(ion.name, 3.0, 3.0) == pytest.approx(ion.mobility_0)
        assert classical.diffusivity(ion.name, 3.0, 3.0) == pytest.approx(ion.diffusivity_0)
        assert full.mobility(ion.name, 3.0, 3.0) < 0.6 * ion.mobility_0
    assert classical.viscosity(3.0, 3.0) == pytest.approx(classical.viscosity_0)
    assert full.viscosity(3.0, 3.0) > 1.1 * full.viscosity_0


def test_phy21_with_switches_round_trips_back_to_the_full_configuration() -> None:
    full = Electrolyte.from_parameter_file()
    there_and_back = full.with_switches(CorrectionSwitches.classical()).with_switches(full.switches)
    for ion in full.species:
        assert there_and_back.mobility(ion.name, 3.0, 3.0) == pytest.approx(
            full.mobility(ion.name, 3.0, 3.0)
        )


def test_phy21_an_ablated_sub_switch_is_caught_too() -> None:
    full = Electrolyte.from_parameter_file()
    ablated = replace(full.switches, mobility=replace(full.switches.mobility, wall=False))
    with pytest.raises(ValueError, match="wall="):
        replace(full, switches=ablated)

    honest = full.with_switches(ablated)
    for ion in honest.species:
        assert honest.correction("mobility", ion.name).use_wall is False
        assert honest.correction("diffusivity", ion.name).use_wall is True


def test_phy13_a_clamp_of_the_ionic_strength_driver_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ionic = Electrolyte.from_parameter_file("willems2020_nacl", driver="ionic_strength")
    divalent = replace(ionic, species=(replace(ionic.ion("Na+"), valence=2), ionic.ion("Cl-")))
    samples = [np.array([2000.0]), np.array([4000.0])]

    with caplog.at_level("WARNING", logger="nanopnp.materials.electrolyte"):
        count = divalent.report_clamp_activations(samples, coordinates=[(1.0, 2.0)])
    assert count == 1
    (record,) = caplog.records
    assert record.getMessage() == (
        "correction driver (ionic strength): concentration correction clamped at 5.3 M for "
        "1 sample(s); peak concentration 6 M is outside the fit range. worst at (1.0, 2.0)"
    )

    caplog.clear()
    averaged = replace(divalent, driver="average")
    with caplog.at_level("WARNING", logger="nanopnp.materials.electrolyte"):
        assert averaged.report_clamp_activations(samples, coordinates=[(1.0, 2.0)]) == 0
    assert not caplog.records

    caplog.clear()
    # The fits see the mean of the clipped concentrations, 4.65 M here, so the unclipped mean of
    # 5.5 M must not be counted as a driver clamp.
    beyond = [np.array([7000.0]), np.array([4000.0])]
    with caplog.at_level("WARNING", logger="nanopnp.materials.electrolyte"):
        assert averaged.report_clamp_activations(beyond, coordinates=[(1.0, 2.0)]) == 1
    assert "correction driver" not in caplog.text

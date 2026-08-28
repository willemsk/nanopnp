"""VER-03, VER-04, VER-05: the correction models reproduce their published values.

The check values come from SPECIFICATION.md section 7.2 and PHY-12, and are
cross-checked in .knowledge/01-physics-epnpns.md section 8. They are asserted
through the registry rather than against a formula re-implemented here: a test
that re-derives the form would pass while the solver used a different one, which
is the whole failure mode the shared `materials.forms` module exists to prevent.
"""

import logging

import numpy as np
import pytest

from nanopnp.core.constants import thermal_voltage
from nanopnp.materials import models
from nanopnp.materials.corrections import load_corrections
from nanopnp.materials.electrolyte import (
    CorrectionSwitches,
    Electrolyte,
    log_clamp_activations,
)

REL_TOL = 5e-4  # the published check values are quoted to four significant figures
FAR_FROM_WALL_NM = 50.0  # f^w is 1 to machine precision well away from the wall


@pytest.fixture(scope="module")
def epnpns() -> Electrolyte:
    """Return the validated ePNP-NS configuration: every correction on."""
    return Electrolyte.from_parameter_file("willems2020_nacl")


@pytest.fixture(scope="module")
def classical() -> Electrolyte:
    """Return classical PNP-NS: every correction resolved to the `none` model."""
    return Electrolyte.from_parameter_file(
        "willems2020_nacl", switches=CorrectionSwitches.classical()
    )


def test_ver03_ion_wall_function_check_values() -> None:
    """f^w_D(0) = 0.0601 and f^w_D(0.75 nm) = 0.9910, shared by D and mu."""
    wall = models.create("willems2020_nacl", "diffusivity", "Na+", concentration=False)
    assert wall.parameters["fw.P1"] == pytest.approx(6.2)  # 1/nm; not 62, not 0.62
    assert wall.parameters["fw.P2"] == pytest.approx(0.01)  # nm, and the offset is PLUS
    assert wall.evaluate(0.0, 0.0) == pytest.approx(0.0601, rel=REL_TOL)
    assert wall.evaluate(0.0, 0.75) == pytest.approx(0.9910, rel=REL_TOL)


def test_ver03_viscosity_wall_function_check_values(epnpns: Electrolyte) -> None:
    """eta0/eta^w(0) = 0.3790 and eta0/eta^w(1.45 nm) = 0.9876.

    The viscosity wall function takes the opposite offset sign to the ion one
    and exceeds 1: the solvent is more viscous at the wall, not less.
    """
    eta_wall = models.create("willems2020_nacl", "viscosity", concentration=False)
    assert 1.0 / eta_wall.evaluate(0.0, 0.0) == pytest.approx(0.3790, rel=REL_TOL)
    assert 1.0 / eta_wall.evaluate(0.0, 1.45) == pytest.approx(0.9876, rel=REL_TOL)
    assert eta_wall.evaluate(0.0, 0.0) > 1.0


def test_ver03_bulk_properties_at_the_validity_limit(epnpns: Electrolyte) -> None:
    """Every property matches its tabulated 5.3 M cap (PHY-12, PHY-13)."""
    c, d = 5.3, FAR_FROM_WALL_NM
    assert epnpns.viscosity(c, d) == pytest.approx(1.752e-3, rel=1e-3)
    assert epnpns.mass_density(c) == pytest.approx(1194.0, rel=1e-3)
    assert epnpns.relative_permittivity(c) == pytest.approx(42.67, rel=1e-3)
    assert epnpns.diffusivity("Na+", c, d) == pytest.approx(8.13e-10, rel=3e-3)
    assert epnpns.diffusivity("Cl-", c, d) == pytest.approx(1.071e-9, rel=1e-3)


def test_ver03_properties_are_capped_above_the_validity_range(epnpns: Electrolyte) -> None:
    """Above 5.3 M every property holds its cap value rather than extrapolating."""
    at_limit = epnpns.viscosity(5.3, FAR_FROM_WALL_NM)
    for beyond in (5.4, 8.0, 20.0):
        assert epnpns.viscosity(beyond, FAR_FROM_WALL_NM) == pytest.approx(at_limit)
        assert epnpns.diffusivity("Na+", beyond, FAR_FROM_WALL_NM) == pytest.approx(
            epnpns.diffusivity("Na+", 5.3, FAR_FROM_WALL_NM)
        )


def test_ver04_nernst_einstein_holds_at_infinite_dilution(epnpns: Electrolyte) -> None:
    """mu_i^0 = D_i^0 / V_T to four figures, and mu is derived rather than fitted."""
    assert thermal_voltage() == pytest.approx(25.693e-3, rel=1e-4)
    for name, expected in (("Na+", 5.1922e-8), ("Cl-", 7.9089e-8)):
        ion = epnpns.ion(name)
        assert ion.mobility_0 == pytest.approx(expected, rel=REL_TOL)
        # The published table value, which PHY-14 says must not be fitted
        # independently, agrees with the derived one.
        assert epnpns.mobility(name, 0.0, FAR_FROM_WALL_NM) == pytest.approx(expected, rel=REL_TOL)


def test_ver05_einstein_ratio_drifts_with_concentration(epnpns: Electrolyte) -> None:
    """D_i/mu_i rises to 1.2-1.7 x kT/e between 0.15 M and 3 M.

    D and mu are fitted to different data - self-diffusion and conductivity - so
    the Einstein relation is a property of the infinite-dilution limit only. A
    test asserting D_i/mu_i = kT/e at finite concentration SHALL NOT be written
    (PHY-14); this is that assertion's replacement.
    """
    v_t = thermal_voltage()
    for name in ("Na+", "Cl-"):
        ratios = [
            epnpns.diffusivity(name, c, FAR_FROM_WALL_NM)
            / epnpns.mobility(name, c, FAR_FROM_WALL_NM)
            / v_t
            for c in (0.15, 1.0, 3.0)
        ]
        assert ratios == sorted(ratios), f"{name}: D/mu should rise with concentration"
        assert 1.0 < ratios[0] < 1.3
        assert 1.2 < ratios[-1] < 1.7


def test_classical_pnp_ns_recovers_the_reference_values_exactly(
    classical: Electrolyte, epnpns: Electrolyte
) -> None:
    """With every correction `none`, X = X0 exactly - no separate code path (PHY-21)."""
    for c in (0.0, 1.0, 3.0, 9.9):
        for d in (0.0, 0.5, FAR_FROM_WALL_NM):
            assert classical.diffusivity("Na+", c, d) == classical.ion("Na+").diffusivity_0
            assert classical.mobility("Cl-", c, d) == classical.ion("Cl-").mobility_0
            assert classical.viscosity(c, d) == classical.viscosity_0
            assert classical.mass_density(c) == classical.mass_density_0
            assert classical.relative_permittivity(c) == 78.15
    # ... and the corrected model does not agree with it, or nothing is switched on.
    assert epnpns.viscosity(3.0, 0.0) != pytest.approx(epnpns.viscosity_0)


def test_correction_parts_switch_independently() -> None:
    """The concentration and wall parts of one correction are separable (PHY-22)."""
    both = models.create("willems2020_nacl", "diffusivity", "Na+")
    wall_only = models.create("willems2020_nacl", "diffusivity", "Na+", concentration=False)
    conc_only = models.create("willems2020_nacl", "diffusivity", "Na+", wall=False)
    c, d = 1.0, 0.2
    assert both.evaluate(c, d) == pytest.approx(wall_only.evaluate(c, d) * conc_only.evaluate(c, d))
    assert conc_only.evaluate(c, d) == pytest.approx(conc_only.evaluate(c, 0.0))


def test_none_is_a_registered_model_not_a_code_branch() -> None:
    """PHY-22: switching a correction off selects a model."""
    assert "none" in models.registered_models()
    off = models.create("none", "viscosity")
    assert off.name == "none"
    assert off.evaluate(3.0, 0.1) == 1.0
    assert off.parameters == {}


def test_unknown_model_and_species_fail_with_a_useful_message() -> None:
    with pytest.raises(KeyError, match="registered models are"):
        models.create("willems2020_kcl", "viscosity")
    with pytest.raises(KeyError, match="no species 'K\\+'"):
        models.create("willems2020_nacl", "diffusivity", "K+")
    with pytest.raises(ValueError, match="takes an ion name"):
        models.create("willems2020_nacl", "diffusivity")
    with pytest.raises(ValueError, match="takes no species"):
        models.create("willems2020_nacl", "viscosity", "Na+")


def test_phy13_clamp_activation_is_logged_with_its_location(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Extrapolation past the fit range is reported, not silent."""
    with caplog.at_level(logging.WARNING):
        count = log_clamp_activations(
            [1.0, 5.9, 6.4],
            label="diffusivity driver",
            limit=5.3,
            coordinates=[(0.0, 0.0), (1.0, 2.0), (0.5, 3.0)],
        )
    assert count == 2
    assert "diffusivity driver" in caplog.text
    assert "(0.5, 3.0)" in caplog.text
    assert log_clamp_activations([1.0, 5.29], label="quiet", limit=5.3) == 0


def test_phy13_per_species_clamp_is_what_actually_activates(
    epnpns: Electrolyte, caplog: pytest.LogCaptureFixture
) -> None:
    """The driver is clamped per species, so the driver itself never exceeds the limit.

    A diagnostic run over driver samples alone would therefore report nothing
    even when the fits were extrapolated; PHY-13 is only discharged by checking
    the species concentrations that went into the average.
    """
    c_na = [1000.0, 8000.0]  # mol/m^3: the second sample is 8 M, well past 5.3 M
    c_cl = [1000.0, 100.0]
    driver = epnpns.average_concentration([np.asarray(c_na), np.asarray(c_cl)])
    assert (np.asarray(driver) <= 5.3).all(), "the driver can never report the clamp itself"
    assert log_clamp_activations(driver, label="driver", limit=5.3) == 0

    with caplog.at_level(logging.WARNING):
        count = epnpns.report_clamp_activations([c_na, c_cl], coordinates=[(0.0, 0.0), (0.0, 1.5)])
    assert count == 1
    assert "Na+ concentration" in caplog.text
    assert "(0.0, 1.5)" in caplog.text


def test_parameter_file_mobilities_and_caps_agree_with_the_evaluated_model() -> None:
    """The tabulated `mu0` and `cap_above_validity` entries are data the tests must gate.

    Neither is read by the solver -- `mu0` is derived from `D0` per PHY-14 and
    the caps are applied by clamping the driver -- so without this test a
    mistranscribed exponent (erratum 2) or a stale cap would go unnoticed.
    """
    document = load_corrections("willems2020_nacl")
    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl")
    for ion in electrolyte.species:
        tabulated = float(document["species"][ion.name]["mobility"]["mu0"])
        assert ion.mobility_0 == pytest.approx(tabulated, rel=REL_TOL)

    solvent, species = document["solvent"], document["species"]
    at_cap = {
        "viscosity": (
            electrolyte.viscosity(5.3, FAR_FROM_WALL_NM),
            solvent["viscosity"]["cap_above_validity"],
        ),
        "density": (electrolyte.mass_density(5.3), solvent["density"]["cap_above_validity"]),
        "permittivity": (
            electrolyte.relative_permittivity(5.3),
            solvent["permittivity"]["cap_above_validity"],
        ),
    }
    for ion in electrolyte.species:
        at_cap[f"D_{ion.name}"] = (
            electrolyte.diffusivity(ion.name, 5.3, FAR_FROM_WALL_NM),
            species[ion.name]["diffusivity"]["cap_above_validity"],
        )
    # The tabulated caps are the published, rounded values -- the density one is
    # quoted to three figures (1.19e3 against the fit's 1193.6) -- so the
    # tolerance is set by their precision, not by the fit's. It is still tight
    # enough to catch a wrong exponent or a mistranscribed coefficient.
    for name, (evaluated, tabulated) in at_cap.items():
        assert evaluated == pytest.approx(float(tabulated), rel=5e-3), (
            f"{name}: the fit at 5.3 M disagrees with the tabulated cap"
        )


def test_provenance_records_what_produced_each_property(epnpns: Electrolyte) -> None:
    """FR-25: a result must be able to record which correction version made it."""
    record = epnpns.provenance
    assert record["parameter_file"] == "willems2020_nacl"
    assert record["driver"] == "average"
    assert record["corrections"]["viscosity"]["model"] == "willems2020_nacl"
    assert record["corrections"]["diffusivity:Na+"]["species"] == "Na+"


def test_provenance_distinguishes_an_ablated_run_from_the_full_one() -> None:
    """FR-25: every switch set away from the validated default must be recorded."""
    full = dict(models.create("willems2020_nacl", "viscosity").provenance)
    ablated = dict(models.create("willems2020_nacl", "viscosity", concentration=False).provenance)
    assert full != ablated
    assert full["concentration_form"] == "poly_jones_dole"
    assert ablated["concentration_form"] == "off"
    assert ablated["concentration_enabled"] == "false"
    assert ablated["wall_enabled"] == "true"


def test_fit_metadata_is_not_reported_as_a_coefficient() -> None:
    """`r_squared` is a goodness-of-fit metric, not a coefficient any form reads."""
    parameters = models.create("willems2020_nacl", "viscosity").parameters
    assert "fc.r_squared" not in parameters
    assert "fw.r_squared" not in parameters
    assert parameters["fc.P1"] == pytest.approx(0.007558)

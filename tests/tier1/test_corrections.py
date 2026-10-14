"""VER-03, VER-04, VER-05: the correction models reproduce their published values."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from nanopnp.core.constants import thermal_voltage
from nanopnp.core.paths import correction_file
from nanopnp.materials import models
from nanopnp.materials.corrections import (
    CorrectionDocument,
    DielectricsBlock,
    FitBlock,
    load_corrections,
)
from nanopnp.materials.electrolyte import (
    CorrectionSwitches,
    Electrolyte,
    log_clamp_activations,
)
from nanopnp.materials.forms import FORM_PARAMETERS, FORMS
from nanopnp.pipeline.case import resolve

REL_TOL = 5e-4  # the published check values are quoted to four significant figures
FAR_FROM_WALL_NM = 50.0  # f^w is 1 to machine precision well away from the wall


@pytest.fixture(scope="module")
def epnpns() -> Electrolyte:
    return Electrolyte.from_parameter_file("willems2020_nacl")


@pytest.fixture(scope="module")
def classical() -> Electrolyte:
    return Electrolyte.from_parameter_file(
        "willems2020_nacl", switches=CorrectionSwitches.classical()
    )


def test_ver03_ion_wall_function_check_values() -> None:
    wall = models.create("willems2020_nacl", "diffusivity", "Na+", concentration=False)
    assert wall.parameters["fw.P1"] == pytest.approx(6.2)  # 1/nm; not 62, not 0.62
    assert wall.parameters["fw.P2"] == pytest.approx(0.01)  # nm, and the offset is PLUS
    assert wall.evaluate(0.0, 0.0) == pytest.approx(0.0601, rel=REL_TOL)
    assert wall.evaluate(0.0, 0.75) == pytest.approx(0.9910, rel=REL_TOL)


def test_ver03_viscosity_wall_function_check_values(epnpns: Electrolyte) -> None:
    eta_wall = models.create("willems2020_nacl", "viscosity", concentration=False)
    assert 1.0 / eta_wall.evaluate(0.0, 0.0) == pytest.approx(0.3790, rel=REL_TOL)
    assert 1.0 / eta_wall.evaluate(0.0, 1.45) == pytest.approx(0.9876, rel=REL_TOL)
    assert eta_wall.evaluate(0.0, 0.0) > 1.0


# PHY-12, PHY-13
def test_ver03_bulk_properties_at_the_validity_limit(epnpns: Electrolyte) -> None:
    c, d = 5.3, FAR_FROM_WALL_NM
    assert epnpns.viscosity(c, d) == pytest.approx(1.752e-3, rel=1e-3)
    assert epnpns.mass_density(c) == pytest.approx(1194.0, rel=1e-3)
    assert epnpns.relative_permittivity(c) == pytest.approx(42.67, rel=1e-3)
    assert epnpns.diffusivity("Na+", c, d) == pytest.approx(8.13e-10, rel=3e-3)
    assert epnpns.diffusivity("Cl-", c, d) == pytest.approx(1.071e-9, rel=1e-3)


def test_ver03_properties_are_capped_above_the_validity_range(epnpns: Electrolyte) -> None:
    at_limit = epnpns.viscosity(5.3, FAR_FROM_WALL_NM)
    for beyond in (5.4, 8.0, 20.0):
        assert epnpns.viscosity(beyond, FAR_FROM_WALL_NM) == pytest.approx(at_limit)
        assert epnpns.diffusivity("Na+", beyond, FAR_FROM_WALL_NM) == pytest.approx(
            epnpns.diffusivity("Na+", 5.3, FAR_FROM_WALL_NM)
        )


def test_ver04_nernst_einstein_holds_at_infinite_dilution(epnpns: Electrolyte) -> None:
    assert thermal_voltage() == pytest.approx(25.693e-3, rel=1e-4)
    for name, expected in (("Na+", 5.1922e-8), ("Cl-", 7.9089e-8)):
        ion = epnpns.ion(name)
        assert ion.mobility_0 == pytest.approx(expected, rel=REL_TOL)
        assert epnpns.mobility(name, 0.0, FAR_FROM_WALL_NM) == pytest.approx(expected, rel=REL_TOL)


# PHY-14
def test_ver05_einstein_ratio_drifts_with_concentration(epnpns: Electrolyte) -> None:
    v_t = thermal_voltage()
    tables = {
        "Na+": (1.208, 1.468, 1.665),
        "Cl-": (1.132, 1.221, 1.279),
    }
    for name, expected in tables.items():
        ratios = [
            epnpns.diffusivity(name, c, FAR_FROM_WALL_NM)
            / epnpns.mobility(name, c, FAR_FROM_WALL_NM)
            / v_t
            for c in (0.15, 1.0, 3.0)
        ]
        assert ratios == sorted(ratios), (
            f"{name}: D/mu should rise monotonically with concentration"
        )
        for ratio, table_val in zip(ratios, expected, strict=True):
            assert abs(ratio - table_val) <= 1e-3, f"{name}: {ratio} != {table_val}"


# PHY-21
def test_classical_pnp_ns_recovers_the_reference_values_exactly(
    classical: Electrolyte, epnpns: Electrolyte
) -> None:
    for c in (0.0, 1.0, 3.0, 9.9):
        for d in (0.0, 0.5, FAR_FROM_WALL_NM):
            assert classical.diffusivity("Na+", c, d) == classical.ion("Na+").diffusivity_0
            assert classical.mobility("Cl-", c, d) == classical.ion("Cl-").mobility_0
            assert classical.viscosity(c, d) == classical.viscosity_0
            assert classical.mass_density(c) == classical.mass_density_0
            assert classical.relative_permittivity(c) == 78.15
    assert epnpns.viscosity(3.0, 0.0) != pytest.approx(epnpns.viscosity_0)


# PHY-22
def test_correction_parts_switch_independently() -> None:
    both = models.create("willems2020_nacl", "diffusivity", "Na+")
    wall_only = models.create("willems2020_nacl", "diffusivity", "Na+", concentration=False)
    conc_only = models.create("willems2020_nacl", "diffusivity", "Na+", wall=False)
    c, d = 1.0, 0.2
    assert both.evaluate(c, d) == pytest.approx(wall_only.evaluate(c, d) * conc_only.evaluate(c, d))
    assert conc_only.evaluate(c, d) == pytest.approx(conc_only.evaluate(c, 0.0))


# PHY-22
def test_none_is_a_registered_model_not_a_code_branch() -> None:
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


# PHY-14
def test_parameter_file_mobilities_and_caps_agree_with_the_evaluated_model() -> None:
    document = load_corrections("willems2020_nacl")
    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl")
    for ion in electrolyte.species:
        tabulated = document.species[ion.name].mobility.mu0
        assert ion.mobility_0 == pytest.approx(tabulated, rel=REL_TOL)

    solvent, species = document.solvent, document.species
    at_cap = {
        "viscosity": (
            electrolyte.viscosity(5.3, FAR_FROM_WALL_NM),
            solvent.viscosity.cap_above_validity,
        ),
        "density": (electrolyte.mass_density(5.3), solvent.density.cap_above_validity),
        "permittivity": (
            electrolyte.relative_permittivity(5.3),
            solvent.permittivity.cap_above_validity,
        ),
    }
    for ion in electrolyte.species:
        at_cap[f"D_{ion.name}"] = (
            electrolyte.diffusivity(ion.name, 5.3, FAR_FROM_WALL_NM),
            species[ion.name].diffusivity.cap_above_validity,
        )
    # Caps are quoted to three figures, so the tolerance follows their precision, not the fit's.
    for name, (evaluated, tabulated) in at_cap.items():
        assert evaluated == pytest.approx(float(tabulated), rel=5e-3), (
            f"{name}: the fit at 5.3 M disagrees with the tabulated cap"
        )


# FR-25
def test_provenance_records_what_produced_each_property(epnpns: Electrolyte) -> None:
    record = epnpns.provenance
    assert record["parameter_file"] == "willems2020_nacl"
    assert record["driver"] == "average"
    assert record["corrections"]["viscosity"]["model"] == "willems2020_nacl"
    assert record["corrections"]["diffusivity:Na+"]["species"] == "Na+"


# FR-25
def test_provenance_distinguishes_an_ablated_run_from_the_full_one() -> None:
    full = dict(models.create("willems2020_nacl", "viscosity").provenance)
    ablated = dict(models.create("willems2020_nacl", "viscosity", concentration=False).provenance)
    assert full != ablated
    assert full["concentration_form"] == "poly_jones_dole"
    assert ablated["concentration_form"] == "off"
    assert ablated["concentration_enabled"] == "false"
    assert ablated["wall_enabled"] == "true"


def test_fit_metadata_is_not_reported_as_a_coefficient() -> None:
    parameters = models.create("willems2020_nacl", "viscosity").parameters
    assert "fc.r_squared" not in parameters
    assert "fw.r_squared" not in parameters
    assert parameters["fc.P1"] == pytest.approx(0.007558)


# VER-03
def test_corrections_load_returns_a_validated_document() -> None:
    document = load_corrections("willems2020_nacl")
    assert isinstance(document, CorrectionDocument)
    assert document.name == "willems2020_nacl"
    assert document.concentration_validity_M == (0.0, 5.3)
    fc = document.species["Na+"].diffusivity.fc
    assert fc is not None and fc.form == "inverse_poly_half"
    assert set(document.ion_wall_function.coefficients) == {"P1", "P2"}


# FR-16
def test_corrections_an_edited_file_is_reread_and_no_document_is_shared(tmp_path: Path) -> None:
    path = tmp_path / "edited.yaml"
    shipped = correction_file("willems2020_nacl").read_text(encoding="utf-8")
    path.write_text(shipped, encoding="utf-8")
    first = load_corrections(path)
    second = load_corrections(path)
    assert first is not second
    assert first.species is not second.species
    assert first.temperature_K == 298.15

    path.write_text(
        shipped.replace("temperature_K: 298.15", "temperature_K: 310.15"), encoding="utf-8"
    )
    assert load_corrections(path).temperature_K == 310.15


# IF-03
def test_corrections_reject_an_unknown_key_naming_it() -> None:
    with pytest.raises(ValidationError, match="P5"):
        FitBlock.model_validate(
            {"form": "inverse_poly_half", "P1": 0.2, "P2": -0.3, "P3": 0.2, "P4": -0.03, "P5": 0.1}
        )


def test_corrections_reject_a_missing_coefficient() -> None:
    with pytest.raises(ValidationError, match="P4"):
        FitBlock.model_validate({"form": "inverse_poly_half", "P1": 0.2, "P2": -0.3, "P3": 0.2})


def test_corrections_reject_an_unknown_form() -> None:
    with pytest.raises(ValidationError, match="unknown correction form 'not_a_form'"):
        FitBlock.model_validate({"form": "not_a_form", "P1": 1.0})


def test_corrections_reject_an_unknown_block_key() -> None:
    with pytest.raises(ValidationError, match="typo"):
        DielectricsBlock.model_validate({"protein": 20.0, "membrane": 3.2, "typo": 1.0})


def test_every_form_declares_its_parameters() -> None:
    assert set(FORM_PARAMETERS) == set(FORMS)


SECOND_FILE_CASE = """
schema: nanopnp/case/v0.5
name: two-correction-files
inputs:
  mesh: {path: pore.msh, format: msh41}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
  corrections:
    viscosity: {model: refitted_nacl, wall: true, concentration: true}
boundary_conditions: {bias_V: 0.1}
physics: {model: epnp-ns, solid_permittivities: {membrane: 3.2}}
numerics: {continuation: none}
"""
"""A case whose viscosity fit is read from a second installed file (FR-16)."""


def test_fr16_editing_a_second_correction_file_moves_the_materials_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nanopnp.core import paths
    from nanopnp.io.artefact import StageInputs
    from nanopnp.materials.stage import MaterialsStage
    from nanopnp.pipeline.case import loads_case

    shipped = correction_file("willems2020_nacl").read_text(encoding="utf-8")
    (tmp_path / "willems2020_nacl.yaml").write_text(shipped, encoding="utf-8")
    second = tmp_path / "refitted_nacl.yaml"
    second.write_text(shipped, encoding="utf-8")
    monkeypatch.setattr(paths, "CORRECTIONS_DIR", tmp_path)
    monkeypatch.setattr(models, "_REGISTRY", dict(models._REGISTRY))

    document = loads_case(SECOND_FILE_CASE)
    single = loads_case(SECOND_FILE_CASE.replace("refitted_nacl", "willems2020_nacl"))
    before = MaterialsStage().run(StageInputs(resolved=resolve(document)))
    reference = MaterialsStage().run(StageInputs(resolved=resolve(single)))
    assert set(before.inputs) == {"corrections", "corrections:refitted_nacl"}
    assert set(reference.inputs) == {"corrections"}

    second.write_text(shipped + "\n# refitted\n", encoding="utf-8")
    after = MaterialsStage().run(StageInputs(resolved=resolve(document)))
    assert after.hash != before.hash
    assert MaterialsStage().run(StageInputs(resolved=resolve(single))).hash == reference.hash


def test_fr16_an_edited_correction_file_is_read_again_in_the_same_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nanopnp.core import paths

    shipped = correction_file("willems2020_nacl").read_text(encoding="utf-8")
    edited = tmp_path / "refitted_nacl.yaml"
    edited.write_text(shipped, encoding="utf-8")
    monkeypatch.setattr(paths, "CORRECTIONS_DIR", tmp_path)
    monkeypatch.setattr(models, "_REGISTRY", dict(models._REGISTRY))

    before = models.create("refitted_nacl", "viscosity")
    assert isinstance(before, models.FittedCorrection)
    assert before.concentration_params["P1"] == pytest.approx(0.007558)

    assert "      P1: 0.007558 " in shipped
    edited.write_text(
        shipped.replace("      P1: 0.007558 ", "      P1: 0.008000 "), encoding="utf-8"
    )
    after = models.create("refitted_nacl", "viscosity")
    assert isinstance(after, models.FittedCorrection)
    assert after.concentration_params["P1"] == pytest.approx(0.008)

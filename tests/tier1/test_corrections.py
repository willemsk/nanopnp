"""VER-03 and VER-04: the shipped correction parameters reproduce their published check values.

These assertions come from SPECIFICATION.md section 7.2 and are cross-checked in
.knowledge/01-physics-epnpns.md. They gate the data file, not the solver: if a
coefficient is mistranscribed, or a correction form is applied with the wrong
sign, one of these fails.
"""

import math
from collections.abc import Mapping

import pytest

from nanopnp.core.constants import thermal_voltage
from nanopnp.materials.corrections import load_corrections

REL_TOL = 5e-4  # the check values are quoted to four significant figures


@pytest.fixture(scope="module")
def nacl():
    return load_corrections("willems2020_nacl")


def _inverse_poly_half(p: Mapping[str, float], c: float) -> float:
    """Evaluate (1 + P1 c^0.5 + P2 c + P3 c^1.5 + P4 c^2)^-1."""
    return 1.0 / (1.0 + p["P1"] * c**0.5 + p["P2"] * c + p["P3"] * c**1.5 + p["P4"] * c**2)


def _ion_wall(p: Mapping[str, float], d: float) -> float:
    """Evaluate f^w(d) = 1 - exp(-P1 (d + P2)). The offset is PLUS; see erratum 1."""
    return 1.0 - math.exp(-p["P1"] * (d + p["P2"]))


def _viscosity_wall(p: Mapping[str, float], d: float) -> float:
    """Evaluate f^w_eta(d) = 1 + exp(-P1 (d - P2)). The offset is MINUS here."""
    return 1.0 + math.exp(-p["P1"] * (d - p["P2"]))


def test_ver03_ion_wall_function_check_values(nacl):
    wall = nacl["ion_wall_function"]
    assert wall["P1"] == pytest.approx(6.2)  # 1/nm, not 62 and not 0.62
    assert _ion_wall(wall, 0.0) == pytest.approx(0.0601, rel=REL_TOL)
    assert _ion_wall(wall, 0.75) == pytest.approx(0.9910, rel=REL_TOL)


def test_ver03_viscosity_wall_function_check_values(nacl):
    fw = nacl["solvent"]["viscosity"]["fw"]
    assert 1.0 / _viscosity_wall(fw, 0.0) == pytest.approx(0.3790, rel=REL_TOL)
    assert 1.0 / _viscosity_wall(fw, 1.45) == pytest.approx(0.9876, rel=REL_TOL)


def test_ver03_bulk_properties_at_validity_limit(nacl):
    c = 5.3  # M, the upper end of the fit range; above this every property is capped

    eta = nacl["solvent"]["viscosity"]
    p = eta["fc"]
    f_eta = 1.0 + p["P1"] * c**0.5 + p["P2"] * c + p["P3"] * c**2 + p["P4"] * c**3.5
    assert eta["eta0"] * f_eta == pytest.approx(1.752e-3, rel=1e-3)

    rho = nacl["solvent"]["density"]
    q = rho["fc"]
    assert rho["rho0"] * (1.0 + q["P1"] * c + q["P2"] * c**2) == pytest.approx(1194.0, rel=1e-3)

    na = nacl["species"]["Na+"]["diffusivity"]
    assert na["D0"] * _inverse_poly_half(na["fc"], c) == pytest.approx(8.13e-10, rel=3e-3)

    cl = nacl["species"]["Cl-"]["diffusivity"]
    assert cl["D0"] * _inverse_poly_half(cl["fc"], c) == pytest.approx(1.071e-9, rel=1e-3)


def test_ver04_nernst_einstein_at_infinite_dilution(nacl):
    """mu_i0 = D_i0 / V_T holds at infinite dilution only (PHY-14)."""
    v_t = thermal_voltage()
    assert v_t == pytest.approx(25.693e-3, rel=1e-4)

    for ion, expected in (("Na+", 5.1922e-8), ("Cl-", 7.9089e-8)):
        species = nacl["species"][ion]
        assert species["diffusivity"]["D0"] / v_t == pytest.approx(expected, rel=REL_TOL)
        assert species["mobility"]["mu0"] == pytest.approx(expected, rel=1e-3)


def test_correction_file_declares_its_schema(nacl):
    assert nacl["schema"] == "nanopnp/corrections/v1"
    assert nacl["concentration_validity_M"] == [0.0, 5.3]

"""VER-77: a wall surface charge against Grahame's relation and Gauss's law (PHY-09, FR-20)."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import ngsolve as ngs
import pytest
import yaml

from nanopnp.core.constants import (
    GAS_CONSTANT,
    REFERENCE_TEMPERATURE_K,
    VACUUM_PERMITTIVITY,
)
from nanopnp.mesh.primitives import DEFAULT_BOUNDARIES, AxialSlabGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.physics.pb import ELECTROLYTE_PERMITTIVITY, debye_length_nm

CONCENTRATION_M = 0.1
ZETA = 2.0


def _grahame_sigma_C_m2() -> float:
    permittivity = VACUUM_PERMITTIVITY * ELECTROLYTE_PERMITTIVITY
    return math.sqrt(
        8.0 * permittivity * GAS_CONSTANT * REFERENCE_TEMPERATURE_K * CONCENTRATION_M * 1e3
    ) * math.sinh(0.5 * ZETA)


def _wall_potential(sign: float, divisions: int) -> float:
    lam = debye_length_nm(CONCENTRATION_M)
    model = models.create("pb", concentration_M=CONCENTRATION_M, order=2, debye_length_nm=lam)
    mesh = AxialSlabGeometry(radius_nm=lam, length_nm=20.0 * lam).generate(maxh_nm=lam / divisions)
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        boundaries=replace(DEFAULT_BOUNDARIES, potential="bulk"),
        surface_charge=sign * _grahame_sigma_C_m2() / model.scales.surface_charge_C_m2,
        surface_charge_boundary="wall",
    )
    return float(solution.state(mesh(0.5 * lam, 0.0)))


def test_ver77_grahame_zeta_from_a_wall_charge_on_an_axial_slab() -> None:
    errors = [abs(_wall_potential(1.0, divisions) - ZETA) / ZETA for divisions in (2, 4, 8)]
    assert errors[0] > errors[1] > errors[2], f"errors {errors} do not fall with refinement"
    assert errors[-1] < 1e-4, f"finest-mesh error {errors[-1]:.3g}"
    opposite = _wall_potential(-1.0, 8)
    assert opposite == pytest.approx(-_wall_potential(1.0, 8), rel=1e-6)


def _pore_case(
    wall_charge: float | None, radius_nm: float, **overrides: object
) -> dict[str, object]:
    classical = {
        name: {"model": "none"}
        for name in ("diffusivity", "mobility", "viscosity", "permittivity", "density", "steric")
    }
    document: dict[str, object] = {
        "schema": "nanopnp/case/v0.5",
        "name": "wall-charge",
        "geometry": {
            "pore": {"shape": "cylinder", "radius_nm": radius_nm},
            "membrane": {"thickness_nm": 10.0 * radius_nm},
            "reservoir": {"radius_nm": 3.0 * radius_nm},
        },
        "electrolyte": {
            "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
            "concentration_M": CONCENTRATION_M,
            "parameters": "willems2020_nacl",
            "corrections": classical,
        },
        "boundary_conditions": {"bias_V": 0.0},
        # A test device and not a material: it holds the displacement through the solid below
        # 1e-4 of the wall's charge, so the lumen alone balances it (VER-77 b).
        "physics": {"model": "pnp-ns", "solid_permittivities": {"membrane": 1e-2}},
        "outputs": ["fields"],
        **overrides,
    }
    if wall_charge is not None:
        document["boundary_conditions"] = {"bias_V": 0.0, "wall_charge_C_m2": wall_charge}
    return document


def test_ver77_gauss_balance_in_a_long_charged_lumen(tmp_path: Path) -> None:
    from scipy.integrate import simpson

    from nanopnp.core.constants import FARADAY
    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.store import Store
    from nanopnp.physics.models import concentration_field_name
    from nanopnp.pipeline.run import offered, run_case
    from nanopnp.post.export import restored

    lam = debye_length_nm(CONCENTRATION_M)
    radius = 5.0 * lam
    sigma = -0.02
    document = _pore_case(
        sigma, radius, numerics={"mesh": {"maxh_nm": 5.0, "wall_h_nm": lam / 5.0}}
    )
    case = tmp_path / "case.yaml"
    case.write_text(yaml.safe_dump(document), encoding="utf-8")
    result = run_case(case, store=Store(tmp_path / "store"), upto="solve", write=False)
    assert result.resolved is not None
    inputs = StageInputs(
        resolved=result.resolved, upstream=offered("solve", result.artefacts, own=False)
    )
    solution, _ = restored(inputs, result.artefacts["solve"])
    mesh = solution.space.mesh
    scale = solution.model.scales.concentration_mol_m3
    valences = {species.name: species.valence for species in result.resolved.electrolyte.species}

    import numpy as np

    nodes, weights = np.polynomial.legendre.leggauss(48)
    radii, radial_weights = 0.5 * radius * (nodes + 1.0), 0.5 * radius * weights
    components = {
        name: solution.component(concentration_field_name(name)) for name in solution.model.species
    }

    def charge_per_length_C_m(z_nm: float) -> float:
        total = 0.0
        for r_nm, weight in zip(radii, radial_weights, strict=True):
            point = mesh(float(r_nm), z_nm)
            density = sum(
                FARADAY * valences[name] * scale * component(point)
                for name, component in components.items()
            )
            total += weight * 2.0 * math.pi * r_nm * density
        return total

    half_length = 0.5 * 10.0 * radius - max(5.0 * lam, 2.0 * radius)
    planes = np.linspace(-half_length, half_length, 17)
    # C m^-3 nm^3 integrated over r and z: 1e-27 m^3 per nm^3, against the wall's C m^-2 nm^2 x nm.
    ionic_C = simpson([charge_per_length_C_m(z) for z in planes], x=planes) * 1e-27
    wall_C = sigma * 2.0 * math.pi * radius * 2.0 * half_length * 1e-18
    assert ionic_C == pytest.approx(-wall_C, rel=1e-3)


def test_ver77_zero_wall_charge_adds_no_term() -> None:
    from nanopnp.charge.stage import ResolvedFields
    from nanopnp.mesh.primitives import CylindricalPoreGeometry
    from nanopnp.physics.models import case_model
    from nanopnp.pipeline.case import loads_case, resolve
    from nanopnp.solve.state import residual_keywords, single_rung

    radius = 2.0
    mesh = CylindricalPoreGeometry(
        pore_radius_nm=radius, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=0.35)
    fields = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())

    def residual_vector(wall_charge: float | None) -> list[float]:
        document = _pore_case(wall_charge, radius)
        document["numerics"] = {"continuation": "none"}
        resolved = resolve(loads_case(yaml.safe_dump(document)))
        rung = single_rung(resolved, mesh, AXISYMMETRIC, ngs.CF(1.0), fields)
        model = case_model(resolved)
        state = model.cold_state(mesh, rung.boundaries)
        form = ngs.BilinearForm(state.space)
        form += model.residual_form(
            state.space, AXISYMMETRIC, state=state, **residual_keywords(rung)
        )
        vector = state.vec.CreateVector()
        form.Apply(state.vec, vector)
        return list(vector)

    without, zero, charged = residual_vector(None), residual_vector(0.0), residual_vector(-0.02)
    norm = max(abs(value) for value in without)
    assert max(abs(a - b) for a, b in zip(without, zero, strict=True)) <= 1e-14 * norm
    assert max(abs(a - b) for a, b in zip(without, charged, strict=True)) > 1e-6 * norm

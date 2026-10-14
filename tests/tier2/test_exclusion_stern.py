"""VER-59 (with FR-15, VER-31): Gauss's law across a generated ion-exclusion shell."""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import simpson

from nanopnp.core.constants import FARADAY, VACUUM_PERMITTIVITY
from nanopnp.core.hashing import file_hash
from nanopnp.density.grid import RadialGrid, read_grid, write_grid
from nanopnp.geometry.profile import (
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
    write_profile,
)
from nanopnp.io.store import Store
from nanopnp.materials.corrections import load_corrections
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import run_case
from nanopnp.solve.stage import warm_start_payload
from nanopnp.solve.state import restore

logger = logging.getLogger(__name__)

INNER_RADIUS_NM = 3.0

# VER-31
OFFSET_NM = 0.25

# VER-31
SIGMA_C_M2 = 0.0435

CENTRE_Z_NM = -12.0

PLANE_Z_NM = 12.0

SIMPSON_INTERVALS = 400

CASE = """\
schema: nanopnp/case/v0.5
name: stern-pipeline
inputs:
  profile: {{path: {profile}}}
  charge: {{path: {charge}, format: field1}}
geometry: {{reservoir: {{radius_nm: 40.0}}, membrane: {{centre_z_nm: {centre}}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
    steric:       {{model: none}}
boundary_conditions: {{bias_V: 0.0, ground: cis}}
physics:
  model: pnp
  flow: false
  variable_density: false
  inertia: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics: {{continuation: none}}
charge: {{exclusion_offset_nm: {offset}}}
outputs: [current]
"""


def _write_tube(path: Path) -> Path:
    points = [(3.0, -15.0), (5.0, -15.0), (5.0, 15.0), (3.0, 15.0)]
    array = np.asarray(points, dtype=np.float64)
    profile = PoreProfile(
        schema=PROFILE_SCHEMA,
        name="tube",
        provenance=ProfileProvenance(
            source="test",
            citation="tests/tier2/test_exclusion_stern.py",
            sha256="0" * 64,
            vertex_count=len(points),
            min_vertex_spacing_nm=min_vertex_spacing(array),
            min_feature_size_nm=min_feature_size(array),
            signed_area_nm2=signed_area(array),
        ),
        vertices=points,
    )
    return write_profile(profile, path)


def _write_band(directory: Path) -> Path:
    r = np.arange(3.0, 5.0 + 1e-9, 0.01)
    z = np.arange(-3.0, 27.0 + 1e-9, 0.01)
    across = np.where((r > 3.2) & (r < 4.8), np.sin(np.pi * (r - 3.2) / 1.6) ** 2, 0.0)
    off = np.abs(z - PLANE_Z_NM)
    along = np.where(
        off <= 9.0, 1.0, np.where(off < 11.0, np.cos(0.25 * np.pi * (off - 9.0)) ** 2, 0.0)
    )
    per_length = float(np.trapezoid(across * 2.0 * np.pi * r * 1e-9, r * 1e-9))
    line_charge = SIGMA_C_M2 * 2.0 * math.pi * INNER_RADIUS_NM * 1e-9
    values = -line_charge / per_length * along[:, None] * across[None, :]
    data = write_grid(RadialGrid.from_axes(r, z, values), directory / "band.npz", format="npz")
    grid = read_grid(data, format="npz")
    header = directory / "band.yaml"
    header.write_text(
        "schema: nanopnp/field/v0.5\nname: band\nquantity: volume_charge_density\n"
        "units: C/m^3\nprovenance: {source: analytic}\n"
        f"data: {{path: {data.name}, format: npz, sha256: {file_hash(data)}}}\n"
        f"grid: {{origin_nm: [{grid.origin_nm[0]!r}, {grid.origin_nm[1]!r}], "
        f"spacing_nm: [{grid.spacing_nm[0]!r}, {grid.spacing_nm[1]!r}], "
        f"shape: [{grid.shape[0]}, {grid.shape[1]}]}}\n",
        encoding="utf-8",
    )
    return header


@pytest.fixture(scope="module")
def solved(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    work = tmp_path_factory.mktemp("stern-pipeline")
    case = work / "stern.case.yaml"
    case.write_text(
        CASE.format(
            profile=_write_tube(work / "tube.yaml"),
            charge=_write_band(work),
            centre=CENTRE_Z_NM,
            offset=OFFSET_NM,
        ),
        encoding="utf-8",
    )
    started = time.perf_counter()
    result = run_case(case, store=Store(work / "store"), workspace=work / "work", upto="solve")
    seconds = time.perf_counter() - started
    solution = restore(
        warm_start_payload(result.artefacts["solve"]),
        resolved=resolve(load_case(case)),
        mesh_artefact=result.artefacts["mesh"],
        charge_artefact=result.artefacts["charge"],
    )
    logger.info(
        "VER-59 Stern through the pipeline: %d elements, walked to stage 10 in %.1f s",
        result.artefacts["mesh"].summary["quality"]["elements"],  # type: ignore[index]
        seconds,
    )
    return result, solution


def _potential_V(solution, r_nm: float) -> float:  # type: ignore[no-untyped-def]
    mesh = solution.space.mesh
    return float(solution.potential(mesh(r_nm, PLANE_Z_NM))) * solution.model.scales.potential_V


def _enclosed_C_m(solution, outer_nm: float) -> float:  # type: ignore[no-untyped-def]
    mesh = solution.space.mesh
    scales = solution.model.scales
    r = np.linspace(0.0, outer_nm, SIMPSON_INTERVALS + 1)
    density = np.zeros_like(r)
    for species, valence in (("Na+", 1), ("Cl-", -1)):
        concentration = solution.concentration(species)
        density += valence * np.array([float(concentration(mesh(x, PLANE_Z_NM))) for x in r])
    density *= FARADAY * scales.concentration_mol_m3
    return float(simpson(density * 2.0 * np.pi * r * 1e-9, x=r * 1e-9))


# VER-31
def test_ver59_the_drop_across_a_generated_shell_obeys_gausss_law(solved) -> None:  # type: ignore[no-untyped-def]
    result, solution = solved
    assert "exclusion" in result.artefacts["mesh"].parameters["materials"]  # type: ignore[operator]
    inner = INNER_RADIUS_NM - OFFSET_NM
    permittivity = load_corrections("willems2020_nacl").solvent.permittivity.eps_r0
    enclosed = _enclosed_C_m(solution, inner)
    expected_V = (
        enclosed
        * math.log(INNER_RADIUS_NM / inner)
        / (2.0 * math.pi * VACUUM_PERMITTIVITY * permittivity)
    )
    drop_V = _potential_V(solution, inner) - _potential_V(solution, INNER_RADIUS_NM)
    logger.info(
        "VER-59 Stern: lambda_enc %.6g C/m, drop %.6g mV against Gauss %.6g mV (%.2e relative)",
        enclosed,
        1e3 * drop_V,
        1e3 * expected_V,
        drop_V / expected_V - 1.0,
    )
    assert drop_V == pytest.approx(expected_V, rel=1e-2)


def test_ver59_the_potential_is_logarithmic_across_the_shell(solved) -> None:  # type: ignore[no-untyped-def]
    _, solution = solved
    inner = INNER_RADIUS_NM - OFFSET_NM
    ends = (_potential_V(solution, inner), _potential_V(solution, INNER_RADIUS_NM))
    middle = _potential_V(solution, math.sqrt(INNER_RADIUS_NM * inner))
    drop = ends[0] - ends[1]
    assert abs(middle - 0.5 * sum(ends)) <= 1e-3 * abs(drop)


def test_ver59_the_shell_drop_is_a_tenth_of_the_wall_potential_or_more(solved) -> None:  # type: ignore[no-untyped-def]
    _, solution = solved
    wall = _potential_V(solution, INNER_RADIUS_NM)
    drop = _potential_V(solution, INNER_RADIUS_NM - OFFSET_NM) - wall
    assert abs(drop) >= 0.1 * abs(wall)

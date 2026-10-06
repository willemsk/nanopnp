"""VER-59 at Tier 2: Gauss's law across a generated ion-exclusion shell (FR-15, VER-31).

VER-31's Stern benchmark, posed through stages 5 to 10 rather than on a drawn
slab: a planar Stern problem cannot be posed through stage 5's axisymmetric
region, so the body is a long cylindrical tube, ``r`` in ``[3, 5]`` nm, and the
check is cylindrical (WP30 plan, *Design* section 3). On a plane where ``phi`` is
flat in ``z``, the charge-free shell ``R - a < r < R`` carries the flux of the
mobile charge it encloses, so

``phi(R - a) - phi(R) = lambda_enc ln(R/(R - a)) / (2 pi eps_0 eps_r,f0)``

with ``lambda_enc = F sum z_i int_0^(R-a) c_i(r) 2 pi r dr`` read off the solved
concentrations on that plane, and ``phi`` logarithmic in ``r`` across the shell,
so that it takes the mean of its ends at ``sqrt(R (R - a))``.

The plane is 12 nm from the bilayer, not on it. **[tested]** With the membrane
on the analysis plane, as *Design* section 3 first placed it, the drop missed
Gauss's law by 6 %: the bilayer, ``eps`` = 3.2 on the body's outer side, curves
``phi`` in ``z`` across the 2 nm body, and ``d^2 phi/dz^2`` is not zero there
although ``d phi/dz`` is. The body is therefore 30 nm long and the bilayer is
moved 12 nm below its middle with ``geometry.membrane.centre_z_nm``.

The fixed charge is a supplied ``volume_charge_density``, smooth across the body
so that the consumer gates resolve it, equivalent per unit length to VER-31's
``sigma_s`` = 0.0435 C m^-2 on the inner wall. ``pnp`` with every correction
``none`` leaves the fluid and the shell at one permittivity, ``eps_r,f0``.
"""

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
from nanopnp.io.case import load_case
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.materials.corrections import load_corrections
from nanopnp.solve.stage import warm_start_payload
from nanopnp.solve.state import restore

logger = logging.getLogger(__name__)

INNER_RADIUS_NM = 3.0
"""``R``: the body's lumen-facing radius."""

OFFSET_NM = 0.25
"""``a``: ``a_Na/2`` of ``willems2020_nacl`` and VER-31's ``lambda_S`` (WP30 D15)."""

SIGMA_C_M2 = 0.0435
"""VER-31's ``sigma_s``, whose charge per unit length on ``r = R`` the band carries."""

CENTRE_Z_NM = -12.0
"""``geometry.membrane.centre_z_nm``: the bilayer 12 nm below the body's middle."""

PLANE_Z_NM = 12.0
"""The analysis plane in the model frame: the body's middle."""

SIMPSON_INTERVALS = 400
"""Simpson's rule on the plane over ``[0, R - a]``."""

CASE = """\
schema: nanopnp/case/v2
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
physics: {{model: pnp, flow: false, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{continuation: none}}
charge: {{exclusion_offset_nm: {offset}}}
outputs: [current]
"""


def _write_tube(path: Path) -> Path:
    """Write the tube ``r`` in [3, 5], ``z`` in [-15, 15] nm as a profile document."""
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
    """Write the fixed charge: ``sin^2`` across ``r`` in [3.2, 4.8], flat over 18 nm of ``z``.

    In the model frame, about the analysis plane, and smooth everywhere, so the
    consumer's quadrature gate resolves it; scaled so that its charge per unit
    length on the plane is ``-sigma_s 2 pi R``.
    """
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
        "schema: nanopnp/field/v1\nname: band\nquantity: volume_charge_density\n"
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
    """Walk the tube through stage 10 with the shell, and return the run and its solution."""
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
        case=load_case(case),
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
    """Return ``phi`` on the analysis plane at ``r``, in V."""
    mesh = solution.space.mesh
    return float(solution.potential(mesh(r_nm, PLANE_Z_NM))) * solution.model.scales.potential_V


def _enclosed_C_m(solution, outer_nm: float) -> float:  # type: ignore[no-untyped-def]
    """Return the mobile charge per unit length within ``r < outer_nm`` on the plane, C/m."""
    mesh = solution.space.mesh
    scales = solution.model.scales
    r = np.linspace(0.0, outer_nm, SIMPSON_INTERVALS + 1)
    density = np.zeros_like(r)
    for species, valence in (("Na+", 1), ("Cl-", -1)):
        concentration = solution.concentration(species)
        density += valence * np.array([float(concentration(mesh(x, PLANE_Z_NM))) for x in r])
    density *= FARADAY * scales.concentration_mol_m3
    return float(simpson(density * 2.0 * np.pi * r * 1e-9, x=r * 1e-9))


def test_ver59_the_drop_across_a_generated_shell_obeys_gausss_law(solved) -> None:  # type: ignore[no-untyped-def]
    """``Delta phi = lambda_enc ln(R/(R - a)) / (2 pi eps_0 eps_r,f0)`` to 1 % (VER-31's own)."""
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
    # Measured 1.3e-4 at the default sizes; 3.6e-3 at size_scale 2, where the
    # lumen's concentration is coarser and the enclosed charge is what moves.
    assert drop_V == pytest.approx(expected_V, rel=1e-2)


def test_ver59_the_potential_is_logarithmic_across_the_shell(solved) -> None:  # type: ignore[no-untyped-def]
    """``phi(sqrt(R (R - a)))`` is the mean of the ends to 1e-3 of the drop: no ions in the shell.

    A shell that held ions would curve the profile by its own space charge; the
    geometric mean is where the logarithm takes the mean of its ends.
    """
    _, solution = solved
    inner = INNER_RADIUS_NM - OFFSET_NM
    ends = (_potential_V(solution, inner), _potential_V(solution, INNER_RADIUS_NM))
    middle = _potential_V(solution, math.sqrt(INNER_RADIUS_NM * inner))
    drop = ends[0] - ends[1]
    assert abs(middle - 0.5 * sum(ends)) <= 1e-3 * abs(drop)


def test_ver59_the_shell_drop_is_a_tenth_of_the_wall_potential_or_more(solved) -> None:  # type: ignore[no-untyped-def]
    """The margin the benchmark lives on: the shell is an effect, not a correction."""
    _, solution = solved
    wall = _potential_V(solution, INNER_RADIUS_NM)
    drop = _potential_V(solution, INNER_RADIUS_NM - OFFSET_NM) - wall
    # 17.8 % measured: the drop is 6.54 mV on a wall potential of -36.8 mV.
    assert abs(drop) >= 0.1 * abs(wall)

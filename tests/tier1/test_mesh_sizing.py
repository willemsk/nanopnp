"""VER-53: the size fields of a generated mesh, and the case keys that set them (FR-10, NUM-30).

``wall_h_nm: auto`` is ``size_scale x min(0.05 nm, lambda_D / 5)`` with lambda_D
at ``eps_r,f0`` (section 5.3.1 NOTE on ``numerics.mesh``). The oracle is NUM-30's
own check values, 1.357, 0.304 and 0.175 nm at 0.05, 1 and 3 M, and the
closed-form crossover ``lambda_D = 0.25 nm``, which the WP21 plan puts at
1.4741 M (Design section 2).
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from nanopnp.core.paths import profile_file
from nanopnp.io.case import (
    CaseValidationError,
    UnsupportedCaseSection,
    loads_case,
    resolve,
)
from nanopnp.mesh.generate import GATE_CONSTANTS, sizing_parameters
from nanopnp.mesh.sizing import (
    SIZES,
    WALL_CEILING_NM,
    case_debye_length_nm,
    ionic_strength_M,
    resolve_wall_size,
)
from nanopnp.sweep.plan import plan_from_document

CASE = """\
schema: nanopnp/case/v2
name: sizing
inputs:
  profile: {{path: {path}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: {concentration}
  temperature_K: {temperature}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
{extra}"""

MESH_CASE = """\
schema: nanopnp/case/v2
name: supplied
inputs:
  mesh: {{path: pore.msh, format: msh41}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics:
  mesh: {{{mesh}}}
"""


def case(
    concentration: float = 1.0,
    temperature: float = 298.15,
    extra: str = "",
    path: Path | None = None,
) -> str:
    """Return a profile case at ``concentration`` and ``temperature``."""
    return CASE.format(
        path=path or profile_file("clya_reference_profile"),
        concentration=concentration,
        temperature=temperature,
        extra=extra,
    )


@pytest.mark.parametrize(
    ("concentration", "debye_nm", "auto_nm"),
    [
        (0.05, 1.357, 0.05),
        (1.0, 0.3035, 0.05),
        (3.0, 0.1752, 0.03505),
        (5.0, 0.1357, 0.02715),
    ],
)
def test_ver53_auto_is_the_ceiling_or_num30_whichever_is_finer(
    concentration: float, debye_nm: float, auto_nm: float
) -> None:
    """NUM-30's lambda_D at eps_r,f0, and ``min(0.05, lambda_D / 5)`` (D7)."""
    wall = resolve_wall_size(loads_case(case(concentration)))
    assert wall.debye_length_nm == pytest.approx(debye_nm, abs=5e-4)
    assert wall.wall_h_nm == pytest.approx(auto_nm, abs=1e-4)
    assert wall.source == "auto"
    # ``auto`` at size_scale 1 is never coarser than NUM-30; only a scale or an
    # explicit size makes it so, and that is recorded rather than refused.
    assert wall.coarser_than_num30 is False
    coarse = resolve_wall_size(
        loads_case(case(concentration, extra="numerics: {mesh: {size_scale: 4.0}}\n"))
    )
    assert coarse.coarser_than_num30 is (4.0 * auto_nm > debye_nm / 5.0)


def test_ver53_num30_alone_would_be_coarse_at_low_salt() -> None:
    """lambda_D / 5 is 0.27 nm at 0.05 M and 0.035 nm at 3 M; the ceiling holds below 1.474 M."""
    low = resolve_wall_size(loads_case(case(0.05)))
    high = resolve_wall_size(loads_case(case(3.0)))
    assert low.debye_target_nm == pytest.approx(0.27, abs=2e-3)
    assert high.debye_target_nm == pytest.approx(0.035, abs=1e-4)
    assert low.wall_h_nm == WALL_CEILING_NM


def test_ver53_the_crossover_is_at_1_4741_molar() -> None:
    """``lambda_D = 0.25 nm`` where ``c = eps_0 eps_r,f0 R T / (2 F^2 (0.25 nm)^2)``."""
    from nanopnp.core.constants import FARADAY, GAS_CONSTANT, VACUUM_PERMITTIVITY
    from nanopnp.core.scaling import REFERENCE_PERMITTIVITY

    crossover_M = (
        VACUUM_PERMITTIVITY
        * REFERENCE_PERMITTIVITY
        * GAS_CONSTANT
        * 298.15
        / (2.0 * FARADAY**2 * (0.25e-9) ** 2)
        / 1e3
    )
    assert crossover_M == pytest.approx(1.4741, abs=1e-4)
    below = resolve_wall_size(loads_case(case(crossover_M * 0.999)))
    above = resolve_wall_size(loads_case(case(crossover_M * 1.001)))
    assert below.wall_h_nm == WALL_CEILING_NM
    assert above.wall_h_nm < WALL_CEILING_NM


def test_ver53_size_scale_multiplies_every_size_and_temperature_enters_as_sqrt_t() -> None:
    """``size_scale`` scales the wall and the table alike; lambda_D goes as sqrt(T) at fixed I."""
    scaled = resolve_wall_size(loads_case(case(3.0, extra="numerics: {mesh: {size_scale: 2.0}}\n")))
    plain = resolve_wall_size(loads_case(case(3.0)))
    assert scaled.wall_h_nm == pytest.approx(2.0 * plain.wall_h_nm, rel=1e-15)
    table = SIZES.scaled(2.0).summary()
    for key, value in SIZES.summary().items():
        assert table[key] == pytest.approx(2.0 * float(value), rel=1e-15)  # type: ignore[arg-type]

    warm = resolve_wall_size(loads_case(case(3.0, temperature=350.0)))
    assert warm.debye_length_nm / plain.debye_length_nm == pytest.approx(
        math.sqrt(350.0 / 298.15), rel=1e-12
    )

    explicit = resolve_wall_size(
        loads_case(case(1.0, extra="numerics: {mesh: {wall_h_nm: 0.04, size_scale: 0.5}}\n"))
    )
    assert explicit.wall_h_nm == pytest.approx(0.02)
    assert explicit.source == "explicit"


def test_ver53_the_ionic_strength_weights_valence_squared() -> None:
    """``I = 1/2 sum z_i^2 c``: c for NaCl, and lambda_D follows it."""
    document = loads_case(case(0.5))
    assert ionic_strength_M(document) == pytest.approx(0.5)
    assert case_debye_length_nm(document) == pytest.approx(0.4292, abs=1e-4)


def test_ver53_the_recipe_carries_the_backend_the_sizes_and_the_gate() -> None:
    """D10: everything that moves a vertex of a generated mesh or a verdict of its gate."""
    wall = resolve_wall_size(loads_case(case(3.0)))
    recipe = sizing_parameters(wall, SIZES)
    assert recipe["backend"] == "netgen"
    assert recipe["wall"] == wall.summary()
    assert recipe["table"] == SIZES.summary()
    assert recipe["grading"] == 0.2
    assert recipe["optsteps2d"] == 5
    assert recipe["gate"] == dict(GATE_CONSTANTS)


@pytest.mark.parametrize(
    ("extra", "error", "fragment"),
    [
        ("numerics: {mesh: {backend: gmsh}}\n", UnsupportedCaseSection, "backend is 'gmsh'"),
        ("numerics: {mesh: {boundary_layer: true}}\n", UnsupportedCaseSection, "FR-11"),
        (
            "geometry: {analyte: {shape: sphere, a_nm: 1.0}}\n",
            UnsupportedCaseSection,
            "geometry.analyte",
        ),
        (
            "geometry: {membrane: {thickness_nm: 0.0}}\n",
            CaseValidationError,
            "geometry.membrane.thickness_nm is 0.0",
        ),
        (
            "geometry: {membrane: {thickness_nm: .inf}}\n",
            CaseValidationError,
            "geometry.membrane.thickness_nm is inf",
        ),
        (
            "geometry: {reservoir: {radius_nm: -1.0}}\n",
            CaseValidationError,
            "geometry.reservoir.radius_nm is -1.0",
        ),
        (
            "geometry: {membrane: {centre_z_nm: .nan}}\n",
            CaseValidationError,
            "geometry.membrane.centre_z_nm is nan",
        ),
        (
            "numerics: {mesh: {wall_h_nm: 0.0}}\n",
            CaseValidationError,
            "numerics.mesh.wall_h_nm is 0.0",
        ),
        (
            "numerics: {mesh: {wall_h_nm: .nan}}\n",
            CaseValidationError,
            "numerics.mesh.wall_h_nm is nan",
        ),
    ],
)
def test_ver53_a_generated_mesh_s_refusals_name_the_key(
    extra: str, error: type[Exception], fragment: str
) -> None:
    """D14: each refusal names the key and its value."""
    with pytest.raises(error) as caught:
        resolve(loads_case(case(extra=extra)))
    assert fragment in str(caught.value)


@pytest.mark.parametrize(
    ("mesh", "key"),
    [
        ("backend: gmsh", "numerics.mesh.backend"),
        ("wall_h_nm: 0.04", "numerics.mesh.wall_h_nm"),
        ("size_scale: 2.0", "numerics.mesh.size_scale"),
        ("boundary_layer: true", "numerics.mesh.boundary_layer"),
    ],
)
def test_ver53_a_mesh_key_beside_a_supplied_mesh_is_refused_naming_it(mesh: str, key: str) -> None:
    """D14: nothing meshes beside ``inputs.mesh``, so a mesh key there would change nothing."""
    with pytest.raises(CaseValidationError, match=key.replace(".", r"\.")):
        loads_case(MESH_CASE.format(mesh=mesh))
    loads_case(MESH_CASE.format(mesh="wall_h_nm: auto, size_scale: 1.0"))


def _sweep(tmp_path: Path, values: list[float]) -> Path:
    """Write a profile case and a sweep over its concentration."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    base = tmp_path / "base.case.yaml"
    base.write_text(case(), encoding="utf-8")
    sweep = tmp_path / "sweep.yaml"
    sweep.write_text(
        "schema: nanopnp/sweep/v1\n"
        "name: salt\n"
        f"base: {base}\n"
        "axes:\n"
        f"  - {{name: salt, path: electrolyte.concentration_M, values: {values}}}\n",
        encoding="utf-8",
    )
    return sweep


def test_ver53_a_salt_axis_is_a_barrier_only_where_it_moves_the_wall(tmp_path: Path) -> None:
    """D15: [1, 3] M resolves two wall sizes and severs; [0.1, 1] M resolves one and chains."""
    severed = plan_from_document(_sweep(tmp_path / "severed", [1.0, 3.0]))
    assert [point.parent for point in severed.points] == [None, None]
    assert any("electrolyte.concentration_M" in warning for warning in severed.warnings)

    chained = plan_from_document(_sweep(tmp_path / "chained", [0.1, 1.0]))
    assert [point.parent for point in chained.points] == [None, 0]
    assert chained.warnings == ()


def test_ver53_upstream_geometry_axes_are_barriers(tmp_path: Path) -> None:
    """D15: an axis over the membrane moves a generated mesh, so each value is its own root."""
    base = tmp_path / "base.case.yaml"
    base.write_text(case(extra="geometry: {membrane: {centre_z_nm: 0.0}}\n"), encoding="utf-8")
    sweep = tmp_path / "sweep.yaml"
    sweep.write_text(
        "schema: nanopnp/sweep/v1\n"
        "name: shift\n"
        f"base: {base}\n"
        "axes:\n"
        "  - {name: shift, path: geometry.membrane.centre_z_nm, values: [0.0, 0.1]}\n",
        encoding="utf-8",
    )
    plan = plan_from_document(sweep)
    assert [point.parent for point in plan.points] == [None, None]

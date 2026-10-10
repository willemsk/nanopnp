"""VER-54 at Tier 2: the reference fixture meshed by both backends, and solved on both (WP23).

The shipped ClyA profile goes through ``inputs.profile``, stage 5 and stage 6 at
the section 5.2.2 sizes on netgen and on Gmsh. Stage 5 runs once: its key does
not name the backend (D1), so the second backend reads it from the store.

What is gated: the three stage-6 gates on each mesh, one vocabulary, every
profile vertex a mesh node, VER-10 on Gmsh at ``size_scale`` 1, 2, 4 and 8 (the
D4 regression: without D4's fields Gmsh fails at 2 and 4), and the frozen case of
WP22 D9 on both backends' meshes at ``size_scale`` 2 to 1e-3.

The 1e-3 is argued, not fitted (WP23 plan, Design section 4). The two backends'
conductances were measured 1.25e-4 apart at ``size_scale`` 2. Refining netgen's
own mesh from ``size_scale`` 2 to 1 moves its conductance by 2.0e-4, so the
backends differ by less than a refinement moves either, and the bound sits eight
times above the measured value: it passes a mesher difference of the size a
discretisation change makes, and fails one that is a different region or a
dropped size field. Everything else is logged at INFO beside each other: counts,
quality and the D9 wall statistics.
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from nanopnp.core.paths import profile_file
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import read_region
from nanopnp.io.store import Store
from nanopnp.mesh.adapter import read
from nanopnp.mesh.quality import QUALITY_FLOOR
from nanopnp.pipeline.run import (
    RunResult,
    run_case,
)

logger = logging.getLogger(__name__)

FROZEN_SIZE_SCALE = 2.0
"""WP22 D9's ``size_scale`` at Tier 2, on both backends' meshes."""

CONDUCTANCE_RTOL = 1e-3
"""The frozen case's bound on ``|G_gmsh / G_netgen - 1|``: 8 x the measured 1.25e-4."""

PROFILE_VERTICES = 185
"""The delivered reference polygon's vertex count (section 5.2.1)."""

MESH_CASE = """\
schema: nanopnp/case/v0.5
name: backends-{backend}-{concentration}-{size_scale}
inputs:
  profile: {{path: {profile}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: {concentration}
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{backend: {backend}, size_scale: {size_scale}}}}}
"""

FROZEN_CASE = """\
schema: nanopnp/case/v0.5
name: frozen-{backend}
inputs:
  profile: {{path: {profile}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
    steric:       {{model: none}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics:
  model: pnp
  flow: false
  variable_density: false
  inertia: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics:
  continuation: none
  stabilisation: none
  mesh: {{backend: {backend}, size_scale: {size_scale}}}
outputs: [current]
"""
"""WP22 D9: uncharged, so G is geometric; 1 M, +50 mV, ground *cis*, every correction ``none``."""


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return the module's working directory."""
    return tmp_path_factory.mktemp("backends")


@pytest.fixture(scope="module")
def store(root: Path) -> Store:
    """Return the module's own store: stage 5 is shared between the backends through it."""
    return Store(root / "store")


def _mesh(
    root: Path, store: Store, backend: str, *, concentration: float = 1.0, size_scale: float = 1.0
) -> RunResult:
    """Run the fixture through stage 6 on ``backend``."""
    case = root / f"{backend}-{concentration}-{size_scale}.case.yaml"
    case.write_text(
        MESH_CASE.format(
            backend=backend,
            concentration=concentration,
            size_scale=size_scale,
            profile=profile_file("clya_reference_profile"),
        ),
        encoding="utf-8",
    )
    return run_case(case, store=store, upto="mesh", write=False)


def _seconds(result: RunResult, stage: str) -> float:
    """Return a stage's wall time in this run."""
    return next(entry.seconds for entry in result.stages if entry.name == stage)


def test_ver54_the_fixture_meshes_on_both_backends_to_one_vocabulary(
    gmsh_module: ModuleType, root: Path, store: Store
) -> None:
    """FR-10: both meshes pass every stage-6 gate, name the same sets and keep every vertex."""
    netgen = _mesh(root, store, "netgen")
    gmsh = _mesh(root, store, "gmsh")
    # D1: one region, assembled once.
    assert gmsh.artefacts["region"].hash == netgen.artefacts["region"].hash
    assert next(entry for entry in gmsh.stages if entry.name == "region").cached
    record = read_region(gmsh.artefacts["region"].payload[REGION_PAYLOAD])
    profile = {tuple(point) for point in record.points().tolist()}
    assert len(profile) == PROFILE_VERTICES

    for backend, result in (("netgen", netgen), ("gmsh", gmsh)):
        artefact = result.artefacts["mesh"]
        assert artefact.parameters["materials"] == ["electrolyte", "membrane", "protein"]
        assert artefact.parameters["boundaries"] == sorted(record.edge_counts)
        summary = artefact.summary
        quality = summary["quality"]
        assert quality["min_sicn"] > QUALITY_FLOOR  # type: ignore[index]
        assert quality["min_gamma"] > QUALITY_FLOOR  # type: ignore[index]
        data = read(artefact.payload["mesh"], format="msh41")
        assert profile <= {tuple(point) for point in data.vertices.tolist()}, backend
        statistics = summary["sizing"]["wall_statistics"]  # type: ignore[index]
        logger.info(
            "fixture on %s %s at the default sizes: %d triangles, min SICN %.4f, mean SICN %.4f, "
            "min gamma %.4f, mean gamma %.4f; wall %d segments, mean %.3f, p95 %.3f, max %.3f x "
            "the target; stage 6 %.1f s",
            backend,
            summary["sizing"]["backend_version"],  # type: ignore[index]
            summary["elements"],
            quality["min_sicn"],  # type: ignore[index]
            quality["mean_sicn"],  # type: ignore[index]
            quality["min_gamma"],  # type: ignore[index]
            quality["mean_gamma"],  # type: ignore[index]
            statistics["segments"],
            statistics["mean_ratio"],
            statistics["p95_ratio"],
            statistics["max_ratio"],
            _seconds(result, "mesh"),
        )


@pytest.mark.parametrize(
    ("concentration", "wall_nm"), [(1.0, 0.05), (3.0, 0.03505), (5.0, 0.02715)]
)
def test_ver54_gmsh_holds_the_wall_size_gate_at_three_wall_sizes(
    gmsh_module: ModuleType, root: Path, store: Store, concentration: float, wall_nm: float
) -> None:
    """D9 of WP21 on Gmsh: the ceiling, and NUM-30 at 3 M and 5 M; the statistics recorded."""
    result = _mesh(root, store, "gmsh", concentration=concentration)
    sizing = result.artefacts["mesh"].summary["sizing"]
    statistics = sizing["wall_statistics"]  # type: ignore[index]
    assert sizing["wall"]["wall_h_nm"] == pytest.approx(wall_nm, abs=5e-6)  # type: ignore[index]
    assert statistics["mean_ratio"] <= 1.15
    assert statistics["max_ratio"] <= 2.0
    quality = result.artefacts["mesh"].summary["quality"]
    logger.info(
        "gmsh wall %.5f nm (%g M): %d triangles, min SICN %.4f, min gamma %.4f; wall %d segments, "
        "mean %.3f, p95 %.3f, max %.3f x the target; stage 6 %.1f s",
        sizing["wall"]["wall_h_nm"],  # type: ignore[index]
        concentration,
        result.artefacts["mesh"].summary["elements"],
        quality["min_sicn"],  # type: ignore[index]
        quality["min_gamma"],  # type: ignore[index]
        statistics["segments"],
        statistics["mean_ratio"],
        statistics["p95_ratio"],
        statistics["max_ratio"],
        _seconds(result, "mesh"),
    )


@pytest.mark.parametrize("size_scale", [2.0, 4.0, 8.0])
def test_ver54_gmsh_passes_ver10_at_every_size_scale(
    gmsh_module: ModuleType, root: Path, store: Store, size_scale: float
) -> None:
    """D4's regression: Gmsh given the table alone fails VER-10 here at 2 and 4.

    ``size_scale`` 1 is the first test's mesh. Stage 6 would abort on a failed
    gate; the minima are asserted as well, so the verdict does not rest on the
    abort alone, and logged.
    """
    result = _mesh(root, store, "gmsh", size_scale=size_scale)
    summary = result.artefacts["mesh"].summary
    quality = summary["quality"]
    assert quality["min_sicn"] > QUALITY_FLOOR  # type: ignore[index]
    assert quality["min_gamma"] > QUALITY_FLOOR  # type: ignore[index]
    statistics = summary["sizing"]["wall_statistics"]  # type: ignore[index]
    logger.info(
        "gmsh at size_scale %g: %d triangles, min SICN %.4f, min gamma %.4f; wall %d segments, "
        "mean %.3f, max %.3f x the target; stage 6 %.1f s",
        size_scale,
        summary["elements"],
        quality["min_sicn"],  # type: ignore[index]
        quality["min_gamma"],  # type: ignore[index]
        statistics["segments"],
        statistics["mean_ratio"],
        statistics["max_ratio"],
        _seconds(result, "mesh"),
    )


def test_ver54_the_frozen_case_conducts_alike_on_both_backends_meshes(
    gmsh_module: ModuleType, root: Path, store: Store
) -> None:
    """The same region measured by a solve: ``|G_gmsh / G_netgen - 1| <= 1e-3`` at size_scale 2."""
    conductance = {}
    elements = {}
    seconds = {}
    for backend in ("netgen", "gmsh"):
        case = root / f"frozen-{backend}.case.yaml"
        case.write_text(
            FROZEN_CASE.format(
                backend=backend,
                size_scale=FROZEN_SIZE_SCALE,
                profile=profile_file("clya_reference_profile"),
            ),
            encoding="utf-8",
        )
        result = run_case(case, store=store, workspace=root / f"frozen-{backend}", write=False)
        conductance[backend] = float(result.quantities["conductance_S"])  # type: ignore[arg-type]
        elements[backend] = result.artefacts["mesh"].summary["elements"]
        seconds[backend] = _seconds(result, "solve")
        assert result.manifest.geometry_and_mesh["sizing"]["backend"] == backend  # type: ignore[index]
    deviation = conductance["gmsh"] / conductance["netgen"] - 1.0
    logger.info(
        "frozen case (WP22 D9) at size_scale %g, stabilisation none: G netgen %.6e S (%d "
        "triangles), G gmsh %.6e S (%d triangles); G_gmsh/G_netgen - 1 = %+.3e against %g; "
        "solve %.1f s and %.1f s",
        FROZEN_SIZE_SCALE,
        conductance["netgen"],
        elements["netgen"],
        conductance["gmsh"],
        elements["gmsh"],
        deviation,
        CONDUCTANCE_RTOL,
        seconds["netgen"],
        seconds["gmsh"],
    )
    assert np.isfinite(deviation)
    assert abs(deviation) <= CONDUCTANCE_RTOL

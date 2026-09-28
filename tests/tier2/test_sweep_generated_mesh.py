"""VER-37 (Tier 2) — a sweep over a *generated* mesh warm-starts (FR-24, WP21 D15).

``tests/tier2/test_sweep.py`` asserts the warm path on a supplied ``.vol`` mesh,
where the parent's stage-10 key can be computed from the bare case. A case that
generates its mesh cannot be keyed that way: its mesh exists only as stage 6's
stored artefact, keyed on the stage-5 recipe (WP21 D10). The member runner used
to key the parent from the bare case, which raised for every such sweep and was
caught as a cold fallback, so every member climbed the full ladder while WP21
D15's barrier logic promised salt sweeps would "keep their warm starts". This
module is the guard: a two-point bias sweep over the Tier-1 synthetic profile,
whose second member must start warm from the first.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from nanopnp.io.store import Store
from nanopnp.mesh.profile import (
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
    write_profile,
)
from nanopnp.sweep.plan import plan_from_document, write_plan
from nanopnp.sweep.run import MemberResult, run_plan

BASE = """\
schema: nanopnp/case/v2
name: generated-sweep
inputs:
  profile: {{path: {path}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.02, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: 20.0}}}}
outputs: [current]
"""
"""The coarse case of ``tests/tier1/test_mesh_generate.py``: a few seconds a solve."""

SWEEP = """\
schema: nanopnp/sweep/v1
name: generated
base: base.yaml
axes:
  - name: bias
    path: boundary_conditions.bias_V
    origin: 0
    values: [0.02, 0.04]
"""
"""A bias step, which WP21 D15 does not make a barrier: the mesh is one mesh."""


def _write_parallelogram(path: Path) -> Path:
    """Write the slanted 1 nm body of ``tests/tier1/test_mesh_generate.py``."""
    points = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
    array = np.asarray(points, dtype=np.float64)
    profile = PoreProfile.model_validate(
        {
            "schema": PROFILE_SCHEMA,
            "name": "parallelogram",
            "provenance": ProfileProvenance(
                source="test",
                citation="tests/tier2/test_sweep_generated_mesh.py",
                sha256="0" * 64,
                vertex_count=len(points),
                min_vertex_spacing_nm=min_vertex_spacing(array),
                min_feature_size_nm=min_feature_size(array),
                signed_area_nm2=signed_area(array),
            ).model_dump(),
            "vertices": points,
        }
    )
    return write_profile(profile, path)


@pytest.fixture(scope="module")
def members(tmp_path_factory: pytest.TempPathFactory) -> tuple[MemberResult, ...]:
    """Plan and run the two-point sweep into a fresh store."""
    work = tmp_path_factory.mktemp("generated-sweep")
    profile = _write_parallelogram(work / "profile.yaml")
    (work / "base.yaml").write_text(BASE.format(path=profile), encoding="utf-8")
    (work / "sweep.yaml").write_text(SWEEP, encoding="utf-8")
    plan = plan_from_document(work / "sweep.yaml")
    directory = work / "sweep"
    write_plan(plan, directory)
    return run_plan(plan, directory, store=Store(work / "store"))


def test_ver37_a_generated_mesh_sweep_warm_starts_from_its_parent(
    members: tuple[MemberResult, ...],
) -> None:
    """The child keys its parent through the parent's stored mesh and starts warm."""
    by_index = {member.index: member for member in members}
    assert all(member.status == "ok" for member in members), [m.error for m in members]
    root, child = dict(by_index[0].warm_start or {}), dict(by_index[1].warm_start or {})
    assert root["status"] == "cold"
    assert child["status"] == "warm", child
    assert by_index[1].iterations is not None and by_index[0].iterations is not None
    assert by_index[1].iterations < by_index[0].iterations

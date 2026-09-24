"""VER-25 and VER-29: stage 7 as a stage — invocable, cancellable, keyed.

The gates themselves are ``tests/tier1/test_charge_fields.py`` (the unit half)
and ``tests/tier2/test_charge_conservation.py`` (the deployed mesh). What is
under test here is the wrapper FR-27 asks for: that stage 7 can be run on its
own from a case file, that cancelling it leaves nothing behind, and that its
artefact key is the field's *contents* rather than the path it was read from.

The last one is the reason this file writes the same header twice under two
names. A key taken over the file path would make a moved input a different run,
and a sweep that copies its inputs into a scratch directory would then miss every
cache hit it should have had -- while every test that reads a field once, from
one place, would pass.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nanopnp.charge.stage import FieldStage
from nanopnp.core.stages import CancelFlag, Cancelled, create, describe
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import UnsupportedCaseSection, loads_case
from nanopnp.mesh.adapter import from_ngsolve, write_msh41

RING = "{centre_r_nm: 2.0, centre_z_nm: 4.0, width_nm: 0.3, charge_e: -12.0}"
"""The Tier-1 ring of ``test_charge_fields``: 0.3 nm wide, so that a mesh this
file can afford in seconds resolves it. The reference 0.085 nm is Tier 2."""

FIELD_DOCUMENT = f"""
schema: nanopnp/field/v1
name: ring
quantity: areal_charge_density
units: C/m^2
q_net_e: -12.0
provenance: {{source: analytic}}
form:
  name: gaussian_ring
  parameters: {RING}
  origin_nm: [0.0, 0.0]
  spacing_nm: [0.01, 0.01]
  shape: [500, 900]
"""


@pytest.fixture(scope="module")
def mesh_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write a named rectangle covering ``r in [0, 6]``, ``z in [0, 10]``, in nm.

    Named in the vocabulary directly rather than through a mapping: what the
    mapping does is VER-27's subject, and giving this mesh exporter-style names
    would test it a second time in the file that is about something else.
    """
    import netgen.occ as occ
    import ngsolve as ngs

    face = occ.Rectangle(6.0, 10.0).Face()
    face.name = "electrolyte"
    face.edges.Min(occ.X).name = "axis"
    face.edges.Max(occ.X).name = "wall"
    face.edges.Min(occ.Y).name = "trans"
    face.edges.Max(occ.Y).name = "cis"
    generated = ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=0.15))
    directory = tmp_path_factory.mktemp("mesh")
    return write_msh41(from_ngsolve(generated), directory / "box.msh")


@pytest.fixture(scope="module")
def field_document(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the field header the case names."""
    path = tmp_path_factory.mktemp("field") / "ring.yaml"
    path.write_text(FIELD_DOCUMENT, encoding="utf-8")
    return path


def case_text(mesh_path: Path, field_path: Path | None) -> str:
    """Return a case naming ``mesh_path``, and ``field_path`` if there is one."""
    charge = "" if field_path is None else f"\n  charge: {{path: {field_path}, format: field1}}"
    return f"""
schema: nanopnp/case/v2
name: field-probe
inputs:
  mesh: {{path: {mesh_path}, format: gmsh}}{charge}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1, ground: cis}}
physics: {{model: pnp-ns}}
numerics: {{continuation: none}}
"""


def _inputs(mesh_path: Path, field_path: Path | None) -> StageInputs:
    """Return the stage inputs for a case naming these two files."""
    return StageInputs(case=loads_case(case_text(mesh_path, field_path)))


# -- introspection -------------------------------------------------------------


def test_ver25_the_field_stage_is_stage_seven_and_describes_itself() -> None:
    """The registry's row and the stage's own ``describe()`` are the same row."""
    stage = create("charge")
    assert isinstance(stage, FieldStage)
    assert stage.describe() == describe("charge")
    assert stage.describe().number == 7


def test_ver25_a_case_supplying_no_field_is_refused_naming_the_stage(mesh_file: Path) -> None:
    """No field is no work, and stage 7 says so rather than emitting an empty artefact.

    An empty artefact would hash, cache and flow downstream exactly as a real one
    does, and the solve would run with zero fixed charge everywhere while every
    record said stage 7 had succeeded.
    """
    with pytest.raises(
        UnsupportedCaseSection, match=re.escape("neither inputs.charge nor inputs.eps_r")
    ):
        FieldStage().run(_inputs(mesh_file, None))


# -- progress, cancellation and the artefact ----------------------------------


def test_ver25_the_field_stage_reports_progress_ending_at_one(
    mesh_file: Path, field_document: Path, tmp_path: Path
) -> None:
    """Stage 7 runs alone, monotonically, and finishes at 1.0 (FR-27)."""
    seen: list[float] = []
    stage = FieldStage(workspace=tmp_path / "work")
    artefact = stage.run(
        _inputs(mesh_file, field_document),
        progress=lambda fraction, message: seen.append(fraction),
    )
    assert seen == sorted(seen)
    assert seen[0] == 0.0
    assert seen[-1] == 1.0
    assert artefact.schema == stage.describe().artefact_schema
    assert artefact.hash
    # The archival copy is written in the canonical SI unit, so that reading it
    # back needs no header (section 5.3.2).
    assert sorted(path.name for path in (tmp_path / "work").iterdir()) == ["charge.npz"]


def test_ver25_a_cancelled_field_stage_writes_nothing(
    mesh_file: Path, field_document: Path, tmp_path: Path
) -> None:
    """Cancellation raises before the archive exists, not after (section 5.3.2)."""
    flag = CancelFlag()
    flag.cancel()
    with pytest.raises(Cancelled):
        FieldStage(workspace=tmp_path / "work").run(_inputs(mesh_file, field_document), cancel=flag)
    assert not (tmp_path / "work").exists()


def test_ver29_the_artefact_carries_the_conservation_it_was_gated_on(
    mesh_file: Path, field_document: Path, tmp_path: Path
) -> None:
    """The gated numbers reach the artefact summary rather than being recomputed.

    Recomputing them for the manifest would mean integrating over the mesh a
    second time, and two integrations are two chances to report a number the
    gate never saw.
    """
    stage = FieldStage(workspace=tmp_path / "work")
    artefact = stage.run(_inputs(mesh_file, field_document))
    recorded = artefact.summary["charge"]["conservation"]
    assert recorded["q_net_e"] == pytest.approx(-12.0)
    # Absolute: the legs are signed, and a field that lost half its charge would
    # satisfy a bare ``< tolerance`` by being negative enough.
    assert abs(recorded["producer"]["relative_error"]) < recorded["producer"]["tolerance"]
    assert abs(recorded["consumer"]["relative_error"]) < recorded["consumer"]["tolerance"]
    assert recorded["interpolation"] == "bilinear"


def test_ver25_the_artefact_key_is_the_field_contents_and_not_its_path(
    mesh_file: Path, field_document: Path, tmp_path: Path
) -> None:
    """The same field read from a second path keys the same artefact.

    ``key()`` also has to agree with ``run()``: they read the same grids by two
    code paths, one of which skips the mesh integrals, and a cache keyed on the
    cheap one that disagreed with the expensive one would return the wrong
    artefact for every hit.
    """
    stage = FieldStage(workspace=tmp_path / "work")
    inputs = _inputs(mesh_file, field_document)
    assert stage.key(inputs).hash == stage.run(inputs).hash

    moved = tmp_path / "renamed.yaml"
    moved.write_text(field_document.read_text(encoding="utf-8"), encoding="utf-8")
    assert stage.key(_inputs(mesh_file, moved)).hash == stage.key(inputs).hash

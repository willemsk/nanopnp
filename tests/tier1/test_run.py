"""VER-32 — the pipeline driver: one case file to one run directory (FR-27, IF-01).

Four claims, each of which fails quietly rather than loudly.

**The pipeline is a dependency order, not the section 5.2 numbering.** Stage 9
resolves the case and stages 6, 7 and 8 all consume it, so
:data:`~nanopnp.io.run.PIPELINE` cannot be sorted by stage number. Nothing in
the driver checks that the order it hard-codes actually satisfies each stage's
declared inputs; a stage added to the registry with a new input, or moved,
would raise a ``KeyError`` from deep inside a stage rather than here.

**The two sets the driver keys its behaviour on are hand-written.**
:data:`~nanopnp.io.run.PAYLOAD_FREE` claims to be exactly the stages with no
``key`` method and :data:`~nanopnp.io.run.WORKSPACE_STAGES` exactly those whose
constructor takes one. Both are enumerated deliberately — see their docstrings
— and both are therefore assertions about code elsewhere, checked here against
that code rather than against a second copy of the list.

**A stage's FR-25 deviations are read off its own artefact.** The driver calls
``deviations(inputs)`` after the artefact is recorded, so
:meth:`~nanopnp.mesh.ingest.MeshStage.deviations` answers from the ``materials``
parameter rather than by ingesting and quality-gating the mesh a second time.
That is only sound while the artefact's parameters carry what the ingested
object carries, so both routes are run and compared.

**``only`` must refuse, not recompute.** A hand-substituted artefact (FR-27) is
testable only if the driver aborts on a store miss; one that quietly recomputed
the upstream stage would read past the substituted file and report a number from
the wrong input.

No solve happens here. The end-to-end walk through stage 12, and QR-08's
reproduction into a fresh store, are Tier 2's (VER-35): a driver defect that
only a converged solve reveals is not a driver defect. Stabilisation is ``none``
(NUM-11).
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.charge.fields import FieldDocument, FormSpec, create_form
from nanopnp.charge.stage import FieldStage, ResolvedFields, smoothed_dielectric_deviations
from nanopnp.core.stages import _catalogue, create, describe
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import loads_case
from nanopnp.io.manifest import CASE_FILENAME, MANIFEST_FILENAME, MANIFEST_SCHEMA
from nanopnp.io.run import (
    PAYLOAD_FREE,
    PIPELINE,
    RUN_RECORD_FILENAME,
    RUN_SCHEMA,
    WORKSPACE_DIRNAME,
    WORKSPACE_STAGES,
    MissingUpstreamError,
    run_case,
)
from nanopnp.io.store import Store
from nanopnp.materials.fields import SolidFractionField
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, exclusion_deviations
from nanopnp.mesh.primitives import CylindricalPoreGeometry

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.mesh.adapter import MeshData

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0
"""The cheapest mesh that carries all four domains, as WP10's other modules use."""

CASE = """
schema: nanopnp/case/v1
name: run-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
boundary_conditions:
  bias_V: 0.02
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [current, transport_numbers, eof_rate]
"""


@pytest.fixture(scope="module")
def case_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the reference case and the mesh it names, once for the module."""
    work = tmp_path_factory.mktemp("run")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    path = work / "case.yaml"
    path.write_text(CASE.format(mesh_path=mesh_path), encoding="utf-8")
    return path


# -- the pipeline order --------------------------------------------------------


def test_ver32_the_pipeline_is_registered_and_in_dependency_order() -> None:
    """Every stage the driver walks exists, and its inputs are already produced.

    Both halves matter. A name that is not registered fails loudly on the first
    run; an order in which a stage precedes something it consumes fails inside
    :meth:`~nanopnp.io.artefact.StageInputs.require`, naming an artefact rather
    than the ordering that made it absent.
    """
    produced = {"case_path"}
    for name in PIPELINE:
        description = describe(name)  # raises if it is not registered
        missing = sorted(set(description.inputs) - produced)
        assert not missing, f"stage {name!r} consumes {missing}, which nothing before it produces"
        produced.add(name)
    assert set(PIPELINE) == {description.name for description in _catalogue_descriptions()}


def _catalogue_descriptions() -> tuple[object, ...]:
    """Return every registered stage description, for the coverage assertion above."""
    return tuple(entry.description for entry in _catalogue().values())


def test_ver32_payload_free_names_exactly_the_stages_with_no_key_method() -> None:
    """The set the driver branches on, checked against the stages themselves.

    ``PAYLOAD_FREE`` decides two things: that ``_probe`` may run the stage to
    learn its key, and that ``only`` resolves it rather than demanding it from
    the store. Both are sound only because running one writes no file. A stage
    that gained a payload and kept its place in the set would have ``only``
    recompute it past a substituted input.
    """
    keyless = {name for name in PIPELINE if not hasattr(create(name), "key")}
    assert keyless == set(PAYLOAD_FREE)


def test_ver32_workspace_stages_names_exactly_the_constructors_that_take_one() -> None:
    """Enumerated rather than discovered, and so asserted against the signatures.

    Discovering it by catching :class:`TypeError` from
    :func:`~nanopnp.core.stages.create` is what this set exists to avoid: a
    genuine ``TypeError`` from inside a constructor would be indistinguishable
    from an unwanted keyword, and the driver would silently rebuild the stage
    with no workspace and write its payload into the store root.
    """
    takes_one = set()
    for name in PIPELINE:
        module_name, _, attribute = _catalogue()[name].target.partition(":")
        factory = getattr(importlib.import_module(module_name), attribute)
        if "workspace" in inspect.signature(factory).parameters:
            takes_one.add(name)
    assert takes_one == set(WORKSPACE_STAGES)


# -- the FR-25 deviations a stage reads off its own artefact -------------------


def _two_triangles(materials: tuple[str, ...]) -> MeshData:
    """Return the smallest mesh carrying ``materials``: one triangle pair each."""
    import numpy as np

    from nanopnp.mesh.adapter import MeshData

    count = len(materials)
    vertices = np.array(
        [[r, float(level)] for level in range(count + 1) for r in (0.0, 1.0)], dtype=np.float64
    )
    triangles = []
    material = []
    for index in range(count):
        base = 2 * index
        triangles += [[base, base + 1, base + 3], [base, base + 3, base + 2]]
        material += [index] * 2
    return MeshData(
        vertices=vertices,
        triangles=np.array(triangles, dtype=np.int64),
        triangle_material=np.array(material, dtype=np.int64),
        materials=materials,
        edges=np.array([[2 * i, 2 * i + 2] for i in range(count)], dtype=np.int64),
        edge_group=np.zeros(count, dtype=np.int64),
        boundaries=("axis",),
    )


def _ingested(materials: tuple[str, ...]) -> IngestedMesh:
    """Return an :class:`IngestedMesh` over that mesh, gates already granted."""
    from nanopnp.mesh.quality import element_quality

    data = _two_triangles(materials)
    return IngestedMesh(
        data=data,
        quality=element_quality(data),
        source=Path(__file__),
        source_hash="0" * 64,
        applied={},
    )


@pytest.mark.parametrize(
    "materials",
    [("electrolyte", "membrane"), ("electrolyte", "membrane", "exclusion")],
    ids=["no-shell", "exclusion-shell"],
)
def test_ver32_the_mesh_stage_reads_the_exclusion_deviation_off_its_artefact(
    materials: tuple[str, ...],
) -> None:
    """The artefact route and the ingested route return the same sentence (FR-25).

    The driver calls ``deviations(inputs)`` with the stage's own artefact in
    hand precisely so that the ion-exclusion shell is reported without a second
    read and quality gate of the mesh file. That shortcut is sound only while
    the artefact's ``materials`` parameter carries what the ingested mesh
    carries, which is what is asserted here — in both directions, so that a
    route which returned ``()`` unconditionally would fail on the shell case.
    """
    ingested = _ingested(materials)
    artefact = MeshStage().artefact(ingested)
    inputs = StageInputs(case=loads_case(_MINIMAL), upstream={"mesh": artefact})

    assert MeshStage().deviations(inputs) == ingested.deviations()
    assert bool(ingested.deviations()) is ("exclusion" in materials)
    assert ingested.deviations() == exclusion_deviations(materials)


def test_ver32_the_field_stage_reads_the_dielectric_deviation_off_its_artefact() -> None:
    """Same claim for stage 7, where the alternative is re-reading the table.

    A supplied ``inputs.eps_r`` is a departure from PHY-20's per-domain
    constants that no case-file switch selects, so the manifest gets it only if
    the stage says so. Re-reading the field document to find that out costs tens
    of megabytes per run; the artefact already names it.
    """
    fields = ResolvedFields(
        charge=None, conservation=None, eps_r=_solid_fraction_field(), material_means=()
    )
    assert fields.deviations(), "the fixture must carry a deviation, or this tests nothing"

    artefact = FieldStage().artefact(fields, "0" * 64)
    inputs = StageInputs(case=loads_case(_MINIMAL), upstream={"charge": artefact})
    assert FieldStage().deviations(inputs) == fields.deviations()
    assert smoothed_dielectric_deviations(smoothed=False) == ()


def _solid_fraction_field() -> SolidFractionField:
    """Return the smallest valid dielectric field: uniform ``chi`` on a 2x2 grid.

    Borrowed verbatim from :mod:`tests.tier1.test_manifest`, so that the
    deviation under test is the one the stage actually produces rather than one
    this module wrote out by hand.
    """
    spec = FormSpec(
        name="uniform",
        parameters={"value": 1.0},
        origin_nm=(0.0, 0.0),
        spacing_nm=(1.0, 1.0),
        shape=(2, 2),
    )
    document = FieldDocument.model_validate(
        {
            "schema": "nanopnp/field/v1",
            "name": "chi",
            "quantity": "solid_fraction",
            "units": "1",
            "provenance": {"source": "analytic"},
            "form": spec.model_dump(),
        }
    )
    return SolidFractionField(document=document, grid=create_form(spec), source=Path(__file__))


# -- the walk itself -----------------------------------------------------------


def test_ver32_a_truncated_run_writes_its_directory_and_reports_monotone_progress(
    case_file: Path, tmp_path: Path
) -> None:
    """``upto`` stops the walk, and what it produced is on disk and consistent.

    Truncated at stage 6 so that this costs a mesh ingestion rather than a
    solve: the claim is about the driver's bookkeeping — the stage records, the
    progress contract, the three files of a run directory — and none of it is
    about the physics.
    """
    seen: list[tuple[float, str]] = []
    store = Store(tmp_path / "store")
    result = run_case(
        case_file,
        store=store,
        upto="mesh",
        workspace=tmp_path / "work",
        progress=lambda fraction, message: seen.append((fraction, message)),
    )

    assert [record.name for record in result.stages] == ["case", "mesh"]
    assert [record.number for record in result.stages] == [9, 6]
    assert all(not record.cached for record in result.stages), "a fresh store cannot hit"
    assert result.quantities == {}, "no stage 11 ran, so there is no number to report"
    assert result.files == ()

    fractions = [fraction for fraction, _ in seen]
    assert fractions == sorted(fractions), "progress must be monotone (FR-27)"
    assert fractions[0] >= 0.0 and fractions[-1] == pytest.approx(1.0)

    for filename in (MANIFEST_FILENAME, CASE_FILENAME, RUN_RECORD_FILENAME):
        assert (result.directory / filename).is_file(), filename
    written_case = (result.directory / CASE_FILENAME).read_text(encoding="utf-8")
    assert written_case == result.manifest.case_text

    record = result.record()
    assert record["schema"] == RUN_SCHEMA
    assert record["manifest"] == result.manifest.hash
    assert set(record["artefacts"]) == {"case", "mesh"}
    assert result.manifest.document()["schema"] == MANIFEST_SCHEMA


def test_ver32_a_run_writes_its_scratch_inside_the_store_it_was_given(
    case_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No workspace named means one under *this* store, not the process default.

    Each file-writing stage falls back to ``store_root()`` when it is built
    without a workspace, and that is ``$NANOPNP_STORE`` or the working
    directory — so a sweep worker or a test that named its own store would find
    the run's scratch mesh somewhere it never asked about while the artefact
    pointing at it lived in the store it did. Asserted by running from a
    directory that would catch the fallback: nothing may appear there.
    """
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.delenv("NANOPNP_STORE", raising=False)

    store = Store(tmp_path / "store")
    result = run_case(case_file, store=store, upto="mesh")

    assert list(elsewhere.iterdir()) == [], "a run leaked files outside the store it was given"
    scratch = sorted((store.root / WORKSPACE_DIRNAME).glob("run-*"))
    assert len(scratch) == 1, scratch
    assert (scratch[0] / "mesh" / "mesh.msh").is_file()

    mesh = result.artefacts["mesh"]
    written = Path(str(mesh.payload["mesh"]))
    assert store.root in written.parents


def test_ver32_a_second_run_through_the_same_store_is_served_from_it(
    case_file: Path, tmp_path: Path
) -> None:
    """The store is a cache, and the record says which stages used it (QR-08).

    ``cached`` is what QR-08's reproduction check reads: a run whose every stage
    was served did no physics, and a reproduction that could not tell would be
    asserting that a dictionary lookup is deterministic.
    """
    store = Store(tmp_path / "store")
    first = run_case(case_file, store=store, upto="mesh", workspace=tmp_path / "work")
    second = run_case(case_file, store=store, upto="mesh", workspace=tmp_path / "work")

    assert all(record.cached for record in second.stages)
    assert [record.hash for record in second.stages] == [record.hash for record in first.stages]
    assert second.directory == first.directory, "the same case writes the same run directory"


def test_ver32_only_refuses_an_upstream_the_store_does_not_hold(
    case_file: Path, tmp_path: Path
) -> None:
    """A missing substitution aborts naming it, rather than being recomputed.

    ``only`` exists so that a hand-substituted artefact (FR-27) can be shown to
    have been *read*. A driver that recomputed the upstream stage on a miss
    would read past the substituted file and report a number from the wrong
    input, which is the failure this refusal makes impossible.
    """
    with pytest.raises(MissingUpstreamError) as raised:
        run_case(
            case_file,
            store=Store(tmp_path / "store"),
            upto="materials",
            only=True,
            workspace=tmp_path / "work",
        )
    message = str(raised.value)
    assert "'mesh'" in message
    assert "nanopnp/mesh/v1" in message
    assert str(tmp_path / "store") in message


def test_ver32_upto_names_a_stage_this_case_does_not_walk(case_file: Path, tmp_path: Path) -> None:
    """Stage 7 is registered, and this case gives it nothing to read.

    Two different errors share one flag, and conflating them sends a reader to
    the wrong place: ``--upto charge`` on a case with no field is not a typo.
    """
    with pytest.raises(KeyError, match="nothing for it to read"):
        run_case(case_file, store=Store(tmp_path / "store"), upto="charge", write=False)
    with pytest.raises(KeyError, match="no stage 'sovle'"):
        run_case(case_file, store=Store(tmp_path / "store"), upto="sovle", write=False)


_MINIMAL = """
schema: nanopnp/case/v1
name: minimal
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns}
"""

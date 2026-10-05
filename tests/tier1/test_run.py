"""VER-32 — the pipeline driver: one case file to one run directory (FR-27, IF-01).

Three claims, each of which fails quietly rather than loudly.

**The pipeline is a dependency order, not the section 5.2 numbering.** Stage 9
resolves the case and stages 6, 7 and 8 all consume it, so
:func:`~nanopnp.core.stages.walk_order` cannot be sorted by stage number.
:func:`~nanopnp.core.stages.register` refuses a stage whose inputs are not
registered before it; this checks the order that results, so a stage that
reached the registry some other way would fail here rather than with a
``KeyError`` from deep inside a stage. The facts the walk reads off each
stage's description are checked against the stages by VER-64
(``test_stage_conformance.py``).

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

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.charge.fields import FieldDocument, FormSpec, create_form
from nanopnp.charge.stage import (
    FieldStage,
    ResolvedFields,
    gate_parameters,
    smoothed_dielectric_deviations,
)
from nanopnp.core import stages as stages_module
from nanopnp.core.hashing import file_hash
from nanopnp.core.stages import StageDescription, _catalogue, describe, register, walk_order
from nanopnp.io import run as run_module
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import ResolvedCase, loads_case, resolve
from nanopnp.io.manifest import CASE_FILENAME, MANIFEST_FILENAME, MANIFEST_SCHEMA
from nanopnp.io.run import (
    RUN_RECORD_FILENAME,
    RUN_SCHEMA,
    WORKSPACE_DIRNAME,
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
schema: nanopnp/case/v2
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
    for name in walk_order():
        description = describe(name)  # raises if it is not registered
        missing = sorted(set(description.inputs) - produced)
        assert not missing, f"stage {name!r} consumes {missing}, which nothing before it produces"
        produced.add(name)
    assert set(walk_order()) == {description.name for description in _catalogue_descriptions()}


def _catalogue_descriptions() -> tuple[object, ...]:
    """Return every registered stage description, for the coverage assertion above."""
    return tuple(entry.description for entry in _catalogue().values())


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

    case = loads_case(_MINIMAL)
    artefact = FieldStage().artefact(fields, "0" * 64, resolved=resolve(case))
    inputs = StageInputs(case=case, upstream={"charge": artefact})
    assert FieldStage().deviations(inputs) == fields.deviations()
    assert smoothed_dielectric_deviations(smoothed=False) == ()


def test_ver29_the_field_key_carries_the_solid_set_only_with_a_dielectric_field() -> None:
    """The per-material means of ``chi`` are classified by the solid names, so they key stage 7.

    By name and not by value: a permittivity classifies nothing. Without a
    dielectric field no gate reads the set, and keying on it would re-run stage 7
    for a change it cannot see.
    """
    dielectric = ResolvedFields(
        charge=None, conservation=None, eps_r=_solid_fraction_field(), material_means=()
    )
    bare = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
    base = resolve(loads_case(_MINIMAL))
    protein = resolve(
        loads_case(
            _MINIMAL.replace(
                "physics: {model: pnp-ns}",
                "physics: {model: pnp-ns, solid_permittivities: {protein: 10.0}}",
            )
        )
    )
    softer = resolve(
        loads_case(
            _MINIMAL.replace(
                "physics: {model: pnp-ns}",
                "physics: {model: pnp-ns, solid_permittivities: {protein: 4.0}}",
            )
        )
    )

    def key(resolved: ResolvedCase, fields: ResolvedFields) -> str:
        return FieldStage().artefact(fields, "0" * 64, resolved=resolved).hash

    assert key(protein, dielectric) != key(base, dielectric)
    assert key(protein, dielectric) == key(softer, dielectric)
    assert key(protein, bare) == key(base, bare)
    assert gate_parameters(protein, dielectric)["solids"] == ["protein"]


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


def test_qr08_a_truncated_walk_does_not_overwrite_the_record_of_the_full_run(
    case_file: Path, tmp_path: Path
) -> None:
    """``--upto`` and the shell's **Build geometry** write beside a full run, never over it.

    The run directory is named by the case; a truncated walk of the same case used to land
    in the same directory and replace ``run.json`` and the manifest, so a full run could no
    longer be reproduced from its directory (CODE_REVIEW_003 CR-2, QR-08).
    """
    store = Store(tmp_path / "store")
    full = run_case(case_file, store=store, workspace=tmp_path / "work")
    assert full.quantities, "a full run records its quantities"
    recorded = (full.directory / RUN_RECORD_FILENAME).read_bytes()
    manifest = (full.directory / MANIFEST_FILENAME).read_bytes()

    truncated = run_case(case_file, store=store, upto="mesh", workspace=tmp_path / "work")
    assert truncated.directory != full.directory
    assert (full.directory / RUN_RECORD_FILENAME).read_bytes() == recorded
    assert (full.directory / MANIFEST_FILENAME).read_bytes() == manifest
    assert (truncated.directory / RUN_RECORD_FILENAME).is_file()


def test_qr08_a_complete_walk_is_complete_when_its_case_drops_the_last_registered_stage(
    case_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A walk is complete at the last stage *this case* walks, not the last registered.

    A stage registered after ``report`` that needs ``structure:`` is dropped from this
    case, which has none. The walk still ends where the case's walk ends, so its record is
    the case's own run record rather than a truncated one written beside it (QR-08).
    """
    monkeypatch.setattr(stages_module, "_REGISTRY", dict(stages_module._REGISTRY))
    register(
        StageDescription(
            name="external",
            number=13,
            title="External",
            inputs=("case", "solve"),
            outputs=(),
            artefact_schema="external/v1",
            takes_workspace=False,
            takes_store=False,
            key_is_artefact=False,
            weight=0.1,
            needs_section="structure",
        ),
        "nanopnp.external:ExternalStage",
    )
    result = run_case(
        case_file, store=Store(tmp_path / "store"), workspace=tmp_path / "work", write=False
    )
    assert result.stages[-1].name == "report"
    assert not result.directory.name.startswith("run-probe-upto-"), result.directory.name


@pytest.mark.parametrize("linesep", ["\n", "\r\n"])
def test_qr08_the_run_directory_case_hashes_to_the_recorded_case_input(
    case_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, linesep: str
) -> None:
    """The copy beside the manifest is what ``reproduce`` checks the recorded hash against.

    The recorded hash is of the source file, written here as a text-mode write
    writes it on each platform; the CRLF case stands in for Windows, where an LF
    copy made every archived run refuse to reproduce as a moved input.
    """
    monkeypatch.setattr(os, "linesep", linesep)
    source = tmp_path / "case.yaml"
    source.write_bytes(case_file.read_text(encoding="utf-8").replace("\n", linesep).encode("utf-8"))

    result = run_case(source, store=Store(tmp_path / "store"), upto="mesh")

    recorded = result.manifest.document()["inputs"]["files"]["case"]["sha256"]  # type: ignore[index]
    assert file_hash(result.directory / CASE_FILENAME) == recorded == file_hash(source)


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

    # The scratch is removed when the walk ends, so where it was made is
    # recorded as it is made.
    made: list[Path] = []
    original = run_module._scratch

    def watched(store: Store) -> Path:
        made.append(original(store))
        return made[-1]

    monkeypatch.setattr(run_module, "_scratch", watched)

    store = Store(tmp_path / "store")
    result = run_case(case_file, store=store, upto="mesh")

    assert list(elsewhere.iterdir()) == [], "a run leaked files outside the store it was given"
    assert len(made) == 1, made
    assert made[0].parent == store.root / WORKSPACE_DIRNAME

    mesh = result.artefacts["mesh"]
    written = Path(str(mesh.payload["mesh"]))
    assert store.root in written.parents
    assert written.is_file()


def test_ver32_a_run_removes_its_scratch_once_the_store_holds_the_payloads(
    case_file: Path, tmp_path: Path
) -> None:
    """``Store.put`` copies every payload, so the workspace would hold each one twice.

    Across an envelope sweep that is one duplicate mesh, field export and
    solution per member on the store's own filesystem, never reclaimed. A
    workspace the caller named is the caller's, and is left alone.
    """
    store = Store(tmp_path / "store")
    result = run_case(case_file, store=store, upto="mesh")
    assert list((store.root / WORKSPACE_DIRNAME).glob("run-*")) == []
    assert Path(str(result.artefacts["mesh"].payload["mesh"])).is_file()

    named = tmp_path / "work"
    run_case(case_file, store=Store(tmp_path / "other"), upto="mesh", workspace=named)
    assert (named / "mesh" / "mesh.msh").is_file()


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
schema: nanopnp/case/v2
name: minimal
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns}
"""


# -- the protonation stage in the walk (WP27 D2, D3, D16) -----------------------

_PQR_LINES = """\
ATOM      1  N   GLU A  18      -2.661   5.770 -35.426 -0.3000 1.8500
ATOM      2  CA  GLU A  18      -1.598   4.789 -35.571  0.3000 2.2750
ATOM      3  C   GLU A  18      -2.071   3.395 -35.184  0.5100 2.0000
ATOM      4  O   GLU A  18      -1.657   2.404 -35.775 -1.5100 1.7000
"""
"""A four-atom PQR whose charges sum to -1 e: enough for the walk to read and gate."""


def _pqr_case(case_file: Path, tmp_path: Path) -> Path:
    """Write the module's case with ``inputs.pqr`` beside its mesh."""
    pqr = tmp_path / "supplied.pqr"
    pqr.write_text(_PQR_LINES, encoding="utf-8")
    text = case_file.read_text(encoding="utf-8").replace(
        "inputs:\n", f"inputs:\n  pqr: {{path: {pqr}, format: pqr}}\n", 1
    )
    path = tmp_path / "pqr.case.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_ver57_protonation_runs_before_the_deposit_it_feeds(
    case_file: Path, tmp_path: Path
) -> None:
    """WP28 D8, retiring WP27 D3: both halves of stage 7 run before the materials.

    A case that protonates, under a model declaring ``fixed_charge``, deposits.
    The stage still sits after ``mesh`` and before ``charge`` (WP27 D2); a walk
    may still end there; and a case with nothing to protonate still refuses it
    naming why.
    """
    from nanopnp.io.run import UnknownStageError, selected_stages

    supplied = resolve(loads_case(_pqr_case(case_file, tmp_path).read_text(encoding="utf-8")))
    assert supplied.deposits_charge
    assert selected_stages(supplied, "materials") == (
        "case",
        "mesh",
        "protonation",
        "charge",
        "materials",
    )
    assert selected_stages(supplied, "protonation") == ("case", "mesh", "protonation")
    bare = resolve(loads_case(case_file.read_text(encoding="utf-8")))
    assert "protonation" not in selected_stages(bare, None)
    assert "charge" not in selected_stages(bare, None)
    with pytest.raises(UnknownStageError, match="nothing for it to protonate"):
        selected_stages(bare, "protonation")


def test_ver57_a_walk_to_protonation_records_it_in_the_charge_group(
    case_file: Path, tmp_path: Path
) -> None:
    """``inputs.pqr`` walked to the stage: the Charge group carries ``Q_net`` and the file.

    A walk to ``mesh`` records the stage not run with the reason, which is a
    different fact from a stage that ran (WP27 D16); so does stage 7, which a
    walk stopped short of it did not reach (WP28 D8).
    """
    case = _pqr_case(case_file, tmp_path)
    store = Store(tmp_path / "store")
    result = run_case(case, store=store, upto="protonation", write=False)
    group = result.manifest.charge
    assert group["status"] == "not run"
    assert "stopped before stage 7" in str(group["reason"])
    record = group["protonation"]
    assert isinstance(record, dict)
    assert record["q_net_e"] == [-1]
    assert record["source"] == "inputs.pqr"
    assert record["pqr_sha256"] == file_hash(tmp_path / "supplied.pqr")
    assert "pqr" in result.manifest.inputs["files"]  # type: ignore[operator]
    truncated = run_case(case, store=store, upto="mesh", write=False)
    skipped = truncated.manifest.charge["protonation"]
    assert isinstance(skipped, dict)
    assert skipped["status"] == "not run"
    assert "stopped before stage 7" in str(skipped["reason"])

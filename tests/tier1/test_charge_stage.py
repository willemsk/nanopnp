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


def case_text(mesh_path: Path, field_path: Path | None, *, order: str = "P2") -> str:
    """Return a case naming ``mesh_path``, and ``field_path`` if there is one, at ``order``."""
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
numerics: {{continuation: none, elements: {{phi: {order}, c: {order}}}}}
"""


def _inputs(mesh_path: Path, field_path: Path | None, *, order: str = "P2") -> StageInputs:
    """Return the stage inputs for a case naming these two files."""
    return StageInputs(case=loads_case(case_text(mesh_path, field_path, order=order)))


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


def test_ver29_the_artefact_key_moves_with_the_order_its_gates_integrate_at(
    mesh_file: Path, field_document: Path, tmp_path: Path
) -> None:
    """One field on one mesh at two element orders is two stage-7 artefacts.

    The summary records the conservation integrals, and they are taken at the
    solve's quadrature. Keyed on the field and the mesh alone, the second order
    would be served the first order's artefact, and its manifest would record a
    conservation measured at a quadrature it never used.
    """
    stage = FieldStage(workspace=tmp_path / "work")
    second = stage.run(_inputs(mesh_file, field_document))
    third = stage.key(_inputs(mesh_file, field_document, order="P3"))
    assert third.hash != second.hash
    assert third.hash == stage.run(_inputs(mesh_file, field_document, order="P3")).hash


def test_val03_case_identity_carries_the_supplied_field_contents(
    mesh_file: Path, field_document: Path, tmp_path: Path
) -> None:
    """Two cases differing only in their charge table are two golden identities.

    The solve provenance records only that a charge field was supplied, so the
    identity takes the field's contents from the stage-7 key: a golden of one
    protonation state must not be accepted for another. The same table read from
    another path is the same case, and a case supplying no field keeps the
    identity it had, which is what every published ``case_hash`` rests on.
    """
    from nanopnp.core.hashing import content_hash
    from nanopnp.io.case import resolve
    from nanopnp.validation.comsol import (
        CASE_IDENTITY_SCHEMA,
        DISCRETISATION_KEYS,
        MODEL_OPTION_DISCRETISATION_KEYS,
        case_identity,
    )

    def identity(field: Path | None) -> str:
        return case_identity(resolve(loads_case(case_text(mesh_file, field))))

    halved = tmp_path / "halved.yaml"
    halved.write_text(
        FIELD_DOCUMENT.replace("charge_e: -12.0", "charge_e: -6.0").replace(
            "q_net_e: -12.0", "q_net_e: -6.0"
        ),
        encoding="utf-8",
    )
    moved = tmp_path / "moved.yaml"
    moved.write_text(field_document.read_text(encoding="utf-8"), encoding="utf-8")
    assert identity(halved) != identity(field_document)
    assert identity(moved) == identity(field_document)

    # With no field, the record is the solve provenance less the discretisation,
    # exactly as before the field contents joined it.
    provenance = resolve(loads_case(case_text(mesh_file, None))).solve_provenance
    record = {key: value for key, value in provenance.items() if key not in DISCRETISATION_KEYS}
    record["model_options"] = {
        key: value
        for key, value in sorted(provenance["model_options"].items())
        if key not in MODEL_OPTION_DISCRETISATION_KEYS
    }
    assert identity(None) == content_hash(CASE_IDENTITY_SCHEMA, record)


# -- the producer path (WP28) ----------------------------------------------------

PRODUCER_ATOMS_A: tuple[tuple[str, float, float, float, float, float], ...] = (
    # name, x, y, z (Å), charge (e), radius (Å): six atoms inside the membrane of
    # the pore below (r in 2.0-10 nm, |z| < 3 nm), summing to -1 e.
    ("N", 30.0, 5.0, -10.0, -0.5, 1.85),
    ("CA", -35.0, 20.0, 5.0, -0.5, 2.275),
    ("C", 0.0, 45.0, 12.0, 0.25, 2.0),
    ("O", 40.0, -30.0, -15.0, -0.25, 1.7),
    ("CB", 25.0, 25.0, 0.0, 0.5, 2.175),
    ("CG", -50.0, -10.0, 18.0, -0.5, 2.175),
)
"""The supplied PQR's atoms: off-axis, of CHARMM-like radii, all in a solid."""


def _pqr_text() -> str:
    """Return the producer PQR in PDB2PQR's fixed columns."""
    lines = []
    for serial, (name, x, y, z, charge, radius) in enumerate(PRODUCER_ATOMS_A, start=1):
        lines.append(
            f"ATOM  {serial:5d} {name:<4} GLU A  18    {x:8.3f}{y:8.3f}{z:8.3f}"
            f" {charge:7.4f} {radius:6.4f}"
        )
    return "\n".join(lines) + "\n"


PRODUCER_CASE = """
schema: nanopnp/case/v2
name: producer-probe
inputs:
  mesh: {{path: {mesh}, format: vol, groups: {{default: interface}}}}
  pqr: {{path: {pqr}, format: pqr}}
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
boundary_conditions: {{bias_V: 0.02, ground: cis}}
physics: {{model: pnp, flow: false, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: none, elements: {{phi: {order}, c: {order}}}}}
outputs: [current, fields]
"""


@pytest.fixture(scope="module")
def producer_files(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Write the cheapest four-domain pore mesh and the producer PQR, once."""
    from nanopnp.mesh.primitives import CylindricalPoreGeometry

    work = tmp_path_factory.mktemp("producer")
    mesh = work / "pore.vol"
    CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    # 0.5 nm elements: at 1 nm the deployed field's per-plane error under the
    # 0.5 nm weight is 3.2e-3, which the gate refuses as it should; it falls to
    # 2.3e-4 here (`.knowledge/04` section 3.3).
    ).generate(maxh_nm=0.5, wall_h_nm=0.5).ngmesh.Save(str(mesh))
    pqr = work / "atoms.pqr"
    pqr.write_text(_pqr_text(), encoding="utf-8")
    return mesh, pqr


def _producer_case(files: tuple[Path, Path], directory: Path, *, order: str = "P2") -> Path:
    """Write the producer case at ``order`` and return its path."""
    mesh, pqr = files
    path = directory / f"producer-{order}.case.yaml"
    path.write_text(PRODUCER_CASE.format(mesh=mesh, pqr=pqr, order=order), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def produced(producer_files: tuple[Path, Path], tmp_path_factory: pytest.TempPathFactory):
    """Walk the producer case through stage 7 once, into a store kept for the module."""
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    work = tmp_path_factory.mktemp("produced")
    store = Store(work / "store")
    case = _producer_case(producer_files, work)
    return case, store, run_case(case, store=store, upto="charge", write=False)


def test_ver01_the_producer_stage_deposits_keys_and_records_its_report(produced) -> None:
    """A ``pqr`` case walks both halves of stage 7; the artefact names both inputs (D7, D8)."""
    from nanopnp.core.constants import ELEMENTARY_CHARGE
    from nanopnp.io.artefact import CHARGE_GRID_SCHEMA

    case, store, result = produced
    assert [record.name for record in result.stages][-2:] == ["protonation", "charge"]
    stage7 = result.artefacts["charge"]
    assert set(stage7.inputs) == {"mesh", "protonation", "charge_grid"}
    assert stage7.inputs["protonation"] == result.artefacts["protonation"].hash
    fields = stage7.parameters["fields"]
    gates = stage7.parameters["gates"]
    assert fields["charge"] == {  # type: ignore[index]
        "source": "deposited",
        "order": 2,
        "kernel": "azimuthal-mean-3d-gaussian/v1",
    }
    assert gates["planes"] == 12  # type: ignore[index]
    assert gates["plane_smoothing_nm"] == 0.5  # type: ignore[index]
    assert set(stage7.payload) == {"charge", "charge_document", "deposit"}
    lattice = store.get(CHARGE_GRID_SCHEMA, stage7.inputs["charge_grid"])
    assert lattice is not None
    assert lattice.inputs == {"protonation": stage7.inputs["protonation"]}

    record = stage7.summary["charge"]
    conservation = record["conservation"]  # type: ignore[index]
    assert record["q_net_e"] == pytest.approx(-1.0, abs=1e-12)  # type: ignore[index]
    assert abs(conservation["producer"]["relative_error"]) < 1e-12  # type: ignore[index]
    assert abs(conservation["consumer"]["relative_error"]) < 1e-12  # type: ignore[index]
    plane = conservation["per_plane"]  # type: ignore[index]
    assert plane["grid_worst_relative_error"] < 1e-12
    assert plane["mesh_worst_relative_error"] < 1e-3
    assert record["solid_share"]["solid_share"] == 1.0  # type: ignore[index]
    assert record["material_charge_e"]["membrane"] == pytest.approx(-1.0)  # type: ignore[index]
    # The manifest's Charge group is the stage's record, protonation beside it.
    group = result.manifest.charge
    assert group["charge"]["conservation"] == conservation  # type: ignore[index]
    assert group["protonation"]["source"] == "inputs.pqr"  # type: ignore[index]
    # And the key taken before the run is the artefact the run produced.
    stage = FieldStage()
    upstream = {name: result.artefacts[name] for name in ("mesh", "protonation")}
    from nanopnp.io.case import load_case

    key = stage.key(StageInputs(case=load_case(case), upstream=upstream))
    assert key.hash == stage7.hash
    assert record["lattice"]["q_net_e"] * ELEMENTARY_CHARGE == pytest.approx(  # type: ignore[index]
        -ELEMENTARY_CHARGE
    )


def test_ver01_a_new_element_order_redeposits_without_resumming(
    produced, producer_files: tuple[Path, Path], tmp_path: Path
) -> None:
    """The lattice is keyed without the mesh's discretisation: P3 re-deposits it from the store."""
    from nanopnp.io.run import run_case

    _, store, first = produced
    case = _producer_case(producer_files, tmp_path, order="P3")
    again = run_case(case, store=store, upto="charge", write=False)
    stage7 = again.artefacts["charge"]
    assert stage7.inputs["charge_grid"] == first.artefacts["charge"].inputs["charge_grid"]
    assert stage7.hash != first.artefacts["charge"].hash
    assert stage7.summary["charge"]["lattice"]["cached"] is True  # type: ignore[index]
    assert stage7.summary["charge"]["order"] == 3  # type: ignore[index]


def test_ver29_the_export_reads_back_through_inputs_charge_to_the_same_digest(
    produced, tmp_path: Path
) -> None:
    """``stage charge --export X.yaml`` writes the document and its ``.npz`` (D11, IF-05)."""
    from nanopnp.charge.fields import load_field
    from nanopnp.charge.stage import export_charge
    from nanopnp.density.grid import read_grid, writable_formats

    _, _, result = produced
    stage7 = result.artefacts["charge"]
    written = export_charge(stage7, tmp_path / "exported.yaml")
    assert [path.name for path in written] == ["exported.npz", "exported.yaml"]
    field = load_field(tmp_path / "exported.yaml")
    stored = read_grid(stage7.payload["charge"], format="npz")
    assert field.grid.digest() == stored.digest()
    assert field.document.q_net_e == pytest.approx(-1.0, abs=1e-12)
    assert field.document.axis_cutoff_nm == 0.01
    assert field.planar_integral_C() / 1.602176634e-19 == pytest.approx(-1.0, abs=1e-12)
    if "dx" in writable_formats():
        (dx,) = export_charge(stage7, tmp_path / "exported.dx")
        assert read_grid(dx).shape == stored.shape


def test_ver29_a_producer_case_handed_no_stage_7_artefact_is_refused_naming_it(
    produced,
) -> None:
    """D9: the solve keys and reads a deposited charge only from stage 7's artefact."""
    from nanopnp.io.case import load_case
    from nanopnp.solve.stage import SolveStage

    case, _, result = produced
    upstream = {name: result.artefacts[name] for name in ("mesh",)}
    with pytest.raises(KeyError, match="stage 7 \\('charge'\\)"):
        SolveStage().key(StageInputs(case=load_case(case), upstream=upstream))


class _CancelOnCall:
    """A token that turns true on its ``at``-th question, counting from 1."""

    def __init__(self, at: int) -> None:
        self.at = at
        self.asked = 0

    def cancelled(self) -> bool:
        self.asked += 1
        return self.asked >= self.at


@pytest.mark.parametrize(
    ("at", "where"),
    [
        (1, "reading the fields"),
        (2, "summing the kernel of frame 0"),
        (3, "the solid-share gate"),
        (4, "locating the lattice"),
        (5, "the projection onto the mesh"),
        (6, "the conservation gates"),
        (7, "writing the deposit"),
    ],
)
def test_ver25_the_producer_stage_cancels_between_frames_and_before_each_gate(
    produced, tmp_path: Path, at: int, where: str
) -> None:
    """D12: between frames, before the projection and before each gate; nothing written."""
    from nanopnp.io.case import load_case

    case, _, result = produced
    upstream = {name: result.artefacts[name] for name in ("mesh", "protonation")}
    work = tmp_path / "work"
    with pytest.raises(Cancelled, match=re.escape(where)):
        FieldStage(workspace=work).run(
            StageInputs(case=load_case(case), upstream=upstream), cancel=_CancelOnCall(at)
        )
    assert not (work / "deposit.npz").exists()


def test_ver29_a_charged_walk_solves_and_exports_the_deposited_charge(
    producer_files: tuple[Path, Path], tmp_path: Path
) -> None:
    """D9 end to end: the solve, the restore and the ``rho_fixed`` export read the deposit."""
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    case = _producer_case(producer_files, tmp_path)
    result = run_case(case, store=Store(tmp_path / "store"), workspace=tmp_path / "work")
    assert [record.name for record in result.stages][-5:] == [
        "charge",
        "materials",
        "solve",
        "qoi",
        "report",
    ]
    assert result.artefacts["solve"].inputs["charge"] == result.artefacts["charge"].hash
    fields = result.artefacts["solve"].summary["fields"]
    assert fields["charge"]["source"] == "deposited"  # type: ignore[index]
    attributes = result.artefacts["report"].summary["files"]["attributes"]  # type: ignore[index]
    assert any("rho_fixed_C_m3" in names for names in attributes.values())
    assert result.quantities["currents_A"]

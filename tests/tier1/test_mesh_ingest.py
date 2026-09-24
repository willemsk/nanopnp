"""VER-27: the ingestion gate — the one place a mis-named boundary can be caught.

Every other test in this repository is written against a mesh this codebase
built, whose group names are correct by construction. Phase 1 solves on a mesh it
did not build (section 8.1), and there the names are whatever the file says.
Under the ``r``-weighted forms of section 6.2 the natural condition is the free
one (NUM-06), so a pore wall the run selects on and the mesh does not supply
assembles cleanly, converges, and reports a current that leaked through a no-flux
boundary that was never imposed. There is no residual for it. That is the failure
these tests are about, and every one of them is a way it could reach a solve.

The mesh below is deliberately named the way an exported one is — ``Wall``,
``PoreFluid``, ``Bilayer`` — so that "the mapping did nothing" and "the mapping
did the right thing" cannot look alike.
"""

from pathlib import Path

import numpy as np
import pytest

from nanopnp.core.stages import CancelFlag, Cancelled, create, describe
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import CaseDocument, loads_case, resolve
from nanopnp.mesh.adapter import MeshData, read, write_msh41
from nanopnp.mesh.ingest import (
    BOUNDARY_VOCABULARY,
    MATERIAL_VOCABULARY,
    MeshStage,
    MeshVocabularyError,
    apply_groups,
    ingest,
    required_names,
)
from nanopnp.mesh.quality import MeshQualityError

FILE_GROUPS = (
    "{PoreFluid: electrolyte, Membrane: membrane, "
    "Axis: axis, Wall: wall, Bilayer: membrane, Top: cis, Bottom: trans}"
)
"""The mapping the reference case supplies: every group of :func:`exported_mesh`."""


def exported_mesh(
    *,
    materials: tuple[str, ...] = ("PoreFluid", "Membrane"),
    boundaries: tuple[str, ...] = ("Axis", "Wall", "Bilayer", "Top", "Bottom"),
    slivered: bool = False,
) -> MeshData:
    """Return a two-domain mesh in an exporter's own names, not the vocabulary.

    A three-by-three grid of vertices in ``r >= 0``: four cells split into eight
    triangles, the lower half one domain and the upper half the other, with the
    four sides and the internal seam named separately. Small enough to read, and
    it carries the two things a mapping has to get right — two namespaces that
    share the name ``Bilayer``, and a many-to-one merge.
    """
    vertices = np.array([[i / 2.0, j / 2.0] for j in range(3) for i in range(3)], dtype=float)
    if slivered:
        # Collapse the middle row onto the bottom one: every element of the lower
        # half becomes a sliver, and none of them is inverted.
        vertices[3:6, 1] = 0.002
    triangles = np.array(
        [
            row
            for j in range(2)
            for i in range(2)
            for row in (
                [3 * j + i, 3 * j + i + 1, 3 * j + i + 4],
                [3 * j + i, 3 * j + i + 4, 3 * j + i + 3],
            )
        ]
    )
    return MeshData(
        vertices=vertices,
        triangles=triangles,
        triangle_material=np.array([0, 0, 0, 0, 1, 1, 1, 1]),
        materials=materials,
        edges=np.array([[0, 3], [3, 6], [2, 5], [5, 8], [3, 4], [4, 5], [0, 1], [6, 7]]),
        edge_group=np.array([0, 0, 1, 1, 2, 2, 3, 4]),
        boundaries=boundaries,
    )


def case_text(
    mesh_path: Path,
    *,
    groups: str = FILE_GROUPS,
    physics: str = "{model: pnp-ns, solid_permittivities: {membrane: 3.2}}",
    numerics: str = "{continuation: none}",
) -> str:
    """Return a case naming ``mesh_path`` with ``groups`` as its mapping."""
    return f"""
schema: nanopnp/case/v2
name: ingest-probe
inputs:
  mesh: {{path: {mesh_path}, format: gmsh, groups: {groups}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1, ground: cis}}
physics: {physics}
numerics: {numerics}
"""


@pytest.fixture
def mesh_file(tmp_path: Path) -> Path:
    """Write :func:`exported_mesh` to an MSH 4.1 file and return its path."""
    return write_msh41(exported_mesh(), tmp_path / "exported.msh")


def resolved_case(mesh_path: Path, **kwargs: str) -> tuple[CaseDocument, object]:
    """Return the document and its resolution for a case naming ``mesh_path``."""
    document = loads_case(case_text(mesh_path, **kwargs))
    return document, resolve(document)


# -- what the run selects on, derived rather than listed -----------------------


def test_ver27_the_required_names_come_from_the_case_and_not_from_a_list(
    mesh_file: Path,
) -> None:
    """Both electrodes, both fluid alternatives, the no-slip pair and the axis.

    The list is derived because a constant one is wrong in both directions: it
    would demand ``cis`` and ``trans`` of a cylinder that has neither, and would
    say nothing about a case that widened ``numerics.wall_distance.sources`` to a
    name no group supplies.
    """
    _, resolved = resolved_case(mesh_file)
    required = required_names(resolved)

    purposes = " | ".join(r.purpose for r in (*required.materials, *required.boundaries))
    assert "PHY-03" in purposes
    # The bias is applied as BoundaryCF({ground: 0, driven: V}), so each
    # electrode is a requirement on its own and not merely an alternative.
    grounded = [r for r in required.boundaries if r.options == ("cis",)]
    driven = [r for r in required.boundaries if r.options == ("trans",)]
    assert len(grounded) == 1 and "grounded" in grounded[0].purpose
    assert len(driven) == 1 and "driven" in driven[0].purpose
    # Disjunctive: no-slip asks for the wall or the bilayer, not for both.
    no_slip = next(r for r in required.boundaries if "no-slip" in r.purpose)
    assert no_slip.options == ("wall", "membrane")
    assert no_slip.satisfied_by(frozenset({"wall"}))
    assert not no_slip.satisfied_by(frozenset({"axis", "cis"}))
    assert "axis" in required.names and "electrolyte" in required.names


def test_ver27_a_flow_free_model_does_not_require_a_no_slip_boundary(mesh_file: Path) -> None:
    """``physics.model: pnp`` carries no momentum, so it selects on no wall.

    Derivation, not a list: the same mesh under the same mapping is asked for
    fewer names because this run poses fewer conditions. It is still asked for
    ``wall`` by ``numerics.wall_distance.sources``, which is a case field and not
    a consequence of the momentum equation.
    """
    _, resolved = resolved_case(
        mesh_file,
        physics="{model: pnp, flow: false, solid_permittivities: {membrane: 3.2}}",
    )
    purposes = [r.purpose for r in required_names(resolved).boundaries]
    assert not any("no-slip" in purpose for purpose in purposes)
    assert not any("u_r = 0" in purpose for purpose in purposes)
    assert any("PHY-02" in purpose for purpose in purposes)


def test_ver27_the_distance_sources_are_required_even_with_every_wall_factor_off(
    mesh_file: Path,
) -> None:
    """``numerics.wall_distance.sources`` is a case field, not a correction switch.

    An ablation with every wall correction disabled would otherwise pass a gate
    the validated configuration fails, which is the one comparison an ablation
    exists to make.
    """
    _, resolved = resolved_case(mesh_file)
    sources = [r for r in required_names(resolved).boundaries if "PHY-02" in r.purpose]
    assert len(sources) == 1
    assert sources[0].options == ("wall",)


def test_ver27_a_selection_pattern_that_is_not_a_flat_alternation_is_refused(
    mesh_file: Path,
) -> None:
    """A requirement derived from a mis-parsed pattern is a gate that cannot fail."""
    document = loads_case(
        case_text(mesh_file, numerics="{continuation: none, wall_distance: {sources: 'w.*'}}")
    )
    with pytest.raises(MeshVocabularyError, match="flat alternation"):
        required_names(resolve(document))


# -- the mapping ---------------------------------------------------------------


def test_ver27_the_mapping_renames_both_namespaces_and_records_what_it_did() -> None:
    """``Wall`` becomes ``wall`` in the boundaries and ``Membrane`` a domain."""
    mapped, applied = apply_groups(
        exported_mesh(),
        {
            "Axis": "axis",
            "Wall": "wall",
            "Bilayer": "membrane",
            "Top": "cis",
            "Bottom": "trans",
            "PoreFluid": "electrolyte",
            "Membrane": "membrane",
        },
    )
    assert set(mapped.materials) == {"electrolyte", "membrane"}
    assert set(mapped.boundaries) == {"axis", "wall", "membrane", "cis", "trans"}
    assert applied["Wall"] == "wall"
    # The flat map crosses the namespaces on purpose: one key, both tables.
    assert applied["Bilayer"] == "membrane" and applied["Membrane"] == "membrane"


def test_ver27_many_to_one_merges_the_groups_it_names() -> None:
    """A CAD export splitting one wall into several curves is one ``wall`` here."""
    mesh = exported_mesh(boundaries=("Axis", "WallLower", "WallUpper", "Top", "Bottom"))
    mapped, _ = apply_groups(
        mesh,
        {
            "Axis": "axis",
            "WallLower": "wall",
            "WallUpper": "wall",
            "Top": "cis",
            "Bottom": "trans",
            "PoreFluid": "electrolyte",
            "Membrane": "membrane",
        },
    )
    assert mapped.boundaries.count("wall") == 1
    assert (
        mapped.edges_of("wall").shape[0]
        == mesh.edges_of("WallLower").shape[0] + mesh.edges_of("WallUpper").shape[0]
    )


def test_ver27_a_group_already_in_the_vocabulary_claims_itself() -> None:
    """A mesh this codebase generated ingests with an empty mapping.

    Section 5.3.1 says every group must be claimed; a group whose own name is a
    vocabulary name is claimed by that fact. The failure the gate exists for is a
    name the solver does *not* speak slipping through unnoticed, and a name it
    does speak is not one of those.
    """
    mesh = exported_mesh(
        materials=("electrolyte", "membrane"),
        boundaries=("axis", "wall", "membrane", "cis", "trans"),
    )
    mapped, applied = apply_groups(mesh, {})
    assert mapped.boundaries == mesh.boundaries
    assert applied["wall"] == "wall"


def test_ver27_an_unclaimed_group_aborts_and_says_why_a_free_boundary_is_silent() -> None:
    """The abort names the group, the vocabulary and NUM-06."""
    with pytest.raises(MeshVocabularyError) as raised:
        apply_groups(exported_mesh(), {"Axis": "axis"})
    message = str(raised.value)
    assert "'Wall'" in message and "'PoreFluid'" in message
    assert "NUM-06" in message
    assert "'wall'" in message and "'electrolyte'" in message


def test_ver27_a_mapping_written_the_wrong_way_round_says_so() -> None:
    """The one ergonomic trap of keying on the file's names, caught by name."""
    with pytest.raises(MeshVocabularyError, match="the other way round"):
        apply_groups(exported_mesh(), {"wall": "Wall", "axis": "Axis"})


def test_ver27_a_key_naming_no_group_of_the_mesh_lists_what_it_carries() -> None:
    """A typo in the mapping is not a silently ignored entry."""
    with pytest.raises(MeshVocabularyError) as raised:
        apply_groups(exported_mesh(), {"Walls": "wall"})
    assert "'Walls'" in str(raised.value)
    assert "Wall" in str(raised.value)


def test_ver27_a_group_mapped_into_the_wrong_namespace_aborts() -> None:
    """``axis`` is a boundary and never a domain; the check is per namespace."""
    with pytest.raises(MeshVocabularyError, match="wrong namespace") as raised:
        apply_groups(exported_mesh(), {"PoreFluid": "axis"})
    assert "not a domain name" in str(raised.value)


def test_ver27_the_two_namespaces_are_the_specified_vocabulary() -> None:
    """Section 5.3.1's lists, with no aliases in either (FR-16, IF-06)."""
    assert MATERIAL_VOCABULARY == (
        "analyte",
        "cis",
        "electrolyte",
        "exclusion",
        "membrane",
        "protein",
        "trans",
    )
    assert BOUNDARY_VOCABULARY == (
        "analyte",
        "axis",
        "cis",
        "interface",
        "membrane",
        "membrane_outer",
        "trans",
        "wall",
    )


# -- the gate itself -----------------------------------------------------------


def test_ver27_a_name_the_run_selects_on_and_no_group_supplies_aborts(mesh_file: Path) -> None:
    """The failure the whole module exists for: ``wall`` mapped away.

    Every group is claimed and the mesh is sound, so nothing else in the pipeline
    has anything to complain about. Only the derived requirement notices that
    this run will select on ``wall`` and find nothing.
    """
    groups = (
        "{PoreFluid: electrolyte, Membrane: membrane, "
        "Axis: axis, Wall: interface, Bilayer: membrane, Top: cis, Bottom: trans}"
    )
    _, resolved = resolved_case(mesh_file, groups=groups)
    with pytest.raises(MeshVocabularyError) as raised:
        ingest(resolved.mesh, resolved)
    message = str(raised.value)
    assert "'wall'" in message
    assert "PHY-02" in message or "no-slip" in message
    assert "NUM-06" in message


def test_phy03_a_solid_domain_with_no_permittivity_aborts_naming_phy20(
    mesh_file: Path,
) -> None:
    """Poisson is solved on the solids too, so a missing entry is 24x too large."""
    _, resolved = resolved_case(mesh_file, physics="{model: pnp-ns}")
    with pytest.raises(MeshVocabularyError) as raised:
        ingest(resolved.mesh, resolved)
    assert "solid_permittivities" in str(raised.value)
    assert "3.2" in str(raised.value)


def test_ver27_a_fluid_domain_needs_no_permittivity(mesh_file: Path) -> None:
    """The electrolyte's eps_r is a correction of its own (PHY-20), not an entry."""
    _, resolved = resolved_case(mesh_file)
    ingested = ingest(resolved.mesh, resolved)
    assert set(ingested.data.materials) == {"electrolyte", "membrane"}


def test_qr12_a_slivered_supplied_mesh_aborts_before_any_solve(tmp_path: Path) -> None:
    """VER-10's gate runs on an ingested mesh exactly as on a generated one."""
    path = write_msh41(exported_mesh(slivered=True), tmp_path / "slivered.msh")
    _, resolved = resolved_case(path)
    with pytest.raises(MeshQualityError) as raised:
        ingest(resolved.mesh, resolved)
    assert raised.value.gate in {"minimum SICN", "minimum gamma"}


def test_ver27_a_missing_mesh_file_names_the_path(tmp_path: Path) -> None:
    """The first step of the gate, and the one a typo hits."""
    document = loads_case(case_text(tmp_path / "absent.msh"))
    resolved = resolve(document)
    with pytest.raises(FileNotFoundError, match=r"absent\.msh"):
        ingest(resolved.mesh, resolved)


def test_ver27_the_gated_mesh_carries_what_the_gates_measured(mesh_file: Path) -> None:
    """The report and the mapping travel with the mesh, for FR-25 to record."""
    _, resolved = resolved_case(mesh_file)
    ingested = ingest(resolved.mesh, resolved)

    summary = ingested.summary()
    assert summary["source"] == "exported.msh"
    assert summary["content_hash"] == ingested.content_hash
    assert summary["groups"]["Wall"] == "wall"
    quality = summary["quality"]
    assert quality["elements"] == ingested.data.element_count
    assert quality["min_sicn"] > 0.3 and quality["min_gamma"] > 0.3
    assert quality["inverted"] == 0


# -- the stage -----------------------------------------------------------------


def test_ver25_the_mesh_stage_is_stage_six_and_describes_itself() -> None:
    """FR-27: the registry can say what this stage takes without importing it."""
    description = describe("mesh")
    assert description.number == 6
    assert description.inputs == ("case",)
    assert create("mesh").describe() == description


def test_ver27_the_artefact_key_is_the_contents_and_the_mapping(
    mesh_file: Path, tmp_path: Path
) -> None:
    """Two maps over one file are two runs; one mesh under two names is one run.

    The mapping is a *parameter* of the artefact and not a summary field. The
    same file read under two different ``inputs.mesh.groups`` maps poses two
    different sets of boundary conditions, and keying them alike would serve one
    solve's answer out of the other's cache entry (section 5.3.2).
    """
    stage = MeshStage(workspace=tmp_path / "work")
    first = stage.key(StageInputs(case=loads_case(case_text(mesh_file))))

    copied = tmp_path / "renamed.msh"
    copied.write_bytes(mesh_file.read_bytes())
    same = stage.key(StageInputs(case=loads_case(case_text(copied))))
    assert same.hash == first.hash

    other_map = (
        "{PoreFluid: electrolyte, Membrane: membrane, "
        "Axis: axis, Wall: wall, Bilayer: interface, Top: cis, Bottom: trans}"
    )
    remapped = stage.key(StageInputs(case=loads_case(case_text(mesh_file, groups=other_map))))
    assert remapped.hash != first.hash


def test_ver25_the_mesh_stage_reports_progress_ending_at_one(
    mesh_file: Path, tmp_path: Path
) -> None:
    """FR-27: monotone, ending at 1, and the archival copy speaks the vocabulary."""
    reports: list[tuple[float, str]] = []
    stage = MeshStage(workspace=tmp_path / "work")
    artefact = stage.run(
        StageInputs(case=loads_case(case_text(mesh_file))),
        progress=lambda fraction, message: reports.append((fraction, message)),
    )

    fractions = [fraction for fraction, _ in reports]
    assert fractions == sorted(fractions)
    assert fractions[-1] == pytest.approx(1.0)
    assert artefact.hash == stage.key(StageInputs(case=loads_case(case_text(mesh_file)))).hash
    assert artefact.payload["mesh"].is_file()
    # Written from the mapped mesh, so reading it back needs no mapping at all.
    written, applied = apply_groups(read(artefact.payload["mesh"]), {})
    assert set(written.boundaries) == {"axis", "wall", "membrane", "cis", "trans"}
    assert all(key == value for key, value in applied.items())


def test_ver25_a_cancelled_mesh_stage_writes_nothing(mesh_file: Path, tmp_path: Path) -> None:
    """Cancellation raises before the archival copy exists."""
    flag = CancelFlag()
    flag.cancel()
    with pytest.raises(Cancelled, match="mesh"):
        MeshStage(workspace=tmp_path / "work").run(
            StageInputs(case=loads_case(case_text(mesh_file))), cancel=flag
        )
    assert not (tmp_path / "work").exists()

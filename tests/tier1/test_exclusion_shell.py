"""VER-59, the shell: stage 5's ion-exclusion shell on a convex body (FR-15, FR-09, QR-12).

The body is the parallelogram of ``tests/conftest.py``, in a 30 nm reservoir. It
is convex, so its offset ``O`` is convex and the closing of step 2 fills
nothing: the outer surface then lies within the exact offset on both sides, to
the sagitta of a resampled chord inside and to 1e-6 nm outside (WP30 Outcomes,
on *Design* section 2). The shell's construction is the section 5.2.1 NOTE on the
ion-exclusion shell; its case refusals are the section 5.3.1 NOTE on the v2 keys
that change a number.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.core.stages import MissingExtraError
from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import (
    EXCLUSION,
    RegionGateError,
    RegionRecord,
    RegionStage,
    build_region,
    derive_region,
    distance_to_loop,
    exclusion_shell,
    measure,
    name_region,
    read_region,
    region_graph,
    write_region,
)
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import CaseValidationError, MembraneSpec, ReservoirSpec, loads_case, resolve
from nanopnp.materials.corrections import load_corrections
from nanopnp.mesh.generate import sizing_parameters, wall_statistics
from nanopnp.mesh.ingest import MeshStage, deployed_mesh
from nanopnp.mesh.sizing import (
    EXCLUSION_WALL_DIVISION,
    SIZES,
    WallSize,
    divided_wall_size,
    resolve_wall_size,
    wall_divisions,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.case import CaseDocument


def eps_r0(document: CaseDocument) -> float:
    """Return ``eps_r,f0`` read from the case's parameter file, as the sizing took it before D7."""
    return load_corrections(document.electrolyte.parameters).solvent.permittivity.eps_r0


def wall_size(document: CaseDocument) -> WallSize:
    """Return :func:`resolve_wall_size` at the parameter file's ``eps_r,f0``."""
    return resolve_wall_size(document, permittivity_0=eps_r0(document))


OFFSET_NM = 0.25
"""``a``: ``a_Na/2`` of ``willems2020_nacl`` and VER-31's ``lambda_S`` (WP30 D15)."""

H_C_NM = 0.05
"""The contour's size target at the default density grid spacing."""

CASE = """\
schema: nanopnp/case/v2
name: shell
inputs:
  profile: {{path: {path}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: {scale}}}}}
{charge}"""


def case_text(profile: Path, *, charge: str = "", scale: float = 5.0) -> str:
    """Return the coarse profile case, with an optional ``charge:`` line."""
    return CASE.format(path=profile, charge=charge, scale=scale)


def _offset(a: float = OFFSET_NM) -> str:
    """Return the ``charge:`` block setting the exclusion offset."""
    return f"charge: {{exclusion_offset_nm: {a}}}\n"


@pytest.fixture(scope="module")
def shelled(parallelogram_profile: Path, tmp_path_factory: pytest.TempPathFactory):
    """Return the case, and its stage-5 and stage-6 artefacts, at ``a`` = 0.25 nm."""
    work = tmp_path_factory.mktemp("shell")
    case = loads_case(case_text(parallelogram_profile, charge=_offset()))
    region = RegionStage(workspace=work / "region").run(StageInputs(case=case))
    mesh = MeshStage(workspace=work / "mesh").run(
        StageInputs(case=case, upstream={"region": region})
    )
    return case, region, mesh


@pytest.fixture(scope="module")
def plain(parallelogram_profile: Path, tmp_path_factory: pytest.TempPathFactory):
    """Return the shell-free stage-5 artefact of the same body."""
    work = tmp_path_factory.mktemp("plain")
    case = loads_case(case_text(parallelogram_profile))
    return RegionStage(workspace=work / "region").run(StageInputs(case=case))


def _record(artefact) -> RegionRecord:  # type: ignore[no-untyped-def]
    """Return the record a stage-5 artefact carries."""
    return read_region(Path(artefact.payload["region"]))


# -- the shell's geometry ----------------------------------------------------------


def test_ver59_every_wall_node_lies_within_the_band_about_the_exact_offset(shelled) -> None:
    """``[a - max(h_c^2/a, a/100), a + 1e-6]`` nm from the body, at every ``wall`` node."""
    case, region, mesh = shelled
    record = _record(region)
    data = deployed_mesh(resolve(case), mesh).data
    wall = data.boundaries.index("wall")
    nodes = np.unique(data.edges[data.edge_group == wall])
    distance = distance_to_loop(data.vertices[nodes], record.points())
    low = OFFSET_NM - max(H_C_NM**2 / OFFSET_NM, OFFSET_NM / 100.0)
    assert distance.min() >= low, distance.min()
    assert distance.max() <= OFFSET_NM + 1e-6, distance.max()
    shell = record.exclusion
    assert shell is not None
    assert shell.holes.count == 0
    assert low <= shell.distance_nm[0] <= shell.distance_nm[1] <= OFFSET_NM + 1e-6


def test_ver59_the_shell_is_one_face_named_wall_outside_and_interface_within(shelled) -> None:
    """One ``exclusion`` face; ``wall`` bounds it and the electrolyte only (D8)."""
    _, region, _ = shelled
    record = _record(region)
    shape = build_region(record)
    faces = [face for face in shape.faces if face.name == EXCLUSION]
    assert len(faces) == 1
    edges_of = {str(face.name): set(face.edges) for face in shape.faces}
    for edge in set(shape.edges):
        if edge.name == "wall":
            assert edge in edges_of[EXCLUSION] and edge in edges_of["electrolyte"]
        if edge in edges_of["protein"]:
            assert edge.name == "interface"
    seams = {edge for edge in edges_of[EXCLUSION] if edge.name == "interface"}
    assert seams & edges_of["protein"] and seams & edges_of["membrane"]
    assert set(record.face_areas_nm2) == {"electrolyte", "exclusion", "membrane", "protein"}


def test_ver59_a_body_edge_left_facing_the_electrolyte_beside_a_shell_is_refused(
    shelled,
) -> None:
    """A loop that leaves the body's foot on the membrane uncovered is refused, naming where.

    Cut from the offset over ``z`` in ``[0.9, 1.7]`` outward of ``r = 5``: the
    shell then starts at ``z = 1.7``, one face still, and the body's outer edge
    between the membrane's upper face and there meets the electrolyte.
    """
    from shapely.geometry import Polygon, box

    _, region, _ = shelled
    record = _record(region)
    assert record.exclusion is not None
    cut = Polygon(record.exclusion.loop).difference(box(5.0, 0.9, 7.0, 1.7))
    loop = [(float(r), float(z)) for r, z in list(cut.exterior.coords)[:-1]]
    broken = record.model_copy(
        update={"exclusion": record.exclusion.model_copy(update={"loop": loop})}
    )
    with pytest.raises(RegionGateError) as raised:
        build_region(broken)
    message = str(raised.value)
    assert "facing the electrolyte beside an exclusion shell" in message
    r, z = (float(v) for v in re.findall(r"\(r, z\) = \(([-0-9.]+), ([-0-9.]+)\)", message)[0])
    assert 1.4 < z < 1.7 and r == pytest.approx(3.0 + (z + 3.0) / 2.0, abs=1e-6)


def test_ver59_the_membrane_chord_and_junction_are_the_shell_free_regions(shelled, plain) -> None:
    """The shell is carved against an unchanged membrane (section 5.2.1 NOTE)."""
    with_shell, without = _record(shelled[1]), _record(plain)
    assert with_shell.membrane == without.membrane
    assert with_shell.junction_nm == without.junction_nm
    assert with_shell.axis_split_nm == without.axis_split_nm
    assert with_shell.face_areas_nm2["membrane"] == pytest.approx(
        without.face_areas_nm2["membrane"], rel=1e-12
    )
    assert with_shell.face_areas_nm2["protein"] == pytest.approx(
        without.face_areas_nm2["protein"], rel=1e-12
    )


def test_ver59_an_offset_closing_the_constriction_is_refused_naming_its_z() -> None:
    """A body within ``a + h_c`` of the axis is refused, naming the z interval and the radius."""
    points = np.array([(0.25, -3.0), (2.0, -3.0), (2.0, 3.0), (0.25, 3.0)])
    with pytest.raises(RegionGateError) as raised:
        exclusion_shell(points, OFFSET_NM, H_C_NM, reservoir_radius_nm=30.0)
    message = str(raised.value)
    assert "closing the constriction over z = [" in message
    assert "least radius is 0.2500 nm" in message
    assert "a + h_c = 0.3000 nm" in message


def test_ver59_an_outer_surface_inside_the_bound_is_refused_naming_where(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The thickness bound is a gate: one chord per quarter circle sags 0.073 nm, and is refused.

    The resampling of step 4 keeps every chord near ``1.25 h_c`` and the surface
    within the bound by argument; the gate is what asserts it on every shell.
    """
    from nanopnp.geometry import region

    monkeypatch.setattr(region, "EXCLUSION_QUAD_SEGS", 1)
    points = np.array([(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)])
    with pytest.raises(RegionGateError) as raised:
        exclusion_shell(points, OFFSET_NM, H_C_NM, reservoir_radius_nm=30.0)
    message = str(raised.value)
    assert "exclusion shell thickness" in message
    assert "at least a - max(h_c^2/a, a/100) = 0.24000 nm" in message
    assert "(r, z) = (" in message


def test_ver59_a_necked_pocket_is_filled_and_recorded() -> None:
    """A notch whose mouth is under ``2a`` wide encloses fluid no ion reaches: filled, recorded."""
    points = np.array(
        [
            (3.0, -3.0),
            (5.0, -3.0),
            (5.0, 2.15),
            (4.6, 2.15),
            (4.6, 1.8),
            (3.8, 1.8),
            (3.8, 2.8),
            (4.6, 2.8),
            (4.6, 2.45),
            (5.0, 2.45),
            (5.0, 3.0),
            (3.0, 3.0),
        ]
    )
    shell = exclusion_shell(points, OFFSET_NM, H_C_NM, reservoir_radius_nm=30.0)
    assert shell.holes.count == 1
    # The pocket, 0.8 x 1.0 nm, less 0.25 nm on every side: 0.3 x 0.5 nm with
    # rounded corners, so a little under 0.15 nm^2.
    assert 0.12 < shell.holes.area_nm2 < 0.15
    centre = shell.holes.centroids_nm[0]
    # Symmetric in z about the mouth; nudged outward by the round joins at its lips.
    assert centre[1] == pytest.approx(2.3, abs=1e-9)
    assert 4.2 < centre[0] < 4.21


# -- the case refusals ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("charge", "fragments"),
    [
        (_offset(0.1), ("charge.exclusion_offset_nm", "geometry.density.grid_spacing_nm", "2 h_c")),
        (_offset(0.05), ("charge.exclusion_offset_nm", "geometry.density.grid_spacing_nm")),
    ],
)
def test_ver59_an_offset_at_most_twice_h_c_is_refused_naming_both_keys(
    parallelogram_profile: Path, charge: str, fragments: tuple[str, ...]
) -> None:
    """``0 < a <= 2 h_c`` is narrower than the feature-size criterion admits (D11)."""
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(case_text(parallelogram_profile, charge=charge)))
    assert all(fragment in str(raised.value) for fragment in fragments), raised.value


def test_ver59_the_keys_beside_a_supplied_mesh_or_without_a_profile_are_refused() -> None:
    """A knob with no effect is refused naming both keys (D12)."""
    mesh_case = (
        "schema: nanopnp/case/v2\nname: supplied\n"
        "inputs:\n  mesh: {path: pore.msh, format: msh41}\n"
        "electrolyte:\n  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 1.0\n"
        "boundary_conditions: {bias_V: 0.05, ground: cis}\n"
        "physics: {model: pnp-ns}\n"
    )
    for charge in (_offset(), "charge: {dielectric_transition_nm: 0.15}\n"):
        with pytest.raises(CaseValidationError) as raised:
            resolve(loads_case(mesh_case + charge))
        message = str(raised.value)
        assert "beside inputs.mesh" in message
        assert re.search(r"charge\.(exclusion_offset|dielectric_transition)_nm", message)


def test_ver59_the_case_without_shapely_is_refused_naming_the_extra_and_the_key(
    parallelogram_profile: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The shell is built with Shapely, which is in ``structure`` (section 5.2.1 NOTE)."""
    monkeypatch.setitem(sys.modules, "shapely", None)
    case = loads_case(case_text(parallelogram_profile, charge=_offset()))
    with pytest.raises(MissingExtraError) as raised:
        RegionStage(workspace=tmp_path).run(StageInputs(case=case))
    message = str(raised.value)
    assert "'structure' extra" in message
    assert "charge.exclusion_offset_nm" in message


# -- the record and the key ------------------------------------------------------------


def test_ver59_the_record_round_trips_and_rebuilds_without_shapely(
    shelled, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stage 6 rebuilds the shell from the record's loop, with no Shapely at all (D10)."""
    record = _record(shelled[1])
    again = read_region(write_region(record, tmp_path / "region.yaml"))
    assert again == record
    monkeypatch.setitem(sys.modules, "shapely", None)
    areas, counts = measure(build_region(again))
    assert counts == record.edge_counts
    assert areas == pytest.approx(record.face_areas_nm2, rel=1e-12)


def test_ver59_the_offset_keys_stage_5_and_6_only_when_it_is_non_zero(
    parallelogram_profile: Path, shelled, plain
) -> None:
    """``exclusion`` enters the stage-5 parameters and the stage-6 recipe only with ``a > 0``."""
    _, region, mesh = shelled
    assert "exclusion" not in plain.parameters
    assert region.parameters["exclusion"] == {  # type: ignore[comparison-overlap]
        "offset_nm": OFFSET_NM,
        "h_c_nm": H_C_NM,
        "constants": {
            "join": "round",
            "quad_segs": 8,
            "closing": "2h_c",
            "holes": "filled",
            "resample": "L/floor(L/1.05h_c)",
            "spacing": "h_c",
            "axis_clearance": "h_c",
            "inner_bound": "max(h_c^2/a, a/100)",
        },
    }
    assert {k: v for k, v in region.parameters.items() if k != "exclusion"} == dict(
        plain.parameters
    )
    explicit = loads_case(case_text(parallelogram_profile, charge=_offset(0.0)))
    assert RegionStage().key(StageInputs(case=explicit)).hash == plain.hash
    assert mesh.parameters["sizing"]["exclusion"] == "wall_h_nm"  # type: ignore[index]
    assert (
        mesh.parameters["sizing"]["exclusion_wall"]  # type: ignore[index]
        == "ceil(L/(1.1 wall_h)) equal segments"
    )
    assert "exclusion" in mesh.parameters["materials"]  # type: ignore[operator]
    # Gmsh divides the ring's edges finely enough unaided, so its recipe has no rule.
    wall = wall_size(loads_case(case_text(parallelogram_profile, charge=_offset())))
    gmsh = sizing_parameters(wall, SIZES.scaled(wall.size_scale), "gmsh", exclusion=True)
    assert "exclusion_wall" not in gmsh
    assert gmsh["exclusion"] == "wall_h_nm"


@pytest.mark.parametrize(
    ("length_nm", "wall_h_nm", "count", "size_nm"),
    [
        (0.0525, 0.05, 1, 0.05),
        (0.0575, 0.05, 2, 0.02875),
        (0.0525, 0.045, 2, 0.02625),
        (0.0525, 0.035, 2, 0.02625),
        (0.0525, 0.0225, 3, 0.0175),
        (0.0525, 0.25, 1, 0.25),
    ],
)
def test_ver59_netgen_cuts_a_shell_wall_edge_into_equal_segments_of_at_most_1_1_h(
    length_nm: float, wall_h_nm: float, count: int, size_nm: float
) -> None:
    """``n = ceil(L / 1.1 h)``; ``maxh`` is ``L/n``, or the target itself where ``n`` is 1."""
    assert wall_divisions(length_nm, wall_h_nm) == count
    assert divided_wall_size(length_nm, wall_h_nm) == pytest.approx(size_nm, rel=1e-12)
    assert length_nm / count <= EXCLUSION_WALL_DIVISION * wall_h_nm


def test_ver59_the_shell_meshes_at_a_wall_target_its_whole_edges_failed(
    parallelogram_profile: Path, tmp_path: Path
) -> None:
    """At 3 M the ``auto`` target is 0.035 nm, 1.5 of whose ring edges netgen left whole.

    The wall-size gate refused that mesh at a mean of 1.455 (``.knowledge/06``
    section 8.1.4). Now every ``wall`` edge is cut into at least
    :func:`wall_divisions` segments, and the mesh passes the gate.
    """
    text = case_text(parallelogram_profile, charge=_offset(), scale=1.0)
    case = loads_case(text.replace("concentration_M: 1.0", "concentration_M: 3.0"))
    region = RegionStage(workspace=tmp_path / "region").run(StageInputs(case=case))
    mesh = MeshStage(workspace=tmp_path / "mesh").run(
        StageInputs(case=case, upstream={"region": region})
    )
    target = wall_size(case).wall_h_nm
    assert target == pytest.approx(0.03505, abs=5e-5)
    shape = build_region(_record(region))
    expected = sum(
        wall_divisions(float(edge.mass), target)
        for edge in set(shape.edges)  # a glued edge is listed once per face it bounds
        if edge.name == "wall"
    )
    data = deployed_mesh(resolve(case), mesh).data
    statistics = wall_statistics(data, target)
    # At least the asked-for count: netgen may add a node, as it did once here
    # at the 0.01 nm edge the membrane cuts off the ring, but never leaves fewer.
    assert expected <= statistics.count <= expected + 2
    assert statistics.mean_ratio <= EXCLUSION_WALL_DIVISION


def test_ver59_a_sweep_over_the_offset_severs_its_warm_starts(
    parallelogram_profile: Path, tmp_path: Path
) -> None:
    """The offset moves the mesh, so each of its values is a cold root, and the plan says so.

    A chain across it would be refused member by member at the solve, whose
    warm start gates on the mesh hash (section 5.3.2); the transition moves only
    a coefficient on one mesh, and keeps its chain.
    """
    from nanopnp.sweep.plan import plan_from_document

    base = case_text(parallelogram_profile, charge=_offset(0.0))
    (tmp_path / "base.yaml").write_text(base, encoding="utf-8")
    roots = {}
    for key, values in (
        ("exclusion_offset_nm", "[0.0, 0.25]"),
        ("dielectric_transition_nm", "[0.0, 0.15]"),
    ):
        sweep = tmp_path / f"{key}.yaml"
        sweep.write_text(
            "schema: nanopnp/sweep/v1\nname: probe\nbase: base.yaml\naxes:\n"
            f"  - name: knob\n    path: charge.{key}\n    values: {values}\n",
            encoding="utf-8",
        )
        plan = plan_from_document(sweep, check_meshes=False)
        roots[key] = sum(1 for point in plan.points if point.parent is None)
        if key == "exclusion_offset_nm":
            assert any("charge.exclusion_offset_nm" in warning for warning in plan.warnings)
    assert roots == {"exclusion_offset_nm": 2, "dielectric_transition_nm": 1}


def test_ver59_the_gmsh_region_graph_reads_the_four_faces(shelled) -> None:
    """WP23's graph reads the shelled region: four closed loops, counts and areas the record's."""
    record = _record(shelled[1])
    graph = region_graph(build_region(record), record)
    assert set(graph.faces) == {"electrolyte", "exclusion", "membrane", "protein"}
    assert graph.edge_counts() == record.edge_counts
    for name, area in record.face_areas_nm2.items():
        assert graph.area(name) == pytest.approx(area, rel=1e-9)


def test_ver59_the_manifest_lists_the_switch_and_the_mesh_material_deviation(
    parallelogram_profile: Path, tmp_path: Path
) -> None:
    """FR-25 with no new code: the switch, and ``exclusion`` on the mesh (D14)."""
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    case = tmp_path / "shell.case.yaml"
    case.write_text(case_text(parallelogram_profile, charge=_offset()), encoding="utf-8")
    result = run_case(
        case, store=Store(tmp_path / "store"), workspace=tmp_path / "work", upto="mesh"
    )
    manifest = result.manifest
    paths = [deviation.path for deviation in manifest.deviations]
    assert "charge.exclusion_offset_nm" in paths
    sources = [deviation.source for deviation in manifest.contributed_deviations]
    assert "mesh material 'exclusion'" in sources


def test_ver59_derive_region_at_zero_offset_runs_none_of_the_shell(
    parallelogram_profile: Path, plain
) -> None:
    """With ``a = 0`` none of the NOTE runs: the record is the shell-free one."""
    profile = load_profile(parallelogram_profile)
    record = derive_region(profile, MembraneSpec(), ReservoirSpec(radius_nm=30.0))
    assert record.exclusion is None
    assert record == _record(plain)
    shape = build_region(record)
    name_region(shape, reservoir_radius_nm=30.0)
    assert not any(face.name == EXCLUSION for face in shape.faces)

"""VER-33: the IF-07 field export: exactness, the split and the units."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from nanopnp.core.scaling import Scales
from nanopnp.core.typing import Expression, Mesh, Numeric
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS, CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.models import ModelSolution
from nanopnp.post.export import (
    EXPORT_SCHEMA,
    OMEGA_STEM,
    OMEGA_W_STEM,
    FieldExport,
    export_fields,
    p2_nodes,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import meshio

    from nanopnp.charge.stage import ResolvedFields
    from nanopnp.io.resolved import ResolvedCase

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0

EXACT_NM = 1e-10

MEMBRANE_PERMITTIVITY = {"membrane": 3.2}


def _quadratic(
    a: float, b: float, c: float, d: float, e: float
) -> Callable[[Numeric, Numeric], Numeric]:

    def evaluate(x: Numeric, y: Numeric) -> Numeric:
        return a * x * x + b * x * y + c * y * y + d * x + e

    return evaluate


NONDIMENSIONAL: dict[str, Callable[[Numeric, Numeric], Numeric]] = {
    "potential": _quadratic(0.03, -0.05, 0.02, 0.4, -1.1),
    "c_Na+": _quadratic(-0.02, 0.04, 0.01, -0.3, 2.0),
    "c_Cl-": _quadratic(0.05, 0.01, -0.03, 0.7, 1.5),
    "velocity_r": _quadratic(0.01, 0.02, -0.01, 0.5, -0.2),
    "velocity_z": _quadratic(-0.03, 0.01, 0.02, -0.6, 0.9),
    "wall_distance": _quadratic(0.02, -0.01, 0.03, 0.2, 1.0),
}


# NUM-01
def _pressure(x: Numeric, y: Numeric) -> Numeric:
    return 0.8 * x - 1.3 * y + 0.25


@pytest.fixture(scope="module")
def mesh() -> Mesh:
    return PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM)


@pytest.fixture(scope="module")
def solution(mesh: Mesh) -> ModelSolution:
    import ngsolve as ngs

    model = models.create("epnp-ns", solid_permittivities=MEMBRANE_PERMITTIVITY)
    space = model.space(mesh)
    state = model.cold_state(mesh)
    fluid = mesh.Materials(ELECTROLYTE_DOMAINS)
    for field, component in zip(model.fields, state.components, strict=True):
        region = None if field.domain is None else fluid
        if field.element == "vector_h1":
            target: Expression = ngs.CF(
                (
                    NONDIMENSIONAL["velocity_r"](ngs.x, ngs.y),
                    NONDIMENSIONAL["velocity_z"](ngs.x, ngs.y),
                )
            )
        elif field.name == "pressure":
            target = _pressure(ngs.x, ngs.y)
        else:
            target = NONDIMENSIONAL[field.name](ngs.x, ngs.y)
        if region is None:
            component.Set(target)
        else:
            component.Set(target, definedon=region)

    distance = ngs.GridFunction(ngs.H1(mesh, order=2))
    distance.Set(NONDIMENSIONAL["wall_distance"](ngs.x, ngs.y))
    return ModelSolution(model=model, space=space, state=state, wall_distance_nm=distance)


@pytest.fixture(scope="module")
def exported(solution: ModelSolution, tmp_path_factory: pytest.TempPathFactory) -> FieldExport:
    import ngsolve as ngs

    mesh = solution.space.mesh
    directory = tmp_path_factory.mktemp("fields")
    return export_fields(
        solution,
        directory,
        scales=solution.model.scales,
        relative_permittivity=mesh.MaterialCF(MEMBRANE_PERMITTIVITY, default=ngs.CF(78.0)),
        fixed_charge_C_m3=ngs.CF(1.0e6) * ngs.x,
    )


def _read(export: FieldExport, stem: str) -> meshio.Mesh:
    import meshio

    return meshio.read(export.omega[0].with_name(f"{stem}.xdmf"))


def test_ver33_the_exported_node_count_is_the_p2_degree_of_freedom_count(mesh: Mesh) -> None:
    import ngsolve as ngs

    nodes = p2_nodes(mesh)
    assert nodes.points_nm.shape[0] == mesh.nv + mesh.nedge
    assert nodes.points_nm.shape[0] == ngs.H1(mesh, order=2).ndof
    assert nodes.cells.shape == (mesh.ne, 6)


def test_ver33_each_midside_node_is_the_midpoint_of_its_own_vertex_pair(mesh: Mesh) -> None:
    import numpy as np

    nodes = p2_nodes(mesh)
    points = nodes.points_nm
    for midside, (first, second) in enumerate(((0, 1), (1, 2), (2, 0)), start=3):
        expected = 0.5 * (points[nodes.cells[:, first]] + points[nodes.cells[:, second]])
        assert np.abs(points[nodes.cells[:, midside]] - expected).max() < EXACT_NM


def test_ver33_a_permuted_midside_node_fails_that_same_check(mesh: Mesh) -> None:
    import numpy as np

    nodes = p2_nodes(mesh)
    points = nodes.points_nm
    permuted = np.roll(nodes.cells[:, 3:], 1, axis=1)
    worst = 0.0
    for midside, (first, second) in enumerate(((0, 1), (1, 2), (2, 0))):
        expected = 0.5 * (points[nodes.cells[:, first]] + points[nodes.cells[:, second]])
        worst = max(worst, float(np.abs(points[permuted[:, midside]] - expected).max()))
    assert worst > 0.1, "a permutation of the midside nodes must be detectable"


def test_ver33_a_quadratic_survives_the_export_exactly_on_the_whole_domain(
    exported: FieldExport,
) -> None:
    import numpy as np

    grid = _read(exported, OMEGA_STEM)
    x, y = grid.points[:, 0], grid.points[:, 1]
    expected = NONDIMENSIONAL["potential"](x, y) * _scales(exported).potential_V
    assert np.abs(grid.point_data["phi_V"] - expected).max() < EXACT_NM


def test_ver33_a_quadratic_survives_the_export_exactly_on_the_fluid(
    exported: FieldExport,
) -> None:
    import numpy as np

    grid = _read(exported, OMEGA_W_STEM)
    x, y = grid.points[:, 0], grid.points[:, 1]
    scales = _scales(exported)
    for name, attribute in (("c_Na+", "c_Na+_mol_m3"), ("c_Cl-", "c_Cl-_mol_m3")):
        expected = NONDIMENSIONAL[name](x, y) * scales.concentration_mol_m3
        assert np.abs(grid.point_data[attribute] - expected).max() < EXACT_NM * abs(
            scales.concentration_mol_m3
        )


def test_ver33_the_pressure_is_exact_at_the_midside_nodes_it_did_not_ask_for(
    exported: FieldExport,
) -> None:
    import numpy as np

    grid = _read(exported, OMEGA_W_STEM)
    scales = _scales(exported)
    expected = _pressure(grid.points[:, 0], grid.points[:, 1]) * scales.pressure_Pa
    assert np.abs(grid.point_data["p_Pa"] - expected).max() < EXACT_NM * abs(scales.pressure_Pa)


def test_ver33_the_two_files_carry_the_whole_domain_and_fluid_field_sets(
    exported: FieldExport,
) -> None:
    omega = _read(exported, OMEGA_STEM)
    omega_w = _read(exported, OMEGA_W_STEM)
    assert set(omega.point_data) == {"phi_V", "rho_fixed_C_m3"}
    assert set(omega.cell_data) == {"material_id", "eps_r"}
    assert set(omega_w.point_data) == {
        "c_Na+_mol_m3",
        "c_Cl-_mol_m3",
        "u_m_s",
        "p_Pa",
        "wall_distance_nm",
    }
    assert omega_w.cell_data == {}


def test_ver33_the_fluid_file_holds_no_node_that_only_a_solid_element_carries(
    solution: ModelSolution,
    exported: FieldExport,
) -> None:
    import numpy as np

    mesh = solution.space.mesh
    whole = {tuple(point) for point in np.round(p2_nodes(mesh).points_nm, 12)}
    fluid = {
        tuple(point)
        for point in np.round(p2_nodes(mesh, materials=ELECTROLYTE_DOMAINS).points_nm, 12)
    }
    solid_only = whole - fluid
    assert solid_only, "the mesh must have solid-only nodes for this test to mean anything"

    written = {tuple(point) for point in np.round(_read(exported, OMEGA_W_STEM).points[:, :2], 12)}
    assert written == fluid
    assert not written & solid_only


# PHY-01
def test_ver33_the_velocity_is_written_as_a_three_component_vector(
    exported: FieldExport,
) -> None:
    import numpy as np

    grid = _read(exported, OMEGA_W_STEM)
    velocity = grid.point_data["u_m_s"]
    assert velocity.shape == (grid.points.shape[0], 3)
    scale = _scales(exported).velocity_m_s
    x, y = grid.points[:, 0], grid.points[:, 1]
    for column, name in enumerate(("velocity_r", "velocity_z")):
        expected = NONDIMENSIONAL[name](x, y) * scale
        assert np.abs(velocity[:, column] - expected).max() < EXACT_NM * abs(scale)
    assert np.all(velocity[:, 2] == 0.0)


def _scales(export: FieldExport) -> Scales:
    recorded = json.loads(_metadata(export, OMEGA_STEM)["scales"])
    return Scales(
        length_nm=recorded["length_nm"],
        concentration_M=recorded["concentration_M"],
        temperature_K=recorded["temperature_K"],
        diffusivity_m2_s=recorded["diffusivity_m2_s"],
        viscosity_Pa_s=recorded["viscosity_Pa_s"],
        relative_permittivity=recorded["relative_permittivity"],
    )


def _metadata(export: FieldExport, stem: str) -> dict[str, Any]:
    import h5py

    path = export.omega[0].with_name(f"{stem}.h5")
    with h5py.File(path, "r") as handle:
        return {key: value for key, value in handle.attrs.items()}


def test_ver33_the_recorded_scale_set_is_the_one_the_state_was_solved_in(
    solution: ModelSolution, exported: FieldExport
) -> None:
    recorded = json.loads(_metadata(exported, OMEGA_STEM)["scales"])
    assert recorded == solution.model.scales.summary()
    assert _metadata(exported, OMEGA_STEM)["coordinate_units"] == "nm"


def test_ver33_the_two_pi_of_the_axisymmetric_measure_is_absent(
    exported: FieldExport,
) -> None:
    import math

    import numpy as np

    grid = _read(exported, OMEGA_STEM)
    x, y = grid.points[:, 0], grid.points[:, 1]
    nondimensional = NONDIMENSIONAL["potential"](x, y)
    far = np.abs(nondimensional) > 0.5
    ratio = grid.point_data["phi_V"][far] / nondimensional[far]
    assert np.abs(ratio - _scales(exported).potential_V).max() < 1e-15
    assert abs(float(np.median(ratio)) / _scales(exported).potential_V - 2.0 * math.pi) > 1.0
    assert int(_metadata(exported, OMEGA_STEM)["two_pi_applied"]) == 0


# PHY-02
def test_ver33_the_wall_distance_is_written_in_nm_and_not_rescaled(
    exported: FieldExport,
) -> None:
    import numpy as np

    grid = _read(exported, OMEGA_W_STEM)
    expected = NONDIMENSIONAL["wall_distance"](grid.points[:, 0], grid.points[:, 1])
    assert np.abs(grid.point_data["wall_distance_nm"] - expected).max() < EXACT_NM


def test_ver33_the_topology_is_triangle_6_at_six_nodes_per_element(
    exported: FieldExport,
) -> None:
    root = ET.parse(exported.omega[0]).getroot()
    topology = root.find("Domain/Grid/Topology")
    assert topology is not None
    assert topology.attrib["TopologyType"] == "Triangle_6"
    assert topology.attrib["NodesPerElement"] == "6"


def test_ver33_heavy_data_is_compressed(exported: FieldExport) -> None:
    import h5py

    for path in exported.paths():
        if path.suffix != ".h5":
            continue
        with h5py.File(path, "r") as handle:
            datasets = list(handle.values())
            assert datasets, f"{path} holds no heavy data"
            for dataset in datasets:
                assert dataset.compression == "gzip", f"{path}:{dataset.name} is uncompressed"


def test_if07_each_file_names_its_schema_and_the_materials_it_covers(
    exported: FieldExport,
) -> None:
    omega = _metadata(exported, OMEGA_STEM)
    omega_w = _metadata(exported, OMEGA_W_STEM)
    assert omega["schema"] == omega_w["schema"] == EXPORT_SCHEMA
    assert omega["domain"] == "omega"
    assert omega_w["domain"] == "omega_w"
    assert set(json.loads(omega["domain_materials"])) == {"electrolyte", "membrane", "cis", "trans"}
    assert set(json.loads(omega_w["domain_materials"])) == {"electrolyte", "cis", "trans"}


def test_if07_a_discontinuous_quantity_is_written_cell_centred(
    exported: FieldExport,
) -> None:
    import numpy as np

    grid = _read(exported, OMEGA_STEM)
    permittivity = np.concatenate(grid.cell_data["eps_r"])
    assert set(np.unique(permittivity)) == {3.2, 78.0}
    identifiers = np.concatenate(grid.cell_data["material_id"])
    assert identifiers.shape == (grid.cells[0].data.shape[0],)
    assert set(np.unique(identifiers)) == set(range(4))


# QR-12
def test_if07_a_material_selection_matching_nothing_is_refused_naming_the_mesh(
    mesh: Mesh,
) -> None:
    with pytest.raises(ValueError, match="no element of the mesh carries a material"):
        p2_nodes(mesh, materials="protein")


# FR-25
def test_if07_the_export_reports_every_path_and_attribute_it_wrote(
    exported: FieldExport,
) -> None:
    assert len(exported.paths()) == 4
    assert all(isinstance(path, Path) and path.exists() for path in exported.paths())
    assert exported.attributes[OMEGA_STEM] == ("phi_V", "rho_fixed_C_m3", "eps_r", "material_id")
    assert exported.attributes[OMEGA_W_STEM] == (
        "c_Cl-_mol_m3",
        "c_Na+_mol_m3",
        "p_Pa",
        "u_m_s",
        "wall_distance_nm",
    )


def test_if07_the_report_exports_the_fixed_charge_it_read_for_the_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    import nanopnp.post.stage as post_stage
    import nanopnp.solve.state as solve_state
    from nanopnp.charge.stage import read_fields
    from nanopnp.cli import main
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    example = Path(__file__).resolve().parents[2] / "examples" / "02-charged-pore"
    field = Path(shutil.copy(example / "ring.field.yaml", tmp_path))
    mesh_path = tmp_path / "pore.msh"
    assert main(["mesh", "cylinder", "--out", str(mesh_path)]) == 0
    case = tmp_path / "charged.case.yaml"
    case.write_text(
        (example / "classical.case.yaml")
        .read_text(encoding="utf-8")
        .replace("path: pore.msh", f"path: {mesh_path}")
        .replace("path: ring.field.yaml", f"path: {field}")
        .replace("outputs: [current, transport_numbers, eof_rate]", "outputs: [current, fields]"),
        encoding="utf-8",
    )

    reads = {"post": 0, "restore": 0}

    def counting(key: str) -> Callable[[ResolvedCase], ResolvedFields]:
        def counted(resolved: ResolvedCase) -> ResolvedFields:
            reads[key] += 1
            return read_fields(resolved)

        return counted

    monkeypatch.setattr(post_stage, "read_fields", counting("post"))
    monkeypatch.setattr(solve_state, "read_fields", counting("restore"))

    result = run_case(case, store=Store(tmp_path / "store"))
    assert reads == {"post": 1, "restore": 1}
    omega = next(path for path in result.files if path.name == f"{OMEGA_STEM}.xdmf")
    assert "rho_fixed_C_m3" in omega.read_text(encoding="utf-8")

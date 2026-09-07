"""VER-33 — the IF-07 field export: exactness, the split, the units.

The export is the one place a solved state leaves the process in a form somebody
*looks at*, and every way it can be wrong is a way that looks right. A permuted
midside node draws a plausible picture of a different function. A fluid field
padded over the membrane draws a depletion that is really an absence. A scale
applied twice, or the ``2 pi`` of the axisymmetric measure applied at all, moves
every number by a constant nobody notices in a colour map.

So nothing here is asserted against the writer's own sampling. Each field is set
to an analytic polynomial that the P2 space represents exactly, and the file is
then checked against that polynomial evaluated at **the coordinates the file
itself carries** — a route that shares no code with the export. A quadratic is
reproduced exactly or it is not, and the tolerance is round-off rather than a
judgement.

Nothing is solved. What is under test is the mapping from a finite-element
function to a file, and a converged state exercises no part of that a
deterministic polynomial does not.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from nanopnp.core.scaling import Scales
from nanopnp.core.typing import Expression, Mesh, Numeric
from nanopnp.io.fields import (
    FIELDS_SCHEMA,
    OMEGA_STEM,
    OMEGA_W_STEM,
    FieldExport,
    export_fields,
    p2_nodes,
)
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS, CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.models import ModelSolution

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import meshio

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0
"""The coarsest mesh carrying all four materials. Nothing here is a physics
assertion, and a mesh with a fluid/solid interface is all the split needs."""

EXACT_NM = 1e-10
"""Round-off tolerance on a quadratic, in the units each field is written in.

Measured worst case is 1.4e-12 over the whole domain and the fluid alike; the
margin is three decades so that a change of linear solver cannot make the test
flap while still failing a real interpolation error by orders of magnitude.
"""

MEMBRANE_PERMITTIVITY = {"membrane": 3.2}


def _quadratic(
    a: float, b: float, c: float, d: float, e: float
) -> Callable[[Numeric, Numeric], Numeric]:
    """Return ``(x, y) -> a x^2 + b x y + c y^2 + d x + e``, for arrays or symbols."""

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
"""The nondimensional field each component is set to before the export runs.

Quadratics, so a P2 space carries them with no error of its own, and none of
them constant or proportional to another: a mix-up between two attributes has to
show as a difference rather than as a coincidence.
"""


def _pressure(x: Numeric, y: Numeric) -> Numeric:
    """``p~``, linear because NUM-01 puts pressure in the P1 half of Taylor-Hood."""
    return 0.8 * x - 1.3 * y + 0.25


@pytest.fixture(scope="module")
def mesh() -> Mesh:
    """Return the meshed pore. Module-scoped: meshing dominates this module."""
    return PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM)


@pytest.fixture(scope="module")
def solution(mesh: Mesh) -> ModelSolution:
    """Return an ePNP-NS state whose every field is a known analytic polynomial.

    Built from :meth:`cold_state` and then overwritten rather than solved. The
    export maps coefficients to a file; a converged state exercises nothing in
    that map which a polynomial does not, and it would cost a ladder.
    """
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
    """Return the result of one export, written once for the whole module."""
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
    """Return one written pair, read back through meshio rather than through us."""
    import meshio

    return meshio.read(export.omega[0].with_name(f"{stem}.xdmf"))


# -- the node set -------------------------------------------------------------


def test_ver33_the_exported_node_count_is_the_p2_degree_of_freedom_count(mesh: Mesh) -> None:
    """``ndof = nv + nedge``, and the export writes exactly that many nodes."""
    import ngsolve as ngs

    nodes = p2_nodes(mesh)
    assert nodes.points_nm.shape[0] == mesh.nv + mesh.nedge
    assert nodes.points_nm.shape[0] == ngs.H1(mesh, order=2).ndof
    assert nodes.cells.shape == (mesh.ne, 6)


def test_ver33_each_midside_node_is_the_midpoint_of_its_own_vertex_pair(mesh: Mesh) -> None:
    """The Triangle_6 convention, asserted geometrically rather than by index.

    Node 3 lies between nodes 0 and 1, node 4 between 1 and 2, node 5 between 2
    and 0. This is the property a local edge numbering would silently permute.
    """
    import numpy as np

    nodes = p2_nodes(mesh)
    points = nodes.points_nm
    for midside, (first, second) in enumerate(((0, 1), (1, 2), (2, 0)), start=3):
        expected = 0.5 * (points[nodes.cells[:, first]] + points[nodes.cells[:, second]])
        assert np.abs(points[nodes.cells[:, midside]] - expected).max() < EXACT_NM


def test_ver33_a_permuted_midside_node_fails_that_same_check(mesh: Mesh) -> None:
    """The convention check has teeth: rolling the three midsides breaks it.

    Without this, a test that merely passes proves only that *some* assignment
    was made, not that it was the right one.
    """
    import numpy as np

    nodes = p2_nodes(mesh)
    points = nodes.points_nm
    permuted = np.roll(nodes.cells[:, 3:], 1, axis=1)
    worst = 0.0
    for midside, (first, second) in enumerate(((0, 1), (1, 2), (2, 0))):
        expected = 0.5 * (points[nodes.cells[:, first]] + points[nodes.cells[:, second]])
        worst = max(worst, float(np.abs(points[permuted[:, midside]] - expected).max()))
    assert worst > 0.1, "a permutation of the midside nodes must be detectable"


# -- exactness ----------------------------------------------------------------


def test_ver33_a_quadratic_survives_the_export_exactly_on_the_whole_domain(
    exported: FieldExport,
) -> None:
    """``phi_V`` read back equals its polynomial at the file's own coordinates."""
    import numpy as np

    grid = _read(exported, OMEGA_STEM)
    x, y = grid.points[:, 0], grid.points[:, 1]
    expected = NONDIMENSIONAL["potential"](x, y) * _scales(exported).potential_V
    assert np.abs(grid.point_data["phi_V"] - expected).max() < EXACT_NM


def test_ver33_a_quadratic_survives_the_export_exactly_on_the_fluid(
    exported: FieldExport,
) -> None:
    """The fluid-restricted fields are exact too — including at interface nodes.

    This is the assertion the module docstring's carrier exists for. Evaluating a
    ``definedon``-restricted space directly returns zero wherever the mesh's point
    search lands in a solid element, which on this mesh it does at 16 of the 208
    fluid nodes; the error there is the field's own magnitude, not a round-off.
    """
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
    """A P1 function written at P2 nodes: the midpoint value is the endpoint mean.

    NUM-01 puts ``p`` one order below the velocity, and the export writes both on
    one node set. That is only lossless because a linear function's value at an
    edge midpoint *is* the average of its ends — so the assertion belongs here
    explicitly rather than being folded into the quadratic check.
    """
    import numpy as np

    grid = _read(exported, OMEGA_W_STEM)
    scales = _scales(exported)
    expected = _pressure(grid.points[:, 0], grid.points[:, 1]) * scales.pressure_Pa
    assert np.abs(grid.point_data["p_Pa"] - expected).max() < EXACT_NM * abs(scales.pressure_Pa)


# -- the split ----------------------------------------------------------------


def test_ver33_the_two_files_carry_the_whole_domain_and_fluid_field_sets(
    exported: FieldExport,
) -> None:
    """``phi`` over Omega; ``c_i``, ``u``, ``p`` and ``d`` over Omega_w, and no crossing."""
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
    """No membrane-only node appears in the Omega_w file (IF-07's no-padding rule).

    The interface nodes *are* fluid nodes and must be present; what must not be
    present is a node no fluid element touches, because a value written there
    could only be an invention.
    """
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


def test_ver33_the_velocity_is_written_as_a_three_component_vector(
    exported: FieldExport,
) -> None:
    """XDMF's ``Vector`` means three components; the third is ``u_theta`` = 0 (PHY-01)."""
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


# -- units --------------------------------------------------------------------


def _scales(export: FieldExport) -> Scales:
    """Return the scale set the file records, rebuilt from the file's own JSON."""
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
    """Return the HDF5 root attributes of one written pair."""
    import h5py

    path = export.omega[0].with_name(f"{stem}.h5")
    with h5py.File(path, "r") as handle:
        return {key: value for key, value in handle.attrs.items()}


def test_ver33_the_recorded_scale_set_is_the_one_the_state_was_solved_in(
    solution: ModelSolution, exported: FieldExport
) -> None:
    """Every defining input and derived scale of section 6.3, recoverable exactly."""
    recorded = json.loads(_metadata(exported, OMEGA_STEM)["scales"])
    assert recorded == solution.model.scales.summary()
    assert _metadata(exported, OMEGA_STEM)["coordinate_units"] == "nm"


def test_ver33_the_two_pi_of_the_axisymmetric_measure_is_absent(
    exported: FieldExport,
) -> None:
    """The pointwise values carry the SI scale and nothing else.

    Asserted as a ratio rather than as a difference, because the failure this
    guards against — section 6.7's ``2 pi`` applied a second time, here — is a
    constant factor that a plot cannot show and a tolerance would swallow.
    """
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


def test_ver33_the_wall_distance_is_written_in_nm_and_not_rescaled(
    exported: FieldExport,
) -> None:
    """``d`` is already in nm (PHY-02); a scale applied to it would be a second one."""
    import numpy as np

    grid = _read(exported, OMEGA_W_STEM)
    expected = NONDIMENSIONAL["wall_distance"](grid.points[:, 0], grid.points[:, 1])
    assert np.abs(grid.point_data["wall_distance_nm"] - expected).max() < EXACT_NM


# -- the container ------------------------------------------------------------


def test_ver33_the_topology_is_triangle_6_at_six_nodes_per_element(
    exported: FieldExport,
) -> None:
    """The XDMF says what IF-07 requires, read from the file rather than from meshio."""
    root = ET.parse(exported.omega[0]).getroot()
    topology = root.find("Domain/Grid/Topology")
    assert topology is not None
    assert topology.attrib["TopologyType"] == "Triangle_6"
    assert topology.attrib["NodesPerElement"] == "6"


def test_ver33_heavy_data_is_compressed(exported: FieldExport) -> None:
    """Every dataset in every heavy file is gzipped (IF-07).

    Not a preference: the reference mesh writes about 9.2 MB per solve, and
    WP11's envelope is 3 675 of them.
    """
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
    """A reader can tell which part of Omega it holds without decoding ``material_id``."""
    omega = _metadata(exported, OMEGA_STEM)
    omega_w = _metadata(exported, OMEGA_W_STEM)
    assert omega["schema"] == omega_w["schema"] == FIELDS_SCHEMA
    assert omega["domain"] == "omega"
    assert omega_w["domain"] == "omega_w"
    assert set(json.loads(omega["domain_materials"])) == {"electrolyte", "membrane", "cis", "trans"}
    assert set(json.loads(omega_w["domain_materials"])) == {"electrolyte", "cis", "trans"}


def test_if07_a_discontinuous_quantity_is_written_cell_centred(
    exported: FieldExport,
) -> None:
    """``eps_r`` and ``material_id`` jump across a material interface.

    Written node-centred, each would take one side of the jump arbitrarily and a
    viewer would draw a ramp across every boundary element. Cell-centred, the
    exported permittivity takes exactly the two values the model assigns.
    """
    import numpy as np

    grid = _read(exported, OMEGA_STEM)
    permittivity = np.concatenate(grid.cell_data["eps_r"])
    assert set(np.unique(permittivity)) == {3.2, 78.0}
    identifiers = np.concatenate(grid.cell_data["material_id"])
    assert identifiers.shape == (grid.cells[0].data.shape[0],)
    assert set(np.unique(identifiers)) == set(range(4))


def test_if07_a_material_selection_matching_nothing_is_refused_naming_the_mesh(
    mesh: Mesh,
) -> None:
    """QR-12: an empty selection would write an empty file rather than abort."""
    with pytest.raises(ValueError, match="no element of the mesh carries a material"):
        p2_nodes(mesh, materials="protein")


def test_if07_the_export_reports_every_path_and_attribute_it_wrote(
    exported: FieldExport,
) -> None:
    """The FR-25 manifest records the export by what it contains, not by a flag."""
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

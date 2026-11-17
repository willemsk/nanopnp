"""Charge on the mesh: the map, the deployed charge and the residue link carry the walk's record."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from nanopnp import Case, Session
from nanopnp.charge.stage import stored_lattice
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.gui.charge import charge_image
from nanopnp.gui.render import ChargeRequest, render_charge_elements
from nanopnp.gui.web.plane import deployed_layer
from nanopnp.io.store import Store
from nanopnp.pipeline.run import RunResult
from nanopnp.plot.data import ResidueCharges
from nanopnp.post.export import FIXED_CHARGE_ATTRIBUTE


@pytest.fixture(scope="module")
def walked(charged_tube, tmp_path_factory: pytest.TempPathFactory) -> RunResult:
    work = tmp_path_factory.mktemp("study-charge")
    case = charged_tube.write(work / "case")
    pqr = case.parent / "atoms.pqr"
    lines = pqr.read_text().splitlines()
    first, second = (n for n, line in enumerate(lines) if line.startswith("ATOM"))
    # The second atom in a residue of its own, so that a point on the map ranks one over the other.
    lines[second] = lines[second].replace("GLU A  18", "GLU A  19")
    assert lines[first] != lines[second]
    pqr.write_text("\n".join(lines) + "\n", encoding="utf-8")
    store = Store(work / "store", runs=work / "runs")
    return Session(store).run(Case.load(case), upto="charge")


def _volumes_m3(vertices_nm: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    # Each straight triangle's volume of revolution, 2 pi times its area times its mean r: a route
    # of its own, not the quadrature the means were taken with.
    corners = vertices_nm[triangles]
    edge_a, edge_b = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    area = 0.5 * np.abs(edge_a[:, 0] * edge_b[:, 1] - edge_a[:, 1] * edge_b[:, 0])
    return np.asarray(2.0 * math.pi * area * corners[:, :, 0].mean(axis=1) * 1e-27)


def test_ver60_the_studys_charge_on_the_mesh_shows_the_walks_record(walked, charged_tube) -> None:
    # A map, a mesh layer or a residue that disagrees with the record shows a charge the solve did
    # not assemble.
    recorded = walked.artefacts["charge"].summary["charge"]["conservation"]
    lattice = stored_lattice(walked.artefacts["charge"])
    assert lattice is not None
    assert charge_image(lattice).integral_e == pytest.approx(recorded["q_grid_e"], rel=1e-12)

    # The deployed charge, one r-weighted mean per element, keeps the charge the solve assembles.
    assert walked.directory is not None
    rendered = render_charge_elements(ChargeRequest(run=str(walked.directory), elements=True))
    layer = deployed_layer(Path(rendered.path))
    assert layer["bar"] == {"quantity": FIXED_CHARGE_ATTRIBUTE, "unit": "C/m^3"}
    assert layer["scale"] == [-rendered.limit, rendered.limit]
    vertices = np.reshape(layer["vertices_nm"], (-1, 2))
    triangles = np.reshape(layer["triangles"], (-1, 3))
    assert len(layer["values"]) == len(triangles) == rendered.elements
    mesh_e = float(np.dot(layer["values"], _volumes_m3(vertices, triangles))) / ELEMENTARY_CHARGE
    assert mesh_e == pytest.approx(recorded["q_mesh_e"], rel=1e-12)

    # Each charged atom's residue ranks first at the atom, and its marker sits where it was put.
    charges = ResidueCharges.of(
        walked.artefacts["protonation"], walked.artefacts["charge"], walked.resolved
    )
    assert charges is not None
    assert [(key, name) for key, name, _ in charges.residues()] == [
        ("A:18", "GLU"),
        ("A:19", "GLU"),
    ]
    for key, (_, x_A, y_A, _, q_e) in zip(("A:18", "A:19"), charged_tube.atoms, strict=True):
        ((r_nm, z_nm, charge_e),) = charges.markers(key)
        assert (r_nm, charge_e) == (pytest.approx(math.hypot(x_A, y_A) / 10.0), q_e)
        ranked = charges.at(r_nm, z_nm)
        assert ranked[0][0] == key
        assert math.copysign(1.0, ranked[0][1]) == math.copysign(1.0, q_e)

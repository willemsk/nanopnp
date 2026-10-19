"""VER-66, QR-14, IF-03, QR-11 — the backend registries (WP39)."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.cli import main
from nanopnp.core.errors import EXIT_CASE
from nanopnp.core.paths import profile_file
from nanopnp.io.case import CaseValidationError
from nanopnp.io.store import Store
from nanopnp.mesh import meshers
from nanopnp.mesh.adapter import read as read_mesh
from nanopnp.mesh.meshers import create_mesher, register_mesher
from nanopnp.numerics import linear
from nanopnp.numerics.linear import create_solver, register_solver
from nanopnp.physics import stabilisation as stabilisation_mod
from nanopnp.physics.stabilisation import (
    create as create_stabilisation,
)
from nanopnp.physics.stabilisation import (
    register as register_stabilisation,
)
from nanopnp.pipeline.case import loads_case
from nanopnp.pipeline.run import run_case, run_document

if TYPE_CHECKING:
    from nanopnp.geometry.region import RegionRecord
    from nanopnp.mesh.adapter import MeshData


class _StubMesher:
    def __init__(self, target: str = "netgen") -> None:
        self._inner = create_mesher(target)
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return "stub-mesher"

    def settings(self, *, exclusion: bool) -> dict[str, object]:
        self.calls.append("settings")
        return self._inner.settings(exclusion=exclusion)

    def mesh(
        self, record: RegionRecord, wall_h_nm: float, sizes: dict[str, float]
    ) -> tuple[MeshData, str]:
        self.calls.append("mesh")
        return self._inner.mesh(record, wall_h_nm, sizes)


class _StubSolver:
    def __init__(self, target: str = "umfpack") -> None:
        self._inner = create_solver(target)
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return "stub-solver"

    def solve(self, matrix: object, rhs: object, correction: object, freedofs: object) -> None:
        self.calls.append("solve")
        self._inner.solve(matrix, rhs, correction, freedofs)


class _StubStabilisation:
    def __init__(self, target: str = "none") -> None:
        self._inner = create_stabilisation(target)
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return "stub-mode"

    @property
    def parameters(self) -> Mapping[str, float]:
        return self._inner.parameters

    @property
    def provenance(self) -> Mapping[str, str]:
        return self._inner.provenance

    @property
    def terms(self) -> tuple[str, ...]:
        self.calls.append("terms")
        return self._inner.terms

    def flow_terms(self, *args: object, **kwargs: object) -> object:
        self.calls.append("flow_terms")
        return self._inner.flow_terms(*args, **kwargs)

    def transport_streamline(self, *args: object, **kwargs: object) -> object:
        self.calls.append("transport_streamline")
        return self._inner.transport_streamline(*args, **kwargs)

    def transport_crosswind(self, *args: object, **kwargs: object) -> object:
        self.calls.append("transport_crosswind")
        return self._inner.transport_crosswind(*args, **kwargs)

    def indicator_term(self, *args: object, **kwargs: object) -> object:
        self.calls.append("indicator_term")
        return self._inner.indicator_term(*args, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)


@pytest.fixture
def registered_stubs() -> Iterator[tuple[_StubMesher, _StubSolver, _StubStabilisation]]:
    mesher = _StubMesher("netgen")
    solver = _StubSolver("umfpack")
    stabilisation = _StubStabilisation("none")

    # Registered inside the ``try``, so that one refused registration cannot
    # leave the others behind for the rest of the session, where the exact
    # registered tuples of ``test_linear_solver.py`` would then fail.
    try:
        register_mesher("stub-mesher", lambda: mesher)
        register_solver("stub-solver", lambda: solver)
        register_stabilisation("stub-mode", lambda: stabilisation)
        yield mesher, solver, stabilisation
    finally:
        meshers._REGISTRY.pop("stub-mesher", None)
        linear._REGISTRY.pop("stub-solver", None)
        stabilisation_mod._REGISTRY.pop("stub-mode", None)


@pytest.fixture(scope="module")
def quickstart_pore_msh(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from nanopnp.mesh.adapter import from_ngsolve, write_msh41
    from nanopnp.mesh.primitives import CylindricalPoreGeometry

    generated = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=0.35, check_quality=False)
    return write_msh41(from_ngsolve(generated), tmp_path_factory.mktemp("pore") / "pore.msh")


def test_ver66_forwarding_solver_and_mode_agree_with_plain_run(
    registered_stubs: tuple[_StubMesher, _StubSolver, _StubStabilisation],
    quickstart_pore_msh: Path,
    tmp_path: Path,
) -> None:
    import numpy as np

    _, stub_solver, stub_mode = registered_stubs

    def make_case(solver_name: str, mode_name: str) -> str:
        return f"""\
schema: nanopnp/case/v0.5
name: ver66-comparison
inputs:
  mesh: {{path: {quickstart_pore_msh}, format: msh41, groups: {{default: interface}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics:
  model: pnp
  flow: false
  variable_density: false
  inertia: false
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: none
  linear: {{solver: {solver_name}}}
  stabilisation: {mode_name}
"""

    plain_dir = tmp_path / "plain"
    stub_dir = tmp_path / "stub"
    plain_dir.mkdir()
    stub_dir.mkdir()

    plain_path = plain_dir / "case.yaml"
    stub_path = stub_dir / "case.yaml"
    plain_path.write_text(make_case("umfpack", "none"), encoding="utf-8")
    stub_path.write_text(make_case("stub-solver", "stub-mode"), encoding="utf-8")

    plain_res = run_case(
        plain_path,
        store=Store(plain_dir / "store"),
        workspace=plain_dir / "work",
    )
    stub_res = run_case(
        stub_path,
        store=Store(stub_dir / "store"),
        workspace=stub_dir / "work",
    )

    assert len(stub_solver.calls) > 0, "stub solver was not invoked"
    assert "solve" in stub_solver.calls
    assert len(stub_mode.calls) > 0, "stub stabilisation mode was not invoked"

    with (
        np.load(plain_res.artefacts["solve"].payload["state"], allow_pickle=False) as a_plain,
        np.load(stub_res.artefacts["solve"].payload["state"], allow_pickle=False) as a_stub,
    ):
        plain_fields = {k: a_plain[k] for k in a_plain.files if k.startswith("field.")}
        stub_fields = {k: a_stub[k] for k in a_stub.files if k.startswith("field.")}
        assert sorted(plain_fields) == sorted(stub_fields)
        for key in plain_fields:
            assert np.array_equal(plain_fields[key], stub_fields[key]), f"field {key} differed"


# VER-52
def test_ver66_forwarding_mesher_agrees_with_netgen_on_supplied_profile(
    registered_stubs: tuple[_StubMesher, _StubSolver, _StubStabilisation],
    tmp_path: Path,
) -> None:
    import numpy as np

    stub_mesher, _, _ = registered_stubs
    fixture_path = profile_file("clya_reference_profile")

    def make_profile_case(backend_name: str) -> str:
        return f"""\
schema: nanopnp/case/v0.5
name: ver66-profile
inputs:
  profile: {{path: {fixture_path}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics:
  mesh: {{backend: {backend_name}}}
"""

    netgen_dir = tmp_path / "netgen_walk"
    stub_dir = tmp_path / "stub_walk"
    netgen_dir.mkdir()
    stub_dir.mkdir()

    netgen_text = make_profile_case("netgen")
    stub_text = make_profile_case("stub-mesher")
    netgen_res = run_document(
        loads_case(netgen_text),
        case_text=netgen_text,
        upto="mesh",
        store=Store(netgen_dir / "store"),
        workspace=netgen_dir / "work",
    )
    stub_res = run_document(
        loads_case(stub_text),
        case_text=stub_text,
        upto="mesh",
        store=Store(stub_dir / "store"),
        workspace=stub_dir / "work",
    )

    assert "mesh" in stub_mesher.calls
    assert "settings" in stub_mesher.calls

    assert stub_res.artefacts["mesh"].parameters["sizing"]["backend"] == "stub-mesher"
    assert netgen_res.artefacts["mesh"].parameters["sizing"]["backend"] == "netgen"

    netgen_data = read_mesh(netgen_res.artefacts["mesh"].payload["mesh"], format="msh41")
    stub_data = read_mesh(stub_res.artefacts["mesh"].payload["mesh"], format="msh41")

    np.testing.assert_array_equal(stub_data.vertices, netgen_data.vertices)
    np.testing.assert_array_equal(stub_data.triangles, netgen_data.triangles)


def test_ver66_an_unregistered_rejected_solver_is_refused_naming_num21(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    fixture_path = profile_file("clya_reference_profile")
    case_text = f"""\
schema: nanopnp/case/v0.5
name: rejected-solver
inputs:
  profile: {{path: {fixture_path}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics:
  linear: {{solver: mumps}}
"""
    expected = (
        "numerics.linear.solver 'mumps' is not usable: MUMPS is absent from the NGSolve wheel"
    )
    with pytest.raises(CaseValidationError) as caught:
        loads_case(case_text)
    assert expected in str(caught.value)
    assert "NUM-21" in str(caught.value)
    case_file = tmp_path / "case.yaml"
    case_file.write_text(case_text, encoding="utf-8")
    assert main(["validate", "case", str(case_file)]) == EXIT_CASE
    assert expected in capsys.readouterr().err


def test_ver66_registered_meshers_in_fresh_process_imports_no_backend() -> None:
    code = (
        "import sys, json\n"
        "from nanopnp.mesh.meshers import registered_meshers\n"
        "meshers = registered_meshers()\n"
        "assert 'gmsh' in meshers\n"
        "assert 'netgen' in meshers\n"
        "prohibited = ('gmsh', 'nanopnp.mesh.gmsh_backend', 'netgen', 'ngsolve')\n"
        "imported = [m for m in prohibited if m in sys.modules]\n"
        "print(json.dumps(imported))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    imported = json.loads(proc.stdout)
    assert imported == []

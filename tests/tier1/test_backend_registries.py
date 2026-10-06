"""VER-66, QR-14, IF-03, QR-11 — the backend registries (WP39).

Verifies that mesher, linear solver and stabilisation choices operate as uniform
registries that can be extended by external backends without touching solver or
pipeline code, and that unregistered names are refused consistently across
the document validator, the desktop editor and the CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.cli import main
from nanopnp.core.errors import EXIT_CASE, EXIT_OK
from nanopnp.core.paths import profile_file
from nanopnp.gui.case_model import CaseEditor
from nanopnp.io.case import CaseDocument, CaseValidationError
from nanopnp.io.store import Store
from nanopnp.mesh import meshers
from nanopnp.mesh.adapter import read as read_mesh
from nanopnp.mesh.generate import sizing_parameters
from nanopnp.mesh.meshers import create_mesher, register_mesher
from nanopnp.mesh.sizing import SIZES, WallSize
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
from nanopnp.pipeline.checks import check_document
from nanopnp.pipeline.run import run_case, run_document

if TYPE_CHECKING:
    from nanopnp.geometry.region import RegionRecord
    from nanopnp.mesh.adapter import MeshData


# -- Stub backend implementations ----------------------------------------------


class _StubMesher:
    """A mesher delegating to Netgen while recording invocations."""

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
    """A linear solver delegating to UMFPACK while recording invocations."""

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
    """A stabilisation mode delegating to 'none' while recording invocations."""

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
    """Register stub mesher, solver and stabilisation mode for one test."""
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
    """Generate the quick-start pore mesh using NGSolve."""
    from nanopnp.mesh.adapter import from_ngsolve, write_msh41
    from nanopnp.mesh.primitives import CylindricalPoreGeometry

    generated = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=0.35, check_quality=False)
    return write_msh41(from_ngsolve(generated), tmp_path_factory.mktemp("pore") / "pore.msh")


# -- Verification tests --------------------------------------------------------


def test_ver66_stubs_validate_and_appear_in_editor_options(
    registered_stubs: tuple[_StubMesher, _StubSolver, _StubStabilisation],
    tmp_path: Path,
) -> None:
    """A stub mesher, solver and mode validate in a case and are offered by the editor."""
    fixture_path = profile_file("clya_reference_profile")
    case_text = f"""\
schema: nanopnp/case/v2
name: stub-validation-case
inputs:
  profile: {{path: {fixture_path}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics:
  mesh: {{backend: stub-mesher}}
  linear: {{solver: stub-solver}}
  stabilisation: stub-mode
"""
    case_file = tmp_path / "case.yaml"
    case_file.write_text(case_text, encoding="utf-8")

    document = loads_case(case_text)
    assert isinstance(document, CaseDocument)
    checked = check_document(document)
    assert checked is document

    # CLI validate case command
    code = main(["validate", "case", str(case_file)])
    assert code == EXIT_OK

    # Desktop editor options
    editor = CaseEditor.open(case_file)
    assert "stub-mesher" in (editor.state("numerics.mesh.backend").options or ())
    assert "stub-solver" in (editor.state("numerics.linear.solver").options or ())
    assert "stub-mode" in (editor.state("numerics.stabilisation").options or ())
    assert editor.problems() is None


def test_ver66_forwarding_solver_and_mode_agree_with_plain_run(
    registered_stubs: tuple[_StubMesher, _StubSolver, _StubStabilisation],
    quickstart_pore_msh: Path,
    tmp_path: Path,
) -> None:
    """On the quickstart pore, stub solver and mode match plain run bitwise and log calls."""
    import numpy as np

    _, stub_solver, stub_mode = registered_stubs

    def make_case(solver_name: str, mode_name: str) -> str:
        return f"""\
schema: nanopnp/case/v2
name: ver66-comparison
inputs:
  mesh: {{path: {quickstart_pore_msh}, format: msh41, groups: {{default: interface}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: pnp, flow: false, solid_permittivities: {{membrane: 3.2}}}}
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

    # Both stubs recorded invocations
    assert len(stub_solver.calls) > 0, "stub solver was not invoked"
    assert "solve" in stub_solver.calls
    assert len(stub_mode.calls) > 0, "stub stabilisation mode was not invoked"

    # Bitwise array equality of solved state fields
    with (
        np.load(plain_res.artefacts["solve"].payload["state"], allow_pickle=False) as a_plain,
        np.load(stub_res.artefacts["solve"].payload["state"], allow_pickle=False) as a_stub,
    ):
        plain_fields = {k: a_plain[k] for k in a_plain.files if k.startswith("field.")}
        stub_fields = {k: a_stub[k] for k in a_stub.files if k.startswith("field.")}
        assert sorted(plain_fields) == sorted(stub_fields)
        for key in plain_fields:
            assert np.array_equal(plain_fields[key], stub_fields[key]), f"field {key} differed"


def test_ver66_forwarding_mesher_agrees_with_netgen_on_supplied_profile(
    registered_stubs: tuple[_StubMesher, _StubSolver, _StubStabilisation],
    tmp_path: Path,
) -> None:
    """The VER-52 fixture walked to mesh with stub mesher reproduces Netgen exactly."""
    import numpy as np

    stub_mesher, _, _ = registered_stubs
    fixture_path = profile_file("clya_reference_profile")

    def make_profile_case(backend_name: str) -> str:
        return f"""\
schema: nanopnp/case/v2
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

    # Invocations recorded
    assert "mesh" in stub_mesher.calls
    assert "settings" in stub_mesher.calls

    # Recipe names the stub
    assert stub_res.artefacts["mesh"].parameters["sizing"]["backend"] == "stub-mesher"
    assert netgen_res.artefacts["mesh"].parameters["sizing"]["backend"] == "netgen"

    # Mesh geometry bitwise identical
    netgen_data = read_mesh(netgen_res.artefacts["mesh"].payload["mesh"], format="msh41")
    stub_data = read_mesh(stub_res.artefacts["mesh"].payload["mesh"], format="msh41")

    np.testing.assert_array_equal(stub_data.vertices, netgen_data.vertices)
    np.testing.assert_array_equal(stub_data.triangles, netgen_data.triangles)


@pytest.mark.parametrize(
    ("path", "unregistered_value", "expected_fragment"),
    [
        (
            "numerics.mesh.backend",
            "nonexistent_mesher",
            (
                "numerics.mesh.backend 'nonexistent_mesher' is not a registered mesher; "
                "the meshers are"
            ),
        ),
        (
            "numerics.linear.solver",
            "nonexistent_solver",
            "numerics.linear.solver 'nonexistent_solver' is not available; the solvers are",
        ),
        (
            "numerics.stabilisation",
            "nonexistent_mode",
            (
                "numerics.stabilisation 'nonexistent_mode' is not a registered mode; "
                "the available modes are"
            ),
        ),
    ],
)
def test_ver66_unregistered_name_is_refused_consistently_cli_and_editor(
    path: str,
    unregistered_value: str,
    expected_fragment: str,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """An unregistered name for each key is refused with identical text in CLI and editor."""
    fixture_path = profile_file("clya_reference_profile")
    base_case = f"""\
schema: nanopnp/case/v2
name: unregistered-test
inputs:
  profile: {{path: {fixture_path}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics:
  mesh: {{backend: netgen}}
  linear: {{solver: umfpack}}
  stabilisation: none
"""
    base_file = tmp_path / "base_case.yaml"
    base_file.write_text(base_case, encoding="utf-8")

    # Desktop editor check
    editor = CaseEditor.open(base_file)
    editor.stage(path, unregistered_value)
    with pytest.raises(CaseValidationError):
        editor.commit()
    editor_problems = editor.problems()
    assert expected_fragment in editor_problems

    # Document validation through loads_case
    defaults = {
        "numerics.mesh.backend": "netgen",
        "numerics.linear.solver": "umfpack",
        "numerics.stabilisation": "none",
    }
    values = {**defaults, path: unregistered_value}
    bad_case_text = f"""\
schema: nanopnp/case/v2
name: unregistered-test
inputs:
  profile: {{path: {fixture_path}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics:
  mesh: {{backend: {values["numerics.mesh.backend"]}}}
  linear: {{solver: {values["numerics.linear.solver"]}}}
  stabilisation: {values["numerics.stabilisation"]}
"""
    bad_file = tmp_path / f"bad_{path.replace('.', '_')}.yaml"
    bad_file.write_text(bad_case_text, encoding="utf-8")

    with pytest.raises(CaseValidationError) as exc_info:
        loads_case(bad_case_text)
    assert expected_fragment in str(exc_info.value)

    # Command line validation via main
    code = main(["validate", "case", str(bad_file)])
    assert code == EXIT_CASE
    captured = capsys.readouterr()
    assert expected_fragment in captured.err


def test_ver66_an_unregistered_rejected_solver_is_refused_naming_num21(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """``mumps``, unregistered, is refused with NUM-21's reason, not as merely unknown (D3, D7)."""
    fixture_path = profile_file("clya_reference_profile")
    case_text = f"""\
schema: nanopnp/case/v2
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


def test_ver66_a_mesher_naming_a_common_recipe_entry_is_refused() -> None:
    """A mesher's settings cannot overwrite the recipe entries every backend shares (D2)."""

    class Clashing:
        name = "clashing"

        def settings(self, *, exclusion: bool = False) -> dict[str, object]:
            return {"backend": "netgen", "optsteps2d": 5}

    register_mesher("clashing", Clashing)  # type: ignore[arg-type]
    try:
        wall = WallSize(wall_h_nm=0.1, source="explicit", debye_length_nm=0.5, size_scale=1.0)
        with pytest.raises(ValueError, match="mesher 'clashing' returns settings backend"):
            sizing_parameters(wall, SIZES, "clashing")
    finally:
        meshers._REGISTRY.pop("clashing", None)


def test_ver66_registered_meshers_in_fresh_process_imports_no_backend() -> None:
    """In a fresh process, registered_meshers() holds 'gmsh' without importing backend modules."""
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

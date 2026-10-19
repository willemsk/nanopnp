"""VER-43 and VER-44: the shell's view-models, asserted where Qt cannot be built."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

VOCABULARY = (
    "epnp-ns",
    "pnp-ns",
    "willems2020_nacl",
    "borukhov",
    "umfpack",
    "superlu",
    "no_slip",
    "supg",
    "taubin",
    '"propka"',
    "'propka'",
    "CHARMM",
    "PEOEPB",
    "SWANSON",
    "phi_V",
    "u_m_s",
    "p_Pa",
    "mol_m3",
    "profile1",
    '"hand-edit"',
    "rho_fixed_C_m3",
)


# CON-09, VER-55, CON-10, VER-60
def test_if09_the_view_models_import_no_qt_and_no_ngsolve() -> None:
    probe = (
        "import sys;"
        "import nanopnp.gui.case_model, nanopnp.gui.run_model,"
        " nanopnp.gui.solver, nanopnp.gui.probe,"
        " nanopnp.gui.convergence, nanopnp.gui.scene, nanopnp.gui.render,"
        " nanopnp.gui.geometry, nanopnp.gui.assess, nanopnp.gui.charge;"
        "print(sorted(m for m in ('PySide6','PyQt5','PyQt6','ngsolve','netgen',"
        " 'MDAnalysis','skimage','shapely','gmsh','pdb2pqr','propka') if m in sys.modules))"
    )
    found = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    assert found.stdout.strip() == "[]", found.stdout


def _without_payloads(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        targets = (
            [node.target]
            if isinstance(node, ast.AnnAssign)
            else node.targets
            if isinstance(node, ast.Assign)
            else []
        )
        if any(isinstance(target, ast.Name) and target.id == "PAYLOADS" for target in targets):
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return source.replace(segment, "")
    return source


# FR-25
def test_if09_no_option_list_is_written_in_the_shell() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "nanopnp" / "gui"
    offenders = {
        f"{path.relative_to(root)}: {value}"
        for path in root.rglob("*.py")
        for value in VOCABULARY
        if value in _without_payloads(path.read_text(encoding="utf-8"))
    }
    assert not offenders, (
        f"{sorted(offenders)} name case-file values inside gui/; every enumeration must come "
        "from the schema or from a live registry, through nanopnp.pipeline.checks.options_at"
    )

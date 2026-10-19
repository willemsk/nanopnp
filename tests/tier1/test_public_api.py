"""VER-45: the public surface of nanopnp (IF-01, the section 3.1 public-surface NOTE)."""

from __future__ import annotations

import json
import subprocess
import sys


def test_ver45_import_nanopnp_imports_no_solver_and_no_numpy() -> None:
    code = (
        "import sys, json\n"
        "import nanopnp\n"
        "dir(nanopnp)\n"
        "heavy = ('ngsolve', 'netgen', 'numpy')\n"
        "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in heavy)))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []

"""VER-43 — the packaging probe carries the payloads RSK-13 is about.

§8.2.1 amendment A4 names the import set rather than leaving it to the builder,
because a probe omitting Qt WebEngine would retire RSK-13 without exercising the
dependency most likely to defeat packaging. This module holds that amendment to
the code: :data:`~nanopnp.gui.probe.PAYLOADS` is checked against the amendment,
and the module's own ``import`` statements are checked against
:data:`~nanopnp.gui.probe.PAYLOADS`.

Reading the source rather than the constant is the point. A declared set nothing
compares against the code is a comment; parsed, a payload dropped from the probe
fails here instead of shipping a bundle that proves less than it claims.

Nothing here constructs a Qt object, or imports one: ``PySide6.QtWidgets`` does
not import at all on the Linux push gate (`.knowledge/07-software-stack.md` §5),
and this test runs there.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from nanopnp.gui import probe
from nanopnp.gui.probe import LICENCE_NOTICE_FILENAME, PAYLOADS, licence_notice

AMENDED_PAYLOAD_SET = frozenset(
    {
        "PySide6.QtWidgets",
        "PySide6.QtWebEngineWidgets",
        "ngsolve",
        "netgen",
        "ngsolve.webgui",
    }
)
"""The import set §8.2.1 amendment A4 names, written out from the specification."""

BINARY_ROOTS = frozenset({"PySide6", "ngsolve", "netgen"})
"""Top-level packages whose payloads are compiled and have to be bundled."""


def _runtime_imports(source: Path) -> set[str]:
    """Return every module a file imports at run time, by dotted name.

    ``if TYPE_CHECKING:`` blocks are skipped: an annotation-only import is not a
    payload, and counting one would let the probe claim a dependency it never
    loads.
    """
    tree = ast.parse(source.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.dump(node.test):
            # Blank the guarded body so ``ast.walk`` does not reach it.
            node.body = []
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            found.add(node.module)
            found |= {f"{node.module}.{alias.name}" for alias in node.names}
    return found


def test_rsk13_the_probe_names_the_payloads_it_must_carry() -> None:
    """``PAYLOADS`` is amendment A4's set, and the module imports every member."""
    assert frozenset(PAYLOADS) == AMENDED_PAYLOAD_SET

    imported = _runtime_imports(Path(probe.__file__))
    missing = sorted(payload for payload in PAYLOADS if payload not in imported)
    assert not missing, (
        f"{missing} are declared in nanopnp.gui.probe.PAYLOADS but the module does not import "
        "them at run time, so the bundle would not be forced to carry them (RSK-13, §8.2.1 A4)"
    )


def test_rsk13_the_probe_imports_no_undeclared_binary_payload() -> None:
    """Nothing outside the declared payloads' own packages is imported.

    The other direction: a compiled package the probe loads but does not declare
    is one the bundle has to carry and amendment A4 never promised, so the next
    reader of ``PAYLOADS`` would be reading a stale list. It is also how CON-09's
    "PyQt SHALL NOT be used" and CON-10's gmsh rule are enforced on the one
    module that links a toolkit — an ``import PyQt6`` here would ship a GPL-3
    library inside an LGPL bundle.
    """
    third_party = {
        name.split(".")[0]
        for name in _runtime_imports(Path(probe.__file__))
        if name.split(".")[0] not in sys.stdlib_module_names and name.split(".")[0] != "nanopnp"
    }
    declared = {payload.split(".")[0] for payload in PAYLOADS}
    assert third_party == declared, (
        f"the probe imports {sorted(third_party)}; amendment A4 declares {sorted(declared)}"
    )


def test_con11_the_licence_notice_states_the_bundle_licence() -> None:
    """The notice names every obligation the bundle carries, and its own licence.

    CON-11: the bundle defaults to UMFPACK, which is GPL-2+, so the bundle as a
    whole is distributed under GPL-2+ while the library stays BSD-3, and the
    notice "SHALL state them". Asserted on the shipped file rather than on prose
    in a plan, because it is the file that travels with the bundle.
    """
    notice = licence_notice()
    assert notice.name == LICENCE_NOTICE_FILENAME
    text = notice.read_text(encoding="utf-8")
    for obligation in ("BSD-3-Clause", "LGPL-2.1", "LGPL-3", "GPL-2+"):
        assert obligation in text, f"the bundle licence notice does not name {obligation}"
    assert "This bundle is distributed under" in text
    assert "UMFPACK" in text and "BSD-3-Clause" in text

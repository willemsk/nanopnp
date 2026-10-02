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

WP31 adds PDB2PQR and PROPKA (VER-60, D14). Their exercise runs here unfrozen, as
the frozen ``--selftest`` runs it on ``windows-latest``, and it is made to fail
twice, once naming each payload.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from nanopnp.charge import protonation
from nanopnp.charge.pqr import chain_characters
from nanopnp.core.paths import STRUCTURES_DIR, structure_file
from nanopnp.gui import probe
from nanopnp.gui.probe import (
    FRAGMENT,
    FRAGMENT_Q_NET_E,
    LICENCE_NOTICE_FILENAME,
    PAYLOADS,
    PayloadError,
    exercise_payloads,
    licence_notice,
)
from nanopnp.io.case import ResolvedProtonation

AMENDED_PAYLOAD_SET = frozenset(
    {
        "PySide6.QtWidgets",
        "PySide6.QtWebEngineWidgets",
        "ngsolve",
        "netgen",
        "ngsolve.webgui",
        # WP24 D16, D17: the geometry pipeline's compiled payloads, and Gmsh (B8).
        "MDAnalysis",
        "gemmi",
        "skimage.measure",
        "shapely.geometry",
        "gmsh",
        # WP31 D14: stage 7's protonation, pure Python with data trees.
        "pdb2pqr",
        "propka",
    }
)
"""The import set §8.2.1 amendment A4 names, written out from the specification."""

NOTICE_NAMES = {
    "PySide6": "PySide6",
    "ngsolve": "NGSolve",
    "netgen": "Netgen",
    "MDAnalysis": "MDAnalysis",
    "gemmi": "gemmi",
    "skimage": "scikit-image",
    "shapely": "Shapely",
    "gmsh": "Gmsh",
    "pdb2pqr": "PDB2PQR",
    "propka": "PROPKA",
}
"""Each payload's top-level package, by the name the CON-11 notice gives its row."""

BINARY_ROOTS = frozenset(
    {"PySide6", "ngsolve", "netgen", "MDAnalysis", "gemmi", "skimage", "shapely", "gmsh"}
)
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


def test_ver60_the_notice_has_a_row_for_each_payload() -> None:
    """Every payload the bundle carries has a row in the CON-11 notice's table (WP31 D15)."""
    assert set(NOTICE_NAMES) == {payload.split(".")[0] for payload in PAYLOADS}
    rows = [
        line.split("|")[1]
        for line in licence_notice().read_text(encoding="utf-8").splitlines()
        if line.startswith("| ")
    ]
    unlisted = sorted(
        name for name in NOTICE_NAMES.values() if not any(name in row for row in rows)
    )
    assert not unlisted, f"the bundle licence notice has no row for {unlisted}"


def test_ver60_the_shipped_fragment_is_the_deposited_one(
    fragment_2wcd: Callable[..., object],
) -> None:
    """The probe's structure is what the stage gives PDB2PQR for ``GLU 18``-``LEU 26`` (D14).

    Its atom records are :func:`~nanopnp.charge.protonation.frame_pdb`'s bytes
    for the fragment cut from the vendored 2WCD, so ``FRAGMENT_Q_NET_E`` is about
    the fragment `.knowledge/07` section 3 measured, and an unknown name is refused
    rather than handed to PDB2PQR, which would fetch it.
    """
    ensemble = fragment_2wcd(18, 26)
    heavy = np.flatnonzero(np.char.upper(ensemble.element.astype(str)) != "H")  # type: ignore[attr-defined]
    written = protonation.frame_pdb(
        ensemble,  # type: ignore[arg-type]
        0,
        heavy,
        chain_characters(ensemble.chain.tolist()),  # type: ignore[attr-defined]
    ).decode("ascii")
    shipped = structure_file(FRAGMENT).read_text(encoding="ascii")
    assert [line for line in shipped.splitlines() if not line.startswith("REMARK")] == (
        written.splitlines()
    )
    with pytest.raises(FileNotFoundError, match="2wcd-not-shipped") as refused:
        structure_file("2wcd-not-shipped")
    assert str(STRUCTURES_DIR) in str(refused.value)


pdb2pqr_installed = pytest.mark.skipif(
    not all(importlib.util.find_spec(name) for name in ("pdb2pqr", "propka")),
    reason="the structure extra carries PDB2PQR and PROPKA",
)


@pdb2pqr_installed
def test_ver60_the_probe_protonates_the_fragment_at_both_ph_values() -> None:
    """The unfrozen exercise reports the fragment's ``Q_net`` at pH 2 and pH 8 (D14)."""
    assert FRAGMENT_Q_NET_E == {2.0: 0.0, 8.0: -3.0}
    report = exercise_payloads({"pdb2pqr"})
    assert list(report) == ["pdb2pqr"]
    assert f"protonated {FRAGMENT}, +0 e at pH 2, -3 e at pH 8" in report["pdb2pqr"]


@pdb2pqr_installed
def test_ver60_a_missing_data_tree_fails_naming_pdb2pqr(monkeypatch: pytest.MonkeyPatch) -> None:
    """With PDB2PQR's data lookup stubbed to raise, the exercise names PDB2PQR.

    The lookup is where a bundle without ``pdb2pqr/dat/`` fails: PDB2PQR finds
    its force-field files through ``Path(__file__).parent``.
    """
    import pdb2pqr.io

    def absent(name: str, type_: str = "DAT") -> Path:
        raise FileNotFoundError(f"Unable to find {type_} file for {name}")

    monkeypatch.setattr(pdb2pqr.io, "test_for_file", absent)
    with pytest.raises(PayloadError) as failed:
        exercise_payloads({"pdb2pqr"})
    assert failed.value.payload == "pdb2pqr"
    assert "Unable to find" in str(failed.value)


@pdb2pqr_installed
def test_ver60_charges_that_ignore_the_ph_fail_naming_propka(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the titration arguments removed, PDB2PQR runs and the exercise names PROPKA.

    Without a titration method the pH reaches nothing, so both runs give the
    standard states' charges: what a bundle that lost ``propka.cfg``, and with it
    the titration, would look like if PDB2PQR carried on without it.
    """
    arguments = protonation.pdb2pqr_arguments

    def untitrated(settings: ResolvedProtonation) -> tuple[str, ...]:
        return tuple(
            flag
            for flag in arguments(settings)
            if not flag.startswith(("--with-ph", "--titration-state-method"))
        )

    monkeypatch.setattr(protonation, "pdb2pqr_arguments", untitrated)
    with pytest.raises(PayloadError) as failed:
        exercise_payloads({"pdb2pqr"})
    assert failed.value.payload == "propka"
    assert "at every pH" in str(failed.value)


@pdb2pqr_installed
def test_ver60_a_missing_parameter_file_fails_naming_propka(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With PROPKA's ``propka.cfg`` out of reach, the exercise names PROPKA, not PDB2PQR.

    PROPKA looks for it beside its own modules, at ``Path(__file__).parent``, as a
    bundle that dropped the file would have it look. The exception surfaces out of
    PDB2PQR's run, and the exercise names the library whose code raised it. A frozen
    bundle with the file removed failed this way (`.knowledge/07` section 5).
    """
    import propka.input
    import propka.lib

    monkeypatch.setattr(propka.input, "__file__", str(tmp_path / "input.py"))
    monkeypatch.setattr(propka.lib, "__file__", str(tmp_path / "lib.py"))
    with pytest.raises(PayloadError) as failed:
        exercise_payloads({"pdb2pqr"})
    assert failed.value.payload == "propka"
    assert "propka.cfg" in str(failed.value)

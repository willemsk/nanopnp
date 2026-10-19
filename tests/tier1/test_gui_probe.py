"""VER-43: the packaging probe carries the payloads RSK-13 is about."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from nanopnp.charge import protonation
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
from nanopnp.io.resolved import ResolvedProtonation

AMENDED_PAYLOAD_SET = frozenset(
    {
        "PySide6.QtWidgets",
        "PySide6.QtWebEngineWidgets",
        "ngsolve",
        "netgen",
        "ngsolve.webgui",
        "MDAnalysis",
        "gemmi",
        "skimage.measure",
        "shapely.geometry",
        "gmsh",
        "pdb2pqr",
        "propka",
    }
)

# CON-11
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


def _runtime_imports(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.dump(node.test):
            node.body = []
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            found.add(node.module)
            found |= {f"{node.module}.{alias.name}" for alias in node.names}
    return found


def test_rsk13_the_probe_names_the_payloads_it_must_carry() -> None:
    assert frozenset(PAYLOADS) == AMENDED_PAYLOAD_SET

    imported = _runtime_imports(Path(probe.__file__))
    missing = sorted(payload for payload in PAYLOADS if payload not in imported)
    assert not missing, (
        f"{missing} are declared in nanopnp.gui.probe.PAYLOADS but the module does not import "
        "them at run time, so the bundle would not be forced to carry them (RSK-13, §8.2.1 A4)"
    )


# CON-09, CON-10
def test_rsk13_the_probe_imports_no_undeclared_binary_payload() -> None:
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
    notice = licence_notice()
    assert notice.name == LICENCE_NOTICE_FILENAME
    text = notice.read_text(encoding="utf-8")
    for obligation in ("BSD-3-Clause", "LGPL-2.1", "LGPL-3", "GPL-2+"):
        assert obligation in text, f"the bundle licence notice does not name {obligation}"
    assert "This bundle is distributed under" in text
    assert "UMFPACK" in text and "BSD-3-Clause" in text


def test_ver60_the_notice_has_a_row_for_each_payload() -> None:
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


pdb2pqr_installed = pytest.mark.skipif(
    not all(importlib.util.find_spec(name) for name in ("pdb2pqr", "propka")),
    reason="the structure extra carries PDB2PQR and PROPKA",
)


@pdb2pqr_installed
def test_ver60_the_probe_protonates_the_fragment_at_both_ph_values() -> None:
    assert FRAGMENT_Q_NET_E == {2.0: 0.0, 8.0: -3.0}
    report = exercise_payloads({"pdb2pqr"})
    assert list(report) == ["pdb2pqr"]
    assert f"protonated {FRAGMENT}, +0 e at pH 2, -3 e at pH 8" in report["pdb2pqr"]


@pdb2pqr_installed
def test_ver60_charges_that_ignore_the_ph_fail_naming_propka(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

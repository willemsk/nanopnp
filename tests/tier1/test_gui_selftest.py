"""VER-43, VER-60, RSK-13: the self-test exercises the payloads an installation needs."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from nanopnp.charge import protonation
from nanopnp.cli import main as cli_main
from nanopnp.gui.web import selftest
from nanopnp.gui.web.selftest import (
    FRAGMENT,
    FRAGMENT_Q_NET_E,
    PAYLOADS,
    PayloadError,
    exercise_payloads,
)
from nanopnp.io.resolved import ResolvedProtonation

AMENDED_PAYLOAD_SET = frozenset(
    {
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


def test_rsk13_the_selftest_names_the_payloads_it_must_carry() -> None:
    assert frozenset(PAYLOADS) == AMENDED_PAYLOAD_SET

    imported = _runtime_imports(Path(selftest.__file__))
    missing = sorted(payload for payload in PAYLOADS if payload not in imported)
    assert not missing, (
        f"{missing} are declared in nanopnp.gui.web.selftest.PAYLOADS but the module does not "
        "import them at run time, so the self-test would pass without them"
    )


# CON-09, CON-10
def test_rsk13_the_selftest_imports_no_undeclared_binary_payload() -> None:
    third_party = {
        name.split(".")[0]
        for name in _runtime_imports(Path(selftest.__file__))
        if name.split(".")[0] not in sys.stdlib_module_names and name.split(".")[0] != "nanopnp"
    }
    declared = {payload.split(".")[0] for payload in PAYLOADS}
    assert third_party == declared, (
        f"the self-test imports {sorted(third_party)}; amendment A4 declares {sorted(declared)}"
    )


def test_ver43_a_hidden_ngsolve_fails_naming_ngsolve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "ngsolve", None)
    with pytest.raises(PayloadError) as failed:
        exercise_payloads({"ngsolve"})
    assert failed.value.payload == "ngsolve"


def test_ver43_a_served_renderer_of_other_bytes_fails_naming_ngsolve_webgui(
    tmp_path: Path,
) -> None:
    other = tmp_path / "webgui.js"
    other.write_text("// not the shipped renderer\n", encoding="utf-8")
    with pytest.raises(PayloadError) as failed:
        exercise_payloads({"ngsolve.webgui"}, renderer=other)
    assert failed.value.payload == "ngsolve.webgui"
    assert "not the shipped renderer" in str(failed.value)


def test_ver43_the_whole_selftest_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_main(["gui", "--selftest"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert any("served the shipped renderer" in line for line in printed)
    assert len(printed) == len([p for p in PAYLOADS if p not in ("netgen", "propka")]), printed


pdb2pqr_installed = pytest.mark.skipif(
    not all(importlib.util.find_spec(name) for name in ("pdb2pqr", "propka")),
    reason="the structure extra carries PDB2PQR and PROPKA",
)


@pdb2pqr_installed
def test_ver60_the_selftest_protonates_the_fragment_at_both_ph_values() -> None:
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

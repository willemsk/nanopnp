"""A golden's case identity names the charge stage 7 deposits and the ``chi`` it derives (VAL-03).

Section 8.2.5 E3 closes OPN-07: a deposited charge enters
:func:`~nanopnp.validation.comsol.case_identity` by its stage-7 recipe, the
protonation key and the kernel's physical parameters, and a derived ``chi`` by
its derivation parameters and the structure's key (WP34 D1, D3). The export
lattice's spacing and the element order are discretisation and stay out (D2).
On ``main`` before WP34, pH 5, 7.5 and 9 and ``sharpness`` 0.8 of example 06 all
gave ``8559ee13...``; the first test fails there.

The identity hashes the structure file's bytes and never reads its atoms, so
the deposited 2WCD stands in for example 06's prepared copy: these tests are
about which keys move the hash, not about what stage 1 makes of the file.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from nanopnp.core.hashing import content_hash
from nanopnp.io.case import ResolvedCase, load_case, resolve
from nanopnp.validation.comsol import (
    CASE_IDENTITY_SCHEMA,
    DISCRETISATION_KEYS,
    MODEL_OPTION_DISCRETISATION_KEYS,
    case_identity,
)

pytest.importorskip("MDAnalysis", reason="stage 1's key needs the structure extra")

ROOT = Path(__file__).resolve().parents[2]
DEPOSITED_2WCD = ROOT / "tests" / "data" / "structures" / "2wcd.pdb.gz"
EXAMPLE_06 = ROOT / "examples" / "06-pdb-to-mesh" / "2wcd.case.yaml"

Edit = Callable[[dict[str, Any]], None]


@pytest.fixture
def example_06(tmp_path: Path) -> Callable[..., ResolvedCase]:
    """Return a function resolving example 06 under an edit of its document."""
    structure = tmp_path / "2wcd.pdb.gz"
    shutil.copyfile(DEPOSITED_2WCD, structure)
    counter = iter(range(1_000))

    def _resolved(edit: Edit | None = None) -> ResolvedCase:
        document = yaml.safe_load(EXAMPLE_06.read_text(encoding="utf-8"))
        document["structure"]["source"]["path"] = str(structure)
        if edit is not None:
            edit(document)
        path = tmp_path / f"case-{next(counter)}.case.yaml"
        path.write_text(yaml.safe_dump(document), encoding="utf-8")
        return resolve(load_case(path))

    return _resolved


@pytest.fixture
def identity(example_06: Callable[..., ResolvedCase]) -> Callable[..., str]:
    """Return a function giving example 06's identity under an edit of its document."""

    def _identity(edit: Edit | None = None) -> str:
        return case_identity(example_06(edit))

    return _identity


def _charge(**keys: float) -> Edit:
    """Return an edit setting keys of the ``charge:`` block, dotted for ``smearing``."""

    def edit(document: dict[str, Any]) -> None:
        block = document.setdefault("charge", {})
        for key, value in keys.items():
            if key in ("sharpness", "grid_spacing_nm"):
                block.setdefault("smearing", {})[key] = value
            else:
                block[key] = value

    return edit


def _pqr(path: Path) -> Edit:
    """Return an edit supplying ``path`` as ``inputs.pqr``."""

    def edit(document: dict[str, Any]) -> None:
        document.setdefault("inputs", {})["pqr"] = {"path": str(path), "format": "pqr"}

    return edit


def _pqr_text(charge_e: float) -> str:
    """Return a one-atom PQR whose bytes depend on ``charge_e``."""
    return f"ATOM      1  N   MET A   1       0.000   0.000   0.000 {charge_e:7.4f} 1.8240\nEND\n"


def test_val03_case_identity_names_a_deposited_charge(
    identity: Callable[..., str], tmp_path: Path
) -> None:
    """VAL-03, E3: the protonation and the kernel move the identity; the discretisation does not."""
    default = identity()
    moved = {
        "pH 5": identity(_charge(ph=5.0)),
        "pH 7.5 (default)": default,
        "pH 9": identity(_charge(ph=9.0)),
        "sharpness 0.8": identity(_charge(sharpness=0.8)),
    }
    assert len(set(moved.values())) == len(moved), moved
    # D2: the export lattice and the element order are discretisation.
    assert identity(_charge(grid_spacing_nm=0.01)) == default

    def order(document: dict[str, Any]) -> None:
        document.setdefault("numerics", {})["elements"] = {"phi": "P1", "c": "P1"}

    assert identity(order) == default

    # The PQR's contents are the charge; where the file lives is not.
    first, second = tmp_path / "a" / "x.pqr", tmp_path / "b" / "x.pqr"
    other = tmp_path / "c" / "x.pqr"
    for path, text in (
        (first, _pqr_text(-0.3)),
        (second, _pqr_text(-0.3)),
        (other, _pqr_text(0.3)),
    ):
        path.parent.mkdir()
        path.write_text(text, encoding="utf-8")
    from_first = identity(_pqr(first))
    assert identity(_pqr(second)) == from_first
    assert identity(_pqr(other)) != from_first
    assert from_first != default


def test_val03_case_identity_names_a_derived_chi(identity: Callable[..., str]) -> None:
    """VAL-03, E3: ``dielectric_transition_nm`` moves a deriving case's identity (D3)."""
    sharp = identity()
    narrow = identity(_charge(dielectric_transition_nm=0.1))
    wide = identity(_charge(dielectric_transition_nm=0.2))
    assert len({sharp, narrow, wide}) == 3


def test_val03_identity_leaves_the_solve_provenance_alone(
    example_06: Callable[..., ResolvedCase],
) -> None:
    """VAL-03, VER-23, D5: ``fields.charge`` still means "supplied", and no solve key moves.

    The recipe is added to the identity's own record, never to the solve
    provenance every stage key is built from, so computing the identity leaves
    that provenance as it was.
    """
    resolved = example_06()
    before = content_hash(CASE_IDENTITY_SCHEMA, resolved.solve_provenance)
    assert resolved.deposits_charge
    case_identity(resolved)
    provenance = resolved.solve_provenance
    assert provenance["fields"] == {"charge": False, "eps_r": False}
    assert "deposited_charge" not in provenance
    assert "derived_eps_r" not in provenance
    assert content_hash(CASE_IDENTITY_SCHEMA, provenance) == before


def test_val03_non_producer_identity_is_unchanged() -> None:
    """D4: a case that neither supplies, deposits nor derives a field hashes as it did."""
    case = ROOT / "examples" / "01-quickstart" / "quickstart.case.yaml"
    resolved = resolve(load_case(case))
    assert not resolved.deposits_charge
    assert not resolved.derives_eps_r
    record: dict[str, object] = {
        key: value
        for key, value in resolved.solve_provenance.items()
        if key not in DISCRETISATION_KEYS
    }
    options = record["model_options"]
    assert isinstance(options, dict)
    record["model_options"] = {
        key: value
        for key, value in sorted(options.items())
        if key not in MODEL_OPTION_DISCRETISATION_KEYS
    }
    assert case_identity(resolved) == content_hash(CASE_IDENTITY_SCHEMA, record)

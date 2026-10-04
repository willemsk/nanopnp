"""A golden's case identity names the charge stage 7 deposits and the ``chi`` it derives (VAL-03).

Section 8.2.5 E3 closes OPN-07: a deposited charge enters
:func:`~nanopnp.validation.comsol.case_identity` by its stage-7 recipe, the
stage-1 and protonation keys' parameters and the kernel's, and a derived ``chi``
by its derivation parameters and the stage-1 key's parameters (WP34 D1, D3). The
export lattice's spacing and the element order are discretisation and stay out
(D2), and so do the protonation gates' tolerances, which move a verdict and
never a charge. A non-zero ion-exclusion offset is a physics switch and enters.
A finished run's identity is read from the artefacts the run recorded, never
from the files its case names now. pH 5, 7.5 and 9 and
``sharpness`` 0.8 of example 06 must not share one identity (the old value was
``8559ee13...``); the first test fails on a hash that ignores them.

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

from nanopnp.charge import protonation as protonation_module
from nanopnp.core.hashing import content_hash
from nanopnp.core.stages import create
from nanopnp.io.artefact import Artefact, StageInputs
from nanopnp.io.case import ResolvedCase, load_case, resolve
from nanopnp.io.store import Store
from nanopnp.validation import runs
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


def test_val03_identity_ignores_the_protonation_gate_tolerances(
    identity: Callable[..., str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """VAL-03: a gate tolerance moves whether a protonation is accepted, not the case.

    Tightening one must not give every depositing case a new identity, or every
    golden made before it would refuse every later run of the same physics.
    """
    default = identity()
    monkeypatch.setattr(protonation_module, "Q_NET_TOLERANCE_E", 1e-9)
    monkeypatch.setattr(protonation_module, "REGISTRATION_TOLERANCE_A", 1e-9)
    monkeypatch.setattr(protonation_module, "MINIMUM_CALPHA", 1)
    assert identity() == default
    assert identity(_charge(ph=5.0)) != default


def test_val03_case_identity_names_the_exclusion_shell(identity: Callable[..., str]) -> None:
    """VAL-03, FR-15: a non-zero ``exclusion_offset_nm`` moves the identity; 0 does not (D4)."""
    default = identity()
    assert identity(_charge(exclusion_offset_nm=0.0)) == default
    shells = {identity(_charge(exclusion_offset_nm=offset)) for offset in (0.2, 0.3)}
    assert len(shells) == 2
    assert default not in shells
    # The shell and the derived chi are two switches, and each moves the identity alone.
    both = identity(_charge(exclusion_offset_nm=0.3, dielectric_transition_nm=0.15))
    transition = identity(_charge(dielectric_transition_nm=0.15))
    assert len({default, both, transition, identity(_charge(exclusion_offset_nm=0.3))}) == 4


def _recorded(resolved: ResolvedCase) -> dict[str, Artefact]:
    """Return the stage-1 and protonation keys a run of ``resolved`` records."""
    structure = create("structure").key(StageInputs(case=resolved.document))
    protonation = create("protonation").key(
        StageInputs(case=resolved.document, upstream={"structure": structure})
    )
    return {"structure": structure, "protonation": protonation}


def test_val03_run_identity_is_read_from_the_recorded_artefacts(
    example_06: Callable[..., ResolvedCase], tmp_path: Path
) -> None:
    """VAL-03: a finished run's identity describes the structure it solved, from anywhere.

    Read from the recorded artefacts, the identity is the one the case gives
    before any run, and it stays so when the structure file has since gone or
    changed, where the case alone would refuse or move.
    """
    resolved = example_06()
    recorded = _recorded(resolved)
    expected = case_identity(resolved)
    assert case_identity(resolved, recorded=recorded) == expected
    for edit in (_charge(dielectric_transition_nm=0.15), _charge(exclusion_offset_nm=0.3)):
        changed = example_06(edit)
        assert case_identity(changed, recorded=_recorded(changed)) == case_identity(changed)

    structure = tmp_path / "2wcd.pdb.gz"
    original = structure.read_bytes()
    structure.write_bytes(original + b"\n")
    assert case_identity(resolved) != expected
    assert case_identity(resolved, recorded=recorded) == expected
    structure.unlink()
    with pytest.raises(ValueError, match="does not exist"):
        case_identity(resolved)
    assert case_identity(resolved, recorded=recorded) == expected

    with pytest.raises(KeyError, match="'protonation'"):
        case_identity(resolved, recorded={"structure": recorded["structure"]})


def test_val03_reopen_reads_the_runs_own_upstream_artefacts(
    example_06: Callable[..., ResolvedCase], tmp_path: Path
) -> None:
    """VAL-03: a run's stage-1 and protonation artefacts come from its store, or it is refused."""
    resolved = example_06()
    store = Store(tmp_path / "store")
    stored = {name: store.put(artefact) for name, artefact in _recorded(resolved).items()}
    record = {
        "artefacts": {
            name: {"schema": artefact.schema, "hash": artefact.hash}
            for name, artefact in stored.items()
        }
    }
    upstream = runs._upstream(tmp_path, record, store, resolved)
    assert sorted(upstream) == ["protonation", "structure"]
    assert case_identity(resolved, recorded=upstream) == case_identity(resolved)

    with pytest.raises(runs.RunError, match="holds no"):
        runs._upstream(tmp_path, record, Store(tmp_path / "empty"), resolved)
    with pytest.raises(runs.RunError, match="records no 'protonation'"):
        runs._upstream(
            tmp_path,
            {"artefacts": {"structure": record["artefacts"]["structure"]}},
            store,
            resolved,
        )

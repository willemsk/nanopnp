"""No refusal names a release that has shipped (VER-67, IF-02; WP40, ``MOD-14``).

The release-name check reads the source with no checked module imported, and reads
which releases are tagged from ``CHANGELOG.md``'s milestone headings, never from git:
a CI checkout carries no tags (WP40 D2). Each refusal names its requirement and the release
that schedules it, or says that none does, and exits as it did (VER-47); the texts are the WP40
plan's *Design* §1. A string pairing a requirement with a release agrees with §3.2 (D10).
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path
from typing import Any

import pytest
import yaml

from nanopnp.charge.stage import _field_path
from nanopnp.cli import main
from nanopnp.core.errors import EXIT_CASE
from nanopnp.io.case import Inputs, SuppliedArtefact, UnsupportedCaseSection
from nanopnp.io.defaults import CONFIGURATION_PATHS
from nanopnp.io.resolved import ResolvedCase
from nanopnp.mesh.ingest import _source_path
from nanopnp.pipeline import checks
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.pipeline.run import input_files
from nanopnp.validation.modularity import (
    release_pairing_mismatches,
    requirement_releases,
    stale_release_literals,
    tagged_releases,
)

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"
SPECIFICATION = ROOT / "SPECIFICATION.md"
QUICKSTART = ROOT / "examples" / "01-quickstart" / "quickstart.case.yaml"
STORE_HASH = "a" * 64


def _quickstart() -> dict[str, Any]:
    raw: dict[str, Any] = yaml.safe_load(QUICKSTART.read_text(encoding="utf-8"))
    return raw


def _refusal(raw: dict[str, Any]) -> str:
    """Return the text of the refusal resolving ``raw`` raises, checking its class."""
    with pytest.raises(UnsupportedCaseSection) as caught:
        resolve(loads_case(yaml.safe_dump(raw, sort_keys=False)))
    return str(caught.value)


# -- the check (D1 to D3) -------------------------------------------------------------


def test_ver67_tagged_releases_are_the_changelog_milestones() -> None:
    text = (
        "# Changelog\n\n## [0.3.0-alpha.1] - 2026-09-25\n\n## [0.2.0] - 2026-09-24\n\n"
        "### Added\n\n## [0.2.0-alpha.10] - 2026-09-23\n\n## [0.1.0] - 2026-09-02\n"
    )
    assert tagged_releases(text) == ("v0.1", "v0.2")
    live = tagged_releases(CHANGELOG.read_text(encoding="utf-8"))
    assert live[:4] == ("v0.1", "v0.2", "v0.3", "v0.4")


def test_ver67_a_changelog_that_names_no_release_or_skips_one_is_refused() -> None:
    with pytest.raises(ValueError, match=r"no release"):
        tagged_releases("# Changelog\n\n## [0.5.0-alpha.1] - 2026-10-05\n")
    with pytest.raises(ValueError, match=r"v0\.2"):
        tagged_releases("## [0.3.0] - 2026-09-30\n\n## [0.1.0] - 2026-09-02\n")


def test_ver67_a_changelog_that_lost_its_oldest_releases_is_refused() -> None:
    # A truncated head would un-tag v0.1 and v0.2, and pass every string naming them.
    with pytest.raises(ValueError, match=r"v0\.1"):
        tagged_releases("## [0.3.0] - 2026-09-30\n")
    with pytest.raises(ValueError, match=r"v1\.0"):
        tagged_releases("## [1.1.0] - x\n\n## [0.2.0] - x\n\n## [0.1.0] - x\n")
    # A major other than 0 opens at its minor 0.
    assert tagged_releases("## [1.0.0] - x\n") == ("v1.0",)
    with pytest.raises(ValueError, match=r"v1\.0"):
        tagged_releases("## [1.1.0] - x\n")
    # The stable release follows the last minor of major 0 without a gap.
    assert tagged_releases("## [1.0.0] - x\n\n## [0.2.0] - x\n\n## [0.1.0] - x\n") == (
        "v0.1",
        "v0.2",
        "v1.0",
    )


def test_ver67_a_synthetic_refusal_naming_a_tagged_release_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    root.mkdir()
    sources = {
        "refuse.py": (
            "def f(x):\n"
            '    """Arrived in v0.2."""\n'
            "    if x:\n"
            '        raise ValueError(f"strategy {x!r} is v0.2; it is not run")\n'
            '    raise ValueError("an analyte is FR-21, v0.7")\n'
        ),
        "names.py": (
            'SCHEMA = "nanopnp/case/v0.2"\n'
            'TAG = "tagged v0.2.0-alpha.3"\n'
            'LATER = "v0.20 is a later minor"\n'
            'STABLE = "may change before v1.0"\n'
        ),
    }
    for relative, text in sources.items():
        (root / relative).write_text(text, encoding="utf-8")
    found = stale_release_literals(("v0.1", "v0.2"), root)
    assert found == (
        ("names.py", 2, "v0.2", "tagged v0.2.0-alpha.3"),
        ("refuse.py", 4, "v0.2", " is v0.2; it is not run"),
    )
    assert stale_release_literals(("v0.1", "v0.2", "v0.7", "v1.0"), root) == (
        ("names.py", 2, "v0.2", "tagged v0.2.0-alpha.3"),
        ("names.py", 4, "v1.0", "may change before v1.0"),
        ("refuse.py", 4, "v0.2", " is v0.2; it is not run"),
        ("refuse.py", 5, "v0.7", "an analyte is FR-21, v0.7"),
    )


def test_ver67_no_string_in_the_package_names_a_tagged_release() -> None:
    stale = stale_release_literals(tagged_releases(CHANGELOG.read_text(encoding="utf-8")))
    assert stale == (), "\n".join(
        f"src/nanopnp/{path}:{line} names {release}, which is tagged: {text!r}"
        for path, line, release, text in stale
    )


def test_ver67_the_requirement_releases_are_read_from_the_release_column() -> None:
    table = (
        "| ID | Requirement | Release |\n|---|---|---|\n"
        "| **FR-01** | SHALL ingest. | v0.3 |\n| **FR-11** | MAY mesh. | post-1.0 |\n"
        "| **QR-02** | By v0.7 SHALL match. | Correctness |\n"
    )
    assert requirement_releases(table) == {"FR-01": "v0.3", "FR-11": "post-1.0"}
    live = requirement_releases(SPECIFICATION.read_text(encoding="utf-8"))
    assert live["FR-21"] == "v0.7"
    assert live["FR-11"] == "post-1.0"
    assert len(live) == 29


def test_ver67_a_string_pairing_a_requirement_with_another_release_is_found(
    tmp_path: Path,
) -> None:
    sources = {
        "pair.py": (
            '"""FR-21 is v0.2 here, in a docstring, so it is not checked."""\n'
            "OK = 'an analyte is FR-21, v0.7'\n"
            "WRONG = 'an analyte is FR-21, v0.4'\n"
            "LATER = 'boundary layers are FR-11, after v1.0'\n"
            "EARLY = 'boundary layers are FR-11, v0.7'\n"
            "TWO = 'FR-21 and FR-11 are scheduled in v0.4'\n"
            "NONE = 'FR-21 is scheduled'\n"
            "DEFERRED = 'FR-27 reads it, REV-62, deferred to v0.6'\n"
            "GONE = 'FR-99, v0.4'\n"
        )
    }
    for relative, text in sources.items():
        (tmp_path / relative).write_text(text, encoding="utf-8")
    table = {"FR-21": "v0.7", "FR-11": "post-1.0"}
    assert release_pairing_mismatches(table, tmp_path) == (
        ("pair.py", 3, "FR-21", "v0.4", "v0.7", "an analyte is FR-21, v0.4"),
        ("pair.py", 5, "FR-11", "v0.7", "post-1.0", "boundary layers are FR-11, v0.7"),
        ("pair.py", 9, "FR-99", "v0.4", "absent from section 3.2", "FR-99, v0.4"),
    )


def test_ver67_no_string_pairs_a_requirement_with_a_release_its_row_does_not_give() -> None:
    table = requirement_releases(SPECIFICATION.read_text(encoding="utf-8"))
    wrong = release_pairing_mismatches(table)
    assert wrong == (), "\n".join(
        f"src/nanopnp/{path}:{line} pairs {requirement} with {release}, but section 3.2 "
        f"gives {expected}: {text!r}"
        for path, line, requirement, release, expected, text in wrong
    )


# -- every inputs: key has a reader (REV-68, VER-47) ----------------------------------


def test_ver47_every_inputs_key_is_hashed_and_read_by_a_stage() -> None:
    package = ROOT / "src" / "nanopnp"
    stage_side = {
        path: path.read_text(encoding="utf-8")
        for path in package.rglob("*.py")
        if path.relative_to(package).parts[0] not in {"io", "pipeline", "sweep", "cli", "gui"}
    }
    declared = set(Inputs.model_fields)
    carried = {field.name for field in dataclasses.fields(ResolvedCase)}
    assert declared <= carried, (
        f"keys the resolved case does not carry: {sorted(declared - carried)}"
    )
    hashing = inspect.getsource(input_files)
    hashed = {key for key in declared if f'("{key}", resolved.{key})' in hashing}
    readers = {
        key: [path for path, text in stage_side.items() if f"resolved.{key}" in text]
        for key in declared
    }
    assert hashed == declared, f"keys input_files does not hash: {sorted(declared - hashed)}"
    unread = sorted(key for key, found in readers.items() if not found)
    assert unread == [], f"inputs: keys no stage reads (FR-25: hashed, never used): {unread}"


# -- the refusals (D4 to D8) ----------------------------------------------------------


def test_fr27_the_num20_strategy_is_refused_naming_its_schedule() -> None:
    raw = _quickstart()
    raw.setdefault("numerics", {})["nonlinear"] = {"strategy": "hybrid"}
    assert _refusal(raw) == (
        "numerics.nonlinear.strategy 'hybrid' selects NUM-20's hybrid segregated fallback, "
        "which no release of SPECIFICATION.md schedules; every rung is solved by the "
        "monolithic damped Newton of NUM-16 (strategy: newton)"
    )


def test_fr27_the_num20_damping_is_refused_naming_its_schedule() -> None:
    raw = _quickstart()
    raw.setdefault("numerics", {})["nonlinear"] = {"damping": "backtracking"}
    assert _refusal(raw) == (
        "numerics.nonlinear.damping 'backtracking' selects NUM-20's damped Newton with l2 "
        "backtracking, which no release of SPECIFICATION.md schedules; the damping is "
        "NUM-16's, adapted on residual reduction (damping: residual), whose recovery rule "
        "the reference records"
    )


def _field_refusal(key: str, what: str) -> str:
    """Return the refusal of ``inputs.<key>: artefact:`` on a supplied field, as WP40 words it."""
    return (
        f"inputs.{key}: artefact: names {what} by its store hash. FR-27's substitution reads a "
        "supplied field by path only, and no release of SPECIFICATION.md schedules the store "
        f"form; supply inputs.{key}: path: instead"
    )


MESH_REFUSAL = (
    "inputs.mesh: artefact: names a mesh by its store hash. FR-27's substitution reads a "
    "supplied mesh by path only; the store form is REV-62, deferred to v0.6 (section 8.2.9 "
    "I3); supply inputs.mesh: path: instead"
)


@pytest.mark.parametrize(
    ("key", "what"), [("charge", "a fixed-charge field"), ("eps_r", "a dielectric field")]
)
def test_fr27_a_field_named_by_store_hash_is_refused_at_resolution_and_at_the_stage(
    key: str, what: str
) -> None:
    expected = _field_refusal(key, what)
    raw = _quickstart()
    raw["inputs"][key] = {"artefact": STORE_HASH}
    assert _refusal(raw) == expected
    with pytest.raises(UnsupportedCaseSection) as caught:
        _field_path(SuppliedArtefact(artefact=STORE_HASH), key=key)
    assert str(caught.value) == expected


def test_fr27_a_mesh_named_by_store_hash_is_refused_at_resolution_and_at_the_stage() -> None:
    raw = _quickstart()
    raw["inputs"]["mesh"] = {"artefact": STORE_HASH, "format": "msh41"}
    assert _refusal(raw) == MESH_REFUSAL
    with pytest.raises(UnsupportedCaseSection) as caught:
        _source_path(SuppliedArtefact(artefact=STORE_HASH, format="msh41"))
    assert str(caught.value) == MESH_REFUSAL


def test_ver47_validate_case_refuses_a_stored_mesh_with_exit_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = _quickstart()
    raw["inputs"]["mesh"] = {"artefact": STORE_HASH, "format": "msh41"}
    case_file = tmp_path / "stored.case.yaml"
    case_file.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    assert main(["validate", "case", str(case_file)]) == EXIT_CASE
    captured = capsys.readouterr()
    assert MESH_REFUSAL in captured.err
    assert "Traceback" not in captured.err


def test_ver24_the_mesher_reason_names_its_requirement_not_a_release() -> None:
    assert CONFIGURATION_PATHS["numerics.mesh.backend"] == (
        "the mesher is stage 6's choice (FR-10), recorded in the Geometry and mesh group of "
        "the manifest (section 5.3.3); it changes the discretisation, not the model"
    )


def test_fr27_the_empty_refusal_tables_are_gone() -> None:
    assert not hasattr(checks, "_UNCONSUMED_INPUTS")
    assert not hasattr(checks, "_UNREAD_CHARGE_KEYS")
    assert "not delivered in this release" not in Path(checks.__file__).read_text(encoding="utf-8")

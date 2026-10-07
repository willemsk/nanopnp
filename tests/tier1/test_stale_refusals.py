"""No refusal names a release that has shipped (VER-67, IF-02; WP40, ``MOD-14``).

The release-name check reads the source with no checked module imported, and reads
which releases are tagged from ``CHANGELOG.md``'s milestone headings, never from git:
a CI checkout carries no tags (WP40 D2). The refusal texts are those of the WP40 plan,
*Design* §1; each names its requirement and the release that schedules it, or says that
none does, and exits as it did (VER-47).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"
QUICKSTART = ROOT / "examples" / "01-quickstart" / "quickstart.case.yaml"
STORE_HASH = "a" * 64


def _quickstart() -> dict[str, Any]:
    raw: dict[str, Any] = yaml.safe_load(QUICKSTART.read_text(encoding="utf-8"))
    return raw


def _refusal(raw: dict[str, Any]) -> str:
    """Return the text of the refusal resolving ``raw`` raises, checking its class."""
    from nanopnp.io.case import UnsupportedCaseSection
    from nanopnp.pipeline.case import loads_case, resolve

    with pytest.raises(UnsupportedCaseSection) as caught:
        resolve(loads_case(yaml.safe_dump(raw, sort_keys=False)))
    return str(caught.value)


# -- the check (D1 to D3) -------------------------------------------------------------


def test_ver67_tagged_releases_are_the_changelog_milestones() -> None:
    from nanopnp.validation.modularity import tagged_releases

    text = (
        "# Changelog\n\n## [0.3.0-alpha.1] - 2026-09-25\n\n## [0.2.0] - 2026-09-24\n\n"
        "### Added\n\n## [0.2.0-alpha.10] - 2026-09-23\n\n## [0.1.0] - 2026-09-02\n"
    )
    assert tagged_releases(text) == ("v0.1", "v0.2")
    live = tagged_releases(CHANGELOG.read_text(encoding="utf-8"))
    assert live[:4] == ("v0.1", "v0.2", "v0.3", "v0.4")
    assert live == tuple(f"v0.{minor}" for minor in range(1, len(live) + 1))


def test_ver67_a_changelog_that_names_no_release_or_skips_one_is_refused() -> None:
    from nanopnp.validation.modularity import tagged_releases

    with pytest.raises(ValueError, match=r"no release"):
        tagged_releases("# Changelog\n\n## [0.5.0-alpha.1] - 2026-10-05\n")
    with pytest.raises(ValueError, match=r"v0\.2"):
        tagged_releases("## [0.3.0] - 2026-09-30\n\n## [0.1.0] - 2026-09-02\n")


def test_ver67_a_synthetic_refusal_naming_a_tagged_release_is_refused(tmp_path: Path) -> None:
    from nanopnp.validation.modularity import stale_release_literals

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


@pytest.mark.xfail(strict=True, reason="planned: WP40 D3")
def test_ver67_no_string_in_the_package_names_a_tagged_release() -> None:
    from nanopnp.validation.modularity import stale_release_literals, tagged_releases

    stale = stale_release_literals(tagged_releases(CHANGELOG.read_text(encoding="utf-8")))
    assert stale == (), "\n".join(
        f"src/nanopnp/{path}:{line} names {release}, which is tagged: {text!r}"
        for path, line, release, text in stale
    )


# -- the refusals (D4 to D8) ----------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="planned: WP40 D6")
def test_fr27_the_num20_strategy_is_refused_naming_its_schedule() -> None:
    raw = _quickstart()
    raw.setdefault("numerics", {})["nonlinear"] = {"strategy": "hybrid"}
    assert _refusal(raw) == (
        "numerics.nonlinear.strategy 'hybrid' selects NUM-20's hybrid segregated fallback, "
        "which no release of SPECIFICATION.md schedules; every rung is solved by the "
        "monolithic damped Newton of NUM-16 (strategy: newton)"
    )


@pytest.mark.xfail(strict=True, reason="planned: WP40 D6")
def test_fr27_the_num20_damping_is_refused_naming_its_schedule() -> None:
    raw = _quickstart()
    raw.setdefault("numerics", {})["nonlinear"] = {"damping": "backtracking"}
    assert _refusal(raw) == (
        "numerics.nonlinear.damping 'backtracking' selects NUM-20's damped Newton with l2 "
        "backtracking, which no release of SPECIFICATION.md schedules; the damping is "
        "NUM-16's, adapted on residual reduction (damping: residual), whose recovery rule "
        "the reference records"
    )


FIELD_REFUSAL = (
    "inputs.{key}: artefact: names {what} by its store hash. FR-27's substitution reads a "
    "supplied field by path only, and no release of SPECIFICATION.md schedules the store "
    "form; supply inputs.{key}: path: instead"
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
    from nanopnp.charge.stage import _field_path
    from nanopnp.io.case import SuppliedArtefact, UnsupportedCaseSection

    expected = FIELD_REFUSAL.format(key=key, what=what)
    raw = _quickstart()
    raw["inputs"][key] = {"artefact": STORE_HASH}
    assert _refusal(raw) == expected
    with pytest.raises(UnsupportedCaseSection) as caught:
        _field_path(SuppliedArtefact(artefact=STORE_HASH), key=key)
    assert str(caught.value) == expected


def test_fr27_a_mesh_named_by_store_hash_is_refused_at_resolution_and_at_the_stage() -> None:
    from nanopnp.io.case import SuppliedArtefact, UnsupportedCaseSection
    from nanopnp.mesh.ingest import _source_path

    raw = _quickstart()
    raw["inputs"]["mesh"] = {"artefact": STORE_HASH, "format": "msh41"}
    assert _refusal(raw) == MESH_REFUSAL
    with pytest.raises(UnsupportedCaseSection) as caught:
        _source_path(SuppliedArtefact(artefact=STORE_HASH, format="msh41"))
    assert str(caught.value) == MESH_REFUSAL


def test_ver47_validate_case_refuses_a_stored_mesh_with_exit_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from nanopnp.cli import main
    from nanopnp.core.errors import EXIT_CASE

    raw = _quickstart()
    raw["inputs"]["mesh"] = {"artefact": STORE_HASH, "format": "msh41"}
    case_file = tmp_path / "stored.case.yaml"
    case_file.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    assert main(["validate", "case", str(case_file)]) == EXIT_CASE
    captured = capsys.readouterr()
    assert MESH_REFUSAL in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.xfail(strict=True, reason="planned: WP40 D7")
def test_ver24_the_mesher_reason_names_its_requirement_not_a_release() -> None:
    from nanopnp.io.defaults import CONFIGURATION_PATHS

    assert CONFIGURATION_PATHS["numerics.mesh.backend"] == (
        "the mesher is stage 6's choice (FR-10), recorded in the Geometry and mesh group of "
        "the manifest (section 5.3.3); it changes the discretisation, not the model"
    )


@pytest.mark.xfail(strict=True, reason="planned: WP40 D8")
def test_fr27_the_empty_refusal_tables_are_gone() -> None:
    from nanopnp.pipeline import checks

    assert not hasattr(checks, "_UNCONSUMED_INPUTS")
    assert not hasattr(checks, "_UNREAD_CHARGE_KEYS")
    assert "not delivered in this release" not in Path(checks.__file__).read_text(encoding="utf-8")

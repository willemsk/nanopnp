"""VER-72 (d, e): the planned tests and the plans' Outcomes agree with the code.

- **Planned tests** (``xfail(strict=True, reason="planned: WP<n> …")``) must be
  strict and name a planned package that is not yet delivered.
- **Names in Outcomes**: every ``name()`` quoted in an Outcome of a plan from
  :data:`FIRST_CHECKED` on is a function, class or module-level assignment of
  ``src/nanopnp``. Only the call form is checked, because a dotted name in a plan
  is as often a case path or a field as code; a dotted call whose first part is
  not a ``nanopnp`` name, such as ``gmsh.initialize()``, is third-party.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from nanopnp.validation.findings import REPOSITORY
from nanopnp.validation.modularity import Module, parse_package

PLANS = REPOSITORY / "docs" / "plans"
TESTS = REPOSITORY / "tests"

FIRST_CHECKED = 40
"""The first work package whose Outcomes are checked; the plans before it are left as written."""

PLANNED = re.compile(r"^planned: WP(\d+)\b")
"""The reason a planned test's ``xfail`` marker opens with."""

STATUS = re.compile(r"^\*\*Status: ([^.*,]+)")
"""A plan's Status line; its first words are ``delivered`` once the package has merged."""

CALL = re.compile(r"`([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\(\)`")
"""A quoted ``name()`` or ``dotted.name()``."""


# -- planned tests (VER-72 d) -----------------------------------------------------


def _plan(number: int, plans: Path) -> Path | None:
    found = sorted(plans.glob(f"wp{number}-*.md"))
    return found[0] if found else None


def _status(plan: Path) -> str:
    for line in plan.read_text(encoding="utf-8").splitlines():
        match = STATUS.match(line)
        if match:
            return match.group(1).strip()
    return ""


def _xfail_markers(tree: ast.AST) -> Iterator[ast.Call]:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "xfail"
        ):
            yield node


def stale_planned_markers(tests: Path = TESTS, plans: Path = PLANS) -> list[str]:
    """Return a diagnostic for each ``planned:`` marker that cannot stay where it is."""
    problems = []
    for path in sorted(tests.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for marker in _xfail_markers(tree):
            keywords = {k.arg: k.value for k in marker.keywords}
            reason = keywords.get("reason")
            if not (isinstance(reason, ast.Constant) and isinstance(reason.value, str)):
                continue
            match = PLANNED.match(reason.value)
            if match is None:
                continue
            place = f"{path.relative_to(tests.parent).as_posix()}:{marker.lineno}"
            number = int(match.group(1))
            plan = _plan(number, plans)
            strict = keywords.get("strict")
            if not (isinstance(strict, ast.Constant) and strict.value is True):
                problems.append(
                    f"{place}: planned test of WP{number} is not strict=True, so it can pass "
                    "unnoticed with its marker left on"
                )
            if plan is None:
                problems.append(f"{place}: planned test names WP{number}, which has no plan")
            elif _status(plan).startswith("delivered"):
                problems.append(
                    f"{place}: WP{number} is delivered ({plan.name}) and its planned test still "
                    "carries its xfail marker. Delete the marker; if the test fails, the "
                    "package is not delivered"
                )
    return problems


def test_ver72_no_planned_test_outlives_its_package() -> None:
    problems = stale_planned_markers()
    assert problems == [], "\n".join(problems)


@pytest.fixture
def records(tmp_path: Path) -> tuple[Path, Path]:
    """Return a tests tree and a plans directory: WP90 planned, WP91 delivered."""
    tests, plans = tmp_path / "tests", tmp_path / "docs" / "plans"
    (tests / "tier1").mkdir(parents=True)
    plans.mkdir(parents=True)
    (plans / "wp90-open.md").write_text(
        "# WP90\n\n**Status: planned, not started.** Written.\n", encoding="utf-8"
    )
    (plans / "wp91-done.md").write_text(
        "# WP91\n\n**Status: delivered, 6 October 2026.** Written.\n", encoding="utf-8"
    )
    return tests, plans


def _marked(reason: str, strict: str = "True") -> str:
    return (
        "import pytest\n\n"
        f"@pytest.mark.xfail(strict={strict}, reason={reason!r})\n"
        "def test_x():\n    assert False\n"
    )


def test_ver72_a_planned_marker_on_an_open_package_is_kept(records: tuple[Path, Path]) -> None:
    tests, plans = records
    (tests / "tier1" / "test_a.py").write_text(_marked("planned: WP90 D3"), encoding="utf-8")
    (tests / "tier1" / "test_b.py").write_text(_marked("a known bug", "False"), encoding="utf-8")
    assert stale_planned_markers(tests, plans) == []


@pytest.mark.parametrize(
    ("reason", "strict", "expected"),
    [
        ("planned: WP91 D2", "True", "WP91 is delivered (wp91-done.md)"),
        ("planned: WP92 D1", "True", "names WP92, which has no plan"),
        ("planned: WP90 D3", "False", "is not strict=True"),
    ],
)
def test_ver72_a_stale_planned_marker_is_named(
    records: tuple[Path, Path], reason: str, strict: str, expected: str
) -> None:
    tests, plans = records
    (tests / "tier1" / "test_a.py").write_text(_marked(reason, strict), encoding="utf-8")
    problems = stale_planned_markers(tests, plans)
    assert len(problems) == 1
    assert problems[0].startswith("tests/tier1/test_a.py:3: ")
    assert expected in problems[0]


# -- names in Outcomes (VER-72 e) ---------------------------------------------------


def defined_names(modules: tuple[Module, ...]) -> tuple[frozenset[str], frozenset[str]]:
    """Return the names ``src/nanopnp`` defines and the names its modules go by.

    A name is a function or class anywhere, methods included, or a module-level
    assignment. A module goes by each dotted suffix of its name: ``gmsh_backend``,
    ``mesh.gmsh_backend``, ``nanopnp.mesh.gmsh_backend``.
    """
    names: set[str] = set()
    known: set[str] = set()
    for module in modules:
        parts = module.name.split(".")
        known |= {".".join(parts[start:]) for start in range(len(parts))}
        for node in ast.walk(module.tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                names.add(node.name)
        for statement in module.tree.body:
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
                if isinstance(statement, ast.AnnAssign)
                else []
            )
            names |= {target.id for target in targets if isinstance(target, ast.Name)}
    return frozenset(names), frozenset(known)


def _outcome_lines(text: str) -> Iterator[tuple[int, str]]:
    inside = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("> **Outcome"):
            inside = True
        elif not line.startswith(">"):
            inside = False
        if inside:
            yield number, line


def unresolved_outcome_names(
    text: str, names: frozenset[str], modules: frozenset[str]
) -> list[tuple[int, str]]:
    """Return ``(line, quoted)`` of each ``name()`` in an Outcome block that the code lacks."""
    missing = []
    for number, line in _outcome_lines(text):
        for quoted in CALL.findall(line):
            parts = quoted.split(".")
            if len(parts) > 1 and parts[0] not in names and parts[0] not in modules:
                continue
            if parts[-1] not in names:
                missing.append((number, quoted))
    return missing


def _checked_plans(plans: Path = PLANS, first: int = FIRST_CHECKED) -> list[Path]:
    found = []
    for path in sorted(plans.glob("wp*-*.md")):
        match = re.match(r"wp(\d+)-", path.name)
        if match and int(match.group(1)) >= first:
            found.append(path)
    return found


def test_ver72_every_name_an_outcome_quotes_exists() -> None:
    names, modules = defined_names(parse_package())
    missing = [
        f"{path.relative_to(REPOSITORY).as_posix()}:{line}: `{quoted}()` is not in src/nanopnp"
        for path in _checked_plans()
        for line, quoted in unresolved_outcome_names(
            path.read_text(encoding="utf-8"), names, modules
        )
    ]
    assert missing == [], "\n".join(missing)


OUTCOME = """# WP90

> **Outcome — The registries (D1).**
> The editor reads `registered_meshers()` and `registered_modes()`, and
> `mesh.meshers.create_mesher()`; Gmsh opens with `gmsh.initialize()`.

Prose outside an Outcome may say `registered_widgets()`.
"""
"""A missing ``registered_modes()``, beside names that resolve or are not checked."""


def test_ver72_an_outcome_naming_a_missing_function_is_named() -> None:
    names, modules = defined_names(parse_package())
    assert unresolved_outcome_names(OUTCOME, names, modules) == [(4, "registered_modes")]


def test_ver72_outcomes_are_checked_from_wp40_on(tmp_path: Path) -> None:
    for number in (39, 40, 41):
        (tmp_path / f"wp{number}-x.md").write_text("# x\n", encoding="utf-8")
    assert [p.name for p in _checked_plans(tmp_path)] == ["wp40-x.md", "wp41-x.md"]

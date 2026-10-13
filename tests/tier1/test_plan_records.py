"""VER-72 (e): the plans' Outcomes agree with the code.

Every ``name()`` quoted in an Outcome of a plan from :data:`FIRST_CHECKED` on is a function,
class or module-level assignment of ``src/nanopnp``. Only the call form is checked, because a
dotted name in a plan is as often a case path or a field as code; a dotted call whose first part
is not a ``nanopnp`` name, such as ``gmsh.initialize()``, is third-party.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

from nanopnp.validation.findings import REPOSITORY
from nanopnp.validation.modularity import Module, parse_package

PLANS = REPOSITORY / "docs" / "plans"
TESTS = REPOSITORY / "tests"

FIRST_CHECKED = 40
"""The first work package whose Outcomes are checked; the plans before it are left as written."""

CALL = re.compile(r"`([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\(\)`")
"""A quoted ``name()`` or ``dotted.name()``."""


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
    """Yield ``(line, text)`` of each line of an Outcome blockquote, an indented one included."""
    inside = False
    for number, line in enumerate(text.splitlines(), start=1):
        quoted = line.lstrip()
        if quoted.startswith("> **Outcome"):
            inside = True
        elif not quoted.startswith(">"):
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

- A work item, annotated in place:

  > **Outcome — measured.** `registered_panels()` was not needed.
"""
"""Missing ``registered_modes()`` and ``registered_panels()``, beside names not checked."""


def test_ver72_an_outcome_naming_a_missing_function_is_named() -> None:
    names, modules = defined_names(parse_package())
    assert unresolved_outcome_names(OUTCOME, names, modules) == [
        (4, "registered_modes"),
        (11, "registered_panels"),
    ]


def test_ver72_outcomes_are_checked_from_wp40_on(tmp_path: Path) -> None:
    for number in (39, 40, 41):
        (tmp_path / f"wp{number}-x.md").write_text("# x\n", encoding="utf-8")
    assert [p.name for p in _checked_plans(tmp_path)] == ["wp40-x.md", "wp41-x.md"]

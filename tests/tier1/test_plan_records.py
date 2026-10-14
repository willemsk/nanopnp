"""VER-72 (e): the plans' Outcomes agree with the code."""

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

CALL = re.compile(r"`([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\(\)`")


# -- names in Outcomes ---------------------------------------------------


def defined_names(modules: tuple[Module, ...]) -> tuple[frozenset[str], frozenset[str]]:
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

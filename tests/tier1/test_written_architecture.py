"""VER-79: the written architecture and decisions stay equal to the tree."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from nanopnp.validation.findings import REPOSITORY
from nanopnp.validation.modularity import node_of, parse_package

OVERVIEW = REPOSITORY / "specification" / "05-software-design" / "01-architectural-overview.md"
COMMAND = "uv run .claude/scripts/decisions.py"


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(path.stem, module)
    spec.loader.exec_module(module)
    return module


architecture = _load(REPOSITORY / "docs" / "scripts" / "architecture.py")
decisions = _load(REPOSITORY / ".claude" / "scripts" / "decisions.py")


def _module_rows(text: str) -> set[str]:
    return {
        match.group(1)
        for line in text.splitlines()
        if (match := architecture.TABLE_ROW.match(line))
    }


def _subpackages() -> set[str]:
    return {node_of(module.name) for module in parse_package()} - {"nanopnp"}


def test_ver79_section_5_1_module_rows_equal_the_subpackages() -> None:
    text = OVERVIEW.read_text(encoding="utf-8")
    rows, subpackages = _module_rows(text), _subpackages()
    assert not subpackages - rows, f"subpackages without a §5.1 row: {sorted(subpackages - rows)}"
    assert not rows - subpackages, f"§5.1 rows without a subpackage: {sorted(rows - subpackages)}"
    without_plot = "\n".join(line for line in text.splitlines() if not line.startswith("| `plot/`"))
    assert "plot" in subpackages - _module_rows(without_plot)


def test_ver79_the_decisions_page_equals_what_the_script_renders() -> None:
    expected = decisions.render().splitlines()
    written = decisions.PAGE.read_text(encoding="utf-8").splitlines()
    first = next(
        (
            number
            for number, (want, have) in enumerate(zip(expected, written, strict=False), 1)
            if want != have
        ),
        None if len(expected) == len(written) else min(len(expected), len(written)) + 1,
    )
    assert first is None, f"docs/project/decisions.md differs at line {first}; run `{COMMAND}`"


def test_ver79_every_ruling_has_one_holds_now_entry() -> None:
    letters = decisions.ruling_letters()
    entries = decisions.holds_now()
    assert not set(letters) - set(entries), (
        f"rulings without a holds-now entry: {sorted(set(letters) - set(entries))}"
    )
    assert not set(entries) - set(letters), (
        f"holds-now entries without a ruling: {sorted(set(entries) - set(letters))}"
    )

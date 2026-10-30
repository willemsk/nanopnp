"""VER-46: no command in an example README's console fences is left for no test to run."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.validation.examples import EXPECTED_EXIT, untagged_commands

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@pytest.mark.parametrize(
    "readme", sorted(EXAMPLES.glob("*/README.md")), ids=lambda path: path.parent.name
)
def test_ver46_an_example_readme_leaves_no_command_untagged(readme: Path) -> None:
    assert not untagged_commands(readme, EXPECTED_EXIT), readme.parent.name


def test_ver46_an_untagged_console_command_is_found_and_a_tested_one_is_not(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "<!-- example: run -->\n```console\n$ nanopnp run a.yaml\n```\n\n"
        "```console\n$ nanopnp plot a.yaml --out a.png\n$ ls\n```\n"
        "<!-- example: other -->\n```console\n$ python go.py\n```\n",
        encoding="utf-8",
    )
    found = untagged_commands(readme, EXPECTED_EXIT)
    assert found == [["nanopnp", "plot", "a.yaml", "--out", "a.png"], ["python", "go.py"]]

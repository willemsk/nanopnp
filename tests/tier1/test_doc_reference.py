"""VER-45 — the generated reference pages cover exactly what they document (IF-02, IF-03).

The case-file, command-line and exit-code references are rendered at build time
from the live schema walk, argument parser and exit enumeration
(:mod:`nanopnp.cli.reference`), so they cannot drift by hand. What can still go
wrong is the renderer: a field it skips, a nested subcommand it never walks, an
exit class it forgets. Each is asserted here in both directions, against the
object the page claims to render.
"""

from __future__ import annotations

import argparse
import re

from nanopnp.cli import build_parser
from nanopnp.cli.errors import EXCLUDED, EXIT_CODES, EXIT_MEANINGS
from nanopnp.cli.reference import (
    render_case_reference,
    render_cli_reference,
    render_exit_codes,
)
from nanopnp.io.case import case_fields, options_at, schema_default
from nanopnp.io.defaults import SWITCH_PATHS


def _rows(text: str) -> dict[str, list[str]]:
    """Return each table row keyed by its first (back-quoted) cell."""
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = re.match(r"^\| `([^`]+)` \|(.*)\|$", line)
        if match:
            key = match.group(1)
            assert key not in rows, f"{key} is listed twice"
            rows[key] = [cell.strip() for cell in match.group(2).split(" | ")]
    return rows


def test_ver45_case_reference_lists_exactly_the_schema_walk() -> None:
    """One row per ``case_fields()`` path, and no row for anything else."""
    rows = _rows(render_case_reference())
    paths = [reference.path for reference in case_fields()]
    assert set(rows) == set(paths)
    assert len(rows) == len(paths)


def test_ver45_case_reference_takes_default_and_options_from_the_schema() -> None:
    """Required fields say so; a restricted field lists what ``options_at`` admits."""
    rows = _rows(render_case_reference())
    for reference in case_fields():
        _type, default, accepts, validated = rows[reference.path]
        has_default, _value = schema_default(reference.path)
        assert (default == "**required**") is not has_default, reference.path
        options = options_at(reference.path) or ()
        assert re.findall(r"`([^`]+)`", accepts) == list(options), reference.path
        assert bool(validated) is (reference.path in SWITCH_PATHS), reference.path


def test_ver45_case_reference_shows_the_validated_default_apart_from_the_schema_default() -> None:
    """A correction defaults to ``none`` in the schema and to the fitted file when validated.

    The distinction a user most needs: a case naming no correction solves
    classical PNP-NS, and the manifest records that as deviations (FR-25).
    """
    rows = _rows(render_case_reference())
    _type, default, _accepts, validated = rows["electrolyte.corrections.diffusivity.model"]
    assert default == "none"
    assert validated == "willems2020_nacl"


def _all_parsers(parser: argparse.ArgumentParser) -> list[argparse.ArgumentParser]:
    found = [parser]
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                found += _all_parsers(child)
    return found


def test_ver45_cli_reference_covers_every_command_and_option() -> None:
    """Every parser ``build_parser()`` defines has a section, and every option a row."""
    text = render_cli_reference()
    sections = re.split(r"^## `([^`]+)`$", text, flags=re.M)
    by_command = dict(zip(sections[1::2], sections[2::2], strict=True))
    parsers = _all_parsers(build_parser())
    assert set(by_command) == {parser.prog for parser in parsers}
    for parser in parsers:
        body = by_command[parser.prog]
        for action in parser._actions:
            if isinstance(action, argparse._HelpAction | argparse._VersionAction):
                continue
            if isinstance(action, argparse._SubParsersAction):
                for name in action.choices:
                    assert f"{parser.prog} {name}" in by_command
                continue
            label = action.option_strings[0] if action.option_strings else action.dest
            assert f"`{label}`" in body, f"{parser.prog}: {label} is undocumented"


def test_ver45_exit_code_reference_is_the_enumeration() -> None:
    """The class table, the exception map and the exclusions, each in both directions."""
    text = render_exit_codes()
    classes = {
        int(code): meaning
        for code, meaning in re.findall(r"^\| `(\d+)` \| (.*) \|$", text, flags=re.M)
    }
    assert set(classes) == set(EXIT_MEANINGS)
    assert set(EXIT_CODES.values()) | {0, 1, 2} == set(EXIT_MEANINGS)
    mapped = {
        name: int(code)
        for name, code in re.findall(r"^\| `([\w.]+:\w+)` \| `(\d+)` \|$", text, flags=re.M)
    }
    assert mapped == EXIT_CODES
    excluded = set(re.findall(r"^\| `([\w.]+:\w+)` \| [^`]", text, flags=re.M))
    assert excluded == set(EXCLUDED)

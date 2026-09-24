"""Renderers for the generated reference pages of the user documentation (VER-45).

Each function here turns a live object of the package into Markdown: the case-file
schema walk (:func:`nanopnp.io.case.case_fields`), the argument parser
(:func:`nanopnp.cli.build_parser`), the exit-code enumeration
(:mod:`nanopnp.cli.errors`) and the public surface (:data:`nanopnp.PUBLIC`). Nothing
generated is committed: ``docs/scripts/generate.py`` calls these at build time, so a
field, a flag or an exit class added later appears in the documentation without an
edit to it, and a reference page cannot drift from the code it describes.

They are pure — no file is written and no solver imported — so that Tier 1 can
assert, in both directions, that each page covers exactly what it documents.
"""

from __future__ import annotations

import argparse
import types
from pathlib import Path
from typing import Literal, Union, get_args, get_origin

import yaml

from nanopnp import PUBLIC
from nanopnp.cli import build_parser
from nanopnp.cli.errors import EXCLUDED, EXIT_CODES, EXIT_MEANINGS
from nanopnp.io.case import (
    _PIPELINE_SECTIONS,
    SCHEMA,
    SEQUENCE_INDEX,
    FieldValue,
    case_fields,
    options_at,
    schema_default,
)
from nanopnp.io.defaults import SWITCH_PATHS, VALIDATED_DEFAULT_CASE, value_at

__all__ = [
    "API_SECTIONS",
    "render_api_reference",
    "render_case_reference",
    "render_cli_reference",
    "render_exit_codes",
]

USAGE_WIDTH = 88
"""Column width usage lines are wrapped to; fixed so the output does not depend on
the terminal that ran the build."""

API_SECTIONS: dict[str, str] = {
    "nanopnp.io.run": "Running a case",
    "nanopnp.io.case": "Case files",
    "nanopnp.io.store": "The artefact store",
    "nanopnp.sweep.plan": "Sweeps",
    "nanopnp.sweep.run": "Sweeps",
    "nanopnp.core.stages": "Stages, progress and cancellation",
}
"""The heading each defining module's names are documented under."""


# -- the case file -------------------------------------------------------------


def _type_name(annotation: object) -> str:
    """Return a reader's name for a declared field type."""
    names: dict[object, str] = {
        str: "string",
        float: "number",
        int: "integer",
        bool: "boolean",
        Path: "path",
    }
    if annotation in names:
        return names[annotation]
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        return "choice"
    if origin in (Union, types.UnionType):
        present = [argument for argument in arguments if argument is not type(None)]
        text = " or ".join(_type_name(argument) for argument in present)
        return f"{text}, optional" if len(present) < len(arguments) else text
    if origin is dict and len(arguments) == 2:
        return f"mapping of {_type_name(arguments[0])} to {_type_name(arguments[1])}"
    if origin is list and len(arguments) == 1:
        return f"list of {_type_name(arguments[0])}"
    return str(annotation).replace("typing.", "")


def _flow(value: FieldValue) -> str:
    """Return a value as it would be written in a case file, on one line."""
    if value is None:
        return "unset"
    if isinstance(value, Path):
        value = str(value)
    text: str = yaml.safe_dump(value, default_flow_style=True, sort_keys=False)
    return text.strip().removesuffix("...").strip()


def _cell(text: str) -> str:
    """Escape a table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def render_case_reference() -> str:
    """Return the case-file reference: every editable field of the current case schema.

    One row per path of :func:`~nanopnp.io.case.case_fields`, grouped by section,
    with the declared type, the schema's default, the values accepted where a
    type or a live registry restricts them (:func:`~nanopnp.io.case.options_at`),
    and, for a switch, the validated default the FR-25 manifest measures
    deviations against (:data:`~nanopnp.io.defaults.VALIDATED_DEFAULT_CASE`).
    """
    lines = [
        "# Case-file reference",
        "",
        f"Generated from the `{SCHEMA}` schema by `nanopnp.cli.reference`; every",
        "editable field is listed, and nothing here is written by hand. A path written",
        f"`a.{SEQUENCE_INDEX}.b` names field `b` of each element of the list `a`.",
        "",
        "**Default** is what a document omitting the field is validated with. **Validated",
        "default** is given for each switch of the model: the configuration of the published",
        "ePNP-NS model (PHY-21, PHY-22). A run whose switch differs from it lists that switch",
        "under the manifest's deviations (FR-25), so the schema default and the validated",
        "default are deliberately not the same thing: a document that names no correction",
        "solves classical PNP-NS and says so in its manifest.",
        "",
    ]
    sections: dict[str, list[str]] = {}
    for reference in case_fields():
        head = reference.path.split(".", 1)[0] if "." in reference.path else "document"
        has_default, default = schema_default(reference.path)
        options = options_at(reference.path)
        validated = (
            _flow(value_at(VALIDATED_DEFAULT_CASE, reference.path))
            if reference.path in SWITCH_PATHS
            else ""
        )
        row = (
            f"| `{reference.path}` | {_cell(_type_name(reference.annotation))} | "
            f"{_cell(_flow(default)) if has_default else '**required**'} | "
            f"{_cell(', '.join(f'`{option}`' for option in options)) if options else ''} | "
            f"{_cell(validated)} |"
        )
        sections.setdefault(head, []).append(row)

    for head, rows in sections.items():
        lines += [f"## `{head}`" if head != "document" else "## Top level", ""]
        if head in _PIPELINE_SECTIONS:
            lines += [
                f"This section drives {_PIPELINE_SECTIONS[head]}, which lands in v0.9. This",
                "release refuses a case carrying it, naming the section; supply the artefact",
                "it would produce through `inputs:` instead.",
                "",
            ]
        lines += [
            "| Path | Type | Default | Accepts | Validated default |",
            "|---|---|---|---|---|",
            *rows,
            "",
        ]
    return "\n".join(lines)


# -- the command line ----------------------------------------------------------


def _parsers(
    parser: argparse.ArgumentParser,
) -> list[tuple[argparse.ArgumentParser, str]]:
    """Return ``parser`` and every parser under it, depth first, with its help line."""
    found: list[tuple[argparse.ArgumentParser, str]] = [(parser, parser.description or "")]
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            helps = {choice.dest: choice.help or "" for choice in action._choices_actions}
            for name, child in action.choices.items():
                below = _parsers(child)
                found.append((child, helps.get(name, "")))
                found += below[1:]
    return found


def _usage(parser: argparse.ArgumentParser) -> str:
    """Return a parser's usage line at a fixed width."""
    formatter = argparse.HelpFormatter(prog=parser.prog, width=USAGE_WIDTH)
    formatter.add_usage(parser.usage, parser._actions, parser._mutually_exclusive_groups)
    return formatter.format_help().strip()


def _expanded(parser: argparse.ArgumentParser, action: argparse.Action) -> str:
    """Return an action's help text with argparse's ``%`` substitutions applied."""
    if not action.help:
        return ""
    formatter = argparse.HelpFormatter(prog=parser.prog, width=USAGE_WIDTH)
    return formatter._expand_help(action)


def command_parsers() -> list[tuple[str, argparse.ArgumentParser, str]]:
    """Return ``(command, parser, help)`` for ``nanopnp`` and every subcommand under it."""
    return [(parser.prog, parser, text) for parser, text in _parsers(build_parser())]


def render_cli_reference() -> str:
    """Return the command-line reference: every command, its usage and its options."""
    lines = [
        "# Command-line reference",
        "",
        "Generated from `nanopnp.cli.build_parser()`; every command and option is listed.",
        "No flag changes what is solved: every quantity that changes a number lives in the",
        "case file (the IF-02 configuration NOTE). The exit status of every command is the",
        "contract of the [exit-code reference](exit-codes.md).",
        "",
    ]
    for command, parser, text in command_parsers():
        lines += [f"## `{command}`", ""]
        if text:
            lines += [text[0].upper() + text[1:] + ("" if text.endswith(".") else "."), ""]
        lines += ["```text", _usage(parser), "```", ""]
        rows = []
        for action in parser._actions:
            if isinstance(action, argparse._HelpAction | argparse._VersionAction):
                continue
            if isinstance(action, argparse._SubParsersAction):
                continue
            name = ", ".join(f"`{option}`" for option in action.option_strings) or (
                f"`{action.metavar or action.dest}`"
            )
            default = action.default
            # By identity, not ``in``: ``0 == False`` and ``0.0 == False``, so a
            # membership test would hide a numeric default of zero. A counting
            # flag's zero is the one "no default worth showing" besides these.
            hidden = (
                default is None
                or default is False
                or default is argparse.SUPPRESS
                or isinstance(action, argparse._CountAction)
                or not action.option_strings
            )
            shown = "" if hidden else f"`{default}`"
            rows.append(f"| {name} | {_cell(_expanded(parser, action))} | {shown} |")
        if rows:
            lines += ["| Argument | Meaning | Default |", "|---|---|---|", *rows, ""]
    return "\n".join(lines)


def render_exit_codes() -> str:
    """Return the exit-code reference: the classes, and which exception maps to which."""
    lines = [
        "# Exit codes",
        "",
        "The exit status of every `nanopnp` command is a contract (the IF-02 exit-code NOTE):",
        "a job array branches on it, and a member that *failed* must be distinguishable from",
        "one that was *refused*. Generated from `nanopnp.cli.errors`.",
        "",
        "| Code | Meaning |",
        "|---|---|",
        *(f"| `{code}` | {_cell(meaning)} |" for code, meaning in sorted(EXIT_MEANINGS.items())),
        "",
        "A single sweep member dispatched with `--index` exits with that member's own code. A",
        "local multi-worker sweep exits `0` once every member has reached a terminal state and",
        "the dataset is written; the per-member codes are in the dataset.",
        "",
        "## Which failure exits with which code",
        "",
        "The mapping is an explicit enumeration. A subclass takes its base class's code.",
        "",
        "| Exception | Code |",
        "|---|---|",
        *(f"| `{name}` | `{code}` |" for name, code in sorted(EXIT_CODES.items())),
        "",
        "## Deliberately unclassified",
        "",
        "These exit `1`, each for a stated reason.",
        "",
        "| Exception | Why |",
        "|---|---|",
        *(f"| `{name}` | {_cell(reason)} |" for name, reason in sorted(EXCLUDED.items())),
        "",
    ]
    return "\n".join(lines)


# -- the Python API ------------------------------------------------------------


def render_api_reference() -> str:
    """Return the API reference over the IF-01 public surface, as mkdocstrings directives."""
    lines = [
        "# Python API",
        "",
        "The stable API is exactly the names below, each importable from the top-level",
        "package (`from nanopnp import run_case`); the IF-01 public-surface NOTE. Every other",
        "module is internal and may change before v1.0. `import nanopnp` is cheap: the names",
        "resolve on first use, so introspecting the package never imports the solver.",
        "",
    ]
    by_section: dict[str, list[str]] = {}
    for name, module in PUBLIC.items():
        by_section.setdefault(API_SECTIONS[module], []).append(f"::: {module}.{name}")
    for section, directives in by_section.items():
        lines += [f"## {section}", ""]
        for directive in directives:
            lines += [directive, ""]
    return "\n".join(lines)

"""The workbench project file and the paths an item of a project names (FR-32)."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from nanopnp.core.paths import names_a_path
from nanopnp.io.case import CORRECTION_PROPERTIES
from nanopnp.io.case_paths import path_fields
from nanopnp.io.store import atomic_write_bytes

PROJECT_SCHEMA = "nanopnp/project/v0.6"

PROJECT_FILENAME = "nanopnp-project.yaml"

ITEM_NAME = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
"""What an item's name may be: it is the item's file stem."""

ItemKind = Literal["molecular", "continuum", "physics", "study", "comparison"]

ITEM_KINDS: tuple[ItemKind, ...] = ("molecular", "continuum", "physics", "study", "comparison")

FOLDERS: dict[ItemKind, str] = {
    "molecular": "models/molecular",
    "continuum": "models/continuum",
    "physics": "models/physics",
    "study": "studies",
    "comparison": "comparisons",
}
"""The folder of each kind of item, beside the project file."""

INPUTS_FOLDER = "inputs"

RUNS_FOLDER = "runs"

SWEEPS_FOLDER = "sweeps"

STORE_FOLDER = "store"

Suite = Literal["molecular", "continuum", "study", "analysis"]

SUITES: tuple[Suite, ...] = ("molecular", "continuum", "study", "analysis")

ITEM_SUITES: dict[ItemKind, Suite] = {
    "molecular": "molecular",
    "continuum": "continuum",
    # The Continuum suite holds the physics defaults until the frame gives physics its own suite.
    "physics": "continuum",
    "study": "study",
    "comparison": "analysis",
}
"""The suite whose tools edit each kind of item."""


class ProjectFormatError(ValueError):
    """A project file is not a project file of this release."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SuiteLayout(_Strict):
    """How one suite's window is divided, saved with the project."""

    rail_percent: float = Field(default=18.0, gt=0.0, lt=100.0)
    bottom_percent: float = Field(default=25.0, gt=0.0, lt=100.0)
    rail_folded: bool = False
    bottom_folded: bool = True


class Library(_Strict):
    """The names of a project's items, by kind; the folder is the truth."""

    molecular: list[str] = Field(default_factory=list)
    continuum: list[str] = Field(default_factory=list)
    physics: list[str] = Field(default_factory=list)
    studies: list[str] = Field(default_factory=list)
    comparisons: list[str] = Field(default_factory=list)


LIBRARY_FIELDS: dict[ItemKind, str] = {
    "molecular": "molecular",
    "continuum": "continuum",
    "physics": "physics",
    "study": "studies",
    "comparison": "comparisons",
}


class ProjectFile(_Strict):
    """The project file: names and a layout, and no physics."""

    schema_: str = Field(default=PROJECT_SCHEMA, alias="schema")
    name: str
    library: Library = Field(default_factory=Library)
    open: list[str] = Field(default_factory=list)
    current: str | None = None
    layout: dict[Suite, SuiteLayout] = Field(default_factory=dict)
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def names(self, kind: ItemKind) -> list[str]:
        """Return the indexed names of one kind."""
        found: list[str] = getattr(self.library, LIBRARY_FIELDS[kind])
        return found


def valid_name(name: str) -> bool:
    """Return whether ``name`` may name an item."""
    return re.fullmatch(ITEM_NAME, name) is not None


def read_project(folder: str | Path) -> ProjectFile:
    """Read the project file of ``folder``; ProjectFormatError if it is not one."""
    path = Path(folder) / PROJECT_FILENAME
    if not path.is_file():
        raise ProjectFormatError(f"{folder} holds no {PROJECT_FILENAME}, so it is not a project")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ProjectFormatError(f"{path}: not readable as YAML: {error}") from None
    if not isinstance(raw, Mapping):
        raise ProjectFormatError(f"{path}: a project file is a YAML mapping")
    if raw.get("schema") != PROJECT_SCHEMA:
        raise ProjectFormatError(
            f"{path}: expected schema {PROJECT_SCHEMA!r}, found {raw.get('schema')!r}"
        )
    try:
        return ProjectFile.model_validate(raw)
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        raise ProjectFormatError(f"{path}: {where}: {first['msg']}") from None


def write_project(folder: str | Path, project: ProjectFile) -> Path:
    """Write the project file of ``folder`` atomically, and return its path."""
    target = Path(folder) / PROJECT_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(project.model_dump(by_alias=True, mode="json"), sort_keys=False)
    atomic_write_bytes(target, text.encode("utf-8"))
    return target


def item_reference(kind: ItemKind, name: str) -> str:
    """Return an item as the project file writes it: ``<kind>/<name>``."""
    return f"{kind}/{name}"


def split_reference(reference: str) -> tuple[ItemKind, str]:
    """Return the kind and name of ``<kind>/<name>``; ValueError if it is neither."""
    kind, _, name = reference.partition("/")
    if kind not in ITEM_KINDS or not name:
        raise ValueError(
            f"{reference!r} is not <kind>/<name> with a kind of {', '.join(ITEM_KINDS)}"
        )
    return kind, name


def _input_fields() -> tuple[str, ...]:
    own = tuple(path for path in path_fields() if not path.startswith("models."))
    corrections = ["electrolyte.parameters"]
    corrections += [f"electrolyte.corrections.{name}.model" for name in CORRECTION_PROPERTIES]
    return own + tuple(corrections)


def item_inputs(body: Mapping[str, Any]) -> dict[str, str]:
    """Return the input files an item's mapping names, by dotted case path, as written."""
    found: dict[str, str] = {}
    for dotted in _input_fields():
        value = _at(body, dotted)
        if not isinstance(value, str):
            continue
        # A correction name that is not a path is an installed file's, not an input.
        if dotted.startswith("electrolyte.") and not names_a_path(value):
            continue
        found[dotted] = value
    return found


def rewrite_inputs(
    body: dict[str, Any], rewrite: Callable[[str, str], str | None]
) -> dict[str, str]:
    """Replace each input path of ``body`` in place by what ``rewrite(dotted, value)`` returns.

    A ``None`` leaves the value. The result maps each changed path to its new value.
    """
    changed: dict[str, str] = {}
    for dotted, value in item_inputs(body).items():
        replacement = rewrite(dotted, value)
        if replacement is None or replacement == value:
            continue
        *parents, last = dotted.split(".")
        cursor: Any = body
        for part in parents:
            cursor = cursor[part]
        cursor[last] = replacement
        changed[dotted] = replacement
    return changed


def _at(body: Mapping[str, Any], dotted: str) -> object:
    cursor: object = body
    for part in dotted.split("."):
        if not isinstance(cursor, Mapping) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor

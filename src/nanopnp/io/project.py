"""The workbench project file, its folders and the names its items are referred to by."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator

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

Suite = Literal["molecular", "continuum", "physics", "study", "analysis"]

SUITES: tuple[Suite, ...] = ("molecular", "continuum", "physics", "study", "analysis")

ITEM_SUITES: dict[ItemKind, Suite] = {
    "molecular": "molecular",
    "continuum": "continuum",
    "physics": "physics",
    "study": "study",
    "comparison": "analysis",
}
"""The suite whose tools edit each kind of item."""


class ProjectFormatError(ValueError):
    """A project file is not a project file of this release."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SuiteLayout(_Strict):
    """How one suite's window is divided, in pixels, saved with the project."""

    rail_px: int = Field(default=240, ge=160, le=480)
    bottom_px: int = Field(default=220, ge=120, le=560)
    rail_folded: bool = False
    bottom_folded: bool = True

    @model_validator(mode="before")
    @classmethod
    def _drop_percentages(cls, data: object) -> object:
        # An earlier release saved the sizes in percent of the window; they restart at the defaults.
        if isinstance(data, Mapping):
            return {k: v for k, v in data.items() if k not in ("rail_percent", "bottom_percent")}
        return data


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
    """The project file: names, a layout and the project's settings, and no physics.

    The workbench checks ``settings`` against its declared list; this file only carries them.
    """

    schema_: str = Field(default=PROJECT_SCHEMA, alias="schema")
    name: str
    library: Library = Field(default_factory=Library)
    open: list[str] = Field(default_factory=list)
    current: str | None = None
    layout: dict[Suite, SuiteLayout] = Field(default_factory=dict)
    settings: dict[str, JsonValue] = Field(default_factory=dict)
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

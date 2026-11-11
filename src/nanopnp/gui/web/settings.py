"""The workbench's settings: one declared list, the user's file, and a project's values over it."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import Field, JsonValue, TypeAdapter, ValidationError

from nanopnp.core.paths import RECENT_PROJECTS_KEPT, config_root
from nanopnp.io.store import atomic_write_bytes

__all__ = [
    "SECTIONS",
    "SETTINGS",
    "SETTINGS_FILENAME",
    "Setting",
    "Settings",
    "load",
    "register",
    "rows",
    "save",
    "search",
    "write_atomically",
]

SETTINGS_FILENAME = "workbench.yaml"

logger = logging.getLogger(__name__)

Scope = Literal["user", "project", "both"]
"""Whose file holds a setting: the user's, the project's, or either, the project's winning."""

Applies = Literal["at once", "next run", "next start"]

SECTIONS: dict[str, str] = {
    "appearance": "Appearance and accessibility",
    "keyboard": "Keyboard and editing guards",
    "runs": "Runs and storage",
    "numbers": "Units and numbers",
}
"""The settings page's sections, by identifier, in the order it lists them."""


@dataclass(frozen=True)
class Setting:
    """One setting: where it is listed, whose file holds it, its default and its values.

    Parameters
    ----------
    keywords
        The words the search and the palette find it by, besides its title and description.
    adapter
        Validates a value read from a file or entered on the page.
    choices
        Each allowed value and its label, where the values are a list.
    applies
        When a change takes effect: ``at once``, at the ``next run`` or at the ``next start``.
    """

    id: str
    section: str
    title: str
    description: str
    keywords: tuple[str, ...]
    scope: Scope
    default: JsonValue
    adapter: TypeAdapter[Any]
    choices: Mapping[str, str] | None = None
    applies: Applies = "at once"

    def validate(self, value: object) -> JsonValue:
        """Return ``value`` checked against the setting; ValidationError where it is not one."""
        checked: JsonValue = self.adapter.validate_python(value)
        return checked

    @property
    def per_project(self) -> bool:
        """Whether a project may set it."""
        return self.scope in ("project", "both")

    def words(self) -> str:
        """Return the text a search reads: title, description and keywords, in lower case."""
        return " ".join((self.title, self.description, *self.keywords)).lower()


SETTINGS: dict[str, Setting] = {}
"""Every declared setting, by identifier; a later package or a plugin adds to it."""


def register(setting: Setting) -> Setting:
    """Declare a setting; ValueError for a taken identifier, an unknown section or a bad default."""
    if setting.id in SETTINGS:
        raise ValueError(f"the setting {setting.id!r} is declared already")
    if setting.section not in SECTIONS:
        raise ValueError(f"{setting.id}: no section {setting.section!r}")
    setting.validate(setting.default)
    if setting.choices is not None and setting.default not in setting.choices:
        raise ValueError(f"{setting.id}: the default {setting.default!r} is not a choice")
    SETTINGS[setting.id] = setting
    return setting


def search(text: str) -> tuple[Setting, ...]:
    """Return the settings whose title, description or keywords hold every word of ``text``."""
    words = text.lower().split()
    return tuple(s for s in SETTINGS.values() if all(word in s.words() for word in words))


def rows(section: str) -> tuple[Setting, ...]:
    """Return one section's settings, in the order they were declared."""
    return tuple(s for s in SETTINGS.values() if s.section == section)


_BOOL: TypeAdapter[Any] = TypeAdapter(bool)

register(
    Setting(
        "theme",
        "appearance",
        "Theme",
        "The colours of every screen: the system's light or dark, or a theme.",
        ("colour", "color", "dark", "light", "palette"),
        "user",
        "system",
        TypeAdapter(Annotated[str, Field(min_length=1, max_length=64)]),
        {"system": "Follow the system", "light": "Light", "dark": "Dark"},
    )
)
register(
    Setting(
        "density",
        "appearance",
        "Density",
        "How tall the rows and controls are.",
        ("compact", "rows", "size"),
        "user",
        "medium",
        TypeAdapter(Literal["medium", "compact"]),
        {"medium": "Medium", "compact": "Compact"},
    )
)
register(
    Setting(
        "spacing",
        "appearance",
        "Spacing",
        "How much room the panels leave between groups.",
        ("tight", "padding", "gaps"),
        "user",
        "default",
        TypeAdapter(Literal["default", "tight"]),
        {"default": "Default", "tight": "Tight"},
    )
)
register(
    Setting(
        "charge_colours",
        "appearance",
        "Charge colours",
        "Which colour a positive charge takes in the 3D view and on the charge map; a negative "
        "one takes the other.",
        ("colour map", "red", "blue", "positive", "negative", "electrostatics"),
        "user",
        "blue-positive",
        TypeAdapter(Literal["blue-positive", "red-positive"]),
        {
            "blue-positive": "Positive blue, negative red",
            "red-positive": "Positive red, negative blue",
        },
    )
)
register(
    Setting(
        "viewer_background",
        "appearance",
        "3D view background",
        "The background of the molecule and mesh views.",
        ("viewer", "canvas", "black", "white"),
        "user",
        "near-black",
        TypeAdapter(Literal["near-black", "theme", "white"]),
        {"near-black": "Near-black", "theme": "The theme's", "white": "White"},
    )
)
register(
    Setting(
        "reduced_motion",
        "appearance",
        "Reduced motion",
        "Whether panels and menus animate.",
        ("animation", "motion", "accessibility"),
        "user",
        "system",
        TypeAdapter(Literal["system", "on", "off"]),
        {"system": "Follow the system", "on": "Reduce motion", "off": "Full motion"},
    )
)
register(
    Setting(
        "keys",
        "keyboard",
        "Keyboard shortcuts",
        "The chord each command runs.",
        ("shortcuts", "keybindings", "chords", "hotkeys"),
        "user",
        {},
        TypeAdapter(dict[str, str]),
    )
)
register(
    Setting(
        "confirm",
        "keyboard",
        "Ask before resetting or quitting",
        "Reset, Reset layout and Quit ask first.",
        ("guard", "confirm", "reset", "quit"),
        "user",
        True,
        _BOOL,
    )
)
register(
    Setting(
        "recent_projects",
        "runs",
        "Recent projects",
        "How many recent projects the welcome screen and the dialogs list.",
        ("recent", "history", "projects"),
        "user",
        8,
        TypeAdapter(Annotated[int, Field(ge=1, le=RECENT_PROJECTS_KEPT)]),
    )
)
register(
    Setting(
        "open_last_project",
        "runs",
        "Open the last project at start",
        "Opens the project used last when the workbench starts without one.",
        ("startup", "start", "reopen", "projects"),
        "user",
        True,
        _BOOL,
        applies="next start",
    )
)
register(
    Setting(
        "store_cap_gb",
        "runs",
        "Store size cap (GB)",
        "Removes the least recently used results no run uses once the store is larger.",
        ("store", "disk", "cache", "storage", "limit", "clean"),
        "both",
        None,
        TypeAdapter(Annotated[float, Field(ge=0.5, le=10_000)] | None),
        applies="next run",
    )
)
register(
    Setting(
        "significant_figures",
        "numbers",
        "Significant figures",
        "How many figures a number is shown with; the stored value keeps every one.",
        ("digits", "precision", "figures", "numbers"),
        "both",
        4,
        TypeAdapter(Annotated[int, Field(ge=2, le=10)]),
    )
)
register(
    Setting(
        "number_style",
        "numbers",
        "Number style",
        "Whether a number is shown with a unit prefix or a power of ten.",
        ("prefixes", "powers", "scientific", "units", "numbers"),
        "both",
        "prefixes",
        TypeAdapter(Literal["prefixes", "powers"]),
        {"prefixes": "Unit prefixes (12.5 nm)", "powers": "Powers of ten (1.25e-8 m)"},
    )
)


def _valid(values: Mapping[str, object], where: str, *, project: bool) -> dict[str, JsonValue]:
    kept: dict[str, JsonValue] = {}
    for key, value in values.items():
        setting = SETTINGS.get(str(key))
        if setting is None or (project and not setting.per_project):
            logger.warning("%s: ignoring %r, which is no setting here", where, key)
            continue
        try:
            kept[setting.id] = setting.validate(value)
        except ValidationError as error:
            logger.warning("%s: ignoring %s: %s", where, setting.id, error.errors()[0]["msg"])
    return kept


@dataclass(frozen=True)
class Settings:
    """The user's values, and a project's over them where a setting's scope allows."""

    user: Mapping[str, JsonValue] = field(default_factory=dict)
    project: Mapping[str, JsonValue] = field(default_factory=dict)

    def value(self, identifier: str) -> JsonValue:
        """Return a setting's value: the project's, else the user's, else the default."""
        setting = SETTINGS[identifier]
        if setting.per_project and identifier in self.project:
            return self.project[identifier]
        return self.user.get(identifier, setting.default)

    def source(self, identifier: str) -> Literal["project", "user", "default"]:
        """Return whose value :meth:`value` gives."""
        if SETTINGS[identifier].per_project and identifier in self.project:
            return "project"
        return "user" if identifier in self.user else "default"

    def with_user(self, identifier: str, value: object) -> Settings:
        """Return these settings with the user's value of one setting replaced, checked first."""
        return Settings(
            {**self.user, identifier: SETTINGS[identifier].validate(value)}, self.project
        )

    def without_user(self, identifier: str) -> Settings:
        """Return these settings with the user's value of one setting back at its default."""
        return Settings({k: v for k, v in self.user.items() if k != identifier}, self.project)

    def with_project(self, values: Mapping[str, object], where: str = "the project") -> Settings:
        """Return the user's values with a project's over them; an invalid value is dropped."""
        return Settings(self.user, _valid(values, where, project=True))

    @property
    def theme(self) -> str:
        """The chosen theme's name, or ``system``."""
        return str(self.value("theme"))

    @property
    def density(self) -> str:
        """``medium`` or ``compact``."""
        return str(self.value("density"))

    @property
    def spacing(self) -> str:
        """``default`` or ``tight``."""
        return str(self.value("spacing"))

    @property
    def viewer_background(self) -> str:
        """``near-black``, ``theme`` or ``white``."""
        return str(self.value("viewer_background"))

    @property
    def reduced_motion(self) -> str:
        """``system``, ``on`` or ``off``."""
        return str(self.value("reduced_motion"))

    @property
    def keys(self) -> dict[str, str]:
        """The user's key bindings, by command identifier."""
        chosen = self.value("keys")
        return {str(k): str(v) for k, v in chosen.items()} if isinstance(chosen, dict) else {}


def write_atomically(target: Path, text: str) -> None:
    """Write ``text`` to ``target`` through a temporary file, so a reader never sees half of it."""
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(target, text.encode("utf-8"))


def load() -> Settings:
    """Read the user's settings; each entry is checked alone, and one that fails is dropped."""
    path = config_root() / SETTINGS_FILENAME
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return Settings()
    except (OSError, yaml.YAMLError) as error:
        logger.warning("ignoring the settings in %s: %s", path, error)
        return Settings()
    if not isinstance(raw, Mapping):
        logger.warning("ignoring the settings in %s: not a mapping", path)
        return Settings()
    return Settings(_valid(raw, str(path), project=False))


def save(settings: Settings) -> Path:
    """Write the user's values and return the file; a project's values stay in its own file."""
    path = config_root() / SETTINGS_FILENAME
    write_atomically(path, yaml.safe_dump(dict(settings.user), sort_keys=False))
    return path

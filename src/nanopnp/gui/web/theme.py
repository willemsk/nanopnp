"""The workbench's themes: the two shipped with the tokens, and the user's own."""

from __future__ import annotations

import functools
import json
import logging
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from nanopnp.core.paths import config_root
from nanopnp.gui.web.assets import TOKENS
from nanopnp.gui.web.settings import Settings, write_atomically

__all__ = [
    "THEME_SCHEMA",
    "Theme",
    "appearance",
    "css",
    "dark",
    "duplicate",
    "load",
    "save",
    "script_json",
    "shipped",
    "user_themes",
]

THEME_SCHEMA: Literal["nanopnp/workbench-theme/v0.6"] = "nanopnp/workbench-theme/v0.6"
THEMES_FOLDER = "themes"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
TOKEN_NAME = re.compile(r"^[a-z0-9-]+$")
_TOKEN = re.compile(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;")

logger = logging.getLogger(__name__)


class Theme(BaseModel):
    """A theme: a base (light or dark) and the colour tokens it sets over the default's."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["nanopnp/workbench-theme/v0.6"] = Field(default=THEME_SCHEMA, alias="schema")
    name: str
    base: Literal["light", "dark"]
    colours: dict[str, str] = {}


def _block(text: str, opener: str) -> str:
    start = text.index(opener)
    return text[start : text.index("}", start)]


def shipped() -> dict[str, Theme]:
    """Return the light and dark themes, read from the tokens the pages load."""
    return {name: theme.model_copy(deep=True) for name, theme in _shipped().items()}


@functools.cache
def _shipped() -> dict[str, Theme]:
    text = TOKENS.read_text(encoding="utf-8")
    light = dict(_TOKEN.findall(_block(text, ":root {")))
    dark = {**light, **dict(_TOKEN.findall(_block(text, ':root[data-theme="dark"]')))}
    return {
        "light": Theme(name="light", base="light", colours=light),
        "dark": Theme(name="dark", base="dark", colours=dark),
    }


def _folder() -> Path:
    return config_root() / THEMES_FOLDER


def user_themes() -> dict[str, Theme]:
    """Return the user's themes by name; a file that does not read is left out.

    Read again only when a theme file changed, by the newest modification time in its folder.
    """
    folder = _folder()
    try:
        stamp = (
            max((path.stat().st_mtime_ns for path in folder.glob("*.yaml")), default=0),
            folder.stat().st_mtime_ns,
        )
    except OSError:
        stamp = (0, 0)
    cached = _USER_THEMES.get(folder)
    if cached is not None and cached[0] == stamp:
        return {name: theme.model_copy(deep=True) for name, theme in cached[1].items()}
    found = _read_user_themes(folder)
    _USER_THEMES[folder] = (stamp, found)
    return {name: theme.model_copy(deep=True) for name, theme in found.items()}


_USER_THEMES: dict[Path, tuple[tuple[int, int], dict[str, Theme]]] = {}


def _read_user_themes(folder: Path) -> dict[str, Theme]:
    found: dict[str, Theme] = {}
    for path in sorted(folder.glob("*.yaml")):
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
            theme = Theme.model_validate(raw)
        except (OSError, yaml.YAMLError, ValidationError) as error:
            logger.warning("ignoring the theme %s: %s", path, error)
            continue
        if theme.name == path.stem and NAME.match(theme.name):
            found[theme.name] = theme
    return found


def load(name: str) -> Theme | None:
    """Return the theme of this name, a user's or a shipped one, or None."""
    return {**shipped(), **user_themes()}.get(name)


def save(theme: Theme) -> Path:
    """Write a user's theme; its name, base and colours are checked first.

    Raises
    ------
    ValueError
        If the name is not a file name, shadows a shipped theme, or a colour is not ``#rrggbb``
        or not a token of the default theme.
    """
    if not NAME.match(theme.name) or theme.name in shipped():
        raise ValueError(f"{theme.name!r} is not a name for a theme of your own")
    known = shipped()["light"].colours
    for token, value in theme.colours.items():
        if token not in known or not HEX.match(value):
            raise ValueError(f"{token}: {value!r} is not a colour token set to #rrggbb")
    path = _folder() / f"{theme.name}.yaml"
    dumped = theme.model_dump(mode="json", by_alias=True)
    write_atomically(path, yaml.safe_dump(dumped, sort_keys=False))
    _USER_THEMES.clear()
    return path


def duplicate(source: Theme) -> Theme:
    """Save a copy of a theme under a free name, ``<name>-copy``, and return it."""
    taken = {*shipped(), *user_themes()}
    name, number = f"{source.name}-copy", 1
    while name in taken:
        number += 1
        name = f"{source.name}-copy-{number}"
    theme = Theme(name=name, base=source.base, colours=dict(source.colours))
    save(theme)
    return theme


def script_json(value: object) -> str:
    """Return ``value`` as JSON that is safe inside an inline ``<script>`` element."""
    return json.dumps(value).replace("<", "\\u003c")


def css(theme: Theme) -> str:
    """Return the style rule that sets a user theme's colours on the root it is chosen for.

    A theme file is read from disk and may be hand-edited or shared, so only a token name and a
    ``#rrggbb`` value, as ``save`` accepts, reach the page.
    """
    lines = "".join(
        f"--{token}:{value};"
        for token, value in theme.colours.items()
        if TOKEN_NAME.match(token) and HEX.match(value)
    )
    return f':root[data-user-theme="{theme.name}"][data-theme]{{{lines}}}'


# The 3D view's background is a token of its own, which the setting points at the theme or white.
_VIEWER = {
    "near-black": "",
    "theme": ":root{--canvas-3d:var(--canvas-plot);--canvas-3d-ink:var(--canvas-plot-ink)}",
    "white": ":root{--canvas-3d:#ffffff;--canvas-3d-ink:#16181d}",
}


_MOTION = {"on": "reduce", "off": "full"}


def dark(settings: Settings) -> bool | None:
    """Return whether Quasar draws dark: None follows the system, else the chosen theme's base."""
    chosen = load(settings.theme)
    return None if chosen is None else chosen.base == "dark"


def appearance(settings: Settings) -> str:
    """Return the script that sets the root's theme, density, spacing and motion, and the colours.

    A theme of the user's that is gone leaves the system's choice. The script runs in the head,
    before the first paint, and again when the settings change.
    """
    chosen = load(settings.theme)
    rules = _VIEWER[settings.viewer_background]
    if chosen is not None and chosen.name not in shipped():
        rules = css(chosen) + rules
    attributes = {
        "data-theme": chosen.base if chosen is not None else None,
        "data-user-theme": chosen.name
        if chosen is not None and chosen.name not in shipped()
        else None,
        "data-density": "compact" if settings.density == "compact" else None,
        "data-spacing": "tight" if settings.spacing == "tight" else None,
        "data-motion": _MOTION.get(settings.reduced_motion),
    }
    return (
        "(()=>{const r=document.documentElement;"
        f"for(const [k,v] of Object.entries({script_json(attributes)}))"
        "{if(v===null){r.removeAttribute(k)}else{r.setAttribute(k,v)}}"
        "let s=document.getElementById('user-theme');"
        "if(!s){s=document.createElement('style');s.id='user-theme';document.head.appendChild(s)}"
        f"s.textContent={script_json(rules)};}})();"
    )

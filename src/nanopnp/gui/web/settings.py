"""The user's workbench settings: theme, density, spacing, viewer background and key bindings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from nanopnp.core.paths import config_root
from nanopnp.io.store import atomic_write_bytes

__all__ = ["SETTINGS_FILENAME", "Settings", "load", "save", "write_atomically"]

SETTINGS_FILENAME = "workbench.yaml"

logger = logging.getLogger(__name__)


class Settings(BaseModel):
    """What the user sets once for every project (WB-18, WB-19, WB-30, WB-31)."""

    model_config = ConfigDict(extra="forbid")

    theme: str = "system"
    density: Literal["medium", "compact"] = "medium"
    spacing: Literal["default", "tight"] = "default"
    viewer_background: Literal["near-black", "theme", "white"] = "near-black"
    keys: dict[str, str] = {}


def write_atomically(target: Path, text: str) -> None:
    """Write ``text`` to ``target`` through a temporary file, so a reader never sees half of it."""
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(target, text.encode("utf-8"))


def load() -> Settings:
    """Read the user's settings; a missing or unreadable file gives the defaults."""
    path = config_root() / SETTINGS_FILENAME
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return Settings.model_validate(raw)
    except FileNotFoundError:
        return Settings()
    except (OSError, yaml.YAMLError, ValidationError) as error:
        logger.warning("ignoring the settings in %s: %s", path, error)
        return Settings()


def save(settings: Settings) -> Path:
    """Write the user's settings and return the file."""
    path = config_root() / SETTINGS_FILENAME
    write_atomically(path, yaml.safe_dump(settings.model_dump(mode="json"), sort_keys=False))
    return path

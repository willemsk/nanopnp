"""VER-78 (l): every declared setting reaches its search, its palette command and its file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from nanopnp.api.project import Project
from nanopnp.gui.web import settings
from nanopnp.gui.web.commands import SETTING_COMMAND, setting_commands
from nanopnp.gui.web.settings import SETTINGS, SETTINGS_FILENAME, Settings

# A value away from the default for each setting; a setting declared without one fails here.
CHANGED: dict[str, Any] = {
    "theme": "dark",
    "density": "compact",
    "spacing": "tight",
    "viewer_background": "white",
    "charge_colours": "red-positive",
    "reduced_motion": "on",
    "keys": {"palette": "Ctrl+Shift+K"},
    "confirm": False,
    "recent_projects": 3,
    "open_last_project": False,
    "store_cap_gb": 2.5,
    "significant_figures": 6,
    "number_style": "powers",
}

INVALID = ["not", "a", "value"]


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "config"
    monkeypatch.setenv("NANOPNP_CONFIG", str(folder))
    return folder


@pytest.mark.parametrize("identifier", sorted(SETTINGS))
def test_ver78_every_declared_setting_reaches_its_search_its_command_and_its_file(
    identifier: str, config: Path, tmp_path: Path
) -> None:
    setting = SETTINGS[identifier]
    assert setting.validate(setting.default) == setting.default
    assert setting in settings.rows(setting.section)
    for word in setting.keywords:
        assert setting in settings.search(word), word
    opening = [c for c in setting_commands() if c.id == f"{SETTING_COMMAND}{identifier}"]
    assert len(opening) == 1
    assert setting.title in opening[0].title

    changed = CHANGED[identifier]
    assert changed != setting.default
    settings.save(Settings().with_user(identifier, changed))
    assert settings.load().value(identifier) == changed

    if setting.per_project:
        project = Project.create(tmp_path / "project")
        project.save_setting(identifier, changed)
        reopened = Project.open(project.root)
        mine = Settings().with_project(reopened.settings)
        assert mine.value(identifier) == changed
        assert mine.source(identifier) == "project"
    else:
        assert Settings().with_project({identifier: changed}).value(identifier) == setting.default

    # One entry that fails its check is dropped; the file's other entries stay.
    other = next(key for key in CHANGED if key != identifier)
    (config / SETTINGS_FILENAME).write_text(
        yaml.safe_dump({identifier: INVALID, other: CHANGED[other]}), encoding="utf-8"
    )
    read = settings.load()
    assert read.value(identifier) == setting.default
    assert read.value(other) == CHANGED[other]

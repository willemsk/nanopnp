"""Render the browser workbench: every fixture state, a 2WCD project and the shell's own states.

    uv run python .claude/scripts/gui/render_shell.py [--only <group> ...] <out-dir>

Groups, each shot light and dark:

- ``states``: every screen of every fixture state (``shell-<state>-<screen>-<scheme>``);
- ``2wcd``: every screen of a project holding example 07's dodecamer, walked to its charge by
  ``server --project`` (``shell-2wcd-<screen>-<scheme>``);
- ``extra``: the dialogs, menus, folded rail, panel tabs, settings sections, key capture, palette
  query, glossary and About, on the charged fixture (``shell-extra-<name>-<scheme>``);
- ``compact``: a few screens under a user configuration of compact density, tight spacing and a
  theme of the user's own (``shell-compact-<screen>-<scheme>``).

The 2WCD project is built once into ``cache/2wcd-<key>/`` beside ``<out-dir>``, ``key`` being 12 hex
digits of the SHA-256 of the case file and the deposited structure; its first walk fills the
project's store, so a later render reads the charge from it. A cache is built in a temporary
sibling and renamed, so a half-built one is never used. Starts one server per state, all at once,
writes ``manifest.json``, runs `shoot.cjs`, and stops the servers by closing their standard input.
Exits with `shoot.cjs`'s status (2 if a page did not load), or 1 if a server did not start.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from nanopnp.api.case import Case
from nanopnp.api.project import Project
from nanopnp.gui.web import server, theme
from nanopnp.gui.web.screens import SCREENS
from nanopnp.gui.web.settings import SETTINGS_FILENAME
from nanopnp.gui.web.states import STATES

ROOT = Path(__file__).resolve().parents[3]
SHOOT = Path(__file__).with_name("shoot.cjs")
EXAMPLE = ROOT / "examples" / "07-pdb-to-charged-run" / "2wcd.case.yaml"
PREPARE = ROOT / "examples" / "06-pdb-to-mesh" / "prepare.py"
DEPOSITED = ROOT / "tests" / "data" / "structures" / "2wcd.pdb.gz"
VIEWPORT = [1280, 800]
SCHEMES = ("light", "dark")
READY = 'body[data-screen-ready="1"]'
GROUPS = ("states", "2wcd", "extra", "compact", "molecular")
THEME_NAME = "dusk"
START_S = 1800
"""How long a server may take to print its ready line: the 2WCD walk comes before it."""

MENU = "[data-control=menu-{}]"
ITEM = '.q-menu .q-item:has-text("{}")'


def menu_item(menu: str, title: str) -> list[str]:
    """Return the clicks that open a menu and choose one of its items."""
    return [MENU.format(menu), ITEM.format(title)]


EXTRAS: tuple[tuple[str, str, list[str]], ...] = (
    ("dialog-new", "/molecular", menu_item("file", "New project")),
    ("dialog-open", "/molecular", menu_item("file", "Open project")),
    ("dialog-import", "/molecular", menu_item("file", "Import case")),
    ("dialog-export", "/molecular", menu_item("file", "Export project")),
    ("menu-file", "/molecular", [MENU.format("file")]),
    ("menu-view", "/molecular", [MENU.format("view")]),
    ("menu-help", "/molecular", [MENU.format("help")]),
    ("panel-queue", "/study?panel=queue", []),
    ("panel-log", "/study?panel=log", []),
    ("settings-background", "/settings?setting=viewer_background", []),
    ("settings-key-capture", "/settings?setting=keys", ["[data-control=key-project-new]"]),
    ("palette-empty", "/molecular", ["[data-control=palette-open]"]),
    ("palette-query", "/molecular?palette=suite", []),
    ("palette-keyword", "/molecular?palette=preferences", []),
    ("glossary", "/molecular?dialog=glossary", []),
    ("about", "/molecular?dialog=about", []),
    # Last: the fold is saved in the project, so the light shot folds the rail and the dark one,
    # after it, finds it folded (extra_entries).
    ("rail-folded", "/molecular", ["[data-control=rail-fold]"]),
)
COMPACT = ("molecular", "settings", "changes")
COMPACT_CLICKS = {"settings": ["[data-control=theme-colours] .q-item"]}


PROJECT_EXTRAS: list[tuple[str, str, list[str]]] = [
    ("m-prepare-open", "/molecular/prepare", ["[data-control=open-structure]"]),
    (
        "m-protonation-states",
        "/molecular/protonation",
        ['[data-control=tool-readout] button[aria-label^="Titratable groups"]'],
    ),
    (
        "m-protonation-warnings",
        "/molecular/protonation",
        ['[data-control=tool-readout] button[aria-label*="warnings"]'],
    ),
    ("m-view-settings", "/molecular/view", menu_item("file", "Settings")),
]
"""Windows opened over a tool of the 2WCD project, none of which writes to it."""


def cache_key() -> str:
    """Return the first 12 hex digits of the SHA-256 of the 2WCD case and its raw structure."""
    digest = hashlib.sha256()
    for source in (EXAMPLE, DEPOSITED):
        digest.update(source.read_bytes())
    return digest.hexdigest()[:12]


def build_cache(folder: Path) -> None:
    """Prepare the dodecamer, copy the case beside it and import the case into a project."""
    folder.mkdir(parents=True)
    prepared = folder / "2wcd-prepared.pdb"
    subprocess.run(
        [sys.executable, str(PREPARE), str(DEPOSITED), str(prepared)], check=True, cwd=ROOT
    )
    case = folder / EXAMPLE.name
    shutil.copy(EXAMPLE, case)
    project = Project.create(folder / "project", name="2wcd")
    project.import_case(Case.load(case))


def cached_project(out: Path) -> Path:
    """Return the 2WCD project of the cache beside ``out``, built now if it is not there."""
    cache = out.resolve().parent / "cache" / f"2wcd-{cache_key()}"
    if cache.is_dir():
        print(f"2WCD project reused from {cache}", file=sys.stderr)
    else:
        print(f"2WCD project building in {cache}", file=sys.stderr)
        pending = cache.with_name(f"{cache.name}.building-{os.getpid()}")
        shutil.rmtree(pending, ignore_errors=True)
        cache.parent.mkdir(parents=True, exist_ok=True)
        try:
            build_cache(pending)
            pending.rename(cache)
        finally:
            shutil.rmtree(pending, ignore_errors=True)
    return cache / "project"


def write_config(folder: Path) -> None:
    """Write a user configuration: compact density, tight spacing and a theme of the user's own."""
    folder.mkdir(parents=True, exist_ok=True)
    dusk = theme.shipped()["dark"].model_copy(update={"name": THEME_NAME})
    dusk.colours.update({"accent": "#c77dff", "surface": "#1d1b2e"})
    (folder / "themes").mkdir(exist_ok=True)
    dumped = dusk.model_dump(mode="json", by_alias=True)
    (folder / "themes" / f"{THEME_NAME}.yaml").write_text(
        yaml.safe_dump(dumped, sort_keys=False), encoding="utf-8"
    )
    settings = {"density": "compact", "spacing": "tight", "theme": THEME_NAME}
    (folder / SETTINGS_FILENAME).write_text(yaml.safe_dump(settings), encoding="utf-8")


def launch(*arguments: str, config: Path | None = None) -> subprocess.Popen[str]:
    """Start the workbench with these arguments, without waiting for its ready line."""
    environment = dict(os.environ)
    if config is not None:
        environment["NANOPNP_CONFIG"] = str(config)
    return subprocess.Popen(
        [sys.executable, "-m", "nanopnp.gui.web.server", "--no-browser", *arguments],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env=environment,
    )


def first_address(process: subprocess.Popen[str], *arguments: str) -> str:
    """Return the first address of a workbench launched with ``arguments``, once it is ready."""
    assert process.stdout is not None
    found = server.READY.match(process.stdout.readline().strip())
    if found is None:
        process.kill()
        raise SystemExit(f"the server started with {' '.join(arguments)} printed no ready line")
    return found.group(1)


def start(*arguments: str, config: Path | None = None) -> tuple[subprocess.Popen[str], str]:
    """Start the workbench with these arguments and return it with its first address."""
    process = launch(*arguments, config=config)
    return process, first_address(process, *arguments)


def entry(
    identifier: str, first: str, path: str, scheme: str, click: list[str] | None = None
) -> dict[str, Any]:
    """Return one manifest entry: a path of the server at ``first``, shot in a colour scheme."""
    shot: dict[str, Any] = {
        "id": f"{identifier}-{scheme}",
        "url": first.split("/?")[0] + path,
        "via": [first],
        "ready": READY,
        "viewport": VIEWPORT,
        "scheme": scheme,
        "wait_ms": 500,
    }
    if click:
        shot["click"] = click
    return shot


def states_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return every screen of every fixture state, starting a server for each."""
    manifest = []
    # All the servers start at once; each is then waited for in turn.
    launched = [(state, launch("--state", state)) for state in STATES]
    servers.extend(process for _, process in launched)
    for state, process in launched:
        first = first_address(process, "--state", state)
        for screen in SCREENS:
            for scheme in SCHEMES:
                manifest.append(entry(f"shell-{state}-{screen.id}", first, screen.path, scheme))
    return manifest


def project_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return every screen of the cached 2WCD project, walked to its charge."""
    process, first = start("--project", str(cached_project(out)))
    servers.append(process)
    return [
        entry(f"shell-2wcd-{screen.id}", first, screen.path, scheme)
        for screen in SCREENS
        for scheme in SCHEMES
    ] + [
        entry(f"shell-2wcd-{name}", first, path, scheme, click)
        for name, path, click in PROJECT_EXTRAS
        for scheme in SCHEMES
    ]


def extra_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return the shell's own states on the charged fixture."""
    process, first = start("--state", "charged-tube")
    servers.append(process)
    return [
        entry(
            f"shell-extra-{name}",
            first,
            path,
            scheme,
            [] if name == "rail-folded" and scheme != SCHEMES[0] else click,
        )
        for name, path, click in EXTRAS
        for scheme in SCHEMES
    ]


def compact_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return a few screens under a user configuration of compact density and a user theme."""
    config = out.resolve() / "config"
    write_config(config)
    process, first = start("--state", "charged-tube", config=config)
    servers.append(process)
    return [
        entry(
            f"shell-compact-{screen.id}", first, screen.path, scheme, COMPACT_CLICKS.get(screen.id)
        )
        for screen in SCREENS
        if screen.id in COMPACT
        for scheme in SCHEMES
    ]


OFF_AXIS_A = 5.0
"""How far the refused project's structure is moved off the z axis, in Å: past the `z` budget."""

BUILD = "[data-control=tool-build]"


def molecular_project(out: Path, name: str, *, off_axis: bool) -> Path:
    """Return a project holding only the cached 2WCD molecular model, its store empty.

    With ``off_axis`` the structure is moved off z and the model asks for ``axis: z``, so its
    stage 1 is refused at the displacement gate.
    """
    source = cached_project(out)
    folder = out.resolve() / "projects" / name
    if folder.exists():
        shutil.rmtree(folder)
    Project.create(folder, name=name)
    (model,) = sorted((source / "models" / "molecular").glob("*.yaml"))
    shutil.copy(model, folder / "models" / "molecular" / model.name)
    shutil.copytree(source / "inputs", folder / "inputs", dirs_exist_ok=True)
    project = Project.open(folder)
    if off_axis:
        (structure,) = sorted((folder / "inputs").glob("*.pdb"))
        moved = []
        for line in structure.read_text(encoding="utf-8").splitlines():
            if line.startswith(("ATOM", "HETATM")):
                line = f"{line[:30]}{float(line[30:38]) + OFF_AXIS_A:8.3f}{line[38:]}"
            moved.append(line)
        structure.write_text("\n".join(moved) + "\n", encoding="utf-8")
        project.set_value("molecular", model.stem, "structure.symmetry.axis", "z")
    return folder


def molecular_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return the Molecular tools refused at stage 1 and held mid-build, on 2WCD.

    The built and the empty tools are the ``2wcd`` and ``states`` groups' ``m-<tool>`` shots.
    """
    manifest = []
    for name, path, wait_ms in (
        ("refused", "/molecular/prepare", 45000),
        ("building", "/molecular/protonation", 2500),
    ):
        # One project per shot: a second build of the same model would find the first's state.
        for scheme in SCHEMES:
            folder = molecular_project(out, f"{name}-{scheme}", off_axis=name == "refused")
            process, first = start("--project", str(folder))
            servers.append(process)
            shot = entry(f"shell-molecular-{name}", first, path, scheme, [BUILD])
            shot["wait_ms"] = wait_ms
            manifest.append(shot)
    return manifest


GROUP_ENTRIES = {
    "states": states_entries,
    "2wcd": project_entries,
    "extra": extra_entries,
    "compact": compact_entries,
    "molecular": molecular_entries,
}


def main(argv: list[str]) -> int:
    """Shoot the shell into the directory named last in ``argv``."""
    groups = list(GROUPS)
    if argv[:1] == ["--only"]:
        groups = []
        argv = argv[1:]
        while argv and argv[0] in GROUPS:
            groups.append(argv.pop(0))
    if len(argv) != 1 or not groups:
        print(__doc__)
        return 64
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    servers: list[subprocess.Popen[str]] = []
    manifest: list[dict[str, Any]] = []
    try:
        # The groups start their servers side by side: a server's start is its imports, and the
        # 2WCD project's is its walk.
        # Two groups read the 2WCD cache, so it is built before they start side by side.
        if {"2wcd", "molecular"} & set(groups):
            cached_project(out)
        with ThreadPoolExecutor(len(groups)) as pool:
            pending = [pool.submit(GROUP_ENTRIES[group], out, servers) for group in groups]
            for future in pending:
                manifest += future.result()
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return subprocess.run(["node", str(SHOOT), str(out / "manifest.json"), str(out)]).returncode
    finally:
        for process in servers:
            if process.stdin is not None:
                process.stdin.close()
        for process in servers:
            process.wait(30)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

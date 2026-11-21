"""Render the browser workbench: every fixture state, a 2WCD project and the shell's own states.

    uv run python .claude/scripts/gui/render_shell.py [--only <group> ...] <out-dir>

Groups, each shot light and dark:

- ``states``: every screen of every fixture state (``shell-<state>-<screen>-<scheme>``);
- ``2wcd``: every screen of a project holding example 07's dodecamer, walked to its charge by
  ``server --project`` (``shell-2wcd-<screen>-<scheme>``);
- ``extra``: the dialogs, menus, folded rail, panel tabs, settings sections, key capture, palette
  query, glossary and About, on the charged fixture (``shell-extra-<name>-<scheme>``);
- ``compact``: a few screens under a user configuration of compact density, tight spacing and a
  theme of the user's own (``shell-compact-<screen>-<scheme>``);
- ``molecular`` and ``continuum``: their tools refused and mid-build, on 2WCD (``continuum``: a
  continuum model whose stage 4 is refused and one held mid-build, shown in Meso's Outline, where
  stage 4 builds);
- ``meso``: the Meso tools on a copy of the 2WCD project, its continuum model's charge case walked
  to its charge with a run record and its deployed charge drawn: each tool, Density's residue list
  after a point is picked, a residue picked on Charge map, the deployed charge, one subunit, the
  overlay of the charge in 3D and of its mean about the axis, and last an Outline edit moving the
  narrowest vertex into the protein, with the residues it moves (``shell-meso-<name>-<scheme>``);
- ``physics``: the Physics tools on example 01's project with the charged tube beside it, its
  study walked to its charge: each tool, a role picked, a change of model's note, a new model with
  no salt, and the shown study refusing the model (``shell-physics-<name>-<scheme>``).
- ``study``: the Study tools on a copy of the 2WCD project, its study walked to its charge with a
  run record, and a sweep over the bias: each tool, the whole case and *New study*; then the charged
  tube run once from Study setup and its convergence in Runs (``shell-study-<name>-<scheme>``).
- ``analysis``: the Analysis tools on a copy of the 2WCD project holding its study solved, swept
  over the bias, a linked variant with one residue neutral solved in a study of its own, and a
  comparison of the two studies' runs: each tool, a cut, a probe, the field on the mesh, a sweep
  point, the variant's study, the comparison's three views, and a copy whose store was cleaned,
  where a run offers *Rebuild* (``shell-analysis-<name>-<scheme>``).

The 2WCD project is built once into ``cache/2wcd-<key>/`` beside ``<out-dir>``, ``key`` being 12 hex
digits of the SHA-256 of the case file and the deposited structure; its first walk fills the
project's store, so a later render reads the charge from it. The analysis project is built once
into ``cache/analysis-<key>/`` from a copy of it, its solves and fields written. A cache is built
in a temporary sibling and renamed, so a half-built one is never used. Starts one server per
state, all at once, writes ``manifest.json``, runs `shoot.cjs`, and stops the servers by closing
their standard input. Exits with `shoot.cjs`'s status (2 if a page did not load), or 1 if a
server did not start.
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
from nanopnp.api.session import Session
from nanopnp.api.sweep import run_plan
from nanopnp.gui.render import (
    ChargeRequest,
    FieldsRequest,
    RenderRequest,
    render,
    render_charge_elements,
    render_fields,
)
from nanopnp.gui.web import server, theme
from nanopnp.gui.web.analysis import AnalysisModel, quantities_of, scene_field
from nanopnp.gui.web.analysis_tools import comparison_maps, map_of
from nanopnp.gui.web.runs import write_sweep
from nanopnp.gui.web.screens import SCREENS
from nanopnp.gui.web.settings import SETTINGS_FILENAME
from nanopnp.gui.web.states import STATES
from nanopnp.io.project import STORE_FOLDER
from nanopnp.io.store import Store
from nanopnp.pipeline.run import RunResult
from nanopnp.post.fields import FIELD_ALIASES, joint_size_range
from nanopnp.sweep.collect import collect
from nanopnp.sweep.document import Axis, load_sweep
from nanopnp.sweep.plan import build_plan, write_plan
from nanopnp.validation.charged_tube import write_charged_tube

ROOT = Path(__file__).resolve().parents[3]
SHOOT = Path(__file__).with_name("shoot.cjs")
EXAMPLE = ROOT / "examples" / "07-pdb-to-charged-run" / "2wcd.case.yaml"
QUICKSTART = ROOT / "examples" / "01-quickstart" / "quickstart.case.yaml"
PREPARE = ROOT / "examples" / "06-pdb-to-mesh" / "prepare.py"
DEPOSITED = ROOT / "tests" / "data" / "structures" / "2wcd.pdb.gz"
VIEWPORT = [1280, 800]
SCHEMES = ("light", "dark")
READY = 'body[data-screen-ready="1"]'
GROUPS = (
    "states",
    "2wcd",
    "extra",
    "compact",
    "molecular",
    "meso",
    "continuum",
    "physics",
    "study",
    "analysis",
)
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
    (
        "c-mesh-sicn",
        "/continuum/mesh",
        [
            "[data-control=plane-colour]",
            ".q-menu .q-item:nth-child(2)",
            "[data-control=histogram-bar]:nth-child(10)",
        ],
    ),
    ("c-mesh-part", "/continuum/mesh", ["[data-control=mesh-part-protein]"]),
    (
        "c-region-domain",
        "/continuum/region",
        ["[data-control=region-domain]", ".q-menu .q-item:nth-child(3)"],
    ),
    # Last: the edit is held by the server, so every shot after it would show it.
    ("m-outline-edit", "/meso/outline", ["[data-control=contour-start]"]),
]
"""Windows opened over a tool of the 2WCD project, none of which writes to it."""

HELD = frozenset({"m-outline-edit"})
"""The extras whose click leaves a state the server holds for the shots after it."""
HELD_WAIT_MS = 2500
"""How long a held extra's shot waits: the editor's pane is drawn after the plane's key."""


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


def filled_cache(out: Path) -> Path:
    """Return the cached 2WCD project with its study walked to its charge in its store.

    The groups that copy the cache's stages read them from its store, so it is filled before they
    start side by side; a later render finds them there and walks nothing.
    """
    folder = cached_project(out)
    project = Project.open(folder)
    session = project.session()
    session.write = False
    session.run(project.study(project.items("study")[0]), upto="charge")
    return folder


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
    identifier: str,
    first: str,
    path: str,
    scheme: str,
    click: list[str] | list[str | dict[str, Any]] | None = None,
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
        # The server holds an edit once a shot has started it, so only the first scheme's starts it.
        {
            **entry(
                f"shell-2wcd-{name}", first, path, scheme, [] if name in HELD and index else click
            ),
            "wait_ms": HELD_WAIT_MS if name in HELD else 500,
        }
        for name, path, click in PROJECT_EXTRAS
        for index, scheme in enumerate(SCHEMES)
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


REFUSING_ISOLEVEL = 0.9
"""An isolevel at which 2WCD's stage 4 is refused: the loop breaks into islands."""


UNMOVED_BY_ISOLEVEL = (
    "nanopnp-structure-v0.5",
    "nanopnp-protonation-v0.5",
    "nanopnp-protonation-frame-v0.5",
    "nanopnp-density-v0.5",
    "nanopnp-reduced-v0.5",
)
"""The store's folders of stages 1 to 3, which a changed isolevel keys as before."""


def continuum_project(out: Path, name: str, *, refused: bool) -> Path:
    """Return a project holding the cached 2WCD molecular and continuum models, its store empty.

    With ``refused`` the continuum model's isolevel is one stage 4 refuses, and the store holds
    the cache's stages 1 to 3, so the build reaches stage 4's refusal in seconds.
    """
    source = cached_project(out)
    folder = molecular_project(out, name, off_axis=False)
    (model,) = sorted((source / "models" / "continuum").glob("*.yaml"))
    shutil.copy(model, folder / "models" / "continuum" / model.name)
    project = Project.open(folder)
    if refused:
        project.set_value("continuum", model.stem, "geometry.contour.isolevel", REFUSING_ISOLEVEL)
        for kept in UNMOVED_BY_ISOLEVEL:
            shutil.copytree(
                source / STORE_FOLDER / "artefacts" / kept,
                folder / STORE_FOLDER / "artefacts" / kept,
                dirs_exist_ok=True,
            )
    project.open_item(f"continuum/{model.stem}")
    return folder


def continuum_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return a continuum model refused at stage 4 and one held mid-build, on 2WCD.

    Stage 4 is built from Meso's Outline, so both are shot there. The built and the empty
    Continuum tools are the ``2wcd`` and ``states`` groups' ``c-<tool>`` shots, and an unsaved edit
    of the outline the ``2wcd`` group's last.
    """
    manifest = []
    for name, path, wait_ms in (
        ("refused", "/meso/outline", 30000),
        ("building", "/meso/outline", 2500),
    ):
        for scheme in SCHEMES:
            folder = continuum_project(out, f"c-{name}-{scheme}", refused=name == "refused")
            process, first = start("--project", str(folder))
            servers.append(process)
            shot = entry(f"shell-continuum-{name}", first, path, scheme, [BUILD])
            shot["wait_ms"] = wait_ms
            manifest.append(shot)
    return manifest


PHYSICS_TOOLS = ("equations", "electrolyte", "conditions", "exposed")
STUDY_BIAS_V = 0.2
"""A bias the charged tube's study sets itself: shown in it, a physics model marks and leaves it."""
IONS = [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}]
PHYSICS_EXTRAS: tuple[tuple[str, str, list[str]], ...] = (
    ("conditions-picked", "/physics/conditions", ["[data-control=role-wall]"]),
    ("conditions-mesh", "/physics/conditions", ["[data-control=physics-show-mesh]"]),
    (
        "conditions-in-tube",
        "/physics/conditions",
        ["[data-control=physics-shown-in]", ".q-menu .q-item:nth-child(1)"],
    ),
    # Last: the change of model is written, and the server holds its note for the shots after it.
    (
        "equations-chosen",
        "/physics/equations",
        ["[data-control=field-physics-model]", ".q-menu .q-item:nth-child(5)"],
    ),
)
"""The quick-start model's tools in states of their own: a role picked, the mesh shown under the
boundaries, the model shown in the charged tube's study, which sets its own bias, and pnp-ns
chosen for it."""


def physics_project(out: Path, name: str) -> Path:
    """Return a project of example 01's case and the charged tube, whose study sets its own bias.

    ``fresh`` adds a physics model with its ions and no salt, opened; ``refusing`` sets the
    quick-start model to pnp, whose switches its study does not run with.
    """
    folder = out.resolve() / "projects" / f"physics-{name}"
    if folder.exists():
        shutil.rmtree(folder)
    project = Project.create(folder, name=f"physics-{name}")
    # The tube first: the server walks the first study to its charge, which example 01 has not.
    project.import_case(Case.load(write_charged_tube(out.resolve() / "projects" / "tube")))
    project.import_case(Case.load(QUICKSTART))
    # Example 01's mesh stored, so Conditions draws its boundaries.
    session = project.session()
    session.write = False
    session.run(project.study("quickstart"), upto="mesh")
    study = project.path("study", "charged-tube")
    written = yaml.safe_load(study.read_text(encoding="utf-8"))
    written["boundary_conditions"] = {"bias_V": STUDY_BIAS_V}
    study.write_text(yaml.safe_dump(written, sort_keys=False), encoding="utf-8")
    if name == "fresh":
        project.new_model("physics", "fresh")
        project.set_value("physics", "fresh", "electrolyte.species", IONS)
        project.open_item("physics/fresh")
    else:
        if name == "refusing":
            project.set_value("physics", "quickstart", "physics.model", "pnp")
        project.open_item("physics/quickstart")
    return folder


def physics_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return the Physics tools drafted on example 01's project with the charged tube beside it."""
    manifest = []
    launched = {
        name: launch("--project", str(physics_project(out, name)))
        for name in ("paired", "fresh", "refusing")
    }
    servers.extend(launched.values())
    first = {name: first_address(process, name) for name, process in launched.items()}
    for tool in PHYSICS_TOOLS:
        for scheme in SCHEMES:
            manifest.append(
                entry(f"shell-physics-{tool}", first["paired"], f"/physics/{tool}", scheme)
            )
    for name, path, click in PHYSICS_EXTRAS:
        for index, scheme in enumerate(SCHEMES):
            # The change of model is written once; the dark shot finds it and its note held.
            held = name == "equations-chosen" and index
            shot = entry(
                f"shell-physics-{name}", first["paired"], path, scheme, [] if held else click
            )
            shot["wait_ms"] = 2500
            manifest.append(shot)
    for name, tools in (
        ("fresh", ("electrolyte", "equations")),
        ("refusing", ("equations", "conditions")),
    ):
        for tool in tools:
            for scheme in SCHEMES:
                manifest.append(
                    entry(f"shell-physics-{name}-{tool}", first[name], f"/physics/{tool}", scheme)
                )
    return manifest


MESO_TOOLS = ("density", "outline", "charge")
OVERLAY_WAIT_MS = 20000
"""How long a shot waits after the overlay's toggle: its first volumes take about 7 s on 2WCD."""
MESO_EXTRAS: tuple[tuple[str, str, list[str], int], ...] = (
    # A click on the plane's centre names the residues nearest that point: Density's plane takes
    # a point, where the Outline's picks a vertex.
    ("density-near", "/meso/density", ["#plane canvas"], 2500),
    ("charge-picked", "/meso/charge", ["[data-control=charge-strip-item]"], 2500),
    ("charge-deployed", "/meso/charge", ["[data-control=charge-layer] button:nth-child(2)"], 2500),
    ("charge-subunit", "/meso/charge", ["[data-control=mol-subunit]"], 2500),
    ("charge-overlay-full", "/meso/charge", ["[data-control=overlay-full]"], OVERLAY_WAIT_MS),
    (
        "charge-overlay-revolved",
        "/meso/charge",
        ["[data-control=overlay-revolved]"],
        OVERLAY_WAIT_MS,
    ),
)
"""The Meso tools in states of their own: the residues nearest a point of Density's plane, a
residue picked from the list, the deployed charge on the mesh, Mol* showing one subunit, and each
of the overlay's two volumes drawn as isosurfaces."""


MOVED_HEADING = "[data-control=contour-moved] h3"
"""The heading of the residues an edit moves into the water."""
OUTLINE_MOVE_NM = 0.5
"""How far the outline edit moves the narrowest vertex into the protein: on 2WCD, two residues'
atoms then lie in the water. Toward the axis it would move into water no atom reaches."""


def outline_edit(walked: RunResult) -> list[str | dict[str, Any]]:
    """Return the steps that open the outline's editor and move its narrowest vertex outward."""
    profile = Path(walked.artefacts["contour"].payload["profile"])
    radii = [r for r, _ in yaml.safe_load(profile.read_text(encoding="utf-8"))["vertices"]]
    narrowest = radii.index(min(radii))
    return [
        "[data-control=contour-start]",
        {"plane_vertex": narrowest},
        {
            "fill": "[data-control=contour-r]",
            "value": round(radii[narrowest] + OUTLINE_MOVE_NM, 4),
        },
        "[data-control=contour-move]",
        # The residues it moves are listed below the editor: a click on their heading scrolls
        # them into view.
        MOVED_HEADING,
    ]


def meso_project(out: Path) -> tuple[Path, list[str | dict[str, Any]]]:
    """Return a copy of the 2WCD project, its continuum model's charge walked and drawn.

    The charge case is walked with a run record, as Meso's Build runs it, and the deployed charge
    is drawn for the record, as Charge map asks the render child for. The steps of the outline's
    edit come with it.
    """
    source = cached_project(out)
    folder = out.resolve() / "projects" / "meso-2wcd"
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(source, folder)
    project = Project.open(folder)
    (continuum,) = project.items("continuum")
    walked = Session(Store(folder / STORE_FOLDER), write=True).run(
        project.charge_case(continuum), upto="charge"
    )
    assert walked.directory is not None
    render_charge_elements(ChargeRequest(run=str(walked.directory), elements=True))
    project.open_item(f"continuum/{continuum}")
    return folder, outline_edit(walked)


def meso_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return the Meso tools on the 2WCD project: each tool, then each state of the charge map."""
    folder, edit = meso_project(out)
    process, first = start("--project", str(folder))
    servers.append(process)
    manifest = []
    for tool in MESO_TOOLS:
        for scheme in SCHEMES:
            shot = entry(f"shell-meso-{tool}", first, f"/meso/{tool}", scheme)
            shot["wait_ms"] = 2500
            manifest.append(shot)
    for name, path, click, wait_ms in MESO_EXTRAS:
        for scheme in SCHEMES:
            shot = entry(f"shell-meso-{name}", first, path, scheme, click)
            shot["wait_ms"] = wait_ms
            manifest.append(shot)
    # Last: the edit is held by the server, so the dark shot finds it made.
    for index, scheme in enumerate(SCHEMES):
        # The dark shot finds the edit made, and picks the same vertex to show its r and z.
        steps = [edit[1], MOVED_HEADING] if index else edit
        shot = entry("shell-meso-outline-moved", first, "/meso/outline", scheme, steps)
        shot["wait_ms"] = 2500
        manifest.append(shot)
    return manifest


STUDY_TOOLS = ("overview", "setup", "sweep", "runs")
STUDY_EXTRAS: tuple[tuple[str, str, list[str | dict[str, Any]]], ...] = (
    ("overview-whole", "/study/overview", ["[data-control=overview-whole-case]"]),
    ("new", "/study/setup", ["[data-control=study-new]"]),
    (
        "more-solver",
        "/study/setup",
        [
            {"fill": "[data-control=study-more]", "value": "numerics.linear.solver"},
            ".q-menu .q-item",
            {"fill": "[data-control=study-more-value]", "value": "superlu"},
            "[data-control=study-more-add]",
        ],
    ),
)
"""The 2WCD study's tools in states of their own: Overview's whole case unfolded, the *New study*
window, and the linear solver set to SuperLU through *More values*, light only and last, since it
changes the study."""
SWEPT_BIAS_V = [-0.05, 0.05]
"""The bias the 2WCD study's sweep varies over: two points, so its forecast stays quick."""


def study_project(out: Path) -> Path:
    """Return a copy of the 2WCD project, its study walked to its charge with a run record.

    The study holds a sweep over the bias.
    """
    source = cached_project(out)
    folder = out.resolve() / "projects" / "study-2wcd"
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(source, folder)
    project = Project.open(folder)
    (study,) = project.items("study")
    project.session().run(project.study(study), upto="charge")
    axis = Axis(name="bias", path="boundary_conditions.bias_V", values=list(SWEPT_BIAS_V))
    write_sweep(project, study, [axis])
    return folder


def study_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return the Study tools on the 2WCD project, then the charged tube run and its convergence."""
    launched = {
        "2wcd": launch("--project", str(study_project(out))),
        "tube": launch("--state", "charged-tube"),
    }
    servers.extend(launched.values())
    first = {name: first_address(process, name) for name, process in launched.items()}
    manifest = [
        entry(f"shell-study-{tool}", first["2wcd"], f"/study/{tool}", scheme)
        for tool in STUDY_TOOLS
        for scheme in SCHEMES
    ]
    for name, path, click in STUDY_EXTRAS:
        # The value set is then listed, and no longer offered: a light shot only.
        for scheme in SCHEMES[:1] if name == "more-solver" else SCHEMES:
            shot = entry(f"shell-study-{name}", first["2wcd"], path, scheme, click)
            shot["wait_ms"] = 2500
            manifest.append(shot)
    # The tube is run once, from the running shot, which shows its queue line while it solves;
    # Runs then draws its convergence, the study's last run, once the 8 s solve has ended (WB-45).
    running = entry(
        "shell-study-tube-running",
        first["tube"],
        "/study/setup?panel=queue",
        SCHEMES[0],
        ["[data-control=study-run]"],
    )
    running["wait_ms"] = 2000
    manifest.append(running)
    for index, scheme in enumerate(SCHEMES):
        run = entry("shell-study-tube-run", first["tube"], "/study/setup", scheme)
        run["wait_ms"] = 10000 if not index else 500
        convergence = entry("shell-study-tube-convergence", first["tube"], "/study/runs", scheme)
        convergence["wait_ms"] = 2500
        manifest += [run, convergence]
    # The run's lines in the log, light only, once it has ended.
    manifest.append(
        entry("shell-study-tube-log", first["tube"], "/study/runs?panel=log", SCHEMES[0])
    )
    return manifest


ANALYSIS_BIASES_V = [-0.1, -0.05, 0.05, 0.1]
"""The biases the analysis project's study is swept over: the case's own 0.05 V among them."""
ANALYSIS_BIAS_V = 0.05
"""The bias the variant's study sets, which is the case's own, so the two runs differ in charge."""
BIAS_PATH = "boundary_conditions.bias_V"
FLIPPED = "ASP"
"""The residue the linked variant flips: the first of this name the structure carries."""
COMPARED = "charged-against-neutral"
"""The comparison of the two studies' runs."""


def first_residue(structure: Path, name: str) -> str:
    """Return the first residue of this name in a PDB file, as a charge edit names it."""
    for line in structure.read_text(encoding="utf-8").splitlines():
        if line.startswith("ATOM") and line[17:20] == name:
            return f"{name} {int(line[22:26])}{line[26].strip()}"
    raise ValueError(f"{structure} holds no {name}")


def retarget(folder: Path, old: Path, new: Path) -> None:
    """Name ``new`` in place of ``old`` in the records of a project's runs and sweeps.

    A run's record, which names its store, and a sweep's members hold absolute folders, so a
    project moved or copied would otherwise point back at the one it came from. A sweep member's
    run folder is in the store. A run's manifest and case stay as the run wrote them: the manifest
    is hashed, and the case must be the one it embeds.
    """
    forms = {str(old), str(old.resolve())}
    for part in ("runs", "sweeps", f"{STORE_FOLDER}/runs"):
        for file in sorted((folder / part).rglob("*")) if (folder / part).is_dir() else ():
            if (
                not file.is_file()
                or file.suffix not in (".json", ".yaml")
                or "viewer" in file.parts
                or file.name in ("manifest.json", "case.yaml")
            ):
                continue
            text = file.read_text(encoding="utf-8")
            moved = text
            for form in forms:
                moved = moved.replace(form, str(new.resolve()))
            if moved != text:
                file.write_text(moved, encoding="utf-8")


def solve_analysis(project: Project) -> tuple[Path, Path, list[Path]]:
    """Solve the study, its bias sweep and the variant's study; return their run folders.

    The tuple is the study's run, the variant's run and every sweep member's, as ``_solve`` of the
    fixture states makes them.
    """
    session = project.session()
    (study,) = project.items("study")
    first = session.run(project.study(study))
    assert first.directory is not None
    points = [{BIAS_PATH: value} for value in ANALYSIS_BIASES_V]
    source = write_sweep(project, study, [Axis(name="bias", assignments=points)])
    plan = build_plan(load_sweep(source), source=source, check_meshes=False)
    directory = session.store.sweep_directory(plan.name, plan.hash)
    write_plan(plan, directory)
    members = run_plan(plan, directory, session=session, workers=2)
    collect(plan, directory, members=members)
    swept = [Path(member.directory) for member in members if member.directory is not None]
    assert len(swept) == len(ANALYSIS_BIASES_V), "every point of the sweep is a run"

    (molecular,) = project.items("molecular")
    (continuum,) = project.items("continuum")
    (physics,) = project.items("physics")
    (structure,) = sorted((project.root / "inputs").glob("*.pdb"))
    residue = first_residue(structure, FLIPPED)
    variant = f"{molecular.split('-')[0]}-{residue.replace(' ', '').lower()}n"
    project.save_variant(molecular, variant, [{"residue": residue, "state": "neutral"}])
    project.new_study(variant, variant, continuum, physics)
    project.set_study_value(variant, BIAS_PATH, ANALYSIS_BIAS_V)
    second = session.run(project.study(variant))
    assert second.directory is not None
    project.new_comparison(
        COMPARED,
        first.directory.relative_to(project.root).as_posix(),
        second.directory.relative_to(project.root).as_posix(),
    )
    return first.directory, second.directory, swept


def _scalar(quantity: str) -> bool:
    # A component's vector is drawn whole, an alias such as potential is a scalar's name.
    return FIELD_ALIASES.get(quantity, (quantity, None))[1] is None


def draw_analysis(project: Project, first: Path, second: Path, runs: list[Path]) -> None:
    """Write every run's fields, and the scenes the explorer and the comparison draw on the mesh.

    Each is drawn here, so that a page does not wait on a render child for it. The comparison
    takes the quantity the explorer opens on, so that one field's scenes serve both, a run
    keeping one field's scenes at a time.
    """
    for run in runs:
        render_fields(FieldsRequest(run=str(run)))
    model = AnalysisModel(project)
    held = [model.fields(run) for run in (first, second)]
    assert held[0] is not None and held[1] is not None
    quantity = quantities_of(held[0])[0]
    compared = project.comparison(COMPARED)
    if scene_field(quantity) != scene_field(compared.quantity):
        compared = project.set_comparison(COMPARED, quantity=quantity)
    # The ranges the pages ask for: the explorer's opening map's, and the comparison's pair's, the
    # side-by-side scale or a component's vector size; a run keeps both scenes of one field.
    shown = map_of(model, first, quantity)
    assert shown is not None
    render(
        RenderRequest(
            run=str(first),
            field=scene_field(quantity),
            document=False,
            colour_range=shown.scale if _scalar(quantity) else None,
        )
    )
    maps = comparison_maps(model, COMPARED)
    assert maps is not None
    pair = (
        maps["first"].scale
        if _scalar(compared.quantity)
        else joint_size_range(held[0], held[1], compared.quantity)
    )
    for run in (first, second):
        request = RenderRequest(
            run=str(run), field=scene_field(compared.quantity), document=False, colour_range=pair
        )
        render(request)


def build_analysis(folder: Path, source: Path) -> None:
    """Build the analysis project in ``folder`` from a copy of the 2WCD project at ``source``."""
    folder.mkdir(parents=True)
    shutil.copytree(source, folder / "project")
    project = Project.open(folder / "project")
    first, second, swept = solve_analysis(project)
    draw_analysis(project, first, second, [first, second, *swept])


def analysis_cache(out: Path) -> Path:
    """Return the analysis project of the cache beside ``out``, built now if it is not there."""
    cache = out.resolve().parent / "cache" / f"analysis-{cache_key()}"
    if cache.is_dir():
        print(f"analysis project reused from {cache}", file=sys.stderr)
    else:
        print(f"analysis project building in {cache}", file=sys.stderr)
        pending = cache.with_name(f"{cache.name}.building-{os.getpid()}")
        shutil.rmtree(pending, ignore_errors=True)
        cache.parent.mkdir(parents=True, exist_ok=True)
        try:
            build_analysis(pending, cached_project(out))
            retarget(pending / "project", pending / "project", cache / "project")
            pending.rename(cache)
        finally:
            shutil.rmtree(pending, ignore_errors=True)
    return cache / "project"


def analysis_project(out: Path, name: str) -> Path:
    """Return a copy of the cached analysis project, named ``name`` among the render's projects."""
    source = analysis_cache(out)
    folder = out.resolve() / "projects" / name
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(source, folder)
    retarget(folder, source, folder)
    return folder


ANALYSIS_TOOLS = ("explorer", "compare")
MAP = "#analysis-map canvas"
PLACING = "[data-control=analysis-placing]"
VIEW = "[data-control=analysis-view]"
MESH_WAIT_MS = 40000
"""How long a shot waits for a scene: the viewer fetches a scene of tens of megabytes."""
ANALYSIS_WAIT_MS = 4000
"""How long a shot waits for its tiles: the maps are drawn after the page is ready."""
EXPLORER_EXTRAS: tuple[tuple[str, list[str], int], ...] = (
    # A click on the map places a cut, the default placing, or with Probe chosen a probe.
    # The cut's chart is below the field and the I-V; a click on its heading scrolls it into view.
    ("cut", [MAP, "[data-control=analysis-cut] h2"], ANALYSIS_WAIT_MS),
    ("probe", [f"{PLACING} button:has-text('Probe')", MAP], ANALYSIS_WAIT_MS),
    ("outline", ["[data-control=analysis-outline]"], ANALYSIS_WAIT_MS),
    ("on-mesh", ["[data-control=analysis-on-mesh] button:has-text('Mesh')"], MESH_WAIT_MS),
    # The two last: the run picked is held by the server, so each shot after it opens on it.
    (
        "sweep-point",
        ["[data-control=analysis-run]", '.q-menu .q-item:has-text("point 1,")'],
        ANALYSIS_WAIT_MS,
    ),
    (
        "variant",
        ["[data-control=analysis-study]", '.q-menu .q-item:has-text("{variant}")'],
        ANALYSIS_WAIT_MS,
    ),
)
"""The explorer in states of its own: a cut, a probe, the outline, the field on the mesh, a point of
the bias sweep, and the study of the linked variant."""
COMPARE_VIEWS = (
    ("difference", "Difference", ANALYSIS_WAIT_MS),
    ("maps", "Side by side", ANALYSIS_WAIT_MS),
    ("mirrored", "Mirrored", ANALYSIS_WAIT_MS),
    ("mesh", "Mesh", MESH_WAIT_MS),
)
"""The comparison's four views; each is written to its file, so the next shot of the server finds
it, and each shot chooses its own."""


def analysis_entries(out: Path, servers: list[subprocess.Popen[str]]) -> list[dict[str, Any]]:
    """Return the Analysis tools on a solved 2WCD project, and on a copy whose store was cleaned."""
    folder = analysis_project(out, "analysis-2wcd")
    cleaned = analysis_project(out, "analysis-cleaned")
    # Every solve of the copy leaves the store: its runs read as removed.
    Project.open(cleaned).clean_store(everything=True)
    base = Project.open(cached_project(out)).items("study")[0]
    (variant,) = (name for name in Project.open(folder).items("study") if name != base)
    launched = {
        "solved": launch("--project", str(folder)),
        "cleaned": launch("--project", str(cleaned)),
    }
    servers.extend(launched.values())
    first = {name: first_address(process, name) for name, process in launched.items()}
    manifest: list[dict[str, Any]] = []

    def shoot(name: str, server: str, path: str, click: list[str] | None, wait_ms: int) -> None:
        for scheme in SCHEMES:
            shot = entry(f"shell-analysis-{name}", first[server], path, scheme, click)
            shot["wait_ms"] = wait_ms
            manifest.append(shot)

    for tool in ANALYSIS_TOOLS:
        shoot(tool, "solved", f"/analysis/{tool}", None, ANALYSIS_WAIT_MS)
    for name, click, wait_ms in EXPLORER_EXTRAS:
        steps = [step.format(variant=variant) if "{variant}" in step else step for step in click]
        shoot(f"explorer-{name}", "solved", "/analysis/explorer", steps, wait_ms)
    for name, title, wait_ms in COMPARE_VIEWS:
        click = [f"{VIEW} button:has-text('{title}')"]
        shoot(f"compare-{name}", "solved", "/analysis/compare", click, wait_ms)
    shoot("explorer-rebuild", "cleaned", "/analysis/explorer", None, ANALYSIS_WAIT_MS)
    return manifest


GROUP_ENTRIES = {
    "states": states_entries,
    "2wcd": project_entries,
    "extra": extra_entries,
    "compact": compact_entries,
    "molecular": molecular_entries,
    "meso": meso_entries,
    "continuum": continuum_entries,
    "physics": physics_entries,
    "study": study_entries,
    "analysis": analysis_entries,
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
        # Six groups read the 2WCD cache, so it is built and its store filled before they start
        # side by side.
        if {"2wcd", "molecular", "meso", "continuum", "study", "analysis"} & set(groups):
            filled_cache(out)
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

"""The gui, project, store and env commands."""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.cli.common import _common, _emit, _refuse
from nanopnp.core.errors import EXIT_OK
from nanopnp.core.paths import (
    CONFIG_VARIABLE,
    CORRECTIONS_DIR,
    DATA_DIR,
    GEOMETRY_DIR,
    REFERENCE_DATA_VARIABLE,
    STORE_ROOT_VARIABLE,
    config_root,
    last_project,
    reference_data_root,
    remember_project,
    store_root,
)
from nanopnp.core.public import __version__

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.api.project import Project
    from nanopnp.cli.common import Subparsers
    from nanopnp.core.hashing import Canonicalisable


def _environment() -> dict[str, Canonicalisable]:
    reference = reference_data_root()
    return {
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "data": str(DATA_DIR),
        "corrections": str(CORRECTIONS_DIR),
        "geometry": str(GEOMETRY_DIR),
        "store": str(Path(store_root()).resolve()),
        STORE_ROOT_VARIABLE: os.environ.get(STORE_ROOT_VARIABLE),
        "config": str(config_root()),
        CONFIG_VARIABLE: os.environ.get(CONFIG_VARIABLE),
        "reference_data": str(reference) if reference is not None else None,
        REFERENCE_DATA_VARIABLE: os.environ.get(REFERENCE_DATA_VARIABLE),
    }


def _env(args: argparse.Namespace) -> int:
    found = _environment()
    lines = [
        f"nanopnp   {found['version']}",
        f"python    {found['python']} on {found['platform']}",
        f"data      {found['data']}",
        f"store     {found['store']} "
        f"({STORE_ROOT_VARIABLE}={found[STORE_ROOT_VARIABLE] or 'unset'})",
        f"config    {found['config']} ({CONFIG_VARIABLE}={found[CONFIG_VARIABLE] or 'unset'})",
        f"reference {found['reference_data'] or 'none'} "
        f"({REFERENCE_DATA_VARIABLE}={found[REFERENCE_DATA_VARIABLE] or 'unset'})",
    ]
    _emit(found, lines, as_json=bool(getattr(args, "json", False)))
    return EXIT_OK


def _project_to_open(args: argparse.Namespace, *, open_last: bool = True) -> Path | None:
    from nanopnp.api.project import Project
    from nanopnp.io.project import PROJECT_FILENAME

    folder: Path | None = args.project
    if folder is None:
        return last_project() if open_last else None
    if folder.is_file():
        if folder.name == PROJECT_FILENAME:
            _refuse(args, f"{folder} is a project file: give its folder, {folder.parent}")
        if folder.suffix in {".yaml", ".yml"}:
            _refuse(
                args,
                f"{folder} is a case file, not a project folder: import it with "
                f"`nanopnp project import {folder} <project folder>`",
            )
        _refuse(args, f"{folder} is a file, not a project folder")
    if (folder / PROJECT_FILENAME).is_file():
        project = Project.open(folder)
    else:
        project = Project.create(folder)
    remember_project(project.root)
    return project.root


def _gui(args: argparse.Namespace) -> int:
    from nanopnp.core.stages import MissingExtraError

    for package in ("fastapi", "uvicorn", "nicegui"):
        if importlib.util.find_spec(package) is None:
            raise MissingExtraError(
                f"nanopnp gui needs the 'gui' extra: {package!r} is not installed. Install the "
                "extras with `uv sync --all-extras`",
                name=package,
            )
    # Named by string: gui sits above cli in the layer order, so an import would point upward.
    server = importlib.import_module("nanopnp.gui.web.server")
    if args.state is not None and args.state not in server.STATES:
        _refuse(args, f"--state {args.state!r}: the states are {', '.join(server.STATES)}")
    if args.project is not None and args.state is not None:
        _refuse(args, "give a project folder or --state, not both")
    project = (
        None
        if args.state is not None
        else _project_to_open(args, open_last=server.open_last_project())
    )
    code: int = server.serve(
        project=project,
        state=args.state,
        port=args.port,
        no_browser=args.no_browser,
        dev=args.dev,
        as_json=bool(getattr(args, "json", False)),
    )
    return code


def _open_or_create(folder: Path) -> Project:
    from nanopnp.api.project import Project
    from nanopnp.io.project import PROJECT_FILENAME

    if (folder / PROJECT_FILENAME).is_file():
        return Project.open(folder)
    return Project.create(folder)


def _project_new(args: argparse.Namespace) -> int:
    from nanopnp.api.project import Project

    project = Project.create(args.folder, args.name)
    payload: dict[str, Canonicalisable] = {"project": str(project.root), "name": project.name}
    _emit(payload, [f"created project {project.name!r} in {project.root}"], as_json=_as_json(args))
    return EXIT_OK


def _project_import(args: argparse.Namespace) -> int:
    from nanopnp.api.case import Case

    case = Case.load(args.case)
    project = _open_or_create(args.project)
    study = project.import_case(case, args.name, link=args.link)
    payload: dict[str, Canonicalisable] = {
        "project": str(project.root),
        "study": study,
        "linked": [str(path) for path in project.linked()],
    }
    lines = [f"imported {args.case} as study {study!r} in {project.root}"]
    lines += [f"  linked, not copied: {path}" for path in project.linked()]
    _emit(payload, lines, as_json=_as_json(args))
    return EXIT_OK


def _project_embed(args: argparse.Namespace) -> int:
    from nanopnp.api.project import Project

    project = Project.open(args.project)
    embedded = project.embed(args.input)
    payload: dict[str, Canonicalisable] = {"project": str(project.root), "input": str(embedded)}
    _emit(payload, [f"embedded {args.input} as {embedded}"], as_json=_as_json(args))
    return EXIT_OK


def _project_export(args: argparse.Namespace) -> int:
    from nanopnp.api.project import Project

    project = Project.open(args.project)
    target = project.export(args.destination, store=args.with_store)
    payload: dict[str, Canonicalisable] = {"project": str(project.root), "export": str(target)}
    _emit(payload, [f"exported {project.root} to {target}"], as_json=_as_json(args))
    return EXIT_OK


def _store_prune(args: argparse.Namespace) -> int:
    from nanopnp.io.store import Store

    store = Store(args.store if args.store is not None else store_root())
    entries = store.stale()
    total = sum(entry.size_bytes for entry in entries)
    size = _size(total)
    if args.remove:
        removed = store.remove(entries)
        payload: dict[str, Canonicalisable] = {"removed": removed, "bytes": total}
        lines = [f"removed {removed} stale entries ({size}) from {store.root}"]
    else:
        payload = {
            "stale": [
                {"schema": entry.schema, "hash": entry.hash, "bytes": entry.size_bytes}
                for entry in entries
            ],
            "count": len(entries),
            "bytes": total,
        }
        lines = [
            f"{entry.schema}  {entry.hash[:12]}  {_size(entry.size_bytes)}" for entry in entries
        ]
        lines.append(
            f"{len(entries)} stale entries ({size}) in {store.root}"
            + ("; --remove deletes them" if entries else "")
        )
    _emit(payload, lines, as_json=_as_json(args))
    return EXIT_OK


def _size(count: int) -> str:
    value = float(count)
    for unit in ("B", "kB", "MB", "GB"):
        if value < 1000.0 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1000.0
    raise AssertionError("unreachable")  # pragma: no cover


def _as_json(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False))


def _register_project(subparsers: Subparsers) -> None:
    project = subparsers.add_parser(
        "project", help="create, fill, copy out or pack a project folder (FR-32)"
    )
    actions = project.add_subparsers(dest="project_command", required=True, metavar="action")

    new = _common(actions.add_parser("new", help="create a project in a missing or empty folder"))
    new.add_argument("folder", type=Path, help="the folder to create the project in")
    new.add_argument("--name", default=None, help="the project's name; the folder's by default")
    new.set_defaults(handler=_project_new)

    imported = _common(
        actions.add_parser(
            "import",
            help="import a case file as a study and the models it is made of",
            description="Import a case file into a project. The project is created in a missing "
            "or empty folder. Each input file is copied into the project's inputs/ folder, or "
            "with --link is left where it lies.",
        )
    )
    imported.add_argument("case", type=Path, help="the case file")
    imported.add_argument("project", type=Path, help="the project folder")
    imported.add_argument("--link", action="store_true", help="leave the inputs where they lie")
    imported.add_argument("--name", default=None, help="the study's name; the case's by default")
    imported.set_defaults(handler=_project_import)

    embed = _common(actions.add_parser("embed", help="copy a linked input into the project"))
    embed.add_argument("project", type=Path, help="the project folder")
    embed.add_argument("input", type=Path, help="the linked input file")
    embed.set_defaults(handler=_project_embed)

    export = _common(
        actions.add_parser("export", help="write a portable copy of the project's readable files")
    )
    export.add_argument("project", type=Path, help="the project folder")
    export.add_argument("destination", type=Path, help="a missing or empty folder")
    export.add_argument(
        "--with-store", action="store_true", help="copy the artefact store in as well"
    )
    export.set_defaults(handler=_project_export)


def _register_store(subparsers: Subparsers) -> None:
    store = subparsers.add_parser("store", help="look after the artefact store")
    actions = store.add_subparsers(dest="store_command", required=True, metavar="action")
    prune = _common(
        actions.add_parser(
            "prune",
            help="list, or with --remove delete, the entries of an older schema version",
            description="List the stored artefacts written under an older version of a schema "
            "this release writes, with their count and total size. An entry of a newer version "
            "is kept: a store may be shared with a newer release.",
        )
    )
    prune.add_argument(
        "--store", type=Path, default=None, help="the store; $NANOPNP_STORE by default"
    )
    prune.add_argument("--remove", action="store_true", help="delete them")
    prune.set_defaults(handler=_store_prune)


def register(subparsers: Subparsers) -> None:
    """Add the gui and env subcommands."""
    gui = _common(
        subparsers.add_parser(
            "gui",
            help="serve the browser workbench on 127.0.0.1 (the 'gui' extra)",
            description="Serve the workbench on 127.0.0.1. The server prints one line, "
            "'nanopnp-gui ready <url>' (with --json, {\"ready\": <url>}), and stops when its "
            "standard input closes or on SIGINT or SIGTERM.",
        )
    )
    gui.add_argument(
        "project",
        nargs="?",
        type=Path,
        default=None,
        help="a project folder to open, or a missing or empty folder to create one in; "
        "with none, the project opened last",
    )
    gui.add_argument("--state", default=None, help="a fixture state in place of a case")
    gui.add_argument("--port", type=int, default=0, help="the port; 0 picks a free one")
    gui.add_argument("--no-browser", action="store_true", help="print the address, open nothing")
    gui.add_argument("--dev", action="store_true", help="reload on a change to the screens' source")
    gui.set_defaults(handler=_gui, parser=gui)

    _register_project(subparsers)
    _register_store(subparsers)

    env = _common(subparsers.add_parser("env", help="report the environment and data locations"))
    env.set_defaults(handler=_env)

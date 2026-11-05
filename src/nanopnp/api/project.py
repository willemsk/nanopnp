"""A workbench project: a plain folder of models, studies, inputs, runs and results (FR-32)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.core.hashing import file_hash
from nanopnp.io.case import SCHEMA, CaseValidationError
from nanopnp.io.defaults import Change, changes, mapping_changes
from nanopnp.io.models import (
    MODEL_KINDS,
    SCHEMAS,
    ModelFile,
    check_model_file,
    leaves,
    owner_of,
)
from nanopnp.io.project import (
    FOLDERS,
    INPUTS_FOLDER,
    ITEM_KINDS,
    PROJECT_FILENAME,
    RUNS_FOLDER,
    STORE_FOLDER,
    SUITES,
    SWEEPS_FOLDER,
    ItemKind,
    ProjectFile,
    ProjectFormatError,
    Suite,
    SuiteLayout,
    item_inputs,
    item_reference,
    read_project,
    rewrite_inputs,
    split_reference,
    valid_name,
    write_project,
)
from nanopnp.io.store import Store

__all__ = ["Problem", "Project", "ProjectError"]

_RUN_FILES = ("case.yaml", "manifest.json", "run.json")

_SUITE_OF: dict[str, Suite] = {
    "molecular": "molecular",
    "continuum": "continuum",
    "study": "study",
    "comparison": "analysis",
}


class ProjectError(ValueError):
    """A project could not be created, opened, changed or exported."""


@dataclass(frozen=True)
class Problem:
    """One thing wrong with a project: an item, the case path, what is wrong and where to fix it.

    Parameters
    ----------
    item
        The item as ``<kind>/<name>``.
    path
        The dotted case path the refusal names; ``None`` where it names none.
    suite
        The suite whose tool edits the item or the path.
    """

    item: str
    path: str | None
    message: str
    suite: Suite

    def summary(self) -> dict[str, str | None]:
        """Return this problem as plain data."""
        return {
            "item": self.item,
            "path": self.path,
            "message": self.message,
            "suite": self.suite,
        }


class Project:
    """A project folder, open: its items, inputs, runs and the store beside them.

    The folder is the truth. The project file indexes the items in it and holds the window's
    layout and no physics.
    """

    def __init__(self, root: Path, document: ProjectFile) -> None:
        self._root = root
        self._file = document

    @property
    def root(self) -> Path:
        """The project folder."""
        return self._root

    @property
    def name(self) -> str:
        """The project's name."""
        return self._file.name

    @property
    def current(self) -> str | None:
        """The item last opened, as ``<kind>/<name>``."""
        return self._file.current

    @property
    def open_items(self) -> tuple[str, ...]:
        """The items open in the window, as ``<kind>/<name>``."""
        return tuple(self._file.open)

    @property
    def layout(self) -> Mapping[Suite, SuiteLayout]:
        """The saved layout of each suite that has one."""
        return dict(self._file.layout)

    @classmethod
    def create(cls, folder: str | Path, name: str | None = None) -> Project:
        """Create a project in a missing or empty folder.

        Raises
        ------
        ProjectError
            If the folder holds anything.
        """
        root = Path(folder).expanduser().resolve()
        if root.exists() and (not root.is_dir() or any(root.iterdir())):
            raise ProjectError(f"{root} is not empty, so a project cannot be created in it")
        root.mkdir(parents=True, exist_ok=True)
        for sub in (*FOLDERS.values(), INPUTS_FOLDER):
            (root / sub).mkdir(parents=True, exist_ok=True)
        document = ProjectFile(name=name if name is not None else root.name or "project")
        write_project(root, document)
        return cls(root, document)

    @classmethod
    def open(cls, folder: str | Path) -> Project:
        """Open a project folder; a file in an item folder the index lacks is appended to it.

        Raises
        ------
        ProjectError
            If the folder holds no project file of this release.
        """
        root = Path(folder).expanduser().resolve()
        try:
            document = read_project(root)
        except ProjectFormatError as error:
            raise ProjectError(str(error)) from None
        project = cls(root, document)
        if project._index():
            write_project(root, project._file)
        return project

    # -- items --------------------------------------------------------------

    def items(self, kind: ItemKind) -> tuple[str, ...]:
        """Return the names of the indexed items of one kind."""
        return tuple(self._file.names(kind))

    def path(self, kind: ItemKind, name: str) -> Path:
        """Return where an item's file is, whether or not it exists."""
        return self._root / FOLDERS[kind] / f"{name}.yaml"

    def study(self, name: str) -> Case:
        """Read a study as the one case it resolves to."""
        return Case.load(self.path("study", name))

    def runs(self, study: str) -> tuple[Path, ...]:
        """Return the run directories of one study."""
        base = self._root / RUNS_FOLDER / study
        if not base.is_dir():
            return ()
        return tuple(sorted(d for d in base.iterdir() if (d / "run.json").is_file()))

    def session(self) -> Session:
        """Return a session over the project's store, runs and sweeps."""
        return Session(
            Store(
                self._root / STORE_FOLDER,
                runs=self._root / RUNS_FOLDER,
                sweeps=self._root / SWEEPS_FOLDER,
            )
        )

    def open_item(self, item: str) -> None:
        """Open an item in the window and make it the current one; ``<kind>/<name>``."""
        kind, name = split_reference(item)
        if name not in self._file.names(kind):
            raise ProjectError(f"the project holds no {kind} {name!r}")
        if item not in self._file.open:
            self._file.open.append(item)
        self._file.current = item
        write_project(self._root, self._file)

    def save_layout(self, suite: Suite, layout: SuiteLayout) -> None:
        """Save how one suite's window is divided."""
        if suite not in SUITES:
            raise ProjectError(f"no suite {suite!r}; the suites are {', '.join(SUITES)}")
        self._file.layout[suite] = layout
        write_project(self._root, self._file)

    # -- inputs -------------------------------------------------------------

    def add_input(self, path: str | Path, *, link: bool = False) -> Path:
        """Copy a file into ``inputs/`` and return the copy, or with ``link`` return the file.

        Raises
        ------
        ProjectError
            If the file is absent, or a different file already has its name in ``inputs/``.
        """
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise ProjectError(f"{source} is not a file, so it cannot be an input")
        if link:
            return source
        target = self._root / INPUTS_FOLDER / source.name
        if target.is_file():
            if target.resolve() == source or file_hash(target) == file_hash(source):
                return target
            raise ProjectError(
                f"inputs/{source.name} is a different file from {source}; rename one of them"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target

    def linked(self) -> tuple[Path, ...]:
        """Return each input file an item names that lies outside the project's ``inputs/``."""
        kept = (self._root / INPUTS_FOLDER).resolve()
        found: dict[Path, None] = {}
        for kind, _, body in self._bodies():
            for value in item_inputs(body).values():
                resolved = self._resolved(kind, value)
                if kept not in resolved.parents:
                    found[resolved] = None
        return tuple(sorted(found))

    def embed(self, path: str | Path) -> Path:
        """Copy a linked input into ``inputs/`` and make each item that names it name the copy."""
        wanted = Path(path).expanduser().resolve()
        copy = self.add_input(wanted)
        for kind, name, body in self._bodies():
            changed = rewrite_inputs(body, self._pointing(kind, wanted, copy))
            if changed:
                self._write_item(kind, name, body)
        return copy

    # -- import -------------------------------------------------------------

    def import_case(self, case: Case, name: str | None = None, *, link: bool = False) -> str:
        """Import a case as a study and the two models it is made of; return the study's name.

        A case that names model files brings them along. Each input file is copied into
        ``inputs/``, or with ``link`` is left where it lies.

        Raises
        ------
        ProjectError
            If the name is not an item name, a different file has an input's name, or the items
            written would resolve to another case than the one given.
        """
        label = name if name is not None else case.name
        if not valid_name(label):
            raise ProjectError(
                f"{label!r} is not an item name: use letters, digits, '.', '_' or '-', and start "
                "with a letter or a digit; name the study with name="
            )
        written: list[Path] = []
        try:
            record = case.models_record
            if record is None:
                study = self._split(case, label, link=link, written=written)
            else:
                study = self._carry(case, label, link=link, written=written)
            self._verify(case, study, label)
        except Exception:
            for target in written:
                target.unlink(missing_ok=True)
            raise
        self._index()
        write_project(self._root, self._file)
        return label

    def _split(self, case: Case, label: str, *, link: bool, written: list[Path]) -> Path:
        source = case.source
        base = source.base if source.base is not None else Path.cwd()
        raw = yaml.safe_load(source.text) if source.text else None
        if not isinstance(raw, dict):
            raw = case.model_dump(by_alias=True, mode="json", exclude_defaults=True)
        pinned = set(case.expressions)
        layers: dict[str, dict[str, Any]] = {"molecular": {}, "continuum": {}, "study": {}}
        for path, value in leaves(raw):
            if value is None:
                continue
            kind = "study" if path in pinned else owner_of(path)
            _put(layers[kind], path, value)
        paths: dict[str, str] = {}
        for kind in MODEL_KINDS:
            layer = layers[kind]
            self._rebase(layer, base, kind, link=link)
            taken = self._model_name(kind, label, {"schema": SCHEMAS[kind], "name": "", **layer})
            body = {"schema": SCHEMAS[kind], "name": taken, **layer}
            self._put_item(kind, taken, body, written)
            paths[kind] = f"../{FOLDERS[kind]}/{taken}.yaml"
        study = layers["study"]
        self._rebase(study, base, "study", link=link)
        study.pop("schema", None)
        study.pop("name", None)
        head: dict[str, Any] = {"schema": SCHEMA, "name": label, "models": paths}
        self._put_item("study", label, {**head, **study}, written)
        return self.path("study", label)

    def _carry(self, case: Case, label: str, *, link: bool, written: list[Path]) -> Path:
        record = case.models_record
        assert record is not None
        paths: dict[str, str] = {}
        for file in record.files:
            paths[file.kind] = self._copy_model(file, link=link, written=written)
        text = case.dumps(study=True)
        body: dict[str, Any] = yaml.safe_load(text)
        body["name"] = label
        body["models"] = paths
        self._rebase(body, record.base, "study", link=link)
        self._put_item("study", label, body, written)
        return self.path("study", label)

    def _copy_model(self, file: ModelFile, *, link: bool, written: list[Path]) -> str:
        body: dict[str, Any] = yaml.safe_load(file.path.read_text(encoding="utf-8"))
        self._rebase(body, file.path.parent, file.kind, link=link)
        taken = self._model_name(file.kind, file.name, body)
        body["name"] = taken
        self._put_item(file.kind, taken, body, written)
        return f"../{FOLDERS[file.kind]}/{taken}.yaml"

    def _model_name(self, kind: ItemKind, wanted: str, body: Mapping[str, Any]) -> str:
        # An identical file under the name is reused; a different one takes the next free name.
        candidate, number = wanted, 1
        while True:
            existing = self.path(kind, candidate)
            if not existing.is_file():
                return candidate
            if existing.read_text(encoding="utf-8") == _text({**body, "name": candidate}):
                return candidate
            number += 1
            candidate = f"{wanted}-{number}"

    def _rebase(self, body: dict[str, Any], base: Path, kind: ItemKind, *, link: bool) -> None:
        def move(_: str, value: str) -> str:
            source = Path(value)
            source = source if source.is_absolute() else base / source
            target = self.add_input(source, link=link)
            return str(target) if link else self._relative(kind, target)

        rewrite_inputs(body, move)

    def _verify(self, case: Case, study: Path, label: str) -> None:
        try:
            read = Case.load(study)
        except (CaseValidationError, FileNotFoundError, ValueError) as error:
            raise ProjectError(f"the study written to {study} is not readable: {error}") from None
        before = _comparable(case)
        after = _comparable(read)
        before["name"] = after["name"] = label
        different = sorted(key for key in before if before[key] != after.get(key))
        if different:
            raise ProjectError(
                f"the items written for {case.name!r} do not resolve to the case given; they "
                f"differ in {', '.join(different)}"
            )

    # -- the changed list and the problems ---------------------------------

    def changes(self, kind: ItemKind, name: str) -> tuple[Change, ...]:
        """Return each value of an item away from its default, and each override of a study."""
        if kind == "study":
            return changes(self.study(name))
        if kind in MODEL_KINDS:
            return mapping_changes(_body(self.path(kind, name)))
        return ()

    def reset(self, kind: ItemKind, name: str, path: str) -> None:
        """Remove a value from the item that sets it, so that it reads its default again.

        Raises
        ------
        ProjectError
            If no item sets the path.
        """
        target_kind, target = kind, name
        if kind == "study":
            record = self.study(name).models_record
            owner = owner_of(path)
            if record is not None and path not in record.overrides and owner in record.kinds:
                file = next(f for f in record.files if f.kind == owner)
                target_kind, target = owner, file.path.stem
        location = self.path(target_kind, target)
        body = _body(location, keep=True)
        if not _delete(body, path):
            raise ProjectError(f"{target_kind} {target!r} sets no {path}")
        self._write_item(target_kind, target, body)

    def problems(self) -> tuple[Problem, ...]:
        """Return each missing file, mismatched name, refused item and missing input."""
        found: list[Problem] = []
        for kind in ITEM_KINDS:
            for name in self._file.names(kind):
                found.extend(self._problems_of(kind, name))
        return tuple(found)

    def _problems_of(self, kind: ItemKind, name: str) -> list[Problem]:
        item, suite = item_reference(kind, name), _SUITE_OF[kind]
        location = self.path(kind, name)
        if not location.is_file():
            return [Problem(item, None, f"{location} is indexed but does not exist", suite)]
        if kind == "comparison":
            return []
        try:
            body = _body(location, keep=True)
        except (OSError, yaml.YAMLError, ProjectError) as error:
            return [Problem(item, None, f"{location} is not readable: {error}", suite)]
        found: list[Problem] = []
        if body.get("name") != name:
            found.append(
                Problem(
                    item,
                    "name",
                    f"the file is {location.name} but its name: is {body.get('name')!r}",
                    suite,
                )
            )
        for dotted, value in item_inputs(body).items():
            resolved = self._resolved(kind, value)
            if not resolved.is_file():
                where = _SUITE_OF[kind] if kind != "study" else _owner_suite(dotted)
                found.append(Problem(item, dotted, f"{resolved} does not exist", where))
        try:
            if kind == "study":
                self.study(name)
            else:
                check_model_file(kind, location)
        except (CaseValidationError, FileNotFoundError, ValueError, KeyError) as error:
            where_path = _error_path(error)
            refused = _owner_suite(where_path) if where_path and kind == "study" else suite
            found.append(Problem(item, where_path, str(error), refused))
        return found

    # -- export -------------------------------------------------------------

    def export(self, destination: str | Path, *, store: bool = False) -> Path:
        """Copy the project, as readable files, to a missing or empty folder.

        Every input an item names is copied into the copy's ``inputs/``, with the items that
        name a linked one rewritten. The run records and their results come with it, the store
        only with ``store``.

        Raises
        ------
        ProjectError
            If an input is missing, two inputs share a name, or the destination holds files.
        """
        target = Path(destination).expanduser().resolve()
        if target.exists() and (not target.is_dir() or any(target.iterdir())):
            raise ProjectError(f"{target} is not empty, so a project cannot be exported to it")
        if target == self._root or self._root in target.parents:
            raise ProjectError("a project cannot be exported into itself")
        plan = self._export_plan()
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._root / PROJECT_FILENAME, target / PROJECT_FILENAME)
        for relative, body in plan.items.items():
            place = target / relative
            place.parent.mkdir(parents=True, exist_ok=True)
            if body is None:
                shutil.copyfile(self._root / relative, place)
            else:
                place.write_text(_text(body), encoding="utf-8")
        for source, relative in plan.inputs.items():
            place = target / relative
            place.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, place)
        self._export_runs(target)
        sweeps = self._root / SWEEPS_FOLDER
        if sweeps.is_dir():
            shutil.copytree(sweeps, target / SWEEPS_FOLDER)
        if store and (self._root / STORE_FOLDER).is_dir():
            shutil.copytree(self._root / STORE_FOLDER, target / STORE_FOLDER)
        return target

    def _pointing(
        self, kind: ItemKind, wanted: Path, copy: Path
    ) -> Callable[[str, str], str | None]:
        def point(_: str, value: str) -> str | None:
            return self._relative(kind, copy) if self._resolved(kind, value) == wanted else None

        return point

    def _gathering(
        self,
        kind: ItemKind,
        name: str,
        names: dict[str, Path],
        inputs: dict[Path, str],
    ) -> Callable[[str, str], str | None]:
        kept = (self._root / INPUTS_FOLDER).resolve()

        def collect(_: str, value: str) -> str | None:
            resolved = self._resolved(kind, value)
            if not resolved.is_file():
                raise ProjectError(f"{resolved} is named by {kind} {name!r} and is missing")
            held = names.get(resolved.name)
            if held is not None and held != resolved and file_hash(held) != file_hash(resolved):
                raise ProjectError(
                    f"{held} and {resolved} share the name {resolved.name}; "
                    "rename one before exporting"
                )
            names.setdefault(resolved.name, resolved)
            inputs[resolved] = f"{INPUTS_FOLDER}/{resolved.name}"
            if kept in resolved.parents:
                return None
            return self._relative(kind, self._root / INPUTS_FOLDER / resolved.name)

        return collect

    def _export_plan(self) -> _Plan:
        kept = (self._root / INPUTS_FOLDER).resolve()
        inputs: dict[Path, str] = {}
        names: dict[str, Path] = {}
        items: dict[str, dict[str, Any] | None] = {}
        for kind in ITEM_KINDS:
            for name in self._file.names(kind):
                location = self.path(kind, name)
                relative = str(location.relative_to(self._root))
                if not location.is_file():
                    raise ProjectError(f"{location} is indexed but does not exist")
                if kind == "comparison":
                    items[relative] = None
                    continue
                body = _body(location, keep=True)

                collect = self._gathering(kind, name, names, inputs)
                changed = rewrite_inputs(body, collect)
                items[relative] = body if changed else None
        for source in sorted((self._root / INPUTS_FOLDER).glob("*")) if kept.is_dir() else ():
            if source.is_file():
                inputs.setdefault(source.resolve(), f"{INPUTS_FOLDER}/{source.name}")
        return _Plan(items=items, inputs=inputs)

    def _export_runs(self, target: Path) -> None:
        base = self._root / RUNS_FOLDER
        if not base.is_dir():
            return
        for study in sorted(p for p in base.iterdir() if p.is_dir()):
            for run in sorted(p for p in study.iterdir() if (p / "run.json").is_file()):
                place = target / RUNS_FOLDER / study.name / run.name
                place.mkdir(parents=True, exist_ok=True)
                for name in _RUN_FILES:
                    if (run / name).is_file():
                        shutil.copyfile(run / name, place / name)
                record = json.loads((run / "run.json").read_text(encoding="utf-8"))
                for entry in record.get("files", []):
                    result = Path(str(entry))
                    if result.is_file():
                        (place / "results").mkdir(exist_ok=True)
                        shutil.copyfile(result, place / "results" / result.name)

    # -- the index and the item files ----------------------------------------

    def _index(self) -> bool:
        changed = False
        for kind in ITEM_KINDS:
            folder = self._root / FOLDERS[kind]
            indexed = self._file.names(kind)
            if not folder.is_dir():
                continue
            for file in sorted(folder.glob("*.yaml")):
                if valid_name(file.stem) and file.stem not in indexed:
                    indexed.append(file.stem)
                    changed = True
        return changed

    def _bodies(self) -> list[tuple[ItemKind, str, dict[str, Any]]]:
        found: list[tuple[ItemKind, str, dict[str, Any]]] = []
        for kind in ("molecular", "continuum", "study"):
            for name in self._file.names(kind):
                location = self.path(kind, name)
                if location.is_file():
                    found.append((kind, name, _body(location, keep=True)))
        return found

    def _put_item(
        self, kind: ItemKind, name: str, body: Mapping[str, Any], written: list[Path]
    ) -> None:
        location = self.path(kind, name)
        if location.is_file():
            if location.read_text(encoding="utf-8") != _text(body):
                raise ProjectError(f"the project already holds a different {kind} {name!r}")
            return
        written.append(self._write_item(kind, name, body))

    def _write_item(self, kind: ItemKind, name: str, body: Mapping[str, Any]) -> Path:
        location = self.path(kind, name)
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_text(_text(body), encoding="utf-8")
        names = self._file.names(kind)
        if name not in names:
            names.append(name)
        return location

    def _resolved(self, kind: ItemKind, value: str) -> Path:
        path = Path(value)
        return (
            path.resolve() if path.is_absolute() else (self._root / FOLDERS[kind] / path).resolve()
        )

    def _relative(self, kind: ItemKind, target: Path) -> str:
        depth = len(Path(FOLDERS[kind]).parts)
        inside = target.resolve().relative_to((self._root / INPUTS_FOLDER).resolve())
        return str(Path(*[".."] * depth, INPUTS_FOLDER, inside).as_posix())


@dataclass(frozen=True)
class _Plan:
    items: dict[str, dict[str, Any] | None]
    inputs: dict[Path, str]


def _put(layer: dict[str, Any], path: str, value: object) -> None:
    *parents, last = path.split(".")
    cursor = layer
    for part in parents:
        cursor = cursor.setdefault(part, {})
    cursor[last] = value


def _text(body: Mapping[str, Any]) -> str:
    return str(yaml.safe_dump(dict(body), sort_keys=False))


def _body(location: Path, *, keep: bool = False) -> dict[str, Any]:
    raw = yaml.safe_load(location.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ProjectError(f"{location} is not a YAML mapping")
    if keep:
        return raw
    return {key: value for key, value in raw.items() if key not in ("schema", "name")}


def _delete(body: dict[str, Any], dotted: str) -> bool:
    *parents, last = dotted.split(".")
    chain: list[dict[str, Any]] = [body]
    for part in parents:
        child = chain[-1].get(part)
        if not isinstance(child, dict):
            return False
        chain.append(child)
    if last not in chain[-1]:
        return False
    del chain[-1][last]
    for depth in range(len(parents), 0, -1):
        if chain[depth]:
            break
        del chain[depth - 1][parents[depth - 1]]
    return True


def _comparable(case: Case) -> dict[str, Any]:
    # An input is the same file when it has the same name: the copy is byte for byte.
    dumped: dict[str, Any] = case.model_dump(by_alias=True, mode="json")
    rewrite_inputs(dumped, lambda _, value: Path(value).name)
    return dumped


def _error_path(error: Exception) -> str | None:
    errors = getattr(error, "errors", None)
    if errors is None or not hasattr(errors, "errors"):
        return None
    first = errors.errors()[0]["loc"]
    return ".".join(str(part) for part in first) or None


def _owner_suite(path: str | None) -> Suite:
    return _SUITE_OF[owner_of(path)] if path else "study"

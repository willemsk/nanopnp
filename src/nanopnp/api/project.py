"""A workbench project: a plain folder of models, studies, inputs, runs and results (FR-32)."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import JsonValue

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.core.hashing import file_hash
from nanopnp.io import case as schema
from nanopnp.io.case import SCHEMA, CaseValidationError, FieldValue
from nanopnp.io.case_paths import (
    UnknownCasePathError,
    field_at,
    input_paths,
    rewrite_inputs,
)
from nanopnp.io.defaults import Change, changes, mapping_changes
from nanopnp.io.manifest import RUN_RECORD_FILENAME
from nanopnp.io.models import (
    EXPOSED,
    MODEL_KINDS,
    SCHEMAS,
    VARIANT_PATH,
    ModelFile,
    ModelKind,
    _holder,
    _put,
    leaves,
    merge_layers,
    owner_of,
    read_model_file,
    split_case_layers,
)
from nanopnp.io.project import (
    FOLDERS,
    INPUTS_FOLDER,
    ITEM_KINDS,
    ITEM_SUITES,
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
    item_reference,
    read_project,
    split_reference,
    valid_name,
    write_project,
)
from nanopnp.io.store import LOCKS, StaleEntry, Store, StoreUsage
from nanopnp.materials.corrections import load_corrections
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk, selected_stages
from nanopnp.sweep.run import MEMBERS_DIRNAME

__all__ = ["Problem", "Project", "ProjectError"]

T = TypeVar("T")

_RUN_FILES = ("case.yaml", "manifest.json", "run.json")

# What a model lacks of a whole case, so that it validates and walks alone. No stage up to a
# kind's ``BUILD_UPTO`` reads a value of it, so a model built alone keys as its studies do.
BUILD_LAYER: Mapping[str, Any] = {
    "electrolyte": {
        "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
        "concentration_M": 0.15,
    },
    "boundary_conditions": {"bias_V": 0.0},
}

# The last stage a model of each kind builds alone; a kind without a row is built by its studies.
BUILD_UPTO: Mapping[ModelKind, str] = {"molecular": "protonation", "continuum": "mesh"}

OWN_OUTLINE: tuple[str, ...] = ("geometry.pore", "inputs.profile", "inputs.mesh")
"""The values with which a continuum model draws its own pore, and reads no molecular model."""

_REFUSED = (ValueError, KeyError, OSError)


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
        self._built: dict[tuple[str, str], tuple[str, frozenset[str]]] = {}

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

    @property
    def settings(self) -> Mapping[str, JsonValue]:
        """The project's own settings, by identifier, over the user's where a setting allows."""
        return dict(self._file.settings)

    def save_setting(self, identifier: str, value: JsonValue) -> None:
        """Save one of the project's settings; ``None`` removes it, so the user's value holds."""
        if value is None:
            self._file.settings.pop(identifier, None)
        else:
            self._file.settings[identifier] = value
        write_project(self._root, self._file)

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
        return Session(self._store())

    def _store(self) -> Store:
        return Store(
            self._root / STORE_FOLDER,
            runs=self._root / RUNS_FOLDER,
            sweeps=self._root / SWEEPS_FOLDER,
        )

    # -- the store ------------------------------------------------------------

    def kept_artefacts(self, holding: frozenset[str] = frozenset()) -> frozenset[str]:
        """Return the store digests a run record, a sweep member or a model's build names.

        Each comes with its inputs. ``holding`` adds the digests of a walk no record names, such
        as the one a window shows.
        """
        named: set[str] = set(holding)
        for kind, upto in BUILD_UPTO.items():
            for name in self._file.names(kind):
                named.update(self._built_stages(kind, name, upto))
        for folder in (self._root / RUNS_FOLDER, self._root / SWEEPS_FOLDER):
            if not folder.is_dir():
                continue
            for record in folder.rglob(RUN_RECORD_FILENAME):
                artefacts = _json_object(record).get("artefacts")
                if isinstance(artefacts, dict):
                    named.update(
                        str(entry["hash"])
                        for entry in artefacts.values()
                        if isinstance(entry, dict) and "hash" in entry
                    )
            for member in folder.rglob(f"{MEMBERS_DIRNAME}/*.json"):
                solution = _json_object(member).get("solution")
                if isinstance(solution, str):
                    named.add(solution)
        return self._store().inputs_closure(named)

    def store_usage(self, holding: frozenset[str] = frozenset()) -> StoreUsage:
        """Return the store's size, and the part of it the project's runs and sweeps keep."""
        return self._store().usage(self.kept_artefacts(holding))

    def clean_store(
        self,
        *,
        everything: bool = False,
        cap_bytes: int | None = None,
        holding: frozenset[str] = frozenset(),
    ) -> tuple[StaleEntry, ...]:
        """Remove stored results, least recently read first, and return what went.

        By default every result no run record, sweep member or ``holding`` names goes; with
        ``cap_bytes`` only as many of those as bring the store to that size; with
        ``everything`` every result, which a run rebuilds when it next needs it. Raises
        StoreBusy, removing nothing, while a walk in any program holds the store.
        """
        store = self._store()
        if everything:
            return store.evict(keep=frozenset())
        return store.evict(keep=self.kept_artefacts(holding), to_bytes=cap_bytes)

    def _built_stages(self, kind: ModelKind, name: str, upto: str) -> frozenset[str]:
        # Keying stage 1 hashes the structure, so the identities are held until the model's
        # resolved text or one of its input files changes.
        try:
            case = self.build_case(kind, name)
            stamp = hashlib.sha256(case.dumps().encode("utf-8"))
            for value in sorted(input_paths(case).values()):
                status = Path(value).stat()
                stamp.update(f"{value}\0{status.st_size}\0{status.st_mtime_ns}\0".encode())
            held = self._built.get((kind, name))
            if held is not None and held[0] == stamp.hexdigest():
                return held[1]
            resolved = resolve(case, base=case.source.base)
            identities = keyed_walk(resolved, store=self._store(), planned=set())
            walked = [
                identities[stage]
                for stage in selected_stages(resolved, upto)
                if stage in identities
            ]
        except _REFUSED:
            return frozenset()
        # A stage not built yet is keyed by a forecast, which its build replaces; the store holds
        # nothing of it to keep.
        found = frozenset(identity.hash for identity in walked if not identity.built)
        if not any(identity.built for identity in walked):
            self._built[kind, name] = (stamp.hexdigest(), found)
        return found

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
            for value in input_paths(body).values():
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
        """Import a case as a study and the models it is made of; return the study's name.

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
        index = self._file.library.model_copy(deep=True)
        kept = set((self._root / INPUTS_FOLDER).glob("*"))
        try:
            record = case.models_record
            if record is None:
                study = self._split(case, label, link=link, written=written)
            else:
                study = self._carry(case, label, link=link, written=written)
            self._verify(case, study, label)
        except Exception:
            # A refused import leaves the folder and the index as they were.
            for target in written:
                target.unlink(missing_ok=True)
            for copied in set((self._root / INPUTS_FOLDER).glob("*")) - kept:
                copied.unlink(missing_ok=True)
            self._file.library = index
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
        layers = split_case_layers(
            raw,
            pinned=frozenset(case.expressions),
            resolved=case.model_dump(by_alias=True, mode="json"),
        )
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
        if file.parent is not None:
            # A linked variant reads its parent beside it, so the parent comes along.
            parent = read_model_file(file.kind, file.parent)
            carried = self._copy_model(parent, link=link, written=written)
            body["variant_of"] = {**body["variant_of"], "model": Path(carried).name}
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

    # -- models: built alone, their values and their variants ----------------

    def build_case(self, kind: ModelKind, name: str) -> Case:
        """Return the case that builds one model alone, up to ``BUILD_UPTO`` of its kind.

        The case is the model's own values over ``BUILD_LAYER`` and its parameter set's solid
        permittivities, merged as a study merges, so its stages key as they do in every study
        that names the model at 0.15 M NaCl. A continuum model is built over the values of the
        molecular model ``molecular_for`` names, unless it declares an idealised pore or
        supplies its outline or mesh.

        Raises
        ------
        ProjectError
            If a model of this kind is built only by its studies.
        CaseValidationError
            If the model's file is refused or its values form no case.
        """
        return self._build_case(kind, name, self.path(kind, name))

    def _build_case(self, kind: ModelKind, name: str, location: Path) -> Case:
        if kind not in BUILD_UPTO:
            raise ProjectError(f"a {kind} model is built by the studies that name it, not alone")
        body = read_model_file(kind, location).body
        layers: list[Mapping[str, Any]] = [_build_layer(idealised=_holds(body, "geometry.pore"))]
        source = f"<{kind} model {name} built alone>"
        molecular = None
        if kind == "continuum" and own_outline(body) is None:
            molecular = self.molecular_for(name)
        if molecular is not None:
            layers.append(read_model_file("molecular", self.path("molecular", molecular)).body)
            source = f"<continuum model {name} built alone over molecular model {molecular}>"
        document = {"schema": SCHEMA, "name": name, **merge_layers([*layers, body])}
        return Case.loads(_text(document), base=location.parent, source=source)

    def molecular_for(self, name: str) -> str | None:
        """Return the molecular model continuum model ``name`` is built alone over, or None.

        It is the one ``set_built_with`` chose; else the molecular model of the first study
        that names the continuum model with one; else the project's first molecular model.
        """
        molecules = self._file.names("molecular")
        held = self._file.built_with.get(name)
        if held is not None and held in molecules:
            return held
        target = self.path("continuum", name).resolve()
        by_file = {self.path("molecular", other).resolve(): other for other in molecules}
        for study in self._file.names("study"):
            location = self.path("study", study)
            named = _body(location).get("models") if location.is_file() else None
            if not isinstance(named, dict):
                continue
            continuum, molecular = named.get("continuum"), named.get("molecular")
            if not isinstance(continuum, str) or not isinstance(molecular, str):
                continue
            if (location.parent / continuum).resolve() != target:
                continue
            found = by_file.get((location.parent / molecular).resolve())
            if found is not None:
                return found
        return molecules[0] if molecules else None

    def set_built_with(self, name: str, molecular: str | None) -> None:
        """Choose the molecular model continuum model ``name`` is built alone over.

        ``None`` returns the choice to ``molecular_for``'s default.

        Raises
        ------
        ProjectError
            If the project holds no such continuum or molecular model.
        """
        if name not in self._file.names("continuum"):
            raise ProjectError(f"the project holds no continuum {name!r}")
        if molecular is None:
            self._file.built_with.pop(name, None)
        elif molecular not in self._file.names("molecular"):
            raise ProjectError(f"the project holds no molecular {molecular!r}")
        else:
            self._file.built_with[name] = molecular
        write_project(self._root, self._file)

    def new_model(self, kind: ModelKind, name: str) -> Path:
        """Create a model that holds no value yet and exposes its kind's list; return its file.

        Raises
        ------
        ProjectError
            If the name is not an item name or the project holds a model of it.
        """
        self._free_name(kind, name)
        exposes = [{"name": label, "path": path} for label, path in EXPOSED[kind]]
        location = self._write_item(
            kind, name, {"schema": SCHEMAS[kind], "name": name, "exposes": exposes}
        )
        write_project(self._root, self._file)
        return location

    def set_value(self, kind: ModelKind, name: str, path: str, value: FieldValue) -> None:
        """Set one value of a model, or with ``None`` remove it; nothing is written if refused.

        Raises
        ------
        ProjectError
            If another kind of model owns the path, the model sets no such value to remove, or
            the value is one a linked variant reads from its parent or leaves to its variants.
        CaseValidationError
            If the edited model is refused, or its values no longer form a case.
        """
        if owner_of(path) != kind:
            raise ProjectError(
                f"{path} belongs to {_holder(owner_of(path))}, not to {kind} model {name!r}"
            )
        body = _body(self.path(kind, name))
        if _linked(body) and path != VARIANT_PATH:
            raise ProjectError(
                f"{kind} {name!r} is a linked variant of {body['variant_of']['model']} and reads "
                f"{path} from it; set the value there, or save the variant as a full copy"
            )
        children = self._linked_variants(kind, name)
        if children and path == VARIANT_PATH:
            raise ProjectError(
                f"{kind} {name!r} is the parent of the linked variant {children[0]!r}, which "
                f"holds its own {VARIANT_PATH}; edit the variant"
            )
        if value is None:
            if not _delete(body, path):
                raise ProjectError(f"{kind} {name!r} sets no {path}")
        else:
            _put(body, path, value)
        self._checked_write(kind, name, body)

    def set_exposed(self, kind: ModelKind, name: str, path: str, on: bool) -> None:
        """List a value of a model among those its studies see first, or take it off the list.

        The entry is named by the last part of its path.

        Raises
        ------
        ProjectError
            If another exposed value already has that name.
        CaseValidationError
            If the path is not a numeric value of this kind of model.
        """
        location = self.path(kind, name)
        body = _body(location)
        listed = body.get("exposes")
        if not isinstance(listed, list) and _linked(body):
            # A linked variant without a list of its own exposes its parent's, as a study reads it.
            listed = _body(location.parent / str(body["variant_of"].get("model"))).get("exposes")
        if not isinstance(listed, list):
            listed = [{"name": label, "path": default} for label, default in EXPOSED[kind]]
        kept = [entry for entry in listed if not _exposes(entry, path)]
        if on and len(kept) == len(listed):
            label = path.rsplit(".", 1)[-1]
            if any(isinstance(entry, dict) and entry.get("name") == label for entry in kept):
                raise ProjectError(
                    f"{kind} {name!r} already exposes a value named {label!r}; rename it in "
                    f"{self.path(kind, name).name} before exposing {path}"
                )
            kept.append({"name": label, "path": path})
        elif on:
            return
        head: dict[str, Any] = {key: body[key] for key in ("schema", "name") if key in body}
        rest = {key: item for key, item in body.items() if key not in (*head, "exposes")}
        self._checked_write(kind, name, {**head, "exposes": kept, **rest})

    def save_variant(
        self,
        parent: str,
        name: str,
        edits: list[dict[str, Any]],
        *,
        copy: bool = False,
    ) -> Path:
        """Save a molecular model with residue edits as a variant of ``parent``; return its file.

        A linked variant holds only ``edits`` and reads every other value from its parent, so a
        change to the parent reaches it. With ``copy`` the variant holds every value itself.

        Parameters
        ----------
        edits
            The whole ``charge.edits`` list of the variant, as a model file writes it.

        Raises
        ------
        ProjectError
            If the name is taken or is not an item name, or a linked variant is asked of a
            parent that is itself a variant or holds edits.
        CaseValidationError
            If the variant is refused, or its values form no case; nothing is written.
        """
        kind: ModelKind = "molecular"
        self._free_name(kind, name)
        if parent not in self._file.names(kind):
            raise ProjectError(f"the project holds no {kind} {parent!r}")
        source = read_model_file(kind, self.path(kind, parent), rebase=False)
        head: dict[str, Any] = {"schema": SCHEMAS[kind], "name": name}
        link = {"model": f"{parent}.yaml", "linked": not copy}
        body: dict[str, Any]
        if copy:
            exposes = _body(self.path(kind, parent)).get("exposes")
            if exposes is not None:
                head["exposes"] = exposes
            body = {**head, "variant_of": link, **_copied(source.body)}
        else:
            if source.variant_of is not None or source.body.get("charge", {}).get("edits"):
                raise ProjectError(
                    f"{kind} {parent!r} is itself a variant or holds {VARIANT_PATH}, and a "
                    "linked variant follows an unedited model; save a full copy instead"
                )
            body = {**head, "variant_of": link}
        _put(body, VARIANT_PATH, _copied(edits))
        location = self._checked_write(kind, name, body)
        write_project(self._root, self._file)
        return location

    def derive_model(
        self,
        kind: ModelKind,
        parent: str,
        name: str,
        values: Mapping[str, FieldValue | None],
    ) -> Path:
        """Save a copy of ``parent`` with values set or removed as a new model; return its file.

        The copy holds the parent's own values and exposed list. Each entry of ``values`` sets
        its path, or with ``None`` removes it where the parent sets it.

        Raises
        ------
        ProjectError
            If the name is taken or is not an item name, the project holds no such parent, or
            another kind of model owns one of the paths.
        CaseValidationError
            If the derived model is refused: a molecular model whose values form no case, or a
            continuum model one of whose values is refused alone; nothing is written.
        """
        self._free_name(kind, name)
        if parent not in self._file.names(kind):
            raise ProjectError(f"the project holds no {kind} {parent!r}")
        for path in values:
            if owner_of(path) != kind:
                raise ProjectError(
                    f"{path} belongs to {_holder(owner_of(path))}, not to a {kind} model"
                )
        location = self.path(kind, parent)
        body: dict[str, Any] = {"schema": SCHEMAS[kind], "name": name}
        exposes = _body(location).get("exposes")
        if exposes is not None:
            body["exposes"] = exposes
        body.update(_copied(read_model_file(kind, location, rebase=False).body))
        for path, value in values.items():
            if value is None:
                _delete(body, path)
            else:
                _put(body, path, _copied(value))
        written = self._checked_write(kind, name, body)
        write_project(self._root, self._file)
        return written

    def _free_name(self, kind: ItemKind, name: str) -> None:
        if not valid_name(name):
            raise ProjectError(
                f"{name!r} is not an item name: use letters, digits, '.', '_' or '-', and start "
                "with a letter or a digit"
            )
        if name in self._file.names(kind) or self.path(kind, name).exists():
            raise ProjectError(f"the project already holds a {kind} {name!r}")

    def _linked_variants(self, kind: ModelKind, name: str) -> list[str]:
        found: list[str] = []
        for other in self._file.names(kind):
            location = self.path(kind, other)
            if other == name or not location.is_file():
                continue
            body = _body(location)
            if _linked(body) and body["variant_of"].get("model") == f"{name}.yaml":
                found.append(other)
        return found

    def _checked_write(self, kind: ModelKind, name: str, body: Mapping[str, Any]) -> Path:
        # Staged beside the item, where a linked variant finds its parent, and moved into place
        # only once it reads as a model and, for a kind built alone, as a case.
        location = self.path(kind, name)
        location.parent.mkdir(parents=True, exist_ok=True)
        staged = location.with_name(f".{location.name}.staged")
        staged.write_text(_text(body), encoding="utf-8")
        try:
            read_model_file(kind, staged, rebase=False)
            # A continuum model is checked by its values alone: its build reads a molecular
            # model, whose own refusal is no reason to refuse this edit.
            if kind == "molecular":
                self._build_case(kind, name, staged)
            else:
                for path, value in leaves(read_model_file(kind, staged, rebase=False).body):
                    _check_leaf(path, value, location)
            staged.replace(location)
        finally:
            staged.unlink(missing_ok=True)
        names = self._file.names(kind)
        if name not in names:
            names.append(name)
        return location

    # -- the changed list and the problems ---------------------------------

    def changes(self, kind: ItemKind, name: str) -> tuple[Change, ...]:
        """Return each value of an item away from its default, and each override of a study.

        A variant's changes are its differences from its parent, each ``default`` the parent's
        value.
        """
        if kind == "study":
            return changes(self.study(name))
        if kind not in MODEL_KINDS:
            return ()
        location = self.path(kind, name)
        body = _body(location)
        link = body.get("variant_of")
        if isinstance(link, dict) and (location.parent / str(link.get("model"))).is_file():
            own = dict(leaves(read_model_file(kind, location, rebase=False).body))
            parent = dict(
                leaves(read_model_file(kind, location.parent / link["model"], rebase=False).body)
            )
            return tuple(
                Change(path, "value", owner_of(path), own.get(path), parent.get(path))
                for path in sorted({*own, *parent})
                if own.get(path) != parent.get(path)
            )
        return mapping_changes(body)

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
        body = _body(location)
        if not _delete(body, path):
            raise ProjectError(f"{target_kind} {target!r} sets no {path}")
        self._write_item(target_kind, target, body)

    def problems(self) -> tuple[Problem, ...]:
        """Return each missing file, mismatched name, refused item and missing input."""
        found: list[Problem] = []
        for kind in ITEM_KINDS:
            for name in self._file.names(kind):
                found.extend(self._problems_of(kind, name))
        shown: list[Problem] = []
        for problem in found:
            message = problem.message.replace(f"{self._root}/", "")
            # A study refused for a model's file repeats that model's problem: list the cause once.
            if problem.item.startswith("study/") and any(
                other.message == message for other in shown
            ):
                continue
            shown.append(Problem(problem.item, problem.path, message, problem.suite))
        return tuple(shown)

    def _problems_of(self, kind: ItemKind, name: str) -> list[Problem]:
        item, suite = item_reference(kind, name), ITEM_SUITES[kind]
        location = self.path(kind, name)
        if not location.is_file():
            return [Problem(item, None, f"{location} is indexed but does not exist", suite)]
        if kind == "comparison":
            return []
        try:
            body = _body(location)
        except (OSError, yaml.YAMLError, ValueError) as error:  # ValueError: not UTF-8, not a map
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
        for dotted, value in input_paths(body).items():
            resolved = self._resolved(kind, value)
            if not resolved.is_file():
                where = ITEM_SUITES[kind] if kind != "study" else _owner_suite(dotted)
                found.append(Problem(item, dotted, f"{resolved} does not exist", where))
        try:
            if kind == "study":
                self.study(name)
            else:
                read_model_file(kind, location, rebase=False)
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
            shutil.copytree(
                self._root / STORE_FOLDER,
                target / STORE_FOLDER,
                ignore=shutil.ignore_patterns(LOCKS),
            )
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
                body = _body(location)

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
        kinds: tuple[ItemKind, ...] = (*MODEL_KINDS, "study")
        for kind in kinds:
            for name in self._file.names(kind):
                location = self.path(kind, name)
                if location.is_file():
                    found.append((kind, name, _body(location)))
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


def _json_object(path: Path) -> dict[str, Any]:
    # A record a crash cut short names nothing; the clean-up keeps what the others name.
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def _text(body: Mapping[str, Any]) -> str:
    return str(yaml.safe_dump(dict(body), sort_keys=False))


def _body(location: Path) -> dict[str, Any]:
    raw = yaml.safe_load(location.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ProjectError(f"{location} is not a YAML mapping")
    return raw


def _linked(body: Mapping[str, Any]) -> bool:
    link = body.get("variant_of")
    return isinstance(link, dict) and link.get("linked") is True


def _exposes(entry: object, path: str) -> bool:
    return isinstance(entry, dict) and entry.get("path") == path


def _copied(value: T) -> T:
    return copy.deepcopy(value)


@cache
def _permittivities() -> Mapping[str, float]:
    parameters = schema.Electrolyte.model_fields["parameters"].default
    dielectrics = load_corrections(parameters).dielectrics
    return {"protein": dielectrics.protein, "membrane": dielectrics.membrane}


def _build_layer(*, idealised: bool) -> dict[str, Any]:
    # An idealised pore's only solid is the membrane.
    solids = {
        name: value
        for name, value in _permittivities().items()
        if name == "membrane" or not idealised
    }
    layer = copy.deepcopy(dict(BUILD_LAYER))
    layer["physics"] = {"solid_permittivities": solids}
    return layer


def own_outline(body: Mapping[str, Any]) -> str | None:
    """Return the value of :data:`OWN_OUTLINE` a continuum model's body sets, or None."""
    return next((path for path in OWN_OUTLINE if _holds(body, path)), None)


def _holds(body: Mapping[str, Any], dotted: str) -> bool:
    cursor: object = body
    for part in dotted.split("."):
        if not isinstance(cursor, Mapping) or part not in cursor:
            return False
        cursor = cursor[part]
    return cursor is not None


def _check_leaf(path: str, value: FieldValue, location: Path) -> None:
    try:
        field_at(path).validate(value)
    except UnknownCasePathError as error:
        raise CaseValidationError(f"{location}: {path}: {error}") from None


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
    return ITEM_SUITES[owner_of(path)] if path else "study"

"""Named molecular and continuum models: their files, their merge under a study, its overrides."""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, fields
from functools import cache
from pathlib import Path
from typing import Any, Literal, TypeVar

import yaml

from nanopnp.core.hashing import file_hash
from nanopnp.core.paths import names_a_path
from nanopnp.io.case import (
    CORRECTION_PROPERTIES,
    SCHEMA,
    CaseDocument,
    CaseValidationError,
    FieldValue,
    validate_mapping,
)
from nanopnp.io.case_paths import (
    UnknownCasePathError,
    _set_at,
    block_paths,
    field_at,
    path_fields,
    schema_default,
    value_at,
)
from nanopnp.io.variables import Resolution, Variable, expression_paths, resolve

MOLECULAR_SCHEMA = "nanopnp/molecular-model/v0.6"

CONTINUUM_SCHEMA = "nanopnp/continuum-model/v0.6"

Kind = Literal["molecular", "continuum", "study"]

MODEL_KINDS: tuple[Literal["molecular", "continuum"], ...] = ("molecular", "continuum")

SCHEMAS: dict[str, str] = {"molecular": MOLECULAR_SCHEMA, "continuum": CONTINUUM_SCHEMA}

# The longest dotted prefix decides; a path with no row is the study's. A mixed block such as
# `charge` is split below its own name.
OWNERS: dict[str, Kind] = {
    "structure": "molecular",
    "charge.ph": "molecular",
    "charge.forcefield": "molecular",
    "charge.titration": "molecular",
    "charge.edits": "molecular",
    "inputs.pqr": "molecular",
    "geometry": "continuum",
    "charge.exclusion_offset_nm": "continuum",
    "numerics.mesh": "continuum",
    "inputs.mesh": "continuum",
    "inputs.profile": "continuum",
    "physics": "continuum",
    "electrolyte": "continuum",
    "boundary_conditions": "continuum",
}

D = TypeVar("D", bound=CaseDocument)

Override = tuple[FieldValue, FieldValue]


def owner_of(path: str) -> Kind:
    """Return which model owns a dotted case path: the longest prefix in ``OWNERS``, else study."""
    parts = path.split(".")
    for depth in range(len(parts), 0, -1):
        found = OWNERS.get(".".join(parts[:depth]))
        if found is not None:
            return found
    return "study"


@dataclass(frozen=True, eq=False)
class ModelFile:
    """One model file a study read: its kind, its name, its location and its digest."""

    kind: Literal["molecular", "continuum"]
    name: str
    path: Path
    sha256: str


@dataclass(frozen=True, eq=False)
class ModelRecord:
    """What a study read: the files, the case the models make alone and the study's overrides.

    Parameters
    ----------
    view
        The case the models and the study's own keys give, without the study's overrides.
    overrides
        Dotted path to ``(model value, study value)``.
    base
        The directory a relative model path is read against.
    """

    files: tuple[ModelFile, ...]
    view: CaseDocument
    overrides: Mapping[str, Override]
    base: Path

    @property
    def paths(self) -> dict[str, str]:
        """The model files by kind, as the ``models:`` block of the document holds them."""
        return {file.kind: str(file.path) for file in self.files}

    @property
    def kinds(self) -> frozenset[str]:
        """The kinds of model the study names."""
        return frozenset(file.kind for file in self.files)

    def attached(self, document: D) -> D:
        """Return ``document`` carrying this record, its overrides recomputed against the view."""
        document._models = ModelRecord(
            files=self.files,
            view=self.view,
            overrides=differences(document, self.view, self.kinds),
            base=self.base,
        )
        return document

    def check_dropped(self, name: str, assignments: Mapping[str, FieldValue]) -> None:
        """Refuse dropping a block that a named model and the study share.

        Raises
        ------
        CaseValidationError
            A path set to ``None`` holds a key a named model sets, so the study form, which
            writes overrides leaf by leaf, could not drop the block whole.
        """
        dumped = _dump(self.view)
        for path, value in assignments.items():
            if value is not None or owner_of(path) != "study":
                continue
            cursor, last = _cursor(dumped, path)
            if cursor is None or cursor.get(last) is None:
                continue
            owned = sorted(
                key
                for key, kind in OWNERS.items()
                if key.startswith(f"{path}.") and kind in self.kinds
            )
            if owned:
                raise CaseValidationError(
                    f"<{name}>: {path}: None: the block holds {', '.join(owned)}, which a named "
                    f"model sets, so a study cannot drop it whole; set those keys in the model "
                    f"file, or substitute the block's own keys one by one"
                )

    def carried(self, document: D, assignments: Mapping[str, FieldValue]) -> D:
        """Return ``document`` with the model files in ``assignments`` read again under its study.

        The study's own keys and its overrides stay.
        """
        paths: dict[str, Path] = {file.kind: file.path for file in self.files}
        for path, value in assignments.items():
            kind = path.removeprefix("models.")
            if kind not in MODEL_KINDS:
                raise CaseValidationError(f"{path}: models: accepts molecular, continuum")
            if value is None:
                raise CaseValidationError(f"{path}: a study cannot drop a model it names")
            if kind not in self.kinds:
                # The study's document holds a default for every key of the new model, which
                # cannot be told from a value it wrote, so each default would override it.
                raise CaseValidationError(
                    f"{path}: the study names no {kind} model, and a substitution swaps a model "
                    f"the study names; write models.{kind} in the study file instead"
                )
            paths[kind] = (self.base / Path(str(value))).resolve()
        study = study_layer(document, self)
        study.pop("models")
        label = f"<{document.name} with models>"
        record = document.variables_record
        if record is None:
            return _resolve(study, paths, self.base, label, type(document))
        # The expressions go back in, so the swap re-reads the study as it was written.
        resolved, resolution = resolve(record.written(study), label)
        swapped = _resolve(resolved, paths, self.base, label, type(document))
        swapped._variables = VariableRecord.of(resolution) if resolution is not None else None
        return swapped


@dataclass(frozen=True, eq=False)
class VariableRecord(Resolution):
    """What a case wrote as variables and expressions, kept beside the numbers they resolved to.

    The fields are those of ``Resolution``, which it extends with the operations that need the
    case's document types.
    """

    @classmethod
    def of(cls, resolution: Resolution) -> VariableRecord:
        """Keep a resolution as a record."""
        return cls(**{field.name: getattr(resolution, field.name) for field in fields(Resolution)})

    def written(self, mapping: Mapping[str, Any]) -> dict[str, Any]:
        """Return ``mapping`` with each expression at its path and ``variables:`` after the name."""
        out: dict[str, Any] = copy.deepcopy(dict(mapping))
        for path, text in self.expressions.items():
            *parents, last = path.split(".")
            parent: Any = out
            for part in parents:
                parent = _child(parent, part)
            # A list entry is a block (`electrolyte.species.0.z`), so the leaf's parent is a dict.
            if isinstance(parent, dict) and last in parent:
                parent[last] = text
        if not self.definitions:
            return out
        head: dict[str, Any] = {key: out.pop(key) for key in ("schema", "name") if key in out}
        block = {name: variable.written() for name, variable in self.definitions.items()}
        return {**head, "variables": block, **out}

    def following(self, document: CaseDocument, edited: CaseDocument) -> VariableRecord:
        """Return this record for ``edited``, keeping the expressions whose field it left alone."""
        kept: dict[str, str] = {}
        for path, text in self.expressions.items():
            try:
                unchanged = value_at(edited, path) == value_at(document, path)
            except UnknownCasePathError:
                unchanged = False
            if unchanged:
                kept[path] = text
        return VariableRecord(self.definitions, self.values, kept, self.uses)

    def reaches(self, name: str) -> tuple[str, ...]:
        """Return the field paths a variable reaches, through other variables too."""
        if name not in self.definitions:
            known = ", ".join(self.definitions) or "none"
            raise UnknownCasePathError(f"variables.{name} is not a variable of the case ({known})")
        moved = {name}
        grown = True
        while grown:
            grown = False
            for variable in self.definitions:
                if variable not in moved and self.uses.get(variable, frozenset()) & moved:
                    moved.add(variable)
                    grown = True
        return tuple(
            sorted(path for path in self.expressions if self.uses.get(path, frozenset()) & moved)
        )

    def manifest(self, document: CaseDocument) -> dict[str, Any]:
        """Return the manifest's record: each variable as written and each field it reached."""
        return {
            "definitions": {
                name: {
                    "written": variable.written(),
                    "value": self.values[name],
                    "unit": variable.unit,
                }
                for name, variable in self.definitions.items()
            },
            "fields": {
                path: {"expression": text, "value": value_at(document, path)}
                for path, text in self.expressions.items()
            },
        }

    def carried(self, document: D, assignments: Mapping[str, FieldValue]) -> D:
        """Return ``document`` read again as written, with ``assignments`` set.

        A path under ``variables.`` sets a variable: a number in its declared unit, or a
        definition. A number at a field drops the expression written there.
        """
        assignments = _expanded(assignments)
        edits = {p: v for p, v in assignments.items() if not _is_variable(p)}
        changed = {p: v for p, v in assignments.items() if _is_variable(p)}
        definitions = dict(self.definitions)
        for path, value in changed.items():
            name = _variable_name(path, self.definitions)
            definitions[name] = _redefined(path, value, self)
        kept = {
            path: text
            for path, text in self.expressions.items()
            if not any(path == edit or path.startswith(f"{edit}.") for edit in edits)
        }
        record = VariableRecord(definitions, self.values, kept, self.uses)
        mapping = _dump(document)
        models = document.models_record
        if models is not None:
            models.check_dropped(document.name, edits)
            mapping["models"] = models.paths
        mapping = record.written(mapping)
        for path, value in edits.items():
            field_at(path).validate(value)
            _set_at(mapping, path, value)
        listed = ", ".join(sorted(assignments)) or "nothing"
        return read_mapping(
            mapping,
            base=None if models is None else models.base,
            source=f"<{document.name} with {listed} substituted>",
            model=type(document),
        )


def _child(node: object, part: str) -> object:
    if isinstance(node, dict):
        return node.get(part)
    if isinstance(node, list) and part.isdigit() and int(part) < len(node):
        return node[int(part)]
    return None


def _expanded(assignments: Mapping[str, FieldValue]) -> dict[str, FieldValue]:
    # `Case.with_` nests a dotted path under an absent block, so `variables.a` arrives as
    # `variables: {a: ...}`.
    found: dict[str, FieldValue] = {}
    for path, value in assignments.items():
        if path != "variables":
            found[path] = value
        elif isinstance(value, Mapping):
            found.update((f"variables.{name}", item) for name, item in value.items())
        else:
            raise CaseValidationError(
                f"variables: {value!r}: set the variables by name, as variables.<name>"
            )
    return found


def _is_variable(path: str) -> bool:
    return path == "variables" or path.startswith("variables.")


def _variable_name(path: str, known: Mapping[str, Variable]) -> str:
    parts = path.split(".")
    if len(parts) != 2:
        raise CaseValidationError(
            f"{path}: set a variable whole, as variables.<name>, with a number in its unit or a "
            "definition"
        )
    if parts[1] not in known:
        raise UnknownCasePathError(
            f"{path!r} is not a variable of the case (it defines {', '.join(known) or 'none'})"
        )
    return parts[1]


def _redefined(path: str, value: FieldValue, record: VariableRecord) -> Variable:
    name = path.split(".")[1]
    unit = record.definitions[name].unit
    if isinstance(value, Variable):
        return value
    if isinstance(value, Mapping):
        try:
            return Variable.model_validate(dict(value))
        except ValueError as error:
            raise CaseValidationError(f"{path}: {value!r} is not a definition: {error}") from None
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise CaseValidationError(
            f"{path}: {value!r} is neither a finite number in {unit!r} nor a definition"
        )
    return Variable(value=float(value), unit=unit)


def read(path: str | Path, *, model: type[D] = CaseDocument) -> D:  # type: ignore[assignment]
    """Read a case file that may name models, and resolve it to one case document."""
    source = Path(path)
    resolved = source.resolve()
    return reads(
        resolved.read_text(encoding="utf-8"), base=resolved.parent, source=str(source), model=model
    )


def reads(
    text: str,
    *,
    base: str | Path | None = None,
    source: str = "<string>",
    model: type[D] = CaseDocument,  # type: ignore[assignment]
) -> D:
    """Resolve a case held in memory, reading the model files it names beside ``base``."""
    return read_mapping(yaml.safe_load(text), base=base, source=source, model=model)


def read_mapping(
    raw: object,
    *,
    base: str | Path | None = None,
    source: str = "<string>",
    model: type[D] = CaseDocument,  # type: ignore[assignment]
) -> D:
    """Resolve a parsed case: its variables first, then the model files it names beside ``base``.

    The case's own mapping resolves to numbers before any model merges, so every stage and every
    hash sees the numbers and the record keeps what was written.
    """
    resolved, resolution = resolve(raw, source)
    if (
        not isinstance(resolved, Mapping)
        or "models" not in resolved
        or resolved.get("schema") != SCHEMA
    ):
        document = validate_mapping(resolved, source, model)
        assert isinstance(document, model)
    else:
        directory = Path(base).resolve() if base is not None else Path.cwd()
        paths = _named_files(resolved["models"], directory, source)
        study = {key: value for key, value in resolved.items() if key != "models"}
        document = _resolve(study, paths, directory, source, model)
    if resolution is not None:
        document._variables = VariableRecord.of(resolution)
    return document


def _named_files(raw: object, directory: Path, source: str) -> dict[str, Path]:
    if not isinstance(raw, Mapping):
        raise CaseValidationError(
            f"{source}: models: is a mapping of molecular: and continuum: model file paths"
        )
    unknown = sorted(set(raw) - set(MODEL_KINDS))
    if unknown:
        raise CaseValidationError(
            f"{source}: models.{unknown[0]}: unknown key; models: accepts molecular, continuum"
        )
    named: dict[str, Path] = {}
    for kind in MODEL_KINDS:
        value = raw.get(kind)
        if value is None:
            continue
        if not isinstance(value, str):
            raise CaseValidationError(f"{source}: models.{kind}: {value!r} is not a file path")
        named[kind] = (directory / value).resolve()
    if not named:
        raise CaseValidationError(
            f"{source}: models: names a molecular: file, a continuum: file or both"
        )
    return named


def _resolve(
    study: Mapping[str, Any],
    paths: Mapping[str, Path],
    directory: Path,
    source: str,
    model: type[D],
) -> D:
    files: list[ModelFile] = []
    layers: list[tuple[str, Mapping[str, Any]]] = []
    for kind in MODEL_KINDS:
        if kind not in paths:
            continue
        found, mapping = _read_model_file(kind, paths[kind], source)
        files.append(found)
        layers.append((str(paths[kind]), mapping))
    named = frozenset(file.kind for file in files)
    pruned = _prune(study, "", named)
    # Nearest to the study first, as the merge's precedence runs: a tie goes to the layer whose
    # value won. The view's study is the pruned one, so a model's value is never the study's.
    models = list(reversed(layers))

    view_raw = _merge_all([mapping for _, mapping in layers], pruned)
    try:
        view = validate_mapping(view_raw, source, model)
    except CaseValidationError as error:
        raise _located(
            error,
            [(source, pruned), *models],
            "the named models with the study's own keys do not form a case, so a model "
            f"cannot be reused alone: {', '.join(str(path) for path in paths.values())}",
        ) from None
    merged_raw = _merge_all([mapping for _, mapping in layers], dict(study))
    merged_raw["models"] = {file.kind: str(file.path) for file in files}
    try:
        document = validate_mapping(merged_raw, source, model)
    except CaseValidationError as error:
        raise _located(error, [(source, study), *models], None) from None
    assert isinstance(document, model)
    record = ModelRecord(
        files=tuple(files),
        view=view,
        overrides=differences(document, view, named),
        base=directory,
    )
    document._models = record
    return document


def _read_model_file(
    kind: Literal["molecular", "continuum"], path: Path, source: str
) -> tuple[ModelFile, dict[str, Any]]:
    if not path.is_file():
        raise CaseValidationError(f"{source}: models.{kind}: {path} is not a file")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise CaseValidationError(f"{path}: a {kind} model is a YAML mapping")
    if raw.get("schema") != SCHEMAS[kind]:
        raise CaseValidationError(
            f"{path}: expected schema {SCHEMAS[kind]!r}, found {raw.get('schema')!r}"
        )
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise CaseValidationError(f"{path}: a {kind} model carries a name")
    if "models" in raw:
        raise CaseValidationError(f"{path}: a model names no model, so it holds no models: key")
    body = {key: value for key, value in raw.items() if key not in ("schema", "name")}
    for expression in expression_paths(body):
        raise CaseValidationError(
            f"{path}: {expression}: an expression belongs to the study, not to a {kind} model; "
            "a model file holds numbers"
        )
    for leaf in _leaves(body, ""):
        if owner_of(leaf) != kind:
            raise CaseValidationError(
                f"{path}: {leaf}: belongs to the {owner_of(leaf)}, not to a {kind} model"
            )
    return ModelFile(kind, name, path, file_hash(path)), _rebased(body, path.parent)


def check_model_file(kind: Literal["molecular", "continuum"], path: str | Path) -> ModelFile:
    """Read a model file as a study would, refusing it as a study does; return its record."""
    return _read_model_file(kind, Path(path), str(path))[0]


def leaves(mapping: Mapping[str, Any]) -> Iterator[tuple[str, Any]]:
    """Yield each dotted leaf of a case or model mapping, with its value; blocks are descended."""
    return _flat(mapping)


def _leaves(mapping: Mapping[str, Any], path: str) -> Iterator[str]:
    return (here for here, _ in _flat(mapping, path))


@cache
def _blocks() -> frozenset[str]:
    return frozenset(block_paths())


@cache
def _correction_leaves() -> tuple[str, ...]:
    return (
        "electrolyte.parameters",
        *(f"electrolyte.corrections.{name}.model" for name in CORRECTION_PROPERTIES),
    )


def _rebased(body: dict[str, Any], directory: Path) -> dict[str, Any]:
    corrections = _correction_leaves()
    for dotted in (*path_fields(), *corrections):
        parent, last = _cursor(body, dotted)
        value = parent.get(last) if parent is not None else None
        if not isinstance(value, str):
            continue
        if dotted in corrections and not names_a_path(value):
            continue
        if not Path(value).is_absolute():
            assert parent is not None
            parent[last] = str((directory / value).resolve())
    return body


def _cursor(body: dict[str, Any], dotted: str) -> tuple[dict[str, Any] | None, str]:
    *parents, last = dotted.split(".")
    cursor: Any = body
    for part in parents:
        cursor = cursor.get(part) if isinstance(cursor, dict) else None
    return (cursor if isinstance(cursor, dict) else None), last


def _merge(base: Mapping[str, Any], over: Mapping[str, Any], path: str) -> dict[str, Any]:
    blocks = _blocks()
    merged = dict(base)
    for key, value in over.items():
        here = f"{path}.{key}" if path else str(key)
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping) and here in blocks:
            merged[key] = _merge(current, value, here)
        else:
            merged[key] = value
    return merged


def _merge_all(models: list[Mapping[str, Any]], study: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for layer in (*models, study):
        merged = _merge(merged, layer, "")
    return merged


def _prune(mapping: Mapping[str, Any], path: str, named: frozenset[str]) -> dict[str, Any]:
    blocks = _blocks()
    kept: dict[str, Any] = {}
    for key, value in mapping.items():
        here = f"{path}.{key}" if path else str(key)
        if isinstance(value, Mapping) and here in blocks:
            inner = _prune(value, here, named)
            # A named model's block the pruning emptied is the model's alone; left as `{}` it
            # would build a block the model never holds, such as an `inputs.pqr` naming no file.
            if inner or owner_of(here) not in named:
                kept[key] = inner
        elif owner_of(here) not in named:
            kept[key] = value
    return kept


_PROBLEM = re.compile(r"^  ([^\s:]+): ")


def _located(
    error: CaseValidationError,
    sources: list[tuple[str, Mapping[str, Any]]],
    context: str | None,
) -> CaseValidationError:
    lines: list[str] = []
    for line in str(error).splitlines():
        match = _PROBLEM.match(line)
        origin = _origin(match.group(1), sources) if match else None
        lines.append(f"{line} [from {origin}]" if origin else line)
    if context is not None:
        lines.insert(1 if len(lines) > 1 else len(lines), f"  ({context})")
    return CaseValidationError("\n".join(lines), error.errors)


def _origin(dotted: str, sources: list[tuple[str, Mapping[str, Any]]]) -> str | None:
    best: tuple[int, str] | None = None
    for label, mapping in sources:
        depth = _depth(mapping, dotted.split("."))
        if depth and (best is None or depth > best[0]):
            best = (depth, label)
    return best[1] if best else None


def _depth(mapping: object, parts: list[str]) -> int:
    cursor: Any = mapping
    for depth, part in enumerate(parts):
        if isinstance(cursor, Mapping) and part in cursor:
            cursor = cursor[part]
        elif isinstance(cursor, list) and part.isdigit() and int(part) < len(cursor):
            cursor = cursor[int(part)]
        else:
            return depth
    return len(parts)


def _dump(document: CaseDocument) -> dict[str, Any]:
    return document.model_dump(by_alias=True, mode="json")


def differences(
    document: CaseDocument, view: CaseDocument, kinds: frozenset[str]
) -> dict[str, Override]:
    """Return ``{path: (view value, document value)}`` for each differing leaf of a named model."""
    found: dict[str, Override] = {}
    _compare(_dump(view), _dump(document), "", kinds, found)
    return found


def _compare(
    first: FieldValue,
    second: FieldValue,
    path: str,
    named: frozenset[str],
    found: dict[str, Override],
) -> None:
    blocks = _blocks()
    is_block = path == "" or path in blocks
    mixed = owner_of(path) == "study" if path else True
    both = isinstance(first, dict) and isinstance(second, dict)
    one = isinstance(first, dict) or isinstance(second, dict)
    if is_block and (both or (one and mixed and (first is None or second is None))):
        left = first if isinstance(first, dict) else {}
        right = second if isinstance(second, dict) else {}
        for key in (*right, *(key for key in left if key not in right)):
            _compare(
                left.get(key),
                right.get(key),
                f"{path}.{key}" if path else str(key),
                named,
                found,
            )
        return
    if first == second or owner_of(path) not in named:
        return
    if first is None and _is_default(path, second):
        return
    found[path] = (first, second)


def _is_default(path: str, value: FieldValue) -> bool:
    try:
        has_default, default = schema_default(path)
    except KeyError:
        return False
    return has_default and default == value


def study_layer(document: CaseDocument, record: ModelRecord) -> dict[str, Any]:
    """Return the study as a mapping: its own keys, expressions, overrides and model paths."""
    layer: dict[str, Any] = {}
    variables = document.variables_record
    written = tuple(variables.expressions) if variables is not None else ()
    for path, value in _flat(_dump(document)):
        # A field the study writes as an expression is the study's own, even where its value
        # equals the model's, or a variable edited later would no longer reach it.
        pinned = any(field == path or field.startswith(f"{path}.") for field in written)
        if (owner_of(path) not in record.kinds or pinned) and value is not None:
            _put(layer, path, value)
    for path, (_, study) in record.overrides.items():
        _put(layer, path, study)
    layer["models"] = record.paths
    return layer


def _flat(mapping: Mapping[str, Any], path: str = "") -> Iterator[tuple[str, Any]]:
    blocks = _blocks()
    for key, item in mapping.items():
        here = f"{path}.{key}" if path else str(key)
        if isinstance(item, Mapping) and here in blocks:
            yield from _flat(item, here)
        else:
            yield here, item


def _put(layer: dict[str, Any], path: str, value: FieldValue) -> None:
    *parents, last = path.split(".")
    cursor = layer
    for part in parents:
        cursor = cursor.setdefault(part, {})
    cursor[last] = value

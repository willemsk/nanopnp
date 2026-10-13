"""Dotted case-file paths: the schema's fields, reading, checking and substituting."""

from __future__ import annotations

import difflib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args, get_origin

from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic.fields import FieldInfo

from nanopnp.io.case import (
    PROFILE_FORMAT,
    CaseDocument,
    CaseValidationError,
    ContourSpec,
    DensitySpec,
    FieldType,
    FieldValue,
    _keys_of,
    _model_of,
    render_problems,
)


def _literal_options(annotation: FieldType) -> tuple[str, ...] | None:
    for candidate in (annotation, *get_args(annotation)):
        if get_origin(candidate) is Literal:
            return tuple(str(value) for value in get_args(candidate))
    return None


class UnknownCasePathError(KeyError):
    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class FieldReference:
    path: str
    annotation: FieldType
    container: Literal["model", "mapping", "sequence"] = "model"

    def validate(self, value: FieldValue) -> FieldValue:
        try:
            return _adapter(self.annotation).validate_python(value)
        except ValidationError as error:
            reasons = "; ".join(problem["msg"] for problem in error.errors())
            raise CaseValidationError(
                f"{self.path}: {value!r} is not a value this field accepts "
                f"({_annotation_name(self.annotation)}): {reasons}"
            ) from None


_ADAPTERS: dict[object, TypeAdapter[object]] = {}


def _adapter(annotation: FieldType) -> TypeAdapter[object]:
    try:
        adapter = _ADAPTERS.get(annotation)
    except TypeError:
        return TypeAdapter(annotation)
    if adapter is None:
        adapter = _ADAPTERS[annotation] = TypeAdapter(annotation)
    return adapter


def _annotation_name(annotation: FieldType) -> str:
    return getattr(annotation, "__name__", None) or str(annotation).replace("typing.", "")


def _entry_annotation(
    annotation: FieldType,
) -> tuple[FieldType, Literal["mapping", "sequence"]] | None:
    for candidate in (annotation, *get_args(annotation)):
        origin = get_origin(candidate)
        arguments = get_args(candidate)
        if origin in (dict, Mapping) and len(arguments) == 2:
            return arguments[1], "mapping"
        if origin in (list, Sequence) and len(arguments) == 1:
            return arguments[0], "sequence"
    return None


def field_at(path: str) -> FieldReference:
    components = [part for part in path.split(".") if part]
    if not components:
        raise UnknownCasePathError("a case-file path cannot be empty")

    owner: type[BaseModel] | None = CaseDocument
    annotation: FieldType = CaseDocument
    container: Literal["model", "mapping", "sequence"] = "model"
    walked: list[str] = []

    for component in components:
        # Container first: a ``list[SpeciesSpec]`` carries a model and is indexed; asking the block
        # first would report ``0`` as an unknown field of ``SpeciesSpec``.
        entry = _entry_annotation(annotation)
        if entry is not None and entry[1] == "sequence" and not _is_index(component):
            # A list is reached only by index; else ``electrolyte.species.name`` reads ``name`` as
            # an index and fails much later, inside a substitution.
            prefix = ".".join(walked) or "<document>"
            raise UnknownCasePathError(
                f"{path!r} is not a field of the case schema: {prefix} is a list, and "
                f"{component!r} is not an index into it"
            )
        if entry is not None:
            annotation, container = entry
        elif owner is not None:
            field = _field_named(owner, component)
            if field is None:
                accepted = ", ".join(_keys_of(owner))
                prefix = ".".join(walked) or "<document>"
                close = difflib.get_close_matches(component, _keys_of(owner), n=1)
                hint = f"did you mean {close[0]!r}? " if close else ""
                raise UnknownCasePathError(
                    f"{path!r} is not a field of the case schema: {prefix} has no "
                    f"{component!r}. {hint}It accepts {accepted}"
                )
            annotation = field.annotation
            container = "model"
        else:
            prefix = ".".join(walked)
            raise UnknownCasePathError(
                f"{path!r} is not a field of the case schema: {prefix} is a "
                f"{_annotation_name(annotation)}, which has no {component!r} inside it"
            )
        walked.append(component)
        owner = _model_of(annotation)

    return FieldReference(path=path, annotation=annotation, container=container)


SEQUENCE_INDEX = "0"


def case_fields() -> tuple[FieldReference, ...]:
    return tuple(_walk_fields(CaseDocument, ""))


def _walk_fields(owner: type[BaseModel], prefix: str) -> list[FieldReference]:
    found: list[FieldReference] = []
    for name, field in owner.model_fields.items():
        path = f"{prefix}{field.alias or name}"
        annotation = field.annotation
        entry = _entry_annotation(annotation)
        if entry is not None:
            element, kind = entry
            nested = _model_of(element)
            if nested is None:
                # The container is itself the value a reader writes; entries are reached under it.
                found.append(FieldReference(path=path, annotation=annotation))
                continue
            if kind == "mapping":
                raise NotImplementedError(
                    f"{path!r} is a mapping of {nested.__name__} blocks; case_fields() has no "
                    "representative key to walk one under, so a mapping of blocks needs a "
                    "decision here rather than silently missing fields"
                )
            found.extend(_walk_fields(nested, f"{path}.{SEQUENCE_INDEX}."))
            continue
        nested = _model_of(annotation)
        if nested is not None:
            found.extend(_walk_fields(nested, f"{path}."))
            continue
        found.append(FieldReference(path=path, annotation=annotation))
    return found


def schema_default(path: str) -> tuple[bool, FieldValue]:
    field_at(path)  # the named diagnostic for a path that is wrong
    owner: type[BaseModel] | None = CaseDocument
    info: FieldInfo | None = None
    for component in path.split("."):
        if _is_index(component):
            continue
        if owner is None:
            raise UnknownCasePathError(f"{path!r} does not end at a declared field of a block")
        info = _field_named(owner, component)
        if info is None:
            raise UnknownCasePathError(f"{path!r} does not end at a declared field of a block")
        owner = _model_of(info.annotation)
    if info is None or info.is_required():
        return False, None
    return True, info.get_default(call_default_factory=True)


def _is_index(component: str) -> bool:
    return component.removeprefix("-").isdigit()


def _field_named(owner: type[BaseModel], component: str) -> FieldInfo | None:
    for name, field in owner.model_fields.items():
        if (field.alias or name) == component:
            return field
    return None


def _declaration(path: str) -> FieldInfo | None:
    owner: type[BaseModel] = CaseDocument
    parts = path.split(".")
    for index, part in enumerate(parts):
        if _is_index(part):
            continue
        field = _field_named(owner, part)
        if field is None:
            return None
        if index == len(parts) - 1:
            return field
        entry = _entry_annotation(field.annotation)
        nested = _model_of(entry[0] if entry is not None else field.annotation)
        if nested is None:
            return None
        owner = nested
    return None


def field_description(path: str) -> str | None:
    field = _declaration(path)
    return None if field is None else field.description


def field_bounds(path: str) -> tuple[float | None, float | None]:
    field_at(path)
    field = _declaration(path)
    if field is None:
        return None, None
    lower = [float(item.ge) for item in field.metadata if getattr(item, "ge", None) is not None]
    upper = [float(item.le) for item in field.metadata if getattr(item, "le", None) is not None]
    return (max(lower) if lower else None), (min(upper) if upper else None)


def value_at(document: CaseDocument, path: str) -> FieldValue:
    field_at(path)
    value: FieldValue = document
    walked: list[str] = []
    for component in path.split("."):
        walked.append(component)
        if value is None:
            raise UnknownCasePathError(
                f"{path!r} cannot be read from this case: {'.'.join(walked[:-1])} is absent from it"
            )
        if isinstance(value, Mapping):
            if component not in value:
                raise UnknownCasePathError(
                    f"{path!r} cannot be read from this case: {'.'.join(walked[:-1])} "
                    f"has no entry {component!r}"
                )
            value = value[component]
        elif isinstance(value, list):
            value = _sequence_entry(value, component, path, walked)
        else:
            value = getattr(value, _attribute_named(type(value), component))
    return value


def _attribute_named(owner: type, component: str) -> str:
    fields: Mapping[str, FieldInfo] = getattr(owner, "model_fields", {})
    for name, field in fields.items():
        if (field.alias or name) == component:
            return name
    return component


def _sequence_entry(
    values: list[FieldValue], component: str, path: str, walked: list[str]
) -> FieldValue:
    try:
        index = int(component)
        return values[index]
    except (ValueError, IndexError):
        raise UnknownCasePathError(
            f"{path!r} cannot be read from this case: {'.'.join(walked[:-1])} holds "
            f"{len(values)} entries, and {component!r} is not an index into them"
        ) from None


def substitute(document: CaseDocument, assignments: Mapping[str, FieldValue]) -> CaseDocument:
    payload = document.model_dump(by_alias=True, mode="json")
    for path, value in assignments.items():
        reference = field_at(path)
        # Validated first so the diagnostic names the path; dumped to JSON because a ``Path`` set
        # into the plain dict would come out of ``model_dump`` as an object YAML cannot write.
        reference.validate(value)
        _set_at(payload, path, value)
    try:
        return CaseDocument.model_validate(payload)
    except ValidationError as error:
        listed = ", ".join(sorted(assignments)) or "nothing"
        raise CaseValidationError(
            render_problems(f"<{document.name} with {listed} substituted>", error), error
        ) from None


def with_profile(document: CaseDocument, path: str | Path) -> CaseDocument:
    payload = document.model_dump(by_alias=True, mode="json")
    payload.pop("structure", None)
    geometry = payload.get("geometry")
    if isinstance(geometry, dict):
        geometry["density"] = DensitySpec().model_dump(mode="json")
        geometry["contour"] = ContourSpec().model_dump(mode="json")
    inputs = payload.setdefault("inputs", {})
    inputs["profile"] = {"path": str(path), "format": PROFILE_FORMAT}
    try:
        return CaseDocument.model_validate(payload)
    except ValidationError as error:
        raise CaseValidationError(
            render_problems(f"<{document.name} with inputs.profile {path}>", error), error
        ) from None


NEUTRAL_SECTIONS: frozenset[str] = frozenset({"charge"})


def with_section(document: CaseDocument, name: str) -> CaseDocument:
    if name not in NEUTRAL_SECTIONS:
        raise ValueError(
            f"section {name!r} cannot be added from a default: only "
            f"{', '.join(sorted(NEUTRAL_SECTIONS))} resolves empty exactly as its absence, so "
            "any other would change the run or be refused; write it in the case file"
        )
    if getattr(document, name) is not None:
        raise ValueError(f"case {document.name!r} already carries a {name}: section")
    payload = document.model_dump(by_alias=True, mode="json")
    payload[name] = {}
    try:
        return CaseDocument.model_validate(payload)
    except ValidationError as error:
        raise CaseValidationError(
            render_problems(f"<{document.name} with {name}: {{}}>", error), error
        ) from None


def _set_at(payload: dict[str, FieldValue], path: str, value: FieldValue) -> None:
    components = path.split(".")
    cursor: FieldValue = payload
    for depth, component in enumerate(components[:-1]):
        prefix = ".".join(components[: depth + 1])
        if isinstance(cursor, list):
            cursor = _sequence_entry(cursor, component, path, components[: depth + 1])
            continue
        if not isinstance(cursor, dict) or cursor.get(component) is None:
            raise UnknownCasePathError(
                f"{path!r} cannot be set on this case: {prefix} is absent from it, so there "
                "is no block to substitute into; give the base case that section first"
            )
        cursor = cursor[component]
    last = components[-1]
    if isinstance(cursor, list):
        cursor[int(last)] = value
    else:
        cursor[last] = value

"""Dotted case-file paths: the schema's fields, reading, checking and substituting.

A dotted path such as ``boundary_conditions.bias_V`` names one field of the
``nanopnp/case/v2`` schema of :mod:`nanopnp.io.case`. A sweep axis, the generated
editor of the desktop shell, the FR-25 deviation record and the generated
case-file reference all index the case by such paths, so the walk over them is
written once, here, against the schema alone (FR-24, IF-09).
"""

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
    """Return the members of a ``Literal``, looking through a union and a list.

    ``list[str]`` and ``float | Literal["auto"]`` both reach here: the first
    carries no ``Literal`` and enumerates nothing, and the second enumerates only
    ``auto``, which is exactly what an editor should offer beside a free numeric
    entry.
    """
    for candidate in (annotation, *get_args(annotation)):
        if get_origin(candidate) is Literal:
            return tuple(str(value) for value in get_args(candidate))
    return None


class UnknownCasePathError(KeyError):
    """A dotted path does not name a field of the case schema (IF-03, FR-24).

    Raised by :func:`field_at` before anything is read or written, so that a
    misspelt sweep axis is refused at plan time by the component that is wrong
    rather than a day later by a member that solved something else. A
    :class:`KeyError` still, so a caller written against the mapping-like
    reading of a path keeps working, but a *named* one: the CLI classifies it as
    the case error it is (IF-02).
    """

    def __str__(self) -> str:
        """Return the message as written, without :class:`KeyError`'s quoting."""
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class FieldReference:
    """One field of the case schema, found by its dotted path.

    Parameters
    ----------
    path
        The dotted path, as it was given.
    annotation
        The type the schema declares at that path. For an entry of a mapping- or
        sequence-valued field it is the *element* type, which is what a value
        written there has to satisfy.
    container
        ``"model"`` for a declared field of a block, ``"mapping"`` for an entry
        of a ``dict``-valued one, ``"sequence"`` for an element of a list. The
        distinction matters to substitution: a mapping entry may be created, a
        model field may not, and a sequence index must already exist.
    """

    path: str
    annotation: FieldType
    container: Literal["model", "mapping", "sequence"] = "model"

    def validate(self, value: FieldValue) -> FieldValue:
        """Return ``value`` as the schema's declared type accepts it.

        Raises
        ------
        CaseValidationError
            If the declared type refuses it, naming the path, the value and
            what was expected. Re-validating the whole document would catch this
            too, but only per point and only after a plan has committed to
            thousands of them (FR-24).
        """
        try:
            return _adapter(self.annotation).validate_python(value)
        except ValidationError as error:
            reasons = "; ".join(problem["msg"] for problem in error.errors())
            raise CaseValidationError(
                f"{self.path}: {value!r} is not a value this field accepts "
                f"({_annotation_name(self.annotation)}): {reasons}"
            ) from None


_ADAPTERS: dict[object, TypeAdapter[object]] = {}
"""One :class:`~pydantic.TypeAdapter` per declared type, built on first use.

Building an adapter compiles a core schema, and a sweep validates every
assignment of every member: building them anew was a quarter of planning the
§8.3 reference sweep (WP33 D12). An adapter holds no state between validations.
"""


def _adapter(annotation: FieldType) -> TypeAdapter[object]:
    """Return the cached adapter for ``annotation``, or a new one if it is unhashable."""
    try:
        adapter = _ADAPTERS.get(annotation)
    except TypeError:
        return TypeAdapter(annotation)
    if adapter is None:
        adapter = _ADAPTERS[annotation] = TypeAdapter(annotation)
    return adapter


def _annotation_name(annotation: FieldType) -> str:
    """Return a readable name for a declared type, for a diagnostic."""
    return getattr(annotation, "__name__", None) or str(annotation).replace("typing.", "")


def _entry_annotation(
    annotation: FieldType,
) -> tuple[FieldType, Literal["mapping", "sequence"]] | None:
    """Return the element type of a mapping- or sequence-valued annotation.

    ``dict[str, float]`` gives ``(float, "mapping")`` and ``list[str]`` gives
    ``(str, "sequence")``; anything else gives ``None``. Walking through the
    container is what lets a sweep vary ``physics.solid_permittivities.membrane``
    or one entry of ``electrolyte.species`` without a second path syntax.
    """
    for candidate in (annotation, *get_args(annotation)):
        origin = get_origin(candidate)
        arguments = get_args(candidate)
        if origin in (dict, Mapping) and len(arguments) == 2:
            return arguments[1], "mapping"
        if origin in (list, Sequence) and len(arguments) == 1:
            return arguments[0], "sequence"
    return None


def field_at(path: str) -> FieldReference:
    """Return the schema's declaration of the field a dotted path names.

    The inverse of :func:`nanopnp.io.defaults.value_at`'s walk, taken over the
    *schema* rather than over a document, so that a path can be checked before
    any case is substituted into (FR-24, §5.3.4). Two loud failures rather than
    one: this names a component that does not exist, and
    :meth:`FieldReference.validate` names a value the field would not accept.

    Parameters
    ----------
    path
        Dotted path under the aliases a case file writes, e.g.
        ``"boundary_conditions.bias_V"`` or
        ``"electrolyte.corrections.diffusivity.wall"``.

    Returns
    -------
    FieldReference
        The declared type and how it is reached.

    Raises
    ------
    UnknownCasePathError
        If any component is not a field of the block it is read from, naming the
        prefix that does exist, the component that does not, and what that block
        accepts (QR-12).
    """
    components = [part for part in path.split(".") if part]
    if not components:
        raise UnknownCasePathError("a case-file path cannot be empty")

    owner: type[BaseModel] | None = CaseDocument
    annotation: FieldType = CaseDocument
    container: Literal["model", "mapping", "sequence"] = "model"
    walked: list[str] = []

    for component in components:
        # The container is tried first, because a ``list[SpeciesSpec]`` carries
        # a model *and* is indexed: ``electrolyte.species.0.name`` steps through
        # the list before it reaches the block, and asking the block first would
        # report ``0`` as an unknown field of ``SpeciesSpec``.
        entry = _entry_annotation(annotation)
        if entry is not None and entry[1] == "sequence" and not _is_index(component):
            # A list is reached only by index. Without this the container branch
            # below would swallow ``electrolyte.species.name`` as though ``name``
            # were an index, hand back the *element* type, and leave the path to
            # fail much later inside a substitution (FR-24, QR-12).
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
"""The index :func:`case_fields` stands on inside a sequence of blocks.

The walk is over the *schema*, which fixes no length, so a representative index
is the only way to name a field of ``electrolyte.species`` at all. ``0`` is the
one every non-empty document has.
"""


def case_fields() -> tuple[FieldReference, ...]:
    """Return every editable field of ``nanopnp/case/v2``, in declaration order.

    The enumeration a generated editor is built from (IF-09), and the one the
    FR-25 switch classification is checked against. It is deliberately not
    :meth:`~pydantic.BaseModel.model_json_schema`: three things the callers need
    do not survive that projection — the container kinds :class:`FieldReference`
    carries, the ``schema:`` alias, and the fact that ``check_document`` asks
    the *installed* registries rather than the document. Walking
    ``model_fields`` gives all three, and gives the dotted paths every other
    component of this package already indexes the case by as a by-product.

    A field is *editable* when it carries a value rather than a block: a leaf,
    a ``list[str]`` or a ``dict[str, float]``, but never ``numerics`` itself.
    Blocks are walked through, including through ``X | None`` and through a
    sequence of blocks — where :data:`SEQUENCE_INDEX` stands for the index, so
    that the path resolves through :func:`field_at` like any other.

    Returns
    -------
    tuple of FieldReference
        Each equal to ``field_at`` of its own path, which
        ``tests/tier1/test_case_fields.py`` asserts element by element: two
        walks over one schema drift, and the one that drifts silently is the one
        no test reads.

    Raises
    ------
    NotImplementedError
        If the schema grows a mapping whose *values* are blocks. ``nanopnp/case/v2``
        has none, and there is no representative key to stand on the way
        :data:`SEQUENCE_INDEX` stands on an index — so the walk says so rather
        than omitting the block's fields, which would make them silently
        uneditable and silently unclassified.
    """
    return tuple(_walk_fields(CaseDocument, ""))


def _walk_fields(owner: type[BaseModel], prefix: str) -> list[FieldReference]:
    """Return the editable fields of ``owner``, depth first, prefixed by ``prefix``."""
    found: list[FieldReference] = []
    for name, field in owner.model_fields.items():
        path = f"{prefix}{field.alias or name}"
        annotation = field.annotation
        entry = _entry_annotation(annotation)
        if entry is not None:
            element, kind = entry
            nested = _model_of(element)
            if nested is None:
                # list[str], dict[str, float]: the container is itself the value
                # a reader writes, and its entries are reached under it.
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
    """Return whether the schema defaults a field, and the default it declares.

    The generated case-file reference prints this beside each path of
    :func:`case_fields` (VER-45), so that the documented default is the one a
    document omitting the field is validated with, rather than a transcription.

    Parameters
    ----------
    path
        A dotted path as :func:`case_fields` names it; a sequence index stands
        for any element.

    Returns
    -------
    tuple
        ``(False, None)`` for a required field; otherwise ``(True, default)``,
        with a ``default_factory`` called for its value.

    Raises
    ------
    UnknownCasePathError
        If the path does not name a declared field of a block.
    """
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
    """Return whether a path component reads as a list index."""
    return component.removeprefix("-").isdigit()


def _field_named(owner: type[BaseModel], component: str) -> FieldInfo | None:
    """Return the field a block declares under ``component``, by alias or by name.

    By alias first, because a case file writes ``schema:`` for a field this
    module has to call ``schema_id``.
    """
    for name, field in owner.model_fields.items():
        if (field.alias or name) == component:
            return field
    return None


def _declaration(path: str) -> FieldInfo | None:
    """Return the pydantic declaration of the block field a dotted path ends on, or ``None``.

    ``None`` for a path that is not a declared field of a block: an entry of a
    mapping or of a sequence carries no declaration of its own.
    """
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
    """Return the description a field of the schema declares, or ``None``.

    The generated case-file reference prints it under its section (VER-45), so a
    normative contract written on a field — the section 5.3.1 NOTE on
    ``structure:`` — reaches the documentation without a hand-written copy.
    """
    field = _declaration(path)
    return None if field is None else field.description


def field_bounds(path: str) -> tuple[float | None, float | None]:
    """Return the inclusive bounds ``(ge, le)`` a field of the schema declares.

    Read from the field's own metadata, the constraints ``Field(ge=..., le=...)``
    puts there, so a graphical editor can size a spin box without a bound of its
    own (IF-09, WP31 D12). A bound the field does not declare, and any exclusive
    one (``gt``, ``lt``), is ``None``: a spin box cannot represent an open end.

    Raises
    ------
    UnknownCasePathError
        If the path is not one the schema declares.
    """
    field_at(path)
    field = _declaration(path)
    if field is None:
        return None, None
    lower = [float(item.ge) for item in field.metadata if getattr(item, "ge", None) is not None]
    upper = [float(item.le) for item in field.metadata if getattr(item, "le", None) is not None]
    return (max(lower) if lower else None), (min(upper) if upper else None)


def value_at(document: CaseDocument, path: str) -> FieldValue:
    """Return the value a dotted path names in a case document.

    Checked against the schema by :func:`field_at` first, so that an unknown
    component is named the same way whether it was asked of the schema or of a
    document. A path that silently resolved to ``None`` would report a switch as
    never deviating, which is the failure :mod:`nanopnp.io.defaults` exists to
    prevent.

    Raises
    ------
    UnknownCasePathError
        If the path is not one the schema declares, or if a block on the way to
        it is absent from *this* document.
    """
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
    """Return the attribute a block's alias names, e.g. ``schema`` to ``schema_id``."""
    fields: Mapping[str, FieldInfo] = getattr(owner, "model_fields", {})
    for name, field in fields.items():
        if (field.alias or name) == component:
            return name
    return component


def _sequence_entry(
    values: list[FieldValue], component: str, path: str, walked: list[str]
) -> FieldValue:
    """Return one element of a list-valued field, by index."""
    try:
        index = int(component)
        return values[index]
    except (ValueError, IndexError):
        raise UnknownCasePathError(
            f"{path!r} cannot be read from this case: {'.'.join(walked[:-1])} holds "
            f"{len(values)} entries, and {component!r} is not an index into them"
        ) from None


def substitute(document: CaseDocument, assignments: Mapping[str, FieldValue]) -> CaseDocument:
    """Return ``document`` with each dotted path set to its assigned value.

    Dump by alias, set into the plain dict, re-validate the **whole document**
    (§5.3.4). Re-validation is what makes a substitution that produces an
    inadmissible case fail with the diagnostic a hand-written case would get, for
    free: a typo hits ``extra="forbid"`` and :func:`render_problems`'s "did you mean"
    message, and a cross-field rule such as the NUM-18 ladder refusal in
    :func:`resolve` still runs. ``model_copy(update=...)`` would accept the typo,
    and rebuilding the object field by field would make a configuration that
    names itself stop being itself.

    Parameters
    ----------
    document
        The base case.
    assignments
        Dotted case-file path to the value to set there. An empty mapping
        returns an equal document, which is the all-origins point of a sweep
        with no axes.

    Returns
    -------
    CaseDocument
        Freshly validated. Never the same object as ``document``.

    Raises
    ------
    UnknownCasePathError
        If a path is not one the schema declares, or if the block it is inside
        is absent from this document.
    CaseValidationError
        If a value is not one the declared type accepts, or if the substituted
        document is not a valid case.
    """
    payload = document.model_dump(by_alias=True, mode="json")
    for path, value in assignments.items():
        reference = field_at(path)
        # Validated against the declared type first, so that the diagnostic
        # names the path rather than pydantic's own location inside a document
        # the caller never wrote. Dumped back to JSON because the payload being
        # written into is a plain dict: a validated ``Path`` set into it would
        # come back out of ``model_dump`` as an object YAML cannot write.
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
    """Return ``document`` rewritten to take its pore profile from ``path`` (WP24 D6).

    How a hand-edited contour enters a run: as a supplied profile, through
    ``inputs.profile``, which stage 5 reads exactly as it reads stage 4's
    (section 5.3.1 NOTE on ``geometry.contour``). Four things change and nothing
    else does:

    - ``structure:`` is removed, because a stage whose output is supplied does
      not run and neither does anything upstream of it;
    - ``geometry.density`` and ``geometry.contour`` are reset to their defaults,
      because stages 2 to 4 read them and do not run;
    - ``inputs.profile`` is set to ``{path, format: profile1}``;
    - the whole document is re-validated.

    :func:`substitute` cannot do this, because it sets values inside blocks the
    document already has and ``inputs.profile`` is absent from a structure case.
    The result is accepted by :func:`resolve`'s ``inputs.profile`` refusals by
    construction, and a command-line user writing it by hand gets the same file.

    Parameters
    ----------
    document
        The case whose profile is replaced: a structure case, or one already
        supplying a profile.
    path
        The profile document. Written verbatim, so a caller wanting the derived
        case to run from any working directory passes an absolute path (WP24 D7);
        case paths resolve against the process's working directory.

    Returns
    -------
    CaseDocument
        Freshly validated.

    Raises
    ------
    CaseValidationError
        If the rewritten document is not a valid case: for instance one that
        also supplies ``inputs.mesh``, which is downstream of the profile.
    """
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
"""The optional top-level sections whose empty mapping resolves exactly as their absence (WP31 D13).

``charge: {}`` and no ``charge:`` both resolve through ``Charge()``: every reader
writes ``document.charge or Charge()``, and :func:`_check_charge` refuses only keys
set away from their defaults. Kept as a set and checked in both directions by
``tests/tier1/test_case_fields.py``, never derived: of the other two optional
sections, ``structure: {}`` does not validate (it needs its point group), and
``geometry: {}`` is refused beside ``inputs.mesh`` where its absence is accepted.
Neutral means the run is unchanged, not the record: stage 9's key is the
validated dump, which carries the explicit block, so it moves as the case hash
does, and the stages keyed on it with it; every other key of stages 1 to 10 stays.
"""


def with_section(document: CaseDocument, name: str) -> CaseDocument:
    """Return ``document`` with the empty section ``name`` written into it (WP31 D13).

    How the desktop shell's **Add section** makes a block's fields editable. Only
    a section of :data:`NEUTRAL_SECTIONS` is added, because only its empty form is
    known to change nothing; a block whose presence is the physics, such as
    ``geometry.analyte``, is never added from a default.

    Raises
    ------
    ValueError
        If ``name`` is not in :data:`NEUTRAL_SECTIONS`, or the document already
        carries it.
    CaseValidationError
        If the rewritten document is not a valid case.
    """
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
    """Set ``value`` into a dumped case document at a dotted path.

    Raises
    ------
    UnknownCasePathError
        If a block on the way is absent from this document. The path is known to
        the *schema* by the time this runs -- ``structure.source.path`` is a real
        field -- and a case that declares no ``structure:`` still has nowhere to
        put it, which is a fact about the document and not about the path.
    """
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

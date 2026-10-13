"""The case editor's view-model: a case file, its fields, and what may be typed into them."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import UnionType
from typing import Literal, TypeAlias, Union, get_args, get_origin

from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
    FieldType,
    FieldValue,
    dump_case,
    render_problems,
)
from nanopnp.io.case_paths import (
    NEUTRAL_SECTIONS,
    FieldReference,
    UnknownCasePathError,
    case_fields,
    field_at,
    field_bounds,
    substitute,
    value_at,
    with_section,
)
from nanopnp.pipeline.case import load_case
from nanopnp.pipeline.checks import check_document, options_at

__all__ = [
    "ABSENT",
    "Absent",
    "CaseEditor",
    "FieldKind",
    "FieldState",
]

FieldKind: TypeAlias = Literal["flag", "choice", "selection", "bounded", "number", "text"]


class Absent:
    """The value of a field the document does not carry; not the same as ``None``."""

    def __repr__(self) -> str:
        return "ABSENT"


ABSENT = Absent()


@dataclass(frozen=True)
class FieldState:
    """One field as the editor presents it."""

    reference: FieldReference
    value: FieldValue | Absent
    options: tuple[str, ...] | None
    kind: FieldKind
    staged: bool = False
    bounds: tuple[float, float] | None = None

    @property
    def path(self) -> str:
        """The dotted path, for a caller that wants only that."""
        return self.reference.path

    @property
    def integral(self) -> bool:
        """Whether the field takes whole numbers only."""
        members = _members(self.reference.annotation)
        return int in members and float not in members


def _origin(annotation: FieldType) -> object:
    return get_origin(annotation)


def _members(annotation: FieldType) -> tuple[FieldType, ...]:
    origin = _origin(annotation)
    if origin is Union or origin is UnionType:
        return tuple(member for member in get_args(annotation) if member is not type(None))
    return (annotation,)


def _optional(annotation: FieldType) -> bool:
    origin = _origin(annotation)
    return (origin is Union or origin is UnionType) and type(None) in get_args(annotation)


def _kind(
    reference: FieldReference,
    options: tuple[str, ...] | None,
    *,
    closed: bool = False,
) -> FieldKind:
    members = _members(reference.annotation)
    numeric = any(member in (int, float) for member in members)
    if bool in members:
        return "flag"
    if options is None:
        if numeric and closed and not _optional(reference.annotation):
            return "bounded"
        return "number" if numeric else "text"
    if _origin(reference.annotation) in (list, tuple, frozenset, set):
        return "selection"
    if numeric:
        # Enumerated values beside a free number: offering only the enumeration
        # would make the number unsettable.
        return "text"
    return "choice"


@dataclass
class CaseEditor:
    """A case file open for editing: its document, its staged edits and its diagnostics.

    Parameters
    ----------
    source
        Where it was read from and where :meth:`save` writes; ``None`` for an in-memory document.
    """

    document: CaseDocument
    source: Path | None = None
    _edits: dict[str, FieldValue] = field(default_factory=dict, repr=False)
    _problems: str | None = field(default=None, repr=False)
    _unsaved: bool = field(default=False, repr=False)

    @classmethod
    def open(cls, path: str | Path) -> CaseEditor:
        """Open a case file.

        Raises
        ------
        nanopnp.io.case.CaseValidationError
            If the file is not a valid case.
        """
        source = Path(path)
        return cls(document=load_case(source), source=source)

    def fields(self) -> tuple[FieldReference, ...]:
        """Return every editable field of the schema, in declaration order."""
        return case_fields()

    def state(self, path: str) -> FieldState:
        """Return one field as the editor presents it.

        Raises
        ------
        nanopnp.io.case_paths.UnknownCasePathError
            If the path is not one the schema declares.
        """
        reference = field_at(path)
        options = options_at(path)
        lower, upper = field_bounds(path)
        closed = (lower, upper) if lower is not None and upper is not None else None
        kind = _kind(reference, options, closed=closed is not None)
        staged = path in self._edits
        return FieldState(
            reference=reference,
            value=self._edits[path] if staged else self.value(path),
            options=options,
            kind=kind,
            staged=staged,
            bounds=closed if kind == "bounded" else None,
        )

    def states(self) -> tuple[FieldState, ...]:
        """Return every field's state, in declaration order."""
        return tuple(self.state(reference.path) for reference in self.fields())

    def value(self, path: str) -> FieldValue | Absent:
        """Return the committed value at a path, or :data:`ABSENT` if its block is missing."""
        try:
            return value_at(self.document, path)
        except UnknownCasePathError:
            field_at(path)  # re-raises for a path the *schema* does not have
            return ABSENT

    def validate(self, path: str, value: FieldValue) -> FieldValue:
        """Return ``value`` as the schema's declared type accepts it at ``path``.

        Raises
        ------
        nanopnp.io.case_paths.UnknownCasePathError
            If the path is not one the schema declares.
        nanopnp.io.case.CaseValidationError
            If the declared type refuses the value.
        """
        return field_at(path).validate(value)

    def stage(self, path: str, value: FieldValue) -> FieldValue:
        """Validate a value at its field and stage it for the next commit."""
        accepted = self.validate(path, value)
        self._edits[path] = value
        self._problems = None
        return accepted

    def discard(self) -> None:
        """Drop every staged edit and the diagnostic from the last failed commit."""
        self._edits.clear()
        self._problems = None

    @property
    def staged(self) -> dict[str, FieldValue]:
        """The edits waiting to be committed, by dotted path."""
        return dict(self._edits)

    @property
    def dirty(self) -> bool:
        """Whether anything is staged or committed but not yet saved."""
        return bool(self._edits) or self._unsaved

    def commit(self) -> CaseDocument:
        """Apply every staged edit and re-validate the whole document.

        Raises
        ------
        nanopnp.io.case.CaseValidationError
            If the result is not admissible; the document and staged edits are unchanged.
        """
        try:
            # The registry and element-order checks a loaded file passes, so the editor refuses what
            # the CLI refuses.
            document = check_document(substitute(self.document, self._edits))
        except CaseValidationError as error:
            self._problems = self._render(error)
            raise CaseValidationError(self._problems, error.errors) from None
        self.document = document
        self._edits.clear()
        self._problems = None
        self._unsaved = True
        return document

    def problems(self) -> str | None:
        """Return the diagnostic from the last failed commit, or ``None``."""
        return self._problems

    def _render(self, error: CaseValidationError) -> str:
        if error.errors is None:
            return str(error)
        return render_problems(
            str(self.source) if self.source is not None else "<case>", error.errors
        )

    def addable(self) -> tuple[str, ...]:
        """Return the neutral sections :meth:`add_section` may write into this document, sorted."""
        return tuple(
            name for name in sorted(NEUTRAL_SECTIONS) if getattr(self.document, name) is None
        )

    def add_section(self, name: str) -> CaseDocument:
        """Write the empty section ``name`` into the document, so its fields can be edited.

        Raises
        ------
        ValueError
            If ``name`` is not a section that can be added, or the document already carries it.
        """
        self.document = with_section(self.document, name)
        self._problems = None
        self._unsaved = True
        return self.document

    def ensure_saved(self) -> Path:
        """Return the file this case is in, writing it only if it has changed.

        Raises
        ------
        ValueError
            If the editor was not opened from a file, or edits are still staged.
        """
        if self._edits:
            raise ValueError(
                "this case has uncommitted edits; commit them before saving, because the file "
                f"would otherwise be written without {', '.join(sorted(self._edits))} and the "
                "run made from it would not be the run that was asked for"
            )
        if self.source is None or self.dirty:
            return self.save()
        return self.source

    def save(self, path: str | Path | None = None) -> Path:
        """Write the committed document back to its file.

        Parameters
        ----------
        path
            Where to write; given, it becomes this editor's source.

        Raises
        ------
        ValueError
            If there is nowhere to write and none was given.
        """
        target = Path(path) if path is not None else self.source
        if target is None:
            raise ValueError(
                "this editor was not opened from a file and no path was given; a case must be "
                "on disk before it is run, because the case file is the unit of reproducibility "
                "and the run manifest names it"
            )
        dump_case(self.document, target)
        self.source = target
        self._unsaved = False
        return target

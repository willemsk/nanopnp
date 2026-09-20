"""The case editor's view-model: a case file, its fields, and what may be typed into them.

Generated from the schema, not written out (IF-09). :func:`~nanopnp.io.case.case_fields`
enumerates every editable dotted path of ``nanopnp/case/v1`` and
:func:`~nanopnp.io.case.options_at` says what each one admits, so this module holds
no default, no unit and no option list of its own. A second list of stabilisation
modes here would be a graphical interface offering a mode the solver does not
apply — a run whose FR-25 manifest describes something that never happened
(§5.3.3).

**No Qt, and no NGSolve.** Nothing in this module imports PySide6, and nothing
imports a stage. That is not tidiness: ``PySide6.QtWidgets`` does not import at
all on the Linux push gate (`.knowledge/07-software-stack.md` §5), so a
view-model that touched Qt could only be tested where Qt happens to work. And
``import nanopnp.io.case`` costs about what one NGSolve import costs — 253 ms
warm against NGSolve's ~370 ms, and NGSolve's is *on top* — so browsing a case
should not pay for a solver.

**Validation happens twice, and the second time is the whole document.**
:meth:`CaseEditor.stage` checks one value against the type the schema declares at
that path, which is what refuses ``"lots"`` in ``bias_V`` the moment it is typed.
:meth:`CaseEditor.commit` re-validates the *whole* document through
:func:`~nanopnp.io.case.substitute`, which is where ``extra="forbid"``, the
registry check and the cross-field rules live (§5.3.4). Both diagnostics are the
ones the command line prints for the same mistake: one error vocabulary, not two.

**The unit of work is a file on disk.** §5.3.1 makes the case file the unit of
reproducibility, so the editor opens one, edits it and saves it, and the shell
runs the saved file. A run from an in-memory document would emit a manifest
naming an input that does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import UnionType
from typing import Literal, TypeAlias, Union, get_args, get_origin

from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
    FieldReference,
    FieldType,
    FieldValue,
    UnknownCasePathError,
    case_fields,
    dump_case,
    field_at,
    load_case,
    options_at,
    render_problems,
    substitute,
    value_at,
)

__all__ = [
    "ABSENT",
    "Absent",
    "CaseEditor",
    "FieldKind",
    "FieldState",
]

FieldKind: TypeAlias = Literal["flag", "choice", "selection", "number", "text"]
"""How a field is edited: a check box, a combo box, a multiple selection, a
numeric entry or a free line. Derived from the type the schema declares, never
from a table of paths."""


class Absent:
    """The value of a field the *document* does not carry.

    ``structure.source.pdb`` is a field of ``nanopnp/case/v1`` whatever a given
    case says, and a Phase-1 case carries no ``structure:`` block at all. That is
    a fact about the document, not about the path (:func:`~nanopnp.io.case.value_at`
    says so in those words), and it is not ``None`` either: ``None`` is a value
    several fields may legitimately hold.
    """

    def __repr__(self) -> str:
        """Render as the singleton's name, so a diagnostic reads plainly."""
        return "ABSENT"


ABSENT = Absent()
"""The singleton :class:`Absent`."""


@dataclass(frozen=True)
class FieldState:
    """One field as the editor presents it.

    Parameters
    ----------
    reference
        The schema's declaration, exactly as :func:`~nanopnp.io.case.field_at`
        returns it.
    value
        What this document holds there, or :data:`ABSENT` when the block it
        lives in is not in this document, or the staged edit when there is one.
    options
        Every value the field admits, or ``None`` where they are not
        enumerable. Always :func:`~nanopnp.io.case.options_at` of the path.
    kind
        How to edit it.
    staged
        Whether :attr:`value` is an uncommitted edit rather than the document's.
    """

    reference: FieldReference
    value: FieldValue | Absent
    options: tuple[str, ...] | None
    kind: FieldKind
    staged: bool = False

    @property
    def path(self) -> str:
        """The dotted path, for a caller that wants only that."""
        return self.reference.path


def _origin(annotation: FieldType) -> object:
    """Return ``get_origin`` widened to ``object``.

    ``typing.get_origin`` is overloaded finely enough that comparing its result
    against ``Literal`` or against ``list`` reads to the checker as comparing
    two disjoint types; the values here are whatever pydantic put on a field, so
    ``object`` is the honest static type for them.
    """
    return get_origin(annotation)


def _members(annotation: FieldType) -> tuple[FieldType, ...]:
    """Return a union's members with ``None`` removed, or the annotation itself."""
    origin = _origin(annotation)
    if origin is Union or origin is UnionType:
        return tuple(member for member in get_args(annotation) if member is not type(None))
    return (annotation,)


def _kind(reference: FieldReference, options: tuple[str, ...] | None) -> FieldKind:
    """Return how a field is edited, from the type the schema declares.

    The order matters where a type is two things at once.
    ``numerics.mesh.wall_h_nm`` is ``float | Literal["auto"]``: it enumerates
    ``auto`` and still takes any number, so it stays a free line rather than
    becoming a combo box that could not express a mesh size. ``physics.model``
    is the mirror image — a plain ``str`` whose admissible values come from a
    registry rather than from its annotation — and is a combo box for that
    reason, which is the whole point of asking
    :func:`~nanopnp.io.case.options_at` rather than the annotation alone.
    """
    members = _members(reference.annotation)
    numeric = any(member in (int, float) for member in members)
    if bool in members:
        return "flag"
    if options is None:
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
    document
        The validated case as last committed.
    source
        Where it was read from and where :meth:`save` writes. ``None`` for a
        document assembled in memory, which :meth:`save` then refuses rather
        than inventing a path — the file is the unit of reproducibility, and the
        shell must not run one that is not on disk (§5.3.1).
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
            If the file is not a valid case, with the diagnostic the command
            line prints for the same file.
        """
        source = Path(path)
        return cls(document=load_case(source), source=source)

    # -- reading ------------------------------------------------------------

    def fields(self) -> tuple[FieldReference, ...]:
        """Return every editable field of the schema, in declaration order."""
        return case_fields()

    def state(self, path: str) -> FieldState:
        """Return one field as the editor presents it.

        Raises
        ------
        nanopnp.io.case.UnknownCasePathError
            If the path is not one the schema declares.
        """
        reference = field_at(path)
        options = options_at(path)
        staged = path in self._edits
        return FieldState(
            reference=reference,
            value=self._edits[path] if staged else self.value(path),
            options=options,
            kind=_kind(reference, options),
            staged=staged,
        )

    def states(self) -> tuple[FieldState, ...]:
        """Return every field's state, in declaration order."""
        return tuple(self.state(reference.path) for reference in self.fields())

    def value(self, path: str) -> FieldValue | Absent:
        """Return what the committed document holds at a path.

        :data:`ABSENT` where the block is not in this document; see
        :class:`Absent` for why that is not ``None``.
        """
        try:
            return value_at(self.document, path)
        except UnknownCasePathError:
            field_at(path)  # re-raises for a path the *schema* does not have
            return ABSENT

    # -- editing ------------------------------------------------------------

    def validate(self, path: str, value: FieldValue) -> FieldValue:
        """Return ``value`` as the schema's declared type accepts it at ``path``.

        Raises
        ------
        nanopnp.io.case.UnknownCasePathError
            If the path is not one the schema declares.
        nanopnp.io.case.CaseValidationError
            If the declared type refuses the value, naming the path, the value
            and the type — the diagnostic
            :meth:`~nanopnp.io.case.FieldReference.validate` already writes, so
            the interface and the sweep planner refuse a bad value in the same
            words.
        """
        return field_at(path).validate(value)

    def stage(self, path: str, value: FieldValue) -> FieldValue:
        """Validate a value at its field and hold it for the next commit.

        The document is **not** touched: a per-field check cannot know whether
        the result is an admissible case, so nothing moves until
        :meth:`commit` has re-validated the whole of it.

        Returns
        -------
        The value as the declared type accepts it.
        """
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
        """Apply every staged edit and re-validate the whole document (§5.3.4).

        Returns
        -------
        CaseDocument
            The new document, which is also this editor's from now on. Staged
            edits are cleared.

        Raises
        ------
        nanopnp.io.case.CaseValidationError
            If the substituted document is not an admissible case. The document
            is left exactly as it was, the edits stay staged so the user can fix
            one of them, and :meth:`problems` returns the diagnostic — rendered
            against this editor's own source, so it is character for character
            what the command line prints for a file holding the same mistake.
        """
        try:
            document = substitute(self.document, self._edits)
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
        """Re-render a substitution failure against this editor's own source.

        :func:`~nanopnp.io.case.substitute` names the document and the paths it
        substituted, which is right for a sweep member assembled in memory and
        wrong here: the user is looking at a file, and the message must be the
        one they would get from ``nanopnp run`` on it.
        """
        if error.errors is None:
            return str(error)
        return render_problems(
            str(self.source) if self.source is not None else "<case>", error.errors
        )

    # -- the file -----------------------------------------------------------

    def ensure_saved(self) -> Path:
        """Return the file this case is in, writing it only if it has changed.

        What "Run" needs, and it is not :meth:`save`. A case file is written by
        hand: it carries comments, its own key order and ``1`` where
        :func:`~nanopnp.io.case.dumps_case` writes ``1.0``, none of which
        survives a round trip and none of which changes the run (§5.3.1 NOTE).
        Rewriting an untouched file would throw all of that away to no purpose,
        so a run that changed nothing runs the bytes the user wrote.

        Returns
        -------
        Path
            The file to run.

        Raises
        ------
        ValueError
            If this editor was not opened from a file; see :meth:`save`. Or if
            edits are still staged: :meth:`save` writes :attr:`document`, which
            does not carry them, so saving here would hand the caller a file
            that is missing what the user typed — and then run it. The caller
            commits first, and sees the whole-document diagnostic if the commit
            is refused.
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
            Where to write, defaulting to the file this editor was opened from.
            Given, it becomes this editor's source, which is what "save as"
            means.

        Returns
        -------
        Path
            The file written.

        Raises
        ------
        ValueError
            If there is nowhere to write and none was given. The case file is
            the unit of reproducibility (§5.3.1), so a run of an unsaved
            document would emit a manifest naming an input that does not exist —
            better refused here than recorded there.
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

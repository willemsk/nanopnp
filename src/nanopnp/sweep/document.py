"""The ``nanopnp/sweep/v1`` specification document (FR-24, IF-03, §5.3.4).

A sweep is specified by its **own** declarative document, naming a base case by
path and the axes to vary. Nothing is added to ``nanopnp/case/v1``, which WP7
froze: a sweep block inside a case would make that case's content hash — and
every artefact key derived from it — a function of a sweep the run does not
perform, and the same base case is swept three different ways in a week.

An **axis** is a named, ordered list of **assignments**, an assignment being a
mapping of dotted case-file paths to the values to set there. An axis varying one
path may be written as ``path:`` plus ``values:``, which is sugar for the same
thing and is expanded here rather than carried as a second concept. Axes combine
as a Cartesian product in declaration order.

The diagnostics copy :mod:`nanopnp.io.case` exactly, ordering included: the
``schema:`` string is checked before structural validation, every model forbids
unknown keys, and the message names the offending key with a suggestion from the
block that rejected it. A sweep document is a configuration file a person writes
by hand, and IF-03's requirement is about that rather than about the case schema
in particular.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nanopnp.io.artefact import SWEEP_SCHEMA
from nanopnp.io.case import CaseValidationError, FieldValue, render_problems

__all__ = [
    "SCHEMA",
    "Axis",
    "SweepDocument",
    "load_sweep",
    "loads_sweep",
]

SCHEMA: str = SWEEP_SCHEMA
"""Schema identifier every sweep document must declare.

Defined in :mod:`nanopnp.io.artefact` beside the artefact that carries it, so
that the string a document declares and the string the store addresses the
collected dataset by cannot drift apart.
"""

Assignment = Mapping[str, FieldValue]
"""One point of one axis: dotted case-file paths to the values to set there."""


class _Strict(BaseModel):
    """Base for every block: unknown keys are rejected, and named in the error."""

    model_config = ConfigDict(extra="forbid")


class Axis(_Strict):
    """One axis of the sweep grid: an ordered list of assignments (§5.3.4).

    Written either as ``assignments:``, a list of path-to-value mappings, or as
    ``path:`` plus ``values:`` for the common case of an axis moving one field.
    The two forms mean the same thing and :meth:`points` returns it; there is no
    third form and deliberately no ``zip:`` operator, an assignment already
    being how several paths are moved together.

    Parameters
    ----------
    name
        The axis's name, used in diagnostics and in the plan file. It names no
        case-file field and reaches no manifest.
    assignments
        The points of this axis, in order.
    path, values
        The single-path sugar. Exactly one of ``assignments`` and this pair is
        given.
    origin
        Index of the point the warm-start forest is rooted at along this axis,
        defaulting to the first. Declared rather than assumed because an axis
        running -200 to +200 mV has its *hardest* corner at index 0: rooting
        there would climb the ladder cold at -200 mV and then walk 400 mV in one
        direction, where rooting at 0 mV walks outward 200 mV each way.
    """

    name: str
    assignments: list[dict[str, FieldValue]] | None = None
    path: str | None = None
    values: list[FieldValue] | None = None
    origin: int = 0

    @model_validator(mode="after")
    def _one_form_and_a_real_origin(self) -> Axis:
        """Reject an axis written in neither form, in both, or rooted off its end."""
        sugar = self.path is not None or self.values is not None
        if sugar == (self.assignments is not None):
            raise ValueError(
                f"axis {self.name!r} is written either as assignments: (a list of "
                "path-to-value mappings) or as path: plus values: (one path, several "
                "values), and this one gives " + ("both" if sugar else "neither")
            )
        if sugar and (self.path is None or self.values is None):
            raise ValueError(
                f"axis {self.name!r} gives {'path' if self.path else 'values'} without the "
                "other; the single-path form needs both"
            )
        if not self.points():
            raise ValueError(f"axis {self.name!r} declares no values, so it varies nothing")
        if not 0 <= self.origin < len(self.points()):
            raise ValueError(
                f"axis {self.name!r} declares origin {self.origin}, which is not an index into "
                f"its {len(self.points())} values (0 to {len(self.points()) - 1})"
            )
        return self

    def points(self) -> tuple[Assignment, ...]:
        """Return this axis's assignments, expanding the single-path form."""
        if self.assignments is not None:
            return tuple(dict(entry) for entry in self.assignments)
        if self.path is None or self.values is None:  # pragma: no cover - the validator refuses it
            return ()
        return tuple({self.path: value} for value in self.values)

    def paths(self) -> tuple[str, ...]:
        """Return every case-file path this axis writes, in first-seen order."""
        seen: dict[str, None] = {}
        for assignment in self.points():
            for path in assignment:
                seen.setdefault(path, None)
        return tuple(seen)


class SweepDocument(_Strict):
    """A validated sweep specification (schema ``nanopnp/sweep/v1``).

    ``schema`` is carried under an alias so the reserved name does not shadow
    ``BaseModel``, exactly as :class:`nanopnp.io.case.CaseDocument` does.
    """

    schema_id: str = Field(alias="schema")
    name: str
    base: Path
    axes: list[Axis] = Field(default_factory=list)
    workers: int | None = None
    """Default worker count for a local run, overridden by ``--workers``.

    A convenience for a checked-in document, not a physics quantity: it changes
    how long the sweep takes and no number it produces, which is why the IF-02
    rule against flags that change a case-file field does not reach it.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _names_are_distinct(self) -> SweepDocument:
        """Reject two axes sharing a name, which no diagnostic could then tell apart."""
        names = [axis.name for axis in self.axes]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(
                f"axis names must be distinct; {', '.join(repr(n) for n in duplicates)} "
                "appears more than once"
            )
        return self

    def base_path(self, source: Path | None) -> Path:
        """Return the base case's path, resolved against the sweep document's own.

        Relative to the document rather than to the working directory: a sweep
        checked into ``docs/sweeps/`` names a case beside it, and that pairing
        must survive being run from anywhere (§8.3).
        """
        if self.base.is_absolute() or source is None:
            return self.base
        return (source.parent / self.base).resolve()

    def shape(self) -> tuple[int, ...]:
        """Return the length of each axis, in declaration order."""
        return tuple(len(axis.points()) for axis in self.axes)

    def origins(self) -> tuple[int, ...]:
        """Return each axis's declared origin index, in declaration order."""
        return tuple(axis.origin for axis in self.axes)

    def summary(self) -> dict[str, object]:
        """Return the record the plan file carries of what was asked for."""
        return {
            "schema": self.schema_id,
            "name": self.name,
            "base": str(self.base),
            "axes": [
                {
                    "name": axis.name,
                    "paths": list(axis.paths()),
                    "length": len(axis.points()),
                    "origin": axis.origin,
                }
                for axis in self.axes
            ],
        }


def loads_sweep(text: str, *, source: str = "<string>") -> SweepDocument:
    """Validate a sweep document from YAML text.

    Parameters
    ----------
    text
        The document.
    source
        Name used in diagnostics.

    Raises
    ------
    CaseValidationError
        If the schema string is wrong or the document does not validate. The
        same exception as a bad case file raises, and for the same reason: both
        are IF-03 configuration documents, both are refused by an edit rather
        than by a retry, and IF-02 gives that one exit class.
    """
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise CaseValidationError(f"{source} is not valid YAML: {error}") from None
    if not isinstance(parsed, dict):
        found = type(parsed).__name__
        raise CaseValidationError(
            f"{source} holds a {found} at the top level, not a sweep document"
        )
    _check_schema(parsed, source)
    try:
        return SweepDocument.model_validate(parsed)
    except ValidationError as error:
        raise CaseValidationError(render_problems(source, error), error) from None


def _check_schema(parsed: Mapping[str, object], source: str) -> None:
    """Reject a document declaring another schema, before structural validation.

    Ordered this way so a document written to a future schema fails naming the
    schema it claims, rather than with a wall of field errors against a shape it
    never declared.
    """
    declared = parsed.get("schema")
    if declared != SCHEMA:
        raise CaseValidationError(
            f"{source} declares schema {declared!r}; this build reads {SCHEMA!r}"
        )


def load_sweep(path: str | Path) -> SweepDocument:
    """Read and validate a sweep document.

    Parameters
    ----------
    path
        The YAML sweep file.

    Returns
    -------
    SweepDocument
        Validated. Its ``base`` is resolved against this file by
        :meth:`SweepDocument.base_path`, which needs the path and so is not done
        here.
    """
    source = Path(path)
    return loads_sweep(source.read_text(encoding="utf-8"), source=str(source))


def merged(assignments: Sequence[Assignment], axes: Sequence[Axis]) -> dict[str, FieldValue]:
    """Return one point's assignments, merged across the axes in declaration order.

    Raises
    ------
    ValueError
        If two axes write the same case-file path. The later one would win
        silently, and an axis whose values never reach the case is an axis whose
        column of the dataset is a lie: the sweep would report varying a field
        it held fixed (QR-12).
    """
    merged_assignment: dict[str, FieldValue] = {}
    owner: dict[str, str] = {}
    for axis, assignment in zip(axes, assignments, strict=True):
        for path, value in assignment.items():
            if path in owner:
                raise ValueError(
                    f"axes {owner[path]!r} and {axis.name!r} both write {path!r}; one would "
                    "silently overwrite the other and the dataset would report an axis the "
                    "members never varied"
                )
            owner[path] = axis.name
            merged_assignment[path] = value
    return merged_assignment

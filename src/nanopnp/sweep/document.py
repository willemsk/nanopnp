"""The nanopnp/sweep/v0.5 specification document (FR-24, IF-03, §5.3.4)."""

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

Assignment = Mapping[str, FieldValue]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Axis(_Strict):
    """One axis of the sweep grid: an ordered list of assignments.

    Parameters
    ----------
    name
        Used in diagnostics and the plan file.
    origin
        Index of the point the warm-start forest is rooted at.
    """

    name: str
    assignments: list[dict[str, FieldValue]] | None = None
    path: str | None = None
    values: list[FieldValue] | None = None
    origin: int = 0

    @model_validator(mode="after")
    def _one_form_and_a_real_origin(self) -> Axis:
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
    """A validated sweep specification."""

    schema_id: str = Field(alias="schema")
    name: str
    base: Path
    axes: list[Axis] = Field(default_factory=list)
    workers: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _names_are_distinct(self) -> SweepDocument:
        names = [axis.name for axis in self.axes]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(
                f"axis names must be distinct; {', '.join(repr(n) for n in duplicates)} "
                "appears more than once"
            )
        return self

    def base_path(self, source: Path | None) -> Path:
        """Return the base case's path, resolved against the sweep document's directory."""
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
    source
        Name used in diagnostics.
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
    declared = parsed.get("schema")
    if declared != SCHEMA:
        raise CaseValidationError(
            f"{source} declares schema {declared!r}; this build reads {SCHEMA!r}"
        )


def load_sweep(path: str | Path) -> SweepDocument:
    """Read and validate a sweep document from path."""
    source = Path(path)
    return loads_sweep(source.read_text(encoding="utf-8"), source=str(source))


def merged(assignments: Sequence[Assignment], axes: Sequence[Axis]) -> dict[str, FieldValue]:
    """Return one point's assignments, merged across the axes; refuse a path two axes write."""
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

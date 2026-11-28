"""The switch records: each on-off setting of the model, its case path and what it brings in."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "SWITCHES",
    "Conflict",
    "Relation",
    "Switch",
    "away",
    "conflicts",
    "governing",
    "in_force",
    "switch",
    "switch_at",
]


@dataclass(frozen=True)
class Relation:
    """Another switch that one requires or excludes, and why."""

    switch: str
    why: str


@dataclass(frozen=True)
class Switch:
    """One switch of the model equations (section 5.4.4).

    Parameters
    ----------
    path
        The case leaf that sets it.
    default
        Its value in the validated model; any other value is a deviation (FR-25).
    terms
        The names of the display terms it brings in force; a term is in force only while every
        record naming it is true.
    requires
        The switches that must be true while this one is.
    excludes
        The switches that must be false while this one is true.
    """

    name: str
    path: str
    default: bool
    terms: tuple[str, ...] = ()
    requires: tuple[Relation, ...] = ()
    excludes: tuple[Relation, ...] = ()


@dataclass(frozen=True)
class Conflict:
    """A switch that is true while one it requires is false, or one it excludes is true."""

    switch: str
    kind: Literal["requires", "excludes"]
    other: str
    why: str

    def __str__(self) -> str:
        return f"{self.switch} {self.kind} {self.other}: {self.why}"


SWITCHES: tuple[Switch, ...] = (
    Switch(
        "flow",
        "physics.flow",
        True,
        (
            "Advection",
            "Momentum",
            "Inertia",
            "Velocity continuity",
            "Variable density",
            "Body force",
        ),
    ),
    Switch("variable_density", "physics.variable_density", True, ("Variable density",)),
    Switch("inertia", "physics.inertia", True, ("Inertia",)),
    Switch(
        "dielectric_gradient_forces",
        "physics.dielectric_gradient_forces",
        False,
        ("Dielectric decrement", "Dielectric-gradient force"),
        requires=(
            Relation(
                "flow",
                "PHY-23 adds the force on the fluid and the term in each ion's flux together, "
                "and a model with no flow has no force term",
            ),
        ),
    ),
)
"""Every switch, in the order a reader lists them."""


def switch(name: str) -> Switch:
    """Return the record of the switch called ``name``.

    Raises
    ------
    KeyError
        If no record has the name; the message names the records.
    """
    for record in SWITCHES:
        if record.name == name:
            return record
    known = ", ".join(record.name for record in SWITCHES)
    raise KeyError(f"no switch is called {name!r}; the switches are {known}")


def switch_at(path: str) -> Switch | None:
    """Return the record a case path sets, or None where it sets no switch."""
    return next((record for record in SWITCHES if record.path == path), None)


def governing(term: str) -> tuple[Switch, ...]:
    """Return the records that name ``term``, with each switch they require, in record order."""
    named = {record.name for record in SWITCHES if term in record.terms}
    for record in SWITCHES:
        if record.name in named:
            named |= {relation.switch for relation in record.requires}
    return tuple(record for record in SWITCHES if record.name in named)


def _value(record: Switch, values: Mapping[str, bool]) -> bool:
    return bool(values.get(record.name, record.default))


def in_force(term: str, values: Mapping[str, bool]) -> bool:
    """Return whether every record governing ``term`` is true; a missing name is at default."""
    return all(_value(record, values) for record in governing(term))


def conflicts(values: Mapping[str, bool]) -> tuple[Conflict, ...]:
    """Return each true record whose required switch is false or whose excluded switch is true."""
    found: list[Conflict] = []
    for record in SWITCHES:
        if not _value(record, values):
            continue
        found += [
            Conflict(record.name, "requires", relation.switch, relation.why)
            for relation in record.requires
            if not _value(switch(relation.switch), values)
        ]
        found += [
            Conflict(record.name, "excludes", relation.switch, relation.why)
            for relation in record.excludes
            if _value(switch(relation.switch), values)
        ]
    return tuple(found)


def away(values: Mapping[str, bool]) -> tuple[Switch, ...]:
    """Return the records ``values`` sets off their validated default."""
    return tuple(record for record in SWITCHES if _value(record, values) != record.default)

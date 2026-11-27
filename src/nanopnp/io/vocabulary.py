"""The field names every layer shares: the solved fields a mesh, a model and an export name."""

from __future__ import annotations

POTENTIAL = "potential"

VELOCITY = "velocity"

VELOCITY_AXIS = "velocity_axis"

PRESSURE = "pressure"

PRESSURE_MEAN = "pressure_mean"


def concentration_field_name(species: str) -> str:
    """Return the field name holding one species' concentration."""
    return f"c_{species}"

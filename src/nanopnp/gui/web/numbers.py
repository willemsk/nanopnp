"""How the workbench shows a number: its significant figures, and unit prefixes or powers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Literal

__all__ = ["Style", "shown"]

Style = Literal["prefixes", "powers"]

# A prefixable unit of the case schema: its symbol unprefixed, and the factor from the field's unit.
_BASE: dict[str, tuple[str, float]] = {
    "nanometer": ("m", 1e-9),
    "nanosecond": ("s", 1e-9),
    "volt": ("V", 1.0),
    "molar": ("M", 1.0),
}
# A unit shown as it is, never prefixed.
_SYMBOL: dict[str, str] = {
    "kelvin": "K",
    "elementary_charge": "e",
    "coulomb / meter ** 2": "C/m²",
    "dimensionless": "",
}
_GAP = "\u202f"
"""The narrow no-break space between a number and its unit."""
_PREFIXES = {-15: "f", -12: "p", -9: "n", -6: "µ", -3: "m", 0: "", 3: "k", 6: "M", 9: "G", 12: "T"}
_PLAIN = (1e-3, 1e6)
"""A number without a unit is written out between these magnitudes, else with a power of ten."""


def _figures(value: float, figures: int) -> str:
    if value == 0:
        return "0"
    places = figures - 1 - math.floor(math.log10(abs(value)))
    text = f"{round(value, places):.{max(places, 0)}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _power(value: float, figures: int) -> str:
    mantissa, exponent = f"{value:.{figures - 1}e}".split("e")
    if "." in mantissa:
        mantissa = mantissa.rstrip("0").rstrip(".")
    return f"{mantissa}e{int(exponent)}"


def shown(value: object, unit: str | None, *, figures: int, style: Style) -> str:
    """Return ``value`` as the workbench shows it, its unit after it where it has one.

    ``unit`` is a field's unit as the case schema names it (``io.variables.field_unit``), or None
    for a value that is not a number. A whole number and a value that is not a number are shown
    as they are; None reads "not set". A mapping lists each key with its value, a list its values,
    and an empty one reads "none".
    """
    if value is None:
        return "not set"
    if isinstance(value, Mapping):
        named = (
            f"{key} {shown(entry, unit, figures=figures, style=style)}"
            for key, entry in value.items()
        )
        return ", ".join(named) or "none"
    if isinstance(value, list | tuple):
        listed = (shown(entry, unit, figures=figures, style=style) for entry in value)
        return ", ".join(listed) or "none"
    if isinstance(value, bool) or not isinstance(value, int | float) or unit is None:
        return str(value)
    if unit in _BASE:
        symbol, factor = _BASE[unit]
        base = float(value) * factor
        if style == "powers":
            return f"{_power(base, figures)}{_GAP}{symbol}"
        if base == 0:
            return f"0{_GAP}{symbol}"
        power = min(max(3 * math.floor(math.log10(abs(base)) / 3), -15), 12)
        text = _figures(base / 10**power, figures)
        # Rounding can carry the figures to 1000 (999.96 nm at four), which is the next prefix's 1.
        if power < max(_PREFIXES) and abs(float(text)) >= 1000:
            power += 3
            text = _figures(base / 10**power, figures)
        return f"{text}{_GAP}{_PREFIXES[power]}{symbol}"
    symbol = _SYMBOL.get(unit, unit)
    if isinstance(value, int):
        text = str(value)
    elif style == "powers" or not (value == 0 or _PLAIN[0] <= abs(value) < _PLAIN[1]):
        text = _power(float(value), figures)
    else:
        text = _figures(float(value), figures)
    return f"{text}{_GAP}{symbol}" if symbol else text

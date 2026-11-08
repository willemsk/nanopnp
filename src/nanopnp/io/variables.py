"""Case variables: named values with units and formulas of them, resolved to numbers."""

from __future__ import annotations

import ast
import math
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from typing import Any, Literal, TypeAlias, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nanopnp.io.case import CaseValidationError, FieldType, FieldValue
from nanopnp.io.case_paths import SEQUENCE_INDEX, _entry_annotation, _literal_options, case_fields

FUNCTIONS: tuple[str, ...] = ("sqrt", "exp", "log", "abs", "min", "max")

MAX_EXPRESSION_LENGTH = 256

# A unit follows from the last component of a field's name; the longest suffix is tried first.
SUFFIX_UNITS: dict[str, str] = {
    "_C_m2": "coulomb / meter ** 2",
    "_nm": "nanometer",
    "_ns": "nanosecond",
    "_V": "volt",
    "_M": "molar",
    "_K": "kelvin",
    "_e": "elementary_charge",
}

DIMENSIONLESS: frozenset[str] = frozenset(
    {
        "geometry.density.sharpness",
        "geometry.contour.isolevel",
        "charge.ph",
        "charge.edits.0.radius_scale",
        "charge.smearing.sharpness",
        "electrolyte.species.0.z",
        "physics.solid_permittivities",
        "numerics.mesh.size_scale",
        "numerics.nonlinear.max_iter",
        "numerics.nonlinear.rtol",
        "structure.ensemble.frames.count",
    }
)

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")

# Above this many bits an exact Fraction is carried as a float, so a nested power cannot grow
# without bound inside 256 characters.
_EXACT_BITS = 2048

_EXACT_POWER = 64

_DIMENSIONLESS = "dimensionless"

_BINARY: dict[type[ast.operator], str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Pow: "**",
}

_UNARY: tuple[type[ast.unaryop], ...] = (ast.UAdd, ast.USub)

Number = Fraction | float

# pint's quantities and registry are not typed to the depth mypy --strict reads.
Quantity: TypeAlias = Any

Registry: TypeAlias = Any


@cache
def _registry() -> Registry:
    # Deferred: importing pint imports NumPy, and a case without variables never needs either.
    import pint

    # Exact fractions: 20 Å is 2 nm, not 1.9999999999999998, so equal cases share one key.
    return pint.UnitRegistry(non_int_type=Fraction)


class Variable(BaseModel):
    """One variable of a case: a value or an expression of other variables, with its unit."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    value: float | None = Field(default=None, allow_inf_nan=False)
    expression: str | None = None
    unit: str = Field(default=_DIMENSIONLESS, min_length=1, max_length=64)

    @model_validator(mode="after")
    def _exactly_one(self) -> Variable:
        if (self.value is None) == (self.expression is None):
            raise ValueError("give exactly one of value: and expression:")
        return self

    def written(self) -> dict[str, Any]:
        """Return the definition as a case file writes it."""
        return self.model_dump(exclude_none=True)


@dataclass(frozen=True, eq=False)
class Resolution:
    """What resolving a case's variables found.

    Parameters
    ----------
    definitions
        Each variable as written.
    values
        Each variable's value as a float in its declared unit.
    expressions
        Field path to the expression the case wrote there.
    uses
        Variable name or field path to the variable names its expression reads directly.
    """

    definitions: Mapping[str, Variable]
    values: Mapping[str, float]
    expressions: Mapping[str, str]
    uses: Mapping[str, frozenset[str]]


def _kind(annotation: FieldType) -> Literal["int", "float"] | None:
    if hasattr(annotation, "__metadata__"):
        return _kind(get_args(annotation)[0])
    options = [annotation, *get_args(annotation)]
    flat = [get_args(item)[0] if hasattr(item, "__metadata__") else item for item in options]
    if float in flat:
        return "float"
    return "int" if int in flat else None


@cache
def _numeric() -> dict[str, tuple[Literal["int", "float"], FieldType, bool]]:
    found: dict[str, tuple[Literal["int", "float"], FieldType, bool]] = {}
    for reference in case_fields():
        entry = _entry_annotation(reference.annotation)
        if entry is not None and entry[1] == "mapping":
            kind = _kind(entry[0])
            if kind is not None:
                found[reference.path] = (kind, entry[0], True)
            continue
        kind = _kind(reference.annotation)
        if kind is not None:
            found[reference.path] = (kind, reference.annotation, False)
    return found


def numeric_paths() -> tuple[str, ...]:
    """Return the generic path of every case field that takes a number.

    A list is entered at index ``0``, and a mapping of numbers is one entry.
    """
    return tuple(_numeric())


def field_unit(path: str) -> str:
    """Return the unit text a numeric field takes, ``dimensionless`` where it has none.

    Raises
    ------
    KeyError
        If the field's name carries no unit suffix and is not listed as dimensionless, so a new
        field cannot enter the case schema without a unit.
    """
    leaf = path.rsplit(".", 1)[-1]
    for suffix in sorted(SUFFIX_UNITS, key=len, reverse=True):
        if leaf.endswith(suffix):
            return SUFFIX_UNITS[suffix]
    if path in DIMENSIONLESS:
        return _DIMENSIONLESS
    raise KeyError(
        f"{path!r} takes a number but its name has no unit suffix "
        f"({', '.join(sorted(SUFFIX_UNITS))}) and it is not listed as dimensionless"
    )


def _suffix_text(unit: str) -> str:
    for suffix, text in SUFFIX_UNITS.items():
        if text == unit:
            return f" (the suffix {suffix!r})"
    return ""


def _generic(parts: Sequence[str]) -> str:
    return ".".join(SEQUENCE_INDEX if part.isdigit() else part for part in parts)


def _numeric_leaf(parts: Sequence[str]) -> tuple[str, Literal["int", "float"], FieldType] | None:
    table = _numeric()
    path = _generic(parts)
    if path in table and not table[path][2]:
        kind, annotation, _ = table[path]
        return path, kind, annotation
    parent = _generic(parts[:-1])
    if parent in table and table[parent][2]:
        kind, annotation, _ = table[parent]
        return parent, kind, annotation
    return None


def _quantity(number: Number, unit: str) -> Quantity:
    registry = _registry()
    return registry.Quantity(number, registry.parse_units(unit))


def _check_unit(unit: str, where: str) -> None:
    try:
        _quantity(Fraction(1), unit).to_root_units()
    except Exception:  # pint raises several types, and AssertionError among them
        raise CaseValidationError(
            f"{where}: {unit!r} is not a unit the units library knows"
        ) from None


def _parse(text: str, where: str) -> ast.Expression:
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise CaseValidationError(
            f"{where}: an expression is at most {MAX_EXPRESSION_LENGTH} characters, "
            f"found {len(text)}"
        )
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        raise CaseValidationError(
            f"{where}: {text!r} is not an expression of numbers, variable names, + - * / **, "
            f"parentheses and {', '.join(FUNCTIONS)}"
        ) from None
    for node in ast.walk(tree):
        _admit(node, text, where)
    return tree


def _admit(node: ast.AST, text: str, where: str) -> None:  # noqa: C901
    def refuse(what: str) -> CaseValidationError:
        return CaseValidationError(
            f"{where}: {text!r}: {what} is not allowed; an expression holds numbers, variable "
            f"names, + - * / **, parentheses and {', '.join(FUNCTIONS)}"
        )

    if isinstance(node, ast.Expression | ast.Load):
        return
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise refuse(f"the constant {node.value!r}")
        if isinstance(node.value, float) and not math.isfinite(node.value):
            raise refuse("a non-finite number")
        return
    if isinstance(node, ast.Name):
        return
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _BINARY:
            raise refuse(f"the operator {type(node.op).__name__}")
        return
    if isinstance(node, ast.operator):
        return
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _UNARY):
            raise refuse(f"the operator {type(node.op).__name__}")
        return
    if isinstance(node, ast.unaryop):
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
            raise refuse("a call of anything but " + ", ".join(FUNCTIONS))
        if node.keywords or any(isinstance(arg, ast.Starred) for arg in node.args):
            raise refuse("a keyword or starred argument")
        return
    raise refuse(f"the {type(node).__name__} form")


def _names(tree: ast.Expression) -> frozenset[str]:
    callees = {id(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    return frozenset(
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and id(node) not in callees
    )


def _bits(number: Number) -> int:
    if isinstance(number, Fraction):
        return number.numerator.bit_length() + number.denominator.bit_length()
    return 0


def _carry(quantity: Quantity, where: str, text: str) -> Quantity:
    magnitude = quantity.magnitude
    if isinstance(magnitude, Fraction) and _bits(magnitude) > _EXACT_BITS:
        try:
            magnitude = float(magnitude)
        except OverflowError:
            raise CaseValidationError(f"{where}: {text!r} overflows") from None
        quantity = _quantity(magnitude, _DIMENSIONLESS) * quantity.units
    if isinstance(magnitude, float) and not math.isfinite(magnitude):
        raise CaseValidationError(f"{where}: {text!r} is not a finite number")
    return quantity


class _Evaluator:
    # Evaluates a vetted tree over variables held in SI base units; nothing is run as code.

    def __init__(
        self, env: Mapping[str, Quantity], units: Mapping[str, str], where: str, text: str
    ) -> None:
        self.env = env
        self.units = units
        self.where = where
        self.text = text

    def fail(self, reason: str) -> CaseValidationError:
        return CaseValidationError(f"{self.where}: {self.text!r}: {reason}")

    def unlike(self) -> CaseValidationError:
        return self.fail(f"adds or compares values of different dimensions{self.used()}")

    def used(self) -> str:
        used = sorted(
            name
            for name in self.units
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", self.text)
        )
        return (
            " (" + ", ".join(f"{name} is in {self.units[name]}" for name in used) + ")"
            if used
            else ""
        )

    def visit(self, node: ast.AST) -> Quantity:
        quantity = self._visit(node)
        return _carry(quantity, self.where, self.text)

    def _visit(self, node: ast.AST) -> Quantity:
        if isinstance(node, ast.Expression):
            return self._visit(node.body)
        if isinstance(node, ast.Constant):
            value = node.value
            assert isinstance(value, int | float)
            return _quantity(Fraction(repr(value)), _DIMENSIONLESS)
        if isinstance(node, ast.Name):
            if node.id not in self.env:
                known = ", ".join(sorted(self.env)) or "none"
                raise self.fail(f"{node.id!r} is not a variable of the case (it defines {known})")
            return self.env[node.id]
        if isinstance(node, ast.UnaryOp):
            operand = self.visit(node.operand)
            return -operand if isinstance(node.op, ast.USub) else operand
        if isinstance(node, ast.BinOp):
            return self._binary(node)
        if isinstance(node, ast.Call):
            return self._call(node)
        raise self.fail("is not an expression this evaluator reads")  # pragma: no cover

    def _binary(self, node: ast.BinOp) -> Quantity:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add | ast.Sub):
            if left.dimensionality != right.dimensionality:
                raise self.unlike()
            return left + right if isinstance(node.op, ast.Add) else left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right.magnitude == 0:
                raise self.fail("divides by zero")
            return left / right
        return self._power(left, right)

    def _dimensionless(self, quantity: Quantity, what: str) -> Number:
        if not quantity.dimensionless:
            raise self.fail(f"{what} must be dimensionless" + self.used())
        magnitude = quantity.to(_DIMENSIONLESS).magnitude
        assert isinstance(magnitude, Fraction | float)
        return magnitude

    def _power(self, base: Quantity, exponent: Quantity) -> Quantity:
        power = self._dimensionless(exponent, "an exponent")
        try:
            if (
                isinstance(power, Fraction)
                and power.denominator == 1
                and abs(power) <= _EXACT_POWER
            ):
                if base.magnitude == 0 and power < 0:
                    raise self.fail("divides by zero")
                return base ** int(power)
            as_float = float(power)
            raised = float(base.magnitude) ** as_float
        except OverflowError:
            raise self.fail("overflows") from None
        except ZeroDivisionError:
            raise self.fail("divides by zero") from None
        if isinstance(raised, complex):
            raise self.fail("takes a real power of a negative number")
        return _quantity(raised, _DIMENSIONLESS) * base.units**as_float

    def _call(self, node: ast.Call) -> Quantity:
        assert isinstance(node.func, ast.Name)
        name = node.func.id
        arguments = [self.visit(argument) for argument in node.args]
        arity = {"sqrt": 1, "exp": 1, "log": 1, "abs": 1}
        if name in arity and len(arguments) != arity[name]:
            raise self.fail(f"{name} takes {arity[name]} argument")
        if name in ("min", "max"):
            if not arguments:
                raise self.fail(f"{name} takes at least one argument")
            if any(item.dimensionality != arguments[0].dimensionality for item in arguments):
                raise self.fail(f"{name} compares values of different dimensions" + self.used())
            chosen = min if name == "min" else max
            return chosen(arguments, key=lambda item: item.magnitude)
        argument = arguments[0]
        if name == "abs":
            return abs(argument)
        if name == "sqrt":
            return self._power(argument, _quantity(0.5, _DIMENSIONLESS))
        magnitude = self._dimensionless(argument, f"the argument of {name}")
        try:
            number = float(magnitude)
        except OverflowError:
            # An exact number beyond the range of a float still has a finite logarithm.
            if name == "exp" or magnitude <= 0:
                raise self.fail(f"{name} of a number beyond the range of a float") from None
            assert isinstance(magnitude, Fraction)  # a float cannot overflow on conversion
            logarithm = math.log(magnitude.numerator) - math.log(magnitude.denominator)
            return _quantity(logarithm, _DIMENSIONLESS)
        try:
            result = math.exp(number) if name == "exp" else math.log(number)
        except (ValueError, OverflowError):
            raise self.fail(f"{name} of {number:g} is not a finite number") from None
        return _quantity(result, _DIMENSIONLESS)


def _definitions(raw: FieldValue, source: str) -> dict[str, Variable]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise CaseValidationError(
            f"{source}: variables: is a mapping of name to {{value: <number>, unit: <text>}} or "
            "{expression: <text>, unit: <text>}"
        )
    found: dict[str, Variable] = {}
    for name, body in raw.items():
        where = f"{source}: variables.{name}"
        if not isinstance(name, str) or not _NAME.match(name):
            raise CaseValidationError(
                f"{where}: a variable name is a letter, then letters, digits or underscores"
            )
        if name in FUNCTIONS or name == "auto":
            raise CaseValidationError(f"{where}: {name!r} is reserved and names no variable")
        if not isinstance(body, Mapping):
            raise CaseValidationError(
                f"{where}: is a mapping with value: or expression:, and unit:"
            )
        try:
            found[name] = Variable.model_validate(dict(body))
        except ValidationError as error:
            reasons = "; ".join(
                f"{'.'.join(str(part) for part in problem['loc']) or 'it'}: {problem['msg']}"
                for problem in error.errors()
            )
            raise CaseValidationError(f"{where}: {reasons}") from None
        _check_unit(found[name].unit, f"{where}.unit")
    return found


def _order(uses: Mapping[str, frozenset[str]], source: str) -> list[str]:
    order: list[str] = []
    state: dict[str, int] = {}

    def visit(name: str, trail: list[str]) -> None:
        if state.get(name) == 2:
            return
        if state.get(name) == 1:
            cycle = [*trail[trail.index(name) :], name]
            raise CaseValidationError(
                f"{source}: variables.{name}: variables refer to each other in a cycle: "
                + " -> ".join(cycle)
            )
        state[name] = 1
        for used in sorted(uses[name]):
            if used in uses:
                visit(used, [*trail, name])
        state[name] = 2
        order.append(name)

    for name in uses:
        visit(name, [])
    return order


def _variable_value(
    name: str,
    variable: Variable,
    tree: ast.Expression | None,
    env: dict[str, Quantity],
    units: Mapping[str, str],
    source: str,
) -> Quantity:
    where = f"{source}: variables.{name}"
    declared = _quantity(Fraction(1), variable.unit).dimensionality
    if tree is None:
        assert variable.value is not None
        return _quantity(Fraction(repr(variable.value)), variable.unit).to_root_units()
    assert variable.expression is not None
    evaluator = _Evaluator(env, units, where, variable.expression)
    result = evaluator.visit(tree)
    if result.dimensionality != declared:
        raise CaseValidationError(
            f"{where}: {variable.expression!r}{evaluator.used()} does not have the dimension "
            f"of its declared unit {variable.unit!r}"
        )
    return result.to_root_units()


def _back(quantity: Quantity, unit: str) -> float:
    magnitude = quantity.to(_registry().parse_units(unit)).magnitude
    return float(magnitude)


def resolve(raw: FieldValue, source: str) -> tuple[FieldValue, Resolution | None]:
    """Resolve the variables and expressions of a case mapping to numbers.

    Returns the mapping with ``variables:`` removed and every expression replaced by its number
    in the unit of the field it sits at, and what was found; ``(raw, None)`` for a case that
    defines no variable and writes no expression.

    Raises
    ------
    CaseValidationError
        If a variable or expression is malformed, refers to an unknown name or a cycle, or does not
        have the dimension of the field it sits at; the message starts with ``source``.
    """
    if not isinstance(raw, Mapping):
        return raw, None
    definitions = _definitions(raw.get("variables"), source)
    sites = list(_expression_sites(raw))
    if not definitions and not sites:
        if "variables" in raw:
            return {key: value for key, value in raw.items() if key != "variables"}, None
        return raw, None

    trees: dict[str, ast.Expression | None] = {}
    uses: dict[str, frozenset[str]] = {}
    for name, variable in definitions.items():
        where = f"{source}: variables.{name}"
        if variable.expression is None:
            trees[name], uses[name] = None, frozenset()
        else:
            tree = _parse(variable.expression, where)
            trees[name], uses[name] = tree, _names(tree)
    unknown = sorted({used for names in uses.values() for used in names} - set(definitions))
    if unknown:
        owner = next(name for name, names in uses.items() if unknown[0] in names)
        raise CaseValidationError(
            f"{source}: variables.{owner}: {unknown[0]!r} is not a variable of the case "
            f"(it defines {', '.join(definitions) or 'none'})"
        )

    env: dict[str, Quantity] = {}
    units = {name: variable.unit for name, variable in definitions.items()}
    for name in _order(uses, source):
        env[name] = _variable_value(name, definitions[name], trees[name], env, units, source)
    values = {name: _back(env[name], definitions[name].unit) for name in definitions}

    resolved = _copy(raw)
    resolved.pop("variables", None)
    expressions: dict[str, str] = {}
    field_uses: dict[str, frozenset[str]] = {}
    for dotted, parts, text in sites:
        leaf = _numeric_leaf(parts)
        assert leaf is not None
        generic, kind, _ = leaf
        where = f"{source}: {dotted}"
        tree = _parse(text, where)
        used = _names(tree)
        result = _Evaluator(env, units, where, text).visit(tree)
        unit = field_unit(generic)
        expected = _quantity(Fraction(1), unit).dimensionality
        if result.dimensionality != expected:
            raise CaseValidationError(
                f"{where}: {text!r}{_Evaluator(env, units, where, text).used()} does not have the "
                f"dimension this field takes: {unit}{_suffix_text(unit)}"
            )
        number = result.to(_registry().parse_units(unit)).magnitude
        _place(resolved, parts, _as_field(number, kind, where, text, unit))
        expressions[dotted] = text
        field_uses[dotted] = used
    return resolved, Resolution(
        definitions=definitions,
        values=values,
        expressions=expressions,
        uses={**uses, **field_uses},
    )


def _as_field(
    number: Number, kind: Literal["int", "float"], where: str, text: str, unit: str
) -> int | float:
    try:
        value = float(number)
    except OverflowError:
        raise CaseValidationError(f"{where}: {text!r} overflows") from None
    if not math.isfinite(value):
        raise CaseValidationError(f"{where}: {text!r} is not a finite number")
    if kind == "int":
        if value != int(value):
            raise CaseValidationError(
                f"{where}: {text!r} is {value:g}, and this field takes a whole number"
            )
        return int(value)
    return value


def expression_paths(raw: FieldValue) -> tuple[str, ...]:
    """Return the dotted path of every numeric field of a case mapping that holds an expression."""
    return tuple(dotted for dotted, _, _ in _expression_sites(raw))


def _expression_sites(
    node: FieldValue, parts: tuple[str, ...] = ()
) -> Iterator[tuple[str, tuple[str, ...], str]]:
    if parts and parts[0] == "variables":
        return
    if isinstance(node, Mapping):
        for key, item in node.items():
            yield from _expression_sites(item, (*parts, str(key)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _expression_sites(item, (*parts, str(index)))
    elif isinstance(node, str) and parts:
        leaf = _numeric_leaf(parts)
        if leaf is None or _plain_number(node):
            return
        _, _, annotation = leaf
        if node in (_literal_options(annotation) or ()):
            return
        yield ".".join(parts), parts, node


def _plain_number(text: str) -> bool:
    # A numeral in a string is the schema's to read, as it was before variables existed. `inf` and
    # `nan` convert too, but they are names a variable may take, so a numeral needs a digit.
    try:
        float(text)
    except ValueError:
        return False
    return any(character.isdigit() for character in text)


def _copy(node: FieldValue) -> FieldValue:
    if isinstance(node, Mapping):
        return {key: _copy(item) for key, item in node.items()}
    if isinstance(node, list):
        return [_copy(item) for item in node]
    return node


def _place(mapping: dict[str, Any], parts: Sequence[str], value: int | float) -> None:
    cursor: Any = mapping
    for part in parts[:-1]:
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    last = parts[-1]
    if isinstance(cursor, list):
        cursor[int(last)] = value
    else:
        cursor[last] = value

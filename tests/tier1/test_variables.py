"""FR-39 — a case's variables resolve to exact numbers, refuse other dimensions and run no code."""

from __future__ import annotations

import builtins
import copy
from pathlib import Path
from typing import Any

import pytest

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.io import variables
from nanopnp.io.artefact import CaseArtefact
from nanopnp.io.case import CaseValidationError, FieldValue, dumps_case
from nanopnp.io.variables import field_unit, numeric_paths, resolve
from nanopnp.sweep.document import load_sweep
from nanopnp.sweep.plan import SweepPlanError, build_plan

SOURCE = "<test>"


def _case(variables_block: dict[str, Any], **leaves: FieldValue) -> dict[str, Any]:
    """Build a bare mapping with `variables:` and the given leaves; resolve reads no schema."""
    case: dict[str, Any] = {"variables": variables_block}
    for dotted, value in leaves.items():
        cursor = case
        *parents, last = dotted.split("__")
        for part in parents:
            cursor = cursor.setdefault(part, {})
        cursor[last] = value
    return case


def _radius(expression: str, **definitions: dict[str, Any]) -> FieldValue:
    case = _case(definitions, geometry__pore__radius_nm=expression)
    resolved, _ = resolve(case, SOURCE)
    return resolved["geometry"]["pore"]["radius_nm"]


def test_fr39_an_expression_off_the_whitelist_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """A formula that could run code, or read an attribute, is refused rather than evaluated."""
    a = {"a": {"value": 2, "unit": "nm"}}
    forbidden = [
        "a.real",
        "a[0]",
        "__import__('os')",
        "f(a)",
        "sqrt(a, base=2)",
        "lambda: 1",
        "a if a else a",
        "a < 2",
        "a and a",
        "'2'",
        "True",
        "[a]",
        "max(*a)",
        "b",
        "x" * 257,
    ]
    for text in forbidden:
        with pytest.raises(CaseValidationError, match=r"geometry\.pore\.radius_nm"):
            _radius(text, **a)

    cycle = {"p": {"expression": "q", "unit": "nm"}, "q": {"expression": "p", "unit": "nm"}}
    with pytest.raises(CaseValidationError, match="cycle"):
        resolve(_case(cycle), SOURCE)

    def boom(*_: object, **__: object) -> None:
        raise AssertionError("code was run")

    real_compile = builtins.compile

    def compile_syntax_only(*args: FieldValue, **kwargs: FieldValue) -> FieldValue:
        # ast.parse compiles to a tree only; a code object is what runs.
        flags = args[3] if len(args) > 3 else kwargs.get("flags", 0)
        if not flags & 0x400:  # ast.PyCF_ONLY_AST
            boom()
        return real_compile(*args, **kwargs)

    monkeypatch.setattr(builtins, "eval", boom)
    monkeypatch.setattr(builtins, "exec", boom)
    monkeypatch.setattr(builtins, "compile", compile_syntax_only)
    assert _radius("sqrt(a*a) + abs(-a) - min(a, 3*a) + 0*max(a, a)", **a) == pytest.approx(2.0)


def test_fr39_a_variable_of_another_dimension_is_refused_at_the_field() -> None:
    """A length where a voltage belongs is a wrong run, so the field refuses it by name."""
    length = {"a": {"value": 2, "unit": "nm"}}
    voltage = {"V": {"value": 50, "unit": "mV"}}

    def bias(expression: str, **definitions: dict[str, Any]) -> None:
        resolve(_case(definitions, boundary_conditions__bias_V=expression), SOURCE)

    for text in ("a", "2*a"):
        with pytest.raises(CaseValidationError, match=r"boundary_conditions\.bias_V.*volt"):
            bias(text, **length)
    with pytest.raises(CaseValidationError, match="different dimensions"):
        bias("a + V", **length, **voltage)
    with pytest.raises(CaseValidationError, match="dimensionless"):
        _radius("exp(a)", **length)
    declared = {"a": {"expression": "2*b", "unit": "volt"}, "b": {"value": 1, "unit": "nm"}}
    with pytest.raises(CaseValidationError, match="declared unit"):
        resolve(_case(declared), SOURCE)
    with pytest.raises(CaseValidationError, match="whole number"):
        resolve(
            _case(
                {"n": {"value": 2.5, "unit": "dimensionless"}},
                structure__ensemble__frames__count="n",
            ),
            SOURCE,
        )
    with pytest.raises(CaseValidationError, match="florb"):
        resolve(_case({"n": {"value": 1, "unit": "florb"}}), SOURCE)


def test_fr39_a_conversion_of_the_same_dimension_is_exact() -> None:
    """20 Å must be exactly 2.0 nm: a last-digit difference would key a different cache entry."""
    cases: list[tuple[str, dict[str, Any], str, float]] = [
        ("geometry__pore__radius_nm", {"value": 20, "unit": "angstrom"}, "a", 2.0),
        ("geometry__pore__radius_nm", {"value": 3.5, "unit": "angstrom"}, "a", 0.35),
        ("geometry__pore__radius_nm", {"value": 0.3, "unit": "Å"}, "a", 0.03),
        ("boundary_conditions__bias_V", {"value": 50, "unit": "mV"}, "a", 0.05),
        ("electrolyte__concentration_M", {"value": 100, "unit": "mM"}, "a", 0.1),
        ("electrolyte__temperature_K", {"value": 25, "unit": "degC"}, "a", 298.15),
        ("geometry__pore__radius_nm", {"value": 2, "unit": "nm"}, "2*a", 4.0),
    ]
    for leaf, definition, expression, expected in cases:
        resolved, found = resolve(_case({"a": definition}, **{leaf: expression}), SOURCE)
        cursor = resolved
        for part in leaf.split("__"):
            cursor = cursor[part]
        assert cursor == expected, (leaf, definition)
        assert found is not None and found.expressions == {leaf.replace("__", "."): expression}
    assert "variables" not in resolved


def test_fr39_every_numeric_field_has_a_unit_or_is_dimensionless() -> None:
    """A field added with no unit suffix must fail here, not accept a number of any dimension."""
    paths = numeric_paths()
    assert "geometry.pore.radius_nm" in paths and "physics.solid_permittivities" in paths
    assert "numerics.mesh.wall_h_nm" in paths
    for path in paths:
        field_unit(path)
    assert field_unit("boundary_conditions.wall_charge_C_m2") == "coulomb / meter ** 2"
    with pytest.raises(KeyError, match="width_um"):
        field_unit("geometry.pore.width_um")
    assert variables.field_unit("numerics.nonlinear.rtol") == "dimensionless"


def test_fr39_a_literal_at_a_numeric_field_stays_a_literal() -> None:
    """`wall_h_nm: auto` is the schema's word; reading it as a variable would refuse every case."""
    case = _case({"a": {"value": 1, "unit": "nm"}}, numerics__mesh__wall_h_nm="auto")
    resolved, _ = resolve(copy.deepcopy(case), SOURCE)
    assert resolved["numerics"]["mesh"]["wall_h_nm"] == "auto"


def test_fr39_a_case_without_variables_is_returned_as_given() -> None:
    """The common case must not copy, change or record anything."""
    raw: dict[str, Any] = {"geometry": {"pore": {"radius_nm": 2.0}}}
    same, found = resolve(raw, SOURCE)
    assert same is raw and found is None


QUICKSTART = (
    Path(__file__).resolve().parents[2] / "examples" / "01-quickstart" / "quickstart.case.yaml"
)


def _with_variable(text: str) -> str:
    """Write the quick-start's pore radius as `2*a`, with `a` = 1 nm."""
    return text.replace("radius_nm: 2}", "radius_nm: 2*a}").replace(
        "name: quickstart\n", "name: quickstart\n\nvariables:\n  a: {value: 1, unit: nm}\n"
    )


def test_fr39_variables_key_by_the_values_they_resolve_to(tmp_path: Path) -> None:
    """`2*a` with a = 1 nm must share every cache key with the case that says `2`."""
    text = QUICKSTART.read_text(encoding="utf-8")
    plain, written = Case.loads(text), Case.loads(_with_variable(text))
    assert written == plain
    assert CaseArtefact(written).hash == CaseArtefact(plain).hash
    first = Session(tmp_path / "plain", write=False).run(plain, upto="mesh")
    second = Session(tmp_path / "written", write=False).run(written, upto="mesh")
    assert {name: a.hash for name, a in second.artefacts.items()} == {
        name: a.hash for name, a in first.artefacts.items()
    }
    assert set(second.artefacts) == {"case", "region", "mesh"}
    assert "variables:" in second.manifest.case_text and "2*a" in second.manifest.case_text
    recorded = second.manifest.inputs["variables"]
    assert recorded["fields"] == {"geometry.pore.radius_nm": {"expression": "2*a", "value": 2.0}}
    assert recorded["definitions"]["a"]["value"] == 1.0


def test_ver62_a_case_without_variables_writes_what_it_did(tmp_path: Path) -> None:
    """A case with no variables must not gain a `variables` key in its text or its manifest."""
    case = Case.loads(QUICKSTART.read_text(encoding="utf-8"))
    assert case.variables_record is None
    assert "variables" not in dumps_case(case)
    run = Session(tmp_path / "store", write=False).run(case, upto="mesh")
    assert "variables" not in run.manifest.inputs
    assert "variables" not in run.manifest.case_text


def test_fr39_an_edit_of_a_variable_moves_the_fields_that_use_it() -> None:
    """A variable edited must re-resolve its fields; a field set whole must drop its formula."""
    case = Case.loads(_with_variable(QUICKSTART.read_text(encoding="utf-8")))
    moved = case.with_(**{"variables.a": 1.25})
    assert moved.geometry is not None and moved.geometry.pore is not None
    assert moved.geometry.pore.radius_nm == 2.5
    converted = case.with_(**{"variables.a": {"value": 5, "unit": "angstrom"}})
    assert converted.geometry is not None and converted.geometry.pore is not None
    assert converted.geometry.pore.radius_nm == 1.0
    kept = case.with_(bias_V=0.1)
    assert kept.expressions == {"geometry.pore.radius_nm": "2*a"}
    dropped = case.with_(**{"geometry.pore.radius_nm": 1.5})
    assert dropped.expressions == {}
    assert "2*a" not in dropped.dumps()
    again = Case.loads(moved.dumps())
    assert again == moved and again.expressions == moved.expressions


def test_fr39_a_sweep_over_a_variable_moves_every_field_that_uses_it(tmp_path: Path) -> None:
    """An axis on `variables.a` must move each field written with `a`, and sever the warm start."""
    text = (
        QUICKSTART.read_text(encoding="utf-8")
        .replace("radius_nm: 2}", "radius_nm: a}")
        .replace("thickness_nm: 6}", "thickness_nm: 3*a}")
        .replace(
            "name: quickstart\n", "name: quickstart\n\nvariables:\n  a: {value: 1, unit: nm}\n"
        )
    )
    (tmp_path / "base.case.yaml").write_text(text, encoding="utf-8")
    sweep = (
        "schema: nanopnp/sweep/v0.5\nname: radii\nbase: base.case.yaml\n"
        "axes:\n  - {name: a, path: variables.a, values: [1.5, 2]}\n"
    )
    source = tmp_path / "radii.sweep.yaml"
    source.write_text(sweep, encoding="utf-8")
    plan = build_plan(load_sweep(source), source=source, check_meshes=False)
    base = plan.base_case()
    members = [plan.case(index, base=base) for index in range(len(plan.points))]
    sizes = [
        (member.geometry.pore.radius_nm, member.geometry.membrane.thickness_nm)  # type: ignore[union-attr]
        for member in members
        if member.geometry is not None
    ]
    assert sizes == [(1.5, 4.5), (2.0, 6.0)]
    assert [point.parent for point in plan.points] == [None, None]
    assert [point.wave for point in plan.points] == [0, 0]
    assert len(plan.warnings) == 1 and "geometry.pore.radius_nm" in plan.warnings[0]
    unknown = tmp_path / "unknown.sweep.yaml"
    unknown.write_text(sweep.replace("variables.a", "variables.b"), encoding="utf-8")
    with pytest.raises(SweepPlanError, match=r"variables\.b"):
        build_plan(load_sweep(unknown), source=unknown, check_meshes=False)

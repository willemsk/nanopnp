"""VER-70: no gate comparison passes a NaN."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "nanopnp"

EXEMPT = {
    "structure/axis.py:measure_axis: n < 2",
    "mesh/adapter.py:_insert_physical_names: start < 0",
    "mesh/adapter.py:_validate: index.size and (int(index.min()) < 0 or int(index.max()) >= limit)",
    "structure/read.py:select: counts[chain] < COVERAGE_FRACTION * most",
    "structure/read.py:select_frames: count > len(window)",
    "sweep/collect.py:_rectification: plus_V is None or minus_V is None or plus_V <= 0.0 or "
    "(plus_V + minus_V != 0.0)",
}

SYNTHETIC = """\
import math

import numpy as np


class GateViolationError(RuntimeError):
    pass


def bare(value, tol):
    if value > tol:
        raise GateViolationError("x")


def negated(value, tol):
    if not value <= tol:
        raise GateViolationError("x")


def guarded(value, tol):
    if not math.isfinite(value) or value > tol:
        raise GateViolationError("x")


def either(a, b, tol):
    if a > tol or not b <= tol:
        raise GateViolationError("x")


def vector(x, tol):
    if np.any(np.abs(x) > tol):
        raise GateViolationError("x")


def counted(items):
    if len(items) < 2:
        raise GateViolationError("x")


def collected(value, tol, failures):
    if value < tol:
        failures.append(GateViolationError("x"))


def other(value, tol):
    if value > tol:
        raise ValueError("x")


def exempted(value, tol):
    if value >= tol:
        raise GateViolationError("x")


def closure(value, tol):
    def inner(x):
        if x > tol:
            raise GateViolationError("x")

    inner(value)


class Holder:
    class Inner:
        def method(self, value, tol):
            if value < tol:
                raise GateViolationError("x")
"""


def test_ver70_the_gate_classes_are_the_exit_tables_class_four() -> None:
    from nanopnp.validation.modularity import gate_classes

    names = gate_classes((PACKAGE / "core" / "errors.py").read_text(encoding="utf-8"))
    assert len(names) == 39
    for name in (
        "GateViolationError",
        "MeshQualityError",
        "WallSizeGateError",
        "ContourGateError",
        "RegionGateError",
        "ChargeFieldError",
        "IndicatorError",
        "ExtensionError",
        "SymmetryGateError",
        "Val06Error",
    ):
        assert name in names, name
    assert "NewtonDivergenceError" not in names  # class 5
    assert "CaseValidationError" not in names  # class 3


def test_ver70_a_nan_permissive_gate_is_found_at_its_line(tmp_path: Path) -> None:
    from nanopnp.validation.modularity import nan_permissive_gates

    package = tmp_path / "pkg"
    (package / "gui").mkdir(parents=True)
    (package / "gates.py").write_text(SYNTHETIC, encoding="utf-8")
    (package / "gui" / "view.py").write_text(
        "def shown(value, tol):\n    if value > tol:\n        raise GateViolationError('x')\n",
        encoding="utf-8",
    )
    exempt = {
        "gates.py:exempted: value >= tol": "the oracle's exemption",
        "gates.py:gone: value > tol": "names a test no longer in the source",
    }
    found = nan_permissive_gates(package, gates=frozenset({"GateViolationError"}), exempt=exempt)
    assert [(gate.path, gate.function, gate.test) for gate in found.violations] == [
        ("gates.py", "bare", "value > tol"),
        ("gates.py", "either", "a > tol or not b <= tol"),
        ("gates.py", "vector", "np.any(np.abs(x) > tol)"),
        ("gates.py", "collected", "value < tol"),
        ("gates.py", "inner", "x > tol"),
        ("gates.py", "method", "value < tol"),
    ]
    lines = SYNTHETIC.splitlines()
    for gate in found.violations:
        assert lines[gate.line - 1].strip() == f"if {gate.test}:"
        assert str(gate) == (
            f"src/nanopnp/gates.py:{gate.line}: {gate.function}: if {gate.test} (VER-70)"
        )
    assert found.stale == ("gates.py:gone: value > tol",)
    namespace: dict[str, object] = {}
    exec(SYNTHETIC, namespace)
    namespace["bare"](math.nan, 1.0)  # type: ignore[operator]
    with pytest.raises(namespace["GateViolationError"]):  # type: ignore[arg-type]
        namespace["negated"](math.nan, 1.0)  # type: ignore[operator]


def test_ver70_no_gate_comparison_in_the_package_passes_a_nan() -> None:
    from nanopnp.validation.modularity import NAN_EXEMPT, gate_classes, nan_permissive_gates

    gates = gate_classes((PACKAGE / "core" / "errors.py").read_text(encoding="utf-8"))
    found = nan_permissive_gates(PACKAGE, gates=gates, exempt=NAN_EXEMPT)
    assert not found.violations, "\n".join(str(gate) for gate in found.violations)
    assert not found.stale
    assert set(NAN_EXEMPT) == EXEMPT
    assert all(reason.strip() for reason in NAN_EXEMPT.values())


def test_ver70_stale_exemption_for_missing_file_is_reported() -> None:
    from nanopnp.validation.modularity import gate_classes, nan_permissive_gates

    gates = gate_classes((PACKAGE / "core" / "errors.py").read_text(encoding="utf-8"))
    exempt = {"nonexistent/module.py:func: x > 0": "test reason"}
    findings = nan_permissive_gates(PACKAGE, gates=gates, exempt=exempt)
    assert "nonexistent/module.py:func: x > 0" in findings.stale


@pytest.mark.parametrize(
    ("field", "criterion"),
    [("mean_ratio", "mean wall segment length"), ("max_ratio", "longest wall segment")],
)
def test_ver70_a_nan_wall_ratio_fails_the_wall_size_gate(field: str, criterion: str) -> None:
    from nanopnp.mesh.generate import WallSizeGateError, WallStatistics, check_wall_size

    values: dict[str, object] = {
        "target_nm": 0.1,
        "count": 10,
        "mean_ratio": 1.0,
        "p95_ratio": 1.0,
        "max_ratio": 1.0,
        "longest": 0,
        "longest_midpoint_nm": (1.0, 0.0),
    }
    values[field] = math.nan
    with pytest.raises(WallSizeGateError, match=criterion):
        check_wall_size(WallStatistics(**values))  # type: ignore[arg-type]


# QR-12
def test_ver70_a_nan_indicator_fails_the_indicator_gate() -> None:
    import ngsolve as ngs

    from nanopnp.mesh.primitives import CylindricalPoreGeometry
    from nanopnp.post.indicator import IndicatorError, check_indicator

    mesh = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0, wall_h_nm=1.0)
    indicator = ngs.GridFunction(ngs.H1(mesh, order=1))
    indicator.vec[:] = math.nan
    with pytest.raises(IndicatorError):
        check_indicator(indicator, mesh)

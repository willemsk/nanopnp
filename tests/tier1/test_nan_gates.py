"""VER-70 (WP42 D1, D2) — no gate comparison passes a NaN.

Every ordering comparison with a NaN is false, so a gate written
``if value > tol: raise`` is skipped by a NaN and the run carries the NaN on: the
plausible wrong answer QR-12 forbids (REV-11). The house form is the negation,
``if not value <= tol: raise``, which a NaN fails. The check reads the source and
imports no checked module; the gate classes are the class-4 entries of the
exit-code table in ``core/errors.py``.
"""

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
"""WP42 D2's six exempt tests: integer operands, or a ``!=`` term a NaN satisfies."""

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
"""


def test_ver70_the_gate_classes_are_the_exit_tables_class_four() -> None:
    """The gates are read from the exit-code table, never listed a second time."""
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
    """Each NaN-permissive form is found, naming file, line and function; the safe forms pass.

    A comparison under ``not``, a test that also asks ``isfinite``, an
    integer-only comparison, a raise of a class that is not a gate, the desktop
    shell and an exempt test are not found; a gate collected into a list is.
    """
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
    ]
    lines = SYNTHETIC.splitlines()
    for gate in found.violations:
        assert lines[gate.line - 1].strip() == f"if {gate.test}:"
        assert str(gate) == (
            f"src/nanopnp/gates.py:{gate.line}: {gate.function}: if {gate.test} (VER-70)"
        )
    assert found.stale == ("gates.py:gone: value > tol",)


def test_ver70_no_gate_comparison_in_the_package_passes_a_nan() -> None:
    """The tree has no NaN-permissive gate, and the exemptions are D2's six, each with a reason."""
    from nanopnp.validation.modularity import NAN_EXEMPT, gate_classes, nan_permissive_gates

    gates = gate_classes((PACKAGE / "core" / "errors.py").read_text(encoding="utf-8"))
    found = nan_permissive_gates(PACKAGE, gates=gates, exempt=NAN_EXEMPT)
    assert not found.violations, "\n".join(str(gate) for gate in found.violations)
    assert not found.stale
    assert set(NAN_EXEMPT) == EXEMPT
    assert all(reason.strip() for reason in NAN_EXEMPT.values())


@pytest.mark.parametrize(
    ("field", "criterion"),
    [("mean_ratio", "mean wall segment length"), ("max_ratio", "longest wall segment")],
)
def test_ver70_a_nan_wall_ratio_fails_the_wall_size_gate(field: str, criterion: str) -> None:
    """``check_wall_size`` passed a NaN ratio before D2; it now aborts naming the criterion."""
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


def test_ver70_a_nan_indicator_fails_the_indicator_gate() -> None:
    """``check_indicator`` passed an all-NaN ``psi`` before D2; it now aborts (QR-12)."""
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

"""VER-43 and VER-44: the form binds the whole schema and the panels bind their models (CON-13)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nanopnp.gui.case_model import CaseEditor

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")
os.environ.pop("DISPLAY", None)
os.environ.pop("WAYLAND_DISPLAY", None)

try:
    from PySide6 import QtWidgets

    from nanopnp.gui.app import MainWindow
    from nanopnp.gui.widgets import ChargeWidget
except (ImportError, OSError) as error:  # pragma: no cover - platform dependent
    pytest.skip(f"PySide6 cannot be constructed here: {error}", allow_module_level=True)

CASE = """
schema: nanopnp/case/v0.5
name: widget-probe
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns, solid_permittivities: {membrane: 3.2}}
numerics: {continuation: default_ladder, stabilisation: none}
"""


@pytest.fixture(scope="module")
def application() -> QtWidgets.QApplication:
    existing = QtWidgets.QApplication.instance()
    if isinstance(existing, QtWidgets.QApplication):
        return existing
    return QtWidgets.QApplication([])


@pytest.fixture
def editor(tmp_path: Path) -> CaseEditor:
    path = tmp_path / "case.yaml"
    path.write_text(CASE, encoding="utf-8")
    return CaseEditor.open(path)


# QR-11
def test_if09_the_window_assembles_its_seven_panels(
    application: QtWidgets.QApplication, editor: CaseEditor
) -> None:
    window = MainWindow(editor)
    tabs = window.centralWidget()
    assert isinstance(tabs, QtWidgets.QTabWidget)
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Case",
        "Geometry",
        "Charge",
        "Run",
        "Convergence",
        "Result",
        "Fields",
    ]
    assert window.windowTitle().endswith("case.yaml")

    charge = tabs.widget(2)
    assert isinstance(charge, ChargeWidget)
    assert charge.control is tabs.widget(1).control
    assert not charge.build_button.isEnabled()
    assert charge.reason()

    run = tabs.widget(3)
    model = run.refresh()
    assert model.state == "idle"
    assert model.fraction == 0.0

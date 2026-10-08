"""QR-03 (WP41 D2) — the conservation gate measures the charge the solve assembles.

Before WP41 the gate integrated a supplied field at order 8 and the coupled Poisson
source assembled it at NGSolve's estimate, order 3. On a 0.5 nm alternating field
the deployed mesh resolves, the gate passed at 2e-5 while the solve carried a charge
1.2e-2 off (WP41 *Design* §1). A supplied field now carries one explicit rule, and
the source term and every leg of its gate are evaluated by it.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry

REPOSITORY = Path(__file__).resolve().parents[2]
RING = REPOSITORY / "examples" / "02-charged-pore" / "ring.field.yaml"
MODELS = REPOSITORY / "src" / "nanopnp" / "physics" / "models.py"
PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)


@pytest.mark.parametrize("quantity", ["areal_charge_density", "volume_charge_density"])
def test_qr03_the_gate_measures_the_charge_the_solve_assembles(quantity: str) -> None:
    """The source term, applied to ``v = 1``, is the gate's ``Q_mesh`` to round-off.

    Both quantities: a volume density is an interpolant too, and its gate stood at
    order 5 against the same order-3 source.
    """
    import ngsolve as ngs

    from nanopnp.charge.fields import FIELD_QUADRATURE_ORDER, ChargeField, load_field
    from nanopnp.numerics.measures import AXISYMMETRIC
    from nanopnp.physics.poisson import charge_source

    ring = load_field(RING)
    units = "C/m^2" if quantity == "areal_charge_density" else "C/m^3"
    field = ChargeField(
        document=ring.document.model_copy(update={"quantity": quantity, "units": units}),
        grid=ring.grid,
        source=ring.source,
    )
    assert field.quadrature_order == FIELD_QUADRATURE_ORDER == 8

    mesh = PORE.generate(maxh_nm=1.0, wall_h_nm=0.35)
    space = ngs.H1(mesh, order=AXISYMMETRIC.element_order)
    source = ngs.LinearForm(space)
    source += charge_source(
        field.volume_density_C_m3(),
        space.TestFunction(),
        AXISYMMETRIC,
        rule_order=field.quadrature_order,
    )
    source.Assemble()
    one = ngs.GridFunction(space)
    one.Set(1.0)
    assembled_C = 2.0 * math.pi * 1e-27 * ngs.InnerProduct(source.vec, one.vec)

    assert assembled_C == pytest.approx(field.mesh_integral_C(mesh, AXISYMMETRIC), rel=1e-12)
    refined = (
        2.0
        * math.pi
        * 1e-27
        * ngs.Integrate(field.volume_density_C_m3() * ngs.x, mesh, order=FIELD_QUADRATURE_ORDER + 3)
    )
    assert field.mesh_integral_C(mesh, AXISYMMETRIC, refined=True) == pytest.approx(
        refined, rel=1e-12
    )


def test_qr03_every_fixed_charge_source_carries_the_charge_s_rule() -> None:
    """Each model's ``charge_source(fixed_charge, ...)`` passes ``rule_order``.

    On the quadrature request, as VER-41 asserts the stabilisation's, because the
    number it moves is a few parts in 10^5 and no walk's tolerance would see a
    model that dropped the keyword.
    """
    tree = ast.parse(MODELS.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "charge_source"
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "fixed_charge"
    ]
    assert len(calls) >= 2, "the coupled models and poisson each assemble a fixed charge"
    for call in calls:
        keywords = {keyword.arg for keyword in call.keywords}
        assert "rule_order" in keywords, f"physics/models.py:{call.lineno} omits rule_order"


def test_qr03_an_explicit_rule_below_num07_s_floor_is_refused() -> None:
    """``rule_order`` replaces the bonus logic, so it carries NUM-07's floor itself."""
    import ngsolve as ngs

    from nanopnp.numerics.measures import AXISYMMETRIC

    mesh = PORE.generate(maxh_nm=4.0)
    test = ngs.H1(mesh, order=2).TestFunction()
    with pytest.raises(ValueError, match="NUM-07"):
        AXISYMMETRIC.volume(test, rule_order=2)
    with pytest.raises(ValueError, match="NUM-07"):
        AXISYMMETRIC.integrate(ngs.CoefficientFunction(1.0), mesh, rule_order=2)
    with pytest.raises(ValueError, match="rule_order"):
        AXISYMMETRIC.volume(test, rule_order=8, singular=True)
    with pytest.raises(ValueError, match="rule_order"):
        AXISYMMETRIC.volume(test, rule_order=8, extra_order=1)


def test_qr03_a_deposited_charge_keeps_the_model_s_default_rule() -> None:
    """A deposit's total is exact at the default order; its rule is Phase 6's (D13, E4)."""
    from nanopnp.charge.deposit import DepositedCharge
    from nanopnp.charge.fields import FIELD_QUADRATURE_ORDER, ChargeField

    assert ChargeField.quadrature_order == FIELD_QUADRATURE_ORDER
    assert DepositedCharge.quadrature_order is None

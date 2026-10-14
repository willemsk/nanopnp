"""QR-03 (WP41 D2) — the conservation gate measures the charge the solve assembles."""

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


# VER-41
def test_qr03_every_fixed_charge_source_carries_the_charge_s_rule() -> None:
    tree = ast.parse(MODELS.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "charge_source"
        and node.args
        and isinstance(node.args[0], ast.Attribute)
        and isinstance(node.args[0].value, ast.Name)
        and node.args[0].value.id == "fixed_charge"
    ]
    assert len(calls) >= 2, "the coupled models and poisson each assemble a fixed charge"
    for call in calls:
        keywords = {keyword.arg for keyword in call.keywords}
        assert "rule_order" in keywords, f"physics/models.py:{call.lineno} omits rule_order"


def test_qr03_an_explicit_rule_below_num07_s_floor_is_refused() -> None:
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
    with pytest.raises(ValueError, match="rule_order"):
        AXISYMMETRIC.integrate(ngs.CoefficientFunction(1.0), mesh, rule_order=8, singular=True)
    with pytest.raises(ValueError, match="rule_order"):
        AXISYMMETRIC.integrate(ngs.CoefficientFunction(1.0), mesh, rule_order=8, extra_order=1)


def test_qr03_default_ladder_threads_the_charge_s_rule_onto_every_charged_rung() -> None:
    import ngsolve as ngs

    from nanopnp.numerics.measures import FixedCharge
    from nanopnp.solve.continuation import default_ladder

    mesh = PORE.generate(maxh_nm=4.0)
    for rule in (8, None):
        rungs = default_ladder(
            mesh, fixed_charge_field=FixedCharge(ngs.CF(1.0), rule), charge_steps=1
        )
        charged = [r for r in rungs if "fixed_charge" in r.solve_kwargs]
        assert charged
        for rung in charged:
            assert isinstance(rung.solve_kwargs["fixed_charge"], FixedCharge)
            assert rung.solve_kwargs["fixed_charge"].rule_order == rule
        assert not any("fixed_charge_rule_order" in r.solve_kwargs for r in rungs)


def test_qr03_a_supplied_and_a_deposited_charge_each_name_their_rule() -> None:
    import ngsolve as ngs

    from nanopnp.charge.deposit import DepositedCharge
    from nanopnp.charge.fields import FIELD_QUADRATURE_ORDER, ChargeField, load_field
    from nanopnp.materials.electrolyte import Electrolyte
    from nanopnp.numerics.measures import FixedCharge
    from nanopnp.physics import models

    ring = load_field(RING)
    supplied = ChargeField(document=ring.document, grid=ring.grid, source=ring.source)
    assert supplied.fixed_charge_C_m3().rule_order == FIELD_QUADRATURE_ORDER
    scales = models.create(
        "poisson", electrolyte=Electrolyte.from_parameter_file("willems2020_nacl")
    ).scales
    assert supplied.assemble(scales).rule_order == FIELD_QUADRATURE_ORDER

    mesh = PORE.generate(maxh_nm=4.0)
    deposited = DepositedCharge(deposit=object(), field=ngs.CF(2.0))  # type: ignore[arg-type]
    assert deposited.fixed_charge_C_m3() == FixedCharge(deposited.field, None)
    scaled = deposited.assemble(scales)
    assert scaled.rule_order is None
    assert scaled.density(mesh(1.0, 1.0)) == pytest.approx(2.0 / scales.charge_density_C_m3)


def test_qr03_a_bare_density_is_refused_by_the_model_that_takes_a_fixed_charge() -> None:
    import ngsolve as ngs

    from nanopnp.materials.electrolyte import Electrolyte
    from nanopnp.numerics.measures import AXISYMMETRIC
    from nanopnp.physics import models

    mesh = PORE.generate(maxh_nm=4.0)
    model = models.create(
        "poisson", electrolyte=Electrolyte.from_parameter_file("willems2020_nacl")
    )
    space = ngs.H1(mesh, order=AXISYMMETRIC.element_order)
    with pytest.raises(TypeError, match="FixedCharge"):
        model.residual_form(space, AXISYMMETRIC, fixed_charge=ngs.CF(1.0))


def test_qr03_a_deposited_charge_keeps_the_model_s_default_rule() -> None:
    from nanopnp.charge.deposit import DepositedCharge
    from nanopnp.charge.fields import FIELD_QUADRATURE_ORDER, ChargeField

    assert ChargeField.quadrature_order == FIELD_QUADRATURE_ORDER
    assert DepositedCharge.quadrature_order is None


def test_qr03_an_explicit_rule_holds_on_a_one_dimensional_mesh() -> None:
    import ngsolve as ngs
    from ngsolve.meshes import Make1DMesh

    from nanopnp.numerics.measures import PLANAR

    mesh = Make1DMesh(2)
    test = ngs.H1(mesh, order=1).TestFunction()
    integrand = ngs.x**9
    form = ngs.LinearForm(PLANAR.volume(integrand * test, rule_order=9)).Assemble()
    gate = PLANAR.integrate(integrand, mesh, rule_order=9)
    assert sum(form.vec) == pytest.approx(gate, rel=1.0e-12)
    assert gate == pytest.approx(0.1, rel=1.0e-12)

"""NUM-07: what one more quadrature order for the ``r`` weight moves (WP34 D7, D8).

NGSolve estimates an integrand's order from its trial and test functions and does
not count the coordinate, so a non-singular ``r``-weighted form is integrated one
order short of its degree (NUM-07 NOTE on the ``r`` weight). ``poisson`` pays the
extra order; the coupled models do not, and whether they should is Phase 4's
decision (section 8.2.5 E4). This module measures it and gates nothing:

- (a) localises the effect to the quadrature, against an exact solution: VER-18's
  manufactured problem on its three levels, at ``weight_extra_order`` 0 and 1.
  If +1 lowers the error at fixed ``h`` but leaves the rate, the effect is a
  consistency constant, as the NOTE predicts.
- (b) sizes it on the case VAL-16 will judge: example 05's frozen ClyA case,
  0.5 M at +50 mV, solved at 0 and at 1. The current, ``G``, ``t+`` and the
  electro-osmotic rate, and the relative ``r``-weighted L2 change of every field.

Each assertion only pins that the seam is inert at 0: (a) reproduces VER-18's
criteria there, and (b)'s case keeps the frozen case's identity. The numbers are
logged and recorded in the NUM-07 NOTE and ``.knowledge/06-numerics-fem.md``
section 2.2.

Stabilisation is ``none`` throughout (NUM-11).
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest
from test_mms import BOUNDARIES, LENGTH_NM, MESH_SIZES_NM, RADIUS_NM, _model

from nanopnp.io.case import load_case, resolve
from nanopnp.physics.measures import AXISYMMETRIC, Measures

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.slow

REPOSITORY = Path(__file__).resolve().parents[2]
EXAMPLE_05 = REPOSITORY / "examples" / "05-clya-reference"
FROZEN_CASE = REPOSITORY / "docs" / "validation" / "cases" / "clya-0.5M-plus50mV.case.yaml"

WEIGHT_ORDERS = (0, 1)
"""The default, and the one extra order ``poisson`` already takes."""

PATCHED_MODULES = ("nanopnp.solve.stage", "nanopnp.solve.state", "nanopnp.post.stage")
"""Every module that builds the production measure on the solve and restore path.

The solve assembles at it, the restore reassembles the residual the NUM-25
reaction flux is read from, and stage 11 integrates at it; all three must agree,
or the current would be the flux of an operator nobody solved.
"""


def test_num07_weight_extra_order_zero_is_the_production_measure() -> None:
    """The seam's default is the measure every key and constant was recorded at."""
    assert Measures() == Measures(symmetry="axisymmetric", element_order=2)
    assert AXISYMMETRIC.weight_extra_order == 0


# -- (a) the manufactured solution ------------------------------------------------


def test_num07_mms_errors_at_each_weight_order() -> None:
    """VER-18's MMS at ``weight_extra_order`` 0 and 1: L2 errors and observed rates."""
    from nanopnp.mesh.primitives import CylinderGeometry
    from nanopnp.physics.models import POTENTIAL, VELOCITY
    from nanopnp.validation.mms import (
        ManufacturedSolution,
        convergence_rates,
        weighted_l2_error,
    )

    model = _model()
    manufactured = ManufacturedSolution.polynomial(model)
    exact = manufactured.coefficient_functions()
    meshes = [
        CylinderGeometry(radius_nm=RADIUS_NM, length_nm=LENGTH_NM).generate(maxh_nm=maxh_nm)
        for maxh_nm in MESH_SIZES_NM
    ]
    errors: dict[int, dict[str, list[float]]] = {}
    for weight in WEIGHT_ORDERS:
        measures = replace(AXISYMMETRIC, weight_extra_order=weight)
        sources = manufactured.source_functions(measures)
        errors[weight] = {name: [] for name in exact}
        for mesh in meshes:
            solution = model.solve(
                mesh,
                measures,
                boundaries=BOUNDARIES,
                potential_values=exact[POTENTIAL],
                concentration_values={s: exact[f"c_{s}"] for s in model.species},
                velocity_values=exact[VELOCITY],
                sources=sources,
            )
            for name, reference in exact.items():
                # The norm is evaluated at the production measure for both, so
                # only the assembled forms differ between the two columns.
                errors[weight][name].append(
                    weighted_l2_error(
                        solution.component(name), reference, mesh, AXISYMMETRIC, what=name
                    )
                )
    for name in exact:
        for weight in WEIGHT_ORDERS:
            values = errors[weight][name]
            logger.info(
                "NUM-07 MMS %s weight +%d: L2 %s, rates %s",
                name,
                weight,
                " ".join(f"{value:.6e}" for value in values),
                " ".join(f"{rate:.4f}" for rate in convergence_rates(values, MESH_SIZES_NM)),
            )
        ratios = [one / zero for zero, one in zip(errors[0][name], errors[1][name], strict=True)]
        logger.info(
            "NUM-07 MMS %s error ratio (+1 / 0) per level: %s",
            name,
            " ".join(f"{ratio:.6f}" for ratio in ratios),
        )

    # At 0 the seam is inert: VER-18's own criteria hold (test_mms.py).
    quadratic = [POTENTIAL, VELOCITY] + [f"c_{species}" for species in model.species]
    for name in quadratic:
        rates = convergence_rates(errors[0][name], MESH_SIZES_NM)
        assert min(rates) > 2.8, f"{name}: rates {rates} at weight 0"
        assert errors[0][name][-1] < 1e-4, f"{name}: finest error {errors[0][name][-1]:.3g}"


# -- (b) example 05's frozen case -------------------------------------------------


@contextmanager
def _weight_order(monkeypatch: pytest.MonkeyPatch, weight: int) -> Iterator[None]:
    """Solve, restore and post-process at ``weight_extra_order = weight``."""
    import importlib

    measure = replace(AXISYMMETRIC, weight_extra_order=weight)
    with monkeypatch.context() as patch:
        for module in PATCHED_MODULES:
            patch.setattr(importlib.import_module(module), "AXISYMMETRIC", measure)
        yield


def _scalar_changes(
    zero: Mapping[str, object], one: Mapping[str, object]
) -> dict[str, tuple[object, object]]:
    """Return each logged quantity at 0 and 1, by name."""
    names = ("current_A", "conductance_S", "transport_number", "eof_m3_s")
    return {name: (zero.get(name), one.get(name)) for name in names}


def test_num07_example_05_at_each_weight_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Example 05's frozen case at 0 and +1: I, G, t+, Q_EOF and every field's L2 change.

    Two stores, one per order. ``weight_extra_order`` is deliberately in no key
    (D7), so a shared store would hand the second solve the first's artefact and
    report a change of exactly zero.
    """
    import ngsolve as ngs

    from nanopnp.cli import main
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store
    from nanopnp.solve.state import restore, warm_start_payload
    from nanopnp.validation.comsol import case_identity
    from nanopnp.validation.mms import weighted_l2_error

    work = tmp_path / "example-05"
    work.mkdir()
    case = work / "clya-0.5M-plus50mV.case.yaml"
    shutil.copyfile(EXAMPLE_05 / case.name, case)
    assert main(["mesh", "reference", "--out", str(work / "clya-reference.msh")]) == 0
    # The case is the frozen one, which is what the seam must leave alone.
    assert case_identity(resolve(load_case(case))) == case_identity(resolve(load_case(FROZEN_CASE)))

    monkeypatch.chdir(work)
    results = {}
    solutions = {}
    for weight in WEIGHT_ORDERS:
        with _weight_order(monkeypatch, weight):
            result = run_case(
                case,
                store=Store(work / f"store-{weight}"),
                workspace=work / f"work-{weight}",
                write=False,
            )
            solutions[weight] = restore(
                warm_start_payload(result.artefacts["solve"]),
                case=load_case(case),
                mesh_artefact=result.artefacts.get("mesh"),
            )
        results[weight] = result
        logger.info("NUM-07 example 05 weight +%d: %s", weight, dict(result.quantities))

    # Two keys alike: the seam is in no key, which is why each order had its own store.
    assert results[0].artefacts["solve"].hash == results[1].artefacts["solve"].hash

    for name, (zero, one) in _scalar_changes(results[0].quantities, results[1].quantities).items():
        if isinstance(zero, float) and isinstance(one, float) and zero != 0.0:
            logger.info(
                "NUM-07 example 05 %s: %.9e -> %.9e, relative change %.3e",
                name,
                zero,
                one,
                (one - zero) / abs(zero),
            )
        else:
            logger.info("NUM-07 example 05 %s: %s -> %s", name, zero, one)

    # Each field's relative r-weighted L2 change, with the +1 state carried onto
    # the 0 state's space: the two meshes are one file, so the dofs coincide.
    base = solutions[0]
    carried = ngs.GridFunction(base.space)
    assert len(carried.vec) == len(solutions[1].state.vec)
    carried.vec.data = solutions[1].state.vec
    moved = replace(base, state=carried)
    mesh = base.space.mesh
    for name in (field.name for field in base.model.fields):
        change = weighted_l2_error(
            moved.component(name), base.component(name), mesh, AXISYMMETRIC, what=name
        )
        logger.info("NUM-07 example 05 field %s: relative L2 change %.3e", name, change)

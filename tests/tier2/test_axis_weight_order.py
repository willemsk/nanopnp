"""NUM-07: what one extra quadrature order for the ``r`` weight moves in the coupled models.

The NUM-07 NOTE on the ``r`` weight records that NGSolve does not count the
coordinate when it estimates an integrand's order, so every non-singular
axisymmetric term is integrated one order short of its degree in ``r``.
``poisson`` adds the order; the coupled models do not, and whether they should is
decided in Phase 6 with VAL-16 and VAL-17 (section 8.2.5 E4, section 8.2.6 F1).
WP34 measures it (D7, D8) through
:attr:`~nanopnp.numerics.measures.Measures.weight_extra_order`, a seam no case
key reaches, and records the numbers in the NOTE and ``.knowledge/06`` section 2.2.

Two legs, both ``slow``, logged and never gated:

(a) VER-18's coupled manufactured solution on its three levels at 0 and +1. The
    exact solution localises the effect to the quadrature: if +1 lowers the error
    at fixed ``h`` but not the rate, it is a consistency constant.
(b) Example 05's frozen case, 0.5 M at +50 mV on the reference mesh, solved at 0
    and +1: the current, the conductance, the transport number and the in-pore
    averages of VAL-17's list that a biased solve carries. Each variant solves in
    its own store, because the seam is not in any key and a shared store would
    hand the second solve the first one's state.

The only assertions are that at 0 each leg reproduces what its own gated test
asserts: VER-18's rates, and example 05's route agreement.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import logging
import math
import shutil
from collections.abc import Iterator, Mapping
from dataclasses import replace
from pathlib import Path

import ngsolve as ngs
import numpy as np
import pytest
from test_mms import BOUNDARIES, LENGTH_NM, MESH_SIZES_NM, RADIUS_NM, _model

from nanopnp.cli import main
from nanopnp.core.constants import AVOGADRO
from nanopnp.geometry.profile import load_profile
from nanopnp.io.store import Store
from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
)
from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.models import ModelSolution
from nanopnp.pipeline.run import run_case
from nanopnp.post.qoi import ROUTE_AGREEMENT_TOLERANCE
from nanopnp.solve import state as solve_state
from nanopnp.validation.examples import copy_example
from nanopnp.validation.mms import ManufacturedSolution, convergence_rates, weighted_l2_error
from nanopnp.validation.runs import reopen

pytestmark = pytest.mark.slow

logger = logging.getLogger(__name__)

REPOSITORY = Path(__file__).resolve().parents[2]
CASE_NAME = "clya-0.5M-plus50mV.case.yaml"

ORDERS = (0, 1)
"""The two values of ``weight_extra_order`` compared: the shipped default and +1."""

PORE_Z_NM = (-1.85, 12.25)
"""The pore's axial extent, the definition of "the pore" for every pore average
(``.knowledge/04`` section 2; ``.knowledge/09`` C, ``is_inside_pore``)."""

SURFACE_LAYER_NM = 0.5
"""``is_inside_pore_surface`` is ``wdf.wd <= 0.5 nm`` (``.knowledge/09`` C)."""

STAGE_MODULES = (
    "nanopnp.solve.stage",
    "nanopnp.solve.state",
    "nanopnp.solve.continuation",
    "nanopnp.post.stage",
    "nanopnp.charge.stage",
)
"""Every module that binds the shared ``AXISYMMETRIC``.

Rebinding the name in each is how the in-process run takes the seam without a
case key, model option or flag reaching it (D7). It reaches only a lookup made
at run time, such as each stage's ``replace(AXISYMMETRIC, ...)``: a default
argument was bound at import, so ``nanopnp.solve.continuation``, whose binding
is only the defaults of ``Rung.measures`` and ``default_ladder``, is unaffected,
and the stages hand the ladder their measures explicitly. The fixture refuses a
module that no longer binds the shared instance.
"""


# -- (a) the manufactured solution ------------------------------------------------


def _mms_errors(measures: Measures) -> dict[str, list[float]]:
    """Return VER-18's L2 errors on its three levels, assembled with ``measures``."""
    model = _model()
    manufactured = ManufacturedSolution.polynomial(model)
    exact = manufactured.coefficient_functions()
    sources = manufactured.source_functions(measures)
    errors: dict[str, list[float]] = {name: [] for name in exact}
    for maxh_nm in MESH_SIZES_NM:
        mesh = CylinderGeometry(radius_nm=RADIUS_NM, length_nm=LENGTH_NM).generate(maxh_nm=maxh_nm)
        solution = model.solve(
            mesh,
            measures,
            boundaries=BOUNDARIES,
            potential_values=exact[POTENTIAL],
            concentration_values={species: exact[f"c_{species}"] for species in model.species},
            velocity_values=exact[VELOCITY],
            sources=sources,
        )
        for name, reference in exact.items():
            # The error norm itself is an integral, at NUM-07's floor, and is
            # measured identically for both variants.
            errors[name].append(
                weighted_l2_error(
                    solution.component(name), reference, mesh, AXISYMMETRIC, what=name
                )
            )
    return errors


def test_num07_weight_order_on_the_coupled_manufactured_solution() -> None:
    """D8 (a): L2 errors and rates at 0 and +1; at 0, VER-18's rates are reproduced."""
    errors = {extra: _mms_errors(Measures(weight_extra_order=extra)) for extra in ORDERS}
    for name in errors[0]:
        rates = {extra: convergence_rates(errors[extra][name], MESH_SIZES_NM) for extra in ORDERS}
        logger.info(
            "NUM-07 MMS %s: maxh %s nm; L2 at 0 %s rates %s; at +1 %s rates %s; ratio %s",
            name,
            MESH_SIZES_NM,
            [f"{e:.4e}" for e in errors[0][name]],
            [f"{r:.3f}" for r in rates[0]],
            [f"{e:.4e}" for e in errors[1][name]],
            [f"{r:.3f}" for r in rates[1]],
            [f"{b / a:.4f}" for a, b in zip(errors[0][name], errors[1][name], strict=True)],
        )
    quadratic = [POTENTIAL, VELOCITY] + [f"c_{species}" for species in _model().species]
    for name in quadratic:
        assert min(convergence_rates(errors[0][name], MESH_SIZES_NM)) > 2.8, name
    assert min(convergence_rates(errors[0][PRESSURE], MESH_SIZES_NM)) > 1.8


# -- (b) example 05 --------------------------------------------------------------


@pytest.fixture
def weight_order(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Rebind every stage module's ``AXISYMMETRIC`` to carry ``weight_extra_order = 1``."""
    raised = replace(AXISYMMETRIC, weight_extra_order=1)
    for name in STAGE_MODULES:
        module = importlib.import_module(name)
        assert module.AXISYMMETRIC is AXISYMMETRIC, f"{name} no longer binds AXISYMMETRIC"
        monkeypatch.setattr(module, "AXISYMMETRIC", raised)
    yield


def _inner_wall_nm() -> tuple[np.ndarray, np.ndarray]:
    """Return the lumen's radius ``r_p(z)``: the smallest crossing of the pore profile at each z."""
    profile = np.asarray(load_profile("clya_reference_profile").vertices, dtype=float)
    edges = np.stack([profile, np.roll(profile, -1, axis=0)], axis=1)
    z_samples = np.linspace(PORE_Z_NM[0], PORE_Z_NM[1], 2_841)
    radius = np.full_like(z_samples, np.nan)
    for k, z in enumerate(z_samples):
        crossings = []
        for (r0, z0), (r1, z1) in edges:
            if (z0 - z) * (z1 - z) <= 0.0 and z0 != z1:
                crossings.append(r0 + (z - z0) * (r1 - r0) / (z1 - z0))
        if crossings:
            radius[k] = min(crossings)
    return z_samples, radius


def _pore_indicator(mesh: ngs.Mesh) -> ngs.GridFunction:
    """Return the element-wise indicator of the lumen between ``PORE_Z_NM``.

    An element of the electrolyte counts when its centroid lies inside the
    lumen. It is a discretisation of the region, the same one for both variants
    on the one mesh, so it moves neither side of the comparison.
    """
    z_wall, r_wall = _inner_wall_nm()
    space = ngs.L2(mesh, order=0)
    indicator = ngs.GridFunction(space)
    values = indicator.vec.FV().NumPy()
    for element in mesh.Elements(ngs.VOL):
        if element.mat != "electrolyte":
            continue
        points = np.array([mesh[v].point for v in element.vertices])
        r, z = points.mean(axis=0)
        if PORE_Z_NM[0] <= z <= PORE_Z_NM[1]:
            wall = np.interp(z, z_wall, r_wall, left=np.nan, right=np.nan)
            if math.isfinite(wall) and r < wall:
                values[space.GetDofNrs(element)[0]] = 1.0
    return indicator


def _in_pore(directory: Path, store: Store) -> dict[str, float]:
    """Return the in-pore averages of one finished run (VAL-17's list, at bias)."""
    run = reopen(directory, store=store)
    solution = run.solution
    scales = run.scales
    mesh = solution.space.mesh
    inside = _pore_indicator(mesh)
    weight = inside * ngs.x
    order = 6

    def integral(integrand: ngs.CoefficientFunction) -> float:
        return float(ngs.Integrate(integrand * weight, mesh, order=order))

    volume = integral(ngs.CoefficientFunction(1.0))
    averages: dict[str, float] = {"pore_volume_nm3": 2.0 * math.pi * volume}
    charge = ngs.CoefficientFunction(0.0)
    for ion in solution.model.electrolyte.species:  # type: ignore[attr-defined]
        c = solution.concentration(ion.name)
        averages[f"c_{ion.name}_M"] = integral(c) / volume * scales.concentration_M
        charge = charge + ion.valence * c
    surface = ngs.IfPos(SURFACE_LAYER_NM - solution.wall_distance_nm, 1.0, 0.0)
    # e per nm^3 of dimensionless charge density: c0 [mol/m^3] N_A 1e-27 m^3/nm^3.
    to_e = scales.concentration_mol_m3 * AVOGADRO * 1e-27 * 2.0 * math.pi
    averages["mobile_charge_e"] = integral(charge) * to_e
    averages["mobile_charge_surface_e"] = integral(charge * surface) * to_e
    averages["mobile_charge_bulk_e"] = integral(charge * (1.0 - surface)) * to_e
    averages["phi_mean_V"] = integral(solution.potential) / volume * scales.potential_V
    return averages


def _numbers(quantities: Mapping[str, object], prefix: str = "") -> dict[str, float]:
    """Flatten a run's quantities to their finite scalar leaves."""
    flat: dict[str, float] = {}
    for key, value in quantities.items():
        name = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(_numbers(value, f"{name}."))
        elif (
            isinstance(value, int | float)
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        ):
            flat[name] = float(value)
    return flat


def _solve_example_05(root: Path, mesh: Path) -> tuple[dict[str, float], dict[str, float], Path]:
    """Run example 05 in its own copy and store.

    Returns its quantities, its in-pore averages and the copy's directory. The
    case names its mesh relative to the working directory, as the README runs
    it, so the run is made from the copy.
    """
    example = copy_example(
        REPOSITORY / "examples" / "05-clya-reference", root, repository=REPOSITORY
    )
    shutil.copyfile(mesh, example / mesh.name)
    store = Store(example / "store")
    with contextlib.chdir(example):
        result = run_case(Path(CASE_NAME), store=store)
        return _numbers(result.quantities), _in_pore(result.directory, store), example


def _restored(example: Path, extra: int) -> ModelSolution:
    """Restore the run in ``example`` with its residual assembled at ``weight_extra_order``."""
    run = next(path.parent for path in (example / "store").rglob("run.json"))
    held = solve_state.AXISYMMETRIC
    solve_state.AXISYMMETRIC = replace(AXISYMMETRIC, weight_extra_order=extra)
    try:
        with contextlib.chdir(example):
            return reopen(run, store=Store(example / "store")).solution
    finally:
        solve_state.AXISYMMETRIC = held


def _cross_residuals(examples: Mapping[int, Path]) -> dict[tuple[int, int], float]:
    """Return ``|R_form(state)|`` over the free dofs, for each variant's form on each state.

    The third route the comparison needs: integrated quantities that barely move
    are what a seam that never reached the solve would also give. Each state must
    be a root of its own form and not of the other's.
    """
    states = {k: _restored(examples[k], 0).state.vec.FV().NumPy().copy() for k in ORDERS}
    norms: dict[tuple[int, int], float] = {}
    for form_extra in ORDERS:
        solution = _restored(examples[0], form_extra)
        free = np.array(list(solution.space.FreeDofs()), dtype=bool)
        vector = solution.state.vec
        out = vector.CreateVector()
        for state_extra in ORDERS:
            vector.FV().NumPy()[:] = states[state_extra]
            solution.residual.Apply(vector, out)
            norms[(form_extra, state_extra)] = float(np.linalg.norm(out.FV().NumPy()[free]))
    relative = np.linalg.norm(states[1] - states[0]) / np.linalg.norm(states[0])
    logger.info(
        "NUM-07 example 05: states differ by %.3e relative; |R| form 0 on 0 %.3e, on 1 %.3e; "
        "form +1 on 0 %.3e, on 1 %.3e",
        relative,
        norms[(0, 0)],
        norms[(0, 1)],
        norms[(1, 0)],
        norms[(1, 1)],
    )
    return norms


def test_num07_weight_order_on_example_05(tmp_path: Path, request: pytest.FixtureRequest) -> None:
    """D8 (b): example 05's quantities and in-pore averages at 0 and +1, logged."""
    # The README's own mesh command, once; both variants solve on its bytes.
    mesh = tmp_path / "clya-reference.msh"
    # The CLI configures logging with force=True, which is right for a command and
    # removes pytest's capture handler here; put it back, or this test logs nothing.
    root_logger = logging.getLogger()
    handlers, level = list(root_logger.handlers), root_logger.level
    try:
        assert main(["mesh", "reference", "--out", str(mesh)]) == 0
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        for handler in handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(level)
    results: dict[int, tuple[dict[str, float], dict[str, float]]] = {}
    examples: dict[int, Path] = {}
    for extra in ORDERS:
        root = tmp_path / f"extra-{extra}"
        root.mkdir()
        if extra:
            request.getfixturevalue("weight_order")
        quantities, in_pore, examples[extra] = _solve_example_05(root, mesh)
        results[extra] = (quantities, in_pore)
    base_q, base_p = results[0]
    raised_q, raised_p = results[1]
    norms = _cross_residuals(examples)
    record = tmp_path / "num07-example-05.json"
    record.write_text(
        json.dumps(
            {
                **{str(k): v for k, v in results.items()},
                "residuals": {f"form {f} on state {k}": n for (f, k), n in norms.items()},
            },
            indent=1,
        ),
        "utf-8",
    )
    logger.info("NUM-07 example 05: every number is in %s", record)
    for label, base, raised in (("quantity", base_q, raised_q), ("in-pore", base_p, raised_p)):
        for key in sorted(base.keys() & raised.keys()):
            a, b = base[key], raised[key]
            relative = (b - a) / abs(a) if a else math.nan
            logger.info(
                "NUM-07 example 05 %s %s: at 0 %.6e, at +1 %.6e, change %.3e (relative %.3e)",
                label,
                key,
                a,
                b,
                b - a,
                relative,
            )
    assert base_q["route_agreement.relative_difference"] < ROUTE_AGREEMENT_TOLERANCE
    # The seam reached the solve: each state is a root of its own form, not the other's.
    for extra in ORDERS:
        other = 1 - extra
        assert norms[(extra, extra)] < 1e-3 * norms[(extra, other)], norms

"""VER-42: the reference-matching stabilised mode, measured rather than assumed.

Four claims, each with its own failure mode, and none of them is "the mode runs".

1. **It is consistent enough.** The streamline term of NUM-14 is built on the
   *approximate* residual — every second derivative of a trial field dropped — so
   it is inconsistent by construction and the manufactured-solution rate of VER-18
   falls from 3 to 2. That is a prediction about a number, so the number is
   measured, reported, and gated only from below. Gating it from above would be
   asserting that an *improvement* is a failure.

2. **The manufactured source reaches ``R~_i``.** Leaving ``s~_i`` out of the
   stabilisation residual is the single easiest mistake in
   :mod:`nanopnp.physics.stabilisation`, and its signature is a rate below 2 —
   which is exactly what a reader who expected 2 would shrug at. So the mistake is
   made deliberately, with the source withheld, and the resulting rate is asserted
   to be visibly worse than the rate with it.

3. **It fixes what it exists to fix.** On a mesh coarse enough that ``Pe_K`` runs
   to 4.7 in the double layer, plain Galerkin drives the counter-ion to
   ``c = -72.9`` and the NUM-17 positivity gate stops the run; the stabilised mode
   climbs the same ladder to convergence. That is the failure Chaudhry, Comer,
   Aksimentiev & Olson (*Commun. Comput. Phys.* **15**, 93, 2014) report and §6.4.1
   cites, reproduced here rather than trusted.

4. **It changes nothing it should not.** The crosswind term is zero wherever
   ``C_cw Pe_K <= 1``, which is everywhere on a mesh meeting NUM-30, and the two
   modes' currents converge to each other at ``O(h^2)`` under wall refinement.
   Both are measured: the first on the assembled term, the second as a rate.

Record the stabilisation mode with every number — every figure below names the mode
and the mesh it came from, and the module constants carry the measured values.
"""

from __future__ import annotations

import itertools
import logging
import math
from dataclasses import replace

import pytest

from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry
from nanopnp.physics import stabilisation as stabilisation_module
from nanopnp.physics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.models import (
    POTENTIAL,
    VELOCITY,
    CoupledBoundaries,
    CoupledModel,
    ModelSolution,
    concentration_field_name,
)
from nanopnp.post import qoi
from nanopnp.solve.continuation import LadderResult, default_ladder, run_ladder
from nanopnp.solve.gates import GateViolationError
from nanopnp.validation.mms import (
    ManufacturedSolution,
    convergence_rates,
    weighted_l2_error,
)

logger = logging.getLogger(__name__)


# -- 1 and 2: the manufactured solution ----------------------------------------


MMS_MEASURES = Measures(symmetry="axisymmetric", element_order=2)
MMS_RADIUS_NM, MMS_LENGTH_NM = 2.0, 4.0
MMS_SIZES_NM = (0.4, 0.2, 0.1)
"""VER-18's own refinement sequence, unchanged.

Reused deliberately: the claim is that *this* mode loses an order on the problem
VER-18 already characterises, and a different sequence would leave the comparison
resting on two measurements that were never made on the same meshes.
"""

MMS_FLOW_SIZES_NM = (0.4, 0.2)
"""The two coarsest levels, for the ``reference`` measurement below.

``reference`` costs 126 s and 436 s at these two levels against ``supg``'s 7 s and
25 s, because the flow pair takes Newton from 5 iterations to 31 (both measured
below). A third level would cost the better part of an hour for a number that is
recorded rather than gated, so the sequence stops here and the test is ``slow``.
"""

MMS_BOUNDARIES = CoupledBoundaries(
    potential="wall|end",
    concentration="wall|end",
    velocity="wall|end",
    velocity_axis="axis",
)
"""VER-18's boundary set, so the pressure needs the mean constraint (NUM-06)."""

STABILISED_RATE_FLOOR = 1.8
"""``2 - 0.2``, the margin ``tests/tier2/test_mms.py`` already allows on its 3.

Not a new tolerance: the *number* being gated changes from 3 to 2 because the
streamline term is inconsistent, and the margin around it is the one VER-18
carries. Gated from below only — a mode that converged faster than predicted
would be a finding, not a failure.
"""

MMS_GATED_MODE = "supg"
"""The mode whose MMS rate is gated: the streamline term, on its own.

NUM-14's prediction — the rate falls from 3 to 2 because the approximate residual
drops every second derivative — is a statement about the *transport* stabilisation,
and ``supg`` is that term in isolation. ``reference`` adds the flow GLS and grad-div
pair, whose own approximate residual costs a further order on a Taylor-Hood pair
(measured below), so a rate measured there would be the flow pair's rate wearing
the transport term's name. An analytic test that localises the error to a single
term beats a whole-model comparison that localises nothing, and on this mesh
sequence ``max Pe_K <= 0.084``, so the crosswind is identically zero and ``supg``
and ``reference`` differ by the flow pair alone. **[tested]**
"""


def _mms_model(mode: str) -> CoupledModel:
    """Return VER-18's model in one stabilisation mode.

    Identical to ``tests/tier2/test_mms.py``'s except for the mode: every
    correction resolves to ``none``, which is the constant-coefficient scope the
    manufactured sources assume, and the steric flux stays on because ``beta_i``
    is a differential operator rather than a coefficient.
    """
    electrolyte = Electrolyte.from_parameter_file(
        switches=replace(CorrectionSwitches.classical(), steric=True)
    )
    return CoupledModel(
        electrolyte=electrolyte,
        concentration_M=0.1,
        name="mms",
        fluid="electrolyte",
        pressure_constraint=True,
        stabilisation=mode,
    )


def _mms_errors(
    mode: str,
    *,
    withhold_source: bool = False,
    sizes: tuple[float, ...] = MMS_SIZES_NM,
) -> dict[str, list[float]]:
    """Solve the manufactured problem at every level and return the L2 errors.

    Parameters
    ----------
    mode
        The stabilisation mode.
    withhold_source
        If true, ``s~_i`` is kept out of ``R~_i`` while the *forms* still carry it,
        which is the wiring mistake NUM-14's NOTE warns about. Patched at the one
        seam both the streamline residual and the crosswind viscosity read it
        through, so neither can be left consistent by accident.
    sizes
        The refinement sequence, coarsest first.
    """
    model = _mms_model(mode)
    manufactured = ManufacturedSolution.polynomial(model)
    exact = manufactured.coefficient_functions()
    sources = manufactured.source_functions(MMS_MEASURES)

    intact = stabilisation_module.approximate_residual

    def without_source(state: object, *, source: object = None) -> object:
        del source
        return intact(state, source=None)  # type: ignore[arg-type]

    if withhold_source:
        stabilisation_module.approximate_residual = without_source  # type: ignore[assignment]
    try:
        errors: dict[str, list[float]] = {name: [] for name in exact}
        for maxh_nm in sizes:
            mesh = CylinderGeometry(radius_nm=MMS_RADIUS_NM, length_nm=MMS_LENGTH_NM).generate(
                maxh_nm=maxh_nm
            )
            solution = model.solve(
                mesh,
                MMS_MEASURES,
                boundaries=MMS_BOUNDARIES,
                potential_values=exact[POTENTIAL],
                concentration_values={
                    species: exact[concentration_field_name(species)] for species in model.species
                },
                velocity_values=exact[VELOCITY],
                sources=sources,
            )
            for name, reference in exact.items():
                errors[name].append(
                    weighted_l2_error(
                        solution.component(name), reference, mesh, MMS_MEASURES, what=name
                    )
                )
    finally:
        stabilisation_module.approximate_residual = intact  # type: ignore[assignment]
    return errors


def _report_rates(
    label: str,
    errors: dict[str, list[float]],
    sizes: tuple[float, ...] = MMS_SIZES_NM,
) -> dict[str, list[float]]:
    """Log every field's errors and rates, and return the rates by field."""
    rates: dict[str, list[float]] = {}
    for name, values in errors.items():
        rates[name] = convergence_rates(values, sizes)
        logger.info(
            "%s: %s errors %s, rates %s (maxh %s nm)",
            label,
            name,
            " ".join(f"{value:.4e}" for value in values),
            " ".join(f"{rate:.3f}" for rate in rates[name]),
            ", ".join(str(size) for size in sizes),
        )
    return rates


def _transport_fields(model: CoupledModel) -> list[str]:
    """Return the field names the stabilisation's transport term touches."""
    return [concentration_field_name(species) for species in model.species]


@pytest.fixture(scope="module")
def streamline_errors() -> dict[str, list[float]]:
    """Return the ``supg`` mode's MMS errors at the three VER-18 levels."""
    return _mms_errors(MMS_GATED_MODE)


@pytest.fixture(scope="module")
def streamline_rates(streamline_errors: dict[str, list[float]]) -> dict[str, list[float]]:
    """Return the ``supg`` mode's MMS rates at the three VER-18 levels."""
    return _report_rates(MMS_GATED_MODE, streamline_errors)


@pytest.fixture(scope="module")
def unstabilised_errors() -> dict[str, list[float]]:
    """Return the ``none`` mode's MMS errors on the same meshes, as the control."""
    return _mms_errors("none")


@pytest.fixture(scope="module")
def unstabilised_rates(unstabilised_errors: dict[str, list[float]]) -> dict[str, list[float]]:
    """Return the ``none`` mode's MMS rates on the same meshes, as the control."""
    return _report_rates("none", unstabilised_errors)


def test_ver42_the_stabilised_mode_loses_an_order_and_no_more(
    streamline_rates: dict[str, list[float]],
) -> None:
    """The concentration rate is measured, reported, and gated only from below.

    NUM-14's NOTE predicts 2 rather than VER-18's 3, because the streamline term
    is built on a residual with every second derivative dropped. Measured
    **2.012 and 2.040** on ``maxh`` 0.4/0.2/0.1 nm in ``supg``, against ``none``'s
    3 on the same meshes, in 152 s. The floor is :data:`STABILISED_RATE_FLOOR`;
    there is no ceiling, because a mode that converged faster than the prediction
    would be worth knowing about and is not a defect.

    Gated in :data:`MMS_GATED_MODE` rather than in ``reference`` for the reason
    that constant records (NUM-14, VER-18, VER-42). **[tested]**
    """
    for name in _transport_fields(_mms_model(MMS_GATED_MODE)):
        rates = streamline_rates[name]
        assert min(rates) > STABILISED_RATE_FLOOR, (
            f"{name}: observed rates {rates} fall below the {STABILISED_RATE_FLOOR} floor, "
            "which is one order short of VER-18's own rate; a rate this low usually means "
            "the manufactured source never reached R~_i"
        )


def test_ver42_the_unstabilised_mode_on_the_same_meshes_still_gives_ver18s_rate(
    unstabilised_rates: dict[str, list[float]],
) -> None:
    """``none`` is unchanged by this work package, asserted on the same sequence.

    VER-18 already asserts this, on its own model built without a ``stabilisation``
    argument at all. The point of repeating it here is that it is the *control* for
    the test above: the two rates are then measured by one helper on one mesh
    sequence, so "the stabilised mode loses an order" is a comparison rather than
    two numbers from two files (PHY-22, VER-18).
    """
    for name in _transport_fields(_mms_model("none")):
        rates = unstabilised_rates[name]
        assert min(rates) > 2.8, f"{name}: observed rates {rates} fall short of P2"


WITHHELD_FOOTPRINT_FACTOR = 5.0
"""How far the term's footprint has to collapse when ``s~_i`` is withheld.

Footprint is ``error(mode)/error(none) - 1`` on the same mesh: how far the
stabilised error sits above the unstabilised one. Intact it is 4.83 and 15.97 for
``Na+`` and 2.99 and 15.77 for ``Cl-`` on ``maxh`` 0.4/0.2 nm; with the source
withheld, 0.065, 0.666, 0.014 and 0.198 — ratios of **24 to 213**. The factor is a
floor with five times that headroom, not a fitted threshold. **[tested]**
"""


def test_ver42_withholding_the_manufactured_source_switches_the_term_off(
    streamline_errors: dict[str, list[float]],
    unstabilised_errors: dict[str, list[float]],
) -> None:
    """The easiest mistake in the module, made on purpose so it cannot pass silently.

    ``R~_i = b~_i . grad(c~_i) - s~_i``, and on the exact solution the two sides
    balance the diffusion that was dropped: ``b~_i . grad(c~_i) - s~_i =
    div(D~ grad(c~_i))``. That is what makes the intact residual ``O(1)`` and the
    term inconsistent.

    Withhold ``s~_i`` and the plan predicted a *worse* rate. It is the opposite
    here, and the measurement is the reason this test is not a comment: this
    manufactured problem is diffusion-dominated — ``max Pe_K <= 0.084`` — so
    ``s~_i`` is the dominant part of ``R~_i`` and dropping it does not corrupt the
    residual, it very nearly **erases** it. The rate then rises from 2.012 towards
    ``none``'s 2.907, and :data:`STABILISED_RATE_FLOOR` has no ceiling, so the
    wiring mistake would sail through the test above wearing the face of a mode
    that beat its own prediction.

    So the assertion is on the footprint rather than on the rate: intact, the term
    puts the error a factor of 3 to 17 above ``none`` on the same mesh; with the
    source withheld it is within 7 %, 1.4 % and 20 % of ``none``. The signature of
    the mistake is a term that has switched itself off, and that is what is gated
    (NUM-14, VER-42). **[tested]**
    """
    damaged = _mms_errors(MMS_GATED_MODE, withhold_source=True, sizes=MMS_FLOW_SIZES_NM)
    _report_rates(f"{MMS_GATED_MODE}, source withheld", damaged, MMS_FLOW_SIZES_NM)

    for name in _transport_fields(_mms_model(MMS_GATED_MODE)):
        for level, maxh_nm in enumerate(MMS_FLOW_SIZES_NM):
            plain = unstabilised_errors[name][level]
            intact = streamline_errors[name][level] / plain - 1.0
            broken = damaged[name][level] / plain - 1.0
            logger.info(
                "%s at maxh %s nm: footprint intact %.3f, source withheld %.3f (%.1fx)",
                name,
                maxh_nm,
                intact,
                broken,
                intact / broken if broken > 0.0 else float("inf"),
            )
            assert intact > WITHHELD_FOOTPRINT_FACTOR * broken, (
                f"{name} at maxh {maxh_nm} nm: the stabilisation's footprint on the error "
                f"is {intact:.3f} intact and {broken:.3f} with the manufactured source "
                "withheld, which is not the collapse that mistake produces; either the "
                "source never reached R~_i in the first place, or the patch in this test "
                "no longer covers the seam it reads it through"
            )


FLOW_PAIR_VELOCITY_FACTOR = 10.0
"""How much of the velocity error the flow pair has to own for the attribution.

The transport stabilisation cannot touch the velocity rows at all: ``supg``'s
velocity error is 2.7617e-04 against ``none``'s 2.7567e-04, 0.2 % apart. So a
``reference`` velocity error an order above both is the flow pair's, and nothing
else's. Measured 3.4483e-02 — a factor of **125**, not 10 — so the factor is a
floor with two orders of headroom rather than a fitted threshold. **[tested]**
"""


@pytest.mark.slow
def test_ver42_the_flow_pair_and_not_the_transport_term_sets_the_reference_rate(
    streamline_errors: dict[str, list[float]],
    unstabilised_errors: dict[str, list[float]],
) -> None:
    """``reference``'s MMS rate is measured, attributed, and deliberately not gated.

    The plan predicted that the flow terms would be "asymptotically inert rather
    than wrong" on a Taylor-Hood pair. They are not. On ``maxh`` 0.4/0.2 nm the
    ``reference`` concentration error is 3.1107e-03 and 1.5722e-03 — rate **0.984**,
    and 0.702 for ``Cl-``, a whole order below the ``supg`` sequence's 2.012 and
    1.908 on the identical meshes — and the
    solve takes 31 Newton iterations against 5, 126 s and 436 s against 7 s and
    25 s.

    The cause is attributable without a fourth mode. ``max Pe_K <= 0.084`` here, so
    the crosswind viscosity is identically zero (asserted below) and the *only*
    difference between ``supg`` and ``reference`` on this problem is the flow GLS
    and grad-div pair. Its momentum residual is approximate on the same rule as the
    transport one, and NUM-14 records the reference's flow equation-residual
    setting as **not recorded in the report** — so this approximation is ours, not
    the reference's, and the reference ran its flow stabilisation on the P1/P1 pair
    where it is what makes the pair legal at all (RSK-18).

    Recorded, not gated: the number is an input to the section 7.4 attribution, and
    WP13's middle rung is therefore first-order accurate, with ``Delta_stab``
    measured there dominated by the flow pair rather than by the transport term
    (NUM-03, NUM-14, VER-42). **[tested]**
    """
    errors = _mms_errors("reference", sizes=MMS_FLOW_SIZES_NM)
    rates = _report_rates("reference", errors, MMS_FLOW_SIZES_NM)

    model = _mms_model("reference")
    coarsest = MMS_FLOW_SIZES_NM[0]
    mesh = CylinderGeometry(radius_nm=MMS_RADIUS_NM, length_nm=MMS_LENGTH_NM).generate(
        maxh_nm=coarsest
    )
    manufactured = ManufacturedSolution.polynomial(model)
    exact = manufactured.coefficient_functions()
    solution = model.solve(
        mesh,
        MMS_MEASURES,
        boundaries=MMS_BOUNDARIES,
        potential_values=exact[POTENTIAL],
        concentration_values={
            species: exact[concentration_field_name(species)] for species in model.species
        },
        velocity_values=exact[VELOCITY],
        sources=manufactured.source_functions(MMS_MEASURES),
    )
    samples = _crosswind_samples(solution)
    for species, (active, exceeding, total, largest) in samples.items():
        logger.info(
            "reference on the MMS mesh at maxh %s nm, %s: %d of %d samples above unit "
            "Pe_K, crosswind active at %d, peak nu_K %.3e",
            coarsest,
            species,
            exceeding,
            total,
            active,
            largest,
        )
        assert active == 0, (
            f"{species}: the crosswind is active at {active} of {total} samples on the "
            "manufactured problem, so the reference-minus-supg difference is not the "
            "flow pair's alone and this test's attribution no longer holds"
        )

    streamline = _report_rates(
        "supg, the same two levels",
        {name: values[:2] for name, values in streamline_errors.items()},
        MMS_FLOW_SIZES_NM,
    )
    for name in _transport_fields(model):
        logger.info(
            "%s: reference rate %.3f against supg %.3f on maxh %s nm",
            name,
            rates[name][0],
            streamline[name][0],
            ", ".join(str(size) for size in MMS_FLOW_SIZES_NM),
        )

    stabilised = streamline_errors[VELOCITY][0]
    plain = unstabilised_errors[VELOCITY][0]
    flowed = errors[VELOCITY][0]
    logger.info(
        "velocity L2 at maxh %s nm: none %.4e, supg %.4e, reference %.4e",
        coarsest,
        plain,
        stabilised,
        flowed,
    )
    assert abs(stabilised - plain) < 0.05 * plain, (
        f"the transport stabilisation moved the velocity error from {plain:.4e} to "
        f"{stabilised:.4e}; it touches only the transport rows, so this contradicts the "
        "attribution the reference measurement rests on"
    )
    assert flowed > FLOW_PAIR_VELOCITY_FACTOR * plain, (
        f"the reference mode's velocity error is {flowed:.4e} against {plain:.4e} "
        f"unstabilised, less than the factor {FLOW_PAIR_VELOCITY_FACTOR} this "
        "attribution expects; if the flow pair has become inert on a Taylor-Hood pair "
        "the plan's original prediction was right after all and this test should say so"
    )


# -- 3: the coarse mesh, where the mode earns its place -------------------------


COARSE_PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=25.0
)
"""The pore of ``tests/tier2/test_current_routes.py``, so the two files' numbers
are comparable; only the wall spacing and the surface charge differ here."""

COARSE_WALL_H_NM = 1.0
"""313 elements, ``max Pe_K = 4.71``: two and a half times the wall spacing NUM-30
would ask for at 0.5 M, which is what puts the operator in the regime this mode
exists for.

On it, ``none`` reaches ``Na+ = -72.9`` at ``(r, z) = (1.001, -4.376)`` nm and the
NUM-17 gate stops the run on rung ``4-ramp-charge-1.00``; ``reference`` converges in
126 Newton iterations over the ten classical rungs, with the crosswind active at
125 of 1 344 fluid samples for ``Na+`` and 123 for ``Cl-`` and peak ``nu_K`` of 3.71
and 5.61. **[tested]**
"""

RESOLVED_WALL_H_NM = 0.2
"""1 491 elements, ``max Pe_K = 0.457``: below unit Peclet everywhere, so the
crosswind term is identically zero. **[tested]**"""

COARSE_CONCENTRATION_M = 0.5
COARSE_BIAS_V = 0.05
COARSE_CHARGE_C_M2 = -0.12
"""Enough charge for ``|zeta~|`` to put ``Pe_K`` well above 1 on the coarse mesh.

A modelling choice for this benchmark and not a fitted property of any pore, the
same as the ``-0.05 C/m^2`` of the route-agreement file. Below about
``-0.10 C/m^2`` on this mesh both modes converge and the comparison measures
nothing; the surviving margin is recorded in the module docstring of the plan.
"""

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}


def _climb(wall_h_nm: float, mode: str, *, charge_C_m2: float = COARSE_CHARGE_C_M2) -> LadderResult:
    """Climb the classical rungs of the NUM-18 ladder in one mode.

    Stages 1 to 5 only: no flow and no corrections. What is under test is the
    transport operator's stability, and the flow block would add cost and a second
    explanation for every difference.
    """
    mesh = COARSE_PORE.generate(maxh_nm=5.0, wall_h_nm=wall_h_nm)
    rungs = default_ladder(
        mesh,
        concentration_M=COARSE_CONCENTRATION_M,
        bias_V=COARSE_BIAS_V,
        surface_charge_C_m2=charge_C_m2,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        start_concentration_M=None,
        charge_steps=2,
        stabilisation=mode,
    )
    return run_ladder([rung for rung in rungs if rung.stage <= 5])


@pytest.fixture(scope="module")
def coarse_reference() -> LadderResult:
    """Return the coarse-mesh climb in ``reference``, which converges."""
    result = _climb(COARSE_WALL_H_NM, "reference")
    logger.info(
        "reference on wall_h %.1f nm (mesh %s): %d iterations, %.1f s, max cell Peclet %.4f",
        COARSE_WALL_H_NM,
        result.mesh,
        result.iterations,
        result.seconds,
        result.max_cell_peclet or float("nan"),
    )
    return result


def test_num17_plain_galerkin_trips_positivity_where_reference_converges(
    coarse_reference: LadderResult,
) -> None:
    """The reason §6.4.1 cites Chaudhry et al., reproduced on this discretisation.

    Same mesh, same charge, same bias, same ladder: ``none`` drives the counter-ion
    to a large negative concentration inside the double layer and the NUM-17 gate
    stops the run naming the species, the value and its ``(r, z)``; ``reference``
    climbs to convergence. Neither half is assumed — the passing climb is the
    fixture and the failing one is raised here — because "the stabilisation helps"
    with only one of the two measured is a claim about nothing.

    ``max Pe_K`` on the converged stabilised state is recorded by the fixture and
    asserted above 1 here, so a future mesh change that quietly moved this pore
    back below unit Peclet fails rather than passing for the wrong reason
    (NUM-12, NUM-17, VER-42, QR-12).
    """
    assert coarse_reference.peclet is not None
    assert coarse_reference.max_cell_peclet is not None
    assert coarse_reference.max_cell_peclet > 1.0, (
        "this benchmark needs an under-resolved double layer to be about anything; "
        f"max Pe_K measured {coarse_reference.max_cell_peclet:.4f}"
    )

    with pytest.raises(GateViolationError) as raised:
        _climb(COARSE_WALL_H_NM, "none")
    message = str(raised.value)
    logger.info("none on the same mesh: %s", message.splitlines()[0])
    assert "concentration positivity" in message
    # The diagnostic has to say where, or it is not a diagnostic (QR-12).
    assert "r = " in message and "z = " in message


def _crosswind_samples(solution: ModelSolution) -> dict[str, tuple[int, int, int, float]]:
    """Return, per species, how many samples have an active crosswind and a high ``Pe_K``.

    ``(active, exceeding, total, max nu_K)`` over the P2 nodal set of the fluid,
    the same sample set the NUM-17 gates and the NUM-12 diagnostic use. Element
    quantities sampled at points: ``h_K`` is element-constant, so a positive sample
    does localise to one element.
    """
    from nanopnp.solve.gates import FieldSampler

    model = solution.model
    functions = {field.name: solution.component(field.name) for field in model.fields}
    states = model.transport_states(functions, solution.wall_distance_nm)
    sampler = FieldSampler(mesh=solution.space.mesh, materials=model.fluid)

    found: dict[str, tuple[int, int, int, float]] = {}
    for species, state in states.items():
        viscosity = sampler.evaluate(stabilisation_module.crosswind_viscosity(state))
        peclet = sampler.evaluate(stabilisation_module.cell_peclet(state))
        active = viscosity > 0.0
        exceeding = peclet >= 1.0
        # The containment of .knowledge/06 section 4.3, asserted where it is
        # measured: Cauchy-Schwarz bounds nu_K by D~_i max(0, C_cw Pe_K - 1), so an
        # active sample at or below unit Peclet contradicts the bound itself.
        stray = int((active & ~exceeding).sum())
        assert stray == 0, (
            f"{species}: {stray} samples carry a positive crosswind viscosity at "
            "Pe_K <= 1, which the Cauchy-Schwarz bound nu_K <= D~_i (C_cw Pe_K - 1) "
            "forbids; either C_cw moved or the residual is not b~_i . grad(c~_i)"
        )
        found[species] = (
            int(active.sum()),
            int(exceeding.sum()),
            int(viscosity.size),
            float(viscosity.max()),
        )
    return found


def test_num12_the_crosswind_is_active_where_the_cell_peclet_exceeds_one(
    coarse_reference: LadderResult,
) -> None:
    """Active on a reported fraction of the coarse mesh, and nowhere below ``Pe_K = 1``.

    The plan asked for "the same elements the NUM-12 warning names". That is not
    assertable as an equality and the containment is the honest form of it: the
    warning is a point sample of ``Pe_K`` and ``nu_K`` is an element quantity, so
    the two counts are not comparable, but ``nu_K > 0`` implies ``C_cw Pe_K > 1``
    by the bound recorded in ``.knowledge/06`` §4.3. :func:`_crosswind_samples`
    asserts that inclusion sample by sample; this test adds that the active set is
    not empty, without which the inclusion is vacuous (NUM-12, NUM-14, VER-42).
    """
    samples = _crosswind_samples(coarse_reference.solution)
    for species, (active, exceeding, total, largest) in samples.items():
        logger.info(
            "reference on wall_h %.1f nm: %s crosswind active at %d of %d fluid samples "
            "(%.1f %%), %d at Pe_K >= 1, max nu_K %.4e",
            COARSE_WALL_H_NM,
            species,
            active,
            total,
            100.0 * active / total,
            exceeding,
            largest,
        )
        assert active > 0, (
            f"{species}: the crosswind term is inactive everywhere on a mesh whose "
            "cell Peclet number reaches 4.7, so this benchmark is not exercising it"
        )
        assert largest > 0.0


def test_num14_the_crosswind_contributes_exactly_zero_on_a_resolved_mesh() -> None:
    """On a mesh meeting NUM-30 the term is zero, asserted on the assembled integrand.

    This is what makes ``reference`` safe to compare against the validated
    production answer: below unit Peclet the crosswind viscosity is *identically*
    zero, not small, so switching the mode on cannot change a resolved result
    through this term. Asserted on the assembled linear form rather than inferred
    from a current, because a current agreeing to round-off is also what a term
    that happened to be small would give (NUM-14, NUM-30, VER-42).
    """
    import ngsolve as ngs
    import numpy as np

    result = _climb(RESOLVED_WALL_H_NM, "reference", charge_C_m2=-0.05)
    logger.info(
        "reference on wall_h %.1f nm (mesh %s): max cell Peclet %.4f",
        RESOLVED_WALL_H_NM,
        result.mesh,
        result.max_cell_peclet or float("nan"),
    )
    assert result.max_cell_peclet is not None
    assert result.max_cell_peclet < 1.0, (
        "this half of the claim needs a resolved mesh; max Pe_K measured "
        f"{result.max_cell_peclet:.4f}"
    )

    solution = result.solution
    model = solution.model
    mesh = solution.space.mesh
    functions = {field.name: solution.component(field.name) for field in model.fields}
    states = model.transport_states(functions, solution.wall_distance_nm)
    mode = model.stabilisation_model

    # A scalar test space over the fluid at the concentration order. Any test
    # function family serves: if nu_K vanishes the integrand vanishes whatever it
    # is multiplied by, and that is the statement under test.
    space = ngs.H1(mesh, order=MMS_MEASURES.element_order, definedon=mesh.Materials(model.fluid))
    for species, state in states.items():
        contributions = mode.transport_contributions(
            trial=state, lagged=state, test=space.TestFunction()
        )
        assert len(contributions) == 2, (
            f"the {mode.name!r} mode produced {len(contributions)} transport contributions; "
            "this test reads the second as the crosswind"
        )
        form = ngs.LinearForm(space)
        form += AXISYMMETRIC.volume(
            contributions[1].integrand,
            definedon=mesh.Materials(model.fluid),
            extra_order=contributions[1].extra_order,
            singular=contributions[1].singular,
        )
        form.Assemble()
        entries = np.asarray(form.vec.FV())
        largest = float(np.abs(entries).max())
        logger.info(
            "%s: assembled crosswind term on the resolved mesh, max |entry| = %.3e",
            species,
            largest,
        )
        assert largest == 0.0, (
            f"{species}: the crosswind term assembles {largest:.3e} on a mesh whose cell "
            f"Peclet number peaks at {result.max_cell_peclet:.4f}; the Cauchy-Schwarz bound "
            "makes it identically zero below 1, so a non-zero entry means the parameter or "
            "the bound is wrong, not that the mesh is marginal"
        )


# -- 4: the two modes' currents converge to each other --------------------------


CURRENT_WALL_H_NM = (0.8, 0.4, 0.2)
"""The wall refinement the mode-to-mode current difference is measured over.

``wall_h`` and not ``maxh``: the stabilisation is a double-layer effect by three
orders of magnitude (``.knowledge/06`` §4.2), so the reservoir spacing is held
fixed at 5 nm and only the spacing that sets ``Pe_K`` moves.
"""

CURRENT_DIFFERENCES = (2.00e-1, 7.38e-2, 1.99e-2)
"""``|I_reference - I_none| / |I_none|`` at the three levels, rates 1.44 and 1.89.

Measured at 0.5 M, +50 mV, ``-0.05 C/m^2``, ``maxh`` 5 nm. Recorded for the scale;
the assertions below are on the *ratio falling* and on the measured rate, because
§1 of the plan predicts the exponent and not the constant in front of it.
**[tested]**
"""


def test_ver42_the_two_modes_currents_converge_to_each_other_under_refinement() -> None:
    """The stabilisation bias is a discretisation error and falls like one.

    If it did not, ``reference`` would not be a *discretisation* of the same
    problem: a term that survived refinement would be a change of model, and the
    §7.4 attribution of the COMSOL comparison would be subtracting something that
    does not go away. So the mode-to-mode difference is measured at three wall
    spacings and its rate reported.

    Gated on the ratio falling at every level and on the finest rate clearing 1.5,
    not on a constant: the measured rates are 1.44 and 1.89, approaching the
    ``O(h^2)`` §1 predicts from below, and the pre-asymptotic first interval is
    exactly what a fixed floor of 1.8 would have failed on for no defect
    (NUM-11, VER-42).
    """
    differences: list[float] = []
    for wall_h_nm in CURRENT_WALL_H_NM:
        currents: dict[str, float] = {}
        for mode in ("none", "reference"):
            result = _climb(wall_h_nm, mode, charge_C_m2=-0.05)
            currents[mode] = qoi.total_current(qoi.reaction_flux_currents(result.solution, "cis"))
        difference = abs(currents["reference"] - currents["none"]) / abs(currents["none"])
        differences.append(difference)
        logger.info(
            "wall_h %.1f nm: I(none) %.6e A, I(reference) %.6e A, difference %.4e",
            wall_h_nm,
            currents["none"],
            currents["reference"],
            difference,
        )

    rates = [
        math.log(differences[index] / differences[index + 1])
        / math.log(CURRENT_WALL_H_NM[index] / CURRENT_WALL_H_NM[index + 1])
        for index in range(len(differences) - 1)
    ]
    logger.info(
        "mode-to-mode current difference %s, rates %s over wall_h %s nm",
        " ".join(f"{value:.4e}" for value in differences),
        " ".join(f"{rate:.3f}" for rate in rates),
        ", ".join(str(size) for size in CURRENT_WALL_H_NM),
    )

    for coarser, finer in itertools.pairwise(differences):
        assert finer < coarser, (
            f"the two modes' currents moved apart under refinement ({coarser:.4e} to "
            f"{finer:.4e}); a stabilisation bias that does not vanish with h is a change "
            "of model, not a discretisation error"
        )
    assert rates[-1] > 1.5, (
        f"the finest interval converges at {rates[-1]:.3f}, short of the O(h^2) the "
        f"streamline term's Pe_K^2 scaling predicts; measured rates {rates}"
    )


# -- the equal-order pair: recorded, not gated ----------------------------------


def _climb_equal_order(mode: str) -> LadderResult:
    """Climb to stage 6 with an equal-order velocity-pressure pair."""
    mesh = COARSE_PORE.generate(maxh_nm=5.0, wall_h_nm=0.4)
    rungs = default_ladder(
        mesh,
        concentration_M=COARSE_CONCENTRATION_M,
        bias_V=COARSE_BIAS_V,
        surface_charge_C_m2=-0.05,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        start_concentration_M=None,
        charge_steps=2,
        stabilisation=mode,
        velocity_order=1,
        pressure_order=1,
    )
    return run_ladder([rung for rung in rungs if rung.stage <= 6])


def test_num03_the_equal_order_pair_is_refused_in_every_mode_without_flow_stabilisation() -> None:
    """P1/P1 is rejected before assembly in ``none`` and in ``supg`` (NUM-03).

    VER-41 already asserts this on a model built directly; what is added here is
    that the refusal survives the *production* path — ``default_ladder`` builds nine
    stages' worth of models and the unstable pair has to be caught on the first of
    them, before any mesh is meshed or any matrix factorised. A gate that only fired
    on a hand-built model would let a case file through.

    The inf-sup gate is conditional on the mode after this work package, not
    removed: the message names both the problem and the mode that would permit it.
    """
    for mode in ("none", "supg"):
        with pytest.raises(ValueError, match="inf-sup") as raised:
            _climb_equal_order(mode)
        message = str(raised.value)
        # Both halves: what is wrong, and which mode would allow it (QR-12).
        assert "reference" in message, message


@pytest.mark.slow
def test_ver42_the_equal_order_pair_is_recorded_and_not_gated() -> None:
    """P1/P1 in ``reference`` against Taylor-Hood, measured and written down.

    **Recorded, not gated.** This is the third rung of WP13's attribution ladder
    and its number is an input to that analysis rather than a verdict on this one:
    an equal-order pair stabilised by PSPG is a different discretisation, and how
    far its velocity sits from the inf-sup stable one is the quantity WP13 needs,
    not a tolerance this package gets to declare. The only assertions are that the
    solve converges and that the difference is finite — a NaN or a divergence would
    be a defect, and nothing else here would catch it (NUM-03, VER-42).

    Measured: **6.86e-02 relative r-weighted L2** on the velocity, 34 Newton
    iterations either way, on 708 elements at ``wall_h`` 0.4 nm, 0.5 M, +50 mV,
    ``-0.05 C/m^2``, through stage 6 of the NUM-18 ladder in ``reference``.
    **[tested]**
    """
    import ngsolve as ngs

    equal = _climb_equal_order("reference")
    mesh = COARSE_PORE.generate(maxh_nm=5.0, wall_h_nm=0.4)
    taylor_hood = run_ladder(
        [
            rung
            for rung in default_ladder(
                mesh,
                concentration_M=COARSE_CONCENTRATION_M,
                bias_V=COARSE_BIAS_V,
                surface_charge_C_m2=-0.05,
                solid_permittivities=MEMBRANE_PERMITTIVITY,
                start_concentration_M=None,
                charge_steps=2,
                stabilisation="reference",
            )
            if rung.stage <= 6
        ]
    )

    difference = weighted_l2_error(
        equal.solution.velocity,
        taylor_hood.solution.velocity,
        equal.solution.space.mesh,
        AXISYMMETRIC,
        what="equal-order velocity",
        definedon=equal.solution.space.mesh.Materials(equal.solution.model.fluid),
    )
    logger.info(
        "equal order P1/P1 in reference: %d iterations, %.1f s, velocity %.4e relative L2 "
        "from Taylor-Hood (%d iterations, %.1f s) on wall_h 0.4 nm, mesh %s",
        equal.iterations,
        equal.seconds,
        difference,
        taylor_hood.iterations,
        taylor_hood.seconds,
        equal.mesh,
    )
    assert math.isfinite(difference)
    assert isinstance(equal.solution.velocity, ngs.CoefficientFunction)

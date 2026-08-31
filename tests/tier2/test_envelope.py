"""Section 8.2 criterion 2: the whole FR-17 operating envelope, reached by the ladder.

    "Converged solutions across 0.005-5 M and +/-200 mV with every correction
     active, reached through the continuation ladder, with no negative
     concentration at any Newton iterate."

Phase 0 runs the 0.05-3 M sub-envelope that NUM-18 stage 9 names, at five
concentrations and six biases. It is a **measurement, not a gate**: marked
``slow``, so it never runs in continuous integration, and what it produces is the
record the end-of-phase report asks for — which points converged, how many
iterations each took, which rungs needed damping below 0.1, and on what mesh.

How the envelope is walked
--------------------------
Not thirty climbs from cold. The ladder is climbed **once**, to the easiest
corner (0.05 M, +50 mV), and every other point is one rung away from a converged
neighbour:

* a spine in concentration at +50 mV, 0.05 -> 0.15 -> 0.5 -> 1.0 -> 3.0 M;
* from each point of that spine, two *monotone* walks in bias — up to +200 mV, and
  down through zero to -200 mV — each recording the envelope points it passes
  through on the way rather than restarting from the spine for each of them.

That is what "warm-start sweeps from a converged neighbour" means, and it is the
difference between three quarters of an hour and four. Measured on the hardest
corner alone (3 M, +/-200 mV, every correction, on a mesh graded to
``lambda_D(3 M)/5``), a climb from cold costs 22 rungs, 106 Newton iterations and
500 s; the whole thirty-point grid costs 45 warm-started rungs. Recording as the
walk passes each point matters as much as the warm start does: restarting each
target from the spine covers the same ground five times over and nearly doubles
the run.

"Every correction active" includes the wall corrections
-------------------------------------------------------
`D`, `mu`, `eta`, `eps` and `rho` each carry a concentration factor *and* a
wall factor in `d`, the distance to the nearest pore boundary. Handing the solve
the saturated constant `SATURATED_WALL_DISTANCE_NM` makes every wall factor
identically 1, which is the bulk limit — the run then exercises half the
correction set while appearing to exercise all of it. So the envelope is run
against a real PHY-02 distance field, computed once per mesh from the pore
**wall** alone; the membrane is deliberately not a source.

What the assertion actually is
------------------------------
There is nothing here to compare against a closed form. The claim is that the
solver *reaches* these operating points, and the way it can fail is by aborting:
the NUM-17 positivity gate fires on a negative concentration, the packing gate on
``Phi >= 1``, or Newton hits its iteration cap. Every one of those raises. So
completing the sweep is the assertion, and the numbers below are the record of
what it cost.
"""

import logging
import math

import pytest

from nanopnp.core.scaling import debye_length_nm
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.distance import wall_distance
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledModel, ModelSolution
from nanopnp.post import qoi
from nanopnp.post.indicator import axial_indicator, lumen_band
from nanopnp.solve.continuation import (
    LADDER_START_CONCENTRATION_M,
    Rung,
    default_ladder,
    mesh_report,
    run_ladder,
)

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=20.0
)

CONCENTRATIONS_M = (0.05, 0.15, 0.5, 1.0, 3.0)
"""The NUM-18 stage-9 range, sampled at five points."""

BIASES_V = (0.05, 0.10, 0.20, -0.05, -0.10, -0.20)
"""Both signs to +/-200 mV, the FR-17 envelope."""

SURFACE_CHARGE_C_M2 = -0.05
"""A charged wall, because an uncharged pore does not exercise the double layer
the packing and positivity gates watch."""

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}
"""An insulating membrane, as in the other Tier-2 benchmarks."""

MAXH_NM = 6.0
WALL_H_NM = 0.09
"""The reduced mesh this envelope is measured on, and it is a reduction.

NUM-30 asks for about ``lambda_D/5`` at the wall, which at 3 M is 0.035 nm and
costs 8 300 elements and 66 000 degrees of freedom. At 0.09 nm — about
``lambda_D(3 M)/2`` — the same run is 3 200 elements and 25 000 degrees of
freedom and converges identically, 74 iterations either way. The envelope is a
demonstration that the ladder reaches these operating points, not a convergence
study, so it is run reduced and the mesh is recorded with the numbers [tested].
"""

BIAS_WALK_STEP_V = 0.05
"""Step of the warm-started bias walk between envelope points.

Larger than the ~10 mV of NUM-18 stage 5, and deliberately: stage 5 climbs from
an equilibrium state that has never seen a bias, while this walks between two
converged operating points a step apart. If a walk step ever fails, it is the
number to halve first.
"""


def _electrolyte() -> Electrolyte:
    """Return the reference electrolyte with every correction active (ePNP-NS)."""
    return Electrolyte.from_parameter_file(
        switches=CorrectionSwitches.for_model("willems2020_nacl")
    )


def _model(concentration_M: float) -> CoupledModel:
    """Return the full ePNP-NS model at one concentration."""
    return CoupledModel(
        electrolyte=_electrolyte(),
        concentration_M=concentration_M,
        name="epnp-ns",
        solid_permittivities=MEMBRANE_PERMITTIVITY,
    )


def _distance(mesh: object) -> object:
    """Return the PHY-02 distance field: to the pore wall, never to the membrane."""
    return wall_distance(mesh, "wall", order=AXISYMMETRIC.element_order)


def _rung(
    name: str,
    model: CoupledModel,
    mesh: object,
    bias_V: float,
    *,
    stage: int,
    distance: object,
) -> Rung:
    """Return one sweep rung: the full model at one concentration and one bias."""
    import ngsolve as ngs

    scales = model.scales
    return Rung(
        name=name,
        stage=stage,
        model=model,
        mesh=mesh,
        measures=AXISYMMETRIC,
        solve_kwargs={
            "potential_values": mesh.BoundaryCF({"cis": 0.0, "trans": bias_V / scales.potential_V}),
            "surface_charge": ngs.CF(SURFACE_CHARGE_C_M2 / scales.surface_charge_C_m2),
            "surface_charge_boundary": "wall",
            "wall_distance_nm": distance,
        },
    )


def _walk(start_V: float, end_V: float) -> tuple[float, ...]:
    """Return the biases a monotone walk visits, from just past ``start_V`` to ``end_V``.

    Empty when the walk has nowhere to go, which is what the reference bias
    itself gets: it is already converged on the spine.
    """
    span = end_V - start_V
    if abs(span) < 1e-12:
        return ()
    steps = max(1, math.ceil(abs(span) / BIAS_WALK_STEP_V))
    return tuple(start_V + span * (index + 1) / steps for index in range(steps))


def _record(
    solution: ModelSolution, concentration_M: float, bias_V: float, indicator: object
) -> qoi.QuantitiesOfInterest:
    """Extract and log one envelope point."""
    quantities = qoi.extract(solution, AXISYMMETRIC, indicator, bias_V=bias_V)
    logger.info(
        "%5.2f M %+4.0f mV: I = %+.4e A, G = %.4e S, t+ = %.4f, Q_EOF = %+.3e m^3/s, routes %.1e",
        concentration_M,
        bias_V * 1e3,
        quantities.current_A,
        quantities.conductance_S,
        quantities.transport_number,
        quantities.eof_m3_s,
        quantities.agreement.relative_difference if quantities.agreement else float("nan"),
    )
    return quantities


@pytest.mark.slow
def test_82_criterion_two_the_whole_envelope_converges_through_the_ladder() -> None:
    """Every point of the 0.05-3 M x +/-200 mV envelope converges (FR-17, section 8.2).

    A gate violation, a Newton divergence or a transfer failure all raise, so
    reaching the end of this function *is* the assertion. What the assertions
    below add is that the sweep covered what it claimed to and that the numbers
    it produced are physical.
    """
    mesh = PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM)
    distance = _distance(mesh)
    report = mesh_report(mesh)
    logger.info(
        "envelope mesh: %d elements, maxh %.1f nm, wall_h %.3f nm (lambda_D(3 M) = %.3f nm)",
        report["elements"],
        MAXH_NM,
        WALL_H_NM,
        debye_length_nm(3.0),
    )

    # -- climb the ladder once, to the easiest corner ----------------------
    start_M = LADDER_START_CONCENTRATION_M
    climb = run_ladder(
        default_ladder(
            mesh,
            concentration_M=start_M,
            bias_V=BIASES_V[0],
            surface_charge_C_m2=SURFACE_CHARGE_C_M2,
            solid_permittivities=MEMBRANE_PERMITTIVITY,
            wall_distance_nm=distance,
            start_concentration_M=None,
            charge_steps=2,
        )
    )
    logger.info(
        "climb to %.2f M, %+.0f mV: %d rungs, %d iterations, %.1f s, damping >= %.3f",
        start_M,
        BIASES_V[0] * 1e3,
        len(climb.rungs),
        climb.iterations,
        climb.seconds,
        climb.minimum_damping_used,
    )
    assert climb.solution.model.steric is True, "the envelope is run with every correction on"

    points: dict[tuple[float, float], qoi.QuantitiesOfInterest] = {}
    records: list[tuple[str, int, float, float]] = []
    spine: ModelSolution = climb.solution
    indicator = axial_indicator(mesh, lower_nm=lumen_band(PORE)[0], upper_nm=lumen_band(PORE)[1])

    for concentration_M in CONCENTRATIONS_M:
        # -- move along the concentration spine at the reference bias ------
        model = _model(concentration_M)
        if not math.isclose(concentration_M, spine.model.concentration_M):
            step = run_ladder(
                [
                    _rung(
                        f"salt-{concentration_M:g}M",
                        model,
                        mesh,
                        BIASES_V[0],
                        stage=9,
                        distance=distance,
                    )
                ],
                initial=spine,
            )
            spine = step.solution
            records.append(
                (
                    f"{concentration_M:g} M spine",
                    step.iterations,
                    step.seconds,
                    step.minimum_damping_used,
                )
            )

        # -- and walk the bias out of it, in each direction, once ----------
        points[concentration_M, BIASES_V[0]] = _record(
            spine, concentration_M, BIASES_V[0], indicator
        )
        for extreme_V in (max(BIASES_V), min(BIASES_V)):
            walking = spine
            for bias_V in _walk(BIASES_V[0], extreme_V):
                name = f"{concentration_M:g}M-{bias_V * 1e3:+.0f}mV"
                step = run_ladder(
                    [_rung(name, model, mesh, bias_V, stage=5, distance=distance)],
                    initial=walking,
                )
                walking = step.solution
                records.append(
                    (
                        f"{concentration_M:g} M {bias_V * 1e3:+.0f} mV",
                        step.iterations,
                        step.seconds,
                        step.minimum_damping_used,
                    )
                )
                # Record on the way past, rather than walking here again from
                # the spine for each target: that is where the halving is.
                wanted = [t for t in BIASES_V if math.isclose(bias_V, t)]
                if wanted:
                    points[concentration_M, wanted[0]] = _record(
                        walking, concentration_M, wanted[0], indicator
                    )

    # -- the record the end-of-phase report asks for ----------------------
    total_iterations = sum(iterations for _, iterations, _, _ in records)
    total_seconds = math.fsum(seconds for _, _, seconds, _ in records) + climb.seconds
    hardest = [name for name, _, _, damping in records if damping < 0.1]
    logger.info(
        "envelope: %d points, %d ladder iterations beyond the climb, %.0f s in total",
        len(points),
        total_iterations,
        total_seconds,
    )
    logger.info("segments that needed damping below 0.1: %s", hardest or "none")

    # -- what the sweep is allowed to have produced -----------------------
    assert len(points) == len(CONCENTRATIONS_M) * len(BIASES_V)
    for (concentration_M, bias_V), quantities in points.items():
        where = f"{concentration_M:g} M, {bias_V * 1e3:+.0f} mV"
        assert quantities.conductance_S > 0.0, f"{where}: {quantities.summary()}"
        assert 0.0 < quantities.transport_number < 1.0, where
        assert quantities.agreement is not None
        assert quantities.agreement.relative_difference < qoi.ROUTE_AGREEMENT_TOLERANCE, where
        assert quantities.eof_m3_s is not None, "the envelope runs with the flow block on"
        assert math.isfinite(quantities.eof_m3_s), where

    # A negatively charged pore is cation-selective at every point of the
    # envelope, and least so at the top of the salt range where the double layer
    # is thinnest against the pore radius.
    selectivity = {
        concentration_M: points[concentration_M, BIASES_V[0]].transport_number
        for concentration_M in CONCENTRATIONS_M
    }
    logger.info("transport number against salt at %+.0f mV: %s", BIASES_V[0] * 1e3, selectivity)
    assert all(value > 0.5 for value in selectivity.values()), selectivity
    assert selectivity[CONCENTRATIONS_M[0]] > selectivity[CONCENTRATIONS_M[-1]], (
        "screening must weaken the selectivity as the salt rises"
    )


@pytest.mark.slow
def test_82_criterion_two_the_hard_corner_from_cold_costs_what_it_costs() -> None:
    """The full ladder to 3 M and +/-200 mV, climbed from cold, on the NUM-30 mesh.

    The sweep above is the efficient way to cover the envelope; this is the
    honest measurement of the hard corner on its own, on the mesh NUM-30 asks for
    rather than the reduced one, so that the reduction is quantified rather than
    assumed. It is the point §8.2 criterion 2 is really about: 3 M, ±200 mV, every
    correction active, no negative concentration at any Newton iterate.
    """
    wall_h_nm = debye_length_nm(3.0) / 5.0
    mesh = PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=wall_h_nm)
    result = run_ladder(
        default_ladder(
            mesh,
            concentration_M=3.0,
            bias_V=0.2,
            surface_charge_C_m2=SURFACE_CHARGE_C_M2,
            solid_permittivities=MEMBRANE_PERMITTIVITY,
            wall_distance_nm=_distance(mesh),
            charge_steps=2,
            concentration_steps=3,
        )
    )
    for record in result.rungs:
        logger.info(
            "  %-24s stage %d  %6.1f s  %2d it  damping >= %.3f",
            record.name,
            record.stage,
            record.seconds,
            record.iterations,
            record.minimum_damping_used,
        )
    logger.info(
        "hard corner: wall_h %.4f nm, %d elements, %d dof, %d rungs, %d iterations, %.0f s, "
        "damping >= %.3f",
        wall_h_nm,
        mesh.ne,
        result.solution.space.ndof,
        len(result.rungs),
        result.iterations,
        result.seconds,
        result.minimum_damping_used,
    )
    assert result.rungs[-1].newton is not None
    assert result.rungs[-1].newton["converged"] is True

    indicator = axial_indicator(mesh, lower_nm=lumen_band(PORE)[0], upper_nm=lumen_band(PORE)[1])
    quantities = qoi.extract(result.solution, AXISYMMETRIC, indicator, bias_V=0.2)
    logger.info("hard corner QoIs: %s", quantities.summary())
    assert quantities.conductance_S > 0.0
    assert quantities.agreement is not None
    assert quantities.agreement.relative_difference < qoi.ROUTE_AGREEMENT_TOLERANCE


@pytest.mark.slow
def test_num18_the_ablation_ladder_reaches_the_same_corner_without_the_corrections() -> None:
    """The same corner in the classical configuration, for the differential test.

    PHY-21 makes ``pnp-ns`` a configuration of ``epnp-ns`` rather than a second
    code path, so the two can be run on the same mesh at the same operating point
    and the difference attributed to the corrections alone. This records that
    difference at the hard corner; §7.4 is where the ablation becomes systematic.
    """
    mesh = PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM)
    distance = _distance(mesh)
    measured: dict[str, qoi.QuantitiesOfInterest] = {}
    indicator = axial_indicator(mesh, lower_nm=lumen_band(PORE)[0], upper_nm=lumen_band(PORE)[1])

    for label, corrections_active in (("epnp-ns", True), ("pnp-ns", False)):
        result = run_ladder(
            default_ladder(
                mesh,
                concentration_M=3.0,
                bias_V=0.2,
                corrections_active=corrections_active,
                surface_charge_C_m2=SURFACE_CHARGE_C_M2,
                solid_permittivities=MEMBRANE_PERMITTIVITY,
                wall_distance_nm=distance,
                charge_steps=2,
                concentration_steps=3,
            )
        )
        assert result.solution.model.name == label
        assert result.solution.model.steric is corrections_active
        measured[label] = qoi.extract(result.solution, AXISYMMETRIC, indicator, bias_V=0.2)
        logger.info(
            "%s at 3 M, +200 mV: %d iterations, %.0f s, G = %.4e S, t+ = %.4f",
            label,
            result.iterations,
            result.seconds,
            measured[label].conductance_S,
            measured[label].transport_number,
        )

    corrected, classical = measured["epnp-ns"], measured["pnp-ns"]
    ratio = corrected.conductance_S / classical.conductance_S
    logger.info("the corrections change the conductance at 3 M by a factor %.4f", ratio)
    # The bound is read off the mobility correction rather than guessed. At 3 M
    # the reference parameterisation gives mu/mu0 = 0.465 for Na+ and 0.552 for
    # Cl-, so a conductance set by mobility alone would fall to about half.
    # Steric exclusion, the raised viscosity and the reduced permittivity all
    # push the same way; nothing in the correction set pushes back. A ratio
    # outside this range means one of them has the wrong sign.
    assert 0.2 < ratio < 0.9, (
        "the concentration corrections roughly halve the ionic mobility at 3 M, so ePNP-NS "
        f"must conduct appreciably less than classical PNP-NS there; the ratio is {ratio:.4f}"
    )

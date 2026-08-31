"""The NUM-17 state gates, driven by a coupled solve rather than a constructed state.

``PositivityGate`` and ``PackingFractionGate`` landed with WP3, but until the
coupled model existed nothing solved for a concentration: ``pb`` slaves its ion
densities to the potential by construction, so the gates had only ever been
checked against states written by hand. These two tests drive a real solve into
each violation and assert that it **aborts** rather than returning a plausible
number, which is the whole of QR-12.

Both configurations are chosen to fail deterministically rather than to be
representative. The pore they describe is not one anybody would run.
"""

from dataclasses import replace

import ngsolve as ngs
import pytest

from nanopnp.core.scaling import REFERENCE_DIFFUSIVITY_M2_S, debye_length_nm
from nanopnp.materials.electrolyte import Electrolyte, IonSpecies
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry, SlabGeometry
from nanopnp.physics import models
from nanopnp.physics.measures import PLANAR, Measures
from nanopnp.solve.gates import GateViolationError, maximum_packing_M

AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)


def test_num17_packing_gate_aborts_a_coupled_solve_at_high_salt() -> None:
    """Classical PNP-NS at 5 M crowds the counterion past ``Phi = 1`` and stops.

    One species alone reaches ``Phi = 1`` at 13.3 M (PHY-05), and a wall held at
    -4 thermal voltages against grounded reservoir ends multiplies the
    counterion by ``exp(4)``, which from a 5 M bulk is far past it. Classical
    PNP-NS has nothing to stop it: without ``beta_i`` the ions are point
    particles and the Boltzmann factor is unbounded. The gate is what turns that
    into an abort naming the crowding rather than a divergence naming nothing.

    Reaching this state at all needs the wall *and* the reservoir ends to carry
    essential data: with the potential fixed on the wall alone, a uniform
    ``phi~`` at the wall value and a uniform ``c~_i = 1`` satisfy every equation
    exactly, and the solve returns that trivial state instead.
    """
    model = models.create("pnp-ns", concentration_M=5.0, fluid="electrolyte")
    screening_nm = debye_length_nm(5.0)
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(
        maxh_nm=0.3, wall_h_nm=screening_nm / 5.0
    )
    boundaries = models.CoupledBoundaries(
        potential="wall|end", concentration="end", velocity="wall", velocity_axis="axis"
    )

    with pytest.raises(GateViolationError) as raised:
        model.solve(
            mesh,
            AXISYMMETRIC,
            boundaries=boundaries,
            potential_values=mesh.BoundaryCF({"wall": -4.0, "end": 0.0}),
            wall_distance_nm=2.0 - ngs.x,
        )

    violation = raised.value
    assert violation.gate == "packing fraction"
    assert violation.value >= 1.0
    assert violation.location is not None, "QR-12 requires the offending coordinate"
    radial, axial = violation.location
    assert radial == pytest.approx(2.0, abs=1e-6), "the crowding is at the wall"
    assert 0.0 <= axial <= 4.0
    assert "packing fraction" in str(violation)
    assert maximum_packing_M() == pytest.approx(13.3, abs=0.1)


def test_num17_positivity_gate_aborts_an_under_resolved_pnp_solve() -> None:
    """A blocked anion at 8 thermal voltages undershoots, and the solve stops.

    Beyond a few ``V_T`` the blocked anion falls by ``exp(-V~)`` across the
    double layer. The primitive formulation of NUM-02 gives no positivity
    guarantee, and a P2 Galerkin approximation of that decay undershoots into
    negative concentration; the gate is what turns a quietly wrong current into
    an abort. The log branch of NUM-02 is the cure, and VER-16 uses it.
    """
    base = Electrolyte.from_parameter_file()
    electrolyte = replace(
        base,
        species=tuple(
            IonSpecies(
                name=ion.name,
                valence=ion.valence,
                diffusivity_0=REFERENCE_DIFFUSIVITY_M2_S,
                steric_diameter=ion.steric_diameter,
                temperature_K=ion.temperature_K,
            )
            for ion in base.species
        ),
    )
    model = models.create(
        "pnp", electrolyte=electrolyte, classical=True, concentration_M=1.0, fluid="electrolyte"
    )
    cation, anion = model.species
    boundaries = models.CoupledBoundaries(
        potential="wall|bulk", concentration={cation: "wall|bulk", anion: "bulk"}
    )
    screening_nm = debye_length_nm(1.0)
    mesh = SlabGeometry(width_nm=20.0, height_nm=0.5).generate(
        maxh_nm=0.5, wall_h_nm=screening_nm / 5.0
    )
    concentrations = {
        cation: mesh.BoundaryCF({"wall": 0.01, "bulk": 1.0}),
        anion: ngs.CF(1.0),
    }

    previous = None
    for bias in (1.0, 2.0, 4.0):
        previous = model.solve(
            mesh,
            PLANAR,
            boundaries=boundaries,
            potential_values=mesh.BoundaryCF({"wall": -bias, "bulk": 0.0}),
            concentration_values=concentrations,
            initial=previous,
        )

    with pytest.raises(GateViolationError) as raised:
        model.solve(
            mesh,
            PLANAR,
            boundaries=boundaries,
            potential_values=mesh.BoundaryCF({"wall": -8.0, "bulk": 0.0}),
            concentration_values=concentrations,
            initial=previous,
        )

    violation = raised.value
    assert violation.gate == "concentration positivity"
    assert violation.quantity == anion
    assert violation.value <= 0.0
    assert violation.location is not None


def test_num17_gates_sample_the_fluid_only() -> None:
    """A concentration gate must not sample a solid, where the field reads zero.

    ``c_i`` lives on the fluid, and a finite-element function evaluated outside
    its ``definedon`` region comes back as zero — which is not positive. Without
    the material restriction the positivity gate would abort on every mesh that
    has a membrane in it, before Newton took a step.
    """
    model = models.create("epnp-ns", concentration_M=0.1)
    mesh = CylindricalPoreGeometry(reservoir_radius_nm=20.0).generate(maxh_nm=6.0)
    space = model.space(mesh)
    state = ngs.GridFunction(space)
    for index, _ in enumerate(model.species, start=1):
        state.components[index].Set(ngs.CF(1.0))

    state_gates, _ = model.gates(mesh, state, AXISYMMETRIC)
    for gate in state_gates:
        gate.check()

    sampled = state_gates[0].sampler.points
    assert len(sampled) > 0
    # Every sample point must lie inside the fluid: the lumen, or either
    # reservoir. Nothing may fall in the membrane annulus.
    pore = CylindricalPoreGeometry()
    half, lumen = pore.half_thickness_nm, pore.pore_radius_nm
    inside_membrane = [(r, z) for r, z in sampled if abs(z) < half - 1e-9 and r > lumen + 1e-9]
    assert not inside_membrane, f"the gate sampled the membrane at {inside_membrane[:3]}"

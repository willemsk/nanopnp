"""NUM-17 and QR-12: the state gates abort a coupled solve that is driven into each violation."""

from dataclasses import replace

import ngsolve as ngs
import pytest

from nanopnp.core.scaling import REFERENCE_DIFFUSIVITY_M2_S, debye_length_nm
from nanopnp.materials.electrolyte import Electrolyte, IonSpecies
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry, SlabGeometry
from nanopnp.numerics.gates import GateViolationError, maximum_packing_M
from nanopnp.numerics.measures import PLANAR, Measures
from nanopnp.physics import models

AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)


# PHY-05
def test_num17_packing_gate_aborts_a_coupled_solve_at_high_salt() -> None:
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


# NUM-02, VER-16
def test_num17_positivity_gate_aborts_an_under_resolved_pnp_solve() -> None:
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
    pore = CylindricalPoreGeometry()
    half, lumen = pore.half_thickness_nm, pore.pore_radius_nm
    inside_membrane = [(r, z) for r, z in sampled if abs(z) < half - 1e-9 and r > lumen + 1e-9]
    assert not inside_membrane, f"the gate sampled the membrane at {inside_membrane[:3]}"

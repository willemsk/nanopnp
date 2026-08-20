"""VER-08: the NUM-17 solver gates fire, and say what and where.

The gates exist because the failure they catch is silent. A concentration that
dips a fraction of a per cent below zero inside the double layer does not stop
Newton; it reverses that species' contribution to the current and produces an
answer that looks like a result. So these tests check two things of every gate:
that it fires at all, and that the diagnostic names the offending quantity and
its location, which is what QR-12 requires and what makes the abort useful.
"""

from __future__ import annotations

import logging

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.solve.gates import (
    ION_DIAMETER_NM,
    WATER_DIAMETER_NM,
    FieldSampler,
    GateViolationError,
    PackingFractionGate,
    PositivityGate,
    PotentialIncrementGate,
    check_all,
    excluded_volume_m3_per_mol,
    maximum_packing_M,
)

SLAB_WIDTH_NM = 4.0
"""Width of the test slab, in nm."""


@pytest.fixture
def sampler() -> FieldSampler:
    """Return a sampler over a small planar slab."""
    mesh = SlabGeometry(width_nm=SLAB_WIDTH_NM).generate(maxh_nm=0.5)
    return FieldSampler(mesh, coordinates=("x", "y"))


def _space(sampler: FieldSampler) -> ngs.FESpace:
    """Return a P2 space on the sampler's mesh."""
    return ngs.H1(sampler.mesh, order=2)


def test_ver08_maximum_packing_matches_the_published_diameters() -> None:
    """``a_i = 0.5 nm`` packs at 13.3 M and ``a_0 = 0.311 nm`` at 55.2 M (PHY-05)."""
    assert maximum_packing_M(ION_DIAMETER_NM) == pytest.approx(13.3, abs=0.05)
    assert maximum_packing_M(WATER_DIAMETER_NM) == pytest.approx(55.2, abs=0.05)


def test_ver08_excluded_volume_is_avogadro_times_the_cube() -> None:
    """``N_A a^3`` in m^3/mol, the conversion that makes ``Phi`` dimensionless."""
    assert excluded_volume_m3_per_mol(ION_DIAMETER_NM) == pytest.approx(7.528e-5, rel=1e-3)


def test_ver08_positivity_gate_passes_on_a_physical_state(sampler: FieldSampler) -> None:
    """A positive concentration everywhere raises nothing."""
    concentration = ngs.GridFunction(_space(sampler))
    concentration.Set(ngs.CF(1000.0))
    PositivityGate(sampler, {"c_Na": concentration}).check()


def test_ver08_positivity_gate_names_the_species_and_the_location(
    sampler: FieldSampler,
) -> None:
    """A negative concentration aborts, naming the species and where it went negative."""
    concentration = ngs.GridFunction(_space(sampler))
    concentration.Set(1000.0 * (ngs.x - 3.0))  # negative for x < 3 nm
    gate = PositivityGate(sampler, {"c_Na": concentration})

    with pytest.raises(GateViolationError) as caught:
        gate.check()

    violation = caught.value
    assert violation.quantity == "c_Na"
    assert violation.value < 0.0
    assert violation.location is not None
    assert violation.location[0] == pytest.approx(0.0, abs=1e-9)
    assert "x =" in str(violation)


def test_ver08_positivity_gate_rejects_exactly_zero(sampler: FieldSampler) -> None:
    """NUM-17 asks for ``min_i c_i > 0``, strictly: ``ln c`` is undefined at zero."""
    concentration = ngs.GridFunction(_space(sampler))
    concentration.Set(ngs.x)  # zero on the wall at x = 0
    with pytest.raises(GateViolationError, match="positivity"):
        PositivityGate(sampler, {"c_Cl": concentration}).check()


def test_ver08_packing_gate_passes_at_a_realistic_concentration(
    sampler: FieldSampler,
) -> None:
    """1 M NaCl packs to about 0.15, comfortably clear of the singularity."""
    bulk = ngs.CF(1000.0)  # mol/m^3
    gate = PackingFractionGate(sampler, {"c_Na": bulk, "c_Cl": bulk})
    gate.check()
    value, _ = sampler.maximum(gate.packing_fraction)
    assert value == pytest.approx(0.1506, rel=1e-3)


def test_ver08_packing_gate_fires_before_the_steric_singularity(
    sampler: FieldSampler,
) -> None:
    """``Phi >= 1`` aborts: ``beta_i`` carries ``1/(1 - Phi)`` and is singular there."""
    crowded = ngs.CF(7000.0)  # mol/m^3 each, Phi = 1.054
    gate = PackingFractionGate(sampler, {"c_Na": crowded, "c_Cl": crowded})

    with pytest.raises(GateViolationError) as caught:
        gate.check()

    assert caught.value.value >= 1.0
    assert "packing fraction" in str(caught.value)
    assert caught.value.location is not None


def test_ver08_packing_gate_warns_before_it_aborts(
    sampler: FieldSampler, caplog: pytest.LogCaptureFixture
) -> None:
    """A run drifting towards the singularity leaves a trace before it stops."""
    warm = ngs.CF(6000.0)  # Phi = 0.903, above the warning threshold, below 1
    gate = PackingFractionGate(sampler, {"c_Na": warm, "c_Cl": warm})

    with caplog.at_level(logging.WARNING, logger="nanopnp.solve.gates"):
        gate.check()

    assert "approaching the singularity" in caplog.text


def test_ver08_packing_gate_sums_over_every_species(sampler: FieldSampler) -> None:
    """The sum retains all species; collapsing it to one would halve ``Phi`` (PHY-05)."""
    bulk = ngs.CF(1000.0)
    one = PackingFractionGate(sampler, {"c_Na": bulk})
    two = PackingFractionGate(sampler, {"c_Na": bulk, "c_Cl": bulk})
    single, _ = sampler.maximum(one.packing_fraction)
    both, _ = sampler.maximum(two.packing_fraction)
    assert both == pytest.approx(2.0 * single, rel=1e-12)


def test_ver08_packing_gate_honours_a_species_specific_diameter(
    sampler: FieldSampler,
) -> None:
    """Per-species diameters are supported; the ion default applies to the rest."""
    gate = PackingFractionGate(
        sampler,
        {"c_Na": ngs.CF(1000.0), "water": ngs.CF(1000.0)},
        diameters_nm={"water": WATER_DIAMETER_NM},
    )
    assert gate.diameter_nm("water") == WATER_DIAMETER_NM
    assert gate.diameter_nm("c_Na") == ION_DIAMETER_NM


def test_num17_increment_gate_caps_the_potential_step(sampler: FieldSampler) -> None:
    """``||delta phi||_inf <= V_T``, which is 1 in the nondimensional variables."""
    increment = ngs.GridFunction(_space(sampler))
    increment.Set(ngs.CF(0.9))
    PotentialIncrementGate(sampler, increment).check()

    increment.Set(0.5 * ngs.x)  # reaches 2 at x = 4 nm
    with pytest.raises(GateViolationError) as caught:
        PotentialIncrementGate(sampler, increment).check()
    assert caught.value.value == pytest.approx(2.0, rel=1e-6)


def test_num17_increment_gate_catches_a_negative_overshoot(sampler: FieldSampler) -> None:
    """The cap is on the magnitude: a large step down is as wrong as a large step up."""
    increment = ngs.GridFunction(_space(sampler))
    increment.Set(ngs.CF(-1.5))
    with pytest.raises(GateViolationError, match="increment"):
        PotentialIncrementGate(sampler, increment).check()


def test_sampler_covers_the_p2_nodal_set(sampler: FieldSampler) -> None:
    """Vertices and edge midpoints are sampled, so a P2 extremum cannot hide.

    A P2 field on a triangle is determined by its six nodal values; sampling all
    of them plus the centroid is what makes the gate a statement about the
    degrees of freedom rather than about a lucky quadrature point.
    """
    mesh = sampler.mesh
    points = sampler.points
    assert len(points) >= mesh.nv
    assert points.shape[1] == 2
    # The wall corner is a vertex and must appear exactly once, without a -0.0 twin.
    corners = [p for p in points if abs(p[0]) < 1e-12 and abs(p[1]) < 1e-12]
    assert len(corners) == 1


def test_check_all_stops_at_the_first_violation(sampler: FieldSampler) -> None:
    """Gates run in order and the first failure is the one reported."""
    negative = ngs.GridFunction(_space(sampler))
    negative.Set(ngs.CF(-1.0))
    gates = [
        PositivityGate(sampler, {"c_Na": negative}),
        PackingFractionGate(sampler, {"c_Na": ngs.CF(1e6)}),
    ]
    with pytest.raises(GateViolationError) as caught:
        check_all(gates)
    assert caught.value.quantity == "c_Na"
    assert caught.value.gate == "concentration positivity"

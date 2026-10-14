"""VER-08: the NUM-17 solver gates fire, and say what and where."""

from __future__ import annotations

import logging

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.numerics.gates import (
    ION_DIAMETER_NM,
    WATER_DIAMETER_NM,
    FieldSampler,
    GateViolationError,
    PackingFractionGate,
    PositivityGate,
    PotentialIncrementGate,
    WallDistanceGate,
    check_all,
    excluded_volume_m3_per_mol,
    maximum_packing_M,
)

SLAB_WIDTH_NM = 4.0


@pytest.fixture
def sampler() -> FieldSampler:
    mesh = SlabGeometry(width_nm=SLAB_WIDTH_NM).generate(maxh_nm=0.5)
    return FieldSampler(mesh, coordinates=("x", "y"))


def _space(sampler: FieldSampler) -> ngs.FESpace:
    return ngs.H1(sampler.mesh, order=2)


# PHY-05
def test_ver08_maximum_packing_matches_the_published_diameters() -> None:
    assert maximum_packing_M(ION_DIAMETER_NM) == pytest.approx(13.3, abs=0.05)
    assert maximum_packing_M(WATER_DIAMETER_NM) == pytest.approx(55.2, abs=0.05)


def test_ver08_excluded_volume_is_avogadro_times_the_cube() -> None:
    assert excluded_volume_m3_per_mol(ION_DIAMETER_NM) == pytest.approx(7.528e-5, rel=1e-3)


def test_ver08_positivity_gate_passes_on_a_physical_state(sampler: FieldSampler) -> None:
    concentration = ngs.GridFunction(_space(sampler))
    concentration.Set(ngs.CF(1000.0))
    PositivityGate(sampler, {"c_Na": concentration}).check()


def test_ver08_positivity_gate_names_the_species_and_the_location(
    sampler: FieldSampler,
) -> None:
    concentration = ngs.GridFunction(_space(sampler))
    concentration.Set(1000.0 * (ngs.x - 3.0))
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
    with pytest.raises(GateViolationError, match="positivity") as caught:
        PositivityGate(sampler, {"c_Cl": ngs.x}).check()

    assert caught.value.value == 0.0


def test_ver08_packing_gate_passes_at_a_realistic_concentration(
    sampler: FieldSampler,
) -> None:
    bulk = ngs.CF(1000.0)
    gate = PackingFractionGate(sampler, {"c_Na": bulk, "c_Cl": bulk})
    gate.check()
    value, _ = sampler.maximum(gate.packing_fraction)
    assert value == pytest.approx(0.1506, rel=1e-3)


def test_ver08_packing_gate_fires_before_the_steric_singularity(
    sampler: FieldSampler,
) -> None:
    crowded = ngs.CF(7000.0)
    gate = PackingFractionGate(sampler, {"c_Na": crowded, "c_Cl": crowded})

    with pytest.raises(GateViolationError) as caught:
        gate.check()

    assert caught.value.value >= 1.0
    assert "packing fraction" in str(caught.value)
    assert caught.value.location is not None


def test_ver08_packing_gate_warns_before_it_aborts(
    sampler: FieldSampler, caplog: pytest.LogCaptureFixture
) -> None:
    warm = ngs.CF(6000.0)
    gate = PackingFractionGate(sampler, {"c_Na": warm, "c_Cl": warm})

    with caplog.at_level(logging.WARNING, logger="nanopnp.numerics.gates"):
        gate.check()

    assert "approaching the singularity" in caplog.text


def test_ver08_packing_gate_sums_over_every_species(sampler: FieldSampler) -> None:
    bulk = ngs.CF(1000.0)
    one = PackingFractionGate(sampler, {"c_Na": bulk})
    two = PackingFractionGate(sampler, {"c_Na": bulk, "c_Cl": bulk})
    single, _ = sampler.maximum(one.packing_fraction)
    both, _ = sampler.maximum(two.packing_fraction)
    assert both == pytest.approx(2.0 * single, rel=1e-12)


def test_ver08_packing_gate_honours_a_species_specific_diameter(
    sampler: FieldSampler,
) -> None:
    gate = PackingFractionGate(
        sampler,
        {"c_Na": ngs.CF(1000.0), "water": ngs.CF(1000.0)},
        diameters_nm={"water": WATER_DIAMETER_NM},
    )
    assert gate.diameter_nm("water") == WATER_DIAMETER_NM
    assert gate.diameter_nm("c_Na") == ION_DIAMETER_NM


def test_num17_increment_gate_caps_the_potential_step(sampler: FieldSampler) -> None:
    increment = ngs.GridFunction(_space(sampler))
    increment.Set(ngs.CF(0.9))
    PotentialIncrementGate(sampler, increment).check()

    increment.Set(0.5 * ngs.x)
    with pytest.raises(GateViolationError) as caught:
        PotentialIncrementGate(sampler, increment).check()
    assert caught.value.value == pytest.approx(2.0, rel=1e-6)


def test_num17_increment_gate_catches_a_negative_overshoot(sampler: FieldSampler) -> None:
    increment = ngs.GridFunction(_space(sampler))
    increment.Set(ngs.CF(-1.5))
    with pytest.raises(GateViolationError, match="increment"):
        PotentialIncrementGate(sampler, increment).check()


def test_qr12_a_nan_anywhere_fails_the_packing_increment_and_wall_distance_gates(
    sampler: FieldSampler,
) -> None:
    space = _space(sampler)
    poisoned = ngs.GridFunction(space)
    poisoned.Set(ngs.CF(1000.0))
    poisoned.vec[3] = float("nan")
    with pytest.raises(GateViolationError, match="packing fraction"):
        PackingFractionGate(sampler, {"c_Na": poisoned, "c_Cl": ngs.CF(1000.0)}).check()

    increment = ngs.GridFunction(space)
    increment.Set(ngs.CF(0.1))
    increment.vec[3] = float("nan")
    with pytest.raises(GateViolationError, match="increment"):
        PotentialIncrementGate(sampler, increment).check()

    distance = ngs.GridFunction(space)
    distance.Set(ngs.CF(1.0))
    distance.vec[3] = float("nan")
    with pytest.raises(GateViolationError, match="min d"):
        WallDistanceGate(sampler, distance).check()


def test_sampler_covers_the_p2_nodal_set(sampler: FieldSampler) -> None:
    mesh = sampler.mesh
    points = sampler.points
    assert len(points) >= mesh.nv
    assert points.shape[1] == 2
    corners = [p for p in points if abs(p[0]) < 1e-12 and abs(p[1]) < 1e-12]
    assert len(corners) == 1


def test_ver08_packing_gate_refuses_an_empty_species_mapping(sampler: FieldSampler) -> None:
    with pytest.raises(ValueError, match="at least one species"):
        PackingFractionGate(sampler, {})


def test_sampler_refuses_a_vector_expression(sampler: FieldSampler) -> None:
    with pytest.raises(ValueError, match="must be scalar"):
        sampler.minimum(ngs.CF((ngs.x, ngs.y)))


def test_sampler_locates_its_points_once(sampler: FieldSampler) -> None:
    assert sampler.located is sampler.located


def test_check_all_stops_at_the_first_violation(sampler: FieldSampler) -> None:
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

"""VER-16: the 1D steady PNP current-voltage response and its limiting current."""

from dataclasses import replace
from itertools import pairwise

import ngsolve as ngs
import pytest

from nanopnp.core.scaling import REFERENCE_DIFFUSIVITY_M2_S, debye_length_nm
from nanopnp.materials.electrolyte import Electrolyte, IonSpecies
from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.numerics.measures import PLANAR
from nanopnp.physics import models
from nanopnp.post.reaction_flux import boundary_reaction_flux

LENGTH_NM = 2000.0

HEIGHT_NM = 0.5

CONCENTRATION_M = 1.0
DEPLETION = 1.0e-3

BIASES = (0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 16.0, 20.0)


def _equal_diffusivity_electrolyte() -> Electrolyte:
    base = Electrolyte.from_parameter_file()
    species = tuple(
        IonSpecies(
            name=ion.name,
            valence=ion.valence,
            diffusivity_0=REFERENCE_DIFFUSIVITY_M2_S,
            steric_diameter=ion.steric_diameter,
            temperature_K=ion.temperature_K,
        )
        for ion in base.species
    )
    return replace(base, species=species)


# NUM-18, NUM-16, NUM-02, NUM-17
@pytest.fixture(scope="module")
def sweep() -> tuple[list[float], float]:
    electrolyte = _equal_diffusivity_electrolyte()
    model = models.create(
        "pnp",
        electrolyte=electrolyte,
        # Classical by construction: ``create`` rebuilds the resolved corrections; the factor 2
        # of the closed form is the Einstein relation, which holds only at mu = D.
        classical=True,
        concentration_M=CONCENTRATION_M,
        fluid="electrolyte",
        log_variables=True,
    )
    cation, anion = model.species
    # The reaction flux is taken block-wise, so the cation's position in the
    # product space is read off the model rather than assumed.
    cation_block = [f.name for f in model.fields].index(f"c_{cation}")
    boundaries = models.CoupledBoundaries(
        potential="wall|bulk",
        concentration={cation: "wall|bulk", anion: "bulk"},
    )
    screening_nm = debye_length_nm(CONCENTRATION_M)
    # The quality gate is off here: the strip is anisotropic by construction, and the solution
    # is constant along its stretched direction, so the interpolation error of its elements is zero.
    mesh = SlabGeometry(width_nm=LENGTH_NM, height_nm=HEIGHT_NM).generate(
        maxh_nm=LENGTH_NM / 40.0, wall_h_nm=screening_nm / 5.0, check_quality=False
    )
    concentrations = {
        cation: mesh.BoundaryCF({"wall": DEPLETION, "bulk": 1.0}),
        anion: ngs.CF(1.0),
    }

    currents: list[float] = []
    previous = None
    for bias in BIASES:
        solution = model.solve(
            mesh,
            PLANAR,
            boundaries=boundaries,
            potential_values=mesh.BoundaryCF({"wall": -bias, "bulk": 0.0}),
            concentration_values=concentrations,
            initial=previous,
        )
        # The flux uses the residual the solve assembled, not a rebuilt copy: a coupled residual
        # reassembled with other arguments is a different operator.
        assert solution.residual is not None
        flux = boundary_reaction_flux(
            solution.residual, solution.state, "wall", component=cation_block
        )
        currents.append(flux / HEIGHT_NM)
        previous = solution

    diffusivity = electrolyte.species[0].diffusivity_0 / REFERENCE_DIFFUSIVITY_M2_S
    limiting = 2.0 * diffusivity * (1.0 - DEPLETION) / LENGTH_NM
    return currents, limiting


def test_ver16_current_saturates_at_the_limiting_value(
    sweep: tuple[list[float], float],
) -> None:
    currents, limiting = sweep
    assert currents[-1] == pytest.approx(limiting, rel=0.03), (
        f"current {currents[-1]:.6g} against limiting {limiting:.6g}"
    )


def test_ver16_response_is_monotone_and_never_exceeds_the_limit_appreciably(
    sweep: tuple[list[float], float],
) -> None:
    currents, limiting = sweep
    assert all(later > earlier for earlier, later in pairwise(currents)), (
        f"the response must be monotone in bias: {currents}"
    )
    assert max(currents) < 1.05 * limiting


def test_ver16_the_plateau_is_the_departure_from_ohm_s_law(
    sweep: tuple[list[float], float],
) -> None:
    currents, limiting = sweep
    assert currents[-1] / currents[0] < 1.25, (
        f"bias rose {BIASES[-1] / BIASES[0]:.0f}-fold; current rose "
        f"{currents[-1] / currents[0]:.3f}-fold"
    )
    ohmic = 2.0 * BIASES[-1] / LENGTH_NM
    assert currents[-1] < 0.1 * ohmic, (
        f"current {currents[-1]:.4g} is not limited against the ohmic {ohmic:.4g}"
    )
    assert currents[0] > 0.75 * limiting, (
        "the film is already close to limiting at the bottom of the sweep, because "
        "the depleted electrode imposes the concentration drop that sets it"
    )

"""VER-16: the 1D steady PNP current-voltage response and its limiting current.

Bazant, Chu & Bayly, *SIAM J. Appl. Math.* **65**, 1463 (2005), pose the
electrochemical thin film: a binary electrolyte between a reservoir and an
electrode that consumes the cation while blocking the anion. The response is the
canonical test of the *full* PNP system rather than of any one term, because the
limiting current is set by the interaction of diffusion, migration and the
zero-flux constraint, not by any of them alone.

The limiting current, derived here rather than quoted
-----------------------------------------------------
The anion is blocked at the electrode and has no source, so in one dimension its
flux is constant and equal to its boundary value, zero. ``J_- = 0`` gives
``c_- = A exp(phi~)`` exactly. Outside the double layers electroneutrality gives
``c_+ = c_- = c``, hence ``grad(phi~) = grad(c)/c`` and

    J_+ = -D_+ (grad c + c grad phi~) = -2 D_+ grad c

which is constant, so ``c`` is linear between its two boundary values. With
``c = c_0`` at the reservoir and ``c = delta c_0`` at the electrode a distance
``L`` away,

    |J_+| = 2 D_+ c_0 (1 - delta) / L

and in the NUM-09 variables, with lengths in the mesh's nanometre,

    |J~_+| = 2 D~_+ (1 - delta) / L~ .

The prefactor 2 is the migration contribution doubling the diffusive one, and it
depends on the reservoir convention; the derivation is stated here rather than a
number copied, because published forms of this result differ by exactly that
kind of factor.

Both ionic diffusivities are made equal for the benchmark, which is a property
of the *test electrolyte* and not of the solver: the closed form above assumes
it, and NaCl's ``D_Na`` and ``D_Cl`` differ by 52 %.
"""

from dataclasses import replace
from itertools import pairwise

import ngsolve as ngs
import pytest

from nanopnp.core.scaling import REFERENCE_DIFFUSIVITY_M2_S, debye_length_nm
from nanopnp.materials.electrolyte import Electrolyte, IonSpecies
from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.physics import models
from nanopnp.physics.measures import PLANAR
from nanopnp.post.reaction_flux import boundary_reaction_flux

LENGTH_NM = 100.0
"""Film thickness ``L~``. The Debye length is 0.30 nm at 1 M, so the
electroneutral core the derivation assumes is 300 screening lengths wide."""

HEIGHT_NM = 0.5
"""Transverse extent. The problem is one-dimensional; this is the slab it is
solved on, and every flux below is divided by it."""

CONCENTRATION_M = 1.0
DEPLETION = 1.0e-3
"""``delta``: the cation concentration the electrode holds, as a fraction of bulk."""

BIASES = (0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 16.0, 20.0)
"""Applied bias in units of ``V_T``; 20 is 514 mV."""


def _equal_diffusivity_electrolyte() -> Electrolyte:
    """Return the reference electrolyte with both ions at ``D_0``."""
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


@pytest.fixture(scope="module")
def sweep() -> tuple[list[float], float]:
    """Return the current at each bias, and the electroneutral limiting current.

    The ramp is warm-started from the previous rung, which is the continuation
    of NUM-18 in miniature: a cold solve at 20 ``V_T`` does not converge, and the
    update-based convergence test of NUM-16 is what lets each rung re-solve from
    its neighbour without demanding another six orders of magnitude from an
    already-converged residual.

    The log-variable branch of NUM-02 is used. That is what it is for: beyond a
    few thermal voltages the blocked anion falls by ``exp(-V~)`` across the
    double layer, and the primitive form undershoots into negative concentration
    — which the NUM-17 gate catches, correctly, by aborting.
    """
    electrolyte = _equal_diffusivity_electrolyte()
    model = models.create(
        "pnp",
        electrolyte=electrolyte,
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
    mesh = SlabGeometry(width_nm=LENGTH_NM, height_nm=HEIGHT_NM).generate(
        maxh_nm=LENGTH_NM / 40.0, wall_h_nm=screening_nm / 5.0
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
        residual = ngs.BilinearForm(solution.space)
        residual += model.residual_form(solution.space, PLANAR)
        # NUM-25, not a cross-section integral of the CG flux (NUM-23): the
        # cation is the only field constrained at the electrode, so the flux is
        # taken component-wise.
        flux = boundary_reaction_flux(residual, solution.state, "wall", component=cation_block)
        currents.append(flux / HEIGHT_NM)
        previous = solution

    diffusivity = electrolyte.species[0].diffusivity_0 / REFERENCE_DIFFUSIVITY_M2_S
    limiting = 2.0 * diffusivity * (1.0 - DEPLETION) / LENGTH_NM
    return currents, limiting


def test_ver16_current_saturates_at_the_limiting_value(
    sweep: tuple[list[float], float],
) -> None:
    """The high-bias current is the electroneutral limiting current to 3 %."""
    currents, limiting = sweep
    assert currents[-1] == pytest.approx(limiting, rel=0.03), (
        f"current {currents[-1]:.6g} against limiting {limiting:.6g}"
    )


def test_ver16_response_is_monotone_and_never_exceeds_the_limit_appreciably(
    sweep: tuple[list[float], float],
) -> None:
    """The I-V curve rises towards the plateau and does not overshoot it."""
    currents, limiting = sweep
    assert all(later > earlier for earlier, later in pairwise(currents)), (
        f"the response must be monotone in bias: {currents}"
    )
    assert max(currents) < 1.05 * limiting


def test_ver16_the_plateau_is_the_departure_from_ohm_s_law(
    sweep: tuple[list[float], float],
) -> None:
    """A fortyfold rise in bias raises the current by less than a quarter.

    This is what "limiting current" means quantitatively. A solver with the
    right conductivity but no depletion physics would give a current
    proportional to the bias; the conductivity of this electrolyte is
    ``sum_i z_i^2 mu~_i c~_i = 2`` in the nondimensional variables, so the ohmic
    prediction at the top of the sweep is ``2 V~ / L~``, twenty times what a
    correct solve returns.
    """
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

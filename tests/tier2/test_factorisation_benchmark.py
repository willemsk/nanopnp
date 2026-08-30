"""Phase 0 exit criterion 3: direct factorisation at production size.

RSK-10 asks whether the two solvers the NGSolve pip wheel actually offers cope
with the reference mesh size — about 1.2e5 cells with five fields — on a laptop.
The specification wants this measured on day one of the phase rather than
discovered at the end of it, because the answer decides whether the iterative
``PCFIELDSPLIT`` fallback of NUM-22 has to be built before the phase can finish.

These tests are marked ``slow`` and are excluded from the push gate. They are
measurements, not gates: the assertions are loose sanity checks that the
factorisation happened and is usable, and the numbers go to the log.

Run them with::

    uv run pytest -m slow --log-cli-level=INFO -v

The block system assembled here is a structural stand-in for the coupled
Jacobian of WP4, not the physics: the same five fields on the same spaces with
the same sparsity pattern and the same coupling blocks. Factorisation cost
depends on the pattern, not on the coefficient values, so this measures the
right thing without waiting for the weak forms.
"""

from __future__ import annotations

import gc
import logging
import sys
import time
from dataclasses import dataclass

import ngsolve as ngs
import numpy as np
import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.solve.linear import to_scipy

logger = logging.getLogger(__name__)

PRODUCTION_MAXH_NM = 0.32
"""Mesh size giving about 1.1e5 cells, the reference size of criterion 3."""

SUPERLU_MAXH_NM = 0.9
"""Mesh size SuperLU is measured at; at the production size it exhausts memory."""

FLUID = "electrolyte|cis|trans"
"""Materials carrying the concentration, velocity and pressure fields (NUM-01)."""

RESERVOIR = "cis|trans"
"""Boundaries carrying the essential conditions: the two reservoir caps.

Without them the block system is **singular** — pure-Neumann Poisson has the
constant null mode and the Stokes block has no way to fix the pressure — and a
direct solver factorises a singular matrix without complaint, returning a
"solution" of norm 1e33 that passes any finiteness check. Constraining the caps,
which is where the bias and the bulk concentrations are imposed in the real
problem, is what lets these tests assert that the factorisation is *usable* and
not merely that it completed.

The constraints *remove* degrees of freedom — 4.50 % of them at the production
size, 5.73 % at the SuperLU size, 8.96 % at maxh 3.0 (measured) — so the
factorisation they are timed against is slightly smaller than the unconstrained
one the recorded table was measured on. The published figures are therefore
upper bounds on the constrained system, which is the safe direction for a
criterion that asks whether the factorisation *fits*.
"""


def peak_memory_MB() -> float:
    """Return the peak resident set size of this process, in MB.

    A high-water mark, so it never falls: within one process only the largest
    factorisation so far is visible. That is the honest figure for "does this
    fit on a laptop", and it is why the scaling study behind these numbers ran
    one configuration per process.

    ``ru_maxrss`` is in kilobytes on Linux and in bytes on macOS. ``resource``
    is a Unix module with no standard-library equivalent on Windows, so the
    figure is NaN there rather than guessed at; nothing asserts on it, the
    numbers go to the log. The import is deferred for the same reason: at module
    scope it fails collection on Windows even though these tests are deselected,
    because pytest imports a module before it reads its markers.
    """
    if sys.platform == "win32":
        return float("nan")

    import resource

    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024.0 * 1024.0) if sys.platform == "darwin" else raw / 1024.0


@dataclass
class CoupledSystem:
    """An assembled five-field block system and the mesh it lives on."""

    mesh: ngs.Mesh
    space: ngs.FESpace
    form: ngs.BilinearForm

    @property
    def cells(self) -> int:
        """Number of triangles."""
        return self.mesh.ne

    @property
    def dofs(self) -> int:
        """Total degrees of freedom across the five fields."""
        return self.space.ndof

    @property
    def nonzeros(self) -> int:
        """Stored nonzeros in the assembled matrix."""
        return self.form.mat.nze


def build_coupled_system(maxh_nm: float) -> CoupledSystem:
    """Assemble the five-field block system of NUM-01 on a cylindrical pore.

    ``phi`` lives on all of ``Omega``; ``c_i``, ``u`` and ``p`` only on the
    fluid. That restriction is not cosmetic — it removes the membrane's degrees
    of freedom from four of the five fields, and with them a sixth of the
    matrix. The reservoir caps carry the essential conditions, without which the
    system is singular; see :data:`RESERVOIR`.
    """
    mesh = CylindricalPoreGeometry().generate(maxh_nm=maxh_nm, wall_h_nm=maxh_nm / 8.0)
    space = ngs.FESpace(
        [
            ngs.H1(mesh, order=2, dirichlet=RESERVOIR),  # phi, on all of Omega
            ngs.H1(mesh, order=2, definedon=FLUID, dirichlet=RESERVOIR),  # c_+
            ngs.H1(mesh, order=2, definedon=FLUID, dirichlet=RESERVOIR),  # c_-
            ngs.VectorH1(mesh, order=2, definedon=FLUID, dirichlet=RESERVOIR),  # u, Taylor-Hood
            ngs.H1(mesh, order=1, definedon=FLUID),  # p
        ]
    )
    (phi, cp, cm, u, p), (v_phi, v_cp, v_cm, v_u, v_p) = space.TnT()
    # The r weight and the quadrature policy come from Measures rather than
    # being written out here: NUM-04 and NUM-07 live in one place, and a
    # benchmark that hand-rolled them would not exercise the production measure.
    fluid = {"definedon": mesh.Materials(FLUID)}

    form = ngs.BilinearForm(space)
    # Poisson, coupled to both ion species.
    form += AXISYMMETRIC.volume(ngs.grad(phi) * ngs.grad(v_phi) - (cp - cm) * v_phi, extra_order=1)
    # Nernst-Planck: diffusion, electromigration, convection.
    form += AXISYMMETRIC.volume(
        ngs.grad(cp) * ngs.grad(v_cp)
        + cp * ngs.grad(phi) * ngs.grad(v_cp)
        + u * ngs.grad(cp) * v_cp,
        **fluid,
    )
    form += AXISYMMETRIC.volume(
        ngs.grad(cm) * ngs.grad(v_cm)
        - cm * ngs.grad(phi) * ngs.grad(v_cm)
        + u * ngs.grad(cm) * v_cm,
        **fluid,
    )
    # Stokes, with the electrical body force closing the loop back to the ions.
    form += AXISYMMETRIC.volume(
        ngs.InnerProduct(ngs.Grad(u), ngs.Grad(v_u)) - ngs.div(v_u) * p - ngs.div(u) * v_p,
        **fluid,
    )
    form += AXISYMMETRIC.volume((cp - cm) * ngs.grad(phi) * v_u, **fluid)
    form.Assemble()
    return CoupledSystem(mesh=mesh, space=space, form=form)


@pytest.mark.slow
def test_criterion3_umfpack_factorises_a_production_sized_problem() -> None:
    """UMFPACK factorises about 1.1e5 cells with five fields, and the cost is recorded.

    Measured on the development laptop (WSL2, 15 GB): 41 s and 6.2 GB peak at
    1.09e5 cells and 1.04e6 degrees of freedom. Both are within a laptop's
    reach, so NUM-21's default direct path stands and the iterative fallback of
    NUM-22 is not needed for the 2D phase.
    """
    system = build_coupled_system(PRODUCTION_MAXH_NM)
    assembled_MB = peak_memory_MB()

    start = time.perf_counter()
    inverse = system.form.mat.Inverse(system.space.FreeDofs(), inverse="umfpack")
    elapsed = time.perf_counter() - start
    peak_MB = peak_memory_MB()

    logger.info(
        "criterion 3, umfpack: %d cells, %d dof, %d nonzeros; factorised in %.1f s; "
        "peak memory %.0f MB (%.0f MB after assembly)",
        system.cells,
        system.dofs,
        system.nonzeros,
        elapsed,
        peak_MB,
        assembled_MB,
    )

    assert system.cells > 1.0e5, "the criterion is about a production-sized mesh"
    # "Usable" means the factorisation actually solves, not merely that it
    # returned finite numbers: a singular system factorises without complaint.
    right = system.form.mat.CreateColVector()
    right[:] = 1.0
    solution = (inverse * right).Evaluate()
    residual = system.form.mat.CreateColVector()
    residual.data = right - system.form.mat * solution
    free = np.asarray(list(system.space.FreeDofs()), dtype=bool)
    assert np.abs(np.asarray(residual.FV().NumPy())[free]).max() < 1e-6


@pytest.mark.slow
def test_criterion3_superlu_is_a_licence_fallback_not_a_performance_one() -> None:
    """SuperLU works, at several times the cost, and does not reach production size.

    Measured on the same laptop, one process per configuration:

    ===========  =========  ============  ==============  ============  =============
    cells        dof        nonzeros      umfpack         superlu       superlu peak
    ===========  =========  ============  ==============  ============  =============
    1.50e4       1.43e5     8.4e6         4.4 s, 855 MB   24.0 s        2593 MB
    3.84e4       3.68e5     2.2e7         14.0 s, 2.2 GB  140.3 s       8656 MB
    1.09e5       1.04e6     6.2e7         41.1 s, 6.2 GB  OOM-killed    >15.4 GB
    ===========  =========  ============  ==============  ============  =============

    So SuperLU costs roughly 3.5x the memory and 10x the time of UMFPACK, scales
    worse in both, and is killed by the kernel at the reference mesh size. That
    matters for CON-11: a redistributable bundle cannot simply swap the GPL-2+
    UMFPACK for the BSD SuperLU and keep the same capability. The trade is real
    and belongs in ADR-003, not in a footnote.

    This test therefore runs at a size SuperLU can handle, and asserts only that
    the BSD path works and agrees with UMFPACK.
    """
    from scipy.sparse.linalg import splu

    system = build_coupled_system(SUPERLU_MAXH_NM)
    free = np.asarray(list(system.space.FreeDofs()), dtype=bool)

    start = time.perf_counter()
    matrix = to_scipy(system.form.mat)[free][:, free].tocsc()
    conversion = time.perf_counter() - start

    start = time.perf_counter()
    factorisation = splu(matrix)
    superlu_elapsed = time.perf_counter() - start

    gc.collect()
    start = time.perf_counter()
    inverse = system.form.mat.Inverse(system.space.FreeDofs(), inverse="umfpack")
    umfpack_elapsed = time.perf_counter() - start

    logger.info(
        "criterion 3, superlu: %d cells, %d dof; superlu %.1f s (+%.1f s scipy conversion) "
        "against umfpack %.1f s, a factor of %.1f; peak memory %.0f MB",
        system.cells,
        system.dofs,
        superlu_elapsed,
        conversion,
        umfpack_elapsed,
        superlu_elapsed / max(umfpack_elapsed, 1e-9),
        peak_memory_MB(),
    )

    right = system.form.mat.CreateColVector()
    right[:] = 1.0
    from_superlu = factorisation.solve(np.asarray(right.FV().NumPy())[free])
    from_umfpack = np.asarray((inverse * right).Evaluate().FV().NumPy())[free]

    # The licensing choice must not also be a numerical one: the two
    # factorisations of the same system have to agree to round-off.
    scale = max(float(np.abs(from_umfpack).max()), 1.0)
    assert np.abs(matrix @ from_superlu - 1.0).max() < 1e-6 * scale
    assert np.abs(from_superlu - from_umfpack).max() < 1e-8 * scale

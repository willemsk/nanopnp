"""NUM-22 (with NUM-01, NUM-21, CON-11): direct factorisation at production size."""

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
from nanopnp.numerics.linear import to_scipy
from nanopnp.numerics.measures import AXISYMMETRIC

logger = logging.getLogger(__name__)

PRODUCTION_MAXH_NM = 0.32

SUPERLU_MAXH_NM = 0.9

# NUM-01
FLUID = "electrolyte|cis|trans"

RESERVOIR = "cis|trans"


def peak_memory_MB() -> float:
    if sys.platform == "win32":
        return float("nan")

    import resource

    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024.0 * 1024.0) if sys.platform == "darwin" else raw / 1024.0


@dataclass
class CoupledSystem:
    mesh: ngs.Mesh
    space: ngs.FESpace
    form: ngs.BilinearForm

    @property
    def cells(self) -> int:
        return self.mesh.ne

    @property
    def dofs(self) -> int:
        return self.space.ndof

    @property
    def nonzeros(self) -> int:
        return self.form.mat.nze


# NUM-01
def build_coupled_system(maxh_nm: float) -> CoupledSystem:
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
    form += AXISYMMETRIC.volume(ngs.grad(phi) * ngs.grad(v_phi) - (cp - cm) * v_phi, extra_order=1)
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
    form += AXISYMMETRIC.volume(
        ngs.InnerProduct(ngs.Grad(u), ngs.Grad(v_u)) - ngs.div(v_u) * p - ngs.div(u) * v_p,
        **fluid,
    )
    form += AXISYMMETRIC.volume((cp - cm) * ngs.grad(phi) * v_u, **fluid)
    form.Assemble()
    return CoupledSystem(mesh=mesh, space=space, form=form)


# NUM-21, NUM-22
@pytest.mark.slow
def test_criterion3_umfpack_factorises_a_production_sized_problem() -> None:
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


# CON-11
@pytest.mark.slow
def test_criterion3_superlu_is_a_licence_fallback_not_a_performance_one() -> None:
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

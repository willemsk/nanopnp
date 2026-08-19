"""The variational reaction flux (NUM-25).

The assembled residual, evaluated against a test function that is 1 on a
Dirichlet boundary and 0 elsewhere, *is* the flux through that boundary. For the
weak form ``R(u; v) = 0`` satisfied on the free degrees of freedom, the residual
that survives on the constrained ones equals the boundary term integrated
against ``v`` — so no post-processing of a gradient is involved and none of the
accuracy of one is lost.

This matters far beyond convenience. Continuous-Galerkin fluxes are not
pointwise conservative, so a current obtained by integrating the flux over an
interior cross-section varies between cross-sections by amounts that can exceed
the rectification signal at low bias (NUM-23). The reaction flux and the
domain-indicator form of NUM-24 are the two routes this project is allowed to
use, and their agreement is a CI gate (VER-11, QR-04).

Hughes, Engel, Mazzei & Larson, *J. Comput. Phys.* **163**, 467 (2000).
"""

from __future__ import annotations

from nanopnp.core.typing import Expression, FESpace, GridFunction


def boundary_indicator(space: FESpace, boundary: str) -> GridFunction:
    """Return the finite-element function equal to 1 on ``boundary`` and 0 elsewhere.

    It must be built by interpolation, never by setting the boundary degrees of
    freedom to 1: NGSolve's higher-order basis is **hierarchical**, so its shape
    functions do not form a partition of unity. Summing the P2 basis functions
    along a boundary edge integrates to 11/12 of its length, not to its length,
    and a reaction flux normalised on that assumption is wrong by 8.3 % at every
    refinement level - a mesh-independent error that looks convincingly like a
    modelling difference rather than a bug.
    """
    import ngsolve as ngs

    indicator = ngs.GridFunction(space, name=f"psi_{boundary}")
    indicator.Set(ngs.CF(1.0), definedon=space.mesh.Boundaries(boundary))
    return indicator


def boundary_reaction_flux(
    residual_form: Expression,
    solution: GridFunction,
    boundary: str,
) -> float:
    """Return the reaction flux of a converged solution through one boundary.

    Parameters
    ----------
    residual_form
        An assembled ``BilinearForm`` holding the residual of the solved
        problem, written in the trial function.
    solution
        The converged solution.
    boundary
        Boundary-name regular expression to integrate over. Its degrees of
        freedom must be the constrained ones of the solve.

    Returns
    -------
    float
        ``int_boundary (grad u . n) ds`` in the units of the form, with ``n``
        the outward normal.
    """
    import ngsolve as ngs

    residual = solution.vec.CreateVector()
    residual_form.Apply(solution.vec, residual)
    indicator = boundary_indicator(solution.space, boundary)
    return float(ngs.InnerProduct(residual, indicator.vec))

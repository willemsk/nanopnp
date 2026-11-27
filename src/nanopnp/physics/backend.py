"""NGSolve's implementation of the operators and the geometry the terms write with."""

from __future__ import annotations

from nanopnp.core.typing import Expression, Mesh
from nanopnp.materials.forms import NGSolveOps
from nanopnp.numerics.measures import Measures
from nanopnp.physics.operators import Geometry, Operators

__all__ = ["NGSOLVE_OPERATORS", "NGSolveOperators", "geometry_of"]


class NGSolveOperators(NGSolveOps):
    """The operators as NGSolve ``CoefficientFunction`` trees."""

    def grad(self, f: Expression) -> Expression:
        """Return the gradient of ``f``: a vector of a scalar, a tensor of a vector."""
        import ngsolve as ngs

        return ngs.grad(f)

    def hessian(self, f: Expression) -> Expression:
        """Return the tensor of second derivatives of the scalar ``f``."""
        return f.Operator("hesse")

    def dot(self, a: Expression, b: Expression) -> Expression:
        """Return the scalar product of two vectors."""
        import ngsolve as ngs

        return ngs.InnerProduct(a, b)

    def inner(self, a: Expression, b: Expression) -> Expression:
        """Return the double contraction ``a : b`` of two tensors."""
        import ngsolve as ngs

        return ngs.InnerProduct(a, b)

    def apply(self, tensor: Expression, vector: Expression) -> Expression:
        """Return the vector ``tensor . vector``."""
        return tensor * vector

    def outer(self, a: Expression, b: Expression) -> Expression:
        """Return the tensor ``a (x) b`` of two vectors."""
        import ngsolve as ngs

        return ngs.OuterProduct(a, b)

    def transpose(self, t: Expression) -> Expression:
        """Return the transpose of the tensor ``t``."""
        return t.trans

    def trace(self, t: Expression) -> Expression:
        """Return the trace of the tensor ``t``."""
        import ngsolve as ngs

        return ngs.Trace(t)

    def component(self, vector: Expression, index: int) -> Expression:
        """Return one component of ``vector``."""
        return vector[index]

    def derivative(self, expression: Expression, variable: Expression) -> Expression:
        """Return the derivative of ``expression`` in ``variable``, a field it is written in."""
        return expression.Diff(variable)

    def element_size(self) -> Expression:
        """Return ``h_K = sqrt(2|K|)`` on a triangle, NGSolve's mesh size."""
        import ngsolve as ngs

        return ngs.specialcf.mesh_size


NGSOLVE_OPERATORS: Operators = NGSolveOperators()


def geometry_of(mesh: Mesh, measures: Measures) -> Geometry:
    """Return ``mesh``'s geometry: the last coordinate axial, the first radial if axisymmetric."""
    import ngsolve as ngs

    dimension = int(mesh.dim)
    coordinates = (ngs.x, ngs.y, ngs.z)[:dimension]
    return Geometry(
        dimension=dimension,
        coordinates=coordinates,
        axial=dimension - 1,
        radial=0 if measures.is_axisymmetric else None,
        identity=ngs.Id(dimension),
    )

"""The operations and the geometry a term writes with, apart from any finite-element library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from nanopnp.core.typing import Expression
from nanopnp.materials.forms import MathOps

__all__ = ["Geometry", "Operators", "divergence", "hoop", "strain"]


class Operators(MathOps, Protocol):
    """Every product, derivative and elementary function a term may use beyond scalar arithmetic."""

    def grad(self, f: Expression) -> Expression:
        """Return the gradient of ``f``: a vector of a scalar, a tensor of a vector."""

    def hessian(self, f: Expression) -> Expression:
        """Return the tensor of second derivatives of the scalar ``f``."""

    def dot(self, a: Expression, b: Expression) -> Expression:
        """Return the scalar product of two vectors."""

    def inner(self, a: Expression, b: Expression) -> Expression:
        """Return the double contraction ``a : b`` of two tensors."""

    def apply(self, tensor: Expression, vector: Expression) -> Expression:
        """Return the vector ``tensor . vector``."""

    def outer(self, a: Expression, b: Expression) -> Expression:
        """Return the tensor ``a (x) b`` of two vectors."""

    def transpose(self, t: Expression) -> Expression:
        """Return the transpose of the tensor ``t``."""

    def trace(self, t: Expression) -> Expression:
        """Return the trace of the tensor ``t``."""

    def component(self, vector: Expression, index: int) -> Expression:
        """Return one component of ``vector``."""

    def derivative(self, expression: Expression, variable: Expression) -> Expression:
        """Return the derivative of ``expression`` in ``variable``, a field it is written in."""

    def element_size(self) -> Expression:
        """Return ``h_K``, the size of the element a point lies in."""


@dataclass(frozen=True)
class Geometry:
    """The dimension and the directions a term reads, so that no term assumes them.

    Parameters
    ----------
    coordinates
        One expression per coordinate, in the mesh's order.
    axial
        The index of the axial direction.
    radial
        The index of the radial direction under the axisymmetric measure; None in planar geometry.
    identity
        The identity tensor of the dimension.
    """

    dimension: int
    coordinates: tuple[Expression, ...]
    axial: int
    radial: int | None
    identity: Expression


def strain(ops: Operators, w: Expression) -> Expression:
    """Return the in-plane rate-of-strain tensor ``eps(w) = sym grad(w)``."""
    gradient = ops.grad(w)
    return 0.5 * (gradient + ops.transpose(gradient))


def hoop(ops: Operators, geometry: Geometry, w: Expression) -> Expression | None:
    """Return the hoop part ``w_r / r`` of a divergence; None without a radial direction."""
    if geometry.radial is None:
        return None
    return ops.component(w, geometry.radial) / geometry.coordinates[geometry.radial]


def divergence(ops: Operators, geometry: Geometry, w: Expression) -> Expression:
    """Return the divergence of ``w``: the trace of its gradient, plus the hoop part if any."""
    planar = ops.trace(ops.grad(w))
    radial = hoop(ops, geometry, w)
    return planar if radial is None else planar + radial

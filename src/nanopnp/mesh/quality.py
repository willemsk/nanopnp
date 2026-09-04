"""Element quality gates: SICN, gamma, and the sign of the Jacobian (VER-10, QR-12).

Section 5.2.2 asks for a minimum element quality above 0.3 on every mesh the
solver runs on, and VER-10 makes it a gate rather than a report: a mesh that
fails aborts the run naming the gate, the offending quantity and where it is
(QR-12). Nothing here is advisory.

**Two measures, both gated.** For a straight-sided triangle ``p0, p1, p2`` let
``A = [p1 - p0, p2 - p0]`` be the Jacobian of the affine map from the unit
triangle, ``E = [[1, 1/2], [0, sqrt(3)/2]]`` the same for the unit equilateral,
and ``J = A E^-1``. Then

.. code-block:: text

    SICN  = sign(det J) . 2 / (|J|_F |J^-1|_F) = 2 det J / |J|_F^2
    gamma = 2 r_in / R_circ = 8 A^2 / (s . a . b . c),   s = (a + b + c) / 2

both 1 on the equilateral element and both scale-invariant. The closed form on
the right of the SICN line is exact for 2x2: the adjugate has the same Frobenius
norm as the matrix, so ``|J|_F |J^-1|_F = |J|_F^2 / |det J|`` and the absolute
values cancel against the sign.

They are **not** interchangeable, which is why "min SICN/gamma > 0.3" is read
here as a conjunction. On the isoceles family with unit base, ``SICN = 0.3`` at
height 0.132966, where ``gamma = 0.129841``; ``gamma = 0.3`` at height 0.215508,
where ``SICN = 0.468673`` [verified]. Reading the gate off either measure alone
admits meshes the other rejects, by a factor of 1.56 in element height.

**gamma cannot see an inverted element**: an equilateral triangle wound
clockwise scores ``gamma = +1`` and ``SICN = -1``. In an axisymmetric ``(r, z)``
mesh that matters more than in a planar one — a negative-Jacobian element
contributes negative area under the ``r`` weight and nothing else complains — so
``SICN <= 0`` is reported under its own name, ``inverted element``, and not as a
quality figure that happens to be low.

The formulas agree with ``gmsh.model.mesh.getElementQualities(..., "minSICN")``
and ``"gamma"`` to every digit gmsh prints [tested], so the 0.3 threshold is
calibrated against the implementation that set it — without putting gmsh on the
default path (CON-10). gmsh returns ``+1`` for the clockwise triangle: a 2-D
element in a discrete entity has no intrinsic orientation there, so the sign is
ours and only the magnitude is comparable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.mesh.adapter import MeshData

QUALITY_FLOOR = 0.3
"""Minimum element quality, on both measures (section 5.2.2, VER-10).

A module constant and not a case field. Adding the knob later is a compatible
change and removing it is not, and a gate a case file can relax is a gate that
gets relaxed to make a bad mesh pass. If a real case ever needs the escape hatch
it is a CLI flag that taints the manifest, not a line in the case.
"""


class MeshQualityError(ValueError):
    """A mesh fails a geometric gate, naming the gate, the quantity and where.

    Parameters
    ----------
    gate
        The gate that failed, e.g. ``"minimum SICN"``.
    quantity
        The offending value, formatted.
    location
        Where it is: the element index and its ``(r, z)`` centroid.
    detail
        What to do about it, when there is something useful to say.

    Attributes are kept beside the message so that a caller — the GUI's error
    panel, a sweep's failure record — can render the three parts separately
    (QR-12).
    """

    def __init__(self, gate: str, quantity: str, location: str, detail: str = "") -> None:
        self.gate = gate
        self.quantity = quantity
        self.location = location
        self.detail = detail
        message = f"mesh quality gate {gate!r} failed: {quantity} at {location}"
        super().__init__(f"{message}; {detail}" if detail else message)


@dataclass(frozen=True)
class QualityReport:
    """Per-element quality of one mesh, and the extrema a manifest records.

    Parameters
    ----------
    element_count
        Number of triangles measured.
    sicn, gamma
        Per-element arrays, in element order.
    inverted
        Indices of elements with ``SICN <= 0``, in ascending order.
    centroids
        ``(m, 2)`` array of element centroids in nm, so that a failure can say
        *where* rather than only *which*.
    """

    element_count: int
    sicn: np.ndarray
    gamma: np.ndarray
    inverted: tuple[int, ...]
    centroids: np.ndarray

    @property
    def min_sicn(self) -> float:
        """Smallest SICN over the mesh."""
        return float(self.sicn.min())

    @property
    def mean_sicn(self) -> float:
        """Mean SICN over the mesh."""
        return float(self.sicn.mean())

    @property
    def min_gamma(self) -> float:
        """Smallest gamma over the mesh."""
        return float(self.gamma.min())

    @property
    def mean_gamma(self) -> float:
        """Mean gamma over the mesh."""
        return float(self.gamma.mean())

    @property
    def worst_sicn_element(self) -> int:
        """Index of the element with the smallest SICN."""
        import numpy as np

        return int(np.argmin(self.sicn))

    @property
    def worst_gamma_element(self) -> int:
        """Index of the element with the smallest gamma."""
        import numpy as np

        return int(np.argmin(self.gamma))

    def centroid(self, element: int) -> tuple[float, float]:
        """Return the ``(r, z)`` centroid of one element, in nm."""
        return float(self.centroids[element, 0]), float(self.centroids[element, 1])

    def summary(self) -> dict[str, object]:
        """Return the figures the provenance manifest carries (FR-25, section 5.2.2)."""
        return {
            "elements": self.element_count,
            "min_sicn": self.min_sicn,
            "mean_sicn": self.mean_sicn,
            "min_gamma": self.min_gamma,
            "mean_gamma": self.mean_gamma,
            "inverted": len(self.inverted),
            "floor": QUALITY_FLOOR,
        }


def element_quality(data: MeshData) -> QualityReport:
    """Return the SICN and gamma of every triangle of ``data``.

    Parameters
    ----------
    data
        The tagged mesh. Only its vertices and triangles are read.

    Returns
    -------
    QualityReport
        Per-element arrays in element order, with the centroids beside them.

    Notes
    -----
    A degenerate element — zero area, or two coincident vertices — scores 0 on
    both measures rather than dividing by zero, and fails the gate on the same
    line as a merely bad one.
    """
    import numpy as np

    points = data.vertices[data.triangles]  # (m, 3, 2)
    edge_1 = points[:, 1] - points[:, 0]
    edge_2 = points[:, 2] - points[:, 0]

    # J = A E^-1 with A = [edge_1, edge_2] as columns; E^-1 = [[1, -1/sqrt(3)],
    # [0, 2/sqrt(3)]], so det J = det A * 2/sqrt(3) and the columns of J are
    # edge_1 and (2 * edge_2 - edge_1) / sqrt(3).
    root_three = np.sqrt(3.0)
    det_a = edge_1[:, 0] * edge_2[:, 1] - edge_1[:, 1] * edge_2[:, 0]
    det_j = det_a * 2.0 / root_three
    column_2 = (2.0 * edge_2 - edge_1) / root_three
    frobenius = (edge_1**2).sum(axis=1) + (column_2**2).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        sicn = np.where(frobenius > 0.0, 2.0 * det_j / frobenius, 0.0)

    a = np.linalg.norm(points[:, 1] - points[:, 0], axis=1)
    b = np.linalg.norm(points[:, 2] - points[:, 1], axis=1)
    c = np.linalg.norm(points[:, 0] - points[:, 2], axis=1)
    area = 0.5 * np.abs(det_a)
    semi = 0.5 * (a + b + c)
    denominator = semi * a * b * c
    with np.errstate(divide="ignore", invalid="ignore"):
        gamma = np.where(denominator > 0.0, 8.0 * area**2 / denominator, 0.0)

    return QualityReport(
        element_count=int(data.triangles.shape[0]),
        sicn=np.nan_to_num(sicn),
        gamma=np.nan_to_num(gamma),
        inverted=tuple(int(index) for index in np.flatnonzero(sicn <= 0.0)),
        centroids=points.mean(axis=1),
    )


def inverted_elements(data: MeshData) -> tuple[int, ...]:
    """Return the indices of elements whose Jacobian determinant is not positive."""
    return element_quality(data).inverted


def check_quality(
    data: MeshData, *, floor: float = QUALITY_FLOOR, where: str = "this mesh"
) -> QualityReport:
    """Gate ``data`` on both quality measures and return the report (VER-10).

    Parameters
    ----------
    data
        The tagged mesh.
    floor
        The gate. Defaults to :data:`QUALITY_FLOOR` and is a parameter only so
        that a test can drive the failure path with a mesh it built on purpose.
    where
        What to call the mesh in a diagnostic — a filename, or the geometry that
        produced it.

    Returns
    -------
    QualityReport
        The report, when every element passes.

    Raises
    ------
    MeshQualityError
        If any element is inverted, or if either measure falls to or below
        ``floor``. Inversion is checked first and reported under its own name:
        gamma is blind to it, so a mesh could otherwise be turned away for a low
        number when the real fault is an element wound the wrong way.
    """
    import numpy as np

    report = element_quality(data)
    if report.inverted:
        worst = report.inverted[0]
        r, z = report.centroid(worst)
        raise MeshQualityError(
            gate="inverted element",
            quantity=f"{len(report.inverted)} element(s) with SICN <= 0, first "
            f"{report.sicn[worst]:.6g}",
            location=f"element {worst} of {where}, centroid (r, z) = ({r:.6g}, {z:.6g}) nm",
            detail="an element wound clockwise contributes negative area under the r weight of "
            "the axisymmetric forms and nothing downstream complains (NUM-01)",
        )
    for name, values in (("minimum SICN", report.sicn), ("minimum gamma", report.gamma)):
        worst = int(np.argmin(values))
        value = float(values[worst])
        if value <= floor:
            r, z = report.centroid(worst)
            raise MeshQualityError(
                gate=name,
                quantity=f"{value:.6g}, at or below the floor of {floor:g}",
                location=f"element {worst} of {where}, centroid (r, z) = ({r:.6g}, {z:.6g}) nm",
                detail="section 5.2.2 requires minimum element quality above 0.3 on both SICN and "
                "gamma; refine or re-mesh around that location",
            )
    return report


def check_radii(data: MeshData, *, where: str = "this mesh") -> None:
    """Reject a mesh with a vertex at negative radius.

    An ``(r, z)`` mesh crossing ``r = 0`` integrates to negative volume under the
    ``r`` weight of the axisymmetric forms, and the ``1/r`` terms of the
    Nernst-Planck and Navier-Stokes forms are worse: they change sign rather than
    growing, so the solve converges to something with no diagnostic attached.

    Raises
    ------
    MeshQualityError
        If any vertex has ``r < 0``, naming the vertex and its coordinates.
    """
    import numpy as np

    radii = data.vertices[:, 0]
    if not radii.size or float(radii.min()) >= 0.0:
        return
    worst = int(np.argmin(radii))
    raise MeshQualityError(
        gate="negative radius",
        quantity=f"r = {float(radii[worst]):.6g} nm",
        location=f"vertex {worst} of {where}, (r, z) = "
        f"({float(data.vertices[worst, 0]):.6g}, {float(data.vertices[worst, 1]):.6g}) nm",
        detail="nanopnp solves the half-plane r >= 0; a mesh mirrored about the axis integrates "
        "to negative volume under the r weight (CON-04, NUM-01)",
    )

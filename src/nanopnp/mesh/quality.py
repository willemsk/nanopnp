"""Element quality gates: SICN, gamma, and the sign of the Jacobian (VER-10, QR-12)."""

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
    def __init__(self, gate: str, quantity: str, location: str, detail: str = "") -> None:
        self.gate = gate
        self.quantity = quantity
        self.location = location
        self.detail = detail
        message = f"mesh quality gate {gate!r} failed: {quantity} at {location}"
        super().__init__(f"{message}; {detail}" if detail else message)


@dataclass(frozen=True)
class QualityReport:
    element_count: int
    sicn: np.ndarray
    gamma: np.ndarray
    inverted: tuple[int, ...]
    centroids: np.ndarray

    @property
    def min_sicn(self) -> float:
        return float(self.sicn.min())

    @property
    def mean_sicn(self) -> float:
        return float(self.sicn.mean())

    @property
    def min_gamma(self) -> float:
        return float(self.gamma.min())

    @property
    def mean_gamma(self) -> float:
        return float(self.gamma.mean())

    @property
    def worst_sicn_element(self) -> int:
        import numpy as np

        return int(np.argmin(self.sicn))

    @property
    def worst_gamma_element(self) -> int:
        import numpy as np

        return int(np.argmin(self.gamma))

    def centroid(self, element: int) -> tuple[float, float]:
        return float(self.centroids[element, 0]), float(self.centroids[element, 1])

    def summary(self) -> dict[str, object]:
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
    return element_quality(data).inverted


def check_quality(
    data: MeshData, *, floor: float = QUALITY_FLOOR, where: str = "this mesh"
) -> QualityReport:
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
        if not value > floor:
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

"""Price a 3D check: VER-13 solved in 3D, VER-17's fluid meshed, and the places written for 2D.

Run ``uv run python prototype/three_d.py``. It gates nothing (WP6.09 D6) and prints what it
measured.
"""

from __future__ import annotations

import math
import time

import netgen.occ as occ
import ngsolve as ngs
import numpy as np
from scipy.special import i0

from nanopnp.core.typing import GridFunction, Mesh
from nanopnp.mesh.adapter import MeshFormatError, from_ngsolve
from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.measures import AXISYMMETRIC, PLANAR
from nanopnp.physics.pb import solve_pb_recorded

RADIUS_NM = 2.0
LENGTH_NM = 4.0
DEBYE_NM = 0.5
ZETA = 1.0
MAXH_NM = 0.4
SAMPLES = np.linspace(0.0, RADIUS_NM, 201)
EXACT = ZETA * i0(SAMPLES / DEBYE_NM) / i0(RADIUS_NM / DEBYE_NM)
WEIGHTS = np.maximum(SAMPLES, 1e-12)

PORE_RADIUS_NM = 2.0
MEMBRANE_THICKNESS_NM = 13.0
RESERVOIR_RADIUS_NM = 50.0
WALL_H_NM = 0.5

# Where the code writes two dimensions and no run below reaches it.
STATIC_PLACES = (
    "mesh/primitives.py (5 calls), mesh/meshers.py:56, mesh/idealised.py:49, "
    "geometry/analyte.py:215: OCCGeometry(..., dim=2), so no 3D mesh is generated",
    "mesh/adapter.py: MeshData holds (r, z) vertices and triangles; to_ngsolve builds "
    "NetgenMesh(dim=2); _read_meshio refuses a third coordinate (CON-04)",
    "numerics/measures.py: Symmetry has two values; coordinate_names two names; "
    "AXISYMMETRIC weights by ngs.x on any mesh, a 3D one included, without a refusal",
    "physics/flow.py: the velocity is a two-vector (CF((0, 0)) at 147); the hoop term "
    "u_r/r of the divergence and the viscous form is axisymmetric alone; kernel.py:598 too",
    "physics/stabilisation.py:223 and post/forces.py:214, 225: ngs.Id(2)",
    "post/forces.py:127, 662: the axial direction is the second component, (x, y) the position",
    "post/indicator.py:85: the axial coordinate is ngs.y",
)


def _weighted_error(solution: GridFunction, mesh: Mesh, *, three_d: bool) -> tuple[float, int]:
    """Return the r-weighted relative L2 error along a radius at mid-height, and points missed."""
    values = []
    weights = []
    exact = []
    missed = 0
    z = 0.5 * LENGTH_NM
    for r, w, e in zip(SAMPLES, WEIGHTS, EXACT, strict=True):
        point = mesh(float(r), 0.0, z) if three_d else mesh(float(r), z)
        if point.nr < 0:
            missed += 1
            continue
        values.append(solution(point))
        weights.append(w)
        exact.append(e)
    computed = np.asarray(values)
    weight = np.asarray(weights)
    reference = np.asarray(exact)
    error = math.sqrt(float(np.sum(weight * (computed - reference) ** 2)))
    return error / math.sqrt(float(np.sum(weight * reference**2))), missed


def _solve(mesh: Mesh, *, planar: bool) -> tuple[GridFunction, float]:
    start = time.perf_counter()
    solution = solve_pb_recorded(
        mesh,
        PLANAR if planar else AXISYMMETRIC,
        debye_length_nm=DEBYE_NM,
        dirichlet="wall",
        boundary_values=ngs.CF(ZETA),
        nonlinear=False,
    )[0]
    return solution, time.perf_counter() - start


def _ver13_three_d() -> Mesh:
    start = time.perf_counter()
    cylinder = occ.Cylinder(occ.Pnt(0, 0, 0), occ.Z, r=RADIUS_NM, h=LENGTH_NM)
    cylinder.solids[0].name = "electrolyte"
    for face in cylinder.faces:
        z = face.center[2]
        on_end = abs(z) < 1e-9 or abs(z - LENGTH_NM) < 1e-9
        face.name = "end" if on_end else "wall"
    mesh = ngs.Mesh(occ.OCCGeometry(cylinder).GenerateMesh(maxh=MAXH_NM))
    mesh.Curve(2)
    meshed = time.perf_counter() - start
    solution, solved = _solve(mesh, planar=True)
    error, missed = _weighted_error(solution, mesh, three_d=True)
    print(
        f"VER-13 3D: {mesh.ne} tetrahedra, {solution.space.ndof} unknowns, mesh {meshed:.2f} s, "
        f"solve {solved:.2f} s, relative error {error:.3e} ({missed} of {SAMPLES.size} points "
        "outside the mesh)"
    )

    flat = CylinderGeometry(radius_nm=RADIUS_NM, length_nm=LENGTH_NM).generate(maxh_nm=MAXH_NM)
    flat_solution, flat_solved = _solve(flat, planar=False)
    flat_error, flat_missed = _weighted_error(flat_solution, flat, three_d=False)
    print(
        f"VER-13 2D: {flat.ne} triangles, {flat_solution.space.ndof} unknowns, "
        f"solve {flat_solved:.2f} s, relative error {flat_error:.3e} ({flat_missed} missed)"
    )
    return mesh


def _ver17_fluid() -> None:
    start = time.perf_counter()
    half = 0.5 * MEMBRANE_THICKNESS_NM
    lumen = occ.Cylinder(occ.Pnt(0, 0, -half), occ.Z, r=PORE_RADIUS_NM, h=MEMBRANE_THICKNESS_NM)
    lumen.solids[0].name = "electrolyte"
    for face in lumen.faces:
        if abs(abs(face.center[2]) - half) > 1e-9:
            face.name = "wall"
            face.maxh = WALL_H_NM
    reservoirs = []
    side = 2.0 * RESERVOIR_RADIUS_NM
    for name, sign in (("cis", 1.0), ("trans", -1.0)):
        ball = occ.Sphere(occ.Pnt(0, 0, sign * half), RESERVOIR_RADIUS_NM)
        low = half if sign > 0 else -half - RESERVOIR_RADIUS_NM
        box = occ.Box(occ.Pnt(-side, -side, low), occ.Pnt(side, side, low + RESERVOIR_RADIUS_NM))
        reservoir = ball * box
        reservoir.solids[0].name = name
        reservoirs.append(reservoir)
    fluid = occ.Glue([lumen, *reservoirs])
    mesh = ngs.Mesh(
        occ.OCCGeometry(fluid).GenerateMesh(maxh=RESERVOIR_RADIUS_NM / 12.0, grading=0.2)
    )
    meshed = time.perf_counter() - start
    space = ngs.H1(mesh, order=2)
    print(
        f"VER-17 fluid 3D, reservoirs {RESERVOIR_RADIUS_NM:g} nm: {mesh.ne} tetrahedra, "
        f"mesh {meshed:.1f} s, order-2 H1 {space.ndof} dofs, three fields {3 * space.ndof} "
        "unknowns (not solved)"
    )


def _rule_order_on_tetrahedra(mesh: Mesh) -> float:
    """Return how far a rule_order integral moves when the tetrahedron's rule is given."""
    space = ngs.H1(mesh, order=2)
    test = space.TestFunction()
    integrand = ngs.x**8 * ngs.y**6 * ngs.z**4 * test
    order = 20
    today = ngs.LinearForm(PLANAR.volume(integrand, rule_order=order)).Assemble()
    explicit = ngs.LinearForm(
        integrand * ngs.dx(intrules={ngs.TET: ngs.IntegrationRule(ngs.TET, order)})
    ).Assemble()
    old = today.vec.FV().NumPy()
    new = explicit.vec.FV().NumPy()
    return float(np.max(np.abs(old - new)) / np.max(np.abs(new)))


def main() -> int:
    mesh = _ver13_three_d()
    _ver17_fluid()
    print("Places that refuse or mishandle a 3D mesh:")
    try:
        from_ngsolve(mesh)
        print("  mesh/adapter.py:from_ngsolve: accepted the 3D mesh")
    except MeshFormatError as error:
        print(f"  mesh/adapter.py:from_ngsolve, so every mesh quality gate: refused: {error}")
    moved = _rule_order_on_tetrahedra(mesh)
    print(
        "  numerics/measures.py:Measures.volume(rule_order=20) on tetrahedra: no TET rule, "
        f"NGSolve's estimate instead; an explicit TET rule moves the vector by {moved:.3e}"
    )
    for place in STATIC_PLACES:
        print(f"  {place}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

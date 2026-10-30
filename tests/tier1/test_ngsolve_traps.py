"""Tier-1 verification of NGSolve traps, workarounds and gate constants (VER-68, K8)."""

from __future__ import annotations

import gc
import inspect
import math
import os
import platform
import subprocess
import sys
import weakref

import ngsolve as ngs
import numpy as np
import pytest
from netgen.geom2d import unit_square
from ngsolve.meshes import MakeStructured2DMesh

from nanopnp.api import sweep as sweep_run
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.primitives import CylindricalPoreGeometry, SlabGeometry
from nanopnp.numerics.gates import (
    INTERIOR_OFFSET,
    MINIMUM_WALL_DISTANCE_NM,
    PACKING_WARNING,
    FieldSampler,
)
from nanopnp.numerics.linear import create_solver, to_scipy
from nanopnp.numerics.measures import AXISYMMETRIC, PLANAR
from nanopnp.physics.pb import debye_length_nm, nonlinear_pb_residual, solve_pb_recorded
from nanopnp.post.reaction_flux import boundary_reaction_flux


def test_ngsolve_traps_1_2_and_7_trial_function_p2_indicator_and_components() -> None:
    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    fes = ngs.H1(mesh, order=2, dirichlet="bottom|left")
    u, v = fes.TnT()
    gfu = ngs.GridFunction(fes)
    gfu.Set(ngs.x + ngs.y)

    a_wrong = ngs.BilinearForm(fes)
    a_wrong += (ngs.grad(gfu) * ngs.grad(v) + ngs.sinh(gfu) * v) * ngs.dx
    a_wrong.AssembleLinearization(gfu.vec)
    assert np.all(to_scipy(a_wrong.mat).data == 0.0)

    a_right = ngs.BilinearForm(fes)
    a_right += (ngs.grad(u) * ngs.grad(v) + ngs.sinh(u) * v) * ngs.dx
    a_right.AssembleLinearization(gfu.vec)
    assert float(np.linalg.norm(to_scipy(a_right.mat).data)) > 1.0

    psi_bad = ngs.GridFunction(fes)
    bnd_dofs = fes.GetDofs(mesh.Boundaries("bottom"))
    for idx in range(fes.ndof):
        if bnd_dofs[idx]:
            psi_bad.vec[idx] = 1.0
    val_bad = float(ngs.Integrate(psi_bad, mesh, ngs.BND, definedon=mesh.Boundaries("bottom")))
    assert val_bad == pytest.approx(11.0 / 12.0, rel=1e-12)
    assert (1.0 - val_bad) == pytest.approx(1.0 / 12.0, rel=1e-12)

    psi_good = ngs.GridFunction(fes)
    psi_good.Set(ngs.CF(1.0), definedon=mesh.Boundaries("bottom"))
    val_good = float(ngs.Integrate(psi_good, mesh, ngs.BND, definedon=mesh.Boundaries("bottom")))
    assert val_good == pytest.approx(1.0, rel=1e-12)

    with pytest.raises(Exception, match="components only available for ProductSpace"):
        getattr(fes, "components", None)


def test_ngsolve_trap_3_set_projection_and_dof_zeroing() -> None:
    mesh = SlabGeometry(width_nm=1.0, height_nm=1.0).generate(maxh_nm=0.5)
    fes = ngs.H1(mesh, order=2, dirichlet="wall")
    gf = ngs.GridFunction(fes)
    cf = -0.2 * ngs.log(ngs.exp(-ngs.x / 0.2))
    gf.Set(cf)
    assert float(cf(mesh(0.0, 0.5))) == pytest.approx(0.0, abs=1e-15)
    wall_dofs = fes.GetDofs(mesh.Boundaries("wall"))
    wall_mask = np.array(wall_dofs)
    for idx in range(fes.ndof):
        if wall_dofs[idx]:
            gf.vec[idx] = 0.0
    assert bool(np.all(gf.vec.FV().NumPy()[wall_mask] == 0.0))


def test_ngsolve_trap_4_integrate_order_replaces_default_five() -> None:
    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    low_order = float(ngs.Integrate(ngs.x**4, mesh, order=2))
    default_order = float(ngs.Integrate(ngs.x**4, mesh))
    wrapped = PLANAR.integrate(ngs.x**4, mesh, extra_order=0)
    assert abs(low_order - 0.2) > 1e-4
    assert default_order == pytest.approx(0.2, abs=1e-14)
    assert wrapped == pytest.approx(0.2, abs=1e-14)


def test_ngsolve_trap_6_reaction_flux_subtracts_load_form() -> None:
    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.25))
    fes = ngs.H1(mesh, order=2, dirichlet="bottom|left")
    u, v = fes.TnT()
    a = ngs.BilinearForm(fes)
    a += ngs.grad(u) * ngs.grad(v) * ngs.dx
    a.Assemble()
    f = ngs.LinearForm(fes)
    f += 1.0 * v * ngs.dx
    f.Assemble()
    gfu = ngs.GridFunction(fes)
    gfu.vec.data = a.mat.Inverse(fes.FreeDofs(), inverse="umfpack") * f.vec

    psi = ngs.GridFunction(fes)
    psi.Set(ngs.CF(1.0), definedon=mesh.Boundaries("bottom|left"))
    flux_without_f = float(ngs.InnerProduct(a.mat * gfu.vec, psi.vec))
    flux_with_f = boundary_reaction_flux(a, gfu, "bottom|left", load_form=f)
    assert flux_without_f != pytest.approx(-1.0, abs=0.05)
    assert flux_with_f == pytest.approx(-1.0, abs=1e-12)

    psi_free = ngs.GridFunction(fes)
    psi_free.Set(ngs.CF(1.0), definedon=mesh.Boundaries("top"))
    res_vec = f.vec.CreateVector()
    res_vec.data = a.mat * gfu.vec - f.vec
    assert abs(float(ngs.InnerProduct(res_vec, psi_free.vec))) > 1e-2
    with pytest.raises(ValueError, match="are free"):
        boundary_reaction_flux(a, gfu, "top", load_form=f)


def test_ngsolve_traps_8_and_9_superlu_registration_and_singular_factorisation() -> None:
    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    fes = ngs.H1(mesh, order=2, dirichlet="bottom|left")
    u, v = fes.TnT()
    a = ngs.BilinearForm(fes)
    a += ngs.grad(u) * ngs.grad(v) * ngs.dx
    a.Assemble()
    f = ngs.LinearForm(fes)
    f += 1.0 * v * ngs.dx
    f.Assemble()

    vec_ngs = f.vec.CreateVector()
    vec_ngs.data = a.mat.Inverse(fes.FreeDofs(), inverse="superlu") * f.vec
    vec_proj = f.vec.CreateVector()
    create_solver("superlu").solve(a.mat, f.vec, vec_proj, fes.FreeDofs())
    assert float(np.max(np.abs(vec_ngs.FV().NumPy() - vec_proj.FV().NumPy()))) < 1e-13

    free_mask = np.array(fes.FreeDofs())
    res_vec = f.vec.CreateVector()
    res_vec.data = a.mat * vec_proj - f.vec
    res_constrained = float(np.linalg.norm(res_vec.FV().NumPy()[free_mask]))
    assert res_constrained < 1e-12

    fes_free = ngs.H1(mesh, order=2)
    u0, v0 = fes_free.TnT()
    a0 = ngs.BilinearForm(fes_free)
    a0 += ngs.grad(u0) * ngs.grad(v0) * ngs.dx
    a0.Assemble()
    f0 = ngs.LinearForm(fes_free)
    f0 += 1.0 * v0 * ngs.dx
    f0.Assemble()
    vec_sing = f0.vec.CreateVector()
    vec_sing.data = a0.mat.Inverse(fes_free.FreeDofs(), inverse="umfpack") * f0.vec
    assert bool(np.isfinite(vec_sing.FV().NumPy()).all())
    res_sing_vec = f0.vec.CreateVector()
    res_sing_vec.data = a0.mat * vec_sing - f0.vec
    res_sing = float(np.linalg.norm(res_sing_vec.FV().NumPy()))
    assert res_sing > 1e-3


def test_ngsolve_traps_10_12_13_14_and_19_forms_and_spaces() -> None:
    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    fes = ngs.H1(mesh, order=2, dirichlet="bottom|left")
    u, v = fes.TnT()

    gf = ngs.GridFunction(fes)
    gf.Set(ngs.CF(2.0))
    before = gf.vec.FV().NumPy().copy()
    gf.Set(ngs.CF(5.0), definedon=mesh.Boundaries("bottom"))
    b_dofs = fes.GetDofs(mesh.Boundaries("bottom"))
    free_mask = ~np.array(b_dofs)
    assert bool(np.all(gf.vec.FV().NumPy()[free_mask] == 0.0))

    gf.Set(ngs.CF(2.0))
    scratch = ngs.GridFunction(fes)
    scratch.Set(ngs.CF(5.0), definedon=mesh.Boundaries("bottom"))
    gf.vec.data = ngs.Projector(b_dofs, False) * gf.vec + ngs.Projector(b_dofs, True) * scratch.vec
    assert np.allclose(gf.vec.FV().NumPy()[free_mask], before[free_mask])
    assert float(gf(mesh(0.5, 0.0))) == pytest.approx(5.0)
    assert float(gf(mesh(0.5, 1.0))) == pytest.approx(2.0)

    prod = ngs.FESpace([fes, fes])
    gf_prod = ngs.GridFunction(prod)
    with pytest.raises(Exception, match="CompoundFESpace does not have an evaluator for BND"):
        gf_prod.Set(ngs.CF((1.0, 0.0)), definedon=mesh.Boundaries("bottom"))
    gf_prod.components[0].Set(ngs.CF(1.0), definedon=mesh.Boundaries("bottom"))

    gfu = ngs.GridFunction(fes)
    gfu.Set(ngs.y)
    bnd = mesh.Boundaries("bottom")
    trace_dy = float(ngs.Integrate(ngs.grad(gfu)[1], mesh, ngs.BND, definedon=bnd))
    lifted_dy = float(
        ngs.Integrate(ngs.BoundaryFromVolumeCF(ngs.grad(gfu))[1], mesh, ngs.BND, definedon=bnd)
    )
    assert abs(trace_dy) < 1e-12
    assert lifted_dy == pytest.approx(1.0, rel=1e-12)
    assert not hasattr(ngs, "BoundaryCF")
    assert hasattr(mesh, "BoundaryCF")

    with pytest.raises(Exception, match="Linearform must have TestFunction"):
        ngs.LinearForm(ngs.CF(1.0) * ngs.dx)
    lf = ngs.LinearForm(fes)
    lf += 1.0 * v * ngs.dx
    lf.Assemble()

    g_zero = ngs.GridFunction(fes)
    g_zero.vec[:] = 0.0
    a_nan = ngs.BilinearForm(fes)
    a_nan += ngs.sqrt(ngs.grad(g_zero) * ngs.grad(g_zero)) * u * v * ngs.dx
    a_nan.Assemble()
    assert not bool(np.isnan(to_scipy(a_nan.mat).data).any())
    a_nan.AssembleLinearization(g_zero.vec)
    assert bool(np.isnan(to_scipy(a_nan.mat).data).all())

    eps = 1e-30
    a_floor = ngs.BilinearForm(fes)
    a_floor += ngs.sqrt(ngs.grad(g_zero) * ngs.grad(g_zero) + eps**2) * u * v * ngs.dx
    a_floor.AssembleLinearization(g_zero.vec)
    assert not bool(np.isnan(to_scipy(a_floor.mat).data).any())


def test_ngsolve_traps_15_16_17_18_and_occ_extent() -> None:
    vertices = np.array([[0.0, 0.0], [1.0, 0.0], [-5e-15, 1.0]], dtype=np.float64)
    triangles = np.array([[0, 1, 2]], dtype=np.int64)
    edges = np.array([[0, 1], [1, 2], [2, 0]], dtype=np.int64)
    data = MeshData(
        vertices=vertices,
        triangles=triangles,
        triangle_material=np.array([0], dtype=np.int64),
        materials=("fluid",),
        edges=edges,
        edge_group=np.array([0, 0, 1], dtype=np.int64),
        boundaries=("wall", "axis"),
    )
    assert data.vertices[2, 0] == 0.0

    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    r_grid = np.array([0.0, 1.0], dtype=np.float64)
    z_grid = np.array([0.0, 1.0], dtype=np.float64)
    values_rz = 10.0 * r_grid[:, None] + z_grid[None, :]
    vc_wrong = ngs.VoxelCoefficient((0.0, 0.0), (1.0, 1.0), values_rz, linear=True)
    vc_right = ngs.VoxelCoefficient((0.0, 0.0), (1.0, 1.0), values_rz.T.copy(), linear=True)
    assert float(vc_wrong(mesh(1.0, 0.0))) == pytest.approx(1.0)
    assert float(vc_right(mesh(1.0, 0.0))) == pytest.approx(10.0)
    assert float(vc_wrong(mesh(0.5, 0.5))) == pytest.approx(float(vc_right(mesh(0.5, 0.5))))
    assert float(vc_right(mesh(1.0, 1.0))) == pytest.approx(11.0)

    assert AXISYMMETRIC.bonus_order(singular=True, extra=0) == 3
    assert AXISYMMETRIC.bonus_order(singular=True, extra=3) == 3
    assert AXISYMMETRIC.bonus_order(singular=True, extra=6) == 6

    pore_mesh = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0)
    pts = np.array([v.point for v in pore_mesh.vertices])
    assert float(np.max(pts[:, 1])) == pytest.approx(13.0, abs=1e-12)


def test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts() -> None:
    assert ngs.config.USE_UMFPACK is True
    assert ngs.config.USE_MUMPS is False
    assert ngs.config.USE_PARDISO is False
    assert ngs.config.USE_MKL is False

    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    fes = ngs.H1(mesh, order=2, dirichlet="bottom")
    u, v = fes.TnT()
    a = ngs.BilinearForm(fes)
    a += ngs.grad(u) * ngs.grad(v) * ngs.dx
    a.Assemble()
    with pytest.raises(Exception, match="MKL Pardiso is not available"):
        a.mat.Inverse(fes.FreeDofs(), inverse="pardiso")

    prod = ngs.FESpace([fes, fes])
    u0, _ = prod.TrialFunction()
    gf_prod = ngs.GridFunction(prod)
    assert u0.Operator("hesse") is not None
    assert (gf_prod.components[0] ** 2).Diff(gf_prod.components[0]) is not None
    assert (u0**2).Diff(u0) is not None

    g_zero = ngs.GridFunction(fes)
    g_zero.vec[:] = 0.0
    a_src = ngs.BilinearForm(fes)
    a_src += (ngs.grad(u) * ngs.grad(v) - 3.0 * v) * ngs.dx
    res_vec = g_zero.vec.CreateVector()
    a_src.Apply(g_zero.vec, res_vec)
    assert float(np.linalg.norm(res_vec.FV().NumPy())) > 0.0
    a_src.AssembleLinearization(g_zero.vec)
    assert np.allclose(to_scipy(a_src.mat).toarray(), to_scipy(a.mat).toarray())

    lam = debye_length_nm(0.1)
    zeta = 2.0
    exact_grad = (2.0 / lam) * math.sinh(0.5 * zeta)
    gmesh = SlabGeometry(width_nm=15.0 * lam, height_nm=lam).generate(maxh_nm=lam / 4.0)
    sol = solve_pb_recorded(
        gmesh,
        PLANAR,
        debye_length_nm=lam,
        dirichlet="wall|bulk",
        boundary_values=gmesh.BoundaryCF({"wall": zeta, "bulk": 0.0}),
        nonlinear=True,
    )[0]
    res = ngs.BilinearForm(sol.space)
    tr, te = sol.space.TnT()
    res += nonlinear_pb_residual(tr, te, PLANAR, debye_length_nm=lam)
    flux_grad = boundary_reaction_flux(res, sol, "wall") / lam
    pw_grad = -float(ngs.grad(sol)(gmesh(0.0, 0.5 * lam))[0])
    err_flux = abs(flux_grad - exact_grad) / exact_grad
    err_pw = abs(pw_grad - exact_grad) / exact_grad
    assert err_flux < 1e-4
    assert 1e-3 < err_pw < 5e-2
    assert err_pw > 10.0 * err_flux


def test_ngsolve_trap_structured_mesh_cpu_features_sampler_and_gate_constants() -> None:
    smesh1 = MakeStructured2DMesh(quads=False, nx=5, ny=5)
    smesh2 = MakeStructured2DMesh(quads=False, nx=5, ny=5)
    c1 = np.array([v.point for v in smesh1.vertices])
    c2 = np.array([v.point for v in smesh2.vertices])
    assert np.array_equal(c1, c2)

    disabled = "X86_V4" if platform.machine().lower().startswith(("arm", "aarch")) else "NEON ASIMD"
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import numpy._core._multiarray_umath as m; assert m.__cpu_features__",
        ],
        env={**os.environ, "NPY_DISABLE_CPU_FEATURES": disabled},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0

    wkd: weakref.WeakKeyDictionary[object, int] = weakref.WeakKeyDictionary()
    with pytest.raises(TypeError):
        wkd[smesh1] = 1

    def _build_sampler() -> tuple[weakref.ReferenceType[object], weakref.ReferenceType[object]]:
        m = MakeStructured2DMesh(quads=False, nx=2, ny=2)
        s1 = FieldSampler.shared(m)
        s2 = FieldSampler.shared(m)
        assert s1 is s2
        return weakref.ref(m), weakref.ref(s1)

    ref_m, ref_s = _build_sampler()
    gc.collect()
    assert ref_m() is None and ref_s() is None

    assert INTERIOR_OFFSET == 1e-4
    assert PACKING_WARNING == 0.8
    assert MINIMUM_WALL_DISTANCE_NM == -1e-3
    unclamped = 1.0 - math.exp(-6.2 * (-1e-3 + 0.01))
    clamped = 1.0 - math.exp(-6.2 * 0.01)
    assert round(unclamped, 4) == 0.0543
    assert round(clamped, 4) == 0.0601
    assert round(clamped - unclamped, 4) == 0.0058
    lam_3m = debye_length_nm(3.0)
    assert (2.0 / lam_3m) ** 2 == pytest.approx(130.0, rel=0.02)

    src_run = inspect.getsource(sweep_run.run_plan)
    src_pool = inspect.getsource(sweep_run._pool)
    assert "with _pool(plan, directory, workers=workers) as run_wave:" in src_run
    assert "with context.Pool(processes=workers, initializer=pin_threads) as pool:" in src_pool

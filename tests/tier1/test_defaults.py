"""Parity tests for domain defaults (mesh/defaults.py and numerics/defaults.py)."""

from __future__ import annotations

from nanopnp.cli import build_parser
from nanopnp.io.case import (
    ElementsSpec,
    LinearSpec,
    MembraneSpec,
    NonlinearSpec,
    NumericsSpec,
    ReservoirSpec,
    WallDistanceSpec,
)
from nanopnp.io.defaults import _VALIDATED_DEFAULTS
from nanopnp.mesh.defaults import (
    DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    DEFAULT_CYLINDER_WALL_H_NM,
    DEFAULT_MAXH_NM,
    DEFAULT_MEMBRANE_CENTRE_Z_NM,
    DEFAULT_MEMBRANE_THICKNESS_NM,
    DEFAULT_PORE_RADIUS_NM,
    DEFAULT_RESERVOIR_RADIUS_NM,
    DEFAULT_WALL_H_NM,
)
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.defaults import (
    DEFAULT_CONTINUATION,
    DEFAULT_ELEMENT_ORDER_P,
    DEFAULT_ELEMENT_ORDER_U,
    DEFAULT_ELEMENTS_C,
    DEFAULT_ELEMENTS_P,
    DEFAULT_ELEMENTS_PHI,
    DEFAULT_ELEMENTS_U,
    DEFAULT_LINEAR_SOLVER,
    DEFAULT_NONLINEAR_DAMPING,
    DEFAULT_NONLINEAR_MAX_ITER,
    DEFAULT_NONLINEAR_RTOL,
    DEFAULT_NONLINEAR_STRATEGY,
    DEFAULT_STABILISATION,
    DEFAULT_WALL_DISTANCE_MAX_NM,
    DEFAULT_WALL_DISTANCE_SOURCES,
)
from nanopnp.numerics.newton import NewtonSettings


def test_mesh_defaults_parity() -> None:
    """Mesh defaults match geometry specs, primitives, and CLI cylinder parser."""
    assert CylindricalPoreGeometry().pore_radius_nm == DEFAULT_PORE_RADIUS_NM
    assert MembraneSpec().thickness_nm == DEFAULT_MEMBRANE_THICKNESS_NM
    assert MembraneSpec().centre_z_nm == DEFAULT_MEMBRANE_CENTRE_Z_NM
    assert ReservoirSpec().radius_nm == DEFAULT_RESERVOIR_RADIUS_NM
    assert DEFAULT_WALL_H_NM == 0.2

    parser = build_parser()
    args = parser.parse_args(["mesh", "cylinder", "--out", "test.msh"])
    assert args.pore_radius_nm == DEFAULT_PORE_RADIUS_NM
    assert args.membrane_thickness_nm == DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM
    assert args.reservoir_radius_nm == DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM
    assert args.maxh_nm == DEFAULT_MAXH_NM
    assert args.wall_h_nm == DEFAULT_CYLINDER_WALL_H_NM


def test_numerics_defaults_parity() -> None:
    """Numerics defaults match solver specs, NewtonSettings, and _VALIDATED_DEFAULTS."""
    assert DEFAULT_NONLINEAR_RTOL == NonlinearSpec().rtol == NewtonSettings().relative_tolerance
    assert DEFAULT_NONLINEAR_MAX_ITER == NonlinearSpec().max_iter == NewtonSettings().max_iterations
    assert NonlinearSpec().strategy == DEFAULT_NONLINEAR_STRATEGY
    assert NonlinearSpec().damping == DEFAULT_NONLINEAR_DAMPING
    assert ElementsSpec().u == DEFAULT_ELEMENTS_U
    assert ElementsSpec().p == DEFAULT_ELEMENTS_P
    assert ElementsSpec().phi == DEFAULT_ELEMENTS_PHI
    assert ElementsSpec().c == DEFAULT_ELEMENTS_C
    assert LinearSpec().solver == DEFAULT_LINEAR_SOLVER
    assert NumericsSpec().continuation == DEFAULT_CONTINUATION
    assert NumericsSpec().stabilisation == DEFAULT_STABILISATION
    assert WallDistanceSpec().sources == DEFAULT_WALL_DISTANCE_SOURCES
    assert WallDistanceSpec().max_distance_nm == DEFAULT_WALL_DISTANCE_MAX_NM

    assert DEFAULT_ELEMENT_ORDER_U == 2
    assert DEFAULT_ELEMENT_ORDER_P == 1

    numerics_defaults = _VALIDATED_DEFAULTS["numerics"]
    assert numerics_defaults["elements"]["u"] == DEFAULT_ELEMENTS_U
    assert numerics_defaults["elements"]["p"] == DEFAULT_ELEMENTS_P
    assert numerics_defaults["elements"]["phi"] == DEFAULT_ELEMENTS_PHI
    assert numerics_defaults["elements"]["c"] == DEFAULT_ELEMENTS_C
    assert numerics_defaults["nonlinear"]["strategy"] == DEFAULT_NONLINEAR_STRATEGY
    assert numerics_defaults["nonlinear"]["damping"] == DEFAULT_NONLINEAR_DAMPING
    assert numerics_defaults["continuation"] == DEFAULT_CONTINUATION
    assert numerics_defaults["stabilisation"] == DEFAULT_STABILISATION
    assert numerics_defaults["wall_distance"]["sources"] == DEFAULT_WALL_DISTANCE_SOURCES
    assert numerics_defaults["wall_distance"]["max_distance_nm"] == DEFAULT_WALL_DISTANCE_MAX_NM
    assert numerics_defaults["linear"]["solver"] == DEFAULT_LINEAR_SOLVER

"""Parity tests for domain defaults (mesh/defaults.py and numerics/defaults.py)."""

from __future__ import annotations

from tests.conftest import CASE_SCHEMA, make_case_dict

from nanopnp.cli import build_parser
from nanopnp.io.case import (
    CaseDocument,
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
from nanopnp.pipeline.case import loads_case


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


def test_case_yaml_template_fixture(case_yaml_template: str) -> None:
    """Verifies loads_case(case_yaml_template) parses and validates cleanly to CaseDocument."""
    doc = loads_case(case_yaml_template)
    assert isinstance(doc, CaseDocument)
    assert doc.schema_id == CASE_SCHEMA
    assert doc.name == "minimal"


def test_make_case_dict_helper() -> None:
    """Tests default dict generation and overrides (both top-level and dotted paths)."""
    base = make_case_dict()
    assert base["schema"] == CASE_SCHEMA
    assert base["name"] == "minimal"
    doc = CaseDocument.model_validate(base)
    assert isinstance(doc, CaseDocument)
    assert doc.schema_id == CASE_SCHEMA
    assert doc.name == "minimal"

    # Top-level override
    overridden = make_case_dict(name="custom")
    assert overridden["name"] == "custom"
    assert CaseDocument.model_validate(overridden).name == "custom"

    # Dotted override and deep-merging
    dotted = make_case_dict(
        name="custom_dotted",
        **{"physics.model": "pnp-ns", "boundary_conditions.bias_V": 0.05},
    )
    assert dotted["name"] == "custom_dotted"
    assert dotted["physics"]["model"] == "pnp-ns"
    assert dotted["boundary_conditions"]["bias_V"] == 0.05
    doc_dotted = CaseDocument.model_validate(dotted)
    assert doc_dotted.name == "custom_dotted"
    assert doc_dotted.boundary_conditions.bias_V == 0.05

    # Nested mapping override deep-merging
    nested = make_case_dict(physics={"solid_permittivities": {"membrane": 3.2}})
    assert nested["physics"]["model"] == "pnp-ns"
    assert nested["physics"]["solid_permittivities"] == {"membrane": 3.2}
    doc_nested = CaseDocument.model_validate(nested)
    assert doc_nested.physics.solid_permittivities == {"membrane": 3.2}


def test_make_case_fixture(make_case) -> None:
    """make_case fixture returns the make_case_dict helper."""
    assert make_case is make_case_dict
    doc = CaseDocument.model_validate(make_case(name="from_fixture"))
    assert doc.name == "from_fixture"

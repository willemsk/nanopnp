"""VER-24: the FR-25 provenance manifest and the validated-default diff it rests on."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal, get_args, get_origin

import pytest

from nanopnp.charge.dielectric import SolidFractionField
from nanopnp.charge.fields import (
    FIELD_QUADRATURE_ORDER,
    ChargeField,
    FieldDocument,
    FormSpec,
    conservation,
    create_form,
)
from nanopnp.charge.stage import ResolvedFields
from nanopnp.io import manifest as manifest_module
from nanopnp.io.artefact import CaseArtefact
from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
)
from nanopnp.io.case_paths import (
    FieldReference,
    case_fields,
)
from nanopnp.io.defaults import (
    CONFIGURATION_PATHS,
    MODEL_SWITCH_PATHS,
    SWITCH_PATHS,
    VALIDATED_DEFAULT_CASE,
    deviations,
    value_at,
)
from nanopnp.io.manifest import build, read
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledModel
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.pipeline.checks import registry_options

MINIMAL = """
schema: nanopnp/case/v0.5
name: minimal
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns}
numerics: {continuation: default_ladder}
"""


def _manifest(document: CaseDocument, **kwargs: object) -> manifest_module.Manifest:
    artefact = CaseArtefact(document)
    return build(document, case_text=MINIMAL, case_hash=artefact.hash, **kwargs)  # type: ignore[arg-type]


def _is_switch(reference: FieldReference) -> bool:
    annotation = reference.annotation
    literal = get_origin(annotation) is Literal or any(
        get_origin(argument) is Literal for argument in get_args(annotation)
    )
    is_registry_str = annotation is str and registry_options(reference.path) is not None
    return (
        annotation is bool
        or literal
        or reference.path.rsplit(".", 1)[-1] == "model"
        or is_registry_str
    )


def test_ver24_backend_registry_paths_are_detected_as_switches() -> None:
    fields_by_path = {ref.path: ref for ref in case_fields()}
    backend_paths = (
        "numerics.mesh.backend",
        "numerics.linear.solver",
        "numerics.stabilisation",
    )
    for path in backend_paths:
        assert path in fields_by_path, f"{path} is not a schema field"
        assert _is_switch(fields_by_path[path]), f"{path} should be recognised as a switch"


# FR-25
def test_ver24_every_switch_typed_field_of_the_schema_is_classified() -> None:
    classified = set(SWITCH_PATHS) | set(CONFIGURATION_PATHS)
    switches = {reference.path for reference in case_fields() if _is_switch(reference)}
    unclassified = switches - classified
    assert not unclassified, (
        f"{sorted(unclassified)} are switch-typed fields of nanopnp/case/v0.5 that are "
        "neither compared against the validated default (SWITCH_PATHS) nor exempted "
        "with a reason (CONFIGURATION_PATHS)"
    )


def test_ver24_every_classified_path_still_names_a_field() -> None:
    walked = {reference.path for reference in case_fields()}
    stale = (set(SWITCH_PATHS) | set(CONFIGURATION_PATHS)) - walked
    assert not stale, f"{sorted(stale)} name no field of nanopnp/case/v0.5"


def test_ver24_every_switch_path_reads_off_the_validated_default() -> None:
    for path in SWITCH_PATHS:
        value_at(VALIDATED_DEFAULT_CASE, path)


def test_ver24_the_two_classifications_are_disjoint() -> None:
    assert not set(SWITCH_PATHS) & set(CONFIGURATION_PATHS)


# PHY-22, PHY-23
def test_ver24_the_validated_default_case_deviates_from_nothing() -> None:
    assert deviations(VALIDATED_DEFAULT_CASE) == ()


def test_ver24_a_disabled_correction_is_recorded_as_a_deviation() -> None:
    document = VALIDATED_DEFAULT_CASE.model_copy(deep=True)
    document.electrolyte.corrections.viscosity.model = "none"
    found = {deviation.path: deviation for deviation in deviations(document)}
    assert "electrolyte.corrections.viscosity.model" in found
    recorded = found["electrolyte.corrections.viscosity.model"]
    assert recorded.value == "none"
    assert recorded.validated == "willems2020_nacl"


# FR-25, PHY-02
def test_ver24_a_moved_wall_distance_cap_is_recorded_as_a_deviation() -> None:
    document = VALIDATED_DEFAULT_CASE.model_copy(deep=True)
    document.numerics.wall_distance.max_distance_nm = 0.3
    found = {deviation.path: deviation for deviation in deviations(document)}
    recorded = found["numerics.wall_distance.max_distance_nm"]
    assert recorded.value == 0.3
    assert recorded.validated == 3.0


def test_ver24_the_model_and_the_case_agree_on_the_switches_they_share() -> None:
    document = VALIDATED_DEFAULT_CASE.model_copy(deep=True)
    # The validated default carries a charge: block so that every switch path reads off it;
    # resolve() refuses it in this release, and its absence reads as the same defaults.
    document.charge = None
    document.physics.inertia = False
    document.physics.dielectric_gradient_forces = True
    document.electrolyte.corrections.steric.model = "none"
    # The NUM-18 ladder drops this deviation (pipeline/checks.py), so one rung is built directly.
    document.numerics.continuation = "none"

    resolved = resolve(document)
    model = CoupledModel(
        electrolyte=resolved.electrolyte,
        concentration_M=resolved.concentration_M,
        inertia=False,
        dielectric_gradient_forces=True,
    )
    from_model = set(model.provenance["deviations_from_validated_default"])
    from_case = {deviation.path for deviation in deviations(document)}
    assert from_model & MODEL_SWITCH_PATHS == from_case & MODEL_SWITCH_PATHS
    # And the overlap is not vacuously empty, which is how this test would rot.
    assert from_case & MODEL_SWITCH_PATHS == {
        "physics.inertia",
        "physics.dielectric_gradient_forces",
        "electrolyte.corrections.steric.model",
    }


def test_ver24_the_solver_group_records_the_settings_and_the_run() -> None:
    document = loads_case(MINIMAL)
    ladder = {"rungs": [], "iterations": 12, "minimum_damping_used": 0.5}
    written = _manifest(document, ladder=ladder).document()
    solver = written["solver"]
    assert isinstance(solver, dict)
    assert solver["model"] == "pnp-ns"
    assert solver["continuation"] == "default_ladder"
    assert solver["run"]["iterations"] == 12


def test_ver24_stabilisation_is_recorded_with_the_number(tmp_path: Path) -> None:
    document = loads_case(MINIMAL)
    written = _manifest(document, stabilisation="reference").document()
    block = written["stabilisation"]
    assert isinstance(block, dict)
    assert block["requested"] == "none"
    assert block["mode"] == "reference"
    assert block["matches_requested"] is False


# FR-25
def test_ver24_a_stabilised_run_appears_under_deviations_without_being_told() -> None:
    for mode in ("supg", "reference"):
        document = loads_case(
            MINIMAL.replace(
                "{continuation: default_ladder}",
                f"{{continuation: default_ladder, stabilisation: {mode}}}",
            )
        )
        written = _manifest(document, stabilisation=mode).document()
        block = written["deviations"]
        assert isinstance(block, dict)
        paths = {entry["path"] for entry in block["switches"]}  # type: ignore[index,union-attr]
        assert "numerics.stabilisation" in paths


# FR-25
def test_num13_the_stabilisation_group_carries_the_mode_s_own_constants() -> None:
    from nanopnp.physics.stabilisation import create as create_stabilisation

    mode = create_stabilisation("reference")
    document = loads_case(MINIMAL)
    written = _manifest(
        document,
        stabilisation="reference",
        stabilisation_parameters=dict(mode.parameters),
        stabilisation_provenance=dict(mode.provenance),
    ).document()
    block = written["stabilisation"]
    assert isinstance(block, dict)
    assert block["parameters"] == dict(mode.parameters)
    assert block["parameter_provenance"] == dict(mode.provenance)
    assert block["parameters"] != {}


def test_num12_the_stabilisation_group_keeps_unmeasured_apart_from_zero() -> None:
    document = loads_case(MINIMAL)
    unmeasured = _manifest(document).document()["stabilisation"]
    assert isinstance(unmeasured, dict)
    assert unmeasured["stabilisation_current_A"] is None
    assert unmeasured["max_cell_peclet"] is None
    assert unmeasured["peclet"] is None

    measured = _manifest(
        document,
        stabilisation="none",
        stabilisation_currents_A={"Na+": 0.0, "Cl-": 0.0},
        peclet={"maximum": 0.31, "species": "Cl-", "exceeding": 0, "samples": 196},
    ).document()["stabilisation"]
    assert isinstance(measured, dict)
    assert measured["stabilisation_current_A"] == {"Na+": 0.0, "Cl-": 0.0}
    assert measured["max_cell_peclet"] == pytest.approx(0.31)
    assert measured["peclet"] == {
        "maximum": 0.31,
        "species": "Cl-",
        "exceeding": 0,
        "samples": 196,
    }


def test_ver24_deviations_reach_the_manifest_by_path() -> None:
    document = loads_case(MINIMAL)
    written = _manifest(document).document()
    block = written["deviations"]
    assert isinstance(block, dict)
    paths = {switch["path"] for switch in block["switches"]}
    assert paths == {deviation.path for deviation in deviations(document)}
    assert block["count"] == len(paths)
    # ``pnp-ns`` with the schema's default corrections is a long way from the
    # validated model, and the manifest must say so rather than imply otherwise.
    assert "physics.model" in paths


def _ring_field() -> ChargeField:
    spec = FormSpec(
        name="gaussian_ring",
        parameters={
            "centre_r_nm": 2.0,
            "centre_z_nm": 4.0,
            "width_nm": 0.3,
            "charge_e": -12.0,
        },
        origin_nm=(0.0, 0.0),
        spacing_nm=(0.01, 0.01),
        shape=(500, 900),
    )
    document = FieldDocument.model_validate(
        {
            "schema": "nanopnp/field/v0.5",
            "name": "ring",
            "quantity": "areal_charge_density",
            "units": "C/m^2",
            "q_net_e": -12.0,
            "provenance": {"source": "analytic"},
            "form": spec.model_dump(),
        }
    )
    # ``source`` is hashed by ResolvedFields.summary(), so it has to be a file
    # that exists; this one will do, and its digest is never asserted.
    return ChargeField(document=document, grid=create_form(spec), source=Path(__file__))


def _solid_fraction_field() -> SolidFractionField:
    spec = FormSpec(
        name="uniform",
        parameters={"value": 1.0},
        origin_nm=(0.0, 0.0),
        spacing_nm=(1.0, 1.0),
        shape=(2, 2),
    )
    document = FieldDocument.model_validate(
        {
            "schema": "nanopnp/field/v0.5",
            "name": "chi",
            "quantity": "solid_fraction",
            "units": "1",
            "provenance": {"source": "analytic"},
            "form": spec.model_dump(),
        }
    )
    return SolidFractionField(document=document, grid=create_form(spec), source=Path(__file__))


# PHY-19
def test_ver24_the_charge_group_carries_the_conservation_report_it_was_gated_on() -> None:
    import netgen.occ as occ
    import ngsolve as ngs

    face = occ.Rectangle(6.0, 10.0).Face()
    face.name = "electrolyte"
    mesh = ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=0.15))

    field = _ring_field()
    report = conservation(field, mesh, AXISYMMETRIC, planes_nm=[2.0, 6.0])
    fields = ResolvedFields(charge=field, conservation=report, eps_r=None, material_means=())

    written = _manifest(loads_case(MINIMAL), charge=fields.summary()).document()
    block = written["charge"]
    assert isinstance(block, dict)
    assert "status" not in block, "a populated charge group must not read as not run"

    charge = block["charge"]
    assert isinstance(charge, dict)
    assert charge["quantity"] == "areal_charge_density"
    assert charge["document_sha256"]
    assert charge["grid_digest"] == field.grid.digest()

    recorded = charge["conservation"]
    assert isinstance(recorded, dict)
    assert recorded == report.summary()
    assert recorded["q_net_e"] == pytest.approx(-12.0)
    assert recorded["producer"]["relative_error"] < recorded["producer"]["tolerance"]
    assert recorded["consumer"]["relative_error"] < recorded["consumer"]["tolerance"]
    assert recorded["quadrature_agreement"]["relative_error"] < 1.0
    assert recorded["per_plane"]["count"] == 2
    # The interpolant is part of the number: nearest-neighbour is a different field, so a
    # reconstructed run must name the one used.
    assert recorded["interpolation"] == "bilinear"


# PHY-19
def test_ver56_a_supplied_charge_field_is_keyed_by_the_rule_its_source_is_assembled_with() -> None:
    fields = ResolvedFields(charge=_ring_field(), conservation=None, eps_r=None, material_means=())
    keyed = fields.parameters()["charge"]
    assert isinstance(keyed, dict)
    assert keyed["quadrature_order"] == FIELD_QUADRATURE_ORDER


# FR-25, PHY-20
def test_ver24_a_stage_contributed_deviation_reaches_the_manifest_and_the_count() -> None:
    fields = ResolvedFields(
        charge=None, conservation=None, eps_r=_solid_fraction_field(), material_means=()
    )
    contributed = fields.deviations()
    assert contributed, "the fixture must actually carry a deviation, or this tests nothing"

    document = loads_case(MINIMAL)
    written = _manifest(document, contributed_deviations=contributed).document()
    block = written["deviations"]
    assert isinstance(block, dict)

    sources = [entry["source"] for entry in block["contributed"]]
    assert sources == ["inputs.eps_r"]
    switches = {entry["path"] for entry in block["switches"]}
    assert switches == {deviation.path for deviation in deviations(document)}
    assert block["count"] == len(switches) + len(sources)
    # No fabricated dotted path: one would name a case-file key that does not
    # exist, and a reader would go looking for it.
    assert all("path" not in entry for entry in block["contributed"])


def test_ver24_the_manifest_round_trips_with_the_case_beside_it(tmp_path: Path) -> None:
    document = loads_case(MINIMAL)
    built = _manifest(document)
    written_path = built.write(tmp_path)
    restored = read(written_path)

    assert restored["hash"] == built.hash
    case = restored["case"]
    assert isinstance(case, dict)
    assert case["text"] == MINIMAL
    # The case beside the manifest re-validates; a manifest whose case no longer parses
    # reconstructs nothing.
    assert loads_case(str(case["text"])).name == document.name


def test_ver24_the_environment_group_names_versions_without_importing_ngsolve() -> None:
    script = (
        "import sys, json;"
        "from nanopnp.io.manifest import environment;"
        "group = environment();"
        "print(json.dumps({'ngsolve': 'ngsolve' in sys.modules,"
        " 'version': group['packages']['ngsolve']}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    reported = json.loads(completed.stdout)
    assert reported["ngsolve"] is False
    assert reported["version"]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("numerics.wall_distance.max_distance_nm", 0.0),
        ("numerics.wall_distance.max_distance_nm", float("nan")),
        ("electrolyte.concentration_M", -0.5),
        ("electrolyte.concentration_M", float("nan")),
        ("boundary_conditions.bias_V", float("inf")),
    ],
)
def test_ver24_resolve_refuses_an_operating_point_no_solve_could_use(
    path: str, value: float
) -> None:
    document = loads_case(MINIMAL)
    section, *middle, leaf = path.split(".")
    target = getattr(document, section)
    for part in middle:
        target = getattr(target, part)
    setattr(target, leaf, value)
    with pytest.raises(CaseValidationError, match=re.escape(path)):
        resolve(document)

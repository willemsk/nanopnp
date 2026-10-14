"""VER-43 — the one walk over ``nanopnp/case/v0.5``, and what is built on it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from nanopnp.core.stages import create, describe
from nanopnp.io.artefact import CASE_SCHEMA, StageInputs
from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
    dump_case,
)
from nanopnp.io.case_paths import (
    NEUTRAL_SECTIONS,
    _walk_fields,
    case_fields,
    field_at,
    with_section,
)
from nanopnp.io.defaults import CONFIGURATION_PATHS, SWITCH_PATHS
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import (
    run_case,
    stored_upstream,
)

SCHEMA_PATHS: tuple[str, ...] = (
    "schema",
    "name",
    "inputs.mesh.path",
    "inputs.mesh.artefact",
    "inputs.mesh.format",
    "inputs.mesh.groups",
    "inputs.charge.path",
    "inputs.charge.artefact",
    "inputs.charge.format",
    "inputs.charge.groups",
    "inputs.eps_r.path",
    "inputs.eps_r.artefact",
    "inputs.eps_r.format",
    "inputs.eps_r.groups",
    "inputs.profile.path",
    "inputs.profile.artefact",
    "inputs.profile.format",
    "inputs.profile.groups",
    "inputs.pqr.path",
    "inputs.pqr.artefact",
    "inputs.pqr.format",
    "inputs.pqr.groups",
    "structure.source.path",
    "structure.source.variant",
    "structure.source.chains",
    "structure.source.selection",
    "structure.ensemble.trajectory",
    "structure.ensemble.frames.last_ns",
    "structure.ensemble.frames.count",
    "structure.symmetry.point_group",
    "structure.symmetry.axis",
    "geometry.density.grid_spacing_nm",
    "geometry.density.kernel",
    "geometry.density.sharpness",
    "geometry.contour.isolevel",
    "geometry.contour.smoothing",
    "geometry.contour.simplify_tol_nm",
    "geometry.membrane.thickness_nm",
    "geometry.membrane.centre_z_nm",
    "geometry.reservoir.radius_nm",
    "geometry.analyte.shape",
    "geometry.analyte.a_nm",
    "geometry.analyte.b_nm",
    "geometry.analyte.z_nm",
    "geometry.analyte.charge_e",
    "charge.ph",
    "charge.forcefield",
    "charge.titration",
    "charge.smearing.sharpness",
    "charge.smearing.grid_spacing_nm",
    "charge.smearing.axis_cutoff_nm",
    "charge.exclusion_offset_nm",
    "charge.dielectric_transition_nm",
    "electrolyte.species.0.name",
    "electrolyte.species.0.z",
    "electrolyte.concentration_M",
    "electrolyte.temperature_K",
    "electrolyte.parameters",
    "electrolyte.driver",
    "electrolyte.corrections.diffusivity.model",
    "electrolyte.corrections.diffusivity.concentration",
    "electrolyte.corrections.diffusivity.wall",
    "electrolyte.corrections.mobility.model",
    "electrolyte.corrections.mobility.concentration",
    "electrolyte.corrections.mobility.wall",
    "electrolyte.corrections.viscosity.model",
    "electrolyte.corrections.viscosity.concentration",
    "electrolyte.corrections.viscosity.wall",
    "electrolyte.corrections.permittivity.model",
    "electrolyte.corrections.permittivity.concentration",
    "electrolyte.corrections.permittivity.wall",
    "electrolyte.corrections.density.model",
    "electrolyte.corrections.density.concentration",
    "electrolyte.corrections.density.wall",
    "electrolyte.corrections.steric.model",
    "electrolyte.corrections.steric.a_ion_nm",
    "electrolyte.corrections.steric.a_water_nm",
    "boundary_conditions.bias_V",
    "boundary_conditions.ground",
    "boundary_conditions.walls.ion_flux",
    "boundary_conditions.walls.slip",
    "physics.model",
    "physics.flow",
    "physics.variable_density",
    "physics.inertia",
    "physics.dielectric_gradient_forces",
    "physics.solid_permittivities",
    "numerics.elements.phi",
    "numerics.elements.c",
    "numerics.elements.u",
    "numerics.elements.p",
    "numerics.mesh.backend",
    "numerics.mesh.wall_h_nm",
    "numerics.mesh.size_scale",
    "numerics.mesh.boundary_layer",
    "numerics.nonlinear.strategy",
    "numerics.nonlinear.damping",
    "numerics.nonlinear.max_iter",
    "numerics.nonlinear.rtol",
    "numerics.continuation",
    "numerics.stabilisation",
    "numerics.wall_distance.sources",
    "numerics.wall_distance.max_distance_nm",
    "numerics.linear.solver",
    "outputs",
)
"""Every editable field of ``nanopnp/case/v0.5``, in declaration order.

Written out rather than computed. A field added to the schema and forgotten
elsewhere fails the test below naming itself, which is the whole point; a field
*removed* fails it too, which is what stops a rename from leaving the editor
and the manifest pointing at nothing.
"""


def test_if09_case_fields_enumerates_the_whole_schema() -> None:
    assert CASE_SCHEMA.startswith("nanopnp/case/")
    found = case_fields()
    assert tuple(reference.path for reference in found) == SCHEMA_PATHS


def test_if09_every_walked_field_is_the_one_field_at_resolves() -> None:
    for reference in case_fields():
        assert field_at(reference.path) == reference


# FR-25
def test_if09_case_fields_refuses_a_mapping_of_blocks() -> None:

    class _Entry(BaseModel):
        value: float = 0.0

    class _Block(BaseModel):
        entries: dict[str, _Entry] = {}

    with pytest.raises(NotImplementedError, match="mapping of _Entry blocks"):
        _walk_fields(_Block, "")


def test_fr25_switch_paths_are_the_same_walk() -> None:
    walked = {reference.path for reference in case_fields()}
    unreachable = [path for path in (*SWITCH_PATHS, *CONFIGURATION_PATHS) if path not in walked]
    assert not unreachable, (
        f"{sorted(unreachable)} are classified by nanopnp.io.defaults but are not fields "
        "case_fields() yields, so the editor indexes the case differently from the manifest"
    )


def test_if09_the_walk_reaches_a_block_behind_an_optional_and_a_sequence() -> None:
    paths = {reference.path for reference in case_fields()}
    assert "geometry.analyte.shape" in paths
    assert "electrolyte.species.0.name" in paths


QUICKSTART = Path(__file__).parents[2] / "examples" / "01-quickstart" / "quickstart.case.yaml"
"""A supplied-mesh case: the one beside which ``geometry: {}`` is refused."""


def _optional_sections() -> tuple[str, ...]:
    return tuple(
        name
        for name, info in CaseDocument.model_fields.items()
        if not info.is_required() and info.default is None
    )


def _without(document: CaseDocument, name: str) -> CaseDocument:
    payload = document.model_dump(by_alias=True, mode="json")
    payload.pop(name, None)
    return CaseDocument.model_validate(payload)


def _resolution(document: CaseDocument) -> dict[str, object]:
    resolved = resolve(document)
    return {
        item.name: getattr(resolved, item.name)
        for item in fields(resolved)
        if item.name != "document"
    }


def _bases(directory: Path, write_tube: Callable[..., Path]) -> tuple[CaseDocument, ...]:
    return (load_case(QUICKSTART), load_case(write_tube(directory)))


def test_ver60_the_neutral_sections_are_optional_sections_of_the_schema() -> None:
    optional = set(_optional_sections())
    assert optional == {"structure", "geometry", "charge"}
    assert optional >= NEUTRAL_SECTIONS
    assert "charge" in NEUTRAL_SECTIONS


def test_ver60_a_listed_section_resolves_empty_as_absent(tmp_path: Path, charged_tube) -> None:
    for base in _bases(tmp_path, charged_tube.write):
        for name in NEUTRAL_SECTIONS:
            absent = _without(base, name)
            added = with_section(absent, name)
            assert getattr(added, name) is not None
            assert _resolution(added) == _resolution(absent), (base.name, name)


def test_ver60_every_unlisted_optional_section_is_refused_empty_or_resolves_differently(
    tmp_path: Path, charged_tube
) -> None:
    for name in sorted(set(_optional_sections()) - NEUTRAL_SECTIONS):
        evidence: list[str] = []
        for base in _bases(tmp_path, charged_tube.write):
            payload = _without(base, name).model_dump(by_alias=True, mode="json")
            payload[name] = {}
            try:
                empty = CaseDocument.model_validate(payload)
                if _resolution(empty) != _resolution(_without(base, name)):
                    evidence.append(f"{base.name}: resolves differently")
            except (ValidationError, CaseValidationError) as error:
                evidence.append(f"{base.name}: refused ({type(error).__name__})")
        assert evidence, f"{name}: {{}} resolves as its absence on every base case; list it"


def test_ver60_with_section_refuses_an_unlisted_or_present_section(tmp_path: Path) -> None:
    base = load_case(QUICKSTART)
    for name in ("structure", "geometry", "analyte", "physics"):
        with pytest.raises(ValueError, match="cannot be added from a default"):
            with_section(base, name)
    present = with_section(_without(base, "charge"), "charge")
    with pytest.raises(ValueError, match="already carries a charge: section"):
        with_section(present, "charge")


def test_ver60_an_empty_charge_section_keys_every_physics_stage_as_its_absence(
    tmp_path: Path, charged_tube
) -> None:
    absent = _without(load_case(charged_tube.write(tmp_path / "tube")), "charge")
    added = with_section(absent, "charge")
    store = Store(tmp_path / "store")
    # The solve's inputs, without the solve: the charge and the materials walks
    # between them cover every stage the solve reads (WP38 D11).
    for upto in ("charge", "materials"):
        run_case(dump_case(absent, tmp_path / "absent.yaml"), store=store, upto=upto)

    def keys(document: CaseDocument) -> dict[str, str]:
        found = stored_upstream(document, store=store)
        found["solve"] = create("solve").key(  # type: ignore[attr-defined]
            StageInputs(resolved=resolve(document), upstream=dict(found))
        )
        return {name: artefact.hash for name, artefact in found.items()}

    before, after = keys(absent), keys(added)
    assert set(before) == set(after)
    assert {name for name in before if before[name] != after[name]} == {"case"}
    assert all(describe(name).number <= 10 for name in before)

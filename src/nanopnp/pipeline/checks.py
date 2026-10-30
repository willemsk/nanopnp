"""The case checks that need the installed registries or this release, beyond the schema."""

from __future__ import annotations

import difflib
import math
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from nanopnp.charge.fields import FIELD_FORMAT
from nanopnp.core.paths import available_corrections
from nanopnp.io.case import (
    CORRECTION_PROPERTIES,
    OUTPUTS,
    PQR_FORMAT,
    PROFILE_FORMAT,
    SUPPLIED_FIELDS,
    CaseDocument,
    CaseValidationError,
    Charge,
    Contour,
    Density,
    Membrane,
    Physics,
    Reservoir,
    Smearing,
    SuppliedArtefact,
    UnsupportedCaseSection,
    render_problems,
    stored_artefact_refused,
)
from nanopnp.io.case_paths import (
    _literal_options,
    case_fields,
    field_at,
    schema_default,
    value_at,
)
from nanopnp.io.resolved import contour_spacing_nm
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.materials.models import PropertyKind, applies_part
from nanopnp.mesh.ingest import SOLID_MATERIALS, fluid_permittivity_refusal
from nanopnp.mesh.meshers import registered_meshers
from nanopnp.numerics.linear import registered_solvers, rejection
from nanopnp.physics.models import (
    LADDER_STRATEGY,
    SWITCHES,
    declaration,
    inf_sup_problem,
    registered_models,
    registered_stabilisations,
)

__all__ = [
    "check_document",
    "check_operating_point",
    "check_referenced_files",
    "check_species",
    "element_orders",
    "options_at",
    "registry_options",
    "require_runnable",
]


def registry_options(path: str) -> tuple[str, ...] | None:
    """Return the values an installed registry admits at a dotted path, or None."""
    if path == "physics.model":
        return registered_models()
    if path == "numerics.mesh.backend":
        return registered_meshers()
    if path == "numerics.stabilisation":
        return registered_stabilisations()
    if path == "numerics.linear.solver":
        return registered_solvers()
    if path == "electrolyte.parameters":
        return available_corrections()
    if path in _CORRECTION_MODEL_PATHS:
        # ``none`` disables a correction by selecting the registered ``none``
        # model rather than by taking a code branch (PHY-22), so it is offered
        # beside the installed parameter files and is not one of them.
        return ("none", *available_corrections())
    if path == "outputs":
        return tuple(sorted(OUTPUTS))
    return None


_CORRECTION_MODEL_PATHS: frozenset[str] = frozenset(
    f"electrolyte.corrections.{name}.model" for name in CORRECTION_PROPERTIES
)


def check_document(document: CaseDocument, *, source: str | None = None) -> CaseDocument:
    """Check a schema-valid document against the registries and element orders."""
    problems: list[str] = []
    if document.physics.model not in registered_models():
        problems.append(
            f"physics.model {document.physics.model!r} is not registered; the models are "
            f"{', '.join(registered_models())}"
        )
    if document.numerics.mesh.backend not in registered_meshers():
        problems.append(
            f"numerics.mesh.backend {document.numerics.mesh.backend!r} is not a registered "
            f"mesher; the meshers are {', '.join(registered_meshers())}"
        )
    if document.numerics.stabilisation not in registered_stabilisations():
        problems.append(
            f"numerics.stabilisation {document.numerics.stabilisation!r} is not a registered "
            f"mode; the available modes are {', '.join(registered_stabilisations())}. "
            "Recording a mode the solver does not apply would make the FR-25 manifest "
            "describe a run that never happened"
        )
    solver = document.numerics.linear.solver
    if solver not in registered_solvers():
        reason = rejection(solver)
        problems.append(
            f"numerics.linear.solver {solver!r} is not usable: {reason}"
            if reason is not None
            else f"numerics.linear.solver {solver!r} is not available; the solvers are "
            f"{', '.join(registered_solvers())}"
        )
    if problems:
        # Rendered as the schema renders a document-level refusal, which is how
        # these read when ``CaseDocument`` asked the registries itself: a caller
        # matching the text, or reading ``errors``, sees no difference.
        error = ValidationError.from_exception_data(
            title=CaseDocument.__name__,
            line_errors=[
                {
                    "type": "value_error",
                    "loc": (),
                    "input": document.model_dump(by_alias=True, mode="json"),
                    "ctx": {"error": ValueError("; ".join(problems))},
                }
            ],
        )
        name = source if source is not None else f"<{document.name}>"
        raise CaseValidationError(render_problems(name, error), error)
    element_orders(document)
    return document


def element_orders(document: CaseDocument) -> tuple[int, int, int]:
    """Return the field, velocity and pressure orders, refusing a pair no solve can use."""
    elements = document.numerics.elements
    order = _order(elements.phi, "phi")
    concentration_order = _order(elements.c, "c")
    if concentration_order != order:
        raise CaseValidationError(
            f"numerics.elements.c is {elements.c!r} and numerics.elements.phi is "
            f"{elements.phi!r}; this release carries one order for phi and c_i, which the "
            "NUM-02 log branch and the PHY-05 steric term both assume"
        )
    # ``u`` is not folded into that equality. The reference mode of section 6.4
    # runs phi and c at P2 with u and p at P1, so the velocity order is a third
    # order rather than a restatement of the first.
    velocity_order = _order(elements.u, "u")
    pressure_order = _order(elements.p, "p")
    model_name = document.physics.model
    model_unread = (
        declaration(model_name).unread if model_name in registered_models() else frozenset()
    )
    if "numerics.elements.u" not in model_unread and document.physics.flow:
        problem = inf_sup_problem(
            velocity_order=velocity_order,
            pressure_order=pressure_order,
            stabilisation=document.numerics.stabilisation,
        )
        if problem is not None:
            raise CaseValidationError(
                f"numerics.elements.u is {elements.u!r} and numerics.elements.p is "
                f"{elements.p!r}: {problem}"
            )
    return order, velocity_order, pressure_order


def options_at(path: str) -> tuple[str, ...] | None:
    """Return the values a case document is accepted with at path, or None if not enumerable."""
    reference = field_at(path)
    literal = _literal_options(reference.annotation)
    registered = registry_options(path)
    if literal is None:
        return registered
    if registered is None:
        return literal
    admitted = set(registered)
    return tuple(value for value in literal if value in admitted)


_ORDERS: dict[str, int] = {"P1": 1, "P2": 2, "P3": 3}


PROFILE_KEYS: tuple[str, ...] = ("exclusion_offset_nm", "dielectric_transition_nm")


SMEARING_KEYS: tuple[str, ...] = ("sharpness", "grid_spacing_nm")


PROTONATION_KEYS: tuple[str, ...] = ("ph", "forcefield", "titration")


def _order(label: str, field: str) -> int:
    try:
        return _ORDERS[label]
    except KeyError:
        raise CaseValidationError(
            f"numerics.elements.{field} {label!r} is not an element label; "
            f"the labels are {', '.join(sorted(_ORDERS))}"
        ) from None


def check_species(document: CaseDocument, electrolyte: Electrolyte) -> None:
    """Check species, steric diameters and temperature against the parameter file."""
    problems: list[str] = []
    temperature_K = document.electrolyte.temperature_K
    if temperature_K != electrolyte.temperature_K:
        problems.append(
            f"electrolyte.temperature_K is {temperature_K} K, but "
            f"{document.electrolyte.parameters!r} is fitted at {electrolyte.temperature_K} K and "
            "the solve takes every material property and V_T from the file; set temperature_K: "
            f"{electrolyte.temperature_K} or supply a parameter file fitted at the temperature "
            "you want"
        )
    for index, species in enumerate(document.electrolyte.species):
        valence = electrolyte.ion(species.name).valence
        if valence != species.z:
            problems.append(
                f"electrolyte.species[{index}].z is {species.z:+d} for {species.name!r}, but "
                f"{document.electrolyte.parameters!r} gives {valence:+d}"
            )
    steric = document.electrolyte.corrections.steric
    if steric.a_ion_nm is not None:
        for index, ion in enumerate(electrolyte.species):
            given_m = steric.a_ion_nm * 1e-9
            if abs(ion.steric_diameter - given_m) > 1e-15:
                problems.append(
                    f"electrolyte.corrections.steric.a_ion_nm is {steric.a_ion_nm} nm, but "
                    f"{document.electrolyte.parameters!r} gives "
                    f"{ion.steric_diameter * 1e9} nm for {ion.name!r} "
                    f"(species[{index}]); the diameters are fitted parameters of the correction "
                    "file and the case file cannot override them (FR-16)"
                )
    if steric.a_water_nm is not None:
        given_m = steric.a_water_nm * 1e-9
        if abs(electrolyte.water_steric_diameter - given_m) > 1e-15:
            problems.append(
                f"electrolyte.corrections.steric.a_water_nm is {steric.a_water_nm} nm, but "
                f"{document.electrolyte.parameters!r} gives "
                f"{electrolyte.water_steric_diameter * 1e9} nm"
            )
    if problems:
        raise CaseValidationError("; ".join(problems))


def require_runnable(document: CaseDocument) -> SuppliedArtefact | None:
    """Reject every section this release does not run; return the supplied mesh, if any."""
    _check_charge(document)
    for supplied in ("mesh", "charge", "eps_r"):
        given: SuppliedArtefact | None = getattr(document.inputs, supplied)
        if given is not None and given.path is None:
            # Stage 6 and stage 7 read a supplied output by path only; refused here so
            # that ``nanopnp validate case`` sees what ``run`` would.
            raise stored_artefact_refused(supplied)
    for supplied, what in SUPPLIED_FIELDS.items():
        field: SuppliedArtefact | None = getattr(document.inputs, supplied)
        if field is None:
            continue
        if field.groups:
            raise CaseValidationError(
                f"inputs.{supplied}.groups is the mesh's vocabulary mapping (IF-06) and means "
                f"nothing for {what}; a field is named by its header document, which carries the "
                "quantity and the units (section 5.3.1 NOTE)"
            )
        if field.format not in (None, FIELD_FORMAT):
            raise CaseValidationError(
                f"inputs.{supplied}.format is {field.format!r}; a supplied field is named by a "
                f"header document, so the format is {FIELD_FORMAT!r} and the *data* format is read "
                "from the document's data.format key (section 5.3.1 NOTE)"
            )
    if document.structure is not None and document.inputs.mesh is not None:
        raise CaseValidationError(
            f"case {document.name!r} carries a structure: section and supplies inputs.mesh. A "
            "stage whose output is supplied does not run, and neither does anything upstream of "
            "it, so the structure would be recorded as an input to a run that never read it "
            "(section 5.3.1 NOTE on inputs:); remove one of them"
        )
    _check_pore(document)
    if document.geometry is not None and document.inputs.mesh is not None:
        raise CaseValidationError(
            f"case {document.name!r} carries a geometry: section and supplies inputs.mesh. A "
            "stage whose output is supplied does not run, and neither does anything upstream of "
            "it, so the geometry would be recorded as an input to a run that never read it "
            "(section 5.3.1 NOTE on geometry.density); remove one of them"
        )
    _check_profile(document)
    if (
        document.inputs.mesh is None
        and document.structure is None
        and document.inputs.profile is None
        and (document.geometry is None or document.geometry.pore is None)
    ):
        raise CaseValidationError(
            f"case {document.name!r} names no geometry: it supplies neither inputs.mesh nor "
            "inputs.profile, declares no geometry.pore and carries no structure: section, so "
            "there is nothing to mesh and "
            "no mesh to solve on (section 5.3.1 NOTE on inputs:)"
        )
    if document.inputs.mesh is None:
        _check_generation(document)
    mesh = document.inputs.mesh
    nonlinear = document.numerics.nonlinear
    if nonlinear.strategy != "newton":
        raise UnsupportedCaseSection(
            f"numerics.nonlinear.strategy {nonlinear.strategy!r} selects NUM-20's hybrid "
            "segregated fallback, which no release of SPECIFICATION.md schedules; every rung is "
            "solved by the monolithic damped Newton of NUM-16 (strategy: newton)"
        )
    if nonlinear.damping != "residual":
        raise UnsupportedCaseSection(
            f"numerics.nonlinear.damping {nonlinear.damping!r} selects NUM-20's damped Newton "
            "with l2 backtracking, which no release of SPECIFICATION.md schedules; the damping is "
            "NUM-16's, adapted on residual reduction (damping: residual), whose recovery rule the "
            "reference records"
        )
    walls = document.boundary_conditions.walls
    if walls.slip != "no_slip" or walls.ion_flux != "no_flux":
        # Nothing downstream reads the wall values: the forms pose no-slip and
        # no-flux unconditionally, so any other value would be recorded in the
        # manifest without being applied (section 5.3.1 NOTE on walls).
        raise UnsupportedCaseSection(
            f"boundary_conditions.walls asks for slip: {walls.slip} and ion_flux: "
            f"{walls.ion_flux}; this release applies slip: no_slip and ion_flux: no_flux only, "
            "and no release of SPECIFICATION.md section 3 schedules the others yet"
        )
    # Read from the model's declaration, never from its name (section 5.4.3
    # NOTE): the switch check first, because a case the model cannot pose is a
    # more precise diagnostic than one about how to continue it.
    _check_solid_permittivity_keys(document)
    _check_physics_switches(document)
    _check_unread(document)
    _check_correction_parts(document)
    _check_switch_partners(document)
    _check_driver(document)
    _check_strategy(document)
    if document.numerics.continuation == LADDER_STRATEGY:
        _check_ladder_can_honour(document.physics)
    _check_outputs(document)
    return mesh


def _check_pore(document: CaseDocument) -> None:
    geometry = document.geometry
    pore = geometry.pore if geometry is not None else None
    note = "section 5.3.1 NOTE on geometry.pore"
    if pore is None:
        charge = document.boundary_conditions.wall_charge_C_m2
        if charge != 0.0:
            raise CaseValidationError(
                f"boundary_conditions.wall_charge_C_m2 is {charge} with no geometry.pore; it is "
                f"the surface charge of an idealised pore's wall, and nothing else has one ({note})"
            )
        if document.numerics.mesh.maxh_nm is not None:
            raise CaseValidationError(
                f"numerics.mesh.maxh_nm is {document.numerics.mesh.maxh_nm} with no "
                f"geometry.pore; it is the global element size of an idealised pore ({note})"
            )
        return
    for name, present in (
        ("structure:", document.structure is not None),
        ("inputs.profile", document.inputs.profile is not None),
        ("inputs.mesh", document.inputs.mesh is not None),
    ):
        if present:
            raise CaseValidationError(
                f"geometry.pore and {name} are both given; an idealised pore is the geometry, "
                f"and {name} would be a second one ({note}); remove one of them"
            )
    assert geometry is not None
    if pore.radius_nm >= geometry.reservoir.radius_nm:
        raise CaseValidationError(
            f"geometry.pore.radius_nm is {pore.radius_nm} nm, not below "
            f"geometry.reservoir.radius_nm {geometry.reservoir.radius_nm} nm; the lumen opens "
            f"into a larger reservoir ({note})"
        )
    if "membrane" not in document.physics.solid_permittivities:
        raise CaseValidationError(
            "physics.solid_permittivities.membrane is not set; the solid around an idealised "
            "pore is the membrane domain, and an unlisted solid is taken as ion-free water "
            f"({note}); set its relative permittivity"
        )
    if geometry.membrane.centre_z_nm != 0.0:
        raise CaseValidationError(
            f"geometry.membrane.centre_z_nm is {geometry.membrane.centre_z_nm} with "
            f"geometry.pore; it is a position in a structure's frame, and the pore sits at 0 "
            f"({note})"
        )
    for key, default in (("density", Density()), ("contour", Contour())):
        if getattr(geometry, key) != default:
            raise CaseValidationError(
                f"geometry.{key} is set beside geometry.pore; stages 2 to 4 read it and an "
                f"idealised pore skips them ({note})"
            )
    backend = document.numerics.mesh.backend
    if backend != "netgen":
        raise CaseValidationError(
            f"numerics.mesh.backend is {backend!r} beside geometry.pore; the idealised pore's "
            f"size field is posed for netgen only ({note})"
        )


def _check_charge(document: CaseDocument) -> None:
    pqr = document.inputs.pqr
    if pqr is not None:
        if pqr.path is None:
            raise CaseValidationError(
                "inputs.pqr: artefact: names a protonation artefact in the store; the stage's "
                "own artefact is reached through a structure: section, and a supplied PQR is "
                "named by inputs.pqr: path: (section 5.3.1 NOTE on inputs:)"
            )
        if pqr.groups:
            raise CaseValidationError(
                "inputs.pqr.groups is the mesh's vocabulary mapping (IF-06) and means nothing "
                "for a PQR file (section 5.3.1 NOTE on inputs:)"
            )
        if pqr.format not in (None, PQR_FORMAT):
            raise CaseValidationError(
                f"inputs.pqr.format is {pqr.format!r}; a supplied PQR file of one frame or one "
                f"MODEL per frame has format {PQR_FORMAT!r} (section 5.3.1 NOTE on inputs:)"
            )
    charge = document.charge
    if charge is None:
        return
    defaults = Charge()
    _check_profile_keys(document, charge)
    _check_smearing(document, charge.smearing, defaults.smearing)
    if charge.titration == "none" and charge.ph != defaults.ph:
        raise CaseValidationError(
            f"charge.ph is {charge.ph} beside charge.titration: none, which runs PDB2PQR "
            "without a titration method, so the pH reaches no calculation; remove charge.ph or "
            "set charge.titration: propka (section 5.3.1 NOTE on the protonation keys)"
        )
    changed = [
        f"charge.{key}"
        for key in PROTONATION_KEYS
        if getattr(charge, key) != getattr(defaults, key)
    ]
    if not changed:
        return
    where = (
        "beside inputs.pqr, which supplies the charges and radii PDB2PQR would compute"
        if pqr is not None
        else "beside inputs.charge, which supplies the field stage 7 would make of them"
        if document.inputs.charge is not None
        else "in a case with neither a structure: section nor inputs.pqr, so there is nothing "
        "to protonate"
        if document.structure is None
        else None
    )
    if where is not None:
        raise CaseValidationError(
            f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set {where}; the "
            "protonation stage they configure does not run, so they would change nothing "
            "(section 5.3.1 NOTE on the protonation keys)"
        )


def _check_profile_keys(document: CaseDocument, charge: Charge) -> None:
    changed = [f"charge.{key}" for key in PROFILE_KEYS if getattr(charge, key) != 0.0]
    if not changed:
        return
    named = f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set away from 0"
    if document.inputs.mesh is not None:
        raise CaseValidationError(
            f"{named} beside inputs.mesh; both are built from the stage-4 profile, and a "
            "supplied mesh has none, so they would change nothing (section 5.3.1 NOTE on the "
            "v2 keys that change a number)"
        )
    if document.structure is None and document.inputs.profile is None:
        raise CaseValidationError(
            f"{named} in a case with neither a structure: section nor inputs.profile; both are "
            "built from the stage-4 profile, and there is none (section 5.3.1 NOTE on the v2 keys "
            "that change a number)"
        )
    if charge.dielectric_transition_nm > 0.0 and document.inputs.eps_r is not None:
        raise CaseValidationError(
            f"charge.dielectric_transition_nm is {charge.dielectric_transition_nm} nm beside "
            "inputs.eps_r; both supply the solid fraction chi, so the case names one quantity "
            "twice; remove one of them (section 5.3.1 NOTE on the v2 keys that change a number)"
        )
    h_c = contour_spacing_nm(document)
    delta = charge.dielectric_transition_nm
    if 0.0 < delta < h_c:
        raise CaseValidationError(
            f"charge.dielectric_transition_nm is {delta} nm, below "
            f"geometry.density.grid_spacing_nm = {h_c} nm: the transition would be finer than "
            "the grid the contour it is built on is placed on (section 4.4 NOTE on the derived "
            "solid fraction)"
        )
    offset = charge.exclusion_offset_nm
    if 0.0 < offset <= 2.0 * h_c:
        raise CaseValidationError(
            f"charge.exclusion_offset_nm is {offset} nm, at most twice "
            f"geometry.density.grid_spacing_nm = {h_c} nm: the shell is a face of width a, and "
            f"section 5.2.1's feature-size criterion admits nothing narrower than 2 h_c = "
            f"{2.0 * h_c:g} nm (section 5.2.1 NOTE on the ion-exclusion shell)"
        )


def _check_smearing(document: CaseDocument, smearing: Smearing, defaults: Smearing) -> None:
    if smearing.axis_cutoff_nm != defaults.axis_cutoff_nm:
        raise CaseValidationError(
            f"charge.smearing.axis_cutoff_nm is {smearing.axis_cutoff_nm}; it is refused away "
            f"from its default {defaults.axis_cutoff_nm} on every path (PHY-18). The deposited "
            "kernel is regular on the axis and takes no guard, and a supplied field declares its "
            "own axis_cutoff_nm in its header document, so the key would change nothing "
            "(section 5.3.1 NOTE on charge.smearing)"
        )
    for key in SMEARING_KEYS:
        value = getattr(smearing, key)
        if not 0.0 < value < math.inf:
            raise CaseValidationError(
                f"charge.smearing.{key} is {value}; it must be finite and positive (PHY-16 "
                "steps 4-6)"
            )
    changed = [
        f"charge.smearing.{key}"
        for key in SMEARING_KEYS
        if getattr(smearing, key) != getattr(defaults, key)
    ]
    if not changed:
        return
    where = (
        "beside inputs.charge, which supplies the field stage 7 would otherwise deposit"
        if document.inputs.charge is not None
        else "in a case with neither a structure: section nor inputs.pqr, so there is nothing "
        "to deposit"
        if document.structure is None and document.inputs.pqr is None
        else None
    )
    if where is not None:
        other = "inputs.charge" if document.inputs.charge is not None else "structure:"
        raise CaseValidationError(
            f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set {where} "
            f"({other}); the deposition stage 7 would configure with "
            f"{'it' if len(changed) == 1 else 'them'} does not run, so "
            f"{'it' if len(changed) == 1 else 'they'} would change nothing (section 5.3.1 NOTE "
            "on charge.smearing)"
        )


def _check_profile(document: CaseDocument) -> None:
    profile = document.inputs.profile
    if profile is None:
        return
    if profile.path is None:
        raise CaseValidationError(
            "inputs.profile: artefact: names a profile in the store; stage 4's artefact is "
            "reached through a structure: section, and a supplied profile is named by "
            "inputs.profile: path: (section 5.3.1 NOTE on inputs:)"
        )
    if profile.groups:
        raise CaseValidationError(
            "inputs.profile.groups is the mesh's vocabulary mapping (IF-06) and means nothing "
            "for a profile, whose one boundary stage 5 names itself (section 5.3.1 NOTE on "
            "inputs:)"
        )
    if profile.format not in (None, PROFILE_FORMAT):
        raise CaseValidationError(
            f"inputs.profile.format is {profile.format!r}; a supplied profile is a "
            f"nanopnp/profile/v0.5 document, format {PROFILE_FORMAT!r} (section 5.3.1 NOTE on "
            "inputs:)"
        )
    if document.structure is not None:
        raise CaseValidationError(
            f"case {document.name!r} carries a structure: section and supplies inputs.profile. "
            "A stage whose output is supplied does not run, and neither does anything upstream "
            "of it, so the structure would be recorded as an input to a run that never read it "
            "(section 5.3.1 NOTE on inputs:); remove one of them"
        )
    geometry = document.geometry
    if geometry is None:
        return
    for key, default in (("density", Density()), ("contour", Contour())):
        if getattr(geometry, key) != default:
            raise CaseValidationError(
                f"geometry.{key} is set beside inputs.profile. Stages 2 to 4 read it and a "
                "supplied profile means they do not run, so it would change nothing; remove it "
                "(section 5.3.1 NOTE on inputs:)"
            )


def _check_generation(document: CaseDocument) -> None:
    mesh = document.numerics.mesh
    if mesh.boundary_layer:
        raise UnsupportedCaseSection(
            "numerics.mesh.boundary_layer is true; boundary-layer meshing is FR-11, after v1.0. "
            "The reference mesh used none, only isotropic grading to the wall (section 5.2.2)"
        )
    geometry = document.geometry
    if geometry is not None and geometry.analyte is not None:
        raise UnsupportedCaseSection(
            f"geometry.analyte is a {geometry.analyte.shape}; an analyte in a generated region "
            "is FR-21, v0.7. The benchmark geometries embed one (PHY-11)"
        )
    membrane = geometry.membrane if geometry is not None else Membrane()
    reservoir = geometry.reservoir if geometry is not None else Reservoir()
    for key, value in (
        ("geometry.membrane.thickness_nm", membrane.thickness_nm),
        ("geometry.reservoir.radius_nm", reservoir.radius_nm),
    ):
        if not (math.isfinite(value) and value > 0.0):
            raise CaseValidationError(
                f"{key} is {value}; it is a length, finite and positive (section 5.3.1 NOTE on "
                "numerics.mesh)"
            )
    if not math.isfinite(membrane.centre_z_nm):
        raise CaseValidationError(
            f"geometry.membrane.centre_z_nm is {membrane.centre_z_nm}; it is a finite position "
            "along the axis in the structure's frame"
        )
    if mesh.wall_h_nm != "auto" and not (math.isfinite(mesh.wall_h_nm) and mesh.wall_h_nm > 0.0):
        raise CaseValidationError(
            f"numerics.mesh.wall_h_nm is {mesh.wall_h_nm}; it is `auto` or an element size in "
            "nm, finite and positive (section 5.3.1 NOTE on numerics.mesh)"
        )
    if mesh.wall_for_concentration_M is not None and mesh.wall_h_nm != "auto":
        raise CaseValidationError(
            f"numerics.mesh.wall_for_concentration_M is {mesh.wall_for_concentration_M} beside "
            f"numerics.mesh.wall_h_nm {mesh.wall_h_nm}; it sizes `auto`, and an explicit size "
            "is used as written, so it would change nothing (section 5.3.1 NOTE on numerics.mesh)"
        )


# default_ladder reads none of these from the case: flow is on from the stage-6 rung and
# the other three sit at the CoupledModel defaults, so a case setting one would be ignored.
_LADDER_PHYSICS: dict[str, bool] = {
    "flow": True,
    "variable_density": True,
    "inertia": True,
    "dielectric_gradient_forces": False,
}


def _check_ladder_can_honour(physics: Physics) -> None:
    mismatched = [
        name for name, fixed in _LADDER_PHYSICS.items() if getattr(physics, name) != fixed
    ]
    if not mismatched:
        return
    named = ", ".join(f"physics.{name}" for name in mismatched)
    raise CaseValidationError(
        f"{named} would be silently ignored by the NUM-18 ladder, which fixes the path rather "
        "than reading these from the case (flow on from stage 6, variable_density and inertia "
        "on, dielectric_gradient_forces off); set numerics.continuation: none to run a single "
        "rung with the switches as given, or set them to match the ladder"
    )


def _admitting(predicate: Callable[[str], bool]) -> str:
    names = [name for name in registered_models() if predicate(name)]
    return ", ".join(names) or "no registered model"


def _honouring(switch: str, value: bool) -> str:
    return _admitting(lambda other: value in declaration(other).switches[switch])


def _accepting(coefficient: str) -> str:
    return _admitting(lambda other: coefficient in declaration(other).coefficients)


def _check_solid_permittivity_keys(document: CaseDocument) -> None:
    named = document.physics.solid_permittivities
    refusal = fluid_permittivity_refusal(named)
    if refusal is not None:
        raise CaseValidationError(refusal)
    solids = sorted(SOLID_MATERIALS)
    for name in named:
        if name not in SOLID_MATERIALS:
            close = difflib.get_close_matches(name, solids, n=1)
            hint = f"; did you mean {close[0]!r}?" if close else ""
            raise CaseValidationError(
                f"physics.solid_permittivities names {name!r}, which is not a material of the "
                f"vocabulary; the solids are {solids}{hint}"
            )


def _check_physics_switches(document: CaseDocument) -> None:
    physics = document.physics
    model = physics.model
    declared = declaration(model)
    for name in SWITCHES:
        value = getattr(physics, name)
        honoured = declared.switches[name]
        if value not in honoured:
            admitted = " or ".join(str(choice).lower() for choice in honoured)
            raise CaseValidationError(
                f"physics.model {model!r} honours physics.{name}: {admitted} only (PHY-21), so "
                f"physics.{name} must be {admitted}; {str(value).lower()} would be recorded in "
                f"the manifest and never applied. Models honouring {str(value).lower()}: "
                f"{_honouring(name, value)}"
            )
    transition = (document.charge or Charge()).dielectric_transition_nm
    if transition > 0.0 and "solid_fraction" not in declared.coefficients:
        raise CaseValidationError(
            f"physics.model {model!r} takes no material permittivity field, so "
            f"charge.dielectric_transition_nm = {transition} nm would derive a chi stage 7 gates "
            "and the solve ignores, as it refuses inputs.eps_r (PHY-24, section 5.4.3). Models "
            f"accepting it: {_accepting('solid_fraction')}"
        )
    if physics.solid_permittivities and not declared.solids:
        raise CaseValidationError(
            f"physics.model {model!r} carries no solid materials, so "
            "physics.solid_permittivities would be recorded and never applied; it is posed on a "
            "mesh with no solid domain (PHY-21 NOTE). Models carrying solids: "
            f"{_admitting(lambda other: declaration(other).solids)}"
        )
    if document.inputs.mesh is None and not declared.solids:
        # Every region stages 5 and 6 build carries a membrane and a protein, so
        # the stage-6 gate would refuse this case -- after meshing it.
        raise CaseValidationError(
            f"physics.model {model!r} carries no solid materials, so it is posed on a mesh with "
            "no solid domain (PHY-21 NOTE), and every mesh stages 5 and 6 generate carries a "
            "membrane and a protein; supply inputs.mesh with no solid domain. Models carrying "
            f"solids: {_admitting(lambda other: declaration(other).solids)}"
        )
    wall_charge = document.boundary_conditions.wall_charge_C_m2
    if wall_charge != 0.0 and "surface_charge" not in declared.coefficients:
        raise CaseValidationError(
            f"physics.model {model!r} takes no surface charge, so "
            f"boundary_conditions.wall_charge_C_m2 = {wall_charge} would be recorded and never "
            f"applied (PHY-09). Models accepting it: {_accepting('surface_charge')}"
        )
    if document.inputs.pqr is not None and "fixed_charge" not in declared.coefficients:
        raise CaseValidationError(
            f"physics.model {model!r} takes no fixed-charge source, so inputs.pqr would be "
            "protonated into a charge stage 7 never deposits and the solve never reads (WP28 D8). "
            f"Models accepting it: {_accepting('fixed_charge')}"
        )
    for supplied, coefficient, what in (
        ("charge", "fixed_charge", "a fixed-charge source"),
        ("eps_r", "solid_fraction", "a material permittivity field"),
    ):
        if getattr(document.inputs, supplied) is not None and coefficient not in (
            declared.coefficients
        ):
            raise CaseValidationError(
                f"physics.model {model!r} takes no {what}, so inputs.{supplied} would be gated by "
                "stage 7 and recorded in the manifest while the solve ignored it (PHY-24). "
                f"Models accepting it: {_accepting(coefficient)}"
            )


def _check_unread(document: CaseDocument) -> None:
    model = declaration(document.physics.model)
    violations: list[tuple[str, object, object]] = []
    for ref in case_fields():
        path = ref.path
        if path in model.unread:
            has_default, default = schema_default(path)
            if not has_default:
                continue
            val = value_at(document, path)
            if val != default:
                violations.append((path, val, default))
    if not violations:
        return
    n = len(violations)
    model_name = document.physics.model
    if n == 1:
        header = (
            f"physics.model '{model_name}' does not read 1 key this case sets; it would be "
            "recorded in the manifest and never applied (PHY-21, section 5.4.3), so leave it "
            "at its default:"
        )
    else:
        header = (
            f"physics.model '{model_name}' does not read {n} keys this case sets; each would be "
            "recorded in the manifest and never applied (PHY-21, section 5.4.3), so leave each "
            "at its default:"
        )
    lines = [header]
    for path, val, default in violations:
        readers = [m for m in registered_models() if path not in declaration(m).unread]
        readers_str = ", ".join(sorted(readers)) or "no registered model"
        val_str = (
            "true"
            if val is True
            else ("false" if val is False else ("none" if val is None else str(val)))
        )
        def_str = (
            "true"
            if default is True
            else ("false" if default is False else ("none" if default is None else str(default)))
        )
        lines.append(f"  {path}: {val_str} (default {def_str}; read by {readers_str})")
    msg = "\n".join(lines)
    raise CaseValidationError(msg)


def _check_correction_parts(document: CaseDocument) -> None:
    decl = declaration(document.physics.model)
    violations: list[tuple[PropertyKind, str, str]] = []
    props: tuple[PropertyKind, ...] = (
        "diffusivity",
        "mobility",
        "viscosity",
        "permittivity",
        "density",
    )
    for prop in props:
        spec = getattr(document.electrolyte.corrections, prop)
        for part in ("concentration", "wall"):
            path = f"electrolyte.corrections.{prop}.{part}"
            if path in decl.unread:
                continue
            is_active = getattr(spec, part)
            if is_active is False and not applies_part(spec.model, prop, part):
                violations.append((prop, part, spec.model))
    if not violations:
        return
    n = len(violations)
    header = (
        "electrolyte.corrections switches off 1 part no correction model applies; it would be "
        "recorded in the manifest as a deviation and never applied (PHY-22), so leave it at "
        "its default, true:"
        if n == 1
        else (
            f"electrolyte.corrections switches off {n} parts no correction model applies; "
            "each would be recorded in the manifest as a deviation and never applied (PHY-22), "
            "so leave each at its default, true:"
        )
    )
    lines = [header]
    for prop, part, model in violations:
        lines.append(
            f"  electrolyte.corrections.{prop}.{part}: false ({prop} model '{model}' has no "
            f"{part} fit)"
        )
    raise CaseValidationError("\n".join(lines))


def _check_switch_partners(document: CaseDocument) -> None:
    decl = declaration(document.physics.model)
    corrections = document.electrolyte.corrections
    physics = document.physics
    lines: list[str] = []

    density = corrections.density
    density_path = "electrolyte.corrections.density"
    if (
        not physics.variable_density
        and f"{density_path}.concentration" not in decl.unread
        and not any(
            getattr(density, part) and applies_part(density.model, "density", part)
            for part in ("concentration", "wall")
        )
    ):
        lines.append(
            f"  physics.variable_density: false (density model '{density.model}' applies no "
            "fit that varies the density, so the flow is already of constant density)"
        )

    permittivity = corrections.permittivity
    permittivity_path = "electrolyte.corrections.permittivity.concentration"
    if (
        physics.dielectric_gradient_forces
        and permittivity_path not in decl.unread
        and not (
            permittivity.concentration
            and applies_part(permittivity.model, "permittivity", "concentration")
        )
    ):
        lines.append(
            "  physics.dielectric_gradient_forces: true (permittivity model "
            f"'{permittivity.model}' applies no concentration fit, so d(eps)/d(c) is zero "
            "and the force vanishes)"
        )
    if lines:
        raise CaseValidationError(
            "a switch is set beside a leaf that leaves it nothing to switch; it would be "
            "recorded in the manifest as a deviation and never applied (PHY-22), so leave "
            "each at its default or restore its partner:\n" + "\n".join(lines)
        )


def _check_driver(document: CaseDocument) -> None:
    decl = declaration(document.physics.model)
    if "electrolyte.driver" in decl.unread:
        return
    if document.electrolyte.driver == "ionic_strength":
        species = document.electrolyte.species
        if len(species) == 2 and abs(species[0].z) == 1 and abs(species[1].z) == 1:
            raise CaseValidationError(
                "electrolyte.driver: ionic_strength drives the corrections with "
                "I = 1/2 sum z_i^2 c_i, which equals the average concentration (c_1 + c_2)/2 "
                "for two species of unit valence, so it would be recorded in the manifest as "
                "a deviation and never change a number (PHY-13); leave it at its default, average"
            )


def _check_strategy(document: CaseDocument) -> None:
    model = document.physics.model
    value = document.numerics.continuation
    admitted = declaration(model).strategies
    if value in admitted:
        return
    raise CaseValidationError(
        f"physics.model {model!r} admits numerics.continuation {', '.join(admitted)} only, not "
        f"{value!r}: the NUM-18 ladder is a path through named models, and every rung from "
        "stage 6 carries the flow coupling and transport this model may not have. Write "
        f"numerics.continuation: {' or '.join(admitted)}, or choose a model admitting {value!r}: "
        f"{_admitting(lambda other: value in declaration(other).strategies)}"
    )


def _check_outputs(document: CaseDocument) -> None:
    model = document.physics.model
    declared = declaration(model).quantities
    undeclared = [word for word in document.outputs if word != "fields" and word not in declared]
    if not undeclared:
        return
    advice = (
        f"remove {', '.join(undeclared)} from outputs"
        if declared
        else "write outputs: [] or outputs: [fields]"
    )
    raise CaseValidationError(
        f"outputs asks for {', '.join(undeclared)}, which physics.model {model!r} does not "
        f"provide; it declares {', '.join(declared) or 'no quantity of interest'} (section 6.7), "
        f"so {advice}. fields, the IF-07 export, is admitted for every model"
    )


def check_operating_point(document: CaseDocument) -> None:
    """Refuse a concentration, bias or distance cap no solve could use; NaN is refused."""
    concentration = document.electrolyte.concentration_M
    if not (math.isfinite(concentration) and concentration > 0.0):
        raise CaseValidationError(
            f"electrolyte.concentration_M is {concentration!r}; it must be finite and positive"
        )
    bias = document.boundary_conditions.bias_V
    if not math.isfinite(bias):
        raise CaseValidationError(f"boundary_conditions.bias_V is {bias!r}; it must be finite")
    cap = document.numerics.wall_distance.max_distance_nm
    if not (math.isfinite(cap) and cap > 0.0):
        raise CaseValidationError(
            f"numerics.wall_distance.max_distance_nm is {cap!r}; the PHY-02 saturation distance "
            "must be finite and positive, or the wall functions are evaluated at a capped d"
        )


def check_referenced_files(document: CaseDocument, *, base: Path | None = None) -> None:
    """Verify that every external file a case document references exists on disk.

    Parameters
    ----------
    base
        The directory a relative path is taken against; the working directory when ``None``.
    """
    where = base if base is not None else Path.cwd()

    def check(key: str, path: Path | None) -> None:
        if path is not None and not (where / path).is_file():
            raise FileNotFoundError(f"{key} '{where / path}' does not exist")

    # Every ``inputs:`` key, read from the schema: a key added later is checked too.
    for leaf in type(document.inputs).model_fields:
        supplied = getattr(document.inputs, leaf)
        if supplied is not None:
            check(f"inputs.{leaf}.path", supplied.path)

    if document.structure is not None:
        if document.structure.source is not None:
            check("structure.source.path", document.structure.source.path)
        if document.structure.ensemble is not None:
            check("structure.ensemble.trajectory", document.structure.ensemble.trajectory)

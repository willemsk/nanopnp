"""The case checks that need the installed registries or this release, beyond the schema."""

from __future__ import annotations

import difflib
import math
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from nanopnp.charge.edits import TitratableGroups, variant_parent
from nanopnp.charge.fields import FIELD_FORMAT
from nanopnp.core.paths import available_corrections
from nanopnp.io.case import (
    CORRECTION_PROPERTIES,
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
from nanopnp.io.resolved import ResolvedCase, contour_spacing_nm
from nanopnp.materials.electrolyte import NO_STERIC_MODEL, Electrolyte
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
from nanopnp.physics.steric import registered_steric_models
from nanopnp.post.outputs import provided, registered_outputs

__all__ = [
    "APPLIED_WALLS",
    "ELEMENT_LABELS",
    "check_document",
    "check_exclusion_offset",
    "check_operating_point",
    "check_referenced_files",
    "check_species",
    "element_orders",
    "options_at",
    "registry_options",
    "require_runnable",
]


_SLIP = "boundary_conditions.walls.slip"
_ION_FLUX = "boundary_conditions.walls.ion_flux"
APPLIED_WALLS: dict[str, str] = {_SLIP: "no_slip", _ION_FLUX: "no_flux"}
"""The one value of each wall condition the release applies; require_runnable refuses the rest."""


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
    if path == _STERIC_MODEL_PATH:
        return (NO_STERIC_MODEL, *registered_steric_models())
    if path in _CORRECTION_MODEL_PATHS:
        # ``none`` disables a correction by selecting the registered ``none``
        # model rather than by taking a code branch (PHY-22), so it is offered
        # beside the installed parameter files and is not one of them.
        return ("none", *available_corrections())
    if path == "outputs":
        return registered_outputs()
    return None


_STERIC_MODEL_PATH = "electrolyte.corrections.steric.model"


_CORRECTION_MODEL_PATHS: frozenset[str] = frozenset(
    f"electrolyte.corrections.{name}.model" for name in CORRECTION_PROPERTIES
)


def check_document(document: CaseDocument, *, source: str | None = None) -> CaseDocument:
    """Check a schema-valid document against the registries and element orders."""
    problems: list[str] = []
    if document.physics.model not in registered_models():
        problems.append(
            f"physics.model {document.physics.model!r} is not registered. "
            f"Use one of: {', '.join(registered_models())}."
        )
    if document.numerics.mesh.backend not in registered_meshers():
        problems.append(
            f"numerics.mesh.backend {document.numerics.mesh.backend!r} is not a registered "
            f"mesher. Use one of: {', '.join(registered_meshers())}."
        )
    if document.numerics.stabilisation not in registered_stabilisations():
        problems.append(
            f"numerics.stabilisation {document.numerics.stabilisation!r} is not a registered "
            f"mode. Use one of: {', '.join(registered_stabilisations())}. "
            "A mode that the solver does not apply makes the FR-25 manifest "
            "describe a run that did not happen."
        )
    steric = document.electrolyte.corrections.steric.model
    if steric not in (NO_STERIC_MODEL, *registered_steric_models()):
        problems.append(
            f"{_STERIC_MODEL_PATH} {steric!r} is not a registered steric model. "
            f"Use one of: {', '.join((NO_STERIC_MODEL, *registered_steric_models()))}."
        )
    unknown = sorted(set(document.outputs) - set(registered_outputs()))
    if unknown:
        problems.append(
            f"outputs {', '.join(unknown)} are not selectable. "
            f"Use these outputs: {', '.join(registered_outputs())}."
        )
    solver = document.numerics.linear.solver
    if solver not in registered_solvers():
        reason = rejection(solver)
        problems.append(
            f"numerics.linear.solver {solver!r} is not usable: {reason.rstrip('.')}."
            if reason is not None
            else f"numerics.linear.solver {solver!r} is not available. "
            f"Use one of: {', '.join(registered_solvers())}."
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
                    "ctx": {"error": ValueError(" ".join(problems))},
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
            f"{elements.phi!r}. This release uses one order for phi and c_i, because the "
            "NUM-02 log branch and the PHY-05 steric term both assume it. Set the two to the "
            "same order."
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
    if path.startswith("numerics.elements."):
        return ELEMENT_LABELS
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

ELEMENT_LABELS: tuple[str, ...] = tuple(_ORDERS)
"""The element labels ``numerics.elements`` accepts, lowest order first."""


PROFILE_KEYS: tuple[str, ...] = ("exclusion_offset_nm", "dielectric_transition_nm")


SMEARING_KEYS: tuple[str, ...] = ("sharpness", "grid_spacing_nm")


PROTONATION_KEYS: tuple[str, ...] = ("ph", "forcefield", "titration")


def _order(label: str, field: str) -> int:
    try:
        return _ORDERS[label]
    except KeyError:
        raise CaseValidationError(
            f"numerics.elements.{field} {label!r} is not an element label. "
            f"Use one of: {', '.join(sorted(_ORDERS))}."
        ) from None


def check_species(document: CaseDocument, electrolyte: Electrolyte) -> None:
    """Check species, steric diameters and temperature against the parameter file."""
    problems: list[str] = []
    temperature_K = document.electrolyte.temperature_K
    if temperature_K != electrolyte.temperature_K:
        problems.append(
            f"electrolyte.temperature_K is {temperature_K} K, but "
            f"{document.electrolyte.parameters!r} is fitted at {electrolyte.temperature_K} K. "
            "The solve takes every material property and V_T from the file. Set temperature_K: "
            f"{electrolyte.temperature_K}. Or supply a parameter file that is fitted at the "
            "temperature that you want."
        )
    for index, species in enumerate(document.electrolyte.species):
        valence = electrolyte.ion(species.name).valence
        if valence != species.z:
            problems.append(
                f"electrolyte.species[{index}].z is {species.z:+d} for {species.name!r}, but "
                f"{document.electrolyte.parameters!r} gives {valence:+d}. Set z to {valence:+d}."
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
                    f"(species[{index}]). The diameters are fitted parameters of the correction "
                    "file. The case file cannot override them (FR-16). Remove a_ion_nm."
                )
    if steric.a_water_nm is not None:
        given_m = steric.a_water_nm * 1e-9
        if abs(electrolyte.water_steric_diameter - given_m) > 1e-15:
            problems.append(
                f"electrolyte.corrections.steric.a_water_nm is {steric.a_water_nm} nm, but "
                f"{document.electrolyte.parameters!r} gives "
                f"{electrolyte.water_steric_diameter * 1e9} nm. Remove a_water_nm."
            )
    if problems:
        raise CaseValidationError(" ".join(problems))


def require_runnable(document: CaseDocument) -> SuppliedArtefact | None:  # noqa: C901
    """Reject every section this release does not run; return the supplied mesh, if any."""
    _check_charge(document)
    for supplied in ("charge", "eps_r"):
        given: SuppliedArtefact | None = getattr(document.inputs, supplied)
        if given is not None and given.path is None:
            # Stage 7 reads a supplied field by path only; refused here so that
            # ``nanopnp validate case`` sees what ``run`` would.
            raise stored_artefact_refused(supplied)
    stored = document.inputs.mesh
    if stored is not None and stored.artefact is not None and (stored.format or stored.groups):
        raise CaseValidationError(
            "inputs.mesh.artefact names a stage-6 artefact that is in the store. That artefact "
            "has its own format and vocabulary mapping. Remove inputs.mesh.format and "
            "inputs.mesh.groups."
        )
    for supplied, what in SUPPLIED_FIELDS.items():
        field: SuppliedArtefact | None = getattr(document.inputs, supplied)
        if field is None:
            continue
        if field.groups:
            raise CaseValidationError(
                f"inputs.{supplied}.groups is the vocabulary mapping of the mesh (IF-06). It "
                f"means nothing for {what}. A header document names a field, and it holds the "
                "quantity and the units (section 5.3.1 NOTE). "
                f"Remove inputs.{supplied}.groups."
            )
        if field.format not in (None, FIELD_FORMAT):
            raise CaseValidationError(
                f"inputs.{supplied}.format is {field.format!r}. A header document names a "
                f"supplied field, so the format must be {FIELD_FORMAT!r}. The program reads the "
                "data format from the data.format key of the document (section 5.3.1 NOTE). "
                f"Set inputs.{supplied}.format to {FIELD_FORMAT!r}."
            )
    if document.structure is not None and document.inputs.mesh is not None:
        raise CaseValidationError(
            f"case {document.name!r} has a structure: section and supplies inputs.mesh. A "
            "stage whose output is supplied does not run. Nothing upstream of it runs. The "
            "structure is recorded as an input to a run that never read it "
            "(section 5.3.1 NOTE on inputs:). Remove one of them."
        )
    _check_pore(document)
    if document.geometry is not None and document.inputs.mesh is not None:
        raise CaseValidationError(
            f"case {document.name!r} has a geometry: section and supplies inputs.mesh. A "
            "stage whose output is supplied does not run. Nothing upstream of it runs. The "
            "geometry is recorded as an input to a run that never read it "
            "(section 5.3.1 NOTE on geometry.density). Remove one of them."
        )
    _check_profile(document)
    if (
        document.inputs.mesh is None
        and document.structure is None
        and document.inputs.profile is None
        and (document.geometry is None or document.geometry.pore is None)
    ):
        raise CaseValidationError(
            f"case {document.name!r} names no geometry. It supplies neither inputs.mesh nor "
            "inputs.profile. It declares no geometry.pore and has no structure: section. "
            "There is nothing to mesh and no mesh to solve on (section 5.3.1 NOTE on inputs:). "
            "Add one of them."
        )
    if document.inputs.mesh is None:
        _check_generation(document)
    mesh = document.inputs.mesh
    nonlinear = document.numerics.nonlinear
    if nonlinear.strategy != "newton":
        raise UnsupportedCaseSection(
            f"numerics.nonlinear.strategy {nonlinear.strategy!r} selects the hybrid segregated "
            "fallback of NUM-20. No release of SPECIFICATION.md schedules it. The monolithic "
            "damped Newton method of NUM-16 solves every rung. Set strategy: newton."
        )
    if nonlinear.damping != "residual":
        raise UnsupportedCaseSection(
            f"numerics.nonlinear.damping {nonlinear.damping!r} selects the damped Newton method "
            "of NUM-20 with l2 backtracking. No release of SPECIFICATION.md schedules it. The "
            "damping is the one of NUM-16, adapted on residual reduction. The reference records "
            "its recovery rule. Set damping: residual."
        )
    walls = document.boundary_conditions.walls
    if (walls.slip, walls.ion_flux) != (APPLIED_WALLS[_SLIP], APPLIED_WALLS[_ION_FLUX]):
        # Nothing downstream reads the wall values: the forms pose no-slip and
        # no-flux unconditionally, so any other value would be recorded in the
        # manifest without being applied (section 5.3.1 NOTE on walls).
        raise UnsupportedCaseSection(
            f"boundary_conditions.walls asks for slip: {walls.slip} and ion_flux: "
            f"{walls.ion_flux}. This release applies slip: no_slip and ion_flux: no_flux only. "
            "No release of SPECIFICATION.md section 3 schedules the others yet. Set slip: "
            "no_slip and ion_flux: no_flux."
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
                f"boundary_conditions.wall_charge_C_m2 is {charge} with no geometry.pore. It is "
                f"the surface charge of the wall of an idealised pore. Nothing else has one "
                f"({note}). Remove it, or add geometry.pore."
            )
        return
    for name, present in (
        ("structure:", document.structure is not None),
        ("inputs.profile", document.inputs.profile is not None),
        ("inputs.mesh", document.inputs.mesh is not None),
    ):
        if present:
            raise CaseValidationError(
                f"geometry.pore and {name} are both given. An idealised pore is the geometry. "
                f"{name} is a second geometry ({note}). Remove one of them."
            )
    assert geometry is not None
    if pore.radius_nm >= geometry.reservoir.radius_nm:
        raise CaseValidationError(
            f"geometry.pore.radius_nm is {pore.radius_nm} nm. It is not below "
            f"geometry.reservoir.radius_nm {geometry.reservoir.radius_nm} nm. The lumen opens "
            f"into a larger reservoir ({note}). Set a pore radius below the reservoir radius."
        )
    if "membrane" not in document.physics.solid_permittivities:
        raise CaseValidationError(
            "physics.solid_permittivities.membrane is not set. The solid around an idealised "
            "pore is the membrane domain. The program takes an unlisted solid as ion-free "
            f"water ({note}). Set its relative permittivity."
        )
    if geometry.membrane.centre_z_nm != 0.0:
        raise CaseValidationError(
            f"geometry.membrane.centre_z_nm is {geometry.membrane.centre_z_nm} with "
            "geometry.pore. It is a position in the frame of a structure. The pore sits at 0 "
            f"({note}). Remove geometry.membrane.centre_z_nm."
        )
    for key, default in (("density", Density()), ("contour", Contour())):
        if getattr(geometry, key) != default:
            raise CaseValidationError(
                f"geometry.{key} is set beside geometry.pore. Stages 2 to 4 read it. An "
                f"idealised pore skips these stages ({note}). Remove it."
            )
    backend = document.numerics.mesh.backend
    if backend != "netgen":
        raise CaseValidationError(
            f"numerics.mesh.backend is {backend!r} beside geometry.pore. The size field of an "
            f"idealised pore works with netgen only ({note}). Set numerics.mesh.backend: netgen."
        )
    for name, value in document.numerics.mesh.sizes.model_dump().items():
        if value is not None:
            raise CaseValidationError(
                f"numerics.mesh.sizes.{name} is {value} beside geometry.pore. An idealised pore "
                "is meshed at the global and wall sizes only. It has no such part, so the key "
                f"changes nothing ({note}). Remove it."
            )


def _check_charge(document: CaseDocument) -> None:
    pqr = document.inputs.pqr
    if pqr is not None:
        if pqr.path is None:
            raise CaseValidationError(
                "inputs.pqr: artefact: names a protonation artefact in the store. A structure: "
                "section reaches the artefact of the stage. A supplied PQR file is named by "
                "inputs.pqr: path: (section 5.3.1 NOTE on inputs:). Set inputs.pqr: path: "
                "instead."
            )
        if pqr.groups:
            raise CaseValidationError(
                "inputs.pqr.groups is the vocabulary mapping of the mesh (IF-06). It means "
                "nothing for a PQR file (section 5.3.1 NOTE on inputs:). Remove it."
            )
        if pqr.format not in (None, PQR_FORMAT):
            raise CaseValidationError(
                f"inputs.pqr.format is {pqr.format!r}. A supplied PQR file of one frame, or of "
                f"one MODEL per frame, has the format {PQR_FORMAT!r} (section 5.3.1 NOTE on "
                f"inputs:). Set inputs.pqr.format to {PQR_FORMAT!r}."
            )
    charge = document.charge
    if charge is None:
        return
    _check_edits(document, charge)
    defaults = Charge()
    _check_profile_keys(document, charge)
    _check_smearing(document, charge.smearing, defaults.smearing)
    if charge.titration == "none" and charge.ph != defaults.ph:
        raise CaseValidationError(
            f"charge.ph is {charge.ph} beside charge.titration: none. This setting runs PDB2PQR "
            "without a titration method, so the pH reaches no calculation. Remove charge.ph, "
            "or set charge.titration: propka (section 5.3.1 NOTE on the protonation keys)."
        )
    changed = [
        f"charge.{key}"
        for key in PROTONATION_KEYS
        if getattr(charge, key) != getattr(defaults, key)
    ]
    if not changed:
        return
    density = document.geometry.density if document.geometry is not None else Density()
    # Under the protonated density the stage runs for stage 2 even where the charge is supplied.
    feeds_density = document.structure is not None and density.atoms == "protonated"
    where = (
        "beside inputs.pqr. That input supplies the charges and radii that PDB2PQR computes "
        "otherwise"
        if pqr is not None
        else "beside inputs.charge with geometry.density.atoms: as_loaded. These leave nothing "
        "for the protonation to feed"
        if document.inputs.charge is not None and not feeds_density
        else "in a case with neither a structure: section nor inputs.pqr. There is nothing "
        "to protonate"
        if document.structure is None
        else None
    )
    if where is not None:
        raise CaseValidationError(
            f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set {where}. The "
            "protonation stage that the keys configure does not run, so the keys have no "
            "effect (section 5.3.1 NOTE on the protonation keys). Remove the keys."
        )


STATE_RESIDUES: frozenset[str] = frozenset({"ASP", "GLU", "HIS"})
"""The parents whose protonation state a charge edit can fix (PDB2PQR's ASH, GLH and HIP)."""


def _check_edits(document: CaseDocument, charge: Charge) -> None:
    if not charge.edits:
        return
    groups = TitratableGroups.load()
    note = "section 5.3.1 NOTE on charge.edits"
    where = (
        "beside inputs.charge. That input supplies the fixed charge that the edit changes"
        if document.inputs.charge is not None
        else "in a case with neither a structure: section nor inputs.pqr. There is no "
        "protonation to edit"
        if document.structure is None and document.inputs.pqr is None
        else None
    )
    if where is not None:
        raise CaseValidationError(f"charge.edits is set {where} ({note}). Remove it.")
    # Keyed on the parsed residue, so 'ASP 021' is the residue 'ASP 21' names.
    seen: dict[tuple[tuple[str, int, str], str], int] = {}
    for index, edit in enumerate(charge.edits):
        name = f"charge.edits[{index}] ({edit.residue})"
        residue = edit.residue_parts
        parent = residue[0]
        named = variant_parent(parent)
        if named is not None:
            raise CaseValidationError(
                f"{name}: {parent} is a protonation-variant name. An edit names the residue by "
                f"its parent, {named} ({note}). Use {named} as the residue name."
            )
        if edit.state is not None:
            reason = (
                f"on {parent}. This residue has no ASH, GLH or HIP state to fix"
                if parent not in STATE_RESIDUES
                else "beside titration: none. That setting runs PDB2PQR without a titration method"
                if charge.titration == "none"
                else f"under the force field {charge.forcefield}. That force field has no "
                "state to fix"
                if charge.forcefield != "CHARMM"
                else "beside inputs.pqr. That input supplies the states that PDB2PQR computes "
                "otherwise"
                if document.inputs.pqr is not None
                else None
            )
            if reason is not None:
                raise CaseValidationError(f"{name}: state is refused {reason} ({note}). Remove it.")
        if edit.charge_change_e is not None and not groups.has_group(parent):
            raise CaseValidationError(
                f"{name}: charge_change_e is refused. {parent} has no titratable group to place "
                f"the change on. The groups are {', '.join(sorted(groups.groups))} ({note}). "
                "Name a residue of one of these groups."
            )
        for kind in ("state", "charge", "radius"):
            earlier = seen.get((residue, kind))
            same = kind == edit.kind
            clash = {edit.kind, kind} == {"state", "charge"}
            if earlier is not None and (same or clash):
                raise CaseValidationError(
                    f"{name} clashes with charge.edits[{earlier}] ({note}). "
                    + (
                        f"Use one {kind} edit for each residue."
                        if same
                        else "Do not set state and charge_change_e on one residue."
                    )
                )
        seen[(residue, edit.kind)] = index


def _check_profile_keys(document: CaseDocument, charge: Charge) -> None:
    changed = [f"charge.{key}" for key in PROFILE_KEYS if getattr(charge, key) != 0.0]
    if not changed:
        return
    named = f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set away from 0"
    if document.inputs.mesh is not None:
        raise CaseValidationError(
            f"{named} beside inputs.mesh. Both are built from the stage-4 profile. A supplied "
            "mesh has no profile, so the keys have no effect (section 5.3.1 NOTE on the "
            "v2 keys that change a number). Remove the keys."
        )
    if document.structure is None and document.inputs.profile is None:
        raise CaseValidationError(
            f"{named} in a case with neither a structure: section nor inputs.profile. Both are "
            "built from the stage-4 profile. The case has no profile (section 5.3.1 NOTE on "
            "the v2 keys that change a number). Add a structure: section or inputs.profile, "
            "or remove the keys."
        )
    if charge.dielectric_transition_nm > 0.0 and document.inputs.eps_r is not None:
        raise CaseValidationError(
            f"charge.dielectric_transition_nm is {charge.dielectric_transition_nm} nm beside "
            "inputs.eps_r. Both supply the solid fraction chi, so the case names one quantity "
            "twice (section 5.3.1 NOTE on the v2 keys that change a number). Remove one of them."
        )
    h_c = contour_spacing_nm(document)
    delta = charge.dielectric_transition_nm
    if 0.0 < delta < h_c:
        raise CaseValidationError(
            f"charge.dielectric_transition_nm is {delta} nm, below "
            f"geometry.density.grid_spacing_nm = {h_c} nm. The transition is finer than the "
            "grid that places the contour (section 4.4 NOTE on the derived solid fraction). "
            f"Set it to {h_c} nm or more."
        )


def check_exclusion_offset(resolved: ResolvedCase) -> None:
    """Refuse an ion-exclusion offset of at most twice the shell's resolution ``h_c``.

    Raises
    ------
    CaseValidationError
        Naming the offset, ``h_c`` and where ``h_c`` comes from: the density grid, or a supplied
        outline's recorded point spacing.
    """
    offset = resolved.exclusion_offset_nm
    h_c = resolved.shell_spacing_nm
    if not 0.0 < offset <= 2.0 * h_c:
        return
    recorded = resolved.outline_spacing_nm
    if recorded is None:
        source = f"geometry.density.grid_spacing_nm = {h_c} nm"
    else:
        assert resolved.profile is not None
        source = f"h_c = {h_c} nm, the point spacing that inputs.profile {resolved.profile.path} "
        if recorded == h_c:
            source += "records"
        else:
            bound, ruling = ("coarsest", "AR6") if h_c < recorded else ("finest", "AR9")
            source += (
                f"records, {recorded:g} nm, held at the {bound} "
                f"geometry.density.grid_spacing_nm (section 8.2.42 {ruling})"
            )
    raise CaseValidationError(_offset_refusal(offset, h_c, source))


def _offset_refusal(offset: float, h_c: float, source: str) -> str:
    return (
        f"charge.exclusion_offset_nm is {offset} nm, at most twice {source}. The shell is a face "
        "of width a. The feature-size criterion of section 5.2.1 admits nothing narrower than "
        f"2 h_c = {2.0 * h_c:g} nm (section 5.2.1 NOTE on the ion-exclusion shell). "
        f"Set it above {2.0 * h_c:g} nm."
    )


def _check_smearing(document: CaseDocument, smearing: Smearing, defaults: Smearing) -> None:
    if smearing.axis_cutoff_nm != defaults.axis_cutoff_nm:
        raise CaseValidationError(
            f"charge.smearing.axis_cutoff_nm is {smearing.axis_cutoff_nm}. The program refuses "
            f"every value other than its default {defaults.axis_cutoff_nm}, on every path "
            "(PHY-18). The deposited kernel is regular on the axis and takes no guard. A "
            "supplied field declares its own axis_cutoff_nm in its header document. The key "
            "changes nothing (section 5.3.1 NOTE on charge.smearing). Remove it."
        )
    for key in SMEARING_KEYS:
        value = getattr(smearing, key)
        if not 0.0 < value < math.inf:
            raise CaseValidationError(
                f"charge.smearing.{key} is {value}. It must be finite and positive (PHY-16 "
                "steps 4-6)."
            )
    changed = [
        f"charge.smearing.{key}"
        for key in SMEARING_KEYS
        if getattr(smearing, key) != getattr(defaults, key)
    ]
    if not changed:
        return
    where = (
        "beside inputs.charge. That input supplies the field that stage 7 deposits otherwise"
        if document.inputs.charge is not None
        else "in a case with neither a structure: section nor inputs.pqr. There is nothing "
        "to deposit"
        if document.structure is None and document.inputs.pqr is None
        else None
    )
    if where is not None:
        other = "inputs.charge" if document.inputs.charge is not None else "structure:"
        raise CaseValidationError(
            f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set {where} "
            f"({other}). Stage 7 does not run the deposition that the keys configure, so the "
            "keys have no effect (section 5.3.1 NOTE on charge.smearing). Remove the keys."
        )


def _check_profile(document: CaseDocument) -> None:
    profile = document.inputs.profile
    if profile is None:
        return
    if profile.path is None:
        raise CaseValidationError(
            "inputs.profile: artefact: names a profile in the store. A structure: section "
            "reaches the artefact of stage 4. A supplied profile is named by "
            "inputs.profile: path: (section 5.3.1 NOTE on inputs:). Set inputs.profile: path: "
            "instead."
        )
    if profile.groups:
        raise CaseValidationError(
            "inputs.profile.groups is the vocabulary mapping of the mesh (IF-06). It means "
            "nothing for a profile. Stage 5 names the one boundary of a profile itself "
            "(section 5.3.1 NOTE on inputs:). Remove it."
        )
    if profile.format not in (None, PROFILE_FORMAT):
        raise CaseValidationError(
            f"inputs.profile.format is {profile.format!r}. A supplied profile is a "
            f"nanopnp/profile/v0.5 document with the format {PROFILE_FORMAT!r} (section 5.3.1 "
            f"NOTE on inputs:). Set inputs.profile.format to {PROFILE_FORMAT!r}."
        )
    geometry = document.geometry
    if geometry is None:
        return
    for key, default in (("density", Density()), ("contour", Contour())):
        if getattr(geometry, key) != default:
            raise CaseValidationError(
                f"geometry.{key} is set beside inputs.profile. Stages 2 to 4 read it. A "
                "supplied profile means that these stages do not run, so the key has no effect "
                "(section 5.3.1 NOTE on inputs:). Remove it."
            )


def _check_generation(document: CaseDocument) -> None:
    mesh = document.numerics.mesh
    if mesh.boundary_layer:
        raise UnsupportedCaseSection(
            "numerics.mesh.boundary_layer is true. A boundary layer is FR-11, after v1.0. "
            "The reference mesh used none. It used isotropic grading to the wall "
            "(section 5.2.2). Set it to false."
        )
    geometry = document.geometry
    if geometry is not None and geometry.analyte is not None:
        raise UnsupportedCaseSection(
            f"geometry.analyte is a {geometry.analyte.shape}. An analyte in a generated region "
            "is FR-21, v0.12. The benchmark geometries embed one (PHY-11). "
            "Remove geometry.analyte."
        )
    membrane = geometry.membrane if geometry is not None else Membrane()
    reservoir = geometry.reservoir if geometry is not None else Reservoir()
    for key, value in (
        ("geometry.membrane.thickness_nm", membrane.thickness_nm),
        ("geometry.reservoir.radius_nm", reservoir.radius_nm),
    ):
        if not (math.isfinite(value) and value > 0.0):
            raise CaseValidationError(
                f"{key} is {value}. It is a length. It must be finite and positive "
                "(section 5.3.1 NOTE on numerics.mesh)."
            )
    if not math.isfinite(membrane.centre_z_nm):
        raise CaseValidationError(
            f"geometry.membrane.centre_z_nm is {membrane.centre_z_nm}. It must be a finite "
            "position along the axis in the frame of the structure."
        )
    if mesh.wall_h_nm != "auto" and not (math.isfinite(mesh.wall_h_nm) and mesh.wall_h_nm > 0.0):
        raise CaseValidationError(
            f"numerics.mesh.wall_h_nm is {mesh.wall_h_nm}. It must be `auto`, or an element "
            "size in nm that is finite and positive (section 5.3.1 NOTE on numerics.mesh)."
        )
    if mesh.wall_for_concentration_M is not None and mesh.wall_h_nm != "auto":
        raise CaseValidationError(
            f"numerics.mesh.wall_for_concentration_M is {mesh.wall_for_concentration_M} beside "
            f"numerics.mesh.wall_h_nm {mesh.wall_h_nm}. It sizes `auto`. The program uses an "
            "explicit size as written, so the key changes nothing (section 5.3.1 NOTE on "
            "numerics.mesh). Remove it."
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
        f"The NUM-18 ladder ignores {named}. The ladder fixes the path. It does not read "
        "these keys from the case. It sets flow on from stage 6, variable_density and inertia "
        "on, and dielectric_gradient_forces off. Set numerics.continuation: none to run a "
        "single rung with the switches as given. Or set the switches to match the ladder."
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
            hint = f" A close name is {close[0]!r}." if close else ""
            raise CaseValidationError(
                f"physics.solid_permittivities names {name!r}. That name is not a material of "
                f"the vocabulary. The solids are {solids}.{hint}"
            )


def _check_physics_switches(document: CaseDocument) -> None:
    physics = document.physics
    model = physics.model
    declared = declaration(model)
    if physics.dielectric_gradient_forces and not physics.flow:
        remedy = (
            "Set physics.flow: true, or set physics.dielectric_gradient_forces: false."
            if True in declared.switches["flow"]
            else f"physics.model {model!r} has no flow. Set physics.dielectric_gradient_forces: "
            "false."
        )
        raise CaseValidationError(
            "physics.dielectric_gradient_forces is true, but the flow is off. PHY-23 adds the "
            "force on the fluid and the term in each ion's flux together. A model with no flow "
            f"has no force term. {remedy}"
        )
    for name in SWITCHES:
        value = getattr(physics, name)
        honoured = declared.switches[name]
        if value not in honoured:
            admitted = " or ".join(str(choice).lower() for choice in honoured)
            raise CaseValidationError(
                f"physics.model {model!r} accepts physics.{name}: {admitted} only (PHY-21). "
                f"physics.{name} must be {admitted}. The manifest records "
                f"{str(value).lower()} and the run does not apply it. Models that accept "
                f"{str(value).lower()}: {_honouring(name, value)}"
            )
    transition = (document.charge or Charge()).dielectric_transition_nm
    if transition > 0.0 and "solid_fraction" not in declared.coefficients:
        raise CaseValidationError(
            f"physics.model {model!r} takes no material permittivity field. "
            f"charge.dielectric_transition_nm = {transition} nm derives a chi that stage 7 "
            "gates and the solve ignores, as it refuses inputs.eps_r (PHY-24, section 5.4.3). "
            "Set it to 0, or use a model that accepts it: "
            f"{_accepting('solid_fraction')}"
        )
    if physics.solid_permittivities and not declared.solids:
        raise CaseValidationError(
            f"physics.model {model!r} has no solid materials. It works on a mesh with no solid "
            "domain (PHY-21 NOTE). The manifest records physics.solid_permittivities and the "
            "run does not apply it. Remove it, or use a model that has solids: "
            f"{_admitting(lambda other: declaration(other).solids)}"
        )
    if document.inputs.mesh is None and not declared.solids:
        # Every region stages 5 and 6 build carries a membrane and a protein, so
        # the stage-6 gate would refuse this case -- after meshing it.
        raise CaseValidationError(
            f"physics.model {model!r} has no solid materials. It works on a mesh with no solid "
            "domain (PHY-21 NOTE). Every mesh that stages 5 and 6 generate has a membrane and "
            "a protein. Supply inputs.mesh with no solid domain, or use a model that has "
            f"solids: {_admitting(lambda other: declaration(other).solids)}"
        )
    wall_charge = document.boundary_conditions.wall_charge_C_m2
    if wall_charge != 0.0 and "surface_charge" not in declared.coefficients:
        raise CaseValidationError(
            f"physics.model {model!r} takes no surface charge. The manifest records "
            f"boundary_conditions.wall_charge_C_m2 = {wall_charge} and the run does not apply "
            "it (PHY-09). Set it to 0, or use a model that accepts it: "
            f"{_accepting('surface_charge')}"
        )
    if document.inputs.pqr is not None and "fixed_charge" not in declared.coefficients:
        raise CaseValidationError(
            f"physics.model {model!r} takes no fixed-charge source. The protonation of "
            "inputs.pqr makes a charge that stage 7 does not deposit. The solve does not read "
            "it (WP28 D8). Remove inputs.pqr, or use a model that accepts it: "
            f"{_accepting('fixed_charge')}"
        )
    for supplied, coefficient, what in (
        ("charge", "fixed_charge", "a fixed-charge source"),
        ("eps_r", "solid_fraction", "a material permittivity field"),
    ):
        if getattr(document.inputs, supplied) is not None and coefficient not in (
            declared.coefficients
        ):
            raise CaseValidationError(
                f"physics.model {model!r} takes no {what}. Stage 7 gates inputs.{supplied} and "
                "the manifest records it, but the solve ignores it (PHY-24). "
                f"Remove inputs.{supplied}, or use a model that accepts it: "
                f"{_accepting(coefficient)}"
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
            f"physics.model '{model_name}' does not read 1 key that this case sets. The "
            "manifest records the key and the run does not apply it (PHY-21, section 5.4.3). "
            "Set the key to its default:"
        )
    else:
        header = (
            f"physics.model '{model_name}' does not read {n} keys that this case sets. The "
            "manifest records each key and the run does not apply any of them (PHY-21, "
            "section 5.4.3). Set each key to its default:"
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
        "electrolyte.corrections switches off 1 part that no correction model applies. The "
        "manifest records it as a deviation and the run does not apply it (PHY-22). Set it "
        "to its default, true:"
        if n == 1
        else (
            f"electrolyte.corrections switches off {n} parts that no correction model applies. "
            "The manifest records each as a deviation and the run does not apply any of them "
            "(PHY-22). Set each part to its default, true:"
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
            "fit that changes the density. The flow has a constant density)"
        )

    permittivity = corrections.permittivity
    permittivity_path = "electrolyte.corrections.permittivity.concentration"
    # A solid fraction's step, (eps_p - eps_r,f) grad(chi), is a force with no fluid fit (PHY-23).
    # A derived chi reaches the electrolyte only where its half-width passes the exclusion shell,
    # which is not electrolyte: neither term is assembled in it.
    charge = document.charge or Charge()
    blended = document.inputs.eps_r is not None or (
        charge.dielectric_transition_nm / 2.0 > charge.exclusion_offset_nm
    )
    if (
        physics.dielectric_gradient_forces
        and not blended
        and permittivity_path not in decl.unread
        and not (
            permittivity.concentration
            and applies_part(permittivity.model, "permittivity", "concentration")
        )
    ):
        lines.append(
            "  physics.dielectric_gradient_forces: true (permittivity model "
            f"'{permittivity.model}' applies no concentration fit. d(eps)/d(c) is zero, so "
            "the force is zero)"
        )
    if lines:
        raise CaseValidationError(
            "A switch is set beside a leaf that leaves it nothing to switch. The manifest "
            "records it as a deviation and the run does not apply it (PHY-22). Set each switch "
            "to its default, or restore its partner:\n" + "\n".join(lines)
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
                "I = 1/2 sum z_i^2 c_i. For two species of unit valence, this equals the "
                "average concentration (c_1 + c_2)/2. The manifest records the setting as a "
                "deviation and it changes no number (PHY-22). Set it to its default, average."
            )


def _check_strategy(document: CaseDocument) -> None:
    model = document.physics.model
    value = document.numerics.continuation
    admitted = declaration(model).strategies
    if value in admitted:
        return
    raise CaseValidationError(
        f"physics.model {model!r} accepts numerics.continuation {', '.join(admitted)} only, "
        f"not {value!r}. The NUM-18 ladder is a path through named models. Every rung from "
        "stage 6 carries the flow coupling and transport, and this model can lack them. Set "
        f"numerics.continuation: {' or '.join(admitted)}, or choose a model that accepts "
        f"{value!r}: {_admitting(lambda other: value in declaration(other).strategies)}"
    )


def _check_outputs(document: CaseDocument) -> None:
    model = document.physics.model
    offered = provided(declaration(model))
    unoffered = [
        word for word in document.outputs if word in registered_outputs() and word not in offered
    ]
    if not unoffered:
        return
    raise CaseValidationError(
        f"outputs asks for {', '.join(unoffered)}. physics.model {model!r} does not provide "
        f"these outputs. It provides {', '.join(offered)} (section 6.7). Remove "
        f"{', '.join(unoffered)} from outputs."
    )


def check_operating_point(document: CaseDocument) -> None:
    """Refuse a concentration, bias or distance cap no solve could use; NaN is refused."""
    concentration = document.electrolyte.concentration_M
    if not (math.isfinite(concentration) and concentration > 0.0):
        raise CaseValidationError(
            f"electrolyte.concentration_M is {concentration!r}. It must be finite and positive."
        )
    bias = document.boundary_conditions.bias_V
    if not math.isfinite(bias):
        raise CaseValidationError(f"boundary_conditions.bias_V is {bias!r}. It must be finite.")
    cap = document.numerics.wall_distance.max_distance_nm
    if not (math.isfinite(cap) and cap > 0.0):
        raise CaseValidationError(
            f"numerics.wall_distance.max_distance_nm is {cap!r}. It is the PHY-02 saturation "
            "distance, where the wall functions cap d. It must be finite and positive."
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

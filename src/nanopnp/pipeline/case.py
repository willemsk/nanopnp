"""Loading a case and resolving it to the objects a run is made of."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from nanopnp.core.paths import correction_source, names_a_path
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.density.map import GRID_SPACING_RANGE_NM
from nanopnp.geometry.profile import load_profile
from nanopnp.io import case as schema
from nanopnp.io.artefact import CaseArtefact, StageInputs
from nanopnp.io.case import (
    CORRECTION_PROPERTIES,
    CaseDocument,
    CaseValidationError,
    Charge,
    Contour,
    Density,
    Geometry,
    SuppliedArtefact,
)
from nanopnp.io.case_paths import value_at
from nanopnp.io.models import read_case, read_case_text
from nanopnp.io.resolved import (
    ResolvedCase,
    ResolvedEdit,
    ResolvedProtonation,
    ResolvedStructure,
    parse_chain_groups,
)
from nanopnp.io.switches import SWITCHES
from nanopnp.materials.electrolyte import CorrectionChoice, CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import DEFAULT_BOUNDARIES
from nanopnp.numerics.newton import DEFAULT_SETTINGS, NewtonSettings
from nanopnp.physics.models import build_case_model, declaration
from nanopnp.pipeline.checks import (
    check_document,
    check_exclusion_offset,
    check_operating_point,
    check_species,
    element_orders,
    require_runnable,
)

_POINT_GROUP = re.compile(r"C([1-9][0-9]*)")


def load_case(path: str | Path) -> CaseDocument:
    """Read and validate a case file against the schema and the installed registries."""
    source = str(Path(path))
    return check_document(read_case(path), source=source)


def loads_case(
    text: str, *, source: str = "<string>", base: str | Path | None = None
) -> CaseDocument:
    """Validate a case document held in memory; see :func:`load_case`.

    Parameters
    ----------
    base
        The directory the model files it names are read beside; the working directory when ``None``.
    """
    return check_document(read_case_text(text, base=base, source=source), source=source)


def _choice(spec: schema.CorrectionChoice, files: Mapping[str, Path], key: str) -> CorrectionChoice:
    model = str(files[key]) if key in files else spec.model
    return CorrectionChoice(model=model, concentration=spec.concentration, wall=spec.wall)


def _switches(block: schema.Electrolyte, files: Mapping[str, Path]) -> CorrectionSwitches:
    corrections = block.corrections

    def choice(name: str) -> CorrectionChoice:
        return _choice(getattr(corrections, name), files, f"electrolyte.corrections.{name}.model")

    return CorrectionSwitches(
        diffusivity=choice("diffusivity"),
        mobility=choice("mobility"),
        viscosity=choice("viscosity"),
        permittivity=choice("permittivity"),
        density=choice("density"),
        steric=corrections.steric.model,
    )


def block_electrolyte(
    block: schema.Electrolyte, base: Path, files: Mapping[str, Path] | None = None
) -> Electrolyte:
    """Return the electrolyte one ``electrolyte:`` block resolves to, as a case resolves it.

    Parameters
    ----------
    base
        The directory a correction named by a path is found against.
    files
        Those paths already found, as a case's resolution finds them first.

    Raises
    ------
    CaseValidationError
        If the block names a correction file that is not there.
    """
    found = _correction_files(block, base) if files is None else files
    return Electrolyte.from_parameter_file(
        str(found.get("electrolyte.parameters", block.parameters)),
        switches=_switches(block, found),
        species=[species.name for species in block.species],
        driver=block.driver,
    )


def _absolute(path: Path, base: Path) -> Path:
    return (base / path).resolve()


def _rebased(supplied: SuppliedArtefact | None, base: Path) -> SuppliedArtefact | None:
    if supplied is None or supplied.path is None:
        return supplied
    return supplied.model_copy(update={"path": _absolute(supplied.path, base)})


def _correction_files(electrolyte: schema.Electrolyte, base: Path) -> dict[str, Path]:
    # Every correction named by a path, found against the case's directory; resolution refuses
    # a file that is not there, naming the key.
    named = {"electrolyte.parameters": electrolyte.parameters}
    for name in CORRECTION_PROPERTIES:
        named[f"electrolyte.corrections.{name}.model"] = getattr(
            electrolyte.corrections, name
        ).model
    found: dict[str, Path] = {}
    for key, value in named.items():
        if not names_a_path(value):
            continue
        try:
            found[key] = correction_source(value, base=base)
        except FileNotFoundError as error:
            raise CaseValidationError(f"{key}: {error}") from None
    return found


def _resolve_structure(document: CaseDocument, base: Path) -> ResolvedStructure | None:
    spec = document.structure
    if spec is None:
        return None
    group = spec.symmetry.point_group.strip()
    match = _POINT_GROUP.fullmatch(group)
    if match is None:
        raise CaseValidationError(
            f"structure.symmetry.point_group {group!r} is not a cyclic point group. Use the form "
            "C<n> with n >= 1. For example, use C12 for ClyA, C7 for alpha-hemolysin or C8 for "
            "MspA (section 5.3.1 NOTE on structure:)."
        )
    n = int(match.group(1))
    # The ring's rules hold where the ring gives the axis; the channel's axis takes any chains.
    ring = n >= 2 and spec.symmetry.axis != "cavity"
    groups = parse_chain_groups(spec.source.chains)
    chains: tuple[str, ...] | None = None
    if groups is not None:
        chains = tuple(chain for group in groups for chain in group)
        grouped = any(len(group) > 1 for group in groups)
        if any(not chain for chain in chains):
            raise CaseValidationError(
                f"structure.source.chains {spec.source.chains!r} has an empty entry. Set it to "
                "`all`, or to a comma-separated list of chain identifiers. To make a group of "
                "chains, join the identifiers with `+`, such as A+B,C+D."
            )
        repeated = sorted({chain for chain in chains if chains.count(chain) > 1})
        if repeated:
            raise CaseValidationError(
                f"structure.source.chains lists {', '.join(repeated)} more than once. "
                "List each chain one time."
            )
        if grouped and n == 1:
            raise CaseValidationError(
                f"structure.source.chains {spec.source.chains!r} groups chains with `+`. "
                "structure.symmetry.point_group C1 has no ring of repeating units to group them "
                "into. List the chains with commas."
            )
        if ring and len({len(group) for group in groups}) > 1:
            odd = next(group for group in groups if len(group) != len(groups[0]))
            raise CaseValidationError(
                f"structure.source.chains {spec.source.chains!r} has groups of unequal size. "
                f"{'+'.join(groups[0])} holds {len(groups[0])} chains. "
                f"{'+'.join(odd)} holds {len(odd)}. "
                "Each group must be one repeating unit of the ring (FR-03)."
            )
        if ring and grouped and len(groups) != n:
            raise CaseValidationError(
                f"structure.source.chains lists {len(groups)} groups "
                f"({', '.join('+'.join(group) for group in groups)}). "
                f"structure.symmetry.point_group {group} has {n} units (FR-03). "
                "Make the two counts equal."
            )
        if ring and not grouped and len(chains) != n:
            raise CaseValidationError(
                f"structure.source.chains lists {len(chains)} chains ({', '.join(chains)}). "
                f"structure.symmetry.point_group {group} has {n} units (FR-03). "
                "Make the two counts equal."
            )
    frames = spec.ensemble.frames
    if frames.last_ns is not None and not frames.last_ns > 0.0:
        raise CaseValidationError(
            f"structure.ensemble.frames.last_ns is {frames.last_ns}. It must be a positive time "
            "in ns."
        )
    if frames.count is not None and frames.count < 1:
        raise CaseValidationError(
            f"structure.ensemble.frames.count is {frames.count}. It must be at least 1."
        )
    trajectory = spec.ensemble.trajectory
    spec = spec.model_copy(
        update={
            "source": spec.source.model_copy(update={"path": _absolute(spec.source.path, base)}),
            "ensemble": spec.ensemble.model_copy(
                update={"trajectory": None if trajectory is None else _absolute(trajectory, base)}
            ),
        }
    )
    return ResolvedStructure(spec=spec, n=n, chains=chains, groups=groups)


def _resolve_density(document: CaseDocument) -> Density | None:
    # Beside a supplied profile the structure feeds the charge alone: stages 2 to 4 do not run.
    if document.structure is None or document.inputs.profile is not None:
        return None
    spec = document.geometry.density if document.geometry is not None else Density()
    low, high = GRID_SPACING_RANGE_NM
    if not low <= spec.grid_spacing_nm <= high:
        raise CaseValidationError(
            f"geometry.density.grid_spacing_nm is {spec.grid_spacing_nm} nm. FR-04 requires "
            f"{low}-{high} nm (0.25-0.5 A). The contour of the trans constriction moves with "
            "the resolution (section 5.3.1 NOTE on geometry.density). Set a value in this range."
        )
    if not 0.0 < spec.sharpness < math.inf:
        raise CaseValidationError(
            f"geometry.density.sharpness is {spec.sharpness}. It scales the radius of each atom "
            "to its Gaussian width. It must be a positive number (section 5.3.1 NOTE on "
            "geometry.density)."
        )
    forcefield = document.charge.forcefield if document.charge is not None else "CHARMM"
    if spec.atoms == "protonated" and document.inputs.pqr is None and forcefield != "CHARMM":
        raise CaseValidationError(
            f"geometry.density.atoms is 'protonated' beside charge.forcefield {forcefield!r}. "
            "Stage 2 takes the radius of each protonated atom from the CHARMM set. That set does "
            "not hold the hydrogen names of this force field. Use charge.forcefield: CHARMM, or "
            "set geometry.density.atoms: as_loaded (section 5.3.1 NOTE on geometry.density)."
        )
    return spec


def _resolve_contour(document: CaseDocument, density: Density | None) -> Contour | None:
    if document.structure is None or density is None:
        return None
    spec = document.geometry.contour if document.geometry is not None else Contour()
    if not (math.isfinite(spec.isolevel) and 0.0 < spec.isolevel < 1.0):
        raise CaseValidationError(
            f"geometry.contour.isolevel is {spec.isolevel}. It is a level of a density in "
            "[0, 1]. It must lie in (0, 1) (section 5.3.1 NOTE on geometry.contour)."
        )
    h = density.grid_spacing_nm
    if not (math.isfinite(spec.simplify_tol_nm) and 0.0 < spec.simplify_tol_nm < h):
        raise CaseValidationError(
            f"geometry.contour.simplify_tol_nm is {spec.simplify_tol_nm} nm. It must be positive "
            f"and below the density grid spacing h = {h} nm. A larger tolerance discards "
            "resolved geometry. It also breaks the feature-size margin of the closing of "
            "radius 2h (section 5.3.1 NOTE on geometry.contour, section 5.2.1)."
        )
    return spec


def _resolve_protonation(document: CaseDocument) -> ResolvedProtonation:
    charge = document.charge if document.charge is not None else Charge()
    edits = []
    for edit in charge.edits:
        parent, resid, icode = edit.residue_parts
        edits.append(ResolvedEdit(parent, resid, icode, edit.kind, edit.value))
    edits.sort(key=lambda edit: (edit.resid, edit.icode, edit.kind))
    return ResolvedProtonation(
        ph=charge.ph,
        forcefield=charge.forcefield,
        titration=charge.titration,
        edits=tuple(edits),
    )


def _model_options(
    document: CaseDocument, *, order: int, velocity_order: int, pressure_order: int
) -> dict[str, Any]:
    physics = document.physics
    candidates: dict[str, Any] = {
        "solid_permittivities": dict(physics.solid_permittivities),
        **{record.name: value_at(document, record.path) for record in SWITCHES},
        "order": order,
        "velocity_order": velocity_order,
        "pressure_order": pressure_order,
        "stabilisation": document.numerics.stabilisation,
    }
    if not candidates["log_variables"]:
        # Off, the key is left out, so a case that never sets it keeps its solve key.
        del candidates["log_variables"]
    declared = declaration(physics.model).options
    return {key: value for key, value in candidates.items() if key in declared}


def resolve(document: CaseDocument, *, base: Path | None = None) -> ResolvedCase:
    """Turn a validated case document into the objects the solver takes.

    Parameters
    ----------
    base
        The directory every relative path the case names is taken against: the case file's, or
        the working directory when ``None``. The resolved case holds each absolute.

    Raises
    ------
    CaseValidationError
        If the case names a correction file that is not there.
    """
    check_document(document)
    where = (base if base is not None else Path.cwd()).resolve()
    files = _correction_files(document.electrolyte, where)
    mesh = _rebased(require_runnable(document), where)
    structure = _resolve_structure(document, where)
    density = _resolve_density(document)
    contour = _resolve_contour(document, density)
    geometry = document.geometry if document.geometry is not None else Geometry()

    electrolyte = block_electrolyte(document.electrolyte, where, files)
    check_species(document, electrolyte)
    check_operating_point(document)

    order, velocity_order, pressure_order = element_orders(document)
    physics = document.physics
    nonlinear = document.numerics.nonlinear
    options = _model_options(
        document, order=order, velocity_order=velocity_order, pressure_order=pressure_order
    )
    # Built here so a builder's own refusal (``pb`` beside an asymmetric salt) is a case
    # error reported now, not when stage 10 builds the model again.
    try:
        model = build_case_model(
            physics.model, electrolyte, document.electrolyte.concentration_M, options
        )
    except (TypeError, ValueError) as error:
        raise CaseValidationError(
            f"physics.model {physics.model!r} cannot be built for this case: {error}"
        ) from error
    spacing = _outline_spacing(document, where)
    resolved = ResolvedCase(
        document=document,
        electrolyte=electrolyte,
        concentration_M=document.electrolyte.concentration_M,
        temperature_K=document.electrolyte.temperature_K,
        bias_V=document.boundary_conditions.bias_V,
        ground=document.boundary_conditions.ground,
        model=physics.model,
        model_options=options,
        newton=NewtonSettings(
            initial_damping=DEFAULT_SETTINGS.initial_damping,
            minimum_damping=DEFAULT_SETTINGS.minimum_damping,
            recovery_damping=DEFAULT_SETTINGS.recovery_damping,
            growth_factor=DEFAULT_SETTINGS.growth_factor,
            max_iterations=nonlinear.max_iter,
            relative_tolerance=nonlinear.rtol,
            absolute_tolerance=DEFAULT_SETTINGS.absolute_tolerance,
            reference_norm=DEFAULT_SETTINGS.reference_norm,
        ),
        linear_solver=document.numerics.linear.solver,
        stabilisation=document.numerics.stabilisation,
        continuation=document.numerics.continuation,
        wall_distance_sources=document.numerics.wall_distance.sources,
        wall_distance_max_nm=document.numerics.wall_distance.max_distance_nm,
        mesh=mesh,
        charge=_rebased(document.inputs.charge, where),
        eps_r=_rebased(document.inputs.eps_r, where),
        outputs=tuple(document.outputs),
        declaration=declaration(physics.model),
        essential_boundaries=dict(model.essential_boundaries(DEFAULT_BOUNDARIES)),
        structure=structure,
        density=density,
        contour=contour,
        profile=_rebased(document.inputs.profile, where),
        membrane=geometry.membrane if mesh is None else None,
        reservoir=geometry.reservoir if mesh is None else None,
        pqr=_rebased(document.inputs.pqr, where),
        protonation=_resolve_protonation(document),
        smearing=(document.charge if document.charge is not None else Charge()).smearing,
        exclusion_offset_nm=(document.charge or Charge()).exclusion_offset_nm,
        dielectric_transition_nm=(document.charge or Charge()).dielectric_transition_nm,
        pore=geometry.pore if mesh is None else None,
        wall_charge_C_m2=document.boundary_conditions.wall_charge_C_m2,
        correction_files=files,
        outline_spacing_nm=spacing,
        outline_h_c_nm=_outline_h_c(spacing),
    )
    _check_structure_beside_profile(resolved)
    check_exclusion_offset(resolved)
    return resolved


def _outline_spacing(document: CaseDocument, base: Path) -> float | None:
    # The point spacing a supplied outline's file records, read only where its shell is on.
    profile = _rebased(document.inputs.profile, base)
    offset = (document.charge or Charge()).exclusion_offset_nm
    if profile is None or profile.path is None or not offset > 0.0:
        return None
    try:
        return load_profile(profile.path).provenance.min_vertex_spacing_nm
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise CaseValidationError(
            f"inputs.profile: {profile.path} is not an outline the ion-exclusion shell can be "
            f"built on: {error}"
        ) from None


def _outline_h_c(recorded: float | None) -> float | None:
    # Held within the density grid's range (§8.2.42 AR6): a few long straight edges shell as the
    # coarsest grid, and one edited edge shortened below the finest does not refine the whole ring.
    if recorded is None:
        return None
    low, high = GRID_SPACING_RANGE_NM
    return min(max(recorded, low), high)


def _check_structure_beside_profile(resolved: ResolvedCase) -> None:
    if resolved.profile is None or resolved.structure is None or resolved.deposits_charge:
        return
    reason = (
        "inputs.charge supplies the charge that stage 7 deposits otherwise"
        if resolved.charge is not None
        else f"physics.model {resolved.model!r} declares no fixed_charge"
    )
    raise CaseValidationError(
        f"case {resolved.name!r} carries a structure: section beside inputs.profile, and "
        f"{reason}. No charge is deposited from the protonation of the structure. Stages 2 "
        "to 4 do not run beside a supplied profile. The structure is recorded as an "
        "input to a run that never read it (section 5.3.1 NOTE on inputs.profile). Remove "
        "structure: or inputs.profile."
    )


class CaseStage:
    """Stage 9 of the walk: the resolved case document, recorded as an artefact."""

    name = "case"

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> CaseArtefact:
        """Resolve the case and emit the stage-9 artefact."""
        check_cancelled(cancel, "case")
        report(progress, 0.0, f"resolving case {inputs.resolved.name!r}")
        artefact = self.key(inputs)
        report(progress, 1.0, f"case {inputs.resolved.name!r} resolved")
        return artefact

    def key(self, inputs: StageInputs) -> CaseArtefact:
        """Return the stage-9 artefact, which is its own key."""
        resolved = inputs.resolved
        return CaseArtefact(resolved.document, summary=resolved.provenance)

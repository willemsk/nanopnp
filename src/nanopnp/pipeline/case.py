"""Loading a case and resolving it to the objects a run is made of."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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
    read_case,
    read_case_text,
)
from nanopnp.io.resolved import (
    ResolvedCase,
    ResolvedProtonation,
    ResolvedStructure,
    parse_chains,
)
from nanopnp.materials.electrolyte import CorrectionChoice, CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import DEFAULT_BOUNDARIES
from nanopnp.numerics.newton import DEFAULT_SETTINGS, NewtonSettings
from nanopnp.physics.models import build_case_model, declaration
from nanopnp.pipeline.checks import (
    check_document,
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


def loads_case(text: str, *, source: str = "<string>") -> CaseDocument:
    """Validate a case document held in memory; see :func:`load_case`."""
    return check_document(read_case_text(text, source=source), source=source)


def _choice(spec: schema.CorrectionChoice, files: Mapping[str, Path], key: str) -> CorrectionChoice:
    model = str(files[key]) if key in files else spec.model
    return CorrectionChoice(model=model, concentration=spec.concentration, wall=spec.wall)


def _switches(document: CaseDocument, files: Mapping[str, Path]) -> CorrectionSwitches:
    corrections = document.electrolyte.corrections

    def choice(name: str) -> CorrectionChoice:
        return _choice(getattr(corrections, name), files, f"electrolyte.corrections.{name}.model")

    return CorrectionSwitches(
        diffusivity=choice("diffusivity"),
        mobility=choice("mobility"),
        viscosity=choice("viscosity"),
        permittivity=choice("permittivity"),
        density=choice("density"),
        steric=corrections.steric.model != "none",
    )


def _absolute(path: Path, base: Path) -> Path:
    return (base / path).resolve()


def _rebased(supplied: SuppliedArtefact | None, base: Path) -> SuppliedArtefact | None:
    if supplied is None or supplied.path is None:
        return supplied
    return supplied.model_copy(update={"path": _absolute(supplied.path, base)})


def _correction_files(document: CaseDocument, base: Path) -> dict[str, Path]:
    # Every correction named by a path, found against the case's directory; resolution refuses
    # a file that is not there, naming the key.
    electrolyte = document.electrolyte
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
            f"structure.symmetry.point_group {group!r} is not a cyclic point group; the accepted "
            "form is C<n> with n >= 1, such as C12 for ClyA, C7 for alpha-hemolysin or C8 for "
            "MspA (section 5.3.1 NOTE on structure:)"
        )
    n = int(match.group(1))
    if n == 1 and spec.symmetry.axis == "auto":
        raise CaseValidationError(
            "structure.symmetry.axis is auto and the point group is C1, which has no chain "
            "permutation to superpose (FR-02); set structure.symmetry.axis: z, which takes the "
            "file's z axis through its origin, unchecked"
        )
    chains = parse_chains(spec.source.chains)
    if chains is not None:
        if any(not chain for chain in chains):
            raise CaseValidationError(
                f"structure.source.chains {spec.source.chains!r} has an empty entry; it is `all` "
                "or a comma-separated list of chain identifiers"
            )
        repeated = sorted({chain for chain in chains if chains.count(chain) > 1})
        if repeated:
            raise CaseValidationError(
                f"structure.source.chains lists {', '.join(repeated)} more than once"
            )
        if len(chains) != n:
            raise CaseValidationError(
                f"structure.source.chains lists {len(chains)} chains ({', '.join(chains)}), and "
                f"structure.symmetry.point_group {group} has {n} (FR-03)"
            )
    frames = spec.ensemble.frames
    if frames.last_ns is not None and not frames.last_ns > 0.0:
        raise CaseValidationError(
            f"structure.ensemble.frames.last_ns is {frames.last_ns}; it is a positive time in ns"
        )
    if frames.count is not None and frames.count < 1:
        raise CaseValidationError(
            f"structure.ensemble.frames.count is {frames.count}; it is at least 1"
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
    return ResolvedStructure(spec=spec, n=n, chains=chains)


def _resolve_density(document: CaseDocument) -> Density | None:
    if document.structure is None:
        return None
    spec = document.geometry.density if document.geometry is not None else Density()
    low, high = GRID_SPACING_RANGE_NM
    if not low <= spec.grid_spacing_nm <= high:
        raise CaseValidationError(
            f"geometry.density.grid_spacing_nm is {spec.grid_spacing_nm} nm; FR-04 requires "
            f"{low}-{high} nm (0.25-0.5 A), because the trans constriction's contour moves with "
            "resolution (section 5.3.1 NOTE on geometry.density)"
        )
    if not 0.0 < spec.sharpness < math.inf:
        raise CaseValidationError(
            f"geometry.density.sharpness is {spec.sharpness}; it scales each atom's radius to "
            "its Gaussian width, so it is a positive number (section 5.3.1 NOTE on "
            "geometry.density)"
        )
    return spec


def _resolve_contour(document: CaseDocument, density: Density | None) -> Contour | None:
    if document.structure is None or density is None:
        return None
    spec = document.geometry.contour if document.geometry is not None else Contour()
    if not (math.isfinite(spec.isolevel) and 0.0 < spec.isolevel < 1.0):
        raise CaseValidationError(
            f"geometry.contour.isolevel is {spec.isolevel}; it is a level of a density in "
            "[0, 1], so it lies in (0, 1) (section 5.3.1 NOTE on geometry.contour)"
        )
    h = density.grid_spacing_nm
    if not (math.isfinite(spec.simplify_tol_nm) and 0.0 < spec.simplify_tol_nm < h):
        raise CaseValidationError(
            f"geometry.contour.simplify_tol_nm is {spec.simplify_tol_nm} nm; it must be positive "
            f"and below the density grid spacing h = {h} nm, because a larger tolerance "
            "discards resolved geometry and breaks the feature-size margin of the closing of "
            "radius 2h (section 5.3.1 NOTE on geometry.contour, section 5.2.1)"
        )
    return spec


def _resolve_protonation(document: CaseDocument) -> ResolvedProtonation:
    charge = document.charge if document.charge is not None else Charge()
    return ResolvedProtonation(
        ph=charge.ph, forcefield=charge.forcefield, titration=charge.titration
    )


def _model_options(
    document: CaseDocument, *, order: int, velocity_order: int, pressure_order: int
) -> dict[str, Any]:
    physics = document.physics
    candidates: dict[str, Any] = {
        "solid_permittivities": dict(physics.solid_permittivities),
        "variable_density": physics.variable_density,
        "inertia": physics.inertia,
        "dielectric_gradient_forces": physics.dielectric_gradient_forces,
        "order": order,
        "velocity_order": velocity_order,
        "pressure_order": pressure_order,
        "stabilisation": document.numerics.stabilisation,
        "flow": physics.flow,
    }
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
    files = _correction_files(document, where)
    mesh = _rebased(require_runnable(document), where)
    structure = _resolve_structure(document, where)
    density = _resolve_density(document)
    contour = _resolve_contour(document, density)
    geometry = document.geometry if document.geometry is not None else Geometry()

    electrolyte = Electrolyte.from_parameter_file(
        str(files.get("electrolyte.parameters", document.electrolyte.parameters)),
        switches=_switches(document, files),
        species=[species.name for species in document.electrolyte.species],
        driver=document.electrolyte.driver,
    )
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
    )
    return resolved


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

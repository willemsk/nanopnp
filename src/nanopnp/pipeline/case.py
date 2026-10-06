"""Loading a case, and resolving it to the objects a run is made of.

:func:`load_case` is :func:`nanopnp.io.case.read_case` followed by
:func:`nanopnp.pipeline.checks.check_document`, so a document read here has been
checked against the installed registries as well as against the schema.
:func:`resolve` turns a document into a :class:`~nanopnp.io.resolved.ResolvedCase`:
it builds the electrolyte, the Newton settings and the model, which is why it sits
above ``materials``, ``numerics`` and ``physics`` rather than in the base beside the
types it returns (WP38 D3).
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import CaseArtefact, StageInputs
from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
    Charge,
    ContourSpec,
    CorrectionChoiceSpec,
    DensitySpec,
    Geometry,
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

GRID_SPACING_RANGE_NM: tuple[float, float] = (0.025, 0.05)
"""FR-04's density grid spacing, 0.25-0.5 Å (section 5.3.1 NOTE on ``geometry.density``)."""


_POINT_GROUP = re.compile(r"C([1-9][0-9]*)")
"""``symmetry.point_group``: a cyclic group ``C<n>``, n >= 1 (section 5.3.1 NOTE)."""


def load_case(path: str | Path) -> CaseDocument:
    """Read and validate a case file, against the schema and the installed registries.

    :func:`~nanopnp.io.case.read_case` followed by
    :func:`~nanopnp.pipeline.checks.check_document`. The ``schema:`` string is
    checked first, so a file written to a future schema fails naming the schema
    it claims rather than with a wall of field errors against a shape it never
    declared. A ``nanopnp/case/v1`` file is read as its v2 upgrade
    (:func:`~nanopnp.io.case.upgrade_v1`).

    Parameters
    ----------
    path
        The YAML case file.

    Returns
    -------
    CaseDocument
        The validated document.

    Raises
    ------
    CaseValidationError
        If the file is not a mapping, declares neither accepted schema, cannot
        be upgraded, fails validation, names a model, a stabilisation mode or a
        linear solver this install does not register, or asks for an element
        pair no solve can use; the message names every offending key by dotted
        path.
    """
    return check_document(read_case(path), source=str(Path(path)))


def loads_case(text: str, *, source: str = "<string>") -> CaseDocument:
    """Validate a case document held in memory; see :func:`load_case`."""
    return check_document(read_case_text(text, source=source), source=source)


def _choice(spec: CorrectionChoiceSpec) -> CorrectionChoice:
    """Return the materials-layer choice one ``corrections`` entry names (WP38 D6)."""
    return CorrectionChoice(model=spec.model, concentration=spec.concentration, wall=spec.wall)


def _switches(document: CaseDocument) -> CorrectionSwitches:
    """Return the PHY-22 switch set the document's ``corrections`` block names."""
    corrections = document.electrolyte.corrections
    return CorrectionSwitches(
        diffusivity=_choice(corrections.diffusivity),
        mobility=_choice(corrections.mobility),
        viscosity=_choice(corrections.viscosity),
        permittivity=_choice(corrections.permittivity),
        density=_choice(corrections.density),
        steric=corrections.steric.model != "none",
    )


def _resolve_structure(document: CaseDocument) -> ResolvedStructure | None:
    """Make the ``structure:`` refusals that need no file (section 5.3.1 NOTE, WP18 D4).

    Each is a refusal here rather than a narrowing of the schema: a narrowed value
    set would move the schema (the section 5.3.1 compatibility rule), and a
    document valid against ``nanopnp/case/v2`` stays valid.

    Raises
    ------
    CaseValidationError
        Naming the key: a point group that is not ``C<n>``, ``axis: auto`` on
        ``C1``, a chain list that is empty, repeats an identifier or does not
        number ``n``, and a non-positive ``last_ns`` or ``count``.
    """
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
    return ResolvedStructure(spec=spec, n=n, chains=chains)


def _resolve_density(document: CaseDocument) -> DensitySpec | None:
    """Make the ``geometry.density`` refusals (section 5.3.1 NOTE, WP19 D2).

    Value checks, not a narrowing of the schema, for the reason
    :func:`_resolve_structure` gives.

    Returns
    -------
    DensitySpec or None
        The block, or its defaults where the case has no ``geometry:``; ``None``
        on a case without ``structure:``, which runs no stage that reads it.

    Raises
    ------
    CaseValidationError
        Naming the key and its value: a grid spacing outside FR-04's
        0.025-0.05 nm, or a sharpness that is not positive.
    """
    if document.structure is None:
        return None
    spec = document.geometry.density if document.geometry is not None else DensitySpec()
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


def _resolve_contour(document: CaseDocument, density: DensitySpec | None) -> ContourSpec | None:
    """Make the ``geometry.contour`` refusals (section 5.3.1 NOTE, WP20 D3).

    Value checks, not a narrowing of the schema, for the reason
    :func:`_resolve_structure` gives.

    Returns
    -------
    ContourSpec or None
        The block, or its defaults where the case has no ``geometry:``; ``None``
        on a case without ``structure:``.

    Raises
    ------
    CaseValidationError
        Naming the key and its value: an isolevel that is not finite or not in
        (0, 1), or a tolerance that is not finite or not in (0, h), which also
        names h.
    """
    if document.structure is None or density is None:
        return None
    spec = document.geometry.contour if document.geometry is not None else ContourSpec()
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
    """Return the ``protonation`` stage's settings, at their defaults without ``charge:``."""
    charge = document.charge if document.charge is not None else Charge()
    return ResolvedProtonation(
        ph=charge.ph, forcefield=charge.forcefield, titration=charge.titration
    )


def _model_options(
    document: CaseDocument, *, order: int, velocity_order: int, pressure_order: int
) -> dict[str, Any]:
    """Return the keyword arguments the named model's builder takes (PHY-21, WP26 D5).

    The case offers one candidate set and the model's declaration selects from it
    (section 5.4.3 NOTE): ``pnp`` fixes ``flow=False`` in its builder and does not
    declare it, and ``pb`` declares ``order`` alone. The candidate order is the one
    the keys have always been written in, so every model's resolved options, and
    with them its stage-10 key, are what they were before the declaration existed.
    :func:`~nanopnp.pipeline.checks.check_document`'s switch check has already
    refused any case where the omission would hide a switch the user set.
    """
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


def resolve(document: CaseDocument) -> ResolvedCase:
    """Turn a validated case document into the objects the solver takes.

    Parameters
    ----------
    document
        A validated case document.

    Returns
    -------
    ResolvedCase
        The electrolyte, the model options, the Newton settings and the mesh the
        run is made of.

    Raises
    ------
    UnsupportedCaseSection
        If the case asks for a pipeline stage a later release owns; the message
        names the section and the release.
    CaseValidationError
        If the document is internally inconsistent — a species the parameter file
        does not carry, a steric diameter or a temperature disagreeing with it, an element label
        that is not one.
    """
    check_document(document)
    mesh = require_runnable(document)
    structure = _resolve_structure(document)
    density = _resolve_density(document)
    contour = _resolve_contour(document, density)
    geometry = document.geometry if document.geometry is not None else Geometry()

    electrolyte = Electrolyte.from_parameter_file(
        document.electrolyte.parameters,
        switches=_switches(document),
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
    # Built once, through the one builder every consumer uses: a builder's own
    # refusal -- ``pb`` beside a salt that is not symmetric monovalent -- is a
    # case error, and is reported now rather than when stage 10 builds the model
    # again (WP26 D10). What a stage below ``physics`` reads of it is kept as
    # data on the resolved case (WP38 D5).
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
        charge=document.inputs.charge,
        eps_r=document.inputs.eps_r,
        outputs=tuple(document.outputs),
        declaration=declaration(physics.model),
        essential_boundaries=dict(model.essential_boundaries(DEFAULT_BOUNDARIES)),
        structure=structure,
        density=density,
        contour=contour,
        profile=document.inputs.profile,
        membrane=geometry.membrane if mesh is None else None,
        reservoir=geometry.reservoir if mesh is None else None,
        pqr=document.inputs.pqr,
        protonation=_resolve_protonation(document),
        smearing=(document.charge if document.charge is not None else Charge()).smearing,
        exclusion_offset_nm=(document.charge or Charge()).exclusion_offset_nm,
        dielectric_transition_nm=(document.charge or Charge()).dielectric_transition_nm,
    )
    return resolved


class CaseStage:
    """Stage 9 of section 5.2: the resolved case document.

    Resolving is the work, and the walk has done it before any stage runs: every
    stage is handed the one resolved case (WP38 D4). What this stage adds is the
    record of it, the stage-9 artefact, keyed on the document and its provenance.
    """

    name = "case"

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> CaseArtefact:
        """Resolve the case and emit the stage-9 artefact.

        Raises
        ------
        Cancelled
            If ``cancel`` is already set; resolution is too short to interrupt
            usefully, so the token is checked once on entry.
        """
        check_cancelled(cancel, "case")
        report(progress, 0.0, f"resolving case {inputs.resolved.name!r}")
        artefact = self.key(inputs)
        report(progress, 1.0, f"case {inputs.resolved.name!r} resolved")
        return artefact

    def key(self, inputs: StageInputs) -> CaseArtefact:
        """Return the stage-9 artefact, which is its own key (FR-27, section 5.3.2).

        The whole of :meth:`run`'s result, summary included: resolving writes no
        file, so there is nothing cheaper to key than the answer, and the walk
        stores this key as the artefact (``key_is_artefact``). :meth:`run` calls
        this, so the two cannot drift apart.
        """
        resolved = inputs.resolved
        return CaseArtefact(resolved.document, summary=resolved.provenance)

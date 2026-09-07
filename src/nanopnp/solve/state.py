"""Persisting a converged state, and restoring the operator it solves (FR-27, QR-08).

Stage 10's payload used to be ``state.gfu`` — NGSolve's own serialisation of a
``GridFunction``. It round-trips the numbers and nothing else, which is enough
to look at a field and not enough to do anything with one. A restored solution
has to be able to answer the NUM-24 and NUM-25 routes, and NUM-25 is *the
assembled residual evaluated on the constrained degrees of freedom*: without the
form, half of the QR-04 cross-check cannot run at all, and stage 11 served from a
stage-10 cache hit would have nothing to check its indicator route against.

So the payload is a self-describing coefficient record (§5.3.2 NOTE): one
coefficient array per field component, **the wall-distance coefficient vector**,
and a descriptor naming what the arrays mean. The distance field is stored rather
than recomputed because a residual reassembled against a freshly solved distance
field is a different operator — the screened-Poisson solve behind
:func:`nanopnp.mesh.distance.wall_distance` is not bit-reproducible across
library versions, and a flux taken against the resulting operator would be wrong
with no diagnostic at all.

Rebuilding the operator means rebuilding the rung that produced it, which is why
:func:`single_rung` and :func:`ladder` live here rather than in
:mod:`nanopnp.solve.stage`. The save path and the restore path then construct the
top rung through one function, and cannot build two models that differ in a
switch nobody recorded. ``stage.py`` imports this module; this module imports
:mod:`nanopnp.solve.continuation`, so nothing is circular.

Restore is a **gate, never an adaptation**. Every value in the descriptor is
re-derived on load from the case, the mesh and the backend, and compared key by
key; the first difference aborts naming the key and both values (QR-12). A
payload whose mesh moved, whose element order changed or whose model gained a
switch is not something to interpolate onto the new space — it is a different
run, and pretending otherwise is how a plausible wrong number is produced. A
change to this contract is a change of artefact schema version (§5.3.2), which is
why :data:`nanopnp.io.artefact.SOLUTION_SCHEMA` is ``v2``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nanopnp.charge.stage import ResolvedFields, gate_fields, read_fields
from nanopnp.core.constants import thermal_voltage
from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.io.artefact import SOLUTION_SCHEMA
from nanopnp.io.case import COUPLED_MODELS, resolve
from nanopnp.mesh.ingest import ingest
from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
from nanopnp.physics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.models import (
    DEFAULT_BOUNDARIES,
    CoupledBoundaries,
    CoupledModel,
    ModelSolution,
    PhysicsModel,
    create,
)
from nanopnp.solve.continuation import ELECTRODES, Rung, default_ladder

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Expression, FESpace, GridFunction, Mesh
    from nanopnp.io.case import CaseDocument, ResolvedCase
    from nanopnp.materials.electrolyte import Electrolyte

__all__ = [
    "STATE_FILENAME",
    "STATE_KEY",
    "StateMismatchError",
    "ladder",
    "reads_wall",
    "restore",
    "save",
    "single_rung",
    "wall_distance_field",
]

STATE_KEY = "state"
"""Key stage 10's payload map records the state file under.

Named rather than spelt twice: the payload is keyed by *role* and not by
filename, and a diagnostic that told a reader to look for ``state.npz`` among
the keys would send them looking for something that is never there.
"""

STATE_FILENAME = "state.npz"
"""Name of the stage-10 payload file. ``.npz`` because it is one compressed
container of named arrays with no dependency beyond NumPy, and because the
descriptor rides in it rather than in a second file that could be separated from
it."""

DESCRIPTOR_ENTRY = "descriptor"
"""Array holding the JSON descriptor, as a zero-dimensional unicode array."""

WALL_DISTANCE_ENTRY = "wall_distance_nm"
"""Array holding the discrete PHY-02 distance field's coefficients, in nm."""

FIELD_PREFIX = "field."
"""Prefix of the per-component coefficient arrays: ``field.phi``, ``field.c_K``."""

SOLVE_ONLY_KEYWORDS = frozenset(
    {
        "boundaries",
        "callback",
        "concentration_values",
        "initial",
        "initial_concentrations",
        "potential_values",
        "settings",
        "solver",
        "velocity_values",
    }
)
"""Rung keywords that configure the *solve* rather than enter the residual.

Everything a rung carries that is not in this set is a coefficient of the
operator and is passed to ``residual_form``. Classifying by exclusion rather
than by an allow-list is deliberate: a keyword added to ``residual_form`` and
forgotten here reaches it and works, while a new *solve* keyword forgotten here
is rejected loudly by the model's own ``_reject_unknown`` rather than silently
dropped from the form.
"""

DESCRIPTOR_KEYS: tuple[str, ...] = (
    "solve_hash",
    "mesh_content_hash",
    "boundaries",
    "stabilisation",
    "wall_distance",
    "model",
    "fields",
    "ndof",
)
"""What the descriptor records, in the order the gate reports a difference.

The order runs from the cheapest and most likely difference to the most
detailed, so the message a user sees names the case or the mesh when one of
those moved rather than the twentieth field of a model provenance that differs
only because of it.

``solve_hash`` is the digest of
:attr:`~nanopnp.io.case.ResolvedCase.solve_provenance` and deliberately not of
the case document: the document carries ``name`` and ``outputs``, neither of
which reaches the operator, and a gate keyed on them would refuse a converged
state to a run that differs only in what it intends to *report*. It is the same
digest stage 10 keys its artefact on, so a state the store serves is a state the
gate admits — two records of one fact, and they must not be able to disagree.
"""


class StateMismatchError(RuntimeError):
    """A stored state does not describe the run it is being restored into.

    Raised rather than adapted to. Interpolating a payload onto a space it was
    not produced on, or reassembling its residual against a model that differs
    in one switch, yields a converged-looking state that solves a different
    problem (QR-12).
    """


def reads_wall(electrolyte: Electrolyte) -> bool:
    """Return whether any resolved correction of ``electrolyte`` evaluates ``d``.

    Asked of the corrections rather than of the model name, exactly as
    :func:`~nanopnp.solve.continuation.default_ladder` asks it: a run whose wall
    factors are all off must not pay for a screened-Poisson solve, and must not
    record a distance field nothing read.
    """
    return any(
        bool(getattr(correction, "use_wall", False))
        for correction in electrolyte.corrections.values()
    )


def wall_distance_field(resolved: ResolvedCase, mesh: Mesh, *, order: int) -> Expression:
    """Return the PHY-02 distance field this case solves against.

    :data:`~nanopnp.physics.coefficients.SATURATED_WALL_DISTANCE_NM` when no
    correction reads ``d``, so a classical run pays for no screened-Poisson solve
    and records no field it never evaluated.
    """
    if not reads_wall(resolved.electrolyte):
        return SATURATED_WALL_DISTANCE_NM
    from nanopnp.mesh.distance import wall_distance

    return wall_distance(
        mesh,
        resolved.wall_distance_sources,
        order=order,
        max_distance_nm=resolved.wall_distance_max_nm,
    )


def single_rung(
    resolved: ResolvedCase,
    mesh: Mesh,
    measures: Measures,
    distance: Expression,
    fields: ResolvedFields,
) -> Rung:
    """Return the one rung a case with ``continuation: none`` solves.

    Cold, at the target operating point. NUM-18 exists because that does not
    converge over most of the FR-17 envelope; the switch is offered because the
    electrostatic models of PHY-21 are not on the ladder at all, and because an
    ablation needs to be able to ask for the cold solve and watch it fail.

    ``distance`` is the PHY-02 field the case solves against, and is passed on
    for the same reason :func:`~nanopnp.solve.continuation.default_ladder` takes
    it: omitting it leaves every wall correction evaluating at
    :data:`~nanopnp.physics.coefficients.SATURATED_WALL_DISTANCE_NM`, which is a
    converged, plausible, wrong answer -- and one :func:`save` then refuses to
    store, after the solve has been paid for.
    """
    options = dict(resolved.model_options)
    if resolved.model in COUPLED_MODELS:
        model = create(
            resolved.model,
            electrolyte=resolved.electrolyte,
            concentration_M=resolved.concentration_M,
            **options,
        )
    else:
        model = create(resolved.model, **options)
    driven = next(iter(ELECTRODES - {resolved.ground}))
    supplied: dict[str, Expression] = {}
    if isinstance(model, CoupledModel):
        # The electrostatic models of PHY-21 take none of these: ``pb`` screens
        # with a Debye length, carries no material permittivity and evaluates no
        # wall factor, and ``resolve`` refuses a case that supplies a field to
        # one of them -- so this branch is the belt to that brace rather than a
        # silent drop. ``wall_distance_nm`` is unconditional inside it, because
        # a coupled model that read ``d`` and was handed none would saturate
        # every wall factor rather than fail (PHY-02).
        if fields.charge is not None:
            supplied["fixed_charge"] = fields.charge.assemble(model.scales)
        if fields.eps_r is not None:
            supplied["solid_fraction"] = fields.eps_r.chi()
        supplied["wall_distance_nm"] = distance
    # Taken from the temperature rather than from ``model.scales``: the
    # electrostatic models of PHY-21 carry no scale set, and every model of the
    # table nondimensionalises the potential by the same ``V_T = RT/F`` (NUM-09).
    thermal_V = thermal_voltage(resolved.temperature_K)
    return Rung(
        name=f"target-{resolved.model}",
        stage=1,
        model=model,
        mesh=mesh,
        measures=measures,
        solve_kwargs={
            "potential_values": mesh.BoundaryCF(
                {resolved.ground: 0.0, driven: resolved.bias_V / thermal_V}
            ),
            **supplied,
        },
    )


def ladder(
    resolved: ResolvedCase,
    mesh: Mesh,
    measures: Measures,
    distance: Expression,
    fields: ResolvedFields,
) -> tuple[Rung, ...]:
    """Return the rungs this case solves, ladder or single (NUM-18).

    Building the rungs costs no assembly and no solve — every model here is a
    frozen dataclass and every coefficient an unevaluated expression — which is
    what lets :func:`restore` rebuild the whole ladder just to read its top rung
    back off, rather than reconstructing that rung's model and coefficients by
    hand and risking a different operator.
    """
    if resolved.continuation == "none":
        return (single_rung(resolved, mesh, measures, distance, fields),)
    # The producer pipeline is still v0.9, so the charge a run carries is the
    # one it was handed through ``inputs.charge`` (FR-27, stage 7). With no
    # field supplied the stage-4 ramp is empty rather than silently zero, and
    # the ladder is the same one WP5 measured.
    return default_ladder(
        mesh,
        concentration_M=resolved.concentration_M,
        bias_V=resolved.bias_V,
        ground=resolved.ground,
        electrolyte=resolved.electrolyte,
        wall_distance_nm=distance,
        measures=measures,
        corrections_active=resolved.model == "epnp-ns",
        switches=resolved.electrolyte.switches,
        # The ladder builds its own models, so the case's ``physics.
        # solid_permittivities`` reaches them only here. Omitting it leaves
        # the membrane at the electrolyte's eps_r -- 24 times too large, and
        # a plausible wrong current with no diagnostic (PHY-03, PHY-20).
        solid_permittivities=dict(resolved.document.physics.solid_permittivities),
        fixed_charge_field=(None if fields.charge is None else fields.charge.volume_density_C_m3()),
        solid_fraction=None if fields.eps_r is None else fields.eps_r.chi(),
    )


def residual_keywords(rung: Rung) -> dict[str, Expression]:
    """Return the rung keywords that are coefficients of its residual form.

    See :data:`SOLVE_ONLY_KEYWORDS` for why the classification is by exclusion.
    """
    return {
        name: value for name, value in rung.solve_kwargs.items() if name not in SOLVE_ONLY_KEYWORDS
    }


def _component_vectors(state: GridFunction, count: int) -> list[Any]:
    """Return the coefficient vector of each field, in declaration order.

    A one-field model's ``GridFunction`` has no ``components``, so the single
    case is not the loop with ``count == 1``.
    """
    if count == 1:
        return [state.vec]
    return [component.vec for component in state.components]


def _component_spaces(space: FESpace, count: int) -> list[FESpace]:
    """Return each field's own space, in declaration order."""
    if count == 1:
        return [space]
    return [component for component in space.components]


def _field_record(model: PhysicsModel, space: FESpace) -> list[dict[str, Any]]:
    """Return the NUM-01 discretisation record: what each field is, and how big.

    The degree-of-freedom count is read from the *space the backend built*, not
    from the model's declaration, so a backend that changed how it counts a
    ``VectorH1`` block or a ``NumberSpace`` is a mismatch rather than a silent
    reinterpretation of the stored array.
    """
    spaces = _component_spaces(space, len(model.fields))
    return [
        {
            "name": declared.name,
            "element": declared.element,
            "order": declared.order,
            "domain": declared.domain,
            "ndof": int(component.ndof),
        }
        for declared, component in zip(model.fields, spaces, strict=True)
    ]


def _canonical(value: Canonicalisable) -> Canonicalisable:
    """Return ``value`` as JSON round-trips it, so tuples and lists compare equal.

    The descriptor is compared against a freshly built Python object, and
    ``("cis", "trans")`` written to JSON comes back as a list. Canonicalising
    both sides is what keeps the gate about the physics rather than about
    container types.
    """
    return json.loads(json.dumps(value, sort_keys=True))


def _descriptor(
    *,
    resolved: ResolvedCase,
    model: PhysicsModel,
    space: FESpace,
    boundaries: CoupledBoundaries,
    mesh_content_hash: str,
    wall_distance_ndof: int | None,
) -> dict[str, Any]:
    """Return the record §5.3.2's NOTE requires the payload to carry.

    Everything here is re-derived on restore from the case, the mesh and the
    backend and compared; nothing is read out of the file and used.
    """
    record: dict[str, Any] = _canonical(
        {
            "solve_hash": content_hash(SOLUTION_SCHEMA, resolved.solve_provenance),
            "mesh_content_hash": mesh_content_hash,
            "boundaries": {
                "potential": boundaries.potential,
                "concentration": boundaries.concentration,
                "velocity": boundaries.velocity,
                "velocity_axis": boundaries.velocity_axis,
            },
            "stabilisation": resolved.stabilisation,
            "wall_distance": {
                "sources": resolved.wall_distance_sources,
                "max_distance_nm": resolved.wall_distance_max_nm,
                "ndof": wall_distance_ndof,
            },
            "model": dict(model.provenance),
            "fields": _field_record(model, space),
            "ndof": int(space.ndof),
        }
    )
    return record


def _gate(stored: Mapping[str, Any], expected: Mapping[str, Any], path: Path) -> None:
    """Compare the two descriptors key by key, aborting on the first difference.

    Raises
    ------
    StateMismatchError
        Naming the key and both values (QR-12). The keys themselves are checked
        too: a payload written by a version that recorded one fewer of them is
        not a payload this one can gate, and silently skipping the missing key
        would make the gate weaker the older the file is.
    """
    if sorted(stored) != sorted(DESCRIPTOR_KEYS):
        missing = sorted(set(DESCRIPTOR_KEYS) - set(stored))
        extra = sorted(set(stored) - set(DESCRIPTOR_KEYS))
        raise StateMismatchError(
            f"{path} carries a descriptor this version cannot gate: "
            f"missing {missing or 'nothing'}, unexpected {extra or 'nothing'}. "
            "A changed payload contract is a changed artefact schema version (section 5.3.2)"
        )
    for key in DESCRIPTOR_KEYS:
        if stored[key] != expected[key]:
            raise StateMismatchError(
                f"{path} was produced with a different {key}, so its coefficients do not "
                f"describe this run and will not be adapted to it:\n"
                f"  stored:   {json.dumps(stored[key], sort_keys=True)}\n"
                f"  this run: {json.dumps(expected[key], sort_keys=True)}"
            )


def save(
    solution: ModelSolution,
    path: Path,
    *,
    resolved: ResolvedCase,
    mesh_content_hash: str,
    boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
) -> Path:
    """Write a converged state and its descriptor to ``path``.

    Parameters
    ----------
    solution
        The converged state, as the top rung of the ladder produced it.
    path
        The ``.npz`` file to write. Its parent is created.
    resolved
        The case this state solves, which supplies the descriptor's case hash,
        stabilisation mode and wall-distance settings.
    mesh_content_hash
        The stage-6 mesh's content hash — its canonical vertices, connectivity
        and tags. The mesh's *path* is deliberately not recorded: a mesh that
        merely moved is the same mesh, and one whose contents changed is not.
    boundaries
        The boundary vocabulary the space was built on.

    Returns
    -------
    Path
        ``path``, written.

    Raises
    ------
    StateMismatchError
        If the case's corrections read ``d`` but the solution carries no
        discrete distance field. A constant would restore an operator whose wall
        factors are saturated everywhere — a converged, plausible, wrong answer.
    """
    import numpy as np

    model = solution.model
    space = solution.space
    distance = solution.wall_distance_nm
    arrays: dict[str, Any] = {}

    stored_distance = reads_wall(resolved.electrolyte)
    wall_ndof: int | None = None
    if stored_distance:
        vector = getattr(distance, "vec", None)
        if vector is None:
            raise StateMismatchError(
                f"{resolved.name!r} activates a wall correction that evaluates d, but the "
                "solution carries no discrete distance field to store; restoring it would "
                "reassemble the residual against a saturated constant and give a different "
                "operator (section 5.3.2 NOTE)"
            )
        coefficients = np.asarray(vector.FV().NumPy(), dtype=np.float64)
        arrays[WALL_DISTANCE_ENTRY] = coefficients
        wall_ndof = int(coefficients.size)

    for declared, vector in zip(
        model.fields, _component_vectors(solution.state, len(model.fields)), strict=True
    ):
        arrays[f"{FIELD_PREFIX}{declared.name}"] = np.asarray(vector.FV().NumPy(), dtype=np.float64)

    descriptor = _descriptor(
        resolved=resolved,
        model=model,
        space=space,
        boundaries=boundaries,
        mesh_content_hash=mesh_content_hash,
        wall_distance_ndof=wall_ndof,
    )
    arrays[DESCRIPTOR_ENTRY] = np.array(json.dumps(descriptor, sort_keys=True))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    return path


def _load_descriptor(path: Path, data: Mapping[str, Any]) -> dict[str, Any]:
    """Return the descriptor stored in ``data``, as a mapping.

    Raises
    ------
    StateMismatchError
        If the entry is absent or is not a JSON object. A payload without a
        descriptor cannot be gated, and a payload that cannot be gated is not
        one this module will restore.
    """
    if DESCRIPTOR_ENTRY not in data:
        raise StateMismatchError(
            f"{path} carries no {DESCRIPTOR_ENTRY!r} entry, so there is nothing to check it "
            "against; it is not a nanopnp/solution/v2 payload"
        )
    try:
        stored = json.loads(str(data[DESCRIPTOR_ENTRY]))
    except json.JSONDecodeError as error:
        raise StateMismatchError(f"{path} carries an unreadable descriptor: {error}") from error
    if not isinstance(stored, dict):
        raise StateMismatchError(
            f"{path} carries a descriptor that is a {type(stored).__name__}, not an object"
        )
    return dict(stored)


def _restore_distance(
    path: Path,
    data: Mapping[str, Any],
    resolved: ResolvedCase,
    mesh: Mesh,
    *,
    order: int,
) -> tuple[Expression, int | None]:
    """Return the stored PHY-02 distance field, rebuilt on its own space.

    Stored rather than re-solved: :func:`nanopnp.mesh.distance.wall_distance`
    runs a screened-Poisson solve whose result is not reproducible to the last
    bit across library versions, and the residual assembled against a field that
    differs in the last bits is a different operator (§5.3.2 NOTE).

    Raises
    ------
    StateMismatchError
        If the case reads ``d`` and the payload carries no distance vector, or
        if the vector does not fit the space this case builds.
    """
    import ngsolve as ngs
    import numpy as np

    if not reads_wall(resolved.electrolyte):
        return SATURATED_WALL_DISTANCE_NM, None
    if WALL_DISTANCE_ENTRY not in data:
        raise StateMismatchError(
            f"{path} carries no {WALL_DISTANCE_ENTRY!r} vector, but this case activates a wall "
            "correction that evaluates d"
        )
    space = ngs.H1(mesh, order=order, dirichlet=resolved.wall_distance_sources)
    coefficients = np.asarray(data[WALL_DISTANCE_ENTRY], dtype=np.float64)
    if coefficients.size != space.ndof:
        raise StateMismatchError(
            f"{path} carries a distance field of {coefficients.size} coefficients, but this "
            f"case builds a space of {space.ndof} on its mesh"
        )
    field = ngs.GridFunction(space, name="wall_distance")
    field.vec.FV().NumPy()[:] = coefficients
    return field, int(coefficients.size)


def _load_state(
    path: Path, data: Mapping[str, Any], model: PhysicsModel, space: FESpace
) -> GridFunction:
    """Return the state grid function, filled from the per-component arrays.

    The lengths are checked here as well as in the descriptor gate. That is not
    redundant: the gate proves the *declared* discretisation matches, and this
    proves the arrays actually in the file match what was declared, which a
    truncated or hand-edited payload would not.
    """
    import ngsolve as ngs
    import numpy as np

    state = ngs.GridFunction(space, name=f"{model.name}_state")
    vectors = _component_vectors(state, len(model.fields))
    for declared, vector in zip(model.fields, vectors, strict=True):
        entry = f"{FIELD_PREFIX}{declared.name}"
        if entry not in data:
            present = ", ".join(sorted(str(name) for name in data)) or "nothing"
            raise StateMismatchError(f"{path} carries no {entry!r} array; it holds {present}")
        coefficients = np.asarray(data[entry], dtype=np.float64)
        target = vector.FV().NumPy()
        if coefficients.size != target.size:
            raise StateMismatchError(
                f"{path} holds {coefficients.size} coefficients for field "
                f"{declared.name!r}, but this run's space has {target.size}"
            )
        target[:] = coefficients
    return state


def restore(path: Path, *, case: CaseDocument) -> ModelSolution:
    """Return the converged solution stored at ``path``, on this case's operator.

    The residual is reassembled from the rung the ladder ends on, against the
    *stored* distance field, so the NUM-25 reaction flux taken from the restored
    solution is the flux of the operator that was actually solved. Every
    coefficient of that operator comes from :func:`ladder`, which is the same
    function the solve used, so the two cannot differ in a switch.

    Parameters
    ----------
    path
        The ``.npz`` payload of a ``nanopnp/solution/v2`` artefact.
    case
        The case document the state is being restored into. Its mesh is ingested
        and gated exactly as a solve would ingest it, because the space the
        coefficients are loaded onto is built on that mesh.

    Returns
    -------
    ModelSolution
        Carrying the model, the space, the state, the reassembled residual and
        the restored distance field. Its ``newton`` record is ``None``: the
        convergence history belongs to the run, and the artefact's summary is
        where it is kept.

    Raises
    ------
    StateMismatchError
        If the payload does not describe this case, this mesh, this
        discretisation or this model. The message names the first key that
        differs and both values; nothing is adapted (QR-12).
    """
    import ngsolve as ngs
    import numpy as np

    resolved = resolve(case)
    ingested = ingest(resolved.mesh, resolved)
    mesh = ingested.mesh
    order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
    measures = replace(AXISYMMETRIC, element_order=order)

    with np.load(path, allow_pickle=False) as archive:
        data = {name: archive[name] for name in archive.files}

    stored = _load_descriptor(path, data)
    distance, wall_ndof = _restore_distance(path, data, resolved, mesh, order=order)

    supplied = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
    if resolved.charge is not None or resolved.eps_r is not None:
        supplied = gate_fields(resolved, read_fields(resolved), mesh, measures=measures)

    top = ladder(resolved, mesh, measures, distance, supplied)[-1]
    model = top.model
    space = model.space(mesh, top.boundaries)

    _gate(
        stored,
        _descriptor(
            resolved=resolved,
            model=model,
            space=space,
            boundaries=top.boundaries,
            mesh_content_hash=ingested.content_hash,
            wall_distance_ndof=wall_ndof,
        ),
        path,
    )

    state = _load_state(path, data, model, space)
    residual = ngs.BilinearForm(space)
    residual += model.residual_form(space, top.measures, **residual_keywords(top))
    return ModelSolution(
        model=model,
        space=space,
        state=state,
        newton=None,
        residual=residual,
        wall_distance_nm=distance,
    )

"""Persisting a converged state and restoring or gating it as a warm start (FR-27, QR-08)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nanopnp.charge.stage import ResolvedFields, case_fields, read_fields
from nanopnp.core.constants import thermal_voltage
from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.io.artefact import SOLUTION_SCHEMA, Artefact
from nanopnp.mesh.ingest import deployed_mesh
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.numerics.gates import FieldSampler, WallDistanceGate, WallDistanceMeasurement
from nanopnp.numerics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
from nanopnp.physics.distance import wall_distance
from nanopnp.physics.models import (
    DEFAULT_BOUNDARIES,
    CoupledBoundaries,
    ModelSolution,
    PhysicsModel,
    case_model,
    declaration,
)
from nanopnp.solve.continuation import (
    ELECTRODES,
    Rung,
    default_ladder,
    model_reads_wall,
    reads_wall,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Expression, FESpace, GridFunction, Mesh
    from nanopnp.io.resolved import ResolvedCase

__all__ = [
    "OPERATOR_KEYS",
    "SPACE_KEYS",
    "STATE_FILENAME",
    "STATE_KEY",
    "StateMismatchError",
    "WarmStart",
    "WarmStartError",
    "check_wall_distance",
    "cold_start",
    "covering_key",
    "descriptor_leaves",
    "ladder",
    "load_initial",
    "reads_distance",
    "reads_wall",
    "restore",
    "save",
    "single_rung",
    "wall_distance_field",
    "warm_start_payload",
]

STATE_KEY = "state"

STATE_FILENAME = "state.npz"

DESCRIPTOR_ENTRY = "descriptor"

WALL_DISTANCE_ENTRY = "wall_distance_nm"

FIELD_PREFIX = "field."

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


SPACE_KEYS: tuple[str, ...] = (
    # A point evaluation outside the source domain returns a plausible number rather than raising.
    "mesh_content_hash",
    "fields",
    "ndof",
    # A ``ground`` flip moves the Dirichlet sets without moving any count.
    "boundaries",
    "model.model",
    "model.fields",
    # The same orders as ``model.fields`` in the case file's vocabulary (NUM-03).
    "model.elements",
    # NUM-02: same names, order and ndof, different meaning (section 5.3.2 warm-start NOTE).
    "model.switches.log_variables",
    "model.switches.pressure_constraint",
    # Stabilisation changes the form, not the space, but the NUM-14 reference mode compares two
    # numbers that must not be reached through each other. The constants are gated too: C_cw = 1
    # and 0.35 are different operators. Provenance prose is in OPERATOR_KEYS.
    "stabilisation",
    "model.stabilisation",
    "model.stabilisation_parameters",
    "wall_distance.ndof",
)

OPERATOR_KEYS: tuple[str, ...] = (
    # ``flow`` is also caught by ``fields``.
    "model.switches.flow",
    "model.switches.variable_density_flow",
    "model.switches.inertia",
    "model.switches.steric",
    "model.switches.dielectric_gradient_forces",
    # ``scales`` follows ``concentration_M``, the salt axis a sweep exists to walk.
    "model.scales",
    "model.materials",
    "model.deviations_from_validated_default",
    # Carries the bias and everything else keying a solve.
    "solve_hash",
    # The target solves its own distance field.
    "wall_distance.sources",
    "wall_distance.max_distance_nm",
    # Recorded, not gated: mode and parameters stay gated in SPACE_KEYS.
    "model.stabilisation_provenance",
)


class StateMismatchError(RuntimeError):
    """A stored state does not describe the run it is restored into; raised rather than adapted."""


class WarmStartError(StateMismatchError):
    """A stored state cannot warm-start this run; a StateMismatchError."""


@dataclass(frozen=True)
class WarmStart:
    """A neighbour's converged state, loaded onto this run's space.

    Parameters
    ----------
    differing
        Every operator key whose stored value differs from this run's, with both values.
    """

    solution: ModelSolution
    source: str
    differing: tuple[str, ...] = ()

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the manifest's warm-start record."""
        return {
            "status": "warm",
            "source": self.source,
            "differing_operator_keys": list(self.differing),
        }


def cold_start(reason: str) -> dict[str, Canonicalisable]:
    """Return the warm-start record of a member that climbed the ladder cold, with the reason."""
    return {"status": "cold", "source": None, "reason": reason, "differing_operator_keys": []}


def reads_distance(resolved: ResolvedCase) -> bool:
    """Return whether this case's solve reads the distance field."""
    return model_reads_wall(case_model(resolved))


def wall_distance_field(resolved: ResolvedCase, mesh: Mesh, *, order: int) -> Expression:
    """Return the distance field this case solves against."""
    if not reads_distance(resolved):
        return SATURATED_WALL_DISTANCE_NM
    return wall_distance(
        mesh,
        resolved.wall_distance_sources,
        order=order,
        max_distance_nm=resolved.wall_distance_max_nm,
    )


def check_wall_distance(
    resolved: ResolvedCase,
    mesh: Mesh,
    distance: Expression,
    *,
    coordinates: tuple[str, str] = ("r", "z"),
) -> WallDistanceMeasurement | None:
    """Gate the discrete distance field this run will read; None if it reads none.

    Raises
    ------
    GateViolationError
        If the field samples below the minimum wall distance anywhere in the fluid.
    """
    if not reads_distance(resolved):
        return None
    sampler = FieldSampler.shared(mesh, coordinates=coordinates, materials=ELECTROLYTE_DOMAINS)
    return WallDistanceGate(sampler, distance).checked()


def single_rung(
    resolved: ResolvedCase,
    mesh: Mesh,
    measures: Measures,
    distance: Expression,
    fields: ResolvedFields,
) -> Rung:
    """Return the one cold rung a case with ``continuation: none`` solves, at its target."""
    model = case_model(resolved)
    declared = declaration(resolved.model)
    driven = next(iter(ELECTRODES - {resolved.ground}))
    supplied: dict[str, Expression] = {}
    # ``wall_distance_nm`` goes to every model that reads ``d``: handed none, it would saturate
    # the wall factors (PHY-02).
    if fields.charge is not None and "fixed_charge" in declared.coefficients:
        supplied["fixed_charge"] = fields.charge.assemble(model.scales)
    if fields.eps_r is not None and "solid_fraction" in declared.coefficients:
        supplied["solid_fraction"] = fields.eps_r.chi()
    if declared.wall_distance:
        supplied["wall_distance_nm"] = distance
    # From the temperature, so every model nondimensionalises by the same V_T (NUM-09).
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
    """Return the rungs this case solves, ladder or single."""
    if resolved.continuation == "none":
        return (single_rung(resolved, mesh, measures, distance, fields),)
    # Neither deposited nor supplied charge leaves the stage-4 ramp empty (FR-27).
    return default_ladder(
        mesh,
        concentration_M=resolved.concentration_M,
        bias_V=resolved.bias_V,
        ground=resolved.ground,
        electrolyte=resolved.electrolyte,
        wall_distance_nm=distance,
        measures=measures,
        # The top rung is the case's own model; the ladder refuses one it does not end at.
        target=resolved.model,
        switches=resolved.electrolyte.switches,
        # ``physics.solid_permittivities`` reaches the ladder's models only here; omitted,
        # the membrane
        # keeps the electrolyte's eps_r, 24 times too large (PHY-03, PHY-20).
        solid_permittivities=dict(resolved.document.physics.solid_permittivities),
        fixed_charge_field=(None if fields.charge is None else fields.charge.fixed_charge_C_m3()),
        solid_fraction=None if fields.eps_r is None else fields.eps_r.chi(),
        # From ``model_options`` so the ladder and ``single_rung`` cannot differ in order
        # or mode (NUM-03, NUM-13).
        stabilisation=resolved.stabilisation,
        velocity_order=resolved.model_options.get("velocity_order"),
        pressure_order=resolved.model_options.get("pressure_order", 1),
    )


def residual_keywords(rung: Rung) -> dict[str, Expression]:
    """Return the rung keywords that are coefficients of its residual form."""
    return {
        name: value for name, value in rung.solve_kwargs.items() if name not in SOLVE_ONLY_KEYWORDS
    }


def _component_vectors(state: GridFunction, count: int) -> list[Any]:
    if count == 1:
        return [state.vec]
    return [component.vec for component in state.components]


def _component_spaces(space: FESpace, count: int) -> list[FESpace]:
    if count == 1:
        return [space]
    return [component for component in space.components]


def _field_record(model: PhysicsModel, space: FESpace) -> list[dict[str, Any]]:
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
    """Write a converged state and its descriptor to ``path``, creating the parent directory.

    Parameters
    ----------
    mesh_content_hash
        The mesh's content hash; the mesh's path is not recorded.

    Raises
    ------
    StateMismatchError
        If the corrections read the distance but the solution carries no distance field.
    """
    import numpy as np

    model = solution.model
    space = solution.space
    distance = solution.wall_distance_nm
    arrays: dict[str, Any] = {}

    stored_distance = reads_distance(resolved)
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
    if DESCRIPTOR_ENTRY not in data:
        raise StateMismatchError(
            f"{path} carries no {DESCRIPTOR_ENTRY!r} entry, so there is nothing to check it "
            "against; it is not a nanopnp/solution/v0.5 payload"
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
    import ngsolve as ngs
    import numpy as np

    if not reads_distance(resolved):
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


def descriptor_leaves(record: Mapping[str, Any], prefix: str = "") -> tuple[str, ...]:
    """Return every leaf of a descriptor as a dotted path; a list is a leaf."""
    found: list[str] = []
    for key, value in record.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping) and value:
            found.extend(descriptor_leaves(value, f"{path}."))
        else:
            found.append(path)
    return tuple(sorted(found))


def covering_key(leaf: str, keys: Sequence[str]) -> str | None:
    """Return the entry of ``keys`` covering a descriptor leaf (longest match), or None."""
    matches = [key for key in keys if leaf == key or leaf.startswith(f"{key}.")]
    return max(matches, key=len) if matches else None


def _leaf_at(record: Mapping[str, Any], path: str) -> Canonicalisable:
    value: Canonicalisable = record
    for component in path.split("."):
        if not isinstance(value, Mapping) or component not in value:
            return None
        value = value[component]
    return value


def warm_start_payload(artefact: Artefact) -> Path:
    """Return the state file of a neighbour's solve artefact; WarmStartError otherwise."""
    if artefact.schema != SOLUTION_SCHEMA:
        raise WarmStartError(
            f"a warm start needs a {SOLUTION_SCHEMA} artefact; {artefact.short_hash} is "
            f"{artefact.schema!r}, whose payload contract is a different one"
        )
    path = artefact.payload.get(STATE_KEY)
    if path is None:
        present = ", ".join(sorted(artefact.payload)) or "nothing"
        raise WarmStartError(
            f"{SOLUTION_SCHEMA} artefact {artefact.short_hash} carries no {STATE_KEY!r} "
            f"payload; it holds {present}"
        )
    return Path(path)


def load_initial(
    path: Path,
    *,
    resolved: ResolvedCase,
    mesh: Mesh,
    measures: Measures,
    distance: Expression,
    fields: ResolvedFields,
    mesh_content_hash: str,
    source: str = "",
) -> WarmStart:
    """Load a neighbour's converged state as this run's starting point.

    Parameters
    ----------
    source
        The neighbour's artefact hash, for provenance only.

    Raises
    ------
    WarmStartError
        If the payload does not describe a space this run could load into.
    """
    import numpy as np

    with np.load(path, allow_pickle=False) as archive:
        data = {name: archive[name] for name in archive.files}
    stored = _load_descriptor(path, data)

    top = ladder(resolved, mesh, measures, distance, fields)[-1]
    model = top.model
    space = model.space(mesh, top.boundaries)
    vector = getattr(distance, "vec", None)
    expected = _descriptor(
        resolved=resolved,
        model=model,
        space=space,
        boundaries=top.boundaries,
        mesh_content_hash=mesh_content_hash,
        wall_distance_ndof=None if vector is None else int(vector.FV().NumPy().size),
    )
    _gate_space(stored, expected, path)
    differing = tuple(
        key for key in OPERATOR_KEYS if _leaf_at(stored, key) != _leaf_at(expected, key)
    )
    state = _load_state(path, data, model, space)
    return WarmStart(
        solution=ModelSolution(model=model, space=space, state=state, newton=None),
        source=source or str(path),
        differing=differing,
    )


def _gate_space(stored: Mapping[str, Any], expected: Mapping[str, Any], path: Path) -> None:
    if sorted(stored) != sorted(DESCRIPTOR_KEYS):
        missing = sorted(set(DESCRIPTOR_KEYS) - set(stored))
        extra = sorted(set(stored) - set(DESCRIPTOR_KEYS))
        raise WarmStartError(
            f"{path} carries a descriptor this version cannot gate: "
            f"missing {missing or 'nothing'}, unexpected {extra or 'nothing'}. "
            "A changed payload contract is a changed artefact schema version (section 5.3.2)"
        )
    for key in SPACE_KEYS:
        found, wanted = _leaf_at(stored, key), _leaf_at(expected, key)
        if found != wanted:
            raise WarmStartError(
                f"{path} cannot warm-start this run: it was produced with a different {key}, so "
                f"its coefficients are a function on another space and mean nothing on this "
                f"one:\n"
                f"  stored:   {json.dumps(found, sort_keys=True)}\n"
                f"  this run: {json.dumps(wanted, sort_keys=True)}"
            )


def restore(
    path: Path,
    *,
    resolved: ResolvedCase,
    mesh_artefact: Artefact | None = None,
    fields: ResolvedFields | None = None,
    charge_artefact: Artefact | None = None,
) -> ModelSolution:
    """Return the converged solution stored at ``path``, on this case's operator.

    Parameters
    ----------
    mesh_artefact
        The run's mesh artefact, needed when the case generates its mesh.

    Raises
    ------
    StateMismatchError
        If the payload does not describe this case, mesh, discretisation or model.
    """
    import ngsolve as ngs
    import numpy as np

    ingested = deployed_mesh(resolved, mesh_artefact)
    mesh = ingested.mesh
    order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
    measures = AXISYMMETRIC.at_order(order)

    with np.load(path, allow_pickle=False) as archive:
        data = {name: archive[name] for name in archive.files}

    stored = _load_descriptor(path, data)
    distance, wall_ndof = _restore_distance(path, data, resolved, mesh, order=order)

    read = None
    if resolved.charge is not None or resolved.eps_r is not None:
        read = fields if fields is not None else read_fields(resolved)
    supplied = case_fields(resolved, read, charge_artefact, mesh, measures=measures)

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
    keywords = residual_keywords(top)
    residual = ngs.BilinearForm(space)
    residual += model.residual_form(space, top.measures, state=state, **keywords)
    return ModelSolution(
        model=model,
        space=space,
        state=state,
        newton=None,
        residual=residual,
        wall_distance_nm=distance,
        solid_fraction=keywords.get("solid_fraction"),
    )

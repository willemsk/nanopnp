"""VER-34: persisting a converged state, and the gate that refuses a wrong one."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from nanopnp.charge.stage import ResolvedFields
from nanopnp.io.artefact import CASE_SCHEMA, SOLUTION_SCHEMA, Artefact, StageInputs
from nanopnp.io.case import CaseDocument
from nanopnp.io.resolved import ResolvedCase
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledBoundaries, ModelSolution
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.post.indicator import axial_indicator
from nanopnp.post.qoi import indicator_currents, reaction_flux_currents, total_current
from nanopnp.solve.continuation import run_ladder
from nanopnp.solve.stage import SolveStage
from nanopnp.solve.state import (
    DESCRIPTOR_ENTRY,
    DESCRIPTOR_KEYS,
    FIELD_PREFIX,
    STATE_FILENAME,
    WALL_DISTANCE_ENTRY,
    StateMismatchError,
    ladder,
    restore,
    save,
    wall_distance_field,
)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 2.0
WALL_H_NM = 0.35

BAND_NM = 2.4

ROUTE_TOLERANCE = 1e-3

CONCENTRATION_M = 0.1
BIAS_V = 0.02

CASE = (
    f"schema: {CASE_SCHEMA}\n"
    """name: state-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: {concentration_M}
  temperature_K: 298.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: willems2020_nacl, wall: true, concentration: true}}
    mobility:     {{model: willems2020_nacl, wall: true, concentration: true}}
    viscosity:    {{model: willems2020_nacl, wall: true, concentration: true}}
    permittivity: {{model: willems2020_nacl}}
    density:      {{model: willems2020_nacl}}
boundary_conditions:
  bias_V: {bias_V}
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [current]
"""
)


@dataclass
class Solved:
    document: CaseDocument
    solution: ModelSolution
    path: Path
    work: Path
    artefact: Artefact | None = None


class _KeepingStage(SolveStage):
    kept: ModelSolution | None = None

    def _write(
        self,
        solution: ModelSolution,
        *,
        resolved: ResolvedCase,
        mesh_content_hash: str,
        boundaries: CoupledBoundaries,
    ) -> dict[str, Path]:
        self.kept = solution
        return super()._write(
            solution,
            resolved=resolved,
            mesh_content_hash=mesh_content_hash,
            boundaries=boundaries,
        )


@pytest.fixture(scope="module")
def mesh_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("mesh") / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(path))
    return path


@pytest.fixture(scope="module")
def solved(mesh_path: Path) -> Solved:
    work = mesh_path.parent
    document = loads_case(
        CASE.format(mesh_path=mesh_path, concentration_M=CONCENTRATION_M, bias_V=BIAS_V)
    )
    stage = _KeepingStage(workspace=work / "fields")
    artefact = stage.run(StageInputs(resolved=resolve(document)))
    assert stage.kept is not None
    return Solved(
        document=document,
        solution=stage.kept,
        path=artefact.payload["state"],
        work=work,
        artefact=artefact,
    )


@pytest.fixture(scope="module")
def stabilised(tmp_path_factory: pytest.TempPathFactory, mesh_path: Path) -> Solved:
    work = tmp_path_factory.mktemp("stabilised")
    document = loads_case(
        CASE.format(mesh_path=mesh_path, concentration_M=CONCENTRATION_M, bias_V=BIAS_V).replace(
            "stabilisation: none", "stabilisation: supg"
        )
    )
    resolved = resolve(document)
    ingested = ingest(resolved.mesh, resolved)
    order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
    measures = replace(AXISYMMETRIC, element_order=order)
    distance = wall_distance_field(resolved, ingested.mesh, order=order)
    empty = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
    rungs = ladder(resolved, ingested.mesh, measures, distance, empty)
    result = run_ladder(rungs)

    path = save(
        result.solution,
        work / STATE_FILENAME,
        resolved=resolved,
        mesh_content_hash=ingested.content_hash,
        boundaries=rungs[-1].boundaries,
    )
    return Solved(document=document, solution=result.solution, path=path, work=work)


def _arrays(path: Path) -> dict[str, Any]:
    import numpy as np

    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def _rewrite(path: Path, arrays: dict[str, Any]) -> Path:
    import numpy as np

    with path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    return path


def _with_descriptor(solved: Solved, tmp_path: Path, descriptor: dict[str, Any]) -> Path:
    import numpy as np

    arrays = _arrays(solved.path)
    arrays[DESCRIPTOR_ENTRY] = np.array(json.dumps(descriptor, sort_keys=True))
    return _rewrite(tmp_path / STATE_FILENAME, arrays)


def _stored_descriptor(solved: Solved) -> dict[str, Any]:
    record: dict[str, Any] = json.loads(str(_arrays(solved.path)[DESCRIPTOR_ENTRY]))
    return record


def _components(solution: ModelSolution) -> list[Any]:
    if len(solution.model.fields) == 1:
        return [solution.state.vec]
    return [component.vec for component in solution.state.components]


# -- the round trip -----------------------------------------------------------


def test_ver34_every_component_coefficient_returns_bit_for_bit(solved: Solved) -> None:
    import numpy as np

    restored = restore(solved.path, resolved=resolve(solved.document))
    assert restored.space.ndof == solved.solution.space.ndof
    names = [field.name for field in solved.solution.model.fields]
    for name, before, after in zip(
        names, _components(solved.solution), _components(restored), strict=True
    ):
        original = np.asarray(before.FV().NumPy(), dtype=np.float64)
        recovered = np.asarray(after.FV().NumPy(), dtype=np.float64)
        assert recovered.shape == original.shape, name
        assert np.max(np.abs(recovered - original)) == 0.0, name


# NUM-25
def test_ver34_the_restored_operator_gives_the_same_reaction_flux(solved: Solved) -> None:
    live = reaction_flux_currents(solved.solution)
    recovered = reaction_flux_currents(restore(solved.path, resolved=resolve(solved.document)))
    assert set(recovered) == set(live)
    for species, value in live.items():
        assert recovered[species] == pytest.approx(value, rel=1e-12), species


# NUM-25
def test_ver34_a_stabilised_state_restores_with_the_operator_it_converged_on(
    stabilised: Solved,
) -> None:
    live = reaction_flux_currents(stabilised.solution)
    recovered = reaction_flux_currents(
        restore(stabilised.path, resolved=resolve(stabilised.document))
    )
    assert set(recovered) == set(live)
    for species, value in live.items():
        assert recovered[species] == pytest.approx(value, rel=1e-12), species


# PHY-02
def test_ver34_the_wall_distance_field_is_restored_and_not_re_solved(
    solved: Solved, tmp_path: Path
) -> None:
    import numpy as np

    arrays = _arrays(solved.path)
    assert WALL_DISTANCE_ENTRY in arrays, "an epnp-ns case reads d and must store it"
    moved = np.asarray(arrays[WALL_DISTANCE_ENTRY], dtype=np.float64).copy()
    moved[0] += 0.25
    arrays[WALL_DISTANCE_ENTRY] = moved
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)

    restored = restore(path, resolved=resolve(solved.document))
    recovered = np.asarray(restored.wall_distance_nm.vec.FV().NumPy(), dtype=np.float64)
    assert np.max(np.abs(recovered - moved)) == 0.0


# FR-27, NUM-25, NUM-34
def test_ver34_the_stage_payload_is_a_state_file_this_module_can_restore(
    solved: Solved,
) -> None:
    artefact = solved.artefact
    assert artefact is not None
    assert artefact.schema == SOLUTION_SCHEMA
    payload = artefact.payload["state"]
    assert payload.name == STATE_FILENAME

    restored = restore(payload, resolved=resolve(solved.document))
    assert restored.residual is not None
    assert set(reaction_flux_currents(restored)) == {"Na+", "Cl-"}


# NUM-26, QR-04, NUM-24, NUM-25
def test_ver34_the_restored_operator_agrees_with_a_route_that_never_sees_it(
    solved: Solved,
) -> None:
    restored = restore(solved.path, resolved=resolve(solved.document))
    # Read from the case, as the solve reads it: another order would integrate a
    # different discretisation (NUM-01).
    order = int(resolve(solved.document).model_options.get("order", AXISYMMETRIC.element_order))
    psi = axial_indicator(restored.space.mesh, lower_nm=-BAND_NM, upper_nm=BAND_NM, order=order)
    measures = replace(AXISYMMETRIC, element_order=order)
    reaction = total_current(reaction_flux_currents(restored))
    indicator = total_current(indicator_currents(restored, measures, psi))
    assert indicator != 0.0
    assert abs(reaction - indicator) / abs(indicator) < ROUTE_TOLERANCE


# -- the descriptor gate ------------------------------------------------------


def _mutations() -> list[tuple[str, Callable[[Any], Any]]]:
    return [
        ("solve_hash", lambda value: "0" * len(str(value))),
        ("mesh_content_hash", lambda value: "0" * len(str(value))),
        ("boundaries", lambda value: {**value, "potential": ["cis"]}),
        ("stabilisation", lambda value: "streamline"),
        ("wall_distance", lambda value: {**value, "max_distance_nm": 99.0}),
        ("model", lambda value: {**value, "stabilisation": "crosswind"}),
        ("fields", lambda value: [{**value[0], "order": 3}, *value[1:]]),
        ("ndof", lambda value: int(value) + 1),
    ]


# QR-12
@pytest.mark.parametrize(("key", "mutate"), _mutations(), ids=[key for key, _ in _mutations()])
def test_ver34_a_descriptor_that_differs_in_one_key_aborts_naming_it(
    solved: Solved, tmp_path: Path, key: str, mutate: Callable[[Any], Any]
) -> None:
    stored = _stored_descriptor(solved)
    assert key in stored, f"{key} is in DESCRIPTOR_KEYS but was never written"
    changed = mutate(stored[key])
    assert changed != stored[key], key
    path = _with_descriptor(solved, tmp_path, {**stored, key: changed})

    with pytest.raises(StateMismatchError) as raised:
        restore(path, resolved=resolve(solved.document))
    message = str(raised.value)
    assert f"different {key}" in message
    assert json.dumps(changed, sort_keys=True) in message
    assert json.dumps(stored[key], sort_keys=True) in message


def test_ver34_a_case_differing_only_in_what_it_reports_restores(solved: Solved) -> None:
    other = loads_case(
        CASE.format(
            mesh_path=solved.work / "pore.vol", concentration_M=CONCENTRATION_M, bias_V=BIAS_V
        )
        .replace("name: state-probe", "name: renamed")
        .replace("outputs: [current]", "outputs: [current, eof_rate, fields]")
    )
    assert resolve(other).provenance != resolve(solved.document).provenance
    assert resolve(other).solve_provenance == resolve(solved.document).solve_provenance

    restored = restore(solved.path, resolved=resolve(other))
    assert restored.space.ndof == solved.solution.space.ndof


def test_ver34_the_gate_checks_every_key_it_declares(solved: Solved) -> None:
    assert tuple(key for key, _ in _mutations()) == DESCRIPTOR_KEYS
    assert sorted(_stored_descriptor(solved)) == sorted(DESCRIPTOR_KEYS)


def test_ver34_a_descriptor_missing_a_key_is_refused_rather_than_skipped(
    solved: Solved, tmp_path: Path
) -> None:
    stored = _stored_descriptor(solved)
    del stored["ndof"]
    path = _with_descriptor(solved, tmp_path, stored)
    with pytest.raises(StateMismatchError, match="missing \\['ndof'\\]"):
        restore(path, resolved=resolve(solved.document))


def test_ver34_a_descriptor_carrying_an_unknown_key_is_refused(
    solved: Solved, tmp_path: Path
) -> None:
    path = _with_descriptor(solved, tmp_path, {**_stored_descriptor(solved), "temperature": 310.0})
    with pytest.raises(StateMismatchError, match="unexpected \\['temperature'\\]"):
        restore(path, resolved=resolve(solved.document))


def test_ver34_a_payload_without_a_descriptor_is_refused_by_schema(
    solved: Solved, tmp_path: Path
) -> None:
    arrays = _arrays(solved.path)
    del arrays[DESCRIPTOR_ENTRY]
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)
    with pytest.raises(StateMismatchError, match=SOLUTION_SCHEMA):
        restore(path, resolved=resolve(solved.document))


def test_ver34_the_solution_schema_is_v2(solved: Solved) -> None:
    assert SOLUTION_SCHEMA == "nanopnp/solution/v0.5"


# -- the fields the state itself carries --------------------------------------


def test_ver34_a_truncated_coefficient_array_is_refused_by_length(
    solved: Solved, tmp_path: Path
) -> None:
    import numpy as np

    arrays = _arrays(solved.path)
    name = next(key for key in arrays if str(key).startswith(FIELD_PREFIX))
    arrays[name] = np.asarray(arrays[name], dtype=np.float64)[:-1]
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)
    with pytest.raises(StateMismatchError, match="coefficients for field"):
        restore(path, resolved=resolve(solved.document))


def test_ver34_a_missing_component_array_names_what_the_file_holds(
    solved: Solved, tmp_path: Path
) -> None:
    arrays = _arrays(solved.path)
    name = next(key for key in arrays if str(key).startswith(FIELD_PREFIX))
    del arrays[name]
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)
    with pytest.raises(StateMismatchError, match="carries no"):
        restore(path, resolved=resolve(solved.document))


# PHY-02
def test_ver34_a_case_reading_d_without_a_stored_distance_is_refused(
    solved: Solved, tmp_path: Path
) -> None:
    arrays = _arrays(solved.path)
    del arrays[WALL_DISTANCE_ENTRY]
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)
    with pytest.raises(StateMismatchError, match=WALL_DISTANCE_ENTRY):
        restore(path, resolved=resolve(solved.document))


# PHY-02
def test_ver34_a_cold_solve_carries_the_wall_distance_the_ladder_carries(solved: Solved) -> None:
    cold = resolve(
        loads_case(
            CASE.format(
                mesh_path=solved.work / "pore.vol",
                concentration_M=CONCENTRATION_M,
                bias_V=BIAS_V,
            ).replace("continuation: default_ladder", "continuation: none")
        )
    )
    assert cold.continuation == "none"
    ingested = ingest(cold.mesh, cold)
    order = int(cold.model_options.get("order", AXISYMMETRIC.element_order))
    measures = replace(AXISYMMETRIC, element_order=order)
    distance = wall_distance_field(cold, ingested.mesh, order=order)
    empty = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())

    rungs = ladder(cold, ingested.mesh, measures, distance, empty)

    assert len(rungs) == 1, "continuation: none is one rung, at the target point"
    assert rungs[0].solve_kwargs["wall_distance_nm"] is distance

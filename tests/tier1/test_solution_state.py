"""VER-34 — persisting a converged state, and the gate that refuses a wrong one.

Stage 10's payload is the only route by which a solved state outlives the
process that solved it, and every later stage that is served from a cache hit
reads it rather than Newton. Two claims therefore have to hold, and each of them
fails silently:

- the numbers come back *exactly*. Not to a tolerance: a coefficient vector is
  either the one that was written or it is a different state wearing its
  provenance, and a round-trip that loses the last bits of a converged solution
  would show up as a QoI that drifts by an amount nobody can attribute;
- the operator comes back too. NUM-25 is the assembled residual evaluated on the
  constrained degrees of freedom, so a restored solution without a residual can
  answer only half of the QR-04 cross-check. The residual is reassembled from
  the rung the ladder ends on, against the **stored** wall-distance field — and
  the test that it is the stored one, rather than a fresh screened-Poisson
  solve, is the perturbation test below, because a re-solved field agrees with
  the stored one to about ten digits and disagreeing in the last bits is exactly
  the failure that produces a plausible wrong flux.

What guards both is the descriptor: everything in it is re-derived on load and
compared key by key, and the first difference aborts (QR-12). Restore is a gate,
never an adaptation, so each of those keys gets a test that mutating it alone is
refused by name.

Stabilisation is ``none`` throughout (NUM-11); the mesh is the coarsest one that
carries all four domains, because what is under test is the payload rather than
the physics.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from nanopnp.charge.stage import ResolvedFields
from nanopnp.io.artefact import SOLUTION_SCHEMA, StageInputs
from nanopnp.io.case import CaseDocument, loads_case, resolve
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import ModelSolution
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
WALL_H_NM = 0.5
"""Element size of the mesh the physics assertions run on.

Not the coarsest mesh that converges. With the wall corrections active the two
QoI routes of NUM-26 disagree by 40 % on a 124-element mesh and by 9.6e-05 on
this one: the 6.2 nm^-1 ion wall function of PHY-08 varies over a tenth of the
pore radius, and a distance field carrying 273 degrees of freedom does not
resolve it. Route agreement is therefore the oracle only above a resolution the
mesh has to actually meet, which is why the restored solution is cross-checked
here and not on the cheaper mesh below.
"""

COARSE_MAXH_NM = 4.0
COARSE_WALL_H_NM = 1.0
"""Element size of the mesh the wiring assertion runs on.

Stage 10 writing the file this module reads is a question about filenames and
keyword arguments; it needs a converged solve and no resolved one, so it gets
the cheapest mesh that carries all four domains.
"""

BAND_NM = 2.4
"""Half-height of the NUM-24 indicator band: 0.8 of the membrane's half-thickness."""

ROUTE_TOLERANCE = 1e-3
"""NUM-26's relative agreement between the two routes."""

CONCENTRATION_M = 0.1
BIAS_V = 0.02

CASE = """
schema: nanopnp/case/v1
name: state-probe
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


@dataclass
class Solved:
    """One converged solve, the state it wrote, and what wrote it."""

    document: CaseDocument
    solution: ModelSolution
    path: Path
    work: Path


@pytest.fixture(scope="module")
def solved(tmp_path_factory: pytest.TempPathFactory) -> Solved:
    """Solve a small ePNP-NS case and save it, keeping the in-memory solution.

    The ladder is climbed here rather than through
    :class:`~nanopnp.solve.stage.SolveStage` because the round-trip assertion
    needs the coefficients as Newton left them, and the stage returns an
    artefact rather than a state. It is the same construction either way: the
    stage calls :func:`~nanopnp.solve.state.ladder` and this calls it too, which
    is why that function was moved out of the stage in the first place.
    """
    work = tmp_path_factory.mktemp("state")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))

    document = loads_case(
        CASE.format(mesh_path=mesh_path, concentration_M=CONCENTRATION_M, bias_V=BIAS_V)
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
    """Return every array of an ``.npz`` payload, eagerly."""
    import numpy as np

    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def _rewrite(path: Path, arrays: dict[str, Any]) -> Path:
    """Write ``arrays`` to ``path`` in the payload's own format and return it."""
    import numpy as np

    with path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    return path


def _with_descriptor(solved: Solved, tmp_path: Path, descriptor: dict[str, Any]) -> Path:
    """Return a copy of the payload carrying ``descriptor`` instead of its own."""
    import numpy as np

    arrays = _arrays(solved.path)
    arrays[DESCRIPTOR_ENTRY] = np.array(json.dumps(descriptor, sort_keys=True))
    return _rewrite(tmp_path / STATE_FILENAME, arrays)


def _stored_descriptor(solved: Solved) -> dict[str, Any]:
    """Return the descriptor the payload was written with."""
    record: dict[str, Any] = json.loads(str(_arrays(solved.path)[DESCRIPTOR_ENTRY]))
    return record


def _components(solution: ModelSolution) -> list[Any]:
    """Return each field's coefficient vector, for a model of any arity."""
    if len(solution.model.fields) == 1:
        return [solution.state.vec]
    return [component.vec for component in solution.state.components]


# -- the round trip -----------------------------------------------------------


def test_ver34_every_component_coefficient_returns_bit_for_bit(solved: Solved) -> None:
    """Restore reproduces the solved coefficients to exactly zero difference.

    Exactly, not to a tolerance. The payload is a coefficient record, not a
    resampling: any nonzero difference here would mean the file and the space
    disagree about what an entry means, and that error is a smooth-looking
    field, not a crash.
    """
    import numpy as np

    restored = restore(solved.path, case=solved.document)
    assert restored.space.ndof == solved.solution.space.ndof
    names = [field.name for field in solved.solution.model.fields]
    for name, before, after in zip(
        names, _components(solved.solution), _components(restored), strict=True
    ):
        original = np.asarray(before.FV().NumPy(), dtype=np.float64)
        recovered = np.asarray(after.FV().NumPy(), dtype=np.float64)
        assert recovered.shape == original.shape, name
        assert np.max(np.abs(recovered - original)) == 0.0, name


def test_ver34_the_restored_operator_gives_the_same_reaction_flux(solved: Solved) -> None:
    """The reassembled residual is the operator the solve converged on (NUM-25).

    ``ModelSolution.residual`` is what the NUM-25 route applies; a restored
    solution carrying a residual built from a *different* rung — one switch on,
    one coefficient defaulted — would still return a number, and the number
    would be wrong by an amount that looks like a modelling difference. Equality
    to the live solution's flux is what says it is the same form.
    """
    live = reaction_flux_currents(solved.solution)
    recovered = reaction_flux_currents(restore(solved.path, case=solved.document))
    assert set(recovered) == set(live)
    for species, value in live.items():
        assert recovered[species] == pytest.approx(value, rel=1e-12), species


def test_ver34_the_wall_distance_field_is_restored_and_not_re_solved(
    solved: Solved, tmp_path: Path
) -> None:
    """The stored PHY-02 vector reaches the operator, rather than a fresh solve.

    Asserted by perturbation because agreement proves nothing here: the
    screened-Poisson solve behind the distance field is deterministic within one
    build, so a re-solved field would match the stored one to ten digits and
    this test would pass while the guarantee — that a restore on another library
    version reassembles the *same* operator — quietly did not hold. A payload
    whose distance vector has been moved must restore the moved field.
    """
    import numpy as np

    arrays = _arrays(solved.path)
    assert WALL_DISTANCE_ENTRY in arrays, "an epnp-ns case reads d and must store it"
    moved = np.asarray(arrays[WALL_DISTANCE_ENTRY], dtype=np.float64).copy()
    moved[0] += 0.25
    arrays[WALL_DISTANCE_ENTRY] = moved
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)

    restored = restore(path, case=solved.document)
    recovered = np.asarray(restored.wall_distance_nm.vec.FV().NumPy(), dtype=np.float64)
    assert np.max(np.abs(recovered - moved)) == 0.0


def test_ver34_the_stage_payload_is_a_state_file_this_module_can_restore(
    tmp_path: Path,
) -> None:
    """Stage 10 writes the payload this module reads (FR-27, section 5.3.2).

    The stage and the fixture above build the ladder through the same function,
    so what is at stake is only the wiring — the filename, the boundaries handed
    to :func:`~nanopnp.solve.state.save`, and the mesh hash. Each of those is a
    silent failure: a payload keyed on the wrong boundaries restores into a
    space with different constraints, and the NUM-25 reaction flux is then taken
    over a boundary the solve left free.

    On its own coarse mesh, because nothing here reads a number out of the
    solution — only that the file exists under the name the stage promised and
    that the gate accepts it.
    """
    work = tmp_path / "coarse"
    work.mkdir()
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=COARSE_MAXH_NM, wall_h_nm=COARSE_WALL_H_NM).ngmesh.Save(str(mesh_path))
    document = loads_case(
        CASE.format(mesh_path=mesh_path, concentration_M=CONCENTRATION_M, bias_V=BIAS_V)
    )

    artefact = SolveStage(workspace=work / "fields").run(StageInputs(case=document))
    assert artefact.schema == SOLUTION_SCHEMA
    payload = artefact.payload["state"]
    assert payload.name == STATE_FILENAME

    restored = restore(payload, case=document)
    assert restored.residual is not None
    assert set(reaction_flux_currents(restored)) == {"Na+", "Cl-"}


def test_ver34_the_restored_operator_agrees_with_a_route_that_never_sees_it(
    solved: Solved,
) -> None:
    """The reassembled residual passes the NUM-26 cross-check (QR-04, RSK-03).

    This is the oracle the two tests above cannot be: they compare the restored
    solution against the live one, and a save path and a restore path that share
    a mistake would agree with each other perfectly. The NUM-24 indicator form
    touches no residual at all — it rebuilds the flux from the coefficients
    through the model's own seams — so its agreement with the NUM-25 reaction
    flux of the *restored* solution is evidence about the operator rather than
    about the round trip.

    The tolerance is NUM-26's own 1e-3, and the mesh is the one that meets it;
    see :data:`MAXH_NM`.
    """
    restored = restore(solved.path, case=solved.document)
    # Read from the case rather than pinned, exactly as the solve reads it: an
    # indicator built at a different order than the model integrates a different
    # discretisation and the cross-check stops being one (NUM-01).
    order = int(resolve(solved.document).model_options.get("order", AXISYMMETRIC.element_order))
    psi = axial_indicator(restored.space.mesh, lower_nm=-BAND_NM, upper_nm=BAND_NM, order=order)
    measures = replace(AXISYMMETRIC, element_order=order)
    reaction = total_current(reaction_flux_currents(restored))
    indicator = total_current(indicator_currents(restored, measures, psi))
    assert indicator != 0.0
    assert abs(reaction - indicator) / abs(indicator) < ROUTE_TOLERANCE


# -- the descriptor gate ------------------------------------------------------


def _mutations() -> list[tuple[str, Callable[[Any], Any]]]:
    """Return one mutation per descriptor key, each changing that key alone.

    Every key is here on purpose rather than a representative sample: a key the
    gate records and does not compare is a key that reads as protection and is
    not, and the failure it lets through — a state restored onto a space it was
    not solved on — is the one this module exists to prevent.
    """
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


@pytest.mark.parametrize(("key", "mutate"), _mutations(), ids=[key for key, _ in _mutations()])
def test_ver34_a_descriptor_that_differs_in_one_key_aborts_naming_it(
    solved: Solved, tmp_path: Path, key: str, mutate: Callable[[Any], Any]
) -> None:
    """Each recorded key is compared, and the diagnostic carries both values.

    Naming the key is not decoration. The operator this refuses to build is one
    that would converge, so the message is the whole diagnosis: it has to say
    which of the case, the mesh, the discretisation or the model moved, and what
    it moved from and to (QR-12).
    """
    stored = _stored_descriptor(solved)
    assert key in stored, f"{key} is in DESCRIPTOR_KEYS but was never written"
    changed = mutate(stored[key])
    assert changed != stored[key], key
    path = _with_descriptor(solved, tmp_path, {**stored, key: changed})

    with pytest.raises(StateMismatchError) as raised:
        restore(path, case=solved.document)
    message = str(raised.value)
    assert f"different {key}" in message
    assert json.dumps(changed, sort_keys=True) in message
    assert json.dumps(stored[key], sort_keys=True) in message


def test_ver34_a_case_differing_only_in_what_it_reports_restores(solved: Solved) -> None:
    """``outputs:`` and ``name:`` do not gate the state, because they do not solve it.

    The gate exists to refuse a state whose coefficients describe a different
    problem. Asking a converged case for one more quantity — adding ``fields``
    so that a run writes a picture — changes neither the operator, the space nor
    the boundary data, so the state still describes the run and refusing it
    would throw away a solve for a question about post-processing. The digest
    the descriptor carries is the one stage 10 keys its artefact on, so a state
    the store serves is a state this gate admits; asserting both here is what
    stops the two drifting apart.
    """
    other = loads_case(
        CASE.format(
            mesh_path=solved.work / "pore.vol", concentration_M=CONCENTRATION_M, bias_V=BIAS_V
        )
        .replace("name: state-probe", "name: renamed")
        .replace("outputs: [current]", "outputs: [current, eof_rate, fields]")
    )
    assert resolve(other).provenance != resolve(solved.document).provenance
    assert resolve(other).solve_provenance == resolve(solved.document).solve_provenance

    restored = restore(solved.path, case=other)
    assert restored.space.ndof == solved.solution.space.ndof


def test_ver34_the_gate_checks_every_key_it_declares(solved: Solved) -> None:
    """The parametrisation above covers ``DESCRIPTOR_KEYS`` exactly.

    Written as an assertion rather than left to review: a key added to the
    descriptor without a mutation here would be recorded, compared, and never
    tested, which is indistinguishable from being recorded and not compared.
    """
    assert tuple(key for key, _ in _mutations()) == DESCRIPTOR_KEYS
    assert sorted(_stored_descriptor(solved)) == sorted(DESCRIPTOR_KEYS)


def test_ver34_a_descriptor_missing_a_key_is_refused_rather_than_skipped(
    solved: Solved, tmp_path: Path
) -> None:
    """A payload this version cannot gate is not one it restores.

    Skipping a key the file does not carry would make the gate weaker the older
    the payload is, which is the opposite of what a schema version is for.
    """
    stored = _stored_descriptor(solved)
    del stored["ndof"]
    path = _with_descriptor(solved, tmp_path, stored)
    with pytest.raises(StateMismatchError, match="missing \\['ndof'\\]"):
        restore(path, case=solved.document)


def test_ver34_a_descriptor_carrying_an_unknown_key_is_refused(
    solved: Solved, tmp_path: Path
) -> None:
    """A payload written by a later version is refused, not partially read."""
    path = _with_descriptor(solved, tmp_path, {**_stored_descriptor(solved), "temperature": 310.0})
    with pytest.raises(StateMismatchError, match="unexpected \\['temperature'\\]"):
        restore(path, case=solved.document)


def test_ver34_a_payload_without_a_descriptor_is_refused_by_schema(
    solved: Solved, tmp_path: Path
) -> None:
    """The ``nanopnp/solution/v1`` payload carried numbers and no record of them.

    That is the whole reason for the version bump: a coefficient array is
    meaningless without the space it belongs to, and a restore that inferred the
    space from the case rather than checking it against the file would read a v1
    payload as a v2 one whenever the two happened to be the same length.
    """
    arrays = _arrays(solved.path)
    del arrays[DESCRIPTOR_ENTRY]
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)
    with pytest.raises(StateMismatchError, match=SOLUTION_SCHEMA):
        restore(path, case=solved.document)


def test_ver34_the_solution_schema_is_v2(solved: Solved) -> None:
    """The payload contract changed, so the artefact schema version did too.

    Section 5.3.2: a changed payload is a changed schema. Pinned here because
    the constant is what the store, the registry and the manifest all agree on,
    and a payload silently reinterpreted under an unchanged version is a wrong
    number with a correct-looking provenance.
    """
    assert SOLUTION_SCHEMA == "nanopnp/solution/v2"


# -- the fields the state itself carries --------------------------------------


def test_ver34_a_truncated_coefficient_array_is_refused_by_length(
    solved: Solved, tmp_path: Path
) -> None:
    """The arrays are checked as well as the descriptor that describes them.

    Not redundant with the gate: the descriptor proves the *declared*
    discretisation matches, and this proves the file actually holds it. A
    payload truncated in transit passes the first check and fails this one.
    """
    import numpy as np

    arrays = _arrays(solved.path)
    name = next(key for key in arrays if str(key).startswith(FIELD_PREFIX))
    arrays[name] = np.asarray(arrays[name], dtype=np.float64)[:-1]
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)
    with pytest.raises(StateMismatchError, match="coefficients for field"):
        restore(path, case=solved.document)


def test_ver34_a_missing_component_array_names_what_the_file_holds(
    solved: Solved, tmp_path: Path
) -> None:
    """The diagnostic lists the entries present, because this is a typo's home."""
    arrays = _arrays(solved.path)
    name = next(key for key in arrays if str(key).startswith(FIELD_PREFIX))
    del arrays[name]
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)
    with pytest.raises(StateMismatchError, match="carries no"):
        restore(path, case=solved.document)


def test_ver34_a_case_reading_d_without_a_stored_distance_is_refused(
    solved: Solved, tmp_path: Path
) -> None:
    """A saturated constant is not a substitute for the field that was solved.

    Restoring without the vector would reassemble every wall factor at its
    far-field value: the ion wall function saturates to 1, the viscosity
    correction to 1, and the resulting operator is the classical one wearing an
    ePNP-NS provenance (PHY-02, section 5.3.2 NOTE).
    """
    arrays = _arrays(solved.path)
    del arrays[WALL_DISTANCE_ENTRY]
    path = _rewrite(tmp_path / STATE_FILENAME, arrays)
    with pytest.raises(StateMismatchError, match=WALL_DISTANCE_ENTRY):
        restore(path, case=solved.document)

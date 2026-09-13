"""VER-37 (Tier 1) — the descriptor partition, and what a warm start may ignore.

:func:`~nanopnp.solve.state.restore` reloads a run's *own* converged state and
every descriptor key must match. A sweep warm-starts one operating point from
another, and two of those keys differ by construction: ``solve_hash`` carries the
bias and everything else that keys a solve, and ``model.scales`` is the NUM-09
scale set, which is a function of the concentration. Gating on either would
refuse the two axes the sweep exists to walk (FR-24, the section 5.3.2 warm-start
NOTE).

So the descriptor's keys are partitioned into those that determine the **space**
and those that determine the **operator**, and this module is where being wrong
about that partition stops being silent. A coefficient vector loaded into a space
it was not produced on is a different function, and there is no residual it would
fail to reduce — so an ungated space key does not fail loudly at any later point,
it produces a converged wrong answer. The enumeration is therefore checked in
**both directions** against the descriptor a real solve produces: every leaf
covered exactly once, and every entry of both lists covering something.

The warm-against-cold agreement — that a point reached warm and the same point
solved cold give the same numbers — is the other half of VER-37 and is a Tier 2
activity, because it needs a converged pair. It is in ``tests/tier2/test_sweep.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from nanopnp.charge.stage import ResolvedFields
from nanopnp.io.artefact import SOLUTION_SCHEMA, Artefact
from nanopnp.io.case import CaseDocument, loads_case, resolve
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.solve.continuation import run_ladder
from nanopnp.solve.state import (
    DESCRIPTOR_ENTRY,
    DESCRIPTOR_KEYS,
    OPERATOR_KEYS,
    SPACE_KEYS,
    STATE_FILENAME,
    STATE_KEY,
    WALL_DISTANCE_ENTRY,
    WarmStart,
    WarmStartError,
    covering_key,
    descriptor_leaves,
    ladder,
    load_initial,
    save,
    wall_distance_field,
    warm_start_payload,
)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 0.35
"""The coarsest mesh NUM-34 admits with the wall corrections on; see
``tests/tier1/test_wall_distance.py``. Nothing here reads a number out of the
solution — what is under test is the descriptor — so the mesh is the cheapest
admissible one rather than the one that meets NUM-26."""

CASE = """
schema: nanopnp/case/v1
name: warm-probe
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
  ground: {ground}
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: {stabilisation}
outputs: [current]
"""


@dataclass
class Neighbour:
    """One converged state, its case, and the ingredients a warm start needs."""

    document: CaseDocument
    path: Path
    mesh_path: Path


def _document(mesh_path: Path, **overrides: object) -> CaseDocument:
    """Return the probe case, with any of its five knobs moved."""
    settings: dict[str, object] = {
        "mesh_path": mesh_path,
        "concentration_M": 0.1,
        "bias_V": 0.02,
        "ground": "cis",
        "stabilisation": "none",
    }
    settings.update(overrides)
    return loads_case(CASE.format(**settings))


@pytest.fixture(scope="module")
def neighbour(tmp_path_factory: pytest.TempPathFactory) -> Neighbour:
    """Solve one case and save its state: the neighbour every test starts from."""
    work = tmp_path_factory.mktemp("warm")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))

    document = _document(mesh_path)
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
    return Neighbour(document=document, path=path, mesh_path=mesh_path)


def _stored_descriptor(neighbour: Neighbour) -> dict[str, Any]:
    """Return the descriptor the neighbour's payload was written with."""
    import numpy as np

    with np.load(neighbour.path, allow_pickle=False) as archive:
        record: dict[str, Any] = json.loads(str(archive[DESCRIPTOR_ENTRY]))
    return record


def _load(neighbour: Neighbour, document: CaseDocument, *, path: Path | None = None) -> WarmStart:
    """Warm-start ``document`` from the neighbour's payload, as a sweep member would."""
    resolved = resolve(document)
    ingested = ingest(resolved.mesh, resolved)
    order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
    measures = replace(AXISYMMETRIC, element_order=order)
    distance = wall_distance_field(resolved, ingested.mesh, order=order)
    empty = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
    return load_initial(
        path or neighbour.path,
        resolved=resolved,
        mesh=ingested.mesh,
        measures=measures,
        distance=distance,
        fields=empty,
        mesh_content_hash=ingested.content_hash,
        source="neighbour",
    )


# -- the partition, in both directions ----------------------------------------


def test_ver37_every_descriptor_leaf_is_covered_by_exactly_one_side(neighbour: Neighbour) -> None:
    """Every leaf of a real descriptor falls in exactly one of the two lists.

    Against the descriptor a *solve* produced rather than one written here: a
    key added to :func:`~nanopnp.solve.state._descriptor` and forgotten in the
    partition would be ungated, and being ungated is the failure that cannot be
    observed at run time — a coefficient vector loaded into the wrong space is
    a different function and reduces its residual perfectly well.
    """
    leaves = descriptor_leaves(_stored_descriptor(neighbour))
    assert leaves, "a real solve must produce a descriptor with leaves in it"
    for leaf in leaves:
        space = covering_key(leaf, SPACE_KEYS)
        operator = covering_key(leaf, OPERATOR_KEYS)
        assert (space is None) != (operator is None), (
            f"descriptor leaf {leaf!r} is covered by "
            f"{'both' if space and operator else 'neither'} of SPACE_KEYS and OPERATOR_KEYS; "
            "every leaf must be gated or explicitly permitted to differ"
        )


def test_ver37_every_entry_of_both_lists_covers_something(neighbour: Neighbour) -> None:
    """The other direction: no entry names a descriptor key that no longer exists.

    A path left behind by a rename would read as protection and be none. Both
    lists are checked, because an orphaned *operator* entry is just as wrong: it
    is what the manifest's record of "which keys differed" is enumerated over.
    """
    leaves = descriptor_leaves(_stored_descriptor(neighbour))
    for key in (*SPACE_KEYS, *OPERATOR_KEYS):
        assert any(covering_key(leaf, (key,)) is not None for leaf in leaves), (
            f"{key!r} is in the partition but names nothing in the descriptor a solve "
            "produces; it is a path left behind by a rename"
        )


def test_ver37_the_partition_covers_the_descriptor_keys_it_claims_to() -> None:
    """Every top-level descriptor key has at least one entry beneath it.

    Cheap, and it catches the case the two tests above cannot: a whole key
    dropped from both lists *and* absent from the descriptor this build happens
    to produce would pass both, and fail the moment a payload carrying it is
    read.
    """
    covered = {key.split(".")[0] for key in (*SPACE_KEYS, *OPERATOR_KEYS)}
    assert covered == set(DESCRIPTOR_KEYS)


def test_ver37_no_entry_is_in_both_lists() -> None:
    """The two lists are disjoint as written, before any descriptor is involved."""
    assert not set(SPACE_KEYS) & set(OPERATOR_KEYS)


# -- what a warm start accepts ------------------------------------------------


def test_ver37_a_neighbour_along_the_bias_axis_loads_and_records_the_difference(
    neighbour: Neighbour,
) -> None:
    """A different bias differs in ``solve_hash`` alone, and it is recorded.

    The bias axis is the one FR-24 exists to walk, and ``solve_hash`` is the
    digest of the whole solve provenance, so *every* axis moves it. Recording
    which keys differed rather than assuming none did is what makes the
    manifest able to say how a member was reached (section 5.3.2).
    """
    warm = _load(neighbour, _document(neighbour.mesh_path, bias_V=-0.05))
    assert warm.differing == ("solve_hash",)
    assert warm.summary() == {
        "status": "warm",
        "source": "neighbour",
        "differing_operator_keys": ["solve_hash"],
    }


def test_ver37_a_neighbour_along_the_salt_axis_loads_and_records_the_scales(
    neighbour: Neighbour,
) -> None:
    """A different concentration moves the NUM-09 scale set, which is permitted.

    ``model.scales`` is a function of ``concentration_M``, so gating it would
    refuse the salt axis outright — and the salt axis is stage 9 of NUM-18, the
    one rung of the ladder that already *is* a sweep. ``model.materials`` moves
    with it, the correction factors being evaluated at the new concentration.
    """
    warm = _load(neighbour, _document(neighbour.mesh_path, concentration_M=0.3))
    assert "model.scales" in warm.differing
    assert "solve_hash" in warm.differing
    assert set(warm.differing) <= set(OPERATOR_KEYS)


def test_ver37_the_loaded_state_carries_no_residual_and_no_stored_distance(
    neighbour: Neighbour,
) -> None:
    """A warm start is where Newton starts, not a solution (section 5.3.2).

    No residual: :func:`~nanopnp.solve.state.restore`'s exists so the NUM-25
    reaction flux can be taken from a reloaded solution, and taking a flux from
    a starting point would be reporting a number nobody solved for. And the
    stored wall-distance vector is not read — the operator being assembled is
    the *target's*, which solves its own field, and reading the neighbour's
    would make this run's answer a function of which member happened to be its
    parent.
    """
    import numpy as np

    document = _document(neighbour.mesh_path, bias_V=-0.05)
    warm = _load(neighbour, document)
    assert warm.solution.residual is None
    assert warm.solution.newton is None

    # Asserted by perturbation, because agreement proves nothing: the distance
    # solve is deterministic within one build, so a loader that *did* read the
    # stored vector would agree with a fresh solve to ten digits and this test
    # would pass while the guarantee did not hold.
    with np.load(neighbour.path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    moved = np.asarray(arrays[WALL_DISTANCE_ENTRY], dtype=np.float64).copy()
    moved[0] += 0.25
    arrays[WALL_DISTANCE_ENTRY] = moved
    tampered = neighbour.path.parent / "tampered.npz"
    with tampered.open("wb") as handle:
        np.savez_compressed(handle, **arrays)

    from_tampered = _load(neighbour, document, path=tampered)
    coefficients = np.asarray(
        from_tampered.solution.state.components[0].vec.FV().NumPy(), dtype=np.float64
    )
    untouched = np.asarray(warm.solution.state.components[0].vec.FV().NumPy(), dtype=np.float64)
    assert np.max(np.abs(coefficients - untouched)) == 0.0


# -- what a warm start refuses ------------------------------------------------


def _mutations() -> list[tuple[str, object]]:
    """Return one mutation per space key, each changing that key alone.

    Applied to the stored descriptor rather than to the case, because several of
    these are not reachable from a case file at all — ``ndof`` and the field
    record are derived — and what is under test is the *gate*, which compares
    two descriptors.
    """
    return [
        ("mesh_content_hash", "0" * 64),
        ("ndof", 1),
        ("fields", []),
        ("boundaries", {"potential": ["trans"]}),
        ("stabilisation", "reference"),
        ("wall_distance", {"sources": "wall", "max_distance_nm": 3.0, "ndof": 1}),
    ]


@pytest.mark.parametrize(("key", "value"), _mutations())
def test_ver37_a_differing_space_key_aborts_naming_it_and_both_values(
    neighbour: Neighbour, key: str, value: object
) -> None:
    """Each space key alone is enough to refuse the payload, and the message says which.

    Every key on purpose rather than a representative sample: a key the gate
    records and does not compare is a key that reads as protection and is not.
    """
    import numpy as np

    with np.load(neighbour.path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    descriptor = json.loads(str(arrays[DESCRIPTOR_ENTRY]))
    descriptor[key] = value
    arrays[DESCRIPTOR_ENTRY] = np.array(json.dumps(descriptor, sort_keys=True))
    path = neighbour.path.parent / f"mutated-{key}.npz"
    with path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)

    with pytest.raises(WarmStartError) as raised:
        _load(neighbour, _document(neighbour.mesh_path), path=path)
    message = str(raised.value)
    assert key in message
    assert "stored:" in message and "this run:" in message


@pytest.mark.parametrize("mode", ["supg", "reference"])
def test_num13_a_warm_start_across_two_stabilisation_modes_is_refused(
    neighbour: Neighbour, mode: str
) -> None:
    """A converged ``none`` state may not seed a stabilised run, or the reverse.

    Nothing about the two spaces differs -- same mesh, same fields, same orders,
    same degree count -- so the coefficient vector would load and Newton would
    converge. It would converge on an operator its starting point was never
    solved with, which is the one thing the stabilised mode exists to make
    comparable: NUM-14's mode is there so that two numbers can be attributed to
    the discretisation, and a comparison whose two sides were reached through
    each other is not one.

    The stored payload is a genuine converged ``none`` run; only the *target*
    case asks for a mode. Placing ``stabilisation`` in :data:`SPACE_KEYS` rather
    than :data:`OPERATOR_KEYS` is what makes this a refusal rather than a
    recorded difference -- deliberately against its class, since the mode changes
    the form and not the space (NUM-13, VER-37, FR-25).
    """
    document = _document(neighbour.mesh_path, stabilisation=mode)
    assert document.numerics.stabilisation == mode

    with pytest.raises(WarmStartError) as raised:
        _load(neighbour, document)
    message = str(raised.value)
    assert "stabilisation" in message
    # Both values, so the message says what crossing was attempted rather than
    # only that one was (QR-12).
    assert '"none"' in message
    assert f'"{mode}"' in message


def test_ver37_the_log_variable_branch_is_a_space_key() -> None:
    """NUM-02: the branch is in the space set, and no shape test would catch it.

    A log-variable model and a primitive one declare the same field names at the
    same order with the same degree count, so ``fields`` and ``ndof`` agree and
    the two mean different things by them. Asserted on the enumeration rather
    than on a solve, because this build has no log-variable ladder to solve.
    """
    assert "model.switches.log_variables" in SPACE_KEYS
    assert "model.switches.log_variables" not in OPERATOR_KEYS


def test_ver37_a_descriptor_this_version_cannot_gate_is_refused(neighbour: Neighbour) -> None:
    """A payload recording one fewer key is not one this version can gate.

    Skipping the missing key would make the gate weaker the older the file is,
    which is the opposite of what a gate is for.
    """
    import numpy as np

    with np.load(neighbour.path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    descriptor = json.loads(str(arrays[DESCRIPTOR_ENTRY]))
    del descriptor["stabilisation"]
    arrays[DESCRIPTOR_ENTRY] = np.array(json.dumps(descriptor, sort_keys=True))
    path = neighbour.path.parent / "short.npz"
    with path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)

    with pytest.raises(WarmStartError, match="cannot gate"):
        _load(neighbour, _document(neighbour.mesh_path), path=path)


def test_ver37_a_superseded_payload_schema_is_refused_by_schema(neighbour: Neighbour) -> None:
    """A ``nanopnp/solution/v1`` artefact is refused before its bytes are opened.

    ``v1`` wrote the backend's native ``state.gfu``, which this module cannot
    open at all, and "the file is not a payload of the version I read" is a
    better diagnostic than whatever NumPy says about its first bytes. The check
    is on the *artefact*, which is what a sweep resolves from the store.
    """
    stale = Artefact(
        schema="nanopnp/solution/v1",
        parameters={},
        payload={STATE_KEY: neighbour.path},
    )
    with pytest.raises(WarmStartError, match="nanopnp/solution/v1"):
        warm_start_payload(stale)

    empty = Artefact(schema=SOLUTION_SCHEMA, parameters={})
    with pytest.raises(WarmStartError, match="carries no 'state' payload"):
        warm_start_payload(empty)

    good = Artefact(schema=SOLUTION_SCHEMA, parameters={}, payload={STATE_KEY: neighbour.path})
    assert warm_start_payload(good) == neighbour.path

"""VER-37 (Tier 1): the descriptor partition, and what a warm start may ignore."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from nanopnp.charge.stage import ResolvedFields
from nanopnp.io.artefact import SOLUTION_SCHEMA, Artefact
from nanopnp.io.case import CaseDocument
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.pipeline.case import loads_case, resolve
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

CASE = """
schema: nanopnp/case/v0.5
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
  elements: {{phi: P2, c: P2, u: {velocity_element}, p: P1}}
outputs: [current]
"""


@dataclass
class Neighbour:
    document: CaseDocument
    path: Path
    mesh_path: Path


def _document(mesh_path: Path, **overrides: object) -> CaseDocument:
    settings: dict[str, object] = {
        "mesh_path": mesh_path,
        "concentration_M": 0.1,
        "bias_V": 0.02,
        "ground": "cis",
        "stabilisation": "none",
        "velocity_element": "P2",
    }
    settings.update(overrides)
    return loads_case(CASE.format(**settings))


@pytest.fixture(scope="module")
def neighbour(tmp_path_factory: pytest.TempPathFactory) -> Neighbour:
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
    import numpy as np

    with np.load(neighbour.path, allow_pickle=False) as archive:
        record: dict[str, Any] = json.loads(str(archive[DESCRIPTOR_ENTRY]))
    return record


def _load(neighbour: Neighbour, document: CaseDocument, *, path: Path | None = None) -> WarmStart:
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
    leaves = descriptor_leaves(_stored_descriptor(neighbour))
    for key in (*SPACE_KEYS, *OPERATOR_KEYS):
        assert any(covering_key(leaf, (key,)) is not None for leaf in leaves), (
            f"{key!r} is in the partition but names nothing in the descriptor a solve "
            "produces; it is a path left behind by a rename"
        )


def test_ver37_the_partition_covers_the_descriptor_keys_it_claims_to() -> None:
    covered = {key.split(".")[0] for key in (*SPACE_KEYS, *OPERATOR_KEYS)}
    assert covered == set(DESCRIPTOR_KEYS)


def test_ver37_no_entry_is_in_both_lists() -> None:
    assert not set(SPACE_KEYS) & set(OPERATOR_KEYS)


# -- what a warm start accepts ------------------------------------------------


# FR-24
def test_ver37_a_neighbour_along_the_bias_axis_loads_and_records_the_difference(
    neighbour: Neighbour,
) -> None:
    warm = _load(neighbour, _document(neighbour.mesh_path, bias_V=-0.05))
    assert warm.differing == ("solve_hash",)
    assert warm.summary() == {
        "status": "warm",
        "source": "neighbour",
        "differing_operator_keys": ["solve_hash"],
    }


# NUM-09, NUM-18
def test_ver37_a_neighbour_along_the_salt_axis_loads_and_records_the_scales(
    neighbour: Neighbour,
) -> None:
    warm = _load(neighbour, _document(neighbour.mesh_path, concentration_M=0.3))
    assert "model.scales" in warm.differing
    assert "solve_hash" in warm.differing
    assert set(warm.differing) <= set(OPERATOR_KEYS)


# NUM-25
def test_ver37_the_loaded_state_carries_no_residual_and_no_stored_distance(
    neighbour: Neighbour,
) -> None:
    import numpy as np

    document = _document(neighbour.mesh_path, bias_V=-0.05)
    warm = _load(neighbour, document)
    assert warm.solution.residual is None
    assert warm.solution.newton is None

    # Perturbed, not compared: the distance solve is deterministic within one build.
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


# NUM-14, VER-37, FR-25
@pytest.mark.parametrize("mode", ["supg", "reference"])
def test_num13_a_warm_start_across_two_stabilisation_modes_is_refused(
    neighbour: Neighbour, mode: str
) -> None:
    document = _document(neighbour.mesh_path, stabilisation=mode)
    assert document.numerics.stabilisation == mode

    with pytest.raises(WarmStartError) as raised:
        _load(neighbour, document)
    message = str(raised.value)
    assert "stabilisation" in message
    assert '"none"' in message
    assert f'"{mode}"' in message


# NUM-03
def test_val01_a_warm_start_across_an_element_order_is_refused(neighbour: Neighbour) -> None:
    document = _document(neighbour.mesh_path, velocity_element="P3")
    assert document.numerics.elements.u == "P3"
    assert _stored_descriptor(neighbour)["model"]["elements"]["velocity"] == 2
    assert "model.elements" in SPACE_KEYS
    assert "fields" in SPACE_KEYS

    with pytest.raises(WarmStartError) as raised:
        _load(neighbour, document)
    message = str(raised.value)
    assert "a different fields" in message
    assert '"name": "velocity"' in message
    assert '"order": 2' in message and '"order": 3' in message


# NUM-02
def test_ver37_the_log_variable_branch_is_a_space_key() -> None:
    assert "model.switches.log_variables" in SPACE_KEYS
    assert "model.switches.log_variables" not in OPERATOR_KEYS


def test_ver37_a_descriptor_this_version_cannot_gate_is_refused(neighbour: Neighbour) -> None:
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


def test_ver37_a_reworded_stabilisation_note_loads_and_is_recorded(neighbour: Neighbour) -> None:
    import numpy as np

    with np.load(neighbour.path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    descriptor = json.loads(str(arrays[DESCRIPTOR_ENTRY]))
    provenance = descriptor["model"]["stabilisation_provenance"]
    provenance["note"] = f"{provenance['note']}, reworded"
    arrays[DESCRIPTOR_ENTRY] = np.array(json.dumps(descriptor, sort_keys=True))
    path = neighbour.path.parent / "reworded-note.npz"
    with path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)

    warm = _load(neighbour, _document(neighbour.mesh_path), path=path)
    assert warm.differing == ("model.stabilisation_provenance",)
    assert "model.stabilisation_provenance" in OPERATOR_KEYS
    assert "model.stabilisation_provenance" not in SPACE_KEYS
    assert {"stabilisation", "model.stabilisation", "model.stabilisation_parameters"} <= set(
        SPACE_KEYS
    )


def test_ver37_every_registered_stabilisation_mode_records_mode_and_terms() -> None:
    from nanopnp.physics.stabilisation import create, registered_stabilisations

    for name in registered_stabilisations():
        mode = create(name)
        provenance = mode.provenance
        assert provenance["mode"] == name
        assert provenance["terms"] == ",".join(mode.terms)

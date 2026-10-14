"""VER-59 (with VER-53): with both WP30 keys at zero, no run key moves."""

from __future__ import annotations

import hashlib
import platform
import sys
from pathlib import Path

import pytest

from nanopnp.core.hashing import content_hash
from nanopnp.geometry.profile import load_profile
from nanopnp.io.artefact import CHARGE_GRID_SCHEMA, StageInputs
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import run_case
from nanopnp.solve.stage import SolveStage

# Stage keys on bbca737 (D16), stage 7 at v1.
KEYS = {
    "region": "bb447f8fc0c1d3fa9318cd82d239f78e43d3ff0d6e3a66d5960c5276cf0d704c",
    "mesh": "069b2cd9753f2dc4b149f71284851e9b9e01d9c0726ad82b0618d7e9f7457000",
    "charge": "79a2f7e5ff8a8743784e8f448711789a72dcbfeaed447c764730dabac9d42f7d",
    "solve": "6e3f8992206e2820221b04c4e2acd12405d4af11fa32b4932ca30c14e8c0b210",
}

# Keys with stage 7 at nanopnp/fields/v2: WP32 D15.
KEYS_V2 = {
    **KEYS,
    "charge": "3810c50e598c543d147a8bd8a804a68d7875c30ec00dfe94d5575f4cc79792dc",
    "solve": "b1370ee6183a4bdebd8697f9dc41846fd5bf8c89d51e246495b498033726806a",
}

# Keys under repo-wide v0.5 schemas: REV-71.
KEYS_V05 = {
    "region": "85d3b34627c4a56b38640ffa6222ec8e53838090cab296a4d596b02cac68b7e2",
    "mesh": "89551d4667c54f0d0c648b4c0e7caed46c3aa4c3e3994b9180366a2252d45517",
    "charge": "474b5b376e231d0f18d0e57e321c5fdb096f92f9a122f9c80b0e3f33e53e30a8",
    "solve": "80e2ee0ec96e63671bb02613fadacc5e565d51bf2a41aa729bfa8dc54f7797dc",
}

PROFILE_SCHEMA_V1 = "nanopnp/profile/v1"

REGION_SCHEMA_V1 = "nanopnp/region/v1"

MESH_ARTEFACT_SCHEMA_V1 = "nanopnp/mesh/v1"

PROTONATION_SCHEMA_V1 = "nanopnp/protonation/v1"

CHARGE_GRID_SCHEMA_V1 = "nanopnp/charge-grid/v1"

FIELDS_SCHEMA_V1 = "nanopnp/fields/v1"

MATERIALS_SCHEMA_V1 = "nanopnp/materials/v1"

CORRECTIONS_SHA256_V1 = "50058ebfa4715c50ac668f40a812e1df56197e9ba972446cf990cb9fd87d48bf"

SOLUTION_SCHEMA_V2 = "nanopnp/solution/v2"

RECORD_SHA256 = "b88bd7712339d83d97a3e691a9c3da9b4fa76d8b1946e190d8af6bdea8341db0"

RECORD_SHA256_WITHOUT_AREAS = "066f20c1ca309da9407fee16cb20c5611b1dd84715e7c820d4f031f6e42ed86e"

RECORD_SHA256_V1 = "03da655ef254808e3403034ac9dd188335edc2f9630edb6565d967528c8583d7"

RECORD_SHA256_WITHOUT_AREAS_V1 = "b41037c3587b2c398b7eb95900b39b620c55156b9a09d17f76ed6d65ca718463"

# Face areas recorded on bbca737.
FACE_AREAS_NM2 = {
    "electrolyte": 1336.3471929717593,
    "membrane": 71.36950114364842,
    "protein": 6.0,
}

ATOMS: tuple[tuple[str, float, float, float, float, float], ...] = (
    # name, x, y, z (Å), charge (e), radius (Å): inside the parallelogram, whose
    # section at height z (nm) is r in [3.5 + z/2, 4.5 + z/2]; they sum to -1 e.
    ("N", 30.0, 0.0, -20.0, -0.5, 1.85),
    ("CA", 0.0, 40.0, 0.0, -0.5, 2.275),
    ("C", -35.355, 35.355, 20.0, 0.25, 2.0),
    ("O", 24.75, -24.75, -10.0, -0.25, 1.7),
    ("CB", -45.0, 0.0, 10.0, 0.5, 2.175),
    ("CG", 0.0, -52.5, 25.0, -0.5, 2.175),
)

CASE = """\
schema: nanopnp/case/v0.5
name: wp30-golden
inputs:
  profile: {{path: {profile}}}
  pqr: {{path: {pqr}, format: pqr}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
    steric:       {{model: none}}
boundary_conditions: {{bias_V: 0.0, ground: cis}}
physics:
  model: pnp
  flow: false
  variable_density: false
  inertia: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics: {{continuation: none, mesh: {{size_scale: 5.0}}}}
{charge}outputs: [current]
"""


def write_golden_case(directory: Path, profile: Path, *, charge: str = "") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    lines = [
        f"ATOM  {serial:5d} {name:<4} GLU A  18    {x:8.3f}{y:8.3f}{z:8.3f} {q:7.4f} {r:6.4f}"
        for serial, (name, x, y, z, q, r) in enumerate(ATOMS, start=1)
    ]
    pqr = directory / "atoms.pqr"
    # Stage 7 keys a supplied PQR on its bytes, so it is written with LF on every
    # platform: Windows would otherwise write CRLF and move the charge key.
    pqr.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    case = directory / "golden.case.yaml"
    case.write_text(CASE.format(profile=profile, pqr=pqr, charge=charge), encoding="utf-8")
    return case


def _without_areas(text: str) -> bytes:
    kept = [line for line in text.splitlines(keepends=True) if "face_areas_nm2" not in line]
    return "".join(kept).encode("utf-8")


def _recording_platform() -> bool:
    return sys.platform == "linux" and platform.machine() == "x86_64"


@pytest.mark.parametrize(
    "charge",
    ["", "charge: {exclusion_offset_nm: 0.0, dielectric_transition_nm: 0.0}\n"],
    ids=["absent", "explicit-zero"],
)
def test_ver59_with_both_keys_at_zero_every_key_and_the_record_are_unchanged(
    tmp_path: Path, parallelogram_profile: Path, charge: str
) -> None:
    case = write_golden_case(tmp_path / "case", parallelogram_profile, charge=charge)
    store = Store(tmp_path / "store")
    # The solve's inputs without the solve: a walk runs its target's inputs alone
    # (WP38 D11), so the charge and the materials are walked to in turn.
    artefacts = {}
    for upto in ("charge", "materials"):
        result = run_case(case, store=store, workspace=tmp_path / "work", upto=upto)
        artefacts.update(result.artefacts)
    solve = SolveStage().key(
        StageInputs(resolved=resolve(load_case(case)), upstream=dict(artefacts))
    )
    found = {name: artefacts[name].hash for name in ("region", "mesh", "charge")}
    found["solve"] = solve.hash
    assert found == KEYS_V05

    # Under the v1 strings, the bbca737 literals: the schemas are all that moved.
    # Each digest is recomputed as ``Artefact.hash`` takes it, checked on v0.5 first.
    region = artefacts["region"]
    mesh = artefacts["mesh"]
    materials = artefacts["materials"]
    charge = artefacts["charge"]
    grid = store.get(CHARGE_GRID_SCHEMA, charge.inputs["charge_grid"])
    assert grid is not None
    for artefact in (region, mesh, materials, grid, charge, solve):
        assert content_hash(artefact.schema, artefact.parameters, artefact.inputs) == artefact.hash
    assert solve.inputs["charge"] == charge.hash

    resolved = resolve(load_case(case))
    assert resolved.profile is not None and resolved.profile.path is not None
    prof = load_profile(resolved.profile.path)
    dump_v1 = {**prof.model_dump(by_alias=True, mode="json"), "schema": PROFILE_SCHEMA_V1}
    prof_v1 = content_hash(PROFILE_SCHEMA_V1, dump_v1)
    region_v1 = content_hash(REGION_SCHEMA_V1, region.parameters, {"profile": prof_v1})
    mesh_v1 = content_hash(MESH_ARTEFACT_SCHEMA_V1, mesh.parameters, {"region": region_v1})

    prot = artefacts["protonation"]
    prot_v1 = content_hash(PROTONATION_SCHEMA_V1, prot.parameters, prot.inputs)
    grid_v1 = content_hash(CHARGE_GRID_SCHEMA_V1, grid.parameters, {"protonation": prot_v1})
    charge_v1 = content_hash(
        FIELDS_SCHEMA_V1,
        charge.parameters,
        {**charge.inputs, "mesh": mesh_v1, "protonation": prot_v1, "charge_grid": grid_v1},
    )
    materials_v1 = content_hash(
        MATERIALS_SCHEMA_V1, materials.parameters, {"corrections": CORRECTIONS_SHA256_V1}
    )
    # At bbca737 (WP30), pnp accepted and recorded variable_density: true, inertia: true;
    # WP42 carries them as false (D5, D10), and its key gained `algorithm_revision` and the
    # newton record's `field_floor_ratio` (REV-71). Restoring the bbca737 record recovers it.
    params_bbca = {
        **{k: v for k, v in solve.parameters.items() if k != "algorithm_revision"},
        "newton": {k: v for k, v in solve.parameters["newton"].items() if k != "field_floor_ratio"},
        "model_options": {
            **solve.parameters["model_options"],
            "variable_density": True,
            "inertia": True,
        },
    }
    solve_v1 = content_hash(
        SOLUTION_SCHEMA_V2,
        params_bbca,
        {"mesh": mesh_v1, "materials": materials_v1, "charge": charge_v1},
    )
    reconstructed = {
        "region": region_v1,
        "mesh": mesh_v1,
        "charge": charge_v1,
        "solve": solve_v1,
    }
    assert reconstructed == KEYS

    record = Path(artefacts["region"].payload["region"])
    text = record.read_text(encoding="utf-8")
    assert hashlib.sha256(_without_areas(text)).hexdigest() == RECORD_SHA256_WITHOUT_AREAS
    assert "exclusion" not in text
    areas = artefacts["region"].summary["face_areas_nm2"]
    assert areas == pytest.approx(FACE_AREAS_NM2, rel=1e-12)
    if _recording_platform():
        assert hashlib.sha256(record.read_bytes()).hexdigest() == RECORD_SHA256
        text_v1 = text.replace("schema: nanopnp/region/v0.5", "schema: nanopnp/region/v1")
        assert hashlib.sha256(_without_areas(text_v1)).hexdigest() == RECORD_SHA256_WITHOUT_AREAS_V1
        assert hashlib.sha256(text_v1.encode("utf-8")).hexdigest() == RECORD_SHA256_V1

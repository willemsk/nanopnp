"""VER-59's first clause: with both WP30 keys at 0, nothing a run is keyed on moves (WP30 D16).

The case is VER-53's coarse synthetic region, the parallelogram body of
``tests/conftest.py`` in a 30 nm reservoir, made a producer case by an
``inputs.pqr`` of six atoms inside the body, so that stage 7 runs and has a key.
It is walked through stage 8 and stage 10 is keyed without solving.

The literals below were recorded on ``bbca737``, the WP30 plan's commit, before
any of WP30's code existed. Every key is a hash of parameters and upstream keys,
never of a computed field, so it is the same on every platform, given the
same input bytes: the PQR, keyed on its bytes, is therefore written with LF. The region
record's bytes are not quite: its face areas are OCC's own integrals, which may
differ in their last bits between platforms. The record is therefore compared
byte for byte with its ``face_areas_nm2`` line taken out, and the areas to 1e-12.
On the platform the literals were recorded on, the whole file is compared too.

WP32 moved stage 7's schema to ``nanopnp/fields/v2`` (D15, the author's decision)
and its lattice's to ``nanopnp/charge-grid/v2``, which moves the stage-7 key and,
through it, the stage-10 key. Both are compared at v2, and also recomputed under
the ``v1`` strings, where they must equal the ``bbca737`` literals: the schema
strings are then shown to be the only thing that moved, so the clause still
compares against what WP30 found.
"""

from __future__ import annotations

import hashlib
import platform
import sys
from pathlib import Path

import pytest

from nanopnp.core.hashing import content_hash
from nanopnp.io.artefact import CHARGE_GRID_SCHEMA, StageInputs
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import run_case
from nanopnp.solve.stage import SolveStage

KEYS = {
    "region": "bb447f8fc0c1d3fa9318cd82d239f78e43d3ff0d6e3a66d5960c5276cf0d704c",
    "mesh": "069b2cd9753f2dc4b149f71284851e9b9e01d9c0726ad82b0618d7e9f7457000",
    "charge": "79a2f7e5ff8a8743784e8f448711789a72dcbfeaed447c764730dabac9d42f7d",
    "solve": "6e3f8992206e2820221b04c4e2acd12405d4af11fa32b4932ca30c14e8c0b210",
}
"""The stage-5, stage-6, stage-7 and stage-10 keys on ``bbca737`` (D16), stage 7 at ``v1``."""

KEYS_V2 = {
    **KEYS,
    "charge": "3810c50e598c543d147a8bd8a804a68d7875c30ec00dfe94d5575f4cc79792dc",
    "solve": "ee0900fc50ce0796f42f2305c920e637eaab75b02e3e2b2a78f763eaefe273bc",
}
"""The same keys with stage 7 at ``nanopnp/fields/v2`` (WP32 D15); region and mesh unchanged."""

FIELDS_SCHEMA_V1 = "nanopnp/fields/v1"
"""The stage-7 schema ``KEYS`` was recorded under."""

CHARGE_GRID_SCHEMA_V1 = "nanopnp/charge-grid/v1"
"""The lattice's schema then; its key is one of stage 7's inputs."""

RECORD_SHA256 = "03da655ef254808e3403034ac9dd188335edc2f9630edb6565d967528c8583d7"
"""``region.yaml``'s digest on ``bbca737``, Linux x86_64, CPython 3.12."""

RECORD_SHA256_WITHOUT_AREAS = "b41037c3587b2c398b7eb95900b39b620c55156b9a09d17f76ed6d65ca718463"
"""The same file's digest with its ``face_areas_nm2`` line removed."""

FACE_AREAS_NM2 = {
    "electrolyte": 1336.3471929717593,
    "membrane": 71.36950114364842,
    "protein": 6.0,
}
"""The record's face areas on ``bbca737``."""

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
schema: nanopnp/case/v2
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
physics: {{model: pnp, flow: false, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{continuation: none, mesh: {{size_scale: 5.0}}}}
{charge}outputs: [current]
"""


def write_golden_case(directory: Path, profile: Path, *, charge: str = "") -> Path:
    """Write the D16 case and its PQR into ``directory`` and return the case.

    ``profile`` is the session's parallelogram profile (``tests/conftest.py``).
    ``charge`` is an optional ``charge:`` block, ending in a newline, for the
    callers that set the WP30 keys explicitly.
    """
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
    """Return the record's text with its ``face_areas_nm2`` line removed."""
    kept = [line for line in text.splitlines(keepends=True) if "face_areas_nm2" not in line]
    return "".join(kept).encode("utf-8")


def _recording_platform() -> bool:
    """Whether this is the platform the whole-file digest was recorded on."""
    return sys.platform == "linux" and platform.machine() == "x86_64"


@pytest.mark.parametrize(
    "charge",
    ["", "charge: {exclusion_offset_nm: 0.0, dielectric_transition_nm: 0.0}\n"],
    ids=["absent", "explicit-zero"],
)
def test_ver59_with_both_keys_at_zero_every_key_and_the_record_are_unchanged(
    tmp_path: Path, parallelogram_profile: Path, charge: str
) -> None:
    """The region, mesh, fields and solve keys, and the record's bytes, equal ``bbca737``'s."""
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
    assert found == KEYS_V2

    # Under the v1 strings, the bbca737 literals: the schemas are all that moved.
    # Each digest is recomputed as ``Artefact.hash`` takes it, checked on v2 first.
    charge = artefacts["charge"]
    grid = store.get(CHARGE_GRID_SCHEMA, charge.inputs["charge_grid"])
    assert grid is not None
    for artefact in (grid, charge, solve):
        assert content_hash(artefact.schema, artefact.parameters, artefact.inputs) == artefact.hash
    assert solve.inputs["charge"] == charge.hash
    grid_v1 = content_hash(CHARGE_GRID_SCHEMA_V1, grid.parameters, grid.inputs)
    charge_v1 = content_hash(
        FIELDS_SCHEMA_V1, charge.parameters, {**charge.inputs, "charge_grid": grid_v1}
    )
    solve_v1 = content_hash(solve.schema, solve.parameters, {**solve.inputs, "charge": charge_v1})
    assert {**found, "charge": charge_v1, "solve": solve_v1} == KEYS

    record = Path(artefacts["region"].payload["region"])
    text = record.read_text(encoding="utf-8")
    assert hashlib.sha256(_without_areas(text)).hexdigest() == RECORD_SHA256_WITHOUT_AREAS
    assert "exclusion" not in text
    areas = artefacts["region"].summary["face_areas_nm2"]
    assert areas == pytest.approx(FACE_AREAS_NM2, rel=1e-12)
    if _recording_platform():
        assert hashlib.sha256(record.read_bytes()).hexdigest() == RECORD_SHA256

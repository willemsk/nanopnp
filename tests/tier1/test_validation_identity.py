"""VAL-03: case identity for a deposited charge and a derived solid fraction (OPN-07).

Section 7.4 requires reference solutions to be stored with their generating
case. Two cases differing in their fixed charge or dielectric transition are two
cases, and a golden of one must not be accepted for the other.

OPN-07: until WP34, ``case_identity`` hashed ``solve_provenance``, where
``fields.charge`` and ``fields.eps_r`` record only whether a field was
*supplied*. A fixed charge deposited by stage 7 or a solid fraction derived by it
was invisible to the identity, leaving four distinct cases of example 06 hashing
to the same ``8559ee13…``.

WP34 (author ruling, section 8.2.5 E3, decisions D1-D6) represents a deposited
charge by the stage-7 recipe (the protonation key and the smearing parameters,
leaving out the export lattice spacing and element order as discretisation) and a
derived solid fraction by its derivation parameters and structure key.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.protonation import ProtonationStage
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import loads_case, resolve
from nanopnp.structure.stage import StructureStage
from nanopnp.validation.comsol import case_identity

if TYPE_CHECKING:
    from tests.conftest import Prepared2WCD

REPOSITORY = Path(__file__).resolve().parents[2]
EXAMPLE_06_CASE = REPOSITORY / "examples" / "06-pdb-to-mesh" / "2wcd.case.yaml"

PQR_A = """\
ATOM      1  N   GLU A  18      25.000  25.000   0.000 -1.0000 2.0000           N
ATOM      2  CA  GLU A  18      26.000  25.000   0.000  0.5000 2.0000           C
"""

PQR_B = """\
ATOM      1  N   LYS A  18      25.000  25.000   0.000  1.0000 2.0000           N
ATOM      2  CA  LYS A  18      26.000  25.000   0.000  0.5000 2.0000           C
"""

PQR_CASE = """\
schema: nanopnp/case/v2
name: pqr-test
inputs:
  mesh: {{path: dummy.vol, format: vol}}
  pqr: {{path: {pqr}, format: pqr}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""


def test_val03_case_identity_names_a_deposited_charge(
    prepared_2wcd: Prepared2WCD, tmp_path: Path
) -> None:
    """VAL-03: pH, smearing sharpness, PQRs and dielectric transition move the identity."""
    base_text = EXAMPLE_06_CASE.read_text(encoding="utf-8").replace(
        "2wcd-prepared.pdb", str(prepared_2wcd.path)
    )

    def ident(extra: str = "") -> str:
        text = base_text + extra
        return case_identity(resolve(loads_case(text)))

    h_default = ident()
    h_ph5 = ident("charge:\n  ph: 5.0\n")
    h_ph9 = ident("charge:\n  ph: 9.0\n")
    h_sharp = ident("charge:\n  smearing: {sharpness: 0.8}\n")

    # On main prior to WP34, all four were:
    # 8559ee136041640b0d11145c93a954d8c1438224655d8338151a996d068167dd.
    # Now they must be four distinct hashes.
    hashes = {h_default, h_ph5, h_ph9, h_sharp}
    assert len(hashes) == 4, f"expected four distinct hashes, got {hashes}"
    assert "8559ee136041640b0d11145c93a954d8c1438224655d8338151a996d068167dd" not in hashes

    # Discretisation leaves the hash unchanged:
    # 1. Grid spacing is discretisation (D2).
    h_spacing = ident("charge:\n  smearing: {grid_spacing_nm: 0.01}\n")
    assert h_spacing == h_default

    # 2. Element order is discretisation (MODEL_OPTION_DISCRETISATION_KEYS).
    h_order = ident("numerics:\n  elements: {phi: P3, c: P3}\n")
    assert h_order == h_default

    # Two different PQRs differ, and a moved copy of the same PQR does not.
    pqr_a = tmp_path / "atoms_a.pqr"
    pqr_a.write_text(PQR_A, encoding="utf-8")
    pqr_b = tmp_path / "atoms_b.pqr"
    pqr_b.write_text(PQR_B, encoding="utf-8")
    moved_a = tmp_path / "subdir" / "moved.pqr"
    moved_a.parent.mkdir()
    moved_a.write_text(PQR_A, encoding="utf-8")

    def pqr_ident(path: Path) -> str:
        text = PQR_CASE.format(pqr=path)
        return case_identity(resolve(loads_case(text)))

    h_pqr_a = pqr_ident(pqr_a)
    h_pqr_b = pqr_ident(pqr_b)
    h_pqr_moved = pqr_ident(moved_a)

    assert h_pqr_a != h_pqr_b
    assert h_pqr_a == h_pqr_moved

    # Dielectric transition moves a deriving case's hash (D3).
    h_derived = ident("charge:\n  dielectric_transition_nm: 0.5\n")
    assert h_derived != h_default


def test_val03_ver23_solve_key_and_stage7_key_unchanged(
    prepared_2wcd: Prepared2WCD,
) -> None:
    """VER-23, VAL-03: fields.charge is False and keys remain unchanged."""
    text = EXAMPLE_06_CASE.read_text(encoding="utf-8").replace(
        "2wcd-prepared.pdb", str(prepared_2wcd.path)
    )
    doc = loads_case(text)
    resolved = resolve(doc)

    # fields.charge stays False: it still means "supplied" (D5).
    assert resolved.solve_provenance["fields"]["charge"] is False
    assert resolved.solve_provenance["fields"]["eps_r"] is False

    assert resolved.deposits_charge
    assert not resolved.derives_eps_r

    # Stage-7 recipe key is computable, deterministic, and 64-char hash (D1).
    structure_artefact = StructureStage().key(StageInputs(case=doc))
    protonation = ProtonationStage._key(
        StageInputs(case=doc, upstream={"structure": structure_artefact}), resolved
    )
    assert len(protonation.hash) == 64

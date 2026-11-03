"""The two-atom charged tube: the case the workbench's fixture states and the tests walk."""

from __future__ import annotations

import json
from pathlib import Path

from nanopnp.io.artefact import CASE_SCHEMA

__all__ = [
    "CHARGED_TUBE_ATOMS",
    "CHARGED_TUBE_RADIUS_A",
    "CHARGED_TUBE_SECOND_FRAME_E",
    "write_charged_tube",
    "write_dielectric_tube",
    "write_parallelogram_profile",
]


def write_parallelogram_profile(path: Path, *, citation: str = "tests/conftest.py") -> Path:
    """Write the four-vertex profile of the fixture tube and return its path."""
    import numpy as np

    from nanopnp.geometry.profile import (
        PROFILE_SCHEMA,
        PoreProfile,
        ProfileProvenance,
        min_feature_size,
        min_vertex_spacing,
        signed_area,
        write_profile,
    )

    points = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
    array = np.asarray(points, dtype=np.float64)
    profile = PoreProfile(
        schema=PROFILE_SCHEMA,
        name="parallelogram",
        provenance=ProfileProvenance(
            source="test",
            citation=citation,
            sha256="0" * 64,
            vertex_count=len(points),
            min_vertex_spacing_nm=min_vertex_spacing(array),
            min_feature_size_nm=min_feature_size(array),
            signed_area_nm2=signed_area(array),
        ),
        vertices=points,
    )
    return write_profile(profile, path)


CHARGED_TUBE_ATOMS: tuple[tuple[str, float, float, float, float], ...] = (
    ("NZ", 32.5, 0.0, -15.0, 1.0),
    ("OE1", 0.0, 47.5, 15.0, -2.0),
)

CHARGED_TUBE_RADIUS_A = 1.5

CHARGED_TUBE_SECOND_FRAME_E: tuple[float, float] = (1.0, -3.0)


# A JSON string is a YAML flow scalar, so a folder with a space, a comma or a brace in its name
# (the workbench writes this case under the user's temporary folder) still parses as one path.
def _quoted(path: Path) -> str:
    return json.dumps(str(path))


# size_scale 5, not the 20 of the uncharged case: at 20 the deployed field's worst plane fails the
# 1e-3 quadrature gate
# (knowledge/04-clya-geometry-and-charge/13-tier-3-test-evidence-the-charged-tube.md).
def write_charged_tube(
    directory: Path, *, frames: int = 1, size_scale: float = 5.0, charge_block: str | None = None
) -> Path:
    """Write a two-atom charged tube, as a case file in ``directory``, and return the case."""
    directory.mkdir(parents=True, exist_ok=True)
    profile = write_parallelogram_profile(directory / "profile.yaml")
    charges = [tuple(atom[4] for atom in CHARGED_TUBE_ATOMS), CHARGED_TUBE_SECOND_FRAME_E]
    lines: list[str] = []
    for frame in range(frames):
        if frames > 1:
            lines.append(f"MODEL     {frame + 1:4d}")
        for serial, ((name, x, y, z, _), charge) in enumerate(
            zip(CHARGED_TUBE_ATOMS, charges[frame], strict=True), start=1
        ):
            lines.append(
                f"ATOM  {serial:5d} {name:<4} GLU A  18    {x:8.3f}{y:8.3f}{z:8.3f}"
                f" {charge:7.4f} {CHARGED_TUBE_RADIUS_A:6.4f}"
            )
        if frames > 1:
            lines.append("ENDMDL")
    pqr = directory / "atoms.pqr"
    pqr.write_text("\n".join(lines) + "\n", encoding="utf-8")
    case = directory / "case.yaml"
    case.write_text(
        f"""schema: {CASE_SCHEMA}
name: charged-tube
inputs:
  profile: {{path: {_quoted(profile)}}}
  pqr: {{path: {_quoted(pqr)}, format: pqr}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: {size_scale}}}}}
"""
        + ("" if charge_block is None else f"charge: {charge_block}\n"),
        encoding="utf-8",
    )
    return case


def write_dielectric_tube(directory: Path) -> Path:
    """Write the fixture tube with a derived dielectric and no charge input, as a case file."""
    case = write_charged_tube(directory)
    (directory / "atoms.pqr").unlink()
    lines = [line for line in case.read_text(encoding="utf-8").splitlines() if "pqr:" not in line]
    text = "\n".join(lines).replace("name: charged-tube", "name: dielectric-tube")
    case.write_text(text + "\ncharge: {dielectric_transition_nm: 0.15}\n", encoding="utf-8")
    return case

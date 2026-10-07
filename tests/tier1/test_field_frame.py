"""FR-27, IF-05 (WP41 D1) — a supplied field is in the model frame, and says so.

Beside a case that generates its mesh, stage 5 moves the profile by
``z <- z - geometry.membrane.centre_z_nm``, so the mesh is in the model frame; a
supplied ``inputs.charge`` or ``inputs.eps_r`` is applied at the mesh's coordinates
without a shift. Stage 7's export declares the frame it was written in, and a field
declaring another frame than the case's is refused rather than applied off by the
difference (REV-06; the section 5.3.1 NOTE on ``inputs.charge``, ``inputs.eps_r``).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from nanopnp.io.case import SuppliedArtefact

FORMS = {
    "charge": {
        "quantity": "areal_charge_density",
        "units": "C/m^2",
        "form": {
            "name": "gaussian_ring",
            "parameters": {
                "centre_r_nm": 2.6,
                "centre_z_nm": 0.0,
                "width_nm": 0.4,
                "charge_e": -6.0,
            },
            "origin_nm": [0.0, -4.0],
            "spacing_nm": [0.05, 0.05],
            "shape": [101, 161],
        },
    },
    "eps_r": {
        "quantity": "solid_fraction",
        "units": "1",
        "form": {
            "name": "uniform",
            "parameters": {"value": 0.5},
            "origin_nm": [0.0, -4.0],
            "spacing_nm": [0.05, 0.05],
            "shape": [101, 161],
        },
    },
}


def _document(tmp_path: Path, key: str, declared: float | None) -> Path:
    """Write a field document for ``inputs.<key>``, declaring ``declared`` if given."""
    header: dict[str, object] = {
        "schema": "nanopnp/field/v1",
        "name": f"frame-probe-{key}",
        "provenance": {"source": "analytic"},
        **FORMS[key],
    }
    if declared is not None:
        header["model_frame_centre_z_nm"] = declared
    path = tmp_path / f"{key}.field.yaml"
    path.write_text(yaml.safe_dump(header, sort_keys=False), encoding="utf-8")
    return path


def _resolved(key: str, path: Path, *, centre_z_nm: float, generates_mesh: bool) -> object:
    """Return the four attributes of a resolved case that reading a field consults."""
    supplied = SuppliedArtefact(path=path, format="field1")
    return SimpleNamespace(
        charge=supplied if key == "charge" else None,
        eps_r=supplied if key == "eps_r" else None,
        generates_mesh=generates_mesh,
        membrane=SimpleNamespace(centre_z_nm=centre_z_nm),
    )


@pytest.mark.xfail(strict=True, reason="planned: WP41 D1")
def test_fr27_a_field_document_declares_its_model_frame(tmp_path: Path) -> None:
    """The header key is optional, a finite length in nm, and absent means undeclared."""
    from nanopnp.charge.fields import load_document

    assert load_document(_document(tmp_path, "charge", 2.5)).model_frame_centre_z_nm == 2.5
    assert load_document(_document(tmp_path, "eps_r", None)).model_frame_centre_z_nm is None


@pytest.mark.xfail(strict=True, reason="planned: WP41 D1")
@pytest.mark.parametrize("key", ["charge", "eps_r"])
def test_fr27_a_field_declaring_another_frame_than_a_generated_mesh_is_refused(
    tmp_path: Path, key: str
) -> None:
    """Declared 0 nm beside ``centre_z_nm = 2`` is refused, naming both and the offset."""
    from nanopnp.charge.fields import FieldDocumentError
    from nanopnp.charge.stage import read_fields

    path = _document(tmp_path, key, 0.0)
    with pytest.raises(FieldDocumentError) as raised:
        read_fields(_resolved(key, path, centre_z_nm=2.0, generates_mesh=True))  # type: ignore[arg-type]
    assert str(raised.value) == (
        f"inputs.{key} declares model_frame_centre_z_nm 0 nm and geometry.membrane.centre_z_nm "
        "is 2 nm: the field was written in another model frame than the mesh stage 5 "
        "generates, so every feature would sit +2 nm along z from where it was written "
        "(section 5.3.1 NOTE on inputs.charge, inputs.eps_r); export the field from this "
        "case, or correct the declaration"
    )


@pytest.mark.xfail(strict=True, reason="planned: WP41 D1")
@pytest.mark.parametrize("key", ["charge", "eps_r"])
def test_fr27_a_matching_undeclared_or_supplied_mesh_frame_is_read(
    tmp_path: Path, key: str
) -> None:
    """Each case that reads: the frames agree; nothing is declared; the mesh is supplied."""
    from nanopnp.charge.stage import read_fields

    for declared, generates_mesh in ((2.0, True), (None, True), (0.0, False)):
        path = _document(tmp_path, key, declared)
        fields = read_fields(
            _resolved(key, path, centre_z_nm=2.0, generates_mesh=generates_mesh)  # type: ignore[arg-type]
        )
        read = fields.charge if key == "charge" else fields.eps_r
        assert read is not None
        assert read.document.model_frame_centre_z_nm == declared


@pytest.mark.xfail(strict=True, reason="planned: WP41 D1")
def test_fr27_stage_7_declares_the_frame_its_lattice_was_exported_in(tmp_path: Path) -> None:
    """The export writes the shift its atoms were moved by, which a re-read checks."""
    import numpy as np

    from nanopnp.charge.fields import load_document
    from nanopnp.charge.stage import write_field_document
    from nanopnp.density.grid import RadialGrid

    grid = RadialGrid.from_axes(
        np.linspace(0.0, 1.0, 11), np.linspace(-1.0, 1.0, 21), np.zeros((21, 11))
    )
    atoms = SimpleNamespace(count=1, frames=1, shift_z_nm=1.5, q_net_e=lambda: 0.0)
    lattice = SimpleNamespace(grid=grid, atoms=atoms, spacing_nm=0.1)
    data = tmp_path / "charge.npz"
    data.write_bytes(b"probe")
    path = write_field_document(lattice, data, tmp_path / "charge.field.yaml")  # type: ignore[arg-type]
    assert load_document(path).model_frame_centre_z_nm == 1.5

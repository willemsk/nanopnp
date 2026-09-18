"""The golden archive's refusals and its round trip (VAL-03, NUM-24, QR-12).

Every test here is about something that would otherwise produce a finite,
plausible, wrong number.

A manifest missing its unit, its evaluation boundary or its sign reference is
refused rather than defaulted, because ``.knowledge/09`` section F records the
evaluation boundary as NOT IN REPORT: only the author knows it, and a build that
guessed would be guessing on every nightly run thereafter.

A ``mol/L`` declaration is refused rather than scaled, because a silent factor of
1000 presents as a 99.9 % discrepancy — a physics failure that is a units
failure.

A ``trans``-referenced current is flipped *and the flip is recorded*, because a
silent sign convention is how a rectification ratio comes out reciprocal
(section 6.7 NOTE).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.io.case import CaseValidationError
from nanopnp.validation.comsol import (
    ARCHIVE_MANIFEST_NAME,
    GOLDEN_SCHEMA,
    MANIFEST_NAME,
    GoldenError,
    GoldenManifest,
    GoldenQuantities,
    export_golden,
    field_unit,
    ingest_golden,
    load_golden,
    loads_manifest,
    table_name,
    write_comsol_table,
)
from nanopnp.validation.probe import PROBE_SCHEMA, ProbeDocument, loads_probe

PROBE_TEXT = (
    f"schema: {PROBE_SCHEMA}\nname: fixture\nmargin_nm: 0.05\npatches:\n"
    "  - {name: near, r_nm: [0.0, 1.0], z_nm: [0.0, 2.0], n_r: 3, n_z: 5}\n"
    "  - {name: far, r_nm: [2.0, 4.0], z_nm: [3.0, 6.0], n_r: 4, n_z: 7}\n"
)
"""Two small non-square patches: 15 + 28 = 43 probe points."""


@pytest.fixture
def probe() -> ProbeDocument:
    """Return the fixture probe document."""
    return loads_probe(PROBE_TEXT)


def manifest_document(probe: ProbeDocument, **overrides: object) -> dict[str, object]:
    """Return a complete, valid manifest mapping, with ``overrides`` applied."""
    document: dict[str, object] = {
        "schema": GOLDEN_SCHEMA,
        "case": "fixture-0.5M-plus50mV",
        "case_hash": "a" * 64,
        "probe": probe.name,
        "probe_hash": probe.hash,
        "refinement": "published",
        "source": "comsol",
        "comsol_version": "COMSOL 5.4 (build 5.4.0.388)",
        "model_file": "npgrid_clya_v8_NaCl_report.mph",
        "export_date": "2026-09-18",
        "fields": {
            "potential": {"expression": "V", "unit": "V"},
            "c_Na+": {"expression": "cpos", "unit": "mol/m^3"},
        },
        "current_boundary": "the cis reservoir cap, boundary 196",
        "current_sign_reference": "cis",
        "quantities": {"bias_V": 0.05, "current_A": 1.25e-9, "conductance_S": 2.5e-8},
    }
    document.update(overrides)
    return document


def write_tables(directory: Path, probe: ProbeDocument, fields: dict[str, float]) -> None:
    """Write one ``%Grid`` table per field per patch, each a known ramp.

    The value is ``scale * (10 r + z)``, which is asymmetric under a transpose
    everywhere off ``r = z`` — the shape the reader's row-order contract is about.
    """
    import numpy as np

    from nanopnp.density.grid import RadialGrid

    for patch in probe.patches:
        r_axis, z_axis = patch.axes_nm()
        r_grid, z_grid = np.meshgrid(r_axis, z_axis, indexing="xy")
        for field, scale in fields.items():
            values = scale * (10.0 * r_grid + z_grid)
            grid = RadialGrid.from_axes(r_axis, z_axis, values)
            write_comsol_table(grid, directory / table_name(field, patch.name))


def _yaml(document: dict[str, object]) -> str:
    """Return a manifest mapping as YAML text."""
    import yaml

    return yaml.safe_dump(document, sort_keys=False)


# -- the declaration refusals -------------------------------------------------


@pytest.mark.parametrize(
    "missing", ["current_boundary", "current_sign_reference", "comsol_version", "model_file"]
)
def test_val03_golden_refuses_undeclared_units_and_sign(probe: ProbeDocument, missing: str) -> None:
    """A manifest leaving a required declaration out is refused, naming it.

    Structural, so exact. Each of these is something only the author knows, and
    a default would be a guess repeated silently on every nightly run.
    """
    document = manifest_document(probe)
    del document[missing]
    with pytest.raises(CaseValidationError) as raised:
        loads_manifest(_yaml(document))
    assert missing in str(raised.value)


@pytest.mark.parametrize(
    "blank", ["current_boundary", "comsol_version", "model_file", "export_date", "case_hash"]
)
def test_val03_golden_refuses_a_blank_declaration(probe: ProbeDocument, blank: str) -> None:
    """An empty string is as useless as an absent key, and is refused the same way.

    ``str`` accepts ``""``; section 7.4 wants the generating model *named*.
    """
    document = manifest_document(probe, **{blank: "   "})
    with pytest.raises(CaseValidationError) as raised:
        loads_manifest(_yaml(document))
    assert blank in str(raised.value)


def test_val03_golden_refuses_a_missing_unit(probe: ProbeDocument) -> None:
    """A field declaring an expression and no unit is refused naming the field."""
    document = manifest_document(probe)
    document["fields"] = {"potential": {"expression": "V"}}
    with pytest.raises(CaseValidationError) as raised:
        loads_manifest(_yaml(document))
    message = str(raised.value)
    assert "unit" in message
    assert "potential" in message


def test_val03_golden_refuses_mol_per_litre_rather_than_scaling_it(
    probe: ProbeDocument,
) -> None:
    """The unit is refused, not converted, and the message says what it would have cost."""
    document = manifest_document(probe)
    document["fields"] = {
        "potential": {"expression": "V", "unit": "V"},
        "c_Na+": {"expression": "cpos", "unit": "mol/L"},
    }
    with pytest.raises(CaseValidationError) as raised:
        loads_manifest(_yaml(document))
    message = str(raised.value)
    assert "mol/L" in message
    assert "factor 1000" in message
    assert "refused rather than converted" in message


def test_val03_golden_refuses_a_field_nothing_samples(probe: ProbeDocument) -> None:
    """A field the comparison does not know would export a table nobody reads."""
    document = manifest_document(probe)
    document["fields"] = {
        "potential": {"expression": "V", "unit": "V"},
        "temperature": {"expression": "T", "unit": "K"},
    }
    with pytest.raises(CaseValidationError, match="temperature"):
        loads_manifest(_yaml(document))


def test_val03_golden_refuses_a_manifest_without_the_potential(probe: ProbeDocument) -> None:
    """The potential is the one field every configuration of the model carries."""
    document = manifest_document(probe)
    document["fields"] = {"c_Na+": {"expression": "cpos", "unit": "mol/m^3"}}
    with pytest.raises(CaseValidationError, match="potential"):
        loads_manifest(_yaml(document))


def test_val03_field_unit_covers_every_exported_field() -> None:
    """The five field kinds of section 7.4 have one declared unit each."""
    assert field_unit("potential") == "V"
    assert field_unit("pressure") == "Pa"
    assert field_unit("velocity_r") == field_unit("velocity_z") == "m/s"
    assert field_unit("c_Cl-") == "mol/m^3"
    with pytest.raises(GoldenError, match="not a field"):
        field_unit("c_")


# -- the hash refusals --------------------------------------------------------


def test_val03_golden_refuses_a_probe_hash_that_is_not_the_grid(
    probe: ProbeDocument, tmp_path: Path
) -> None:
    """An export onto another set of points is refused before a norm is taken.

    Every array keeps its shape, so nothing downstream would notice: the samples
    would simply be in the wrong places.
    """
    (tmp_path / MANIFEST_NAME).write_text(
        _yaml(manifest_document(probe, probe_hash="b" * 64)), encoding="utf-8"
    )
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1.0})
    with pytest.raises(GoldenError, match="probe_hash"):
        ingest_golden(tmp_path, probe=probe)


def test_val03_golden_refuses_a_case_hash_that_is_not_the_run(
    probe: ProbeDocument, tmp_path: Path
) -> None:
    """A golden answering another case is the most expensive kind of wrong answer."""
    (tmp_path / MANIFEST_NAME).write_text(_yaml(manifest_document(probe)), encoding="utf-8")
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1.0})
    ingest_golden(tmp_path, probe=probe)
    golden = load_golden(tmp_path)
    golden.check_case("a" * 64)
    with pytest.raises(GoldenError, match="different case"):
        golden.check_case("c" * 64)


def test_val03_golden_refuses_a_table_on_the_wrong_axes(
    probe: ProbeDocument, tmp_path: Path
) -> None:
    """A table exported on another grid is refused naming the patch and the miss."""
    import numpy as np

    from nanopnp.density.grid import RadialGrid

    (tmp_path / MANIFEST_NAME).write_text(_yaml(manifest_document(probe)), encoding="utf-8")
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1.0})
    patch = probe.patches[0]
    r_axis, z_axis = patch.axes_nm()
    shifted = RadialGrid.from_axes(
        r_axis + 0.5, z_axis, np.zeros((patch.n_z, patch.n_r), dtype=np.float64)
    )
    write_comsol_table(shifted, tmp_path / table_name("potential", patch.name))
    with pytest.raises(GoldenError, match="r axis differs"):
        ingest_golden(tmp_path, probe=probe)


def test_val03_golden_refuses_an_absent_table(probe: ProbeDocument, tmp_path: Path) -> None:
    """A declared field with no table names the file the contract expects."""
    (tmp_path / MANIFEST_NAME).write_text(_yaml(manifest_document(probe)), encoding="utf-8")
    write_tables(tmp_path, probe, {"potential": 1.0})
    with pytest.raises(GoldenError, match=table_name("c_Na\\+", "near")):
        ingest_golden(tmp_path, probe=probe)


# -- the round trip -----------------------------------------------------------


def test_val03_grid_table_round_trips_through_npz(probe: ProbeDocument, tmp_path: Path) -> None:
    """A ``%Grid`` table written and re-ingested reproduces its array bit-for-bit.

    Bitwise, not to a tolerance: the writer emits ``%.17g``, which round-trips
    ``float64`` exactly by definition, so any difference at all is a defect in
    the transport format rather than a rounding budget. The hash follows: a
    golden re-ingested from the same tables keys the same archive.
    """
    import numpy as np

    (tmp_path / MANIFEST_NAME).write_text(_yaml(manifest_document(probe)), encoding="utf-8")
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1e3})
    ingest_golden(tmp_path, probe=probe)
    golden = load_golden(tmp_path)

    expected = []
    for patch in probe.patches:
        points = patch.points_nm()
        expected.append(10.0 * points[:, 0] + points[:, 1])
    reference = np.concatenate(expected)

    assert golden.values["potential"].shape == (probe.count,)
    assert np.array_equal(golden.values["potential"], reference)
    assert np.array_equal(golden.values["c_Na+"], 1e3 * reference)

    again = ingest_golden(tmp_path, probe=probe, destination=tmp_path / "second")
    assert load_golden(again).hash == golden.hash


def test_val03_golden_refuses_a_transposed_square_table_by_construction(
    tmp_path: Path,
) -> None:
    """The transpose guard is the patch shape, and it fires at ingest.

    A square patch cannot exist, so a transposed table always mismatches a
    declared ``(n_z, n_r)``. This asserts the consequence the guard buys: the
    ingest names the shapes rather than reading the wrong field.
    """
    import numpy as np

    from nanopnp.density.grid import RadialGrid

    probe = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: fixture\npatches:\n"
        "  - {name: only, r_nm: [0.0, 1.0], z_nm: [0.0, 2.0], n_r: 3, n_z: 5}\n"
    )
    (tmp_path / MANIFEST_NAME).write_text(_yaml(manifest_document(probe)), encoding="utf-8")
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1.0})
    patch = probe.patches[0]
    r_axis, z_axis = patch.axes_nm()
    transposed = RadialGrid.from_axes(
        z_axis, r_axis, np.zeros((patch.n_r, patch.n_z), dtype=np.float64)
    )
    write_comsol_table(transposed, tmp_path / table_name("potential", patch.name))
    with pytest.raises(GoldenError, match=r"axis differs|table and patch"):
        ingest_golden(tmp_path, probe=probe)


# -- the sign contract --------------------------------------------------------


def test_val03_trans_referenced_current_is_flipped_and_recorded(
    probe: ProbeDocument, tmp_path: Path
) -> None:
    """A ``trans``-referenced golden comes back in section 6.7's sign, and says so.

    The current, the conductance and the electro-osmotic flow rate are the same
    ``psi`` integral with the same outward normal, so all three flip. The
    transport number is a ratio of two quantities that flip together and must
    **not**: negating it is the bug this asserts against.
    """
    quantities = {
        "bias_V": 0.05,
        "current_A": 1.25e-9,
        "currents_A": {"Na+": 8.0e-10, "Cl-": 4.5e-10},
        "transport_number": 0.64,
        "conductance_S": 2.5e-8,
        "eof_m3_s": 3.0e-18,
    }
    (tmp_path / MANIFEST_NAME).write_text(
        _yaml(manifest_document(probe, current_sign_reference="trans", quantities=quantities)),
        encoding="utf-8",
    )
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1.0})
    ingest_golden(tmp_path, probe=probe)
    golden = load_golden(tmp_path)

    assert golden.current_sign_flipped is True
    assert golden.quantities.current_A == pytest.approx(-1.25e-9)
    assert golden.quantities.currents_A == {"Na+": -8.0e-10, "Cl-": -4.5e-10}
    assert golden.quantities.conductance_S == pytest.approx(-2.5e-8)
    assert golden.quantities.eof_m3_s == pytest.approx(-3.0e-18)
    assert golden.quantities.transport_number == pytest.approx(0.64)
    assert golden.quantities.bias_V == pytest.approx(0.05)
    assert golden.summary()["current_sign_flipped"] is True


def test_val03_cis_referenced_current_is_left_alone(probe: ProbeDocument, tmp_path: Path) -> None:
    """Our own convention passes through untouched, and the report says nothing flipped."""
    (tmp_path / MANIFEST_NAME).write_text(_yaml(manifest_document(probe)), encoding="utf-8")
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1.0})
    ingest_golden(tmp_path, probe=probe)
    golden = load_golden(tmp_path)
    assert golden.current_sign_flipped is False
    assert golden.quantities.current_A == pytest.approx(1.25e-9)


# -- what a golden does not carry ---------------------------------------------


def test_val03_an_unexported_field_is_named_rather_than_skipped(
    probe: ProbeDocument, tmp_path: Path
) -> None:
    """A golden without ``pressure`` reports it unavailable; it does not vanish.

    Whether the reference model exports ``p`` at all is answered at export time,
    and a comparison that quietly covered one field fewer would answer it wrongly.
    """
    (tmp_path / MANIFEST_NAME).write_text(_yaml(manifest_document(probe)), encoding="utf-8")
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1.0})
    ingest_golden(tmp_path, probe=probe)
    golden = load_golden(tmp_path)
    assert golden.unavailable(["potential", "c_Na+", "pressure"]) == ("pressure",)
    with pytest.raises(GoldenError, match="carries no field 'pressure'"):
        golden.defined("pressure")


# -- the self-golden path -----------------------------------------------------


def test_val03_export_golden_refuses_to_relabel_a_self_golden_as_comsol(
    probe: ProbeDocument, tmp_path: Path
) -> None:
    """Only ``ingest_golden`` writes a ``source: comsol`` archive.

    One path that could write one from arrays in memory is one path by which a
    self-golden becomes evidence.
    """
    import numpy as np

    manifest = GoldenManifest.model_validate(manifest_document(probe))
    with pytest.raises(GoldenError, match="self-goldens"):
        export_golden({"potential": np.zeros(probe.count)}, manifest, tmp_path)


def test_val03_self_golden_is_written_with_its_source_recorded(
    probe: ProbeDocument, tmp_path: Path
) -> None:
    """A self-golden round-trips through the archive and keeps ``source: self``."""
    import numpy as np

    values = {"potential": np.linspace(-0.2, 0.2, probe.count)}
    manifest = GoldenManifest.model_validate(
        manifest_document(
            probe,
            source="self",
            comsol_version="nanopnp (self-golden, no COMSOL)",
            model_file="tests/tier1/test_comsol_golden.py",
            fields={"potential": {"expression": "phi_V", "unit": "V"}},
            quantities=GoldenQuantities(bias_V=0.05, current_A=1.0e-9).summary(),
        )
    )
    export_golden(values, manifest, tmp_path, tables=probe)
    golden = load_golden(tmp_path)
    assert golden.source == "self"
    assert np.array_equal(golden.values["potential"], values["potential"])
    assert (tmp_path / table_name("potential", probe.patches[0].name)).is_file()
    assert (tmp_path / ARCHIVE_MANIFEST_NAME).is_file()


def test_val03_an_archive_without_its_manifest_is_refused(
    probe: ProbeDocument, tmp_path: Path
) -> None:
    """Half a golden cannot state what it holds, so it is not read as a whole one."""
    (tmp_path / MANIFEST_NAME).write_text(_yaml(manifest_document(probe)), encoding="utf-8")
    write_tables(tmp_path, probe, {"potential": 1.0, "c_Na+": 1.0})
    ingest_golden(tmp_path, probe=probe)
    (tmp_path / ARCHIVE_MANIFEST_NAME).unlink()
    with pytest.raises(GoldenError, match="no golden manifest"):
        load_golden(tmp_path)

"""FR-16, FR-25: a correction file read by path keys stage 8 and the manifest by its content."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.core.paths import correction_file
from nanopnp.io.case import CaseValidationError


def _copy(folder: Path, name: str = "mine.yaml", *, edit: bool = False) -> Path:
    text = correction_file("willems2020_nacl").read_text(encoding="utf-8")
    if edit:
        text = text.replace("willems2020_nacl", "mine", 1) + "\n# edited\n"
    target = folder / name
    target.write_text(text, encoding="utf-8")
    return target


def _case(parameters: str) -> Case:
    return Case.cylinder(concentration_M=0.1, bias_V=0.05).with_(
        **{"electrolyte.parameters": parameters}
    )


def test_fr16_a_correction_file_by_path_keys_stage_8_and_the_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _copy(tmp_path, "first.yaml")
    second = tmp_path / "second.yaml"
    second.write_text(first.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    session = Session(tmp_path / "store", write=False)
    ran = session.run(_case(str(first)), upto="materials")
    edited = session.run(_case(str(second)), upto="materials")
    assert edited.artefacts["materials"].hash != ran.artefacts["materials"].hash
    files = ran.manifest.inputs["files"]
    assert files["electrolyte.parameters"]["path"] == str(first)
    assert files["electrolyte.parameters"]["sha256"]
    listed = [str(row["path"]) for row in ran.manifest.groups()["deviations"]["switches"]]
    assert "electrolyte.parameters" in listed
    # A relative path resolves beside the case file, whatever the working directory.
    (tmp_path / "case.yaml").write_text(_case("first.yaml").dumps(), encoding="utf-8")
    monkeypatch.chdir(tmp_path / "store")
    beside = session.run(Case.load(tmp_path / "case.yaml"), upto="materials")
    assert beside.manifest.inputs["files"]["electrolyte.parameters"]["path"] == str(first)
    assert beside.artefacts["materials"].hash == ran.artefacts["materials"].hash


def test_fr16_a_correction_file_that_is_not_there_is_refused_naming_the_key(
    tmp_path: Path,
) -> None:
    session = Session(tmp_path / "store", write=False)
    with pytest.raises(CaseValidationError, match=r"electrolyte\.parameters"):
        session.run(_case(str(tmp_path / "missing.yaml")), upto="materials")

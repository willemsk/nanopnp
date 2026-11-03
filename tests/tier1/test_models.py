"""A study that names model files resolves to its case written inline and records its overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from nanopnp.api.case import Case
from nanopnp.io.artefact import CaseArtefact
from nanopnp.io.case_paths import block_paths, case_fields, substitute
from nanopnp.io.models import MOLECULAR_SCHEMA, OWNERS, owner_of

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
QUICKSTART = EXAMPLES / "01-quickstart" / "quickstart.case.yaml"
CHARGED = EXAMPLES / "07-pdb-to-charged-run" / "2wcd.case.yaml"
CONTINUUM_SCHEMA = "nanopnp/continuum-model/v0.6"


def _leaves(mapping: dict[str, Any], path: str = "") -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    blocks = set(block_paths())
    for key, value in mapping.items():
        here = f"{path}.{key}" if path else key
        if isinstance(value, dict) and here in blocks:
            found.extend(_leaves(value, here))
        else:
            found.append((here, value))
    return found


def _put(target: dict[str, Any], path: str, value: object) -> None:
    *parents, last = path.split(".")
    for part in parents:
        target = target.setdefault(part, {})
    target[last] = value


def split_case(
    case: Path, directory: Path, *, models: tuple[str, ...] = ("molecular", "continuum")
):
    """Write ``case`` as model files by ownership and a study; return the study's path."""
    raw = yaml.safe_load(case.read_text(encoding="utf-8"))
    layers: dict[str, dict[str, Any]] = {"molecular": {}, "continuum": {}, "study": {}}
    for path, value in _leaves(raw):
        kind = owner_of(path)
        if kind not in models:
            kind = "study"
        if path == "structure.source.path":
            value = str(case.parent / value)
        _put(layers[kind], path, value)
    schemas = {"molecular": MOLECULAR_SCHEMA, "continuum": CONTINUUM_SCHEMA}
    for kind in models:
        if layers[kind]:
            (directory / f"{kind}.yaml").write_text(
                yaml.safe_dump({"schema": schemas[kind], "name": f"my-{kind}", **layers[kind]}),
                encoding="utf-8",
            )
    study = {
        **layers["study"],
        "models": {kind: f"{kind}.yaml" for kind in models if layers[kind]},
    }
    path = directory / "study.case.yaml"
    path.write_text(yaml.safe_dump(study, sort_keys=False), encoding="utf-8")
    return path


def test_fr39_every_case_leaf_has_one_owner() -> None:
    schema_paths = {reference.path for reference in case_fields()} | set(block_paths())
    for row in OWNERS:
        assert any(path == row or path.startswith(f"{row}.") for path in schema_paths), row
    for path in schema_paths:
        assert owner_of(path) in {"molecular", "continuum", "study"}
    assert owner_of("charge.ph") == "molecular"
    assert owner_of("charge.exclusion_offset_nm") == "continuum"
    assert owner_of("charge.smearing.sharpness") == "study"
    assert owner_of("numerics.mesh.maxh_nm") == "continuum"
    assert owner_of("numerics.nonlinear.rtol") == "study"
    assert owner_of("outputs") == "study"


@pytest.mark.parametrize("example", [QUICKSTART, CHARGED])
def test_fr39_a_study_resolves_to_its_case_written_inline(example: Path, tmp_path: Path) -> None:
    study = split_case(example, tmp_path)
    twin = Case.load(example)
    if example == CHARGED:
        twin = twin.with_({"structure.source.path": str(example.parent / "2wcd-prepared.pdb")})
    resolved = Case.load(study)
    assert resolved == twin.with_()
    assert CaseArtefact(resolved).hash == CaseArtefact(twin).hash
    assert resolved.overrides == {}
    assert "models" not in resolved.dumps()
    assert Case.loads(resolved.dumps(study=True)) == twin
    assert Case.loads(resolved.dumps(study=True)).overrides == {}


def test_fr39_a_study_keeps_only_the_keys_no_model_owns(tmp_path: Path) -> None:
    study = split_case(QUICKSTART, tmp_path)
    written = yaml.safe_load(study.read_text(encoding="utf-8"))
    assert set(written) == {"schema", "name", "models", "outputs", "numerics"}
    assert set(written["numerics"]) == {"continuation", "stabilisation"}
    continuum = yaml.safe_load((tmp_path / "continuum.yaml").read_text(encoding="utf-8"))
    assert {"geometry", "electrolyte", "boundary_conditions", "physics"} <= set(continuum)
    assert "outputs" not in continuum


def test_fr39_an_override_is_recorded_beside_the_model_value_and_survives_edits(
    tmp_path: Path,
) -> None:
    case = Case.load(split_case(QUICKSTART, tmp_path))
    longer = case.with_({"geometry.pore.radius_nm": 2.5})
    assert dict(longer.overrides) == {"geometry.pore.radius_nm": (2.0, 2.5)}
    assert dict(longer.with_(outputs=["current"]).overrides) == dict(longer.overrides)
    same = case.with_({"bias_V": 0.05})
    assert dict(same.overrides) == {}, "a value equal to the model's is no override"
    assert dict(case.with_({"bias_V": 0.1}).overrides) == {
        "boundary_conditions.bias_V": (0.05, 0.1)
    }
    assert Case.loads(longer.dumps(study=True)) == longer
    assert dict(Case.loads(longer.dumps(study=True)).overrides) == dict(longer.overrides)


def test_fr39_a_model_swap_resolves_the_study_again_under_its_overrides(tmp_path: Path) -> None:
    study = split_case(QUICKSTART, tmp_path)
    case = Case.load(study).with_({"geometry.pore.radius_nm": 2.5})
    other = yaml.safe_load((tmp_path / "continuum.yaml").read_text(encoding="utf-8"))
    other["name"] = "stronger"
    other["boundary_conditions"]["bias_V"] = 0.1
    (tmp_path / "stronger.yaml").write_text(yaml.safe_dump(other), encoding="utf-8")
    swapped = substitute(case, {"models.continuum": str(tmp_path / "stronger.yaml")})
    assert swapped.boundary_conditions.bias_V == 0.1
    assert swapped.geometry is not None and swapped.geometry.pore is not None
    assert swapped.geometry.pore.radius_nm == 2.5
    assert dict(swapped.overrides) == {"geometry.pore.radius_nm": (2.0, 2.5)}
    assert swapped.outputs == case.outputs
    other["name"] = "named-again"
    other["geometry"]["pore"]["radius_nm"] = 3.0
    (tmp_path / "wider.yaml").write_text(yaml.safe_dump(other), encoding="utf-8")
    both = case.with_({"models.continuum": "wider.yaml", "bias_V": 0.2})
    assert dict(both.overrides) == {
        "geometry.pore.radius_nm": (3.0, 2.5),
        "boundary_conditions.bias_V": (0.1, 0.2),
    }, "a relative model path reads beside the study, and the other edits apply after it"


def test_fr39_a_model_file_that_holds_a_key_it_does_not_own_is_refused(tmp_path: Path) -> None:
    study = split_case(QUICKSTART, tmp_path)
    model = yaml.safe_load((tmp_path / "continuum.yaml").read_text(encoding="utf-8"))
    model["outputs"] = ["current"]
    (tmp_path / "continuum.yaml").write_text(yaml.safe_dump(model), encoding="utf-8")
    with pytest.raises(ValueError, match=r"continuum\.yaml: outputs: belongs to the study"):
        Case.load(study)


def test_fr39_a_model_that_cannot_stand_alone_is_refused_naming_its_file(tmp_path: Path) -> None:
    study = split_case(QUICKSTART, tmp_path)
    model = yaml.safe_load((tmp_path / "continuum.yaml").read_text(encoding="utf-8"))
    del model["electrolyte"]["concentration_M"]
    (tmp_path / "continuum.yaml").write_text(yaml.safe_dump(model), encoding="utf-8")
    with pytest.raises(ValueError, match=r"electrolyte.concentration_M.*continuum\.yaml"):
        Case.load(study)


def test_fr39_a_plain_reader_refuses_a_case_that_names_models(tmp_path: Path) -> None:
    from nanopnp.io.case import read_case

    with pytest.raises(ValueError, match="names models"):
        read_case(split_case(QUICKSTART, tmp_path))

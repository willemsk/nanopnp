"""A study that names model files resolves to its case written inline and records its overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.api.sweep import plan_sweep
from nanopnp.core.hashing import file_hash
from nanopnp.io.artefact import CaseArtefact
from nanopnp.io.case_paths import block_paths, case_fields, substitute
from nanopnp.io.models import OWNERS, SCHEMAS, owner_of, read_case, read_case_text
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case
from nanopnp.sweep.plan import SweepPlanError, plan_from_document

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
QUICKSTART = EXAMPLES / "01-quickstart" / "quickstart.case.yaml"
CHARGED = EXAMPLES / "07-pdb-to-charged-run" / "2wcd.case.yaml"
PARAMETERS = Path(__file__).resolve().parents[2] / "data" / "corrections" / "willems2020_nacl.yaml"


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
    case: Path,
    directory: Path,
    *,
    models: tuple[str, ...] = ("molecular", "continuum", "physics"),
):
    """Write ``case`` as model files by ownership and a study; return the study's path."""
    raw = yaml.safe_load(case.read_text(encoding="utf-8"))
    layers: dict[str, dict[str, Any]] = {
        "molecular": {},
        "continuum": {},
        "physics": {},
        "study": {},
    }
    for path, value in _leaves(raw):
        kind = owner_of(path)
        if kind not in models:
            kind = "study"
        if path == "structure.source.path":
            value = str(case.parent / value)
        _put(layers[kind], path, value)
    for kind in models:
        if layers[kind]:
            (directory / f"{kind}.yaml").write_text(
                yaml.safe_dump({"schema": SCHEMAS[kind], "name": f"my-{kind}", **layers[kind]}),
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
        assert owner_of(path) in {"molecular", "continuum", "physics", "study"}
    assert owner_of("charge.ph") == "molecular"
    assert owner_of("charge.exclusion_offset_nm") == "continuum"
    assert owner_of("charge.smearing.sharpness") == "study"
    assert owner_of("numerics.mesh.maxh_nm") == "continuum"
    assert owner_of("numerics.nonlinear.rtol") == "study"
    assert owner_of("outputs") == "study"
    for path in (
        "electrolyte.concentration_M",
        "boundary_conditions.bias_V",
        "physics.flow",
        "numerics.elements.u",
        "numerics.stabilisation",
        "numerics.wall_distance.max_distance_nm",
    ):
        assert owner_of(path) == "physics", path
    assert owner_of("numerics.mesh.wall_for_concentration_M") == "continuum"
    assert owner_of("numerics.continuation") == "study"
    assert owner_of("numerics.linear.solver") == "study"


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
    assert set(written["numerics"]) == {"continuation"}
    continuum = yaml.safe_load((tmp_path / "continuum.yaml").read_text(encoding="utf-8"))
    assert {"geometry", "numerics"} <= set(continuum)
    assert set(continuum["numerics"]) == {"mesh"}
    physics = yaml.safe_load((tmp_path / "physics.yaml").read_text(encoding="utf-8"))
    assert {"electrolyte", "boundary_conditions", "physics", "numerics"} <= set(physics)
    assert set(physics["numerics"]) == {"stabilisation"}
    assert "outputs" not in continuum and "outputs" not in physics


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
    other = yaml.safe_load((tmp_path / "physics.yaml").read_text(encoding="utf-8"))
    other["name"] = "stronger"
    other["boundary_conditions"]["bias_V"] = 0.1
    (tmp_path / "stronger.yaml").write_text(yaml.safe_dump(other), encoding="utf-8")
    swapped = substitute(case, {"models.physics": str(tmp_path / "stronger.yaml")})
    assert swapped.boundary_conditions.bias_V == 0.1
    assert swapped.geometry is not None and swapped.geometry.pore is not None
    assert swapped.geometry.pore.radius_nm == 2.5
    assert dict(swapped.overrides) == {"geometry.pore.radius_nm": (2.0, 2.5)}
    assert swapped.outputs == case.outputs
    pore = yaml.safe_load((tmp_path / "continuum.yaml").read_text(encoding="utf-8"))
    pore["name"] = "wider"
    pore["geometry"]["pore"]["radius_nm"] = 3.0
    (tmp_path / "wider.yaml").write_text(yaml.safe_dump(pore), encoding="utf-8")
    both = swapped.with_({"models.continuum": "wider.yaml", "bias_V": 0.2})
    assert dict(both.overrides) == {
        "geometry.pore.radius_nm": (3.0, 2.5),
        "boundary_conditions.bias_V": (0.1, 0.2),
    }, "a relative model path reads beside the study, and the other edits apply after it"


def _rebuilt(session: Session, case: Case, upto: str = "mesh") -> set[str]:
    return {record.name for record in session.run(case, upto=upto).stages if not record.cached}


def test_fr39_a_study_reuses_every_stage_its_twin_built(tmp_path: Path) -> None:
    session = Session(Store(tmp_path / "store"), write=False)
    inline = session.run(Case.load(QUICKSTART), upto="mesh")
    study = session.run(Case.load(split_case(QUICKSTART, tmp_path)), upto="mesh")
    assert [record.name for record in study.stages] == [record.name for record in inline.stages]
    assert all(record.cached for record in study.stages)
    assert {name: a.hash for name, a in study.artefacts.items()} == {
        name: a.hash for name, a in inline.artefacts.items()
    }


def test_fr39_an_override_moves_only_the_stages_that_read_it(tmp_path: Path) -> None:
    session = Session(Store(tmp_path / "store"), write=False)
    case = Case.load(split_case(QUICKSTART, tmp_path))
    assert _rebuilt(session, case) == {"case", "region", "mesh"}
    wider = case.with_({"geometry.pore.radius_nm": 2.5})
    assert _rebuilt(session, wider) == {"case", "region", "mesh"}
    assert _rebuilt(session, wider.with_(outputs=["current"])) == {"case"}
    assert _rebuilt(session, case.with_({"bias_V": 0.1})) == {"case"}, "the bias reaches no mesh"
    assert _rebuilt(session, case.with_({"bias_V": 0.05})) == set(), "a value at the model's"


def test_fr39_a_run_records_its_model_files_and_overrides(tmp_path: Path) -> None:
    session = Session(Store(tmp_path / "store"), write=False)
    inline = session.run(Case.load(QUICKSTART), upto="mesh")
    assert "overrides" not in inline.manifest.inputs
    study_path = split_case(QUICKSTART, tmp_path)
    case = Case.load(study_path).with_({"bias_V": 0.1})
    result = session.run(case, upto="mesh")
    files = result.manifest.inputs["files"]
    assert files["models.continuum"]["sha256"] == file_hash(tmp_path / "continuum.yaml")
    assert files["models.physics"]["sha256"] == file_hash(tmp_path / "physics.yaml")
    assert result.manifest.inputs["overrides"] == {
        "boundary_conditions.bias_V": {"model": 0.05, "study": 0.1}
    }
    assert result.manifest.case_text == case.dumps()


def test_fr39_a_sweep_over_models_resolves_each_member(tmp_path: Path) -> None:
    study_path = split_case(QUICKSTART, tmp_path)
    case = Case.load(study_path).with_({"geometry.pore.radius_nm": 2.5})
    other = yaml.safe_load((tmp_path / "physics.yaml").read_text(encoding="utf-8"))
    other["name"] = "stronger"
    other["boundary_conditions"]["bias_V"] = 0.1
    (tmp_path / "stronger.yaml").write_text(yaml.safe_dump(other), encoding="utf-8")
    models = [str(tmp_path / "physics.yaml"), str(tmp_path / "stronger.yaml")]

    session = Session(Store(tmp_path / "store"), write=False)
    planned = plan_sweep(
        case, session=session, axis="models.physics", values=models, check_meshes=False
    )
    members = [planned.plan.case(point.index) for point in planned.plan.points]
    assert [member.boundary_conditions.bias_V for member in members] == [0.05, 0.1]
    assert all(
        member.models_record is not None
        and dict(member.models_record.overrides) == dict(case.overrides)
        for member in members
    )
    assert planned.plan.files.keys() >= set(models)

    (tmp_path / "base.case.yaml").write_text(case.dumps(study=True), encoding="utf-8")
    (tmp_path / "sweep.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "nanopnp/sweep/v0.5",
                "name": case.name,
                "base": "base.case.yaml",
                "axes": [{"name": "physics", "path": "models.physics", "values": models}],
            }
        ),
        encoding="utf-8",
    )
    from_file = plan_from_document(tmp_path / "sweep.yaml", check_meshes=False)
    assert [dict(point.assignments) for point in from_file.points] == [
        dict(point.assignments) for point in planned.plan.points
    ]
    assert from_file.files.keys() >= set(models)
    assert all(point.parent is None for point in from_file.points), "each model is its own root"

    with pytest.raises(SweepPlanError, match="not a file"):
        plan_from_document(
            _sweep_over(tmp_path, ["physics.yaml", "absent.yaml"]), check_meshes=False
        )


def _sweep_over(directory: Path, values: list[str]) -> Path:
    path = directory / "absent.sweep.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema": "nanopnp/sweep/v0.5",
                "name": "absent",
                "base": "base.case.yaml",
                "axes": [{"name": "physics", "path": "models.physics", "values": values}],
            }
        ),
        encoding="utf-8",
    )
    return path


def _exposed(case: Case) -> dict[str, dict[str, tuple[object, ...]]]:
    record = case.models_record
    assert record is not None
    return {
        file.kind: {
            value.name: (value.path, value.unit, value.low, value.high, value.default)
            for value in file.exposed
        }
        for file in record.files
    }


def test_fr39_a_model_exposes_its_kinds_list_unless_its_file_replaces_it(tmp_path: Path) -> None:
    study = split_case(QUICKSTART, tmp_path)
    case = Case.load(study)
    assert _exposed(case) == {
        "continuum": {"size_scale": ("numerics.mesh.size_scale", "dimensionless", 0.0, None, 1.0)},
        "physics": {
            "concentration": ("electrolyte.concentration_M", "molar", None, None, 0.1),
            "bias": ("boundary_conditions.bias_V", "volt", None, None, 0.05),
        },
    }
    physics = yaml.safe_load((tmp_path / "physics.yaml").read_text(encoding="utf-8"))
    physics["exposes"] = [
        {"name": "salt", "path": "electrolyte.concentration_M", "range": [0.05, 3.0]}
    ]
    (tmp_path / "physics.yaml").write_text(yaml.safe_dump(physics), encoding="utf-8")
    declared = Case.load(study)
    assert _exposed(declared)["physics"] == {
        "salt": ("electrolyte.concentration_M", "molar", 0.05, 3.0, 0.1)
    }
    assert CaseArtefact(declared).hash == CaseArtefact(case).hash, "exposes: keys nothing"
    assert declared.overrides == {}


def test_fr39_a_continuum_models_wall_follows_the_physics_salt_unless_pinned(
    tmp_path: Path,
) -> None:
    split_case(QUICKSTART, tmp_path)
    continuum = yaml.safe_load((tmp_path / "continuum.yaml").read_text(encoding="utf-8"))
    assert continuum["numerics"]["mesh"]["wall_h_nm"] == 0.35
    continuum["numerics"]["mesh"]["wall_h_nm"] = "auto"
    (tmp_path / "continuum.yaml").write_text(yaml.safe_dump(continuum), encoding="utf-8")
    physics = yaml.safe_load((tmp_path / "physics.yaml").read_text(encoding="utf-8"))
    salts: dict[float, str] = {}
    for molar in (0.1, 0.5, 3.0, 5.0):
        physics["name"] = f"salt-{molar}"
        physics["electrolyte"]["concentration_M"] = molar
        location = tmp_path / f"salt-{molar}.yaml"
        location.write_text(yaml.safe_dump(physics), encoding="utf-8")
        salts[molar] = str(location)
    case = Case.load(tmp_path / "study.case.yaml")

    def meshes(base: Case, *molars: float) -> int:
        session = Session(Store(tmp_path / "store"), write=False)
        values = [salts[molar] for molar in molars]
        planned = plan_sweep(
            base, session=session, axis="models.physics", values=values, check_meshes=False
        )
        return planned.forecast().builds["mesh"]

    assert meshes(case, 0.1, 0.5) == 1, "below the wall's threshold the salts share a mesh"
    assert meshes(case, 3.0, 5.0) == 2, "above it the wall size follows each salt"
    continuum["numerics"]["mesh"]["wall_for_concentration_M"] = 3.0
    (tmp_path / "continuum.yaml").write_text(yaml.safe_dump(continuum), encoding="utf-8")
    pinned = Case.load(tmp_path / "study.case.yaml")
    assert meshes(pinned, 3.0, 5.0) == 1, "a pinned continuum model keeps one wall size"


def _params(folder: Path) -> str:
    # A copy of the shipped parameters beside the case, named by a relative path.
    folder.mkdir(exist_ok=True)
    (folder / "params.yaml").write_bytes(PARAMETERS.read_bytes())
    return str((folder / "params.yaml").resolve())


def _quickstart(folder: Path, **extra: object) -> Path:
    raw = yaml.safe_load(QUICKSTART.read_text(encoding="utf-8"))
    raw["electrolyte"]["parameters"] = "params.yaml"
    raw["electrolyte"]["corrections"]["diffusivity"]["model"] = "params.yaml"
    raw = {"schema": raw.pop("schema"), "name": raw.pop("name"), **extra, **raw}
    path = folder / "case.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_fr25_every_edit_reads_a_relative_path_beside_its_case(tmp_path: Path) -> None:
    plain_folder = tmp_path / "plain"
    absolute = _params(plain_folder)
    plain = Case.load(_quickstart(plain_folder))
    assert plain.with_().electrolyte.parameters == absolute
    assert substitute(plain, {}).electrolyte.parameters == "params.yaml"

    named_folder = tmp_path / "variables"
    absolute = _params(named_folder)
    path = _quickstart(named_folder, variables={"v": {"value": 50, "unit": "mV"}})
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["boundary_conditions"]["bias_V"] = "v"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    named = Case.load(path).with_(outputs=["current"])
    assert named.electrolyte.parameters == absolute
    assert dict(named.expressions) == {"boundary_conditions.bias_V": "v"}

    study_folder = tmp_path / "study"
    study_folder.mkdir()
    absolute = _params(study_folder)
    study_path = split_case(QUICKSTART, study_folder)
    written = yaml.safe_load(study_path.read_text(encoding="utf-8"))
    written["electrolyte"] = {"corrections": {"diffusivity": {"model": "params.yaml"}}}
    study_path.write_text(yaml.safe_dump(written, sort_keys=False), encoding="utf-8")
    continuum = yaml.safe_load((study_folder / "continuum.yaml").read_text(encoding="utf-8"))
    continuum["name"] = "twin"
    (study_folder / "twin.yaml").write_text(yaml.safe_dump(continuum), encoding="utf-8")
    study = Case.load(study_path)
    assert study.electrolyte.corrections.diffusivity.model == "params.yaml"
    swapped = study.with_({"models.continuum": "twin.yaml"})
    assert swapped.electrolyte.corrections.diffusivity.model == absolute
    assert study.with_(bias_V=0.1).electrolyte.corrections.diffusivity.model == absolute


def test_fr39_every_case_reader_resolves_a_study_and_its_variables(tmp_path: Path) -> None:
    study = split_case(QUICKSTART, tmp_path)
    raw = yaml.safe_load(QUICKSTART.read_text(encoding="utf-8"))
    raw = {"schema": raw.pop("schema"), "name": raw.pop("name"), **raw}
    raw["variables"] = {"a": {"value": 1, "unit": "nm"}}
    raw["geometry"]["pore"]["radius_nm"] = "2*a"
    inline = tmp_path / "inline.case.yaml"
    inline.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    hashes = set()
    for path in (study, inline):
        text = path.read_text(encoding="utf-8")
        documents = [
            read_case(path),
            read_case_text(text, base=path.parent, source=str(path)),
            load_case(path),
        ]
        assert documents[1:] == documents[:-1]
        loaded = Case.load(path)
        assert loaded == read_case(path, model=Case)
        hashes |= {CaseArtefact(document).hash for document in (*documents, loaded)}
        records = [document.models_record for document in (*documents, loaded)]
        variables = [document.variables_record for document in (*documents, loaded)]
        if path == study:
            assert all(
                record is not None
                and record.paths
                == {
                    "continuum": str(tmp_path / "continuum.yaml"),
                    "physics": str(tmp_path / "physics.yaml"),
                }
                for record in records
            )
            assert all(variable is None for variable in variables)
        else:
            assert all(record is None for record in records)
            assert all(
                variable is not None
                and dict(variable.expressions) == {"geometry.pore.radius_nm": "2*a"}
                for variable in variables
            )
            assert loaded.geometry is not None and loaded.geometry.pore is not None
            assert loaded.geometry.pore.radius_nm == 2.0
    assert len(hashes) == 1, "a study, its variables and the case inline key alike"

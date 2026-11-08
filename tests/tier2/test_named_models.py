"""FR-39 (with VER-26): a study that overrides a named model rebuilds only the stages it moves."""

from __future__ import annotations

from pathlib import Path

import yaml

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.io.store import Store

QUICKSTART = Path(__file__).resolve().parents[2] / "examples/01-quickstart/quickstart.case.yaml"
PHYSICS_KEYS = ("electrolyte", "boundary_conditions", "physics")


def _study(directory: Path, *, bias_V: float = 0.05, name: str = "physics") -> Path:
    """Write the quick-start case as a continuum model, a physics model and a study."""
    raw = yaml.safe_load(QUICKSTART.read_text(encoding="utf-8"))
    pore = {"geometry": raw.pop("geometry"), "numerics": {"mesh": raw["numerics"].pop("mesh")}}
    physics = {key: raw.pop(key) for key in PHYSICS_KEYS}
    physics["boundary_conditions"]["bias_V"] = bias_V
    physics["numerics"] = {"stabilisation": raw["numerics"].pop("stabilisation")}
    (directory / "continuum.yaml").write_text(
        yaml.safe_dump(
            {"schema": "nanopnp/continuum-model/v0.6", "name": "quickstart-pore", **pore}
        ),
        encoding="utf-8",
    )
    (directory / f"{name}.yaml").write_text(
        yaml.safe_dump(
            {"schema": "nanopnp/physics-model/v0.6", "name": f"quickstart-{name}", **physics}
        ),
        encoding="utf-8",
    )
    study = {**raw, "models": {"continuum": "continuum.yaml", "physics": f"{name}.yaml"}}
    path = directory / "study.case.yaml"
    path.write_text(yaml.safe_dump(study, sort_keys=False), encoding="utf-8")
    return path


def _held(store: Store) -> set[str]:
    return {
        f"{path.parent.parent.name}/{path.name}"
        for path in (store.root / "artefacts").glob("*/*/*")
        if path.is_dir()
    }


def _computed(session: Session, case: Case) -> set[str]:
    return {record.name for record in session.run(case).stages if not record.cached}


def test_fr39_a_study_rebuilds_only_what_its_override_moves(tmp_path: Path) -> None:
    session = Session(Store(tmp_path / "store"), write=False)
    case = Case.load(_study(tmp_path))
    assert {"region", "mesh", "solve"} <= _computed(session, case), "the base study builds all"

    stronger = case.with_({"bias_V": 0.1})
    assert dict(stronger.overrides) == {"boundary_conditions.bias_V": (0.05, 0.1)}
    assert _computed(session, stronger) == {"case", "solve", "qoi", "report"}

    quieter = stronger.with_(outputs=["current"])
    assert "solve" not in _computed(session, quieter), "a changed output reaches no solve"

    # A sweep over the models reuses what the studies above built, region to solve.
    _study(tmp_path, bias_V=0.1, name="stronger")
    models = [str(tmp_path / "physics.yaml"), str(tmp_path / "stronger.yaml")]
    held = _held(session.store)
    swept = session.sweep(case, axis="models.physics", values=models, check_meshes=False)
    assert [row["cached"] for row in swept.rows] == [True, True]
    # A member is named for its point, so only the stages that hash the case's name are new.
    built = {entry.split("/")[0] for entry in _held(session.store) - held}
    assert {schema for schema in built if "sweep" not in schema} <= {
        "nanopnp-case-v0.6",
        "nanopnp-qoi-v0.5",
        "nanopnp-report-v0.5",
    }

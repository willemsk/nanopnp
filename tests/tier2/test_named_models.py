"""FR-39 (with VER-26): a study that overrides a named model rebuilds only the stages it moves."""

from __future__ import annotations

from pathlib import Path

import yaml

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.io.store import Store

QUICKSTART = Path(__file__).resolve().parents[2] / "examples/01-quickstart/quickstart.case.yaml"
CONTINUUM_KEYS = ("geometry", "electrolyte", "boundary_conditions", "physics")


def _study(directory: Path, *, bias_V: float = 0.05, name: str = "continuum") -> Path:
    """Write the quick-start case as a continuum model and a study that names it."""
    raw = yaml.safe_load(QUICKSTART.read_text(encoding="utf-8"))
    model = {key: raw.pop(key) for key in CONTINUUM_KEYS}
    model["boundary_conditions"]["bias_V"] = bias_V
    model["numerics"] = {"mesh": raw["numerics"].pop("mesh")}
    (directory / f"{name}.yaml").write_text(
        yaml.safe_dump(
            {"schema": "nanopnp/continuum-model/v0.6", "name": f"quickstart-{name}", **model}
        ),
        encoding="utf-8",
    )
    study = {**raw, "models": {"continuum": f"{name}.yaml"}}
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
    models = [str(tmp_path / "continuum.yaml"), str(tmp_path / "stronger.yaml")]
    held = _held(session.store)
    swept = session.sweep(case, axis="models.continuum", values=models, check_meshes=False)
    assert [row["cached"] for row in swept.rows] == [True, True]
    # A member is named for its point, so only the stages that hash the case's name are new.
    built = {entry.split("/")[0] for entry in _held(session.store) - held}
    assert {schema for schema in built if "sweep" not in schema} <= {
        "nanopnp-case-v0.6",
        "nanopnp-qoi-v0.5",
        "nanopnp-report-v0.5",
    }

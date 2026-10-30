"""NUM-17: the gates' SI concentration expressions are built once per solve, not per iterate."""

from __future__ import annotations

from pathlib import Path

import pytest

import nanopnp.physics.models as models
from nanopnp import Case, Session
from nanopnp.io.store import Store


def test_num17_gate_expressions_are_built_once_per_solve_and_evaluated_per_iterate(
    cylindrical_pore_case: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builds: list[tuple[str, ...]] = []
    solves: list[int] = []
    real_build = models.species_concentrations_SI
    real_newton = models.damped_newton

    def build(scales: object, concentrations: dict[str, object]) -> object:
        builds.append(tuple(concentrations))
        return real_build(scales, concentrations)  # type: ignore[arg-type]

    def newton(*arguments: object, **keywords: object) -> object:
        result = real_newton(*arguments, **keywords)  # type: ignore[arg-type]
        solves.append(result.iterations)  # type: ignore[attr-defined]
        return result

    monkeypatch.setattr(models, "species_concentrations_SI", build)
    monkeypatch.setattr(models, "damped_newton", newton)
    Session(Store(tmp_path / "store"), workspace=tmp_path / "work", write=False).run(
        Case.load(cylindrical_pore_case), upto="solve"
    )

    assert len(builds) == len(solves)
    assert sum(solves) > len(builds)

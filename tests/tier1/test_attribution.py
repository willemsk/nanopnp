"""The attribution ladder: the deltas, the verdict, and what the rungs may share."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.pipeline.case import load_case, resolve
from nanopnp.sweep.document import load_sweep
from nanopnp.sweep.plan import WARM_START_BARRIERS, build_plan
from nanopnp.validation.attribution import (
    IDENTITY_TOLERANCE,
    LADDER,
    RungOutcome,
    attribute,
)
from nanopnp.validation.compare import FieldComparison, QoIComparison
from nanopnp.validation.comsol import GOLDEN_SCHEMA, Golden, GoldenManifest, case_identity

LADDER_SWEEP = Path("docs/validation/comsol-ladder.sweep.yaml")
"""The checked-in ladder, planned rather than described."""

FROZEN_CASES = Path("docs/validation/cases")
"""The five frozen cases of section 7.4's NOTE."""

GOLDEN_HASH = "d" * 64
PROBE_HASH = "e" * 64
CASE_HASH = "f" * 64


def _golden(source: str = "comsol") -> Golden:
    import numpy as np

    manifest = GoldenManifest.model_validate(
        {
            "schema": GOLDEN_SCHEMA,
            "case": "fixture",
            "case_hash": CASE_HASH,
            "probe": "fixture",
            "probe_hash": PROBE_HASH,
            "refinement": "published",
            "source": source,
            "comsol_version": "COMSOL 5.4",
            "model_file": "npgrid_clya_v8_NaCl_report.mph",
            "export_date": "2026-09-18",
            "fields": {"potential": {"expression": "V", "unit": "V"}},
            "current_boundary": "the cis reservoir cap",
            "current_sign_reference": "cis",
            "quantities": {"bias_V": 0.05, "current_A": 1.0e-9},
        }
    )
    return Golden(
        manifest=manifest,
        values={"potential": np.zeros(4, dtype=np.float64)},
        quantities=manifest.quantities,
        current_sign_flipped=False,
        hash=GOLDEN_HASH,
    )


def _outcomes(
    field_errors: list[float],
    quantity_errors: list[float] | None = None,
    *,
    golden_hash: str = GOLDEN_HASH,
    points: int = 100,
) -> list[RungOutcome]:
    currents = [0.0, -4.1e-11, -8.1e-11, -9.4e-11]
    outcomes: list[RungOutcome] = []
    for index, rung in enumerate(LADDER):
        relative = None if quantity_errors is None else quantity_errors[index]
        outcomes.append(
            RungOutcome(
                rung=rung,
                golden_hash=golden_hash,
                probe_hash=PROBE_HASH,
                case_hash=CASE_HASH,
                fields=(
                    FieldComparison(
                        field="potential",
                        points=points,
                        rel_L2_r=field_errors[index],
                        rel_l2=2.0 * field_errors[index],
                        max_abs_rel=3.0 * field_errors[index],
                        max_at_nm=(1.5, -0.5),
                    ),
                ),
                quantities=()
                if relative is None
                else (
                    QoIComparison(name="current_A", ours=1.0e-9, golden=1.0e-9, relative=relative),
                ),
                stabilisation_currents_A={"Na+": currents[index]},
            )
        )
    return outcomes


@pytest.mark.parametrize(
    "errors",
    [
        [0.0731, 0.0402, 0.0455, 0.0121],
        [1.0e-3, 1.0e-3, 1.0e-3, 1.0e-3],
        [0.5, 0.25, 0.125, 0.0625],
        [1.0e-14, 0.9, 1.0e-14, 0.4],
    ],
)
def test_val01_ladder_identity_holds_on_synthetic_errors(errors: list[float]) -> None:
    report = attribute(_outcomes(errors), case="fixture", golden=_golden())
    entry = report.attribution("potential")

    assert entry.total == pytest.approx(errors[0])
    assert entry.transport == pytest.approx(errors[1] - errors[0])
    assert entry.flow == pytest.approx(errors[2] - errors[1])
    assert entry.pair == pytest.approx(errors[3] - errors[2])
    assert entry.residual == pytest.approx(errors[3])
    assert abs(entry.identity_residual()) <= IDENTITY_TOLERANCE

    report.check_identity()


def test_val04_reference_limited_verdict() -> None:
    errors = [0.0731, 0.0402, 0.0455, 0.0121]
    below = attribute(
        _outcomes(errors),
        case="fixture",
        golden=_golden(),
        reference_errors={"potential": 0.05},
    )
    assert below.attribution("potential").verdict() == "reference-limited"

    above = attribute(
        _outcomes(errors),
        case="fixture",
        golden=_golden(),
        reference_errors={"potential": 0.001},
    )
    assert above.attribution("potential").verdict() == "attributed"

    unbounded = attribute(_outcomes(errors), case="fixture", golden=_golden())
    entry = unbounded.attribution("potential")
    assert entry.verdict() == "reference-unbounded"
    assert entry.reference_error is None


def test_val04_the_verdict_is_strict_at_the_boundary() -> None:
    errors = [0.1, 0.1, 0.1, 0.02]
    report = attribute(
        _outcomes(errors), case="fixture", golden=_golden(), reference_errors={"potential": 0.02}
    )
    assert report.attribution("potential").verdict() == "attributed"


def _refinement(refinement: str, values: dict[str, object]) -> Golden:
    manifest = GoldenManifest.model_validate(
        {
            **_golden().manifest.model_dump(),
            "refinement": refinement,
            "fields": {
                "potential": {"expression": "V", "unit": "V"},
                "c_Na+": {"expression": "cpos", "unit": "mol/m^3"},
            },
        }
    )
    return Golden(
        manifest=manifest,
        values=values,  # type: ignore[arg-type]
        quantities=manifest.quantities,
        current_sign_flipped=False,
        hash=GOLDEN_HASH,
    )


def test_val04_delta_ref_is_taken_over_the_points_the_rungs_were() -> None:
    import numpy as np

    from nanopnp.validation.attribution import reference_error
    from nanopnp.validation.probe import PROBE_SCHEMA, ProbeGrid, loads_probe

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: band\npatches:\n"
        "  - {name: block, r_nm: [0.5, 3.0], z_nm: [-1.0, 1.0], n_r: 11, n_z: 5}\n"
    )
    points = document.points_nm()
    wall = points[:, 0] >= 3.0 - 1e-12
    fine = 1.0 + points[:, 0] ** 2
    coarse = np.where(wall, 1.5, 1.01) * fine
    grid = ProbeGrid(
        document=document,
        points_nm=points,
        weights_nm2=document.weights_nm2(),
        masks={"potential": ~wall},
        bare={"potential": np.ones(document.count, dtype=bool)},
        dropped={"potential": int(wall.sum())},
    )
    errors = reference_error(
        _refinement("published", {"potential": coarse, "c_Na+": coarse}),
        _refinement("refined_1", {"potential": fine, "c_Na+": fine}),
        grid,
    )
    assert set(errors) == {"potential", "current_A"}
    assert errors["potential"] == pytest.approx(0.01, rel=1e-12)


@pytest.fixture(scope="module")
def ladder_plan():
    document = load_sweep(LADDER_SWEEP)
    return build_plan(document, source=LADDER_SWEEP, check_meshes=False)


def test_val01_ladder_rungs_are_separate_warm_start_components(ladder_plan) -> None:
    points = ladder_plan.points
    assert len(points) == len(LADDER) * 5

    roots = [point for point in points if point.parent is None]
    assert len(roots) == len(LADDER)
    assert sorted(point.coordinates[0] for point in roots) == list(range(len(LADDER)))

    for point in points:
        if point.parent is None:
            continue
        parent = ladder_plan.point(point.parent)
        assert point.coordinates[0] == parent.coordinates[0], (
            f"point {point.index} at rung {point.coordinates[0]} warm-starts from rung "
            f"{parent.coordinates[0]}, which crosses an element space"
        )

    warning = "\n".join(ladder_plan.warnings)
    assert "numerics.stabilisation" in warning
    assert "numerics.elements.u" in warning
    assert "cold" in warning


def test_val01_every_path_the_ladder_writes_is_a_warm_start_barrier() -> None:
    for rung in LADDER:
        for path in rung.assignments():
            assert any(
                path == barrier or path.startswith(f"{barrier}.") for barrier in WARM_START_BARRIERS
            ), f"rung {rung.name!r} writes {path!r}, which no warm-start barrier covers"


def test_val03_the_ladder_members_answer_the_five_frozen_cases(ladder_plan) -> None:
    frozen = {
        path.name.split(".case")[0]: case_identity(resolve(load_case(path)))
        for path in sorted(FROZEN_CASES.glob("*.case.yaml"))
    }
    assert len(frozen) == 5
    assert len(set(frozen.values())) == 5

    by_identity: dict[str, set[int]] = {}
    for index in range(len(ladder_plan.points)):
        identity = case_identity(resolve(ladder_plan.case(index)))
        assert identity in set(frozen.values()), (
            f"member {index} answers no frozen case; its identity is {identity[:12]}"
        )
        by_identity.setdefault(identity, set()).add(ladder_plan.point(index).coordinates[0])

    assert set(by_identity) == set(frozen.values())
    for rungs in by_identity.values():
        assert rungs == set(range(len(LADDER)))

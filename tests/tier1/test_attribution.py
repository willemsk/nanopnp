"""The attribution ladder: the deltas, the verdict, and what the rungs may share.

VAL-01, VAL-02, VAL-04, RSK-09, and section 5.3.2's warm-start partition.

The plan for this package argued that the telescoping identity ``Delta_total +
Delta_transport + Delta_flow + Delta_pair = Delta_resid`` "holds only if all four
rungs were compared against the same golden on the same probe grid with the same
masks". It does not: the sum telescopes for **any** four numbers, so a rung run
against a re-exported golden satisfies it exactly as cleanly as one run against
the right golden. The identity is worth asserting because it catches a slip in
forming the deltas, and it is asserted here — but the job the plan wanted from it
belongs to the provenance and mask gates, which are what the last four tests
below exercise.

Nothing here solves anything. The rung outcomes are built directly, so what is
under test is the algebra and the gates rather than a solver.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.io.case import load_case, resolve
from nanopnp.sweep.document import load_sweep
from nanopnp.sweep.plan import WARM_START_BARRIERS, build_plan
from nanopnp.validation.attribution import (
    IDENTITY_TOLERANCE,
    LADDER,
    Attribution,
    LadderError,
    RungOutcome,
    attribute,
    write_report,
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
    """Return a golden carrying no arrays: the report's provenance, without files."""
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
    """Return one outcome per rung, carrying the given per-rung errors."""
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


# -- the identity -------------------------------------------------------------


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
    """The five deltas telescope back to ``Delta_resid``, to 1e-14 absolute.

    Four synthetic rung errors, including a monotone set, a flat set and a set
    that swings by nine orders between adjacent rungs — the last because the
    identity is an exact cancellation and cancellations are where floating point
    is worst.

    The named deltas are checked against their definitions as well as summing
    correctly, because four deltas that summed correctly and were assigned to the
    wrong rungs would pass a sum-only test and attribute the flow operator's
    contribution to the transport stabilisation.
    """
    report = attribute(_outcomes(errors), case="fixture", golden=_golden())
    entry = report.attribution("potential")

    assert entry.total == pytest.approx(errors[0])
    assert entry.transport == pytest.approx(errors[1] - errors[0])
    assert entry.flow == pytest.approx(errors[2] - errors[1])
    assert entry.pair == pytest.approx(errors[3] - errors[2])
    assert entry.residual == pytest.approx(errors[3])
    assert abs(entry.identity_residual()) <= IDENTITY_TOLERANCE

    report.check_identity()


def test_val01_the_identity_cannot_see_a_stale_golden() -> None:
    """The record of *why* the provenance gate exists, asserted rather than asserted of.

    ``E_0 + (E_1 - E_0) + (E_2 - E_1) + (E_3 - E_2) = E_3`` holds for arbitrary
    numbers, so four errors measured against four different objects telescope
    perfectly. Comparing the hashes is what catches that, and this test pins the
    algebraic fact so the plan's claim is not reintroduced.
    """
    arbitrary = Attribution(key="potential", kind="field", errors=(7.0, -3.0, 11.5, 0.25))
    assert abs(arbitrary.identity_residual()) <= IDENTITY_TOLERANCE


def test_val01_a_ladder_with_a_missing_rung_is_refused() -> None:
    """Three outcomes do not make the remaining deltas mean less; they change what they mean."""
    with pytest.raises(LadderError, match="4 rungs and 3 outcome"):
        attribute(_outcomes([0.1, 0.2, 0.3, 0.4])[:3], case="fixture", golden=_golden())


def test_val01_attribute_refuses_rungs_compared_against_different_goldens() -> None:
    """A rung measured against another golden is refused, naming the rung and both hashes."""
    outcomes = _outcomes([0.1, 0.2, 0.3, 0.4])
    outcomes[2] = RungOutcome(
        rung=outcomes[2].rung,
        golden_hash="0" * 64,
        probe_hash=outcomes[2].probe_hash,
        case_hash=outcomes[2].case_hash,
        fields=outcomes[2].fields,
        quantities=outcomes[2].quantities,
    )
    with pytest.raises(LadderError) as raised:
        attribute(outcomes, case="fixture", golden=_golden())
    message = str(raised.value)
    assert "golden_hash" in message
    assert "reference-taylor-hood" in message


def test_val01_attribute_refuses_rungs_masked_differently() -> None:
    """The mask is a property of the geometry, so two rungs cannot honestly differ in it."""
    outcomes = _outcomes([0.1, 0.2, 0.3, 0.4])
    fewer = outcomes[1]
    outcomes[1] = RungOutcome(
        rung=fewer.rung,
        golden_hash=fewer.golden_hash,
        probe_hash=fewer.probe_hash,
        case_hash=fewer.case_hash,
        fields=(
            FieldComparison(
                field="potential",
                points=99,
                rel_L2_r=0.2,
                rel_l2=0.4,
                max_abs_rel=0.6,
                max_at_nm=(1.5, -0.5),
            ),
        ),
        quantities=fewer.quantities,
    )
    with pytest.raises(LadderError, match="99 probe points"):
        attribute(outcomes, case="fixture", golden=_golden())


# -- VAL-04's verdict ---------------------------------------------------------


def test_val04_reference_limited_verdict() -> None:
    """``Delta_resid < Delta_ref`` is ``reference-limited``; otherwise it is ours to explain.

    Section 7.4's NOTE requires exactly this word: a comparison whose residual
    falls below the reference's own discretisation error is reported as
    reference-limited "rather than as agreement". Absent the refinement pair the
    verdict is neither — RSK-09 is simply unbounded for that case, and saying so
    is the honest report.
    """
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
    """Equality is not "limited": a residual exactly at the bound is still ours."""
    errors = [0.1, 0.1, 0.1, 0.02]
    report = attribute(
        _outcomes(errors), case="fixture", golden=_golden(), reference_errors={"potential": 0.02}
    )
    assert report.attribution("potential").verdict() == "attributed"


# -- the report ---------------------------------------------------------------


def test_val01_the_report_keeps_delta_transport_and_the_stabilisation_currents_apart(
    tmp_path: Path,
) -> None:
    """Both numbers appear, under distinct names, and the markdown says why.

    Section 6.7 extracts ``stabilisation_currents_A`` from a single run; the
    ladder's ``Delta_transport`` is a difference of two runs' distances from a
    third object. WP12 measured them agreeing to 1.55e-3 of the current on its
    benchmark, which is evidence that both measure the same physics — not licence
    to print one as the other.
    """
    report = attribute(
        _outcomes([0.0731, 0.0402, 0.0455, 0.0121], [0.08, 0.05, 0.04, 0.01]),
        case="fixture",
        golden=_golden(),
    )
    record = report.summary()
    entry = next(item for item in record["attributions"] if item["key"] == "potential")
    assert entry["delta_transport"] == pytest.approx(0.0402 - 0.0731)
    assert record["ladder"][1]["stabilisation_currents_A"] == {"Na+": -4.1e-11}

    text = report.markdown()
    assert "Δ_transport" in text
    assert "a different quantity" in text
    assert "not the same number" in text

    document, readable = write_report(report, tmp_path)
    assert document.is_file() and readable.is_file()
    assert "attribution_hash" in document.read_text(encoding="utf-8")


def test_val01_a_self_golden_report_says_so_in_the_first_line() -> None:
    """A ladder against a self-golden tests the machinery and nothing else.

    Every consumer prints ``golden_source``; the markdown puts it above the
    numbers, because a reader who reached the delta table first has already been
    misled.
    """
    report = attribute(_outcomes([0.0, 0.0, 0.0, 0.0]), case="fixture", golden=_golden("self"))
    assert report.golden_source == "self"
    text = report.markdown()
    assert "`self`" in text
    assert "tests the harness and nothing else" in text
    assert text.index("Golden source") < text.index("| key |")


def test_val01_an_unexported_field_is_named_in_the_report() -> None:
    """A golden without ``pressure`` reports it unavailable; the table does not shrink silently.

    ``sampled_fields`` is what makes the statement possible, and it is passed
    rather than derived: a rung's comparisons are already the intersection of our
    fields with the golden's, so a report that asked the golden which of *those*
    it lacked would always answer "none" and would say a golden carrying no
    ``pressure`` had covered it.
    """
    outcomes = _outcomes([0.1, 0.2, 0.3, 0.4], [0.01, 0.02, 0.03, 0.04])
    report = attribute(
        outcomes,
        case="fixture",
        golden=_golden(),
        sampled_fields=["potential", "pressure", "velocity_z"],
    )
    assert report.unavailable_fields == ("pressure", "velocity_z")
    assert set(report.unavailable_quantities) == {
        "conductance_S",
        "transport_number",
        "eof_m3_s",
    }
    markdown = report.markdown()
    assert "Not compared" in markdown
    assert "`pressure`" in markdown


def test_val01_unavailable_fields_cannot_be_derived_from_the_comparisons() -> None:
    """Without ``sampled_fields`` the report can only say what it compared.

    The degenerate answer is pinned here so the parameter is not quietly dropped
    again: every field an outcome carries is by construction one the golden has,
    so the complement over that set is empty however many fields are missing.
    """
    report = attribute(_outcomes([0.1, 0.2, 0.3, 0.4]), case="fixture", golden=_golden())
    assert report.unavailable_fields == ()


# -- the ladder as a sweep ----------------------------------------------------


@pytest.fixture(scope="module")
def ladder_plan():
    """Return the checked-in ladder sweep, planned without touching a mesh."""
    document = load_sweep(LADDER_SWEEP)
    return build_plan(document, source=LADDER_SWEEP, check_meshes=False)


def test_val01_ladder_rungs_are_separate_warm_start_components(ladder_plan) -> None:
    """Planning the ladder puts each rung in its own component, rooted and cold.

    Section 5.3.2 forbids a warm start across an element-space or operator
    change, and ``load_initial`` refuses one at run time — exercised by
    ``tests/tier1/test_warm_start_descriptor.py``, whose
    ``test_val01_a_warm_start_across_an_element_order_is_refused`` and
    ``test_num13_a_warm_start_across_two_stabilisation_modes_is_refused``
    cover the two crossings this axis makes. Here the *plan* is under test: twenty
    solves that each attempt a warm start, fail its gate and fall back is twenty
    diagnostics for a fact the sweep document already states.

    Asserted structurally: no edge of the forest joins two rungs, there is one
    root per rung, and every rung's four remaining members hang off it.
    """
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
    """The ladder and the planner must agree about which paths sever the forest.

    The structural link between :data:`LADDER` and
    :data:`~nanopnp.sweep.plan.WARM_START_BARRIERS`: a rung assignment added later
    over a path the planner does not treat as a barrier would silently restore an
    edge the section 5.3.2 partition forbids.
    """
    for rung in LADDER:
        for path in rung.assignments():
            assert any(
                path == barrier or path.startswith(f"{barrier}.") for barrier in WARM_START_BARRIERS
            ), f"rung {rung.name!r} writes {path!r}, which no warm-start barrier covers"


def test_val01_the_sweep_document_mirrors_the_ladder(ladder_plan) -> None:
    """The document's ``rung`` axis is :data:`LADDER`, value for value and in order.

    Two records of one fact, so they are checked against each other: a document
    that had drifted would dispatch a configuration the report then labelled with
    another rung's name, which is the one error the whole package exists to avoid
    making about the reference.
    """
    document = load_sweep(LADDER_SWEEP)
    rung_axis = next(axis for axis in document.axes if axis.name == "rung")
    assert [dict(entry) for entry in rung_axis.points()] == [
        dict(rung.assignments()) for rung in LADDER
    ]
    assert ladder_plan.document["axes"][0]["name"] == "rung"


def test_val03_the_ladder_members_answer_the_five_frozen_cases(ladder_plan) -> None:
    """Every member's case identity is one of the five frozen cases', and all five occur.

    This is what makes the golden's ``case_hash`` gate mean anything: the sweep
    is only the dispatch, and a member whose identity was not a frozen case's
    would be compared against a golden for a case it did not solve.

    It also pins that the identity is invariant across the ladder — four rungs,
    one case — which is why :data:`~nanopnp.validation.comsol.DISCRETISATION_KEYS`
    is left out of it.
    """
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

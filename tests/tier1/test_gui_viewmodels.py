"""VER-43 and VER-44: the shell's view-models, asserted where Qt cannot be built."""

from __future__ import annotations

import ast
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args, get_origin

import pytest

from nanopnp.core.errors import EXIT_CANCELLED, EXIT_CASE, EXIT_CONVERGENCE, EXIT_GATE
from nanopnp.core.paths import available_corrections
from nanopnp.core.stages import Cancelled as CancelledError
from nanopnp.gui.case_model import ABSENT, CaseEditor
from nanopnp.gui.convergence import RESIDUAL, UPDATE, ConvergenceModel
from nanopnp.gui.render import Rendered, RenderFailed
from nanopnp.gui.run_model import RunModel
from nanopnp.gui.scene import SceneModel
from nanopnp.gui.solver import (
    Cancelled,
    Finished,
    Iteration,
    Progress,
    Rung,
    Stage,
    Started,
    failure_event,
)
from nanopnp.io.case import (
    CaseValidationError,
    dumps_case,
)
from nanopnp.io.case_paths import case_fields
from nanopnp.mesh.meshers import registered_meshers
from nanopnp.numerics.linear import registered_solvers
from nanopnp.physics.models import registered_models, registered_stabilisations
from nanopnp.pipeline.case import load_case
from nanopnp.pipeline.checks import options_at

CASE = """
schema: nanopnp/case/v0.5
name: shell-probe
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns, solid_permittivities: {membrane: 3.2}}
numerics: {continuation: default_ladder, stabilisation: none}
"""

VOCABULARY = (
    "epnp-ns",
    "pnp-ns",
    "willems2020_nacl",
    "borukhov",
    "umfpack",
    "superlu",
    "no_slip",
    "supg",
    "taubin",
    '"propka"',
    "'propka'",
    "CHARMM",
    "PEOEPB",
    "SWANSON",
    "phi_V",
    "u_m_s",
    "p_Pa",
    "mol_m3",
    "profile1",
    '"hand-edit"',
    "rho_fixed_C_m3",
)


@pytest.fixture
def case_file(tmp_path: Path) -> Path:
    path = tmp_path / "case.yaml"
    path.write_text(CASE, encoding="utf-8")
    return path


# CON-09, VER-55, CON-10, VER-60
def test_if09_the_view_models_import_no_qt_and_no_ngsolve() -> None:
    probe = (
        "import sys;"
        "import nanopnp.gui.case_model, nanopnp.gui.run_model,"
        " nanopnp.gui.solver, nanopnp.gui.probe,"
        " nanopnp.gui.convergence, nanopnp.gui.scene, nanopnp.gui.render,"
        " nanopnp.gui.geometry, nanopnp.gui.assess, nanopnp.gui.charge;"
        "print(sorted(m for m in ('PySide6','PyQt5','PyQt6','ngsolve','netgen',"
        " 'MDAnalysis','skimage','shapely','gmsh','pdb2pqr','propka') if m in sys.modules))"
    )
    found = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    assert found.stdout.strip() == "[]", found.stdout


def _without_payloads(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        targets = (
            [node.target]
            if isinstance(node, ast.AnnAssign)
            else node.targets
            if isinstance(node, ast.Assign)
            else []
        )
        if any(isinstance(target, ast.Name) and target.id == "PAYLOADS" for target in targets):
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return source.replace(segment, "")
    return source


# FR-25
def test_if09_no_option_list_is_written_in_the_shell() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "nanopnp" / "gui"
    offenders = {
        f"{path.relative_to(root)}: {value}"
        for path in root.rglob("*.py")
        for value in VOCABULARY
        if value in _without_payloads(path.read_text(encoding="utf-8"))
    }
    assert not offenders, (
        f"{sorted(offenders)} name case-file values inside gui/; every enumeration must come "
        "from the schema or from a live registry, through nanopnp.pipeline.checks.options_at"
    )


def test_if09_editor_refuses_a_value_the_schema_refuses(case_file: Path) -> None:
    editor = CaseEditor.open(case_file)
    before = dumps_case(editor.document)

    with pytest.raises(CaseValidationError) as refused:
        editor.stage("boundary_conditions.bias_V", "lots")

    message = str(refused.value)
    assert "boundary_conditions.bias_V" in message
    assert "'lots'" in message
    assert "float" in message
    assert editor.staged == {}
    assert dumps_case(editor.document) == before


def test_if09_editor_reports_registry_problems_as_the_cli_does(case_file: Path) -> None:
    editor = CaseEditor.open(case_file)
    editor.stage("electrolyte.parameters", "not_installed")
    with pytest.raises(CaseValidationError):
        editor.commit()
    from_the_shell = editor.problems()

    case_file.write_text(
        CASE.replace("parameters: willems2020_nacl", "parameters: not_installed"),
        encoding="utf-8",
    )
    with pytest.raises(CaseValidationError) as refused:
        load_case(case_file)

    assert from_the_shell == str(refused.value)
    assert "not_installed" in str(refused.value)


@pytest.mark.parametrize(
    ("path", "value", "written", "named"),
    [
        ("physics.model", "pnp-nz", "model: pnp-ns,", "is not registered"),
        ("numerics.elements.u", "P1", None, "inf-sup"),
    ],
)
def test_qr11_editor_refuses_what_check_document_refuses_in_the_cli_words(
    case_file: Path, path: str, value: str, written: str | None, named: str
) -> None:
    editor = CaseEditor.open(case_file)
    before = dumps_case(editor.document)
    editor.stage(path, value)
    with pytest.raises(CaseValidationError):
        editor.commit()
    from_the_shell = editor.problems()
    assert dumps_case(editor.document) == before

    edited = (
        CASE.replace(written, f"model: {value},")
        if written is not None
        else CASE.replace(
            "numerics: {continuation: default_ladder, stabilisation: none}",
            "numerics: {continuation: default_ladder, stabilisation: none, elements: {u: P1}}",
        )
    )
    assert edited != CASE
    case_file.write_text(edited, encoding="utf-8")
    with pytest.raises(CaseValidationError) as refused:
        load_case(case_file)
    assert from_the_shell == str(refused.value)
    assert named in str(refused.value)


def test_if09_editor_offers_only_what_the_schema_and_registries_name(case_file: Path) -> None:
    editor = CaseEditor.open(case_file)

    registered = {
        "physics.model": registered_models(),
        "numerics.stabilisation": registered_stabilisations(),
        "numerics.linear.solver": registered_solvers(),
        "numerics.mesh.backend": registered_meshers(),
        "electrolyte.parameters": available_corrections(),
        "electrolyte.corrections.density.model": ("none", *available_corrections()),
    }
    for path, expected in registered.items():
        assert set(editor.state(path).options or ()) == set(expected)

    for reference in case_fields():
        if reference.path in registered:
            continue
        literal = next(
            (
                get_args(candidate)
                for candidate in (reference.annotation, *get_args(reference.annotation))
                if get_origin(candidate) is Literal
            ),
            None,
        )
        if literal is not None:
            assert options_at(reference.path) == tuple(str(value) for value in literal), (
                reference.path
            )


def test_if09_editor_refuses_to_run_a_document_that_is_not_on_disk() -> None:
    from nanopnp.pipeline.case import loads_case

    editor = CaseEditor(document=loads_case(CASE))
    with pytest.raises(ValueError, match="unit of reproducibility"):
        editor.save()


def test_if09_running_an_unchanged_case_does_not_rewrite_the_file(case_file: Path) -> None:
    before = case_file.read_text(encoding="utf-8")
    editor = CaseEditor.open(case_file)
    assert not editor.dirty
    assert editor.ensure_saved() == case_file
    assert case_file.read_text(encoding="utf-8") == before

    editor.stage("boundary_conditions.bias_V", 0.2)
    editor.commit()
    assert editor.dirty
    assert editor.ensure_saved() == case_file
    assert case_file.read_text(encoding="utf-8") != before
    assert load_case(case_file).boundary_conditions.bias_V == pytest.approx(0.2)
    assert not editor.dirty


def test_if09_saving_refuses_while_an_edit_is_still_staged(case_file: Path) -> None:
    editor = CaseEditor.open(case_file)
    editor.stage("boundary_conditions.bias_V", 0.2)
    with pytest.raises(ValueError, match="uncommitted edits"):
        editor.ensure_saved()

    editor.commit()
    assert editor.ensure_saved() == case_file
    assert load_case(case_file).boundary_conditions.bias_V == pytest.approx(0.2)


def test_if09_a_field_absent_from_the_document_reads_as_absent(case_file: Path) -> None:
    editor = CaseEditor.open(case_file)
    assert editor.state("structure.source.path").value is ABSENT
    assert editor.state("geometry.analyte.shape").value is ABSENT
    assert editor.state("inputs.charge.path").value is ABSENT
    assert editor.state("inputs.mesh.artefact").value is None


def _schema_bounds(path: str) -> tuple[float, float] | None:
    from nanopnp.io.case import CaseDocument

    schema = CaseDocument.model_json_schema()
    definitions = schema.get("$defs", {})

    def alternatives(node: dict[str, object]) -> list[dict[str, object]]:
        if "$ref" in node:
            return alternatives(definitions[str(node["$ref"]).rsplit("/", 1)[-1]])
        found = [node]
        for key in ("anyOf", "allOf", "oneOf"):
            for member in node.get(key, ()):  # type: ignore[attr-defined]
                found.extend(alternatives(member))
        return found

    nodes = alternatives(schema)
    for component in path.split("."):
        stepped: list[dict[str, object]] = []
        for node in nodes:
            if component.isdigit() and isinstance(node.get("items"), dict):
                stepped.extend(alternatives(node["items"]))  # type: ignore[arg-type]
            elif component in node.get("properties", {}):  # type: ignore[operator]
                stepped.extend(alternatives(node["properties"][component]))  # type: ignore[index]
            elif isinstance(node.get("additionalProperties"), dict):
                stepped.extend(alternatives(node["additionalProperties"]))  # type: ignore[arg-type]
        nodes = stepped
    numeric = [node for node in nodes if node.get("type") in ("number", "integer")]
    lower = {node["minimum"] for node in numeric if "minimum" in node}
    upper = {node["maximum"] for node in numeric if "maximum" in node}
    if not lower or not upper:
        return None
    assert len(lower) == len(upper) == 1, (path, lower, upper)
    return float(lower.pop()), float(upper.pop())  # type: ignore[arg-type]


# IF-09
def test_ver60_a_bounded_number_spins_over_exactly_the_schema_s_range(case_file: Path) -> None:
    editor = CaseEditor.open(case_file)
    shown = {state.path: state.bounds for state in editor.states() if state.kind == "bounded"}
    declared = {
        reference.path: bounds
        for reference in case_fields()
        if (bounds := _schema_bounds(reference.path)) is not None
        and type(None) not in get_args(reference.annotation)
    }
    assert shown == declared
    assert shown["charge.ph"] == (0.0, 14.0)
    assert editor.state("charge.exclusion_offset_nm").kind == "number"
    assert editor.state("charge.exclusion_offset_nm").bounds is None
    assert editor.state("boundary_conditions.bias_V").bounds is None


@pytest.mark.parametrize(
    ("annotation", "kind", "integral"),
    [
        (float, "bounded", False),
        (int, "bounded", True),
        (float | None, "number", False),
        (int | None, "number", True),
    ],
    ids=["float", "int", "optional-float", "optional-int"],
)
def test_ver60_only_a_field_that_cannot_be_unset_is_a_spin_box(
    annotation: object, kind: str, integral: bool
) -> None:
    from nanopnp.gui.case_model import FieldState, _kind
    from nanopnp.io.case_paths import FieldReference

    reference = FieldReference(path="charge.synthetic", annotation=annotation)  # type: ignore[arg-type]
    found = _kind(reference, None, closed=True)
    assert found == kind
    state = FieldState(
        reference=reference,
        value=ABSENT,
        options=None,
        kind=found,
        bounds=(1.0, 9.0) if found == "bounded" else None,
    )
    assert state.integral is integral
    assert _kind(reference, None, closed=False) == "number"


def test_ver60_add_section_writes_only_a_section_whose_empty_form_changes_nothing(
    case_file: Path,
) -> None:
    from nanopnp.io.case import Charge
    from nanopnp.io.case_paths import NEUTRAL_SECTIONS

    editor = CaseEditor.open(case_file)
    assert editor.addable() == tuple(sorted(NEUTRAL_SECTIONS)) == ("charge",)
    assert editor.state("charge.ph").value is ABSENT
    assert not editor.dirty

    editor.add_section("charge")
    assert editor.addable() == ()
    assert editor.dirty
    assert editor.state("charge.ph").value == Charge().ph
    with pytest.raises(ValueError, match="already carries"):
        editor.add_section("charge")
    with pytest.raises(ValueError, match="cannot be added from a default"):
        editor.add_section("geometry")
    with pytest.raises(ValueError, match="cannot be added from a default"):
        editor.add_section("structure")

    editor.stage("charge.ph", 7.25)
    editor.commit()
    assert editor.ensure_saved() == case_file
    assert load_case(case_file).charge == Charge(ph=7.25)


def test_if09_run_model_fraction_is_monotone_and_ends_at_one() -> None:
    model = RunModel()
    model.consume(
        [
            Started(case="case.yaml", store=None),
            Stage(name="mesh", index=0, total=3),
            Progress(fraction=0.3, message="stage mesh"),
            Progress(fraction=0.1, message="a late report from a superseded stage"),
            Progress(fraction=1.7, message="out of range"),
            Stage(name="solve", index=1, total=3),
            Progress(fraction=0.8, message="rung 4"),
            Finished(directory="runs/probe"),
        ]
    )
    assert model.state == "finished"
    assert model.fraction == 1.0
    assert model.directory == Path("runs/probe")
    assert model.stage == Stage(name="solve", index=1, total=3)

    stepped = RunModel()
    seen: list[float] = []
    for fraction in (0.0, 0.4, 0.2, 0.9, 0.5):
        stepped.consume([Progress(fraction=fraction, message="x")])
        seen.append(stepped.fraction)
    assert seen == sorted(seen)
    assert all(0.0 <= value <= 1.0 for value in seen)


def test_if09_failure_carries_the_cli_exit_class() -> None:
    from nanopnp.numerics.newton import NewtonDivergenceError
    from nanopnp.post.qoi import RouteDisagreementError

    expected = {
        CaseValidationError("the case is wrong"): EXIT_CASE,
        RouteDisagreementError("the two routes disagree"): EXIT_GATE,
        NewtonDivergenceError("the ladder ran out of rungs"): EXIT_CONVERGENCE,
    }
    for error, code in expected.items():
        model = RunModel()
        model.consume([Started(case="case.yaml", store=None), failure_event(error)])
        assert model.state == "failed"
        assert model.exit_code == code
        assert model.diagnosis == str(error)

    cancelled = RunModel()
    cancelled.consume(
        [
            Started(case="case.yaml", store=None),
            Cancelled(where=str(CancelledError("cancelled before stage 'solve'"))),
        ]
    )
    assert cancelled.state == "cancelled"
    assert cancelled.exit_code == EXIT_CANCELLED
    assert "stage 'solve'" in cancelled.diagnosis
    assert cancelled.outcome() is None


# QR-12
def test_if09_an_event_the_model_does_not_apply_is_refused_not_read_as_cancelled() -> None:

    @dataclass(frozen=True)
    class _FutureVariant:
        residual: float

    model = RunModel()
    model.consume([Started(case="case.yaml", store=None)])
    with pytest.raises(TypeError, match="_FutureVariant"):
        model.consume([_FutureVariant(residual=1e-3)])  # type: ignore[list-item]
    assert model.state == "running"


def _ladder(model: RunModel) -> None:
    model.consume(
        [
            Started(case="case.yaml", store=None),
            Stage(name="solve", index=9, total=12),
            Rung(name="1-pb-linear", stage=1, index=0, total=3, reporting=False, tolerance=1e-6),
            Rung(name="3-equilibrium", stage=3, index=1, total=3, reporting=True, tolerance=1e-6),
            Rung(name="9-salt", stage=9, index=2, total=3, reporting=True, tolerance=1e-6),
            Iteration(iteration=1, residual=1e-2, update=2e-1, damping=0.2, trials=1, forced=False),
            Iteration(iteration=2, residual=1e-6, update=1e-3, damping=0.6, trials=1, forced=False),
            Iteration(
                iteration=3, residual=1e-12, update=1e-8, damping=1.0, trials=1, forced=False
            ),
            Finished(directory="runs/probe"),
        ]
    )


def test_ver44_the_plot_bands_the_ladder_and_names_both_kinds_of_silence() -> None:
    model = RunModel()
    _ladder(model)
    plot = model.convergence

    assert plot.state == "complete"
    assert [band.name for band in plot.bands] == ["1-pb-linear", "3-equilibrium", "9-salt"]
    assert [band.stage for band in plot.bands] == [1, 3, 9]
    assert [len(band.steps) for band in plot.bands] == [0, 0, 3]

    silent, on_entry, solved = plot.bands
    assert "takes no Newton callback" in silent.note()
    assert "converged on entry" in on_entry.note()
    assert "converged on entry" not in silent.note()
    assert "3 steps" in solved.note()


def test_ver44_a_solve_served_from_the_store_is_named_not_drawn_empty() -> None:
    served = RunModel()
    served.consume(
        [
            Started(case="case.yaml", store=None),
            Stage(name="solve", index=9, total=12),
            Finished(directory="runs/probe"),
        ]
    )

    assert served.convergence.state == "served"
    assert "served from the artefact store" in served.convergence.summary
    assert served.convergence.bands == []

    truncated = RunModel()
    truncated.consume(
        [
            Started(case="case.yaml", store=None),
            Stage(name="region", index=1, total=3),
            Stage(name="mesh", index=2, total=3),
            Finished(directory="runs/probe"),
        ]
    )
    assert truncated.state == "finished"
    assert truncated.convergence.state == "idle"
    assert "served" not in truncated.convergence.summary

    stopped = RunModel()
    stopped.consume(
        [
            Started(case="case.yaml", store=None),
            Rung(name="1-pb", stage=1, index=0, total=1, reporting=True, tolerance=1e-6),
            Cancelled(where="cancelled before rung '1-pb'"),
        ]
    )
    assert stopped.convergence.state == "stopped"
    assert stopped.convergence.bands[0].closed_on() == ""


def test_ver44_the_band_names_the_num16_test_its_own_numbers_support() -> None:
    forced = ConvergenceModel()
    forced.rung("r", 9, 0, 1, True, 1e-6)
    forced.step(1, 1e-13, 1e-9, 0.01, 6, True)
    forced.settle(finished=True)
    assert forced.bands[0].closed_on() == "residual"
    assert "closed on the residual test" in forced.bands[0].note()
    assert "1 forced" in forced.bands[0].note()

    coarse = ConvergenceModel()
    coarse.rung("r", 9, 0, 1, True, 1e-6)
    coarse.step(1, 1e-13, 1e-2, 1.0, 1, False)
    coarse.settle(finished=True)
    assert coarse.bands[0].closed_on() == "residual"

    met = ConvergenceModel()
    met.rung("r", 9, 0, 1, True, 1e-6)
    met.step(1, 1e-13, 1e-9, 1.0, 1, False)
    met.settle(finished=True)
    assert met.bands[0].closed_on() == "update"


def test_ver44_the_axis_is_logarithmic_whole_decades_and_per_band() -> None:
    model = RunModel()
    _ladder(model)
    plot = model.convergence

    low, high = plot.y_range
    assert low == float(int(low)) and high == float(int(high))
    assert low <= -12.0 <= high
    assert all(tick == float(int(tick)) for tick in plot.ticks())

    band = plot.bands[-1]
    start, end = plot.extent(band)
    points = plot.points(band, RESIDUAL)
    assert len(points) == len(band.steps)
    assert all(start <= x <= end for x, _ in points)
    assert points[-1][1] == pytest.approx(-12.0)
    assert plot.points(plot.bands[0], RESIDUAL) == ()

    updates = plot.points(band, UPDATE)
    assert [y for _, y in updates] != [y for _, y in points]


def test_ver44_a_sample_a_logarithm_cannot_place_is_omitted_and_counted() -> None:
    model = ConvergenceModel()
    model.rung("r", 9, 0, 1, True, 1e-6)
    model.step(1, 0.0, 0.0, 1.0, 1, False)
    model.step(2, 1e-9, 1e-7, 1.0, 1, False)
    model.settle(finished=True)

    assert model.count_omitted() == 2
    assert len(model.points(model.bands[0], RESIDUAL)) == 1
    assert "omitted" in model.summary


def test_ver44_a_step_with_no_rung_is_refused_not_banded_into_the_last_one() -> None:
    model = ConvergenceModel()
    with pytest.raises(ValueError, match="before any rung"):
        model.step(1, 1e-3, 1e-3, 1.0, 1, False)


def test_ver44_the_scene_model_offers_only_the_fields_the_child_reported() -> None:
    model = SceneModel()
    request = model.request("runs/probe")
    assert request.run == "runs/probe"
    assert model.state == "rendering"

    model.consume(
        [
            Rendered(
                document="runs/probe/viewer/scene.html",
                scene="runs/probe/viewer/scene.json",
                field="a_field",
                fields=("a_field", "another_field"),
                elements=124,
            )
        ]
    )
    assert model.state == "loading"
    assert model.fields == ("a_field", "another_field")
    assert model.document == Path("runs/probe/viewer/scene.html")


def test_ver44_a_document_that_loaded_without_drawing_is_a_diagnostic() -> None:
    model = SceneModel()
    model.consume(
        [
            Rendered(
                document="runs/probe/viewer/scene.html",
                scene="runs/probe/viewer/scene.json",
                field="a_field",
                fields=("a_field",),
                elements=8,
            )
        ]
    )

    model.loaded(True)
    assert model.state == "loading", "a loaded document is not a drawn picture"

    missing = SceneModel(**{**vars(model)})
    missing.probed(
        '{"ready": false, "renderer_loaded": false, '
        '"error": "ReferenceError: webgui is not defined", "renderer": "somewhere"}'
    )
    assert missing.state == "blank"
    assert "its renderer was not there" in missing.diagnosis
    assert missing.renderer in missing.diagnosis
    assert str(missing.scene) in missing.diagnosis

    threw = SceneModel(**{**vars(model)})
    threw.probed(
        '{"ready": false, "renderer_loaded": true, '
        '"error": "TypeError: bad scene", "renderer": "somewhere"}'
    )
    assert threw.state == "blank"
    assert "TypeError: bad scene" in threw.diagnosis
    assert "its renderer was not there" not in threw.diagnosis

    silent = SceneModel(**{**vars(model)})
    silent.probed(None)
    assert silent.state == "blank"
    assert "returned nothing" in silent.diagnosis

    drawn = SceneModel(**{**vars(model)})
    drawn.probed('{"ready": true, "renderer_loaded": true, "error": "", "renderer": "somewhere"}')
    assert drawn.state == "drawn"
    assert drawn.diagnosis == ""


def test_ver44_a_refused_render_replaces_the_picture_with_what_the_gate_said() -> None:
    model = SceneModel()
    model.request("runs/probe")
    model.consume(
        [RenderFailed(error="StateMismatchError", message="solve.bias_V: stored 0.02, this 0.2")]
    )

    assert model.state == "failed"
    assert model.diagnosis == "solve.bias_V: stored 0.02, this 0.2"
    assert model.document is None
    assert model.summary == model.diagnosis


def test_ver44_a_render_event_the_model_does_not_apply_is_refused() -> None:

    @dataclass(frozen=True)
    class _FutureVariant:
        note: str

    model = SceneModel()
    with pytest.raises(TypeError, match="_FutureVariant"):
        model.consume([_FutureVariant(note="later")])  # type: ignore[list-item]


# NUM-16, FR-17
def test_ver44_a_long_rung_is_decimated_keeping_its_first_and_last_step() -> None:
    from nanopnp.gui.convergence import MAX_POINTS_PER_BAND

    model = ConvergenceModel()
    model.rung("r", 9, 0, 1, True, 1e-6)
    count = MAX_POINTS_PER_BAND * 3
    for index in range(1, count + 1):
        model.step(index, 1.0 / index, 0.5 / index, 1.0, 1, False)
    model.settle(finished=True)

    band = model.bands[0]
    points = model.points(band, RESIDUAL)
    assert len(band.steps) == count
    assert len(points) == MAX_POINTS_PER_BAND
    start, end = model.extent(band)
    assert points[0][0] == pytest.approx(start + 0.5)
    assert points[-1][0] == pytest.approx(end - 0.5)
    assert points[-1][1] == pytest.approx(math.log10(1.0 / count))

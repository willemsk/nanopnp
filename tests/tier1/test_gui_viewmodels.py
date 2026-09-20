"""VER-43 — the shell's view-models, asserted where Qt cannot be constructed.

Every rule the desktop interface enforces lives below the Qt boundary, and this
module is why. ``PySide6.QtWidgets`` raises ``ImportError: libEGL.so.1`` in the
development container and on ``ubuntu-latest``
(`.knowledge/07-software-stack.md` §5), so a rule implemented in a widget would
be a rule asserted on two of the seven matrix jobs. Here the editor's
validation, the vocabulary it offers, the run state machine and the exit-class
agreement are all asserted on every one of them, at every supported Python
version.

The sharpest test in the file is
:func:`test_if09_editor_reports_registry_problems_as_the_cli_does`, which
asserts *string identity* between the diagnostic the interface shows and the one
``nanopnp run`` prints for a file holding the same mistake. Two renderings of
one error drift, and the one that drifts is the one the user is reading.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args, get_origin

import pytest

from nanopnp.cli.errors import EXIT_CANCELLED, EXIT_CASE, EXIT_CONVERGENCE, EXIT_GATE
from nanopnp.core.paths import available_corrections
from nanopnp.core.stages import Cancelled as CancelledError
from nanopnp.gui.case_model import ABSENT, CaseEditor
from nanopnp.gui.run_model import RunModel
from nanopnp.gui.solver import (
    Cancelled,
    Finished,
    Progress,
    Stage,
    Started,
    failure_event,
)
from nanopnp.io.case import (
    CaseValidationError,
    case_fields,
    dumps_case,
    load_case,
    options_at,
)
from nanopnp.physics.models import registered_models, registered_stabilisations
from nanopnp.solve.linear import AVAILABLE_SOLVERS

CASE = """
schema: nanopnp/case/v1
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
    # Values that belong to the schema and to the registries. If any of these
    # appears in ``gui/``, the interface has grown a second source of truth.
    "epnp-ns",
    "pnp-ns",
    "willems2020_nacl",
    "borukhov",
    "umfpack",
    "superlu",
    "no_slip",
    "supg",
    "taubin",
    "propka",
)


@pytest.fixture
def case_file(tmp_path: Path) -> Path:
    """Write a valid case file the editor can open."""
    path = tmp_path / "case.yaml"
    path.write_text(CASE, encoding="utf-8")
    return path


# -- the boundary -------------------------------------------------------------


def test_if09_the_view_models_import_no_qt_and_no_ngsolve() -> None:
    """In a fresh process, the view-models pull in neither a toolkit nor a solver.

    ``sys.modules`` in a *subprocess*, because this one has imported half the
    package already. Both halves are load-bearing: no Qt is what lets this file
    run on the push gate at all, and no NGSolve is what keeps a shell that is
    only browsing a case off the solver's ~370 ms — the editor validates the
    whole schema without it.

    ``PyQt5`` and ``PyQt6`` are checked as well. CON-09 forbids PyQt outright
    (it is GPL-3 or commercial only), and an import reaching one through some
    transitive path would put the whole bundle's licence in question.
    """
    probe = (
        "import sys;"
        "import nanopnp.gui.case_model, nanopnp.gui.run_model,"
        " nanopnp.gui.solver, nanopnp.gui.probe;"
        "print(sorted(m for m in ('PySide6','PyQt5','PyQt6','ngsolve','netgen')"
        " if m in sys.modules))"
    )
    found = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    assert found.stdout.strip() == "[]", found.stdout


def test_if09_no_option_list_is_written_in_the_shell() -> None:
    """No value of the case vocabulary appears anywhere under ``gui/``.

    The mechanical form of "the editor holds no vocabulary of its own". A
    hard-coded list of stabilisation modes would be an interface offering a mode
    this build does not register — a run whose FR-25 manifest describes
    something that never happened (§5.3.3).
    """
    root = Path(__file__).resolve().parents[2] / "src" / "nanopnp" / "gui"
    offenders = {
        f"{path.relative_to(root)}: {value}"
        for path in root.rglob("*.py")
        for value in VOCABULARY
        if value in path.read_text(encoding="utf-8")
    }
    assert not offenders, (
        f"{sorted(offenders)} name case-file values inside gui/; every enumeration must come "
        "from the schema or from a live registry, through nanopnp.io.case.options_at"
    )


# -- the editor ---------------------------------------------------------------


def test_if09_editor_refuses_a_value_the_schema_refuses(case_file: Path) -> None:
    """A bad value is refused at the field, and the document does not move."""
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
    """The interface's whole-document diagnostic is the command line's, character for character.

    ``electrolyte.parameters`` is a plain ``str``, so the field check cannot
    refuse an uninstalled parameter file; ``_check_registries`` does, on the
    whole document, which is exactly the second stage of validation §5.3.4 asks
    for. What is asserted is that the user reads the same sentence either way.
    """
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


def test_if09_editor_offers_only_what_the_schema_and_registries_name(case_file: Path) -> None:
    """Every option list is ``get_args`` of a ``Literal``, or a live registry.

    Both directions of "no vocabulary of its own": a ``Literal``-typed path
    offers exactly its members, and a registry-backed path offers exactly what
    is installed *now*, so a build without a correction file cannot offer it.
    """
    editor = CaseEditor.open(case_file)

    registered = {
        "physics.model": registered_models(),
        "numerics.stabilisation": registered_stabilisations(),
        "numerics.linear.solver": tuple(sorted(AVAILABLE_SOLVERS)),
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
    """A case assembled in memory has nowhere to be saved, and says so.

    §5.3.1 makes the file the unit of reproducibility. A run of an in-memory
    document would write a manifest naming an input that does not exist, so the
    refusal belongs here rather than in the manifest.
    """
    from nanopnp.io.case import loads_case

    editor = CaseEditor(document=loads_case(CASE))
    with pytest.raises(ValueError, match="unit of reproducibility"):
        editor.save()


def test_if09_running_an_unchanged_case_does_not_rewrite_the_file(case_file: Path) -> None:
    """A run that changed nothing runs the bytes the user wrote.

    A case file is written by hand: comments, key order and ``1`` where
    :func:`~nanopnp.io.case.dumps_case` writes ``1.0`` all survive a run and
    none of them survives a round trip. Since the shell saves before it runs
    (§5.3.1), an unconditional save would quietly destroy them the first time
    anyone pressed Run.
    """
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
    """A staged edit is not in the document, so it must not be silently dropped.

    :meth:`~nanopnp.gui.case_model.CaseEditor.save` writes ``document``, and a
    staged edit is by construction not in it yet. Saving over the file with the
    edit still pending would leave the user looking at a form that says ``0.2``
    and a run, made from that very file, at ``0.1`` — §5.3.1's unit of
    reproducibility reproducing something nobody asked for.
    """
    editor = CaseEditor.open(case_file)
    editor.stage("boundary_conditions.bias_V", 0.2)
    with pytest.raises(ValueError, match="uncommitted edits"):
        editor.ensure_saved()

    editor.commit()
    assert editor.ensure_saved() == case_file
    assert load_case(case_file).boundary_conditions.bias_V == pytest.approx(0.2)


def test_if09_a_field_absent_from_the_document_reads_as_absent(case_file: Path) -> None:
    """A field of the schema the case does not carry is ``ABSENT``, never ``None``.

    ``None`` is a value several fields may legitimately hold, and a panel that
    conflated the two would show ``structure.source.pdb`` as set to nothing
    rather than as living in a block this case has not got — which is a fact
    about the document, and the distinction
    :func:`~nanopnp.io.case.substitute` acts on when it refuses to write into a
    section that is not there.
    """
    editor = CaseEditor.open(case_file)
    # Blocks this case does not carry at all.
    assert editor.state("structure.source.pdb").value is ABSENT
    assert editor.state("geometry.analyte.shape").value is ABSENT
    assert editor.state("inputs.charge.path").value is ABSENT
    # A field of a block it does carry, holding nothing.
    assert editor.state("inputs.mesh.artefact").value is None


# -- run control --------------------------------------------------------------


def test_if09_run_model_fraction_is_monotone_and_ends_at_one() -> None:
    """The bar never goes backwards, and a settled run is at 1.

    :class:`~nanopnp.core.stages.Progress` promises monotone in [0, 1], and
    :func:`~nanopnp.core.stages.report` clamps the range but not the order — a
    queue drained after a cancellation can hand over a late report from a stage
    already superseded. A bar that moved backwards would be reporting the
    transport rather than the run.
    """
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
    """A failure is diagnosed with the §3.1 code the command line would return.

    One representative of each class, asserted against the literal codes of
    §3.1 rather than against a second call to
    :func:`~nanopnp.cli.errors.classify` — which would only establish that the
    classifier agrees with itself.
    """
    from nanopnp.post.qoi import RouteDisagreementError
    from nanopnp.solve.newton import NewtonDivergenceError

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


def test_if09_an_event_the_model_does_not_apply_is_refused_not_read_as_cancelled() -> None:
    """A variant added to ``RunEvent`` fails here rather than settling the run.

    WP15 widens the union with a ``NewtonStep``. Dispatching the terminal state
    from a trailing ``else`` would have made the first Newton step of every run
    read as a cancellation — a run that produced a result reported as one that
    wrote nothing, which is the shape of wrong answer QR-12 exists to refuse.
    """

    @dataclass(frozen=True)
    class _FutureVariant:
        residual: float

    model = RunModel()
    model.consume([Started(case="case.yaml", store=None)])
    with pytest.raises(TypeError, match="_FutureVariant"):
        model.consume([_FutureVariant(residual=1e-3)])  # type: ignore[list-item]
    assert model.state == "running"

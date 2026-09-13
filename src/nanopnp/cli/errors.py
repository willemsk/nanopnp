"""The exception → exit-code table, and the classifier over it (IF-02, QR-12).

Section 3.1 NOTE (IF-02) makes the CLI's exit status a contract: FR-24's job
array branches on it, and QR-06 requires a member that *failed* to be
distinguishable from one that was *refused*. ``3`` says the case file is wrong
and a retry will fail identically; ``4`` says a numerical gate stopped the run
where it stood; ``5`` says the continuation ladder ran out of rungs, which a
different starting point might survive.

**The mapping is an enumeration, not a base-class test.** Every class here is
named, and every public exception class under ``src/nanopnp`` is either in
:data:`EXIT_CODES` or in :data:`EXCLUDED` with a written reason —
:mod:`tests.tier1.test_cli` asserts that in both directions. A base-class test
would classify a gate added later by whichever ``RuntimeError`` it happened to
subclass; here it fails the enumeration instead of silently becoming ``1``.

**No exception module is imported to build the table.** The keys are
``f"{module}:{qualname}"`` strings and :func:`classify` walks the raised
object's ``__mro__``, so classifying an error costs no import at all and
``import nanopnp.cli`` stays at the ~70 ms the deferred-import rule protects
(CLAUDE.md). Naming a base class covers its subclasses for free.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "EXCLUDED",
    "EXIT_CANCELLED",
    "EXIT_CASE",
    "EXIT_CODES",
    "EXIT_CONVERGENCE",
    "EXIT_GATE",
    "EXIT_OK",
    "EXIT_UNEXPECTED",
    "EXIT_USAGE",
    "classify",
]

EXIT_OK: Final = 0
"""The command did what it was asked."""

EXIT_UNEXPECTED: Final = 1
"""An unclassified failure — the only class whose traceback is worth keeping."""

EXIT_USAGE: Final = 2
"""The command line was wrong. argparse's own code; the CLI does not raise it."""

EXIT_CASE: Final = 3
"""The case file was refused. Nothing numerical went wrong and a retry will not help."""

EXIT_GATE: Final = 4
"""A gate of the QR-12 family aborted the run, naming the quantity and its location."""

EXIT_CONVERGENCE: Final = 5
"""Newton or the continuation ladder failed to converge (FR-17, NUM-16)."""

EXIT_CANCELLED: Final = 130
"""The run was cancelled — a token, or SIGINT. 128 + SIGINT, as a shell reports it."""

EXIT_CODES: Final[dict[str, int]] = {
    # -- 3, the case ---------------------------------------------------------
    # IF-03: a case rejected by validation or by schema. The fix is an edit to
    # the case file, so a job array must not retry the member.
    "nanopnp.io.case:CaseValidationError": EXIT_CASE,
    "nanopnp.io.case:UnsupportedCaseSection": EXIT_CASE,
    "pydantic_core._pydantic_core:ValidationError": EXIT_CASE,
    # `outputs:` asked for a quantity this run cannot produce -- `rectification`
    # at one operating point, `analyte_force` with no analyte. A ValueError
    # rather than a gate error: no result is in doubt, and like every other 3
    # the fix is an edit to the case file rather than a retry.
    "nanopnp.post.stage:SelectionError": EXIT_CASE,
    # `--upto` named a stage this run does not walk -- a typo, or stage 7 on a
    # case that supplies no field. 3 rather than 1 for the same reason as every
    # other 3: nothing numerical went wrong, and a job array retrying on
    # "unexpected" would fail identically. 3 rather than 2 because the second of
    # the two conditions is not a wrong command line at all -- `--upto charge`
    # names a registered stage, and it is the *case* that gives it nothing to
    # read -- and because 2 stays argparse's own code, raised where argparse
    # raises it and nowhere else.
    "nanopnp.io.run:UnknownStageError": EXIT_CASE,
    # A dotted path that names no field of the case schema -- a misspelt sweep
    # axis, or a switch path this build and the schema disagree about. 3 for the
    # same reason as every other 3: the fix is an edit to the document that
    # named it, and a job array retrying the member fails identically (FR-24).
    "nanopnp.io.case:UnknownCasePathError": EXIT_CASE,
    # A sweep that cannot be planned as written -- an axis naming a path the case
    # schema does not have, a value of the wrong type, a point the schema refuses,
    # or `rectification` asked for with no opposite-bias pair to produce it from.
    # 3, because a plan is refused by an edit to the sweep document or to the base
    # case; retrying the plan fails identically (FR-24).
    "nanopnp.sweep.plan:SweepPlanError": EXIT_CASE,
    # A file the case file or the command line named is not there. Classified
    # rather than left to fall through to 1 because "unexpected" is what a job
    # array retries, and this is the other kind: the path is wrong, and it will
    # be just as wrong on the retry.
    "builtins:FileNotFoundError": EXIT_CASE,
    # -- 4, the gates --------------------------------------------------------
    # QR-12: every one of these aborts naming the gate, the offending quantity
    # and its location, rather than returning a plausible wrong answer.
    "nanopnp.solve.gates:GateViolationError": EXIT_GATE,
    "nanopnp.post.qoi:RouteDisagreementError": EXIT_GATE,
    "nanopnp.post.forces:ForceDisagreementError": EXIT_GATE,
    "nanopnp.post.indicator:IndicatorError": EXIT_GATE,
    "nanopnp.post.forces:ExtensionError": EXIT_GATE,
    "nanopnp.mesh.ingest:MeshVocabularyError": EXIT_GATE,
    "nanopnp.mesh.quality:MeshQualityError": EXIT_GATE,
    "nanopnp.mesh.adapter:MeshFormatError": EXIT_GATE,
    "nanopnp.mesh.adapter:MeshDataError": EXIT_GATE,
    "nanopnp.mesh.reference:ReferenceGeometryError": EXIT_GATE,
    "nanopnp.geometry.analyte:AnalyteGeometryError": EXIT_GATE,
    "nanopnp.density.grid:GridFormatError": EXIT_GATE,
    "nanopnp.charge.fields:FieldDocumentError": EXIT_GATE,
    "nanopnp.charge.fields:ChargeFieldError": EXIT_GATE,
    "nanopnp.solve.state:StateMismatchError": EXIT_GATE,
    # A neighbour's converged state that does not describe a space this run
    # could load into. A subclass of the above and classified the same way; it
    # is listed because the enumeration walks the source rather than the class
    # hierarchy, which is the point of the enumeration. Note that a sweep never
    # lets one reach the CLI: FR-24 makes the warm start an optimisation, so a
    # refused neighbour falls back to the full ladder and records the reason.
    "nanopnp.solve.state:WarmStartError": EXIT_GATE,
    "nanopnp.io.store:StoreError": EXIT_GATE,
    "nanopnp.io.run:MissingUpstreamError": EXIT_GATE,
    # A dataset that cannot be built from the members that ran -- an unreadable
    # member record, or a pair whose recorded biases are not the opposite ones it
    # was paired on. A gate in the QR-12 sense: rather than report a table it
    # cannot build honestly, the collector stops and names what is wrong. Not a 3,
    # because the members have already run and the fix is to re-run the missing
    # ones rather than to edit a document.
    "nanopnp.sweep.collect:SweepCollectionError": EXIT_GATE,
    # The reproduction refusals are gates in exactly the QR-12 sense: rather
    # than report a comparison it cannot make honestly, the check stops and
    # names what is wrong (an input that moved, a solve served from the store).
    "nanopnp.io.reproduce:InputMovedError": EXIT_GATE,
    "nanopnp.io.reproduce:ReproductionError": EXIT_GATE,
    # -- 5, convergence ------------------------------------------------------
    # Distinguished from 4 because a different starting point may survive it:
    # this is the member a sweep may usefully re-dispatch from a neighbour.
    "nanopnp.solve.newton:NewtonDivergenceError": EXIT_CONVERGENCE,
    "nanopnp.solve.continuation:TransferError": EXIT_CONVERGENCE,
    # -- 130, cancellation ---------------------------------------------------
    "nanopnp.core.stages:Cancelled": EXIT_CANCELLED,
    "builtins:KeyboardInterrupt": EXIT_CANCELLED,
}
"""Every classified exception, keyed on ``f"{module}:{qualname}"``.

A base class covers its subclasses: :func:`classify` walks the raised object's
method resolution order, so a subclass added under a classified base needs no
entry. It still needs one *here* to leave the enumeration test, which walks the
source rather than the class hierarchy — that is the point of the enumeration.
"""

EXCLUDED: Final[dict[str, str]] = {
    "nanopnp.core.hashing:CanonicalisationError": (
        "an internal contract violation, not a user-facing condition: it is raised when a stage "
        "hands the hasher a value no artefact parameter may hold. A user cannot provoke it from a "
        "case file, and if one reaches the CLI it is a bug whose traceback is the diagnostic -- "
        "which is exactly what exit code 1 means"
    ),
    "nanopnp.io.defaults:UnknownSwitchPathError": (
        "likewise internal: the switch paths are a frozen enumeration checked by VER-24 in both "
        "directions, so an unknown one means the manifest code and the case schema have diverged "
        "in this build, not that the user asked for something impossible"
    ),
}
"""Public exception classes deliberately left unclassified, with the reason.

Membership here is a *decision*, recorded where the decision is enforced. The
Tier-1 enumeration accepts a class in this mapping or in :data:`EXIT_CODES` and
refuses one in neither, so a class added later fails a test rather than becoming
a silent ``1``.
"""


def classify(error: BaseException) -> int:
    """Return the exit code an exception should produce (IF-02).

    Parameters
    ----------
    error
        The exception that reached the CLI.

    Returns
    -------
    int
        The code :data:`EXIT_CODES` gives the first class in the exception's
        method resolution order that carries one, or :data:`EXIT_UNEXPECTED`.

    Notes
    -----
    The walk is over ``type(error).__mro__`` and the keys are strings, so no
    exception's defining module is imported to classify it. A class listed in
    :data:`EXCLUDED` classifies as ``1`` here, by design: the exclusion says
    "unexpected is the right answer", and the enumeration test says it was
    decided rather than overlooked.
    """
    for klass in type(error).__mro__:
        code = EXIT_CODES.get(f"{klass.__module__}:{klass.__qualname__}")
        if code is not None:
            return code
    return EXIT_UNEXPECTED

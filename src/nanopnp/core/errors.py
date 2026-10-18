"""The exception to exit-code table, and the classifier over it."""

from __future__ import annotations

from typing import Final

__all__ = [
    "EXCLUDED",
    "EXIT_CANCELLED",
    "EXIT_CASE",
    "EXIT_CODES",
    "EXIT_CONVERGENCE",
    "EXIT_GATE",
    "EXIT_MEANINGS",
    "EXIT_OK",
    "EXIT_UNEXPECTED",
    "EXIT_USAGE",
    "classify",
]

EXIT_OK: Final = 0

EXIT_UNEXPECTED: Final = 1

EXIT_USAGE: Final = 2

EXIT_CASE: Final = 3

EXIT_GATE: Final = 4

EXIT_CONVERGENCE: Final = 5

EXIT_CANCELLED: Final = 130

EXIT_MEANINGS: Final[dict[int, str]] = {
    EXIT_OK: "success",
    EXIT_UNEXPECTED: "an unexpected failure; the only class whose traceback is worth keeping "
    "(re-run with --traceback)",
    EXIT_USAGE: "a usage error: the command line was wrong",
    EXIT_CASE: "the case was refused, by the schema or by validation; a retry fails identically",
    EXIT_GATE: "a numerical gate of the QR-12 family aborted the run, naming the quantity and "
    "where",
    EXIT_CONVERGENCE: "Newton or the continuation ladder did not converge (FR-17, NUM-16)",
    EXIT_CANCELLED: "cancelled, by a token or by SIGINT",
}

EXIT_CODES: Final[dict[str, int]] = {
    # -- 3, the case ---------------------------------------------------------
    "nanopnp.io.case:CaseValidationError": EXIT_CASE,
    "nanopnp.charge.pqr:PQRError": EXIT_CASE,
    "nanopnp.io.case:UnsupportedCaseSection": EXIT_CASE,
    "pydantic_core._pydantic_core:ValidationError": EXIT_CASE,
    # no result is in doubt; the fix is an edit to the case file
    "nanopnp.post.stage:SelectionError": EXIT_CASE,
    # 3 not 2: argparse owns 2, and the case may be what gives the named stage nothing to read
    "nanopnp.pipeline.run:UnknownStageError": EXIT_CASE,
    # the installation is wrong, not the case; a retry fails until the extra is installed
    "nanopnp.core.stages:MissingExtraError": EXIT_CASE,
    "nanopnp.io.case_paths:UnknownCasePathError": EXIT_CASE,
    "nanopnp.sweep.plan:SweepPlanError": EXIT_CASE,
    # the path is as wrong on a retry, and a job array retries "unexpected"
    "builtins:FileNotFoundError": EXIT_CASE,
    # -- 4, the gates --------------------------------------------------------
    "nanopnp.numerics.gates:GateViolationError": EXIT_GATE,
    "nanopnp.post.qoi:RouteDisagreementError": EXIT_GATE,
    "nanopnp.post.forces:ForceDisagreementError": EXIT_GATE,
    "nanopnp.post.indicator:IndicatorError": EXIT_GATE,
    "nanopnp.post.forces:ExtensionError": EXIT_GATE,
    "nanopnp.mesh.ingest:MeshVocabularyError": EXIT_GATE,
    "nanopnp.mesh.quality:MeshQualityError": EXIT_GATE,
    "nanopnp.mesh.adapter:MeshFormatError": EXIT_GATE,
    "nanopnp.mesh.adapter:MeshDataError": EXIT_GATE,
    "nanopnp.geometry.analyte:AnalyteGeometryError": EXIT_GATE,
    "nanopnp.density.grid:GridFormatError": EXIT_GATE,
    "nanopnp.structure.read:StructureInputError": EXIT_GATE,
    "nanopnp.structure.axis:SymmetryGateError": EXIT_GATE,
    "nanopnp.structure.ensemble:EnsembleFormatError": EXIT_GATE,
    "nanopnp.density.radii:DensityInputError": EXIT_GATE,
    "nanopnp.density.union:DensityGateError": EXIT_GATE,
    "nanopnp.geometry.contour:ContourGateError": EXIT_GATE,
    "nanopnp.geometry.region:RegionGateError": EXIT_GATE,
    "nanopnp.mesh.generate:WallSizeGateError": EXIT_GATE,
    # 4 not 1: the mesh is a function of the recipe, so a retry fails identically
    "nanopnp.mesh.gmsh_backend:GmshMeshingError": EXIT_GATE,
    "nanopnp.charge.fields:FieldDocumentError": EXIT_GATE,
    "nanopnp.charge.fields:ChargeFieldError": EXIT_GATE,
    # a malformed or mismatched inputs.pqr is the case's, and exits 3
    "nanopnp.charge.protonation:ProtonationError": EXIT_GATE,
    "nanopnp.solve.state:StateMismatchError": EXIT_GATE,
    # listed because the enumeration walks the source, not the class hierarchy
    "nanopnp.solve.state:WarmStartError": EXIT_GATE,
    "nanopnp.io.store:StoreError": EXIT_GATE,
    "nanopnp.pipeline.run:MissingUpstreamError": EXIT_GATE,
    # 4 not 3: the members already ran, and the fix is to re-run the missing ones
    "nanopnp.sweep.collect:SweepCollectionError": EXIT_GATE,
    "nanopnp.pipeline.reproduce:InputMovedError": EXIT_GATE,
    "nanopnp.pipeline.reproduce:ReproductionError": EXIT_GATE,
    "nanopnp.validation.probe:ProbeGridError": EXIT_GATE,
    "nanopnp.validation.comsol:GoldenError": EXIT_GATE,
    "nanopnp.validation.attribution:LadderError": EXIT_GATE,
    "nanopnp.validation.geometry:GeometryComparisonError": EXIT_GATE,
    "nanopnp.validation.geometry:MissingPlaneError": EXIT_GATE,
    "nanopnp.validation.geometry:GeometryToleranceError": EXIT_GATE,
    "nanopnp.validation.apbs:BoxError": EXIT_GATE,
    "nanopnp.validation.apbs:ApbsError": EXIT_GATE,
    "nanopnp.validation.apbs:Val06Error": EXIT_GATE,
    # 3 not 4: the fix is another directory or a re-run, as for a file the case named
    "nanopnp.validation.runs:RunError": EXIT_CASE,
    # -- 5, convergence ------------------------------------------------------
    # distinguished from 4 because a different starting point may survive it
    "nanopnp.numerics.newton:NewtonDivergenceError": EXIT_CONVERGENCE,
    "nanopnp.solve.continuation:TransferError": EXIT_CONVERGENCE,
    # -- 130, cancellation ---------------------------------------------------
    "nanopnp.core.stages:Cancelled": EXIT_CANCELLED,
    "builtins:KeyboardInterrupt": EXIT_CANCELLED,
}

EXCLUDED: Final[dict[str, str]] = {
    "nanopnp.core.hashing:CanonicalisationError": (
        "an internal contract violation, not a user-facing condition: it is raised when a stage "
        "hands the hasher a value no artefact parameter may hold. A user cannot provoke it from a "
        "case file, and if one reaches the CLI it is a bug whose traceback is the diagnostic -- "
        "which is exactly what exit code 1 means"
    ),
    "nanopnp.validation.examples:ExampleCommandError": (
        "raised by the VER-46 test harness that executes the worked examples' README commands, "
        "never by a command of the CLI: it reports that one of those commands exited nonzero, "
        "and the command's own exit code is the classified one"
    ),
    "nanopnp.validation.costs:CostStudyError": (
        "raised by the cost-study script, run as a module and never by a command of the CLI: it "
        "reports a measurement that cannot be trusted, and the traceback is the diagnostic"
    ),
    "nanopnp.io.defaults:UnknownSwitchPathError": (
        "likewise internal: the switch paths are a frozen enumeration checked by VER-24 in both "
        "directions, so an unknown one means the manifest code and the case schema have diverged "
        "in this build, not that the user asked for something impossible"
    ),
    "nanopnp.io.workspace:MissingWorkspaceError": (
        "raised only to a library caller that constructs a stage without its workspace; the "
        "walk behind every command of the CLI gives each stage one, so no command reaches it and "
        "the traceback is the diagnostic"
    ),
    "nanopnp.io.workspace:WorkspaceInUseError": (
        "raised only to a library caller that names a workspace an earlier run left files in; the "
        "walk behind every command of the CLI gives each stage a fresh directory, so no command "
        "reaches it and the message names the files and the overwrite_workspace switch"
    ),
    "nanopnp.gui.probe:PayloadError": (
        "raised only inside the packaging probe's --selftest, which catches it, prints it naming "
        "the payload and exits 1 itself (WP24 D17); no command of the CLI reaches the probe, and "
        "a broken bundle is a packaging defect rather than a case, gate or convergence class"
    ),
    "nanopnp.validation.findings:LogFormatError": (
        "raised only by the VER-63 findings-log check, which catches it and returns it as one of "
        "the log's errors; no command of the CLI reads a findings log"
    ),
    "nanopnp.validation.stability:FoldError": (
        "raised only when the VER-62 golden's merge script folds a recorded walk in; no command "
        "of the CLI reads or writes the number-stability golden"
    ),
    "nanopnp.mesh.gmsh_backend:GmshInitialisationError": (
        "an internal backend error caught by the Gmsh mesher entry and translated into "
        "MissingExtraError naming gmsh (D11 b); it never reaches the CLI directly, and "
        "MissingExtraError is already classified, as EXIT_CASE"
    ),
}


def classify(error: BaseException) -> int:
    """Return the exit code for an exception: its class's code, or the unexpected-error code."""
    for klass in type(error).__mro__:
        code = EXIT_CODES.get(f"{klass.__module__}:{klass.__qualname__}")
        if code is not None:
            return code
    return EXIT_UNEXPECTED

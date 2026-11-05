"""The validate command: case checks and the COMSOL comparison harness."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.cli.common import _common, _emit, _store
from nanopnp.core.errors import EXIT_OK
from nanopnp.core.public import __version__

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.cli.common import Subparsers
    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.validation.comsol import Golden
    from nanopnp.validation.probe import ProbeDocument, ProbeGrid
    from nanopnp.validation.runs import ReopenedRun


def _validate(args: argparse.Namespace) -> int:
    actions = {
        "case": _validate_case,
        "export-grid": _validate_export_grid,
        "case-hash": _validate_case_hash,
        "ingest-golden": _validate_ingest_golden,
        "export-golden": _validate_export_golden,
        "compare": _validate_compare,
        "report": _validate_report,
    }
    return actions[args.action](args)


def _validate_case(args: argparse.Namespace) -> int:
    from nanopnp.api.case import Case
    from nanopnp.api.session import Session

    case = Case.load(args.case)
    checked = Session(write=False).check(case, files=not getattr(args, "schema_only", False))
    resolved = checked.resolved
    stages = checked.stages
    payload: dict[str, Canonicalisable] = {
        "case": case.name,
        "valid": True,
        "model": resolved.model,
        "stabilisation": resolved.stabilisation,
        "stages": list(stages),
    }
    lines = [
        f"case          {case.name}: valid",
        f"model         {resolved.model}",
        f"stabilisation {resolved.stabilisation}",
        f"stages        {' '.join(stages)}",
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_export_grid(args: argparse.Namespace) -> int:
    from nanopnp.validation.probe import load_probe

    document = load_probe(args.probe)
    text = document.write_comsol_axes()
    if args.output is not None:
        Path(args.output).write_text(text, encoding="utf-8")
    payload: dict[str, Canonicalisable] = {
        "probe": document.name,
        "probe_hash": document.hash,
        "points": document.count,
        "patches": [patch.summary() for patch in document.patches],
        "output": None if args.output is None else str(args.output),
    }
    lines = [f"probe      {document.name}", f"probe_hash {document.hash}"]
    lines += [
        f"patch      {patch.name}: n_r {patch.n_r} x n_z {patch.n_z} = {patch.count} points"
        for patch in document.patches
    ]
    lines.append(f"points     {document.count}")
    if args.output is not None:
        lines.append(f"axes       {args.output}")
    elif not args.json:
        lines += ["", text.rstrip("\n")]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_case_hash(args: argparse.Namespace) -> int:
    from nanopnp.api.case import Case
    from nanopnp.api.session import Session
    from nanopnp.validation.comsol import case_identity

    case = Case.load(args.case)
    identity = case_identity(Session(write=False).check(case, files=False).resolved)
    payload: dict[str, Canonicalisable] = {"case": case.name, "case_hash": identity}
    _emit(payload, [f"case      {case.name}", f"case_hash {identity}"], as_json=args.json)
    return EXIT_OK


def _validate_ingest_golden(args: argparse.Namespace) -> int:
    from nanopnp.validation.comsol import ingest_golden, load_golden

    archive = ingest_golden(args.directory, probe=args.probe, destination=args.destination)
    golden = load_golden(archive)
    payload = dict(golden.summary())
    payload["archive"] = str(archive)
    lines = [
        f"archive     {archive}",
        f"golden_hash {golden.hash}",
        f"case        {golden.manifest.case} ({golden.manifest.refinement})",
        f"source      {golden.source}",
        f"fields      {', '.join(sorted(golden.values))}",
        "sign        "
        + (
            "flipped to the section 6.7 convention"
            if golden.current_sign_flipped
            else "as exported (cis)"
        ),
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_export_golden(args: argparse.Namespace) -> int:
    from nanopnp.validation.comsol import (
        GOLDEN_SCHEMA,
        GoldenManifest,
        export_golden,
    )

    document, sampled, resolved = _sampled_run(args)
    manifest = GoldenManifest.model_validate(
        {
            "schema": GOLDEN_SCHEMA,
            "case": resolved.case.name,
            "case_hash": _identity(resolved),
            "probe": document.name,
            "probe_hash": document.hash,
            "refinement": args.refinement,
            "source": "self",
            "comsol_version": f"nanopnp {__version__} (self-golden, no COMSOL)",
            "model_file": str(resolved.directory),
            "export_date": args.export_date,
            "fields": {name: {"expression": name, "unit": _unit(name)} for name in sorted(sampled)},
            "current_boundary": "the NUM-24 domain indicator, not a boundary",
            "current_sign_reference": "cis",
            "quantities": _self_quantities(resolved.quantities),
        }
    )
    archive = export_golden(
        sampled, manifest, args.destination, tables=document if args.tables else None
    )
    payload: dict[str, Canonicalisable] = {
        "archive": str(archive),
        "case": manifest.case,
        "golden_source": "self",
        "fields": sorted(sampled),
    }
    _emit(
        payload,
        [
            f"archive {archive}",
            f"case    {manifest.case}",
            "source  self -- this golden tests the harness and nothing else",
            f"fields  {', '.join(sorted(sampled))}",
        ],
        as_json=args.json,
    )
    return EXIT_OK


def _validate_compare(args: argparse.Namespace) -> int:
    from nanopnp.validation.compare import (
        compare_fields,
        compare_quantities,
        unavailable_quantities,
        zero_reference_quantities,
    )
    from nanopnp.validation.comsol import load_golden

    document, sampled, resolved = _sampled_run(args)
    golden = load_golden(args.golden)
    golden.check_case(_identity(resolved))
    golden.check_probe(document)
    grid = _probe_grid(document, resolved)
    fields = compare_fields(sampled, golden, grid)
    quantities = compare_quantities(resolved.quantities, golden.quantities)
    zero_reference = zero_reference_quantities(resolved.quantities, golden.quantities)
    payload: dict[str, Canonicalisable] = {
        "run": str(resolved.directory),
        "golden_hash": golden.hash,
        "golden_source": golden.source,
        "current_sign_flipped": golden.current_sign_flipped,
        "fields": [entry.summary() for entry in fields],
        "quantities": [entry.summary() for entry in quantities],
        "unavailable_fields": list(golden.unavailable(sorted(sampled))),
        "unavailable_quantities": list(
            unavailable_quantities(resolved.quantities, golden.quantities)
        ),
        "zero_reference_quantities": zero_reference,
    }
    lines = [
        f"run          {resolved.directory}",
        f"golden       {golden.hash[:12]} ({golden.source}, {golden.manifest.refinement})",
    ]
    lines += [
        f"{entry.field:<12} rel_L2_r {entry.rel_L2_r:.4e}  rel_l2 {entry.rel_l2:.4e}  "
        f"max {entry.max_abs_rel:.4e} at (r, z) = "
        f"({entry.max_at_nm[0]:.4g}, {entry.max_at_nm[1]:.4g}) nm"
        for entry in fields
    ]
    lines += [f"{entry.name:<12} {entry.relative:+.4e} relative" for entry in quantities]
    lines += [
        f"{name:<12} golden is zero; relative error undefined (ours {value:.4e})"
        for name, value in zero_reference.items()
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_report(args: argparse.Namespace) -> int:
    from nanopnp.sweep.collect import read_members
    from nanopnp.sweep.plan import read_plan
    from nanopnp.validation.attribution import (
        LADDER,
        LadderError,
        RungOutcome,
        attribute,
        write_report,
    )
    from nanopnp.validation.compare import (
        compare_fields,
        compare_quantities,
        zero_reference_quantities,
    )
    from nanopnp.validation.comsol import load_golden
    from nanopnp.validation.probe import load_probe
    from nanopnp.validation.runs import reopen

    document = load_probe(args.probe)
    plan = read_plan(args.plan)
    golden = load_golden(args.golden)
    golden.check_probe(document)
    directory = Path(args.plan).parent
    store = None if args.store is None else _store(args)

    by_rung: dict[int, RungOutcome] = {}
    fields_sampled: list[str] = []
    # Every rung is the golden's case on one mesh, so any rung's grid carries the masks the
    # norms were taken over.
    rung_grid: ProbeGrid | None = None
    for member in read_members(directory):
        plan.point(member.index)  # refuses a member this plan does not enumerate
        rung_index = _rung_of(member.assignments)
        if member.status != "ok" or member.directory is None:
            continue
        if rung_index is None or rung_index in by_rung:
            continue
        resolved = reopen(member.directory, store=store)
        if _identity(resolved) != golden.manifest.case_hash:
            continue
        grid = rung_grid = _probe_grid(document, resolved)
        sampled = _sample(resolved, grid)
        fields_sampled = sorted(sampled)
        by_rung[rung_index] = RungOutcome(
            rung=LADDER[rung_index],
            golden_hash=golden.hash,
            probe_hash=golden.manifest.probe_hash,
            case_hash=golden.manifest.case_hash,
            fields=compare_fields(sampled, golden, grid),
            quantities=compare_quantities(resolved.quantities, golden.quantities),
            stabilisation_currents_A=_stabilisation_currents(resolved.quantities),
            zero_reference=zero_reference_quantities(resolved.quantities, golden.quantities),
        )
    missing = [rung.name for rung in LADDER if rung.index not in by_rung]
    if missing:
        raise LadderError(
            f"{directory} holds no completed member for rung(s) {', '.join(missing)} of the "
            "golden's case. The ladder attributes a discrepancy by differences between adjacent "
            "rungs, so a missing one does not make the remaining deltas mean less -- it makes "
            "them mean something else. Run the sweep to completion first"
        )
    assert rung_grid is not None  # four rungs were found, and each built its grid
    report = attribute(
        [by_rung[index] for index in range(len(LADDER))],
        case=golden.manifest.case,
        golden=golden,
        reference_errors=_reference_errors(args, document, golden, rung_grid),
        sampled_fields=fields_sampled,
    )
    json_path, markdown = write_report(report, args.output or directory)
    payload = dict(report.summary())
    payload["files"] = [str(json_path), str(markdown)]
    _emit(payload, [report.markdown()], as_json=args.json)
    return EXIT_OK


def _rung_of(assignments: Mapping[str, Canonicalisable]) -> int | None:
    from nanopnp.validation.attribution import LADDER

    for rung in LADDER:
        if all(assignments.get(path) == value for path, value in rung.assignments().items()):
            return rung.index
    return None


def _reference_errors(
    args: argparse.Namespace, document: ProbeDocument, golden: Golden, grid: ProbeGrid
) -> dict[str, float] | None:
    from nanopnp.validation.attribution import reference_error
    from nanopnp.validation.comsol import load_golden

    if args.refined is None:
        return None
    refined = load_golden(args.refined)
    refined.check_probe(document)
    return reference_error(golden, refined, grid)


def _identity(run: ReopenedRun) -> str:
    from nanopnp.validation.comsol import case_identity

    return case_identity(run.resolved, recorded=run.upstream)


def _unit(field: str) -> str:
    from nanopnp.validation.comsol import field_unit

    return field_unit(field)


def _self_quantities(recorded: Mapping[str, Canonicalisable]) -> dict[str, Canonicalisable]:
    from nanopnp.validation.runs import RunError

    wanted = ("bias_V", "current_A", "currents_A", "transport_number", "conductance_S", "eof_m3_s")
    block = {key: recorded.get(key) for key in wanted if recorded.get(key) is not None}
    absent = [key for key in ("bias_V", "current_A") if key not in block]
    if absent:
        raise RunError(
            f"the run records no {' or '.join(absent)}, which a golden manifest must declare. The "
            "stage-11 summary carries both, so this run stopped before the quantities of interest "
            "were extracted; re-run it with 'current' among its outputs"
        )
    return block


def _stabilisation_currents(
    recorded: Mapping[str, Canonicalisable],
) -> Mapping[str, float] | None:
    value = recorded.get("stabilisation_currents_A")
    return dict(value) if isinstance(value, dict) else None


def _probe_grid(document: ProbeDocument, resolved: ReopenedRun) -> ProbeGrid:
    from nanopnp.validation.compare import probe_domains
    from nanopnp.validation.probe import ProbeGrid

    return ProbeGrid.on_mesh(
        document, resolved.solution.space.mesh, probe_domains(resolved.solution)
    )


def _sample(resolved: ReopenedRun, grid: ProbeGrid) -> dict[str, np.ndarray]:
    from nanopnp.validation.compare import sample_on_probe

    return sample_on_probe(resolved.solution, grid, scales=resolved.scales)


def _sampled_run(
    args: argparse.Namespace,
) -> tuple[ProbeDocument, dict[str, np.ndarray], ReopenedRun]:
    from nanopnp.validation.probe import load_probe
    from nanopnp.validation.runs import reopen

    document = load_probe(args.probe)
    resolved = reopen(args.run, store=None if args.store is None else _store(args))
    grid = _probe_grid(document, resolved)
    return document, _sample(resolved, grid), resolved


def register(subparsers: Subparsers) -> None:
    """Add the validate subcommand with its actions."""
    validate = subparsers.add_parser(
        "validate", help="check a case file; the Tier-3 COMSOL comparison harness (section 7.4)"
    )
    steps = validate.add_subparsers(dest="action", required=True)

    checked = _common(
        steps.add_parser("case", help="check a case file as a run would, without solving it")
    )
    checked.add_argument("case", type=Path, help="the case file")
    checked.add_argument(
        "--schema-only",
        action="store_true",
        help="validate case document schema and resolution semantics only without "
        "checking disk files",
    )
    checked.set_defaults(handler=_validate)

    # %% throughout the help strings: argparse percent-formats help text, and a bare %G raises.
    grid = _common(steps.add_parser("export-grid", help="print the %%Grid axes COMSOL is given"))
    grid.add_argument("probe", type=Path, help="the nanopnp/probe/v0.5 document")
    grid.add_argument("--output", type=Path, default=None, help="write the axes to this file")
    grid.set_defaults(handler=_validate)

    identity = _common(
        steps.add_parser("case-hash", help="print the case_hash a golden must declare")
    )
    identity.add_argument("case", type=Path, help="a frozen case file")
    identity.set_defaults(handler=_validate)

    ingest = _common(
        steps.add_parser("ingest-golden", help="archive a directory of exported tables")
    )
    ingest.add_argument("directory", type=Path, help="holds manifest.yaml and the %%Grid tables")
    ingest.add_argument("--probe", type=Path, required=True, help="the probe document")
    ingest.add_argument("--destination", type=Path, default=None, help="where to write the archive")
    ingest.set_defaults(handler=_validate)

    self_golden = _common(
        steps.add_parser("export-golden", help="write one of our own runs as a self-golden")
    )
    self_golden.add_argument("run", type=Path, help="a finished run directory")
    self_golden.add_argument("--probe", type=Path, required=True, help="the probe document")
    self_golden.add_argument("--destination", type=Path, required=True, help="output directory")
    self_golden.add_argument("--store", type=Path, default=None, help="artefact store root")
    self_golden.add_argument(
        "--refinement", default="published", choices=("published", "refined_1"), help="VAL-04 level"
    )
    # Required, not defaulted: a blank export_date is refused by the manifest and would exit
    # 1; argparse's exit 2 is right.
    self_golden.add_argument(
        "--export-date", required=True, help="date recorded in the manifest, e.g. 2026-09-18"
    )
    self_golden.add_argument(
        "--tables", action="store_true", help="also write the %%Grid transport tables"
    )
    self_golden.set_defaults(handler=_validate)

    against = _common(steps.add_parser("compare", help="compare one run against one golden"))
    against.add_argument("run", type=Path, help="a finished run directory")
    against.add_argument("--probe", type=Path, required=True, help="the probe document")
    against.add_argument("--golden", type=Path, required=True, help="an archived golden")
    against.add_argument("--store", type=Path, default=None, help="artefact store root")
    against.set_defaults(handler=_validate)

    ladder = _common(steps.add_parser("report", help="the four-rung attribution ladder"))
    ladder.add_argument("plan", type=Path, help="the ladder sweep's plan file")
    ladder.add_argument("--probe", type=Path, required=True, help="the probe document")
    ladder.add_argument("--golden", type=Path, required=True, help="the published-mesh golden")
    ladder.add_argument(
        "--refined", type=Path, default=None, help="the refined golden, for VAL-04's Delta_ref"
    )
    ladder.add_argument("--store", type=Path, default=None, help="artefact store root")
    ladder.add_argument("--output", type=Path, default=None, help="where to write the report")
    ladder.set_defaults(handler=_validate)

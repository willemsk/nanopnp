"""Text readings of a run, a sweep dataset and a stored artefact, for `nanopnp inspect`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from nanopnp.io.manifest import GROUPS

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from pathlib import Path

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.artefact import SweepArtefact
    from nanopnp.pipeline.run import RecordedRun

__all__ = [
    "DATASET_QUANTITIES",
    "SECTIONS",
    "artefact_lines",
    "dataset_lines",
    "format_value",
    "run_lines",
    "section_lines",
    "stage_line",
]

SECTIONS: tuple[str, ...] = ("case", *GROUPS)

DATASET_QUANTITIES: tuple[str, ...] = ("current_A", "conductance_S", "transport_number", "eof_m3_s")

_LABEL = 10


def format_value(value: object) -> str:
    """Return a quantity's value as the CLI prints it: floats to six significant figures."""
    if isinstance(value, float):
        if value == 0.0:
            return "0.0"
        return f"{value:.6g}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(format_value(x) for x in value) + "]"
    if isinstance(value, Mapping):
        return "{" + ", ".join(f"{k!r}: {format_value(v)}" for k, v in sorted(value.items())) + "}"
    return str(value)


def stage_line(number: int, name: str, cached: bool, digest: str, seconds: float) -> str:
    """Return one stage's line, as `nanopnp run` prints it."""
    return (
        f"stage {number:>2} {name:<11} {'cached' if cached else 'computed':<8} "
        f"{digest[:12]} {seconds:8.3f} s"
    )


def _label(label: str, text: str) -> str:
    return f"{label:<{_LABEL - 1}} {text}"


def _not_run(group: object) -> str | None:
    if isinstance(group, Mapping) and group.get("status") == "not run":
        return str(group.get("reason", ""))
    return None


def _deviation_lines(deviations: Mapping[str, Canonicalisable], label: str) -> list[str]:
    lines = [
        _label(
            label,
            f"{entry['path']}: {format_value(entry['value'])} "
            f"(validated default {format_value(entry['validated_default'])})",
        )
        for entry in deviations.get("switches", [])
    ]
    lines += [
        _label(label, f"{entry['source']}: {entry['description']}")
        for entry in deviations.get("contributed", [])
    ]
    return lines


def _rung_line(rung: Mapping[str, Canonicalisable]) -> str:
    newton = rung.get("newton")
    if isinstance(newton, Mapping):
        steps = (
            f"{newton.get('iterations')} iterations, "
            f"damping {format_value(newton.get('minimum_damping_used'))}"
        )
    else:
        steps = "linear"
    return _label(
        "rung",
        f"{rung.get('rung')}  {rung.get('model')}  {steps}  {rung.get('seconds', 0.0):.3f} s",
    )


def run_lines(recorded: RecordedRun) -> list[str]:
    """Return the reading of a run: model, stages, rungs, quantities and deviations."""
    document = recorded.manifest.document()
    solver = document["solver"]
    stabilisation = document["stabilisation"]
    lines = [
        _label("run", str(recorded.directory)),
        _label("case", f"{recorded.document.name} {recorded.manifest.case_hash[:12]}"),
        _label("model", f"{solver['model']}, stabilisation {stabilisation['mode']}"),
    ]
    lines += [
        stage_line(stage.number, stage.name, stage.cached, stage.hash, stage.seconds)
        for stage in recorded.stages
    ]
    ladder = solver["run"]
    reason = _not_run(ladder)
    if reason is not None:
        lines.append(_label("rungs", f"not run: {reason}"))
    else:
        lines += [_rung_line(rung) for rung in ladder.get("rungs", [])]
    for group in GROUPS:
        if group != "solver":
            reason = _not_run(document[group])
            if reason is not None:
                lines.append(_label("not run", f"{group}: {reason}"))
    lines += [
        f"{name:<20} {format_value(value)}" for name, value in sorted(recorded.quantities.items())
    ]
    found = _deviation_lines(document["deviations"], "deviation")
    lines += found or [_label("deviations", "none")]
    return lines


def _yaml_lines(value: object, indent: int) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(value, Mapping):
        for key, item in sorted(value.items()):
            if isinstance(item, Mapping) and item:
                lines.append(f"{pad}{key}:")
                lines += _yaml_lines(item, indent + 1)
            elif isinstance(item, str) and "\n" in item:
                lines.append(f"{pad}{key}: |")
                lines += [f"{pad}  {line}" for line in item.rstrip("\n").split("\n")]
            elif isinstance(item, (list, tuple)) and any(
                isinstance(entry, Mapping) for entry in item
            ):
                lines.append(f"{pad}{key}:")
                for entry in item:
                    nested = _yaml_lines(entry, indent + 2)
                    if nested:
                        lines.append(f"{pad}  - {nested[0].lstrip()}")
                        lines += nested[1:]
                    else:
                        lines.append(f"{pad}  - {format_value(entry)}")
            else:
                lines.append(f"{pad}{key}: {format_value(item)}")
    else:
        lines.append(f"{pad}{format_value(value)}")
    return lines


def section_lines(recorded: RecordedRun, name: str) -> list[str]:
    """Return one manifest group, or the case, as indented ``key: value`` lines."""
    group = recorded.manifest.document()[name]
    return [f"{name}:", *_yaml_lines(group, 1)]


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    widths = [max(len(cell) for cell in column) for column in zip(header, *rows, strict=True)]
    return [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in (header, *rows)
    ]


def _columns(paths: Sequence[str]) -> dict[str, str]:
    last: dict[str, int] = {}
    for path in paths:
        tail = path.rsplit(".", 1)[-1]
        last[tail] = last.get(tail, 0) + 1
    return {
        path: path if last[path.rsplit(".", 1)[-1]] > 1 else path.rsplit(".", 1)[-1]
        for path in paths
    }


def _cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def dataset_lines(path: Path, dataset: SweepArtefact) -> list[str]:
    """Return the reading of a sweep dataset: its points as a table, then its rectification."""
    summary = dataset.summary
    rows: list[Mapping[str, Canonicalisable]] = list(summary.get("rows", []))
    counts = ", ".join(f"{count} {status}" for status, count in dict(summary["counts"]).items())
    lines = [f"dataset   {path}   {summary['points']} points: {counts or 'none'}"]
    paths = sorted({key for row in rows for key in dict(row["assignments"])})
    columns = _columns(paths)
    present = [
        name
        for name in DATASET_QUANTITIES
        if any(isinstance(dict(row["quantities"] or {}).get(name), int | float) for row in rows)
    ]
    header = ["id", "status", *[columns[key] for key in paths], *present]
    body = [
        [
            str(row["id"]),
            str(row["status"]),
            *[_cell(dict(row["assignments"]).get(key)) for key in paths],
            *[_cell(dict(row["quantities"] or {}).get(name)) for name in present],
        ]
        for row in rows
    ]
    lines += _table(header, body)
    ratios = list(summary.get("rectification", []))
    if ratios:
        by_id = {str(row["id"]): row for row in rows}
        held = [key for key in paths if not key.endswith(".bias_V") and key != "bias_V"]
        lines.append("rectification")
        lines += _table(
            [*[columns[key] for key in held], "bias_V", "rectification"],
            [
                [
                    *[
                        _cell(dict(by_id[str(entry["forward_id"])]["assignments"]).get(key))
                        for key in held
                    ],
                    _cell(entry["bias_V"]),
                    _cell(entry["rectification"]),
                ]
                for entry in ratios
            ],
        )
    lines += [f"note  {note}" for note in summary.get("rectification_notes", [])]
    return lines


def artefact_lines(path: Path, meta: Mapping[str, Canonicalisable]) -> list[str]:
    """Return the reading of a stored artefact: its schema, key, parameters and summary."""
    lines = [
        f"{path}",
        _label("schema", str(meta.get("schema"))),
        _label("key", str(meta.get("hash"))),
    ]
    for name in ("parameters", "summary"):
        lines.append(f"{name}:")
        lines += _yaml_lines(meta.get(name) or {}, 1)
    return lines

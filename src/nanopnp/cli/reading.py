"""Text readings of a run, a sweep dataset and a stored artefact, for `nanopnp inspect`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from nanopnp.io.manifest import GROUPS

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from pathlib import Path

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.artefact import SweepArtefact
    from nanopnp.pipeline.run import RecordedRun, StageRecord

__all__ = [
    "DATASET_QUANTITIES",
    "SECTIONS",
    "artefact_lines",
    "comparison",
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


def stage_line(record: StageRecord) -> str:
    """Return one stage's line, as `nanopnp run` prints it."""
    return (
        f"stage {record.number:>2} {record.name:<11} "
        f"{'cached' if record.cached else 'computed':<8} {record.hash[:12]} {record.seconds:8.3f} s"
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
    lines += [stage_line(stage) for stage in recorded.stages]
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


def _flatten(value: object, prefix: str, into: dict[str, Canonicalisable], *, lists: bool) -> None:
    if isinstance(value, Mapping) and value:
        for key, item in value.items():
            _flatten(item, f"{prefix}.{key}" if prefix else str(key), into, lists=lists)
    elif lists and isinstance(value, (list, tuple)) and value:
        for index, item in enumerate(value):
            _flatten(item, f"{prefix}.{index}", into, lists=lists)
    else:
        into[prefix] = value


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _relative(left: object, right: object) -> float | None:
    a, b = _number(left), _number(right)
    if a is None or b is None or a == 0.0:
        return None
    return (b - a) / abs(a)


def comparison(
    left: RecordedRun, right: RecordedRun
) -> tuple[dict[str, Canonicalisable], list[str]]:
    """Return two runs compared: the case fields that differ, each one's deviations, the quantities.

    Returns
    -------
    The ``--json`` payload and the text lines.
    """
    cases: list[dict[str, Canonicalisable]] = []
    flat_left: dict[str, Canonicalisable] = {}
    flat_right: dict[str, Canonicalisable] = {}
    _flatten(left.document.model_dump(mode="json"), "", flat_left, lists=True)
    _flatten(right.document.model_dump(mode="json"), "", flat_right, lists=True)
    for path in sorted(set(flat_left) | set(flat_right)):
        a, b = flat_left.get(path), flat_right.get(path)
        if a != b:
            cases.append({"path": path, "left": a, "right": b})

    def listed(run: RecordedRun) -> list[Canonicalisable]:
        block = run.manifest.document()["deviations"]
        return [*block["switches"], *block["contributed"]]

    quantities_left: dict[str, Canonicalisable] = {}
    quantities_right: dict[str, Canonicalisable] = {}
    _flatten(dict(left.quantities), "", quantities_left, lists=False)
    _flatten(dict(right.quantities), "", quantities_right, lists=False)
    quantities = [
        {
            "name": name,
            "left": quantities_left.get(name),
            "right": quantities_right.get(name),
            "relative_difference": _relative(quantities_left.get(name), quantities_right.get(name)),
        }
        for name in sorted(set(quantities_left) | set(quantities_right))
    ]
    payload: dict[str, Canonicalisable] = {
        "left": str(left.directory),
        "right": str(right.directory),
        "case": cases,
        "deviations": {"left": listed(left), "right": listed(right)},
        "quantities": quantities,
    }

    lines = [_label("left", str(left.directory)), _label("right", str(right.directory))]
    lines += [
        _label(
            "case",
            f"{entry['path']}: {format_value(entry['left'])} -> {format_value(entry['right'])}",
        )
        for entry in cases
    ] or [_label("case", "identical")]
    for side, run in (("left", left), ("right", right)):
        found = _deviation_lines(run.manifest.document()["deviations"], f"deviation {side}")
        lines += found or [_label("deviations", f"{side} none")]
    lines += _table(
        ["quantity", "left", "right", "(right - left)/|left|"],
        [
            [
                str(entry["name"]),
                _cell(entry["left"]),
                _cell(entry["right"]),
                _cell(entry["relative_difference"]),
            ]
            for entry in quantities
        ],
    )
    return payload, lines

"""Read a solved 2WCD analysis project and write the data the tree round's boards draw.

`uv run python extract.py <analysis project> <out.json>`. The project is the one
`.claude/scripts/gui/render_shell.py --only analysis` builds into its cache: 2WCD's study solved at
+50 mV, swept over the bias, and a variant with one ASP neutral solved in a study of its own. Every
number is read through the library (`post/fields.py`, `plot/data.py`), as the shell reads it.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from nanopnp.api.project import Project
from nanopnp.gui.web.analysis import AnalysisModel, RunChoice, pore_window
from nanopnp.plot.data import fluid_outline_nm
from nanopnp.post.fields import field_at, field_grid, field_unit, quantity_name

GRID_CELLS = 16_000
"""The cells of each map's grid over the pore's close-up: small enough for a committed page."""
ARROWS = (9, 26)
"""The arrows' grid, r by z."""
CUT_POINTS = 240
REVOLVED_CELLS = 2_400
"""The cells of the (r, z) grid the 3D revolution turns about the axis."""


def _round(value: float) -> float | None:
    if not math.isfinite(value):
        return None
    return float(f"{value:.4g}")


def _rows(values: np.ndarray) -> list[list[float | None]]:
    return [[_round(float(v)) for v in row] for row in values]


def _list(values: np.ndarray) -> list[float | None]:
    return [_round(float(v)) for v in values]


def _species(fields: Any) -> list[str]:  # noqa: ANN401 - SolutionFields
    keys = {*fields.whole[2], *fields.fluid[2]}
    return sorted(key for key in keys if key.endswith("_mol_m3"))


def _grid(fields: Any, quantity: str, window: tuple[float, ...], cells: int) -> dict[str, Any]:  # noqa: ANN401
    r, z, values = field_grid(fields, quantity, window_nm=window, cells=cells)
    return {
        "name": quantity_name(quantity),
        "unit": field_unit(quantity),
        "r": _list(r),
        "z": _list(z),
        "v": _rows(values),
    }


def _own_run(choices: tuple[RunChoice, ...]) -> RunChoice:
    return next(choice for choice in choices if choice.sweep is None)


def main(folder: Path, out: Path) -> None:
    project = Project.open(folder)
    model = AnalysisModel(project)
    studies = model.studies()
    swept = next(study for study in studies if project.sweeps(study))
    variant = next(study for study in studies if study != swept)
    choices = model.choices(swept)
    first = _own_run(choices)
    second = _own_run(model.choices(variant))
    fields = model.fields(first.directory)
    other = model.fields(second.directory)
    if fields is None or other is None:
        raise SystemExit("a run's fields file is not written: render the analysis group first")
    window = pore_window(fields, other)
    species = _species(fields)
    maps = {
        "potential": _grid(fields, "potential", window, GRID_CELLS),
        **{key: _grid(fields, key, window, GRID_CELLS) for key in species},
        "p_Pa": _grid(fields, "p_Pa", window, GRID_CELLS),
    }
    mirrored = _grid(other, "potential", window, GRID_CELLS)
    r_a = np.linspace(window[0] + 0.25, window[1] - 0.25, ARROWS[0])
    z_a = np.linspace(window[2] + 0.5, window[3] - 0.5, ARROWS[1])
    grid_r, grid_z = np.meshgrid(r_a, z_a)
    arrows = {
        "r": _list(grid_r.ravel()),
        "z": _list(grid_z.ravel()),
        "ur": _list(field_at(fields, "u_r", grid_r, grid_z).ravel()),
        "uz": _list(field_at(fields, "u_z", grid_r, grid_z).ravel()),
        "unit": "m/s",
    }
    segments = fluid_outline_nm(fields)
    inside = (
        (np.maximum(segments[:, 0], segments[:, 2]) >= window[0])
        & (np.minimum(segments[:, 0], segments[:, 2]) <= window[1] + 2.0)
        & (np.maximum(segments[:, 1], segments[:, 3]) >= window[2] - 2.0)
        & (np.minimum(segments[:, 1], segments[:, 3]) <= window[3] + 2.0)
    )
    outline = [_list(row) for row in segments[inside]]
    z_cut = np.linspace(window[2], window[3], CUT_POINTS)
    r_cut = np.zeros_like(z_cut)
    cut = {
        "z": _list(z_cut),
        "series": [
            {
                "label": label,
                "quantity": quantity,
                "name": quantity_name(quantity),
                "unit": field_unit(quantity),
                "v": _list(field_at(run, quantity, r_cut, z_cut)),
            }
            for label, run in (("+50 mV", fields), ("+50 mV, ASP neutral", other))
            for quantity in ("potential", *species)
        ],
    }
    points = sorted(
        (choice for choice in choices if choice.bias_V is not None and choice.current_A),
        key=lambda choice: choice.bias_V or 0.0,
    )
    probe = (0.0, 0.0)
    iv = []
    for choice in points:
        member = model.fields(choice.directory)
        at = (
            None
            if member is None
            else _round(
                float(field_at(member, species[0], np.array([probe[0]]), np.array([probe[1]]))[0])
            )
        )
        iv.append(
            {
                "bias_mV": _round((choice.bias_V or 0.0) * 1e3),
                "current_nA": _round((choice.current_A or 0.0) * 1e9),
                "conductance_nS": None
                if choice.conductance_S is None
                else _round(choice.conductance_S * 1e9),
                "probe": at,
                "label": choice.label,
            }
        )
    probes = [
        {
            "r_nm": r_nm,
            "z_nm": z_nm,
            **{
                quantity: _round(
                    float(field_at(fields, quantity, np.array([r_nm]), np.array([z_nm]))[0])
                )
                for quantity in ("potential", *species)
            },
        }
        for r_nm, z_nm in ((0.0, 0.0), (1.2, 3.0))
    ]
    revolved = {
        "potential": _grid(fields, "potential", window, REVOLVED_CELLS),
        species[0]: _grid(fields, species[0], window, REVOLVED_CELLS),
    }
    data = {
        "source": "2WCD, example 07's case, solved by render_shell.py's analysis group",
        "window_nm": [_round(value) for value in window],
        "runs": {
            "first": {"label": "+50 mV", "folder": first.directory.name[:8]},
            "second": {"label": "+50 mV, ASP neutral", "folder": second.directory.name[:8]},
            "study": swept,
            "variant": variant,
        },
        "species": species,
        "maps": maps,
        "mirrored": mirrored,
        "arrows": arrows,
        "outline": outline,
        "cut": cut,
        "iv": iv,
        "probe_nm": list(probe),
        "probes": probes,
        "quantities": model.quantity_rows(first.directory),
        "revolved": revolved,
    }
    text = json.dumps(data, separators=(",", ":"))
    # A page opened from a file cannot fetch JSON, so the boards load it as a script.
    out.write_text(f"window.TREE = {text};\n" if out.suffix == ".js" else text, encoding="utf-8")
    print(f"wrote {out}: {out.stat().st_size / 1e3:.0f} kB", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))

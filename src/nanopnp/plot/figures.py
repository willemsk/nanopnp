"""One figure per stage artefact, and the sweep's, each built without pyplot."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from nanopnp.materials.electrolyte import MOLAR_PER_SI
from nanopnp.mesh.sizing import case_debye_record
from nanopnp.plot import data, panels
from nanopnp.plot.data import DISPLAY, axis_label
from nanopnp.post.export import solution_fields

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np
    from matplotlib.axes import Axes
    from matplotlib.collections import QuadMesh
    from matplotlib.figure import Figure

    from nanopnp.io.artefact import Artefact, StageInputs

__all__ = [
    "charge_figure",
    "contour_figure",
    "density_figure",
    "materials_figure",
    "mesh_figure",
    "protonation_figure",
    "qoi_figure",
    "region_figure",
    "solve_figure",
    "structure_figure",
    "sweep_figure",
    "symmetry_figure",
    "text_figure",
]

NM = DISPLAY["length"].per_SI


def text_figure(message: str) -> Figure:
    """Return a figure holding only ``message``, for an artefact with nothing to draw."""
    from matplotlib.figure import Figure

    figure = Figure(figsize=(6.0, 1.6))
    figure.text(0.5, 0.5, message, ha="center", va="center", wrap=True)
    return figure


def _absent(artefact: Artefact, stage: str, what: str) -> Figure:
    return text_figure(
        f"{artefact.schema}: {what} is not stored here; "
        f"draw it from the run with result.figure({stage!r})"
    )


def _rz_axes(ax: Axes, *, equal: bool = True) -> None:
    ax.set_xlabel(axis_label("r", "length"))
    ax.set_ylabel(axis_label("z", "length"))
    if equal:
        ax.set_aspect("equal", adjustable="box")


def _mesh(
    ax: Axes, r: np.ndarray, z: np.ndarray, values: np.ndarray, *, cmap: str, alpha: float = 1.0
) -> QuadMesh:
    return ax.pcolormesh(r * NM, z * NM, values, shading="auto", cmap=cmap, alpha=alpha)


def structure_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 1: the atoms of the aligned ensemble at ``(r, z)``."""
    from matplotlib.figure import Figure

    atoms = data.structure_atoms(artefact)
    if atoms is None:
        return _absent(artefact, "structure", "the aligned ensemble")
    r, z = atoms
    figure = Figure(figsize=(4.5, 6.0), layout="constrained")
    ax = figure.subplots()
    ax.scatter(r * NM, z * NM, s=0.3, color="0.2", linewidths=0, rasterized=True)
    _rz_axes(ax)
    ax.set_title(f"atoms at r = hypot(x, y), {r.size} drawn")
    return figure


def density_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 2: the density map on its axial section ``y = 0``."""
    from matplotlib.figure import Figure

    section = data.density_section(artefact)
    if section is None:
        return _absent(artefact, "density", "the density map")
    x, z, values = section
    figure = Figure(figsize=(5.0, 6.0), layout="constrained")
    ax = figure.subplots()
    image = _mesh(ax, x, z, values, cmap="viridis")
    figure.colorbar(image, ax=ax, label=axis_label("union density", "density"))
    ax.set_xlabel(axis_label("x", "length"))
    ax.set_ylabel(axis_label("z", "length"))
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("density, axial section y = 0")
    return figure


def symmetry_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 3: the reduced map and its azimuthal variance."""
    from matplotlib.figure import Figure

    reduced = data.reduced_map(artefact)
    if reduced is None:
        return _absent(artefact, "symmetry", "the reduced map")
    figure = Figure(figsize=(8.0, 6.0), layout="constrained")
    left, right = figure.subplots(1, 2, sharey=True)
    r, z = reduced.r_nm * 1e-9, reduced.z_nm * 1e-9
    image = _mesh(left, r, z, reduced.mean, cmap="viridis")
    figure.colorbar(image, ax=left, label=axis_label("mean density", "density"))
    left.set_title("mean over the azimuth")
    _rz_axes(left)
    image = _mesh(right, r, z, reduced.cn_variance, cmap="magma")
    figure.colorbar(image, ax=right, label="Cₙ-averaged variance")
    right.set_title("azimuthal variance")
    right.set_xlabel(axis_label("r", "length"))
    right.set_aspect("equal", adjustable="box")
    return figure


def contour_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 4: the conditioned contour and its constriction, over the reduced map."""
    from matplotlib.figure import Figure

    polygon = data.contour_polygon_m(artefact)
    if polygon is None:
        return _absent(artefact, "contour", "the conditioned contour")
    figure = Figure(figsize=(4.5, 6.0), layout="constrained")
    ax = figure.subplots()
    reduced = None if inputs is None else inputs.upstream.get("symmetry")
    mapped = None if reduced is None else data.reduced_map(reduced)
    if mapped is not None:
        _mesh(ax, mapped.r_nm * 1e-9, mapped.z_nm * 1e-9, mapped.mean, cmap="Greys", alpha=0.6)
    closed = [*polygon, polygon[0]]
    ax.plot([p[0] * NM for p in closed], [p[1] * NM for p in closed], color="tab:blue", lw=1.5)
    panels.mark_constriction(ax, artefact)
    _rz_axes(ax)
    ax.set_title("conditioned pore contour")
    return figure


def region_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 5: the named regions of the model-frame geometry."""
    from matplotlib.figure import Figure

    drawing = data.region_drawing(artefact)
    if drawing is None:
        return _absent(artefact, "region", "the region record")
    figure = Figure(figsize=(5.0, 6.0), layout="constrained")
    ax = figure.subplots()
    radius = drawing.reservoir_radius_m * NM
    membrane = drawing.membrane_m * NM
    ax.fill(membrane[:, 0], membrane[:, 1], color="tab:orange", alpha=0.35, label="membrane")
    pore = [*drawing.pore_m, drawing.pore_m[0]]
    ax.fill([p[0] * NM for p in pore], [p[1] * NM for p in pore], color="tab:blue", alpha=0.3)
    ax.plot([p[0] * NM for p in pore], [p[1] * NM for p in pore], color="tab:blue", label="pore")
    if drawing.exclusion_m is not None:
        shell = [*drawing.exclusion_m, drawing.exclusion_m[0]]
        ax.plot(
            [p[0] * NM for p in shell],
            [p[1] * NM for p in shell],
            color="tab:green",
            ls="--",
            label="ion-exclusion shell",
        )
    ax.axvline(radius, color="0.4", lw=0.8, ls=":", label="reservoir radius")
    _rz_axes(ax)
    ax.legend(loc="upper right", fontsize="small")
    ax.set_title("regions in the model frame")
    return figure


def _debye_target_nm(artefact: Artefact, inputs: StageInputs | None) -> tuple[float | None, str]:
    if inputs is not None:
        return float(cast("float", case_debye_record(inputs.resolved)["debye_target_nm"])), ""
    # A mesh shared by sweep members records the salt of the member that meshed it first.
    sizing = artefact.summary.get("sizing")
    found = sizing.get("debye_target_nm") if isinstance(sizing, Mapping) else None
    return (None, "") if found is None else (float(found), "as meshed")


def mesh_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 6: the element edges, the whole domain by element size, and the lumen by SICN."""
    from matplotlib.figure import Figure

    elements = data.mesh_of(artefact, inputs)
    if elements is None:
        return _absent(artefact, "mesh", "the mesh (a supplied mesh is read from its file)")
    figure = Figure(figsize=(13.0, 6.5), layout="constrained")
    edges, whole, lumen = figure.subplots(1, 3)
    panels.plot_mesh(elements, ax=edges, edges_only=True)
    panels.plot_mesh(elements, ax=whole)
    debye_target_nm, note = _debye_target_nm(artefact, inputs)
    panels.plot_mesh(
        elements,
        ax=lumen,
        zoom_nm=elements.lumen_nm,
        debye_target_nm=debye_target_nm,
        debye_note=note,
    )
    return figure


def protonation_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 7's protonation: each titratable residue's charge."""
    from matplotlib.figure import Figure

    charges = data.protonation_charges(artefact)
    if charges is None:
        return _absent(artefact, "protonation", "the protonation table")
    figure = Figure(figsize=(9.0, 3.5), layout="constrained")
    ax = figure.subplots()
    colour = ["tab:red" if q < 0 else "tab:blue" for q in charges.charge_e]
    ax.bar(range(len(charges.charge_e)), charges.charge_e, color=colour, width=1.0)
    ax.axhline(0.0, color="k", lw=0.5)
    ax.set_xlabel("residue index")
    ax.set_ylabel("charge (e)")
    ax.set_title(f"residue charges, net {charges.charge_e.sum():+.1f} e")
    return figure


def charge_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 7's fields: the deposited charge about zero, and the solid fraction χ."""
    from matplotlib.figure import Figure

    grids = data.charge_grids(artefact)
    if not grids:
        return _absent(artefact, "charge", "a stored charge or ε_r grid")
    figure = Figure(figsize=(4.5 * len(grids), 6.0), layout="constrained")
    axes = list(figure.subplots(1, len(grids), squeeze=False)[0])
    if "charge" in grids:
        panels.plot_charge(grids, ax=axes.pop(0))
    solid = grids.get("solid_fraction")
    if solid is not None:
        ax = axes.pop(0)
        image = _mesh(ax, solid.r_m, solid.z_m, solid.values, cmap="Greys")
        image.set_clim(0.0, 1.0)
        ax.contour(solid.r_m * NM, solid.z_m * NM, solid.values, levels=[0.5], colors="tab:orange")
        figure.colorbar(image, ax=ax, label=f"{solid.quantity} ({solid.unit})")
        _rz_axes(ax)
        ax.set_title("solid fraction, χ = 0.5 drawn")
    return figure


def materials_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 8: each correction against the declared driver and the wall distance."""
    from matplotlib.figure import Figure

    if inputs is None:
        return _absent(artefact, "materials", "the correction models")
    electrolyte = inputs.resolved.electrolyte
    # Every species sits at the case's concentration in the bulk; the driver is formed from
    # them as the solve forms it: <c> = (1/n) sum c_i, or I, clamped to the fitted range.
    bulk_SI = inputs.resolved.concentration_M / MOLAR_PER_SI
    driver_M = float(electrolyte.average_concentration([bulk_SI] * len(electrolyte.species)))
    curves = data.correction_curves(
        electrolyte.corrections,
        driver=electrolyte.driver,
        concentration_M=driver_M,
        validity_M=electrolyte.validity_M,
    )
    if not curves:
        return text_figure("every correction is the none model: the factors are 1")
    figure = Figure(figsize=(8.0, 2.8 * len(curves)), layout="constrained")
    axes = figure.subplots(len(curves), 2, squeeze=False)
    per_M = 1.0
    for (left, right), curve in zip(axes, curves, strict=True):
        left.plot(curve.driver_M * per_M, curve.factor_vs_driver)
        left.axvspan(*curve.validity_M, color="0.9", zorder=0)
        left.axvline(curve.at_driver_M, color="tab:red", lw=1.0, ls="--")
        left.set_xlim(right=max(left.get_xlim()[1], 1.05 * curve.at_driver_M))
        left.annotate(
            f"operating {curve.at_driver_M:g} M",
            (curve.at_driver_M, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(3, -3),
            textcoords="offset points",
            va="top",
            color="tab:red",
            fontsize="small",
        )
        left.set_xlabel(f"{curve.driver_label} (M)")
        left.set_ylabel(f"{curve.name} factor")
        left.set_title(f"{curve.name}: {curve.model} (fitted range shaded)")
        right.plot(curve.distance_m * NM, curve.factor_vs_distance)
        right.set_xlabel(axis_label("distance d to the pore wall", "length"))
        right.set_title(f"at {curve.driver_label} = {curve.at_driver_M:g} M")
    return figure


def _convergence(figure: Figure, residual_ax: Axes, damping_ax: Axes, rungs: list[Any]) -> None:
    offset = 0
    for rung in rungs:
        steps = offset + rung.iteration
        residual_ax.semilogy(steps, rung.residual, marker=".", label=rung.name)
        damping_ax.plot(steps, rung.damping, marker=".", label=rung.name)
        offset = int(steps[-1])
    residual_ax.set_xlabel("Newton step, all rungs")
    residual_ax.set_ylabel("residual")
    residual_ax.legend(fontsize="small")
    damping_ax.set_xlabel("Newton step, all rungs")
    damping_ax.set_ylabel("damping")
    damping_ax.set_ylim(0.0, 1.05)


def solve_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 10: each solved field on its own panel, and the Newton history per rung."""
    from matplotlib.figure import Figure

    history = data.newton_history(artefact)
    rungs = None if history is None else [rung for rung in history if rung.iteration.size]
    summary: Mapping[str, Any] = artefact.summary
    fields = None if inputs is None else solution_fields(inputs, artefact)
    if fields is None and not rungs:
        return _absent(artefact, "solve", "the fields or the Newton history")
    model = fields.model if fields is not None else "solve"
    title = f"{model}, stabilisation: {summary.get('stabilisation', 'not recorded')}"
    quantities: list[str] = []
    if fields is not None:
        held = {*fields.whole[2], *fields.fluid[2]}
        quantities += ["potential"] if "phi_V" in held else []
        quantities += sorted(k for k in held if k.endswith("_mol_m3"))
        quantities += ["u_z"] if "u_m_s" in held else []
        quantities += ["p_Pa"] if "p_Pa" in held else []
    columns = max(1, min(4, len(quantities)))
    rows = -(-len(quantities) // columns) + (1 if rungs else 0)
    figure = Figure(figsize=(4.2 * columns, 5.0 * rows), layout="constrained")
    figure.suptitle(title)
    grid = figure.add_gridspec(rows, columns)
    if fields is not None:
        for index, quantity in enumerate(quantities):
            ax = figure.add_subplot(grid[index // columns, index % columns])
            panels.plot_field(fields, quantity, ax=ax, relative=True)
    if rungs:
        last = rows - 1
        bottom = grid[last, :].subgridspec(1, 2)
        residual_ax = figure.add_subplot(bottom[0, 0])
        damping_ax = figure.add_subplot(bottom[0, 1])
        _convergence(figure, residual_ax, damping_ax, rungs)
    elif fields is not None:
        why = "not recorded for this solve" if history is None else "not reported by this model"
        figure.text(0.5, 0.01, f"Newton history {why}", ha="center")
    return figure


def _flatten(prefix: str, value: object, rows: list[tuple[str, str]]) -> None:
    if isinstance(value, Mapping):
        for key, inner in value.items():
            _flatten(f"{prefix}.{key}" if prefix else str(key), inner, rows)
    elif isinstance(value, float):
        rows.append((prefix, f"{value:.6g}"))
    elif isinstance(value, bool | int | str) or (isinstance(value, list) and len(value) <= 4):
        rows.append((prefix, str(value)))


def qoi_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 11: the quantities of interest as a table."""
    from matplotlib.figure import Figure

    rows: list[tuple[str, str]] = []
    _flatten("", dict(artefact.summary), rows)
    if not rows:
        return _absent(artefact, "qoi", "any quantity")
    figure = Figure(figsize=(6.5, 0.32 * len(rows) + 1.0), layout="constrained")
    ax = figure.subplots()
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=["quantity", "value"], loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.auto_set_column_width([0, 1])
    return figure


HEADLINE = (
    ("current_A", "I", "current", "tab:blue"),
    ("eof_m3_s", "Q_EOF", "flow", "tab:green"),
)
"""The sweep quantities drawn large, as ``(key, symbol, DISPLAY quantity, colour)``."""


def _sweep_axis(
    ax: Axes, curves: data.SweepCurves, values: np.ndarray, colour: str | None = None
) -> None:
    groups = list(dict.fromkeys(curves.group)) or [""]
    for group in groups:
        member = [g == group for g in curves.group] if curves.group else [True] * curves.x.size
        ax.plot(
            curves.x[member],
            values[member],
            marker="o",
            ms=4,
            color=colour if len(groups) == 1 else None,
            label=group or None,
        )
    if len(groups) > 1:
        ax.legend(fontsize="small")
    bad = curves.x[~curves.ok]
    if bad.size:
        ax.plot(bad, [0.0] * bad.size, "rx", transform=ax.get_xaxis_transform(), clip_on=False)
    ax.set_xlabel(curves.axis.rsplit(".", 1)[-1])


def sweep_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw a sweep: the current and flow rate large, the other scalars against the swept axis."""
    from matplotlib.figure import Figure

    rows = data.sweep_rows(artefact)
    curves = None if rows is None else data.sweep_curves(rows)
    if curves is None or not curves.quantities:
        return text_figure("this sweep holds no rows with a scalar quantity")
    axis_name = curves.axis.rsplit(".", 1)[-1]
    if axis_name == "bias_V":
        # Every panel against the bias the current is reported against, as the I-V panel is.
        bias_mV = data.cis_referenced_bias_V(curves) * DISPLAY["potential"].per_SI
        curves = replace(curves, x=bias_mV, axis=axis_label("V", "potential"))
    headline = [h for h in HEADLINE if h[0] in curves.quantities]
    shown = {h[0] for h in headline} | {axis_name}
    names = [n for n in curves.quantities if n not in shown]
    columns = min(3, max(len(names), 1))
    small_rows = -(-len(names) // columns) if names else 0
    height_ratios = ([1.8] if headline else []) + [1.0] * small_rows
    width = 4.6 * max(columns, len(headline))
    figure = Figure(figsize=(width, 3.0 * sum(height_ratios)), layout="constrained")
    cells = 6  # a common multiple of one to three panels per row
    grid = figure.add_gridspec(len(height_ratios), cells, height_ratios=height_ratios)
    offset = 1 if headline else 0
    for index, (key, symbol, quantity, colour) in enumerate(headline):
        span = cells // len(headline)
        ax = figure.add_subplot(grid[0, index * span : (index + 1) * span])
        if key == "current_A" and axis_name == "bias_V":
            panels.plot_iv(artefact, ax=ax)
            continue
        display = DISPLAY[quantity]
        _sweep_axis(ax, curves, curves.quantities[key] * display.per_SI, colour)
        ax.axhline(0.0, color="0.7", lw=0.8, zorder=0)
        ax.axvline(0.0, color="0.7", lw=0.8, zorder=0)
        ax.set_ylabel(f"{symbol} ({display.unit})")
        ax.set_title("I-V curve" if key == "current_A" else "electro-osmotic flow rate")
        ax.grid(alpha=0.3)
    span = cells // columns
    for index, name in enumerate(names):
        column = index % columns
        ax = figure.add_subplot(
            grid[offset + index // columns, column * span : (column + 1) * span]
        )
        _sweep_axis(ax, curves, curves.quantities[name])
        ax.set_ylabel(name)
    if not curves.ok.all():
        figure.suptitle(f"{int((~curves.ok).sum())} point(s) not ok, marked x", color="tab:red")
    return figure

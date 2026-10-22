"""One figure per stage artefact, and the sweep's, each built without pyplot."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from nanopnp.plot import data
from nanopnp.plot.data import DISPLAY, axis_label

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

VIEW_NM = (30.0, 45.0)
"""The ``(r, |z|)`` window of a field panel, cropped from a larger domain."""


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
    """Draw stage 4: the conditioned contour, over the reduced map when inputs give it."""
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
    ax.plot([p[0] * NM for p in closed], [p[1] * NM for p in closed], color="tab:red", lw=1.5)
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
    half = drawing.membrane_half_thickness_m * NM
    radius = drawing.reservoir_radius_m * NM
    ax.fill_between([0.0, radius], -half, half, color="tab:orange", alpha=0.35, label="membrane")
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


def mesh_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 6: element size and SICN, the 0.3 floor marked."""
    from matplotlib.figure import Figure
    from matplotlib.tri import Triangulation

    elements = data.mesh_of(artefact, inputs)
    if elements is None:
        return _absent(artefact, "mesh", "the mesh (a supplied mesh is read from its file)")
    triangulation = Triangulation(
        elements.vertices_m[:, 0] * NM, elements.vertices_m[:, 1] * NM, elements.triangles
    )
    figure = Figure(figsize=(9.0, 6.5), layout="constrained")
    left, right = figure.subplots(1, 2, sharey=True)
    image = left.tripcolor(triangulation, facecolors=elements.size_m * NM, cmap="viridis")
    figure.colorbar(image, ax=left, label=axis_label("longest edge h", "length"))
    left.set_title(f"{triangulation.triangles.shape[0]} elements")
    _rz_axes(left)
    image = right.tripcolor(
        triangulation, facecolors=elements.sicn, cmap="RdYlGn", vmin=0.0, vmax=1.0
    )
    bar = figure.colorbar(image, ax=right, label="SICN")
    bar.ax.axhline(data.SICN_FLOOR, color="k", lw=1.5)
    right.set_title(f"min SICN {elements.sicn.min():.3f} (floor {data.SICN_FLOOR})")
    right.set_xlabel(axis_label("r", "length"))
    right.set_aspect("equal", adjustable="box")
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
    """Draw stage 7's fields: the stored charge and ε_r grids."""
    from matplotlib.figure import Figure

    grids = data.charge_grids(artefact)
    if not grids:
        return _absent(artefact, "charge", "a stored charge or ε_r grid")
    figure = Figure(figsize=(4.5 * len(grids), 6.0), layout="constrained")
    axes = figure.subplots(1, len(grids), squeeze=False)[0]
    for ax, (name, (r, z, values)) in zip(axes, grids.items(), strict=True):
        image = _mesh(ax, r, z, values, cmap="coolwarm" if name == "charge" else "viridis")
        figure.colorbar(image, ax=ax, label="fixed charge" if name == "charge" else "ε_r field")
        _rz_axes(ax)
        ax.set_title(f"stored {name} grid")
    return figure


def materials_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw stage 8: each correction against the declared driver and the wall distance."""
    from matplotlib.figure import Figure

    if inputs is None:
        return _absent(artefact, "materials", "the correction models")
    electrolyte = inputs.resolved.electrolyte
    curves = data.correction_curves(
        electrolyte.corrections,
        driver=electrolyte.driver,
        concentration_M=inputs.resolved.concentration_M,
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
        left.set_xlabel(f"{curve.driver_label} (M)")
        left.set_ylabel(f"{curve.name} factor")
        left.set_title(f"{curve.name}: {curve.model} (fitted range shaded)")
        right.plot(curve.distance_m * NM, curve.factor_vs_distance)
        right.set_xlabel(axis_label("distance d to the pore wall", "length"))
        right.set_title(f"at {curve.driver_label} = {curve.at_driver_M:g} M")
    return figure


def _crop(ax: Axes, points_m: np.ndarray) -> None:
    r_max = min(float(points_m[:, 0].max()) * NM, VIEW_NM[0])
    z_low = max(float(points_m[:, 1].min()) * NM, -VIEW_NM[1])
    z_high = min(float(points_m[:, 1].max()) * NM, VIEW_NM[1])
    ax.set_xlim(0.0, r_max)
    ax.set_ylim(z_low, z_high)


def _field_panel(
    figure: Figure,
    ax: Axes,
    points_m: np.ndarray,
    triangles: np.ndarray,
    values: np.ndarray,
    *,
    title: str,
    label: str,
    scale: float,
    cmap: str,
) -> None:
    from matplotlib.tri import Triangulation

    triangulation = Triangulation(points_m[:, 0] * NM, points_m[:, 1] * NM, triangles)
    image = ax.tripcolor(triangulation, values * scale, shading="gouraud", cmap=cmap)
    figure.colorbar(image, ax=ax, label=label)
    ax.set_title(title)
    _rz_axes(ax)
    _crop(ax, points_m)


def _convergence(figure: Figure, residual_ax: Axes, damping_ax: Axes, rungs: list[Any]) -> None:
    offset = 0
    for rung in rungs:
        if rung.iteration.size == 0:
            continue
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
    """Draw stage 10: the solved fields and the Newton history per rung."""
    from matplotlib.figure import Figure

    rungs = data.newton_history(artefact)
    summary: Mapping[str, Any] = artefact.summary
    fields = None if inputs is None else data.solution_fields(inputs, artefact)
    if fields is None and rungs is None:
        return _absent(artefact, "solve", "the fields or the Newton history")
    model = fields.model if fields is not None else "solve"
    title = f"{model}, stabilisation: {summary.get('stabilisation', 'not recorded')}"
    panels: list[tuple[str, np.ndarray, np.ndarray, np.ndarray, str, float, str]] = []
    if fields is not None:
        points, triangles, whole = fields.whole
        for name, values in whole.items():
            if name == "phi_V":
                panels.append(("potential", points, triangles, values, "V", 1.0, "RdBu_r"))
        points, triangles, fluid = fields.fluid
        for name, values in fluid.items():
            if name.endswith("_mol_m3"):
                scale = DISPLAY["concentration"].per_SI
                panels.append(
                    (name[: -len("_mol_m3")], points, triangles, values, "M", scale, "viridis")
                )
            elif name == "u_m_s":
                speed = (values**2).sum(axis=1) ** 0.5
                scale = DISPLAY["velocity"].per_SI
                panels.append(("speed |u|", points, triangles, speed, "µm/s", scale, "magma"))
            elif name == "p_Pa":
                panels.append(("pressure", points, triangles, values, "Pa", 1.0, "PuOr"))
    columns = max(1, min(4, len(panels)))
    rows = -(-len(panels) // columns) + (1 if rungs else 0)
    figure = Figure(figsize=(4.2 * columns, 5.0 * rows), layout="constrained")
    figure.suptitle(title)
    grid = figure.add_gridspec(rows, columns)
    for index, (name, points, triangles, values, unit, scale, cmap) in enumerate(panels):
        ax = figure.add_subplot(grid[index // columns, index % columns])
        _field_panel(
            figure,
            ax,
            points,
            triangles,
            values,
            title=name,
            label=f"{name} ({unit})",
            scale=scale,
            cmap=cmap,
        )
    if rungs:
        last = rows - 1
        bottom = grid[last, :].subgridspec(1, 2)
        residual_ax = figure.add_subplot(bottom[0, 0])
        damping_ax = figure.add_subplot(bottom[0, 1])
        _convergence(figure, residual_ax, damping_ax, rungs)
    elif fields is not None and inputs is not None:
        figure.text(0.5, 0.01, "Newton history not recorded for this solve", ha="center")
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


def sweep_figure(artefact: Artefact, inputs: StageInputs | None = None) -> Figure:
    """Draw a sweep: each scalar quantity against the swept axis, failed points marked."""
    from matplotlib.figure import Figure

    rows = data.sweep_rows(artefact)
    curves = None if rows is None else data.sweep_curves(rows)
    if curves is None or not curves.quantities:
        return text_figure("this sweep holds no rows with a scalar quantity")
    names = list(curves.quantities)
    columns = min(3, len(names))
    rows_n = -(-len(names) // columns)
    figure = Figure(figsize=(4.2 * columns, 3.0 * rows_n), layout="constrained")
    axes = figure.subplots(rows_n, columns, squeeze=False)
    for ax, name in zip(axes.ravel(), names, strict=False):
        ax.plot(curves.x, curves.quantities[name], marker="o", ms=3)
        bad = curves.x[~curves.ok]
        if bad.size:
            ax.plot(bad, [0.0] * bad.size, "rx", transform=ax.get_xaxis_transform(), clip_on=False)
        ax.set_xlabel(curves.axis)
        ax.set_ylabel(name)
    for ax in axes.ravel()[len(names) :]:
        ax.axis("off")
    if not curves.ok.all():
        figure.suptitle(f"{int((~curves.ok).sum())} point(s) not ok, marked x", color="tab:red")
    return figure

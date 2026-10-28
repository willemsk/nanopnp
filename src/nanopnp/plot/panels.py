"""One panel per view of a solved run, each drawn on a given Axes or a new figure of its own."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nanopnp.plot import data
from nanopnp.plot.data import DISPLAY, axis_label

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np
    from matplotlib.axes import Axes
    from matplotlib.colors import Normalize
    from matplotlib.figure import Figure, SubFigure

    from nanopnp.io.artefact import Artefact
    from nanopnp.post.export import SolutionFields

__all__ = [
    "STREAM_GRID",
    "VIEW_NM",
    "mark_constriction",
    "plot_axial_cutline",
    "plot_charge",
    "plot_field",
    "plot_iv",
    "plot_mesh",
    "plot_radial_cutline",
]

VIEW_NM = (30.0, 45.0)
"""The ``(r, |z|)`` window of a field panel without a zoom, cropped from a larger domain."""

STREAM_GRID = (60, 120)
"""The ``(r, z)`` points of the regular grid the flow's streamlines are traced on."""

_NM = DISPLAY["length"].per_SI

_CONCENTRATION = "_mol_m3"


@dataclass(frozen=True)
class _Shown:
    values: np.ndarray
    label: str
    cmap: str
    centred: bool


def _shown(key: str, values: np.ndarray, bulk_mol_m3: float | None) -> _Shown:
    import numpy as np

    if key in ("potential", "phi_V"):
        return _Shown(
            values * DISPLAY["potential"].per_SI, axis_label("φ", "potential"), "RdBu_r", True
        )
    if key in ("u_r", "u_z"):
        return _Shown(
            values * DISPLAY["velocity"].per_SI, axis_label(key, "velocity"), "BrBG", True
        )
    if key == "p_Pa":
        return _Shown(
            values * DISPLAY["pressure"].per_SI, axis_label("p", "pressure"), "PiYG", True
        )
    if key.endswith(_CONCENTRATION):
        name = key[: -len(_CONCENTRATION)]
        if bulk_mol_m3 is None:
            per = DISPLAY["concentration"].per_SI
            return _Shown(values * per, axis_label(name, "concentration"), "viridis", False)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.log10(values / bulk_mol_m3)
        return _Shown(ratio, f"log₁₀({name} / c_bulk)", "PuOr_r", True)
    return _Shown(values, key, "viridis", False)


def _norm(shown: _Shown, halfrange: float | None = None) -> Normalize | None:
    import numpy as np
    from matplotlib.colors import CenteredNorm

    if not shown.centred:
        if halfrange is not None:
            raise ValueError(f"{shown.label} is not drawn about zero, so it takes no halfrange")
        return None
    if halfrange is not None:
        if not halfrange > 0.0:
            raise ValueError(f"the colour halfrange must be positive, got {halfrange}")
        return CenteredNorm(vcenter=0.0, halfrange=halfrange)
    finite = np.abs(shown.values[np.isfinite(shown.values)])
    reach = float(finite.max()) if finite.size else 0.0
    # CenteredNorm cannot span zero width; a uniform zero field still draws, in the centre colour.
    return CenteredNorm(vcenter=0.0, halfrange=reach if reach > 0.0 else 1.0)


def _bulk(fields: SolutionFields, key: str, relative: bool) -> float | None:
    if not relative or not key.endswith(_CONCENTRATION):
        return None
    try:
        return fields.bulk_mol_m3[key]
    except KeyError:
        known = ", ".join(sorted(fields.bulk_mol_m3)) or "none"
        raise ValueError(f"the fields record no bulk for {key!r}; they record {known}") from None


def _axes(ax: Axes | None, size: tuple[float, float]) -> Axes:
    if ax is not None:
        return ax
    from matplotlib.figure import Figure

    return Figure(figsize=size, layout="constrained").subplots()


def _figure(ax: Axes) -> Figure | SubFigure:
    figure = ax.get_figure()
    if figure is None:
        raise ValueError("the Axes belongs to no figure")
    return figure


def _scale_bar(ax: Axes, length_nm: float, label: str) -> None:
    # Data coordinates, so the bar is to scale; aspect is equal, so it reads in r and z alike.
    left, right = ax.get_xlim()
    low, high = ax.get_ylim()
    end = right - 0.06 * (right - left)
    height = low + 0.06 * (high - low)
    ax.plot([end - length_nm, end], [height, height], color="k", lw=2.5, solid_capstyle="butt")
    ax.text(end, height + 0.02 * (high - low), label, ha="right", va="bottom", fontsize="small")


def _rz(ax: Axes) -> None:
    ax.set_xlabel(axis_label("r", "length"))
    ax.set_ylabel(axis_label("z", "length"))
    ax.set_aspect("equal", adjustable="box")


def _window(ax: Axes, points_m: np.ndarray, zoom_nm: tuple[float, float] | None) -> None:
    reach_r, reach_z = VIEW_NM if zoom_nm is None else zoom_nm
    ax.set_xlim(0.0, min(float(points_m[:, 0].max()) * _NM, reach_r))
    ax.set_ylim(
        max(float(points_m[:, 1].min()) * _NM, -reach_z),
        min(float(points_m[:, 1].max()) * _NM, reach_z),
    )


def _streamlines(ax: Axes, fields: SolutionFields, window_nm: tuple[float, float]) -> None:
    import numpy as np

    reach_r, reach_z = window_nm
    r = np.linspace(0.0, reach_r, STREAM_GRID[0])
    z = np.linspace(-reach_z, reach_z, STREAM_GRID[1])
    grid_r, grid_z = np.meshgrid(r, z)
    flat_r, flat_z = grid_r.ravel(), grid_z.ravel()
    u_r = data.sampled(fields, "u_r", flat_r, flat_z).reshape(grid_r.shape)
    u_z = data.sampled(fields, "u_z", flat_r, flat_z).reshape(grid_r.shape)
    if not np.isfinite(u_z).any():
        return
    ax.streamplot(
        r,
        z,
        np.ma.masked_invalid(u_r),
        np.ma.masked_invalid(u_z),
        color="0.15",
        linewidth=0.6,
        arrowsize=0.7,
        density=0.9,
        broken_streamlines=True,
    )


def plot_field(
    fields: SolutionFields,
    quantity: str,
    *,
    ax: Axes | None = None,
    zoom_nm: tuple[float, float] | None = None,
    relative: bool = False,
    halfrange: float | None = None,
) -> Axes:
    """Draw one solved field over ``(r, z)``; a signed field is coloured about zero.

    Parameters
    ----------
    quantity
        An attribute key of the fields, or ``"potential"``, ``"u_r"`` or ``"u_z"``.
    zoom_nm
        The ``(r, |z|)`` window drawn, in nm; by default up to :data:`VIEW_NM`.
    relative
        Draw a concentration as ``log₁₀(c / c_bulk)``, with the bulk the solve imposed on that
        species (``fields.bulk_mol_m3``).
    halfrange
        The colour scale's reach either side of zero, in the panel's unit (mV for the
        potential); values beyond it saturate. By default the field's largest magnitude.

    Raises
    ------
    KeyError
        The run holds no such field.
    ValueError
        ``halfrange`` is given for a field not drawn about zero, or is not positive.
    """
    points, cells, values = data.field_values(fields, quantity)
    key = data.FIELD_ALIASES.get(quantity, (quantity, None))[0]
    shown = _shown(
        quantity if quantity in ("u_r", "u_z") else key, values, _bulk(fields, key, relative)
    )
    ax = _axes(ax, (4.6, 5.6))
    triangulation = data.field_triangulation(points, cells)
    image = ax.tripcolor(
        triangulation,
        shown.values,
        shading="gouraud",
        cmap=shown.cmap,
        norm=_norm(shown, halfrange),
    )
    _figure(ax).colorbar(
        image, ax=ax, label=shown.label, extend="neither" if halfrange is None else "both"
    )
    if quantity == "u_z":
        _streamlines(ax, fields, zoom_nm or data.fields_lumen_nm(fields))
    ax.set_title(shown.label.split(" (")[0])
    _rz(ax)
    _window(ax, points, zoom_nm)
    return ax


def plot_mesh(
    elements: data.MeshElements,
    *,
    ax: Axes | None = None,
    zoom_nm: tuple[float, float] | None = None,
    debye_target_nm: float | None = None,
    debye_note: str = "",
    edges_only: bool = False,
) -> Axes:
    """Draw a mesh: the whole domain by element size, or a zoomed window by SICN with its edges.

    Parameters
    ----------
    zoom_nm
        The ``(r, |z|)`` window drawn, in nm; given, the elements are coloured by SICN, the gate's
        floor marked, and their edges drawn.
    edges_only
        Draw the element edges alone, in grey on white, over the whole domain or the window.
    debye_target_nm
        ``λ_D / 5`` in nm, drawn as a scale bar.
    debye_note
        Where that value comes from, appended to the bar's label.
    """
    from matplotlib.colors import LogNorm
    from matplotlib.tri import Triangulation

    ax = _axes(ax, (4.6, 5.6))
    vertices = elements.vertices_m * _NM
    triangulation = Triangulation(vertices[:, 0], vertices[:, 1], elements.triangles)
    figure = _figure(ax)
    if edges_only:
        ax.triplot(triangulation, color="0.45", lw=0.3)
        ax.set_title(f"{elements.triangles.shape[0]} elements, {vertices.shape[0]} vertices")
        if zoom_nm is None:
            ax.set_xlim(0.0, float(vertices[:, 0].max()))
            ax.set_ylim(float(vertices[:, 1].min()), float(vertices[:, 1].max()))
        else:
            _window(ax, elements.vertices_m, zoom_nm)
    elif zoom_nm is None:
        size = elements.size_m * _NM
        image = ax.tripcolor(
            triangulation,
            facecolors=size,
            cmap="viridis",
            norm=LogNorm(vmin=float(size.min()), vmax=float(size.max())),
        )
        figure.colorbar(image, ax=ax, label=axis_label("longest edge h", "length"))
        ax.set_title(f"{elements.triangles.shape[0]} elements")
        ax.set_xlim(0.0, float(vertices[:, 0].max()))
        ax.set_ylim(float(vertices[:, 1].min()), float(vertices[:, 1].max()))
    else:
        image = ax.tripcolor(
            triangulation, facecolors=elements.sicn, cmap="RdYlGn", vmin=0.0, vmax=1.0
        )
        ax.triplot(triangulation, color="0.2", lw=0.25)
        bar = figure.colorbar(image, ax=ax, label="SICN")
        bar.ax.axhline(data.SICN_FLOOR, color="k", lw=1.5)
        ax.set_title(f"min SICN {elements.sicn.min():.3f} (floor {data.SICN_FLOOR})")
        _window(ax, elements.vertices_m, zoom_nm)
    if debye_target_nm is not None:
        note = f" ({debye_note})" if debye_note else ""
        _scale_bar(ax, debye_target_nm, f"λ_D/5 = {debye_target_nm:.2g} nm{note}")
    _rz(ax)
    return ax


def _line(
    ax: Axes,
    position: np.ndarray,
    values: np.ndarray,
    key: str,
    bulk_mol_m3: float | None,
    *,
    along: str,
) -> Axes:
    shown = _shown(key, values, bulk_mol_m3)
    ax.plot(position, shown.values, color="tab:blue")
    if shown.centred:
        ax.axhline(0.0, color="0.7", lw=0.8, zorder=0)
    ax.set_xlabel(axis_label(along, "length"))
    ax.set_ylabel(shown.label)
    ax.grid(alpha=0.3)
    return ax


def plot_axial_cutline(
    fields: SolutionFields,
    quantity: str,
    *,
    r_nm: float = 0.0,
    ax: Axes | None = None,
    relative: bool = False,
) -> Axes:
    """Draw one field along the line ``r = r_nm``, against z; a gap where the line leaves it."""
    z, values = data.axial_cutline(fields, quantity, r_nm=r_nm)
    key = data.FIELD_ALIASES.get(quantity, (quantity, None))[0]
    ax = _line(
        _axes(ax, (6.0, 3.2)),
        z,
        values,
        quantity if quantity in ("u_r", "u_z") else key,
        _bulk(fields, key, relative),
        along="z",
    )
    ax.set_title(f"along r = {r_nm:g} nm")
    return ax


def plot_radial_cutline(
    fields: SolutionFields,
    quantity: str,
    *,
    z_nm: float = 0.0,
    ax: Axes | None = None,
    relative: bool = False,
) -> Axes:
    """Draw one field along the line ``z = z_nm``, against r; a gap where the line leaves it."""
    r, values = data.radial_cutline(fields, quantity, z_nm=z_nm)
    key = data.FIELD_ALIASES.get(quantity, (quantity, None))[0]
    ax = _line(
        _axes(ax, (6.0, 3.2)),
        r,
        values,
        quantity if quantity in ("u_r", "u_z") else key,
        _bulk(fields, key, relative),
        along="r",
    )
    ax.set_title(f"across z = {z_nm:g} nm")
    return ax


def _annotation(artefact: Artefact, curves: data.SweepCurves, bias_mV: np.ndarray) -> str:
    import numpy as np

    per = DISPLAY["potential"].per_SI
    group_of = dict(zip(curves.index, curves.group, strict=False))
    lines = []
    ratios: Any = artefact.summary.get("rectification") or []
    for entry in ratios:
        if isinstance(entry, Mapping):
            group = group_of.get(int(entry["forward"]), "")
            lines.append(
                f"RR(±{abs(entry['bias_V']) * per:g} mV) = {entry['rectification']:.3g}"
                + (f", {group}" if group else "")
            )
    conductance = curves.quantities.get("conductance_S")
    if conductance is not None:
        groups = np.array(curves.group or [""] * bias_mV.size)
        for group in dict.fromkeys(groups.tolist()):
            positive = np.flatnonzero(
                (groups == group) & curves.ok & (bias_mV > 0.0) & np.isfinite(conductance)
            )
            if positive.size:
                at = positive[np.argmin(bias_mV[positive])]
                lines.append(
                    f"G = {conductance[at] * DISPLAY['conductance'].per_SI:.3g} nS at "
                    f"+{bias_mV[at]:g} mV" + (f", {group}" if group else "")
                )
    return "\n".join(lines)


def plot_iv(artefact: Artefact, *, ax: Axes | None = None, annotate: bool = True) -> Axes:
    """Draw a bias sweep's current against the bias, with its rectification and conductance.

    Raises
    ------
    ValueError
        The artefact is not a sweep, none of its rows reports a current, or it is not swept
        over the bias.
    """
    rows = data.sweep_rows(artefact)
    curves = None if rows is None else data.sweep_curves(rows)
    if curves is None or "current_A" not in curves.quantities:
        raise ValueError(f"{artefact.schema}: no row reports a current to draw against the bias")
    if curves.axis.rsplit(".", 1)[-1] != "bias_V":
        # Any other axis would be read as a bias in mV: a concentration of 0.2 M as 200 mV.
        raise ValueError(f"{artefact.schema}: swept over {curves.axis}, not the bias")
    ax = _axes(ax, (5.6, 4.0))
    bias = data.cis_referenced_bias_V(curves) * DISPLAY["potential"].per_SI
    current = curves.quantities["current_A"] * DISPLAY["current"].per_SI
    groups = list(dict.fromkeys(curves.group)) or [""]
    for group in groups:
        member = [g == group for g in curves.group] if curves.group else [True] * bias.size
        ax.plot(
            bias[member],
            current[member],
            marker="o",
            ms=4,
            color="tab:blue" if len(groups) == 1 else None,
            label=group or None,
        )
    if len(groups) > 1:
        ax.legend(fontsize="small", loc="lower right")
    failed = bias[~curves.ok]
    if failed.size:
        ax.plot(
            failed, [0.0] * failed.size, "rx", transform=ax.get_xaxis_transform(), clip_on=False
        )
    ax.axhline(0.0, color="0.7", lw=0.8, zorder=0)
    ax.axvline(0.0, color="0.7", lw=0.8, zorder=0)
    ax.set_xlabel(axis_label("V", "potential"))
    ax.set_ylabel(axis_label("I", "current"))
    ax.grid(alpha=0.3)
    text = _annotation(artefact, curves, bias) if annotate else ""
    if text:
        ax.text(
            0.03,
            0.97,
            text,
            transform=ax.transAxes,
            va="top",
            fontsize="small",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85, "lw": 0.5},
        )
    ax.set_title("I-V curve")
    return ax


def mark_constriction(ax: Axes, contour: Artefact) -> None:
    """Mark the narrowest lumen radius stage 4 measured, if its artefact records one."""
    found = contour.summary.get("constriction")
    if not isinstance(found, Mapping):
        return
    r_nm, z_nm = float(found["r_nm"]), float(found["z_nm"])
    ax.plot([0.0, r_nm], [z_nm, z_nm], color="tab:red", lw=1.0, ls="--")
    ax.annotate(
        f"constriction r = {r_nm:.2f} nm",
        (r_nm, z_nm),
        xytext=(4, 4),
        textcoords="offset points",
        color="tab:red",
        fontsize="small",
    )


def plot_charge(grids: Mapping[str, data.StoredGrid], *, ax: Axes | None = None) -> Axes:
    """Draw the deposited charge about zero, the solid's edge ``χ = 0.5`` drawn over it.

    Raises
    ------
    KeyError
        ``grids`` holds no ``charge`` grid.
    """
    import numpy as np

    charge = grids["charge"]
    ax = _axes(ax, (4.6, 5.6))
    shown = _Shown(np.asarray(charge.values, dtype=np.float64), "", "RdBu_r", True)
    image = ax.pcolormesh(
        charge.r_m * _NM,
        charge.z_m * _NM,
        shown.values,
        shading="auto",
        cmap=shown.cmap,
        norm=_norm(shown),
    )
    label = f"{charge.quantity.replace('_', ' ')} ({charge.unit})"
    _figure(ax).colorbar(image, ax=ax, label=label)
    solid = grids.get("solid_fraction")
    if solid is not None:
        ax.contour(
            solid.r_m * _NM,
            solid.z_m * _NM,
            solid.values,
            levels=[0.5],
            colors="0.15",
            linewidths=0.8,
        )
    ax.set_title(f"deposited {charge.quantity.replace('_', ' ')}, the lattice's χ = 0.5 drawn")
    _rz(ax)
    return ax

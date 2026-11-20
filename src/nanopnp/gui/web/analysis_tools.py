"""The Analysis suite's tools: the results explorer and the comparison of two runs."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from nicegui import events, run, ui

from nanopnp.api.project import ProjectError
from nanopnp.gui.geometry import colour_maps
from nanopnp.gui.render import (
    FieldsRequest,
    RenderFailed,
    RenderProcess,
    RenderRequest,
    scene_stem,
)
from nanopnp.gui.web.analysis import (
    AnalysisModel,
    FieldMap,
    Positive,
    RunChoice,
    cut_chart,
    difference_map,
    field_map,
    iv_chart,
    map_drawing,
    mirrored_map,
    pair_maps,
    pore_window,
    quantities_of,
    scene_field,
)
from nanopnp.gui.web.chart_view import ChartView
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.runs import queue_rebuild
from nanopnp.gui.web.screens import SUITES, Tool
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.tools import charge_colours
from nanopnp.io.project import COMPARISON_VIEWS, ComparisonFile
from nanopnp.plot.data import fluid_outline_nm
from nanopnp.post.fields import (
    FIELD_ALIASES,
    field_at,
    field_unit,
    joint_range,
    quantity_name,
)

__all__ = ["analysis_page", "comparison_maps", "map_of"]

_RENDERS: dict[tuple[Path, str], RenderProcess] = {}
"""The render children of the runs' fields and scenes, by run and what they write."""

_FAILED: dict[tuple[Path, str], str] = {}
"""What a render child said where it drew nothing, by run and what it was asked for."""

_MAPS: dict[tuple[object, ...], FieldMap] = {}
_KEPT_MAPS = 8

VIEW_NAMES = {
    "difference": "Difference",
    "maps": "Side by side",
    "mirrored": "Mirrored",
    "mesh": "3D",
}
"""Each view a comparison opens on, as its control names it."""

_OUTLINES: dict[tuple[Path, str | None], Any] = {}
"""Each run's fluid outline, by run and solve: an edge sort over its cells, done once."""

FRAMES = {"pore": "The pore", "whole": "Whole domain"}
"""What a map and its axial cut span, as the control names it: the pore's close-up opens."""

AUTOMATIC = "Automatic: diverging across 0, else viridis"
"""The colour map field's entry for the map's own choice."""


def _palettes() -> dict[str, str]:
    return {"": AUTOMATIC, **{name: name for name in colour_maps()}}


def _named(quantities: list[str] | tuple[str, ...]) -> dict[str, str]:
    return {
        key: f"{quantity_name(key)} ({field_unit(key)})" if field_unit(key) else quantity_name(key)
        for key in quantities
    }


def _kept(key: tuple[object, ...], make: Callable[[], FieldMap]) -> FieldMap:
    found = _MAPS.get(key)
    if found is None:
        found = make()
        _MAPS[key] = found
        while len(_MAPS) > _KEPT_MAPS:
            _MAPS.pop(next(iter(_MAPS)))
    return found


def map_of(
    model: AnalysisModel,
    run: Path,
    quantity: str,
    palette: str | None = None,
    colour_range: tuple[float, float] | None = None,
    *,
    whole: bool = False,
    positive: Positive = "blue",
) -> FieldMap | None:
    """Return one run's map of a quantity, kept for the picture's request; None without fields.

    It spans the pore's close-up, or with ``whole`` the run's whole domain.
    """
    fields = model.fields(run)
    if fields is None:
        return None
    key = ("run", run, model.solve_hash(run), quantity, palette, colour_range, whole, positive)
    window = None if whole else pore_window(fields)
    return _kept(
        key,
        lambda: field_map(
            fields,
            quantity,
            palette=palette,
            colour_range=colour_range,
            window_nm=window,
            positive=positive,
        ),
    )


def comparison_maps(
    model: AnalysisModel, name: str, *, whole: bool = False, positive: Positive = "blue"
) -> dict[str, FieldMap] | None:
    """Return a comparison's maps, ``first``, ``second``, ``difference`` and ``mirrored``.

    None until both runs' fields are read.

    They span the close-up that holds both pores, or with ``whole`` the fluids' overlap.

    Raises
    ------
    ValueError
        If the two runs carry no common quantity of that name.
    """
    compared = model.comparison(name)
    first_run, second_run = (model.run_path(item) for item in compared.runs)
    first, second = model.fields(first_run), model.fields(second_run)
    if first is None or second is None:
        return None
    shown = (compared.quantity, compared.colour_map, compared.range)
    stamp = (model.solve_hash(first_run), model.solve_hash(second_run))
    pair = (first_run, second_run, *stamp, *shown, whole, positive)
    window = None if whole else pore_window(first, second)

    def paired() -> tuple[FieldMap, FieldMap]:
        return pair_maps(
            first,
            second,
            compared.quantity,
            palette=compared.colour_map,
            colour_range=compared.range,
            window_nm=window,
            positive=positive,
        )

    left = _kept(("first", *pair), lambda: paired()[0])
    right = _kept(("second", *pair), lambda: paired()[1])
    difference = _kept(
        ("difference", *pair),
        lambda: difference_map(
            first,
            second,
            compared.quantity,
            palette=compared.colour_map,
            window_nm=window,
            positive=positive,
        ),
    )
    mirrored = _kept(("mirrored", *pair), lambda: mirrored_map(left, right))
    return {"first": left, "second": right, "difference": difference, "mirrored": mirrored}


def _relative(model: AnalysisModel, run: Path) -> str:
    try:
        return run.resolve().relative_to(model.project.root.resolve()).as_posix()
    except ValueError:
        return str(run)


def _outline(model: AnalysisModel, run_dir: Path) -> Any:  # noqa: ANN401 - an array
    fields = model.fields(run_dir)
    if fields is None:
        return None
    key = (run_dir, model.solve_hash(run_dir))
    if key not in _OUTLINES:
        _OUTLINES[key] = fluid_outline_nm(fields)
    return _OUTLINES[key]


def _whole_field(quantity: str) -> bool:
    # A component is drawn in 3D as its vector whole, on the renderer's own range; a scalar, an
    # alias such as potential among them, on the map's.
    return FIELD_ALIASES.get(quantity, (quantity, None))[1] is None


def _reversed(colour_range: tuple[float, float] | None, positive: Positive) -> bool:
    # The renderer's map runs blue to red from low to high: where positive is blue (WB-39), a range
    # across zero is handed to it reversed, so the 3D view's signs read as the map's.
    return (
        colour_range is not None and colour_range[0] < 0.0 < colour_range[1] and positive == "blue"
    )


def _window_query(window: tuple[float, float, float, float] | None) -> dict[str, str]:
    return {} if window is None else {"frame": ",".join(f"{value:.6g}" for value in window)}


def _render(key: tuple[Path, str], request: FieldsRequest | RenderRequest) -> None:
    held = _RENDERS.get(key)
    if held is not None and (held.running or not held.answered):
        return
    _FAILED.pop(key, None)
    process = RenderProcess(request)
    process.start()
    _RENDERS[key] = process


def _drain() -> None:
    # Every page drains every child; a page redraws once a render it waits on has ended.
    for key, process in list(_RENDERS.items()):
        for event in process.drain():
            if isinstance(event, RenderFailed):
                _FAILED[key] = event.message
        if not process.running and process.answered:
            del _RENDERS[key]
        elif not process.running and not process.answered:
            _FAILED[key] = "the render child ended without answering"
            del _RENDERS[key]


def _probe_rows(
    fields: Any,  # noqa: ANN401 - a run's SolutionFields
    quantity: str,
    probes: list[tuple[float, float]],
) -> list[str]:
    import numpy as np

    if not probes:
        return []
    r = np.array([p[0] for p in probes])
    z = np.array([p[1] for p in probes])
    values = field_at(fields, quantity, r, z)
    unit = field_unit(quantity)
    return [
        "outside the field" if not np.isfinite(value) else f"{value:.4g} {unit}".strip()
        for value in values
    ]


class _AnalysisPage:
    """One Analysis tool's page: its pane of choices beside its tiles."""

    def __init__(self, shell: Shell, tool: Tool, built: Views) -> None:
        self.shell = shell
        self.tool = tool
        self.built = built
        self.suite = next(suite for suite in SUITES if suite.id == "analysis")
        project = shell.bench.project
        self.model = None if project is None else AnalysisModel(project)
        self.study: str | None = None
        self.choice: RunChoice | None = None
        # The run's first quantity, once its fields are read.
        self.quantity = ""
        self.palette: str | None = None
        self.cut_r_nm: float = 0.0
        self.placing = "cut"
        self.probes: list[tuple[float, float]] = []
        self.on_mesh = False
        self.whole = False
        self.outline = False
        self.colour_range: tuple[float, float] | None = None
        # Link 3: a click on the map places the cut or a probe, until unlinked (WB-06).
        self.linked = True
        self.compared: str | None = None
        self.seen: object = None
        self.pane: ui.column
        self.status: ui.element
        self.view_box: ui.element
        self.head: ui.element
        self.ready = False
        # The renders this page waits on: it redraws when one ends, whichever page drained it.
        self.waiting: set[tuple[Path, str]] = set()

    # -- the page ---------------------------------------------------------------------------

    def build(self) -> None:
        with ui.element("div").classes("tool-page"):
            self.tool_list()
            with ui.column().classes("tool-pane").props("data-control=tool-pane"):
                heading(self.tool.title, 1)
                self.status = ui.element("div").props("data-control=tool-status role=status")
                self.status.classes("tool-status")
                self.pane = ui.column().classes("analysis-pane w-full")
            self.view_box = ui.element("div").classes("tool-view analysis-view")
            self.view_box.props(
                f'data-control=tool-view role=region aria-label="{self.tool.title}"'
            )
        self.built.listen("plane_point", self.on_point)
        self.built.listen("chart_pick", self.on_chart_pick)
        ui.timer(1.0, self.tick)
        ui.timer(0.1, self.start, once=True)

    def tool_list(self) -> None:
        named = f'aria-label="{self.suite.title} tools"'
        with ui.element("nav").classes("tool-list").props(named):
            for tool in self.suite.tools:
                link = ui.link(target=f"/analysis/{tool.id}").classes("tool-link")
                link.props(f"data-control=tool-link-{tool.id} data-state=none")
                if tool.id == self.tool.id:
                    link.classes("tool-link-open").props("aria-current=page")
                with link:
                    ui.label(tool.title).classes("tool-name")

    async def start(self) -> None:
        await self.built.settled()
        self.choose_defaults()
        await self.redraw()
        self.ready = True
        await ui.run_javascript("document.body.dataset.screenReady = '1'", timeout=10)

    def say(self, text: str, link: tuple[str, str] | None = None) -> None:
        self.status.clear()
        with self.status:
            if link is None:
                ui.label(text)
                return
            # A pointer to another place is a link, and the sentence says what to do there.
            with ui.element("p").classes("status-line"):
                ui.label(text).classes("inline")
                ui.link(link[0], link[1]).props("data-control=analysis-status-link")
                ui.label(".").classes("inline")

    async def tick(self) -> None:
        _drain()
        ended = {key for key in self.waiting if key not in _RENDERS}
        if ended and self.ready:
            self.waiting -= ended
            await self.redraw()

    def wait(self, key: tuple[Path, str], request: FieldsRequest | RenderRequest) -> None:
        _render(key, request)
        self.waiting.add(key)

    async def redraw(self) -> None:
        self.pane.clear()
        self.view_box.clear()
        if self.model is None:
            self.say("No project is open. Create or open one from the File menu.")
            return
        if self.tool.id == "explorer":
            await self.explorer()
        else:
            await self.comparison()

    # -- the explorer -------------------------------------------------------------------------

    def choose_defaults(self) -> None:
        if self.model is None:
            return
        names = self.model.comparisons()
        current = self.model.project.current or ""
        opened = current.removeprefix("comparison/")
        # The comparison the rail opened last, else the first.
        self.compared = opened if opened in names else names[0] if names else None
        studies = self.model.studies()
        shown = self.shell.result_shown
        if shown is not None:
            run_dir = Path(shown)
            for study in studies:
                for choice in self.model.choices(study):
                    if choice.directory == run_dir:
                        self.study, self.choice = study, choice
                        return
        self.study = (
            self.shell.study if self.shell.study in studies else studies[0] if studies else None
        )
        found = self.model.choices(self.study) if self.study else ()
        self.choice = found[0] if found else None

    async def explorer(self) -> None:
        assert self.model is not None
        studies = self.model.studies()
        if not studies:
            self.say("No study yet. Create one in ", ("Study \u203a Study setup", "/study/setup"))
            self.empty_tiles("Run a study to see its result here.")
            return
        with self.pane:
            ui.select(
                list(studies), value=self.study, label="Study", on_change=self.on_study
            ).props("dense data-control=analysis-study").classes("w-full")
            choices = self.model.choices(self.study) if self.study else ()
            if not choices:
                self.say(
                    f"{self.study} has no run yet. Start one in ",
                    ("Study \u203a Runs", "/study/runs"),
                )
                self.empty_tiles("Run the study to see its result here.")
                return
            ui.select(
                {str(choice.directory): choice.label for choice in choices},
                value=None if self.choice is None else str(self.choice.directory),
                label="Run",
                on_change=self.on_run,
            ).props("dense data-control=analysis-run").classes("w-full")
        choice = self.choice
        if choice is None:
            return
        self.shell.result_shown = str(choice.directory)
        state = self.model.state(choice.directory)
        fields = self.model.fields(choice.directory) if state == "solved" else None
        self.explain(choice, state, fields is not None)
        with self.pane:
            ui.button("Open in Runs", on_click=lambda: self.open_runs(choice)).props(
                "flat dense no-caps data-control=analysis-open-runs"
            )
            if state == "removed":
                ui.button("Solve again", on_click=lambda: self.rebuild(choice)).props(
                    "outline dense no-caps data-control=analysis-rebuild"
                )
            quantities = quantities_of(fields) if fields is not None else ()
            if quantities:
                if self.quantity not in quantities:
                    self.quantity = quantities[0]
                self.field_controls(quantities)
                if not self.on_mesh:
                    self.probe_controls(fields)
        with self.view_box, ui.element("div").classes("analysis-tiles"):
            with self.tile("Field", "analysis-field"):
                await self.field_tile(choice, fields)
            with self.tile("Current against bias", "analysis-iv"):
                chart = ChartView("analysis-iv-chart", "analysis-iv-chart", classes="tile-chart")
                chart.show(iv_chart(self.model.choices(choice.study), choice.directory))
            with self.tile("Quantities", "analysis-quantities"):
                self.quantities_tile(choice)
            with self.tile(f"Axial cut, r = {self.cut_r_nm:.3g} nm", "analysis-cut"):
                if fields is None:
                    ui.label(self.unread(choice, "cut")).classes("later")
                else:
                    cut = ChartView(
                        "analysis-cut-chart", "analysis-cut-chart", classes="tile-chart"
                    )
                    window = None if self.whole else pore_window(fields)
                    cut.show(
                        cut_chart(((choice.label, fields),), self.quantity, self.cut_r_nm, window)
                    )

    def explain(self, choice: RunChoice, state: str, read: bool) -> None:
        assert self.model is not None
        if state == "removed":
            self.say(
                "The store no longer holds the fields of this run, and the run record keeps the "
                "numbers. Solve again to draw the map: this takes as long as the first solve."
            )
        elif state == "unsolved":
            self.say("This run did not reach its solve: it has no fields.")
        elif not read:
            key = (choice.directory, "fields")
            if key in _FAILED:
                self.say(f"The run's fields did not read: {_FAILED[key]}")
            else:
                self.wait(key, FieldsRequest(run=str(choice.directory)))
                self.say("Reading the run's fields…")
        else:
            self.say(f"{choice.label}, of study {choice.study}.")

    def unread(self, choice: RunChoice, what: str = "map") -> str:
        assert self.model is not None
        state = self.model.state(choice.directory)
        if state == "removed":
            return f"Solve again to draw the {what}."
        if state == "unsolved":
            return f"The run has no fields to draw a {what} of."
        return f"The {what} draws once the run's fields are read."

    def run_name(self, run_dir: Path) -> str:
        assert self.model is not None
        for study in self.model.studies():
            for choice in self.model.choices(study):
                if choice.directory == run_dir:
                    return f"{choice.label}, of study {study}"
        return _relative(self.model, run_dir)

    def recorded_line(self, run_dir: Path, lead: str = "Recorded") -> None:
        assert self.model is not None
        for study in self.model.studies():
            for choice in self.model.choices(study):
                if choice.directory != run_dir:
                    continue
                parts = []
                if choice.current_A is not None:
                    parts.append(f"current {choice.current_A * 1e9:.4g} nA")
                if choice.conductance_S is not None:
                    parts.append(f"conductance {choice.conductance_S * 1e9:.4g} nS")
                if parts:
                    ui.label(f"{lead}: {', '.join(parts)}").classes("field-hint")
                return

    def link_chip(self) -> None:
        with ui.row().classes("items-center no-wrap"):
            ui.badge(
                "Map, cut and probes linked"
                if self.linked
                else "Not linked: a click places nothing"
            ).props("data-control=analysis-link-state")
            ui.button("Unlink" if self.linked else "Link", on_click=self.toggle_link).props(
                "flat dense no-caps data-control=analysis-link"
            )

    async def toggle_link(self) -> None:
        self.linked = not self.linked
        await self.redraw()

    def tile(self, title: str, control: str) -> Any:  # noqa: ANN401 - a NiceGUI element
        with (
            ui.element("section")
            .classes("analysis-tile")
            .props(f'data-control={control} aria-label="{title}"') as tile
        ):
            with ui.element("div").classes("tile-head") as head:
                heading(title, 2)
        self.head = head
        return tile

    def view_switch(
        self,
        options: dict[str, str],
        value: str,
        changed: Callable[[Any], Any],
        control: str,
        label: str,
    ) -> None:
        """Draw a small switch among two or a few views, in a tile's head or in the pane."""
        ui.toggle(options, value=value, on_change=changed).props(
            f'dense no-caps unelevated data-control={control} aria-label="{label}"'
        ).classes("view-switch")

    def empty_tiles(self, text: str) -> None:
        with self.view_box:
            ui.label(text).classes("later")

    def field_controls(self, quantities: tuple[str, ...]) -> None:
        ui.select(
            _named(quantities), value=self.quantity, label="Quantity", on_change=self.on_quantity
        ).props("dense data-control=analysis-quantity").classes("w-full")
        if not self.on_mesh:
            # The 3D view draws in the renderer's own colour map (AU2), on the map's range.
            ui.select(
                _palettes(),
                value=self.palette or "",
                label="Colour map",
                on_change=self.on_palette,
            ).props("dense data-control=analysis-colour-map").classes("w-full")
        self.range_fields(self.colour_range, self.on_range)
        self.frame_control()
        if self.on_mesh:
            return
        self.outline_control()
        ui.label("A click on the map places").classes("field-hint")
        ui.toggle(
            {"cut": "Cut", "probe": "Probe"}, value=self.placing, on_change=self.on_placing
        ).props(
            'dense no-caps data-control=analysis-placing aria-label="A click on the map places"'
        )
        ui.number("Cut at r (nm)", value=self.cut_r_nm, on_change=self.on_cut).props(
            "dense debounce=600 data-control=analysis-cut-r"
        )

    def range_fields(
        self,
        typed: tuple[float, float] | None,
        changed: Callable[[tuple[float, float] | None], Any],
        quantity: str | None = None,
    ) -> None:
        unit = field_unit(quantity or self.quantity)
        with (
            ui.row()
            .classes("no-wrap items-start w-full")
            .props('role=group aria-label="Colour range"')
        ):
            low = ui.number(
                f"Colours from ({unit})" if unit else "Colours from",
                value=None if typed is None else typed[0],
                placeholder="auto",
            ).props("dense debounce=600 data-control=analysis-range-from")
            high = ui.number(
                f"to ({unit})" if unit else "to",
                value=None if typed is None else typed[1],
                placeholder="auto",
            ).props("dense debounce=600 data-control=analysis-range-to")

        async def typed_range() -> None:
            ends = (low.value, high.value)
            if None in ends:
                await changed(None)
            elif float(ends[0]) < float(ends[1]):
                await changed((float(ends[0]), float(ends[1])))

        low.on_value_change(typed_range)
        high.on_value_change(typed_range)

    def outline_control(self) -> None:
        ui.checkbox("Outline", value=self.outline, on_change=self.on_outline).props(
            "dense data-control=analysis-outline"
        )

    def frame_control(self) -> None:
        ui.label("The map and the cut span").classes("field-hint")
        ui.toggle(FRAMES, value="whole" if self.whole else "pore", on_change=self.on_frame).props(
            'dense no-caps data-control=analysis-frame aria-label="The map and the cut span"'
        )

    def probe_controls(self, fields: Any) -> None:  # noqa: ANN401 - a run's SolutionFields
        heading("Probes", 3)
        with (
            ui.row().classes("no-wrap items-end w-full").props('role=group aria-label="New probe"')
        ):
            r_field = ui.number("r (nm)", value=0.0).props("dense data-control=analysis-probe-r")
            z_field = ui.number("z (nm)", value=0.0).props("dense data-control=analysis-probe-z")

            async def add() -> None:
                if isinstance(r_field.value, int | float) and isinstance(
                    z_field.value, int | float
                ):
                    self.probes.append((max(0.0, float(r_field.value)), float(z_field.value)))
                    await self.redraw()

            ui.button("Add probe", on_click=add).props(
                "outline dense no-caps data-control=analysis-probe-add"
            ).style("white-space: nowrap; flex: none")
        if not self.probes:
            ui.label("Type a probe's r and z, or choose Probe and click the map.").classes(
                "field-hint"
            )
            return
        values = _probe_rows(fields, self.quantity, self.probes)
        for index, ((r_nm, z_nm), value) in enumerate(zip(self.probes, values, strict=True)):
            with (
                ui.row()
                .classes("probe-row items-center no-wrap")
                .props(f"data-control=analysis-probe-{index}")
            ):
                ui.label(f"r {r_nm:.3g} nm, z {z_nm:.3g} nm: {value}")
                ui.button("Remove", on_click=lambda _, k=index: self.remove_probe(k)).props(
                    f'flat dense no-caps aria-label="Remove probe {index + 1}"'
                )

    async def field_tile(self, choice: RunChoice, fields: Any) -> None:  # noqa: ANN401
        assert self.model is not None
        if fields is None:
            ui.label(self.unread(choice)).classes("later")
            return
        with self.head:
            self.view_switch(
                {"map": "Map", "mesh": "3D"},
                "mesh" if self.on_mesh else "map",
                self.on_view,
                "analysis-on-mesh",
                "View",
            )
        window = None if self.whole else pore_window(fields)
        shown = await run.io_bound(
            lambda: (
                map_of(
                    self.model,
                    choice.directory,
                    self.quantity,
                    self.palette,
                    self.colour_range,
                    whole=self.whole,
                    positive=charge_colours(self.shell),
                )
                if self.model is not None
                else None
            )
        )
        if shown is None:
            return
        if self.on_mesh:
            scene = scene_field(self.quantity)
            ranged = shown.scale if _whole_field(self.quantity) else None
            reverse = _reversed(ranged, charge_colours(self.shell))
            self.scene_caption(ranged is not None, reverse)
            self.scene_frame(choice.directory, scene, ranged, "analysis-scene", window, reverse)
            return
        query = urlencode(
            {
                "run": _relative(self.model, choice.directory),
                "quantity": self.quantity,
                "palette": self.palette or "",
                **({"frame": "whole"} if self.whole else {}),
                **(
                    {"range": f"{self.colour_range[0]!r},{self.colour_range[1]!r}"}
                    if self.colour_range is not None
                    else {}
                ),
            }
        )
        outline = _outline(self.model, choice.directory) if self.outline else None
        drawing = map_drawing(
            shown,
            f"/api/analysis/image?{query}",
            cut_r_nm=self.cut_r_nm,
            probes=tuple(self.probes),
            outline_nm=() if outline is None else (outline,),
        )
        ui.element("div").props("id=analysis-map data-control=analysis-map").classes("tile-map")
        self.link_chip()
        await ui.run_javascript(
            f"nano.map('analysis-map', {json.dumps(drawing.json())})", timeout=60
        )

    def scene_caption(self, ranged: bool, reverse: bool) -> None:
        """Say what the 3D view's colours are: the renderer's map, on the map's range and signs."""
        parts = ["The 3D view draws in the renderer's own colour map"]
        if ranged:
            parts.append(" on the map's colour range")
        if reverse:
            parts.append(", positive blue as on the map")
        ui.label("".join(parts) + ".").classes("field-hint")

    def scene_frame(
        self,
        run_dir: Path,
        scene: str,
        colour_range: tuple[float, float] | None,
        control: str,
        window: tuple[float, float, float, float] | None = None,
        reverse: bool = False,
    ) -> None:
        assert self.model is not None
        stem = scene_stem(scene, colour_range)
        key = (run_dir, stem)
        if (run_dir / "viewer" / f"{stem}.json").is_file():
            query = {"run": _relative(self.model, run_dir), "field": scene}
            if colour_range is not None:
                query["range"] = f"{colour_range[0]!r},{colour_range[1]!r}"
            query.update(_window_query(window))
            if reverse:
                query["reverse"] = "1"
            ui.element("iframe").props(
                f'src="/api/analysis/view?{urlencode(query)}" data-control={control} '
                f'title="{scene} on the mesh"'
            ).classes("tile-scene")
        elif key in _FAILED:
            ui.label(f"The field did not draw on the mesh: {_FAILED[key]}").classes("state-err")
        else:
            self.wait(
                key,
                RenderRequest(
                    run=str(run_dir), field=scene, document=False, colour_range=colour_range
                ),
            )
            ui.label("Drawing the field on the mesh…").classes("later").props(
                f"data-control={control}-pending"
            )

    def quantities_tile(self, choice: RunChoice) -> None:
        assert self.model is not None
        rows = self.model.quantity_rows(choice.directory)
        if rows:
            with ui.element("dl").classes("readout-list"):
                for row in rows:
                    with ui.element("dt"):
                        ui.label(row["quantity"])
                    with ui.element("dd"):
                        ui.label(f"{row['value']} {row['unit']}".strip())
        else:
            ui.label("The run recorded no quantity of interest.").classes("later")
        heading("Changed from the validated default", 3)
        deviations = self.model.deviations(choice.directory)
        for line in deviations or ["None: every switch holds its validated default."]:
            ui.label(line).classes("field-hint")
        heading("Folder", 3)
        ui.label(_relative(self.model, choice.directory)).classes("mono").props(
            "data-control=analysis-folder"
        )

    # -- the comparison -----------------------------------------------------------------------

    async def comparison(self) -> None:
        assert self.model is not None
        names = self.model.comparisons()
        with self.pane:
            if names:
                ui.select(
                    list(names),
                    value=self.compared,
                    label="Comparison",
                    on_change=self.on_comparison,
                ).props("dense data-control=analysis-comparison").classes("w-full")
            self.new_comparison()
        if self.compared is None:
            self.say("The project holds no comparison. New comparison pairs two runs.")
            self.empty_tiles("Pair two runs to compare them here.")
            return
        try:
            compared = self.model.comparison(self.compared)
        except (ProjectError, ValueError) as error:
            self.say(f"Comparison {self.compared} does not read: {error}")
            return
        runs = tuple(self.model.run_path(item) for item in compared.runs)
        missing = [
            item for item, path in zip(compared.runs, runs, strict=True) if not path.is_dir()
        ]
        if missing:
            self.say(
                f"Comparison {self.compared} names a run the project lacks: {', '.join(missing)}"
            )
            return
        held = [self.model.fields(path) for path in runs]
        for path, fields in zip(runs, held, strict=True):
            if fields is None and self.model.state(path) == "solved":
                self.wait((path, "fields"), FieldsRequest(run=str(path)))
        if any(fields is None for fields in held):
            self.say("Reading the two runs' fields…")
        else:
            first, second = (self.run_name(path) for path in runs)
            self.say(f"First: {first}. Second: {second}.")
        with self.pane:
            self.comparison_controls(compared, held)
        with self.view_box, ui.element("div").classes("analysis-tiles"):
            await self.comparison_tiles(compared, runs, held)

    def new_comparison(self) -> None:
        assert self.model is not None
        every: dict[str, str] = {}
        for study in self.model.studies():
            for choice in self.model.choices(study):
                if choice.status == "ok":
                    every[_relative(self.model, choice.directory)] = f"{study}: {choice.label}"
        with (
            ui.expansion("New comparison", value=False)
            .props("dense data-control=analysis-new-comparison")
            .classes("w-full")
        ):
            name = ui.input("Name").props("dense data-control=analysis-new-name")
            first = ui.select(every, label="First run").props(
                "dense data-control=analysis-new-first"
            )
            second = ui.select(every, label="Second run").props(
                "dense data-control=analysis-new-second"
            )

            async def create() -> None:
                assert self.model is not None
                if not name.value or not first.value or not second.value:
                    ui.notify("A comparison takes a name and two runs.")
                    return
                try:
                    self.model.project.new_comparison(name.value, first.value, second.value)
                except (ProjectError, ValueError) as error:
                    ui.notify(str(error))
                    return
                self.compared = name.value
                await self.redraw()

            ui.button("Create", on_click=create).props("dense no-caps data-control=analysis-create")

    def comparison_controls(self, compared: ComparisonFile, held: list[Any]) -> None:
        both = (
            sorted(set(quantities_of(held[0])) & set(quantities_of(held[1])))
            if all(fields is not None for fields in held)
            else []
        )
        # The file's own quantity stays offered, as an alias such as potential is.
        if compared.quantity not in both:
            both.insert(0, compared.quantity)
        ui.select(
            _named(both),
            value=compared.quantity,
            label="Quantity",
            on_change=lambda e: self.set_compared(quantity=e.value),
        ).props("dense data-control=analysis-quantity").classes("w-full")
        self.view_switch(
            {view: VIEW_NAMES[view] for view in COMPARISON_VIEWS},
            compared.view,
            lambda e: self.set_compared(view=e.value),
            "analysis-view",
            "View",
        )
        if compared.view != "mesh":
            # The 3D views draw in the renderer's own colour map (AU2).
            ui.select(
                _palettes(),
                value=compared.colour_map or "",
                label="Colour map",
                on_change=lambda e: self.set_compared(colour_map=e.value or None),
            ).props("dense data-control=analysis-colour-map").classes("w-full")
        if compared.view in ("maps", "mirrored", "mesh"):
            self.range_fields(compared.range, self.on_compared_range, compared.quantity)
        self.frame_control()
        if compared.view != "mesh":
            self.outline_control()
        ui.number("Cut at r (nm)", value=self.cut_r_nm, on_change=self.on_cut).props(
            "dense debounce=600 data-control=analysis-cut-r"
        )

    async def comparison_tiles(
        self, compared: ComparisonFile, runs: tuple[Path, ...], held: list[Any]
    ) -> None:
        assert self.model is not None and self.compared is not None
        ready = all(fields is not None for fields in held)
        name = self.compared
        window = None if self.whole or not ready else pore_window(*held)
        maps = (
            await run.io_bound(
                lambda: (
                    comparison_maps(
                        self.model, name, whole=self.whole, positive=charge_colours(self.shell)
                    )
                    if self.model is not None
                    else None
                )
            )
            if ready
            else None
        )
        if compared.view == "mesh":
            scene = scene_field(compared.quantity)
            # The pair's 3D views take one range (AU3): the side-by-side maps' scale, or for a
            # component, whose vector is drawn whole, the two runs' joint range.
            ranged = (
                (
                    maps["first"].scale
                    if _whole_field(compared.quantity)
                    else joint_range(held[0], held[1], compared.quantity)
                )
                if maps is not None
                else None
            )
            reverse = _reversed(ranged, charge_colours(self.shell))
            for index, path in enumerate(runs):
                with self.tile(self.run_name(path), f"analysis-pair-{index}"):
                    self.recorded_line(path)
                    if index == 0:
                        self.scene_caption(ranged is not None, reverse)
                    if ready:
                        self.scene_frame(
                            path, scene, ranged, f"analysis-scene-{index}", window, reverse
                        )
        else:
            shown = {
                "difference": ("difference",),
                "mirrored": ("mirrored",),
            }.get(compared.view, ("first", "second"))
            for which in shown:
                title = {
                    "difference": "Second less first",
                    "mirrored": "Mirrored pair",
                }.get(which) or self.run_name(runs[0 if which == "first" else 1])
                both = which in ("difference", "mirrored")
                with self.tile(title, f"analysis-compare-{which}"):
                    if both:
                        leads = ("First", "Second") if which == "difference" else ("Left", "Right")
                        for path, lead in zip(runs, leads, strict=True):
                            self.recorded_line(path, f"{lead}, {self.run_name(path)}")
                    else:
                        self.recorded_line(runs[0 if which == "first" else 1])
                    if maps is None:
                        ui.label("The map draws once both runs' fields are read.").classes("later")
                        continue
                    query = urlencode(
                        {"which": which, **({"frame": "whole"} if self.whole else {})}
                    )
                    drawing = map_drawing(
                        maps[which],
                        f"/api/analysis/compare/{name}/image?{query}",
                        cut_r_nm=self.cut_r_nm,
                        probes=tuple(self.probes),
                        outline_nm=self.compared_outline(which, runs),
                        mirrored=which == "mirrored",
                    )
                    host = f"analysis-map-{which}"
                    ui.element("div").props(f"id={host} data-control={host}").classes("tile-map")
                    if which == shown[0]:
                        self.link_chip()
                    await ui.run_javascript(
                        f"nano.map('{host}', {json.dumps(drawing.json())})", timeout=60
                    )
        with self.tile(f"Axial cut, r = {self.cut_r_nm:.3g} nm", "analysis-cut"):
            if not ready:
                ui.label("The cut draws once both runs' fields are read.").classes("later")
            else:
                cut = ChartView("analysis-cut-chart", "analysis-cut-chart", classes="tile-chart")
                cut.show(
                    cut_chart(
                        tuple(
                            (self.run_name(path), fields)
                            for path, fields in zip(runs, held, strict=True)
                        ),
                        compared.quantity,
                        self.cut_r_nm,
                        None if self.whole else pore_window(*held),
                    )
                )

    def compared_outline(self, which: str, runs: tuple[Path, ...]) -> tuple[Any, ...]:
        """Return the outlines a comparison's map draws: its run's, or both, the first mirrored."""
        assert self.model is not None
        if not self.outline:
            return ()
        first, second = (_outline(self.model, path) for path in runs)
        if which == "first":
            found: tuple[Any, ...] = (first,)
        elif which == "second":
            found = (second,)
        elif which == "mirrored" and first is not None:
            found = (first * [-1.0, 1.0, -1.0, 1.0], second)
        else:
            found = (first, second)
        return tuple(outline for outline in found if outline is not None)

    async def set_compared(self, **values: Any) -> None:  # noqa: ANN401 - the file's values
        assert self.model is not None and self.compared is not None
        try:
            self.model.project.set_comparison(self.compared, **values)
        except (ProjectError, ValueError) as error:
            ui.notify(str(error))
            return
        await self.redraw()

    # -- what the user does -------------------------------------------------------------------

    async def on_study(self, event: events.ValueChangeEventArguments[Any]) -> None:
        assert self.model is not None
        self.study = event.value
        found = self.model.choices(self.study) if self.study else ()
        self.choice = found[0] if found else None
        await self.redraw()

    async def on_run(self, event: events.ValueChangeEventArguments[Any]) -> None:
        assert self.model is not None and self.study is not None
        self.choice = next(
            (c for c in self.model.choices(self.study) if str(c.directory) == event.value), None
        )
        await self.redraw()

    async def on_quantity(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.quantity = event.value
        # A typed range is in the quantity's unit, so another quantity opens on its own.
        self.colour_range = None
        await self.redraw()

    async def on_palette(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.palette = event.value or None
        await self.redraw()

    async def on_compared_range(self, typed: tuple[float, float] | None) -> None:
        await self.set_compared(range=typed)

    async def on_range(self, typed: tuple[float, float] | None) -> None:
        self.colour_range = typed
        await self.redraw()

    async def on_frame(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.whole = event.value == "whole"
        await self.redraw()

    def on_placing(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.placing = event.value

    async def on_cut(self, event: events.ValueChangeEventArguments[Any]) -> None:
        if isinstance(event.value, int | float):
            self.cut_r_nm = max(0.0, float(event.value))
            await self.redraw()

    async def on_comparison(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.compared = event.value
        await self.redraw()

    async def on_point(self, event: events.GenericEventArguments) -> None:
        args = event.args if isinstance(event.args, dict) else {}
        if not str(args.get("host", "")).startswith("analysis-map"):
            return
        if not self.linked:
            return
        # A click is placed to a hundredth of a nm; a mirrored map's left half is the first run's.
        r_nm = round(abs(float(args.get("r", 0.0))), 2)
        z_nm = round(float(args.get("z", 0.0)), 2)
        if self.placing == "probe":
            self.probes.append((r_nm, z_nm))
        else:
            self.cut_r_nm = max(0.0, r_nm)
        await self.redraw()

    async def on_chart_pick(self, event: events.GenericEventArguments) -> None:
        # A point of the I-V picks the run it is.
        args = event.args if isinstance(event.args, dict) else {}
        if args.get("host") != "analysis-iv-chart" or self.model is None or self.choice is None:
            return
        bias_mV = args.get("x")
        if not isinstance(bias_mV, int | float):
            return
        for choice in self.model.choices(self.choice.study):
            if choice.bias_V is not None and abs(choice.bias_V * 1e3 - bias_mV) < 1e-9:
                self.choice = choice
                await self.redraw()
                return

    async def remove_probe(self, index: int) -> None:
        if 0 <= index < len(self.probes):
            del self.probes[index]
            await self.redraw()

    async def on_view(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.on_mesh = event.value == "mesh"
        await self.redraw()

    async def on_outline(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.outline = bool(event.value)
        await self.redraw()

    def open_runs(self, choice: RunChoice) -> None:
        self.shell.study = choice.study
        self.shell.recorded_shown = str(choice.directory)
        ui.navigate.to("/study/runs")

    def rebuild(self, choice: RunChoice) -> None:
        assert self.model is not None
        threads = int(str(self.shell.settings.value("threads_per_solve")))
        queue_rebuild(self.shell.queue, self.model.project, choice.directory, threads=threads)
        ui.notify("The run is queued to solve again; its fields show when it is done.")


def analysis_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Analysis tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        del field
        shell.last_tool["analysis"] = tool.id
        _AnalysisPage(shell, tool, built).build()

    return page

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
    RunChoice,
    cut_chart,
    difference_map,
    field_map,
    iv_chart,
    map_drawing,
    pair_maps,
    quantities_of,
    scene_field,
)
from nanopnp.gui.web.chart_view import ChartView
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.runs import queue_rebuild
from nanopnp.gui.web.screens import SUITES, Tool
from nanopnp.gui.web.shell import Shell
from nanopnp.io.project import COMPARISON_VIEWS, ComparisonFile
from nanopnp.post.fields import field_at, field_unit, joint_range

__all__ = ["analysis_page", "comparison_maps", "map_of"]

_RENDERS: dict[tuple[Path, str], RenderProcess] = {}
"""The render children of the runs' fields and scenes, by run and what they write."""

_FAILED: dict[tuple[Path, str], str] = {}
"""What a render child said where it drew nothing, by run and what it was asked for."""

_MAPS: dict[tuple[object, ...], FieldMap] = {}
_KEPT_MAPS = 8

VIEW_NAMES = {"difference": "Difference", "maps": "Side by side", "mesh": "On the mesh"}
"""Each view a comparison opens on, as its control names it."""


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
) -> FieldMap | None:
    """Return one run's map of a quantity, kept for the picture's request; None without fields."""
    fields = model.fields(run)
    if fields is None:
        return None
    key = ("run", run, model.solve_hash(run), quantity, palette, colour_range)
    return _kept(
        key, lambda: field_map(fields, quantity, palette=palette, colour_range=colour_range)
    )


def comparison_maps(model: AnalysisModel, name: str) -> dict[str, FieldMap] | None:
    """Return a comparison's maps, ``first``, ``second`` and ``difference``; None without fields.

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
    pair = (first_run, second_run, *stamp, *shown)
    left = _kept(
        ("first", *pair),
        lambda: pair_maps(
            first,
            second,
            compared.quantity,
            palette=compared.colour_map,
            colour_range=compared.range,
        )[0],
    )
    right = _kept(
        ("second", *pair),
        lambda: pair_maps(
            first,
            second,
            compared.quantity,
            palette=compared.colour_map,
            colour_range=compared.range,
        )[1],
    )
    difference = _kept(
        ("difference", *pair),
        lambda: difference_map(first, second, compared.quantity, palette=compared.colour_map),
    )
    return {"first": left, "second": right, "difference": difference}


def _relative(model: AnalysisModel, run: Path) -> str:
    try:
        return run.resolve().relative_to(model.project.root.resolve()).as_posix()
    except ValueError:
        return str(run)


def _render(key: tuple[Path, str], request: FieldsRequest | RenderRequest) -> None:
    held = _RENDERS.get(key)
    if held is not None and (held.running or not held.answered):
        return
    _FAILED.pop(key, None)
    process = RenderProcess(request)
    process.start()
    _RENDERS[key] = process


def _drained() -> bool:
    # Drain every child; True where one answered, so a page draws what it wrote.
    moved = False
    for key, process in list(_RENDERS.items()):
        for event in process.drain():
            moved = True
            if isinstance(event, RenderFailed):
                _FAILED[key] = event.message
        if not process.running and process.answered:
            del _RENDERS[key]
            moved = True
        elif not process.running and not process.answered:
            _FAILED[key] = "the render child ended without answering"
            del _RENDERS[key]
            moved = True
    return moved


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
        self.compared: str | None = None
        self.seen: object = None
        self.pane: ui.column
        self.status: ui.element
        self.view_box: ui.element
        self.ready = False

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

    def say(self, text: str) -> None:
        self.status.clear()
        with self.status:
            ui.label(text)

    async def tick(self) -> None:
        if _drained() and self.ready:
            await self.redraw()

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
            self.say("The project holds no study. Study's Study setup makes one.")
            self.empty_tiles("Run a study to see its result here.")
            return
        with self.pane:
            ui.select(
                list(studies), value=self.study, label="Study", on_change=self.on_study
            ).props("dense data-control=analysis-study").classes("w-full")
            choices = self.model.choices(self.study) if self.study else ()
            if not choices:
                self.say(f"Study {self.study} has no run yet. Study's Runs starts one.")
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
                ui.button("Rebuild", on_click=lambda: self.rebuild(choice)).props(
                    "outline dense no-caps data-control=analysis-rebuild"
                )
            quantities = quantities_of(fields) if fields is not None else ()
            if quantities:
                if self.quantity not in quantities:
                    self.quantity = quantities[0]
                self.field_controls(quantities)
                self.probe_controls(fields)
        with self.view_box, ui.element("div").classes("analysis-tiles"):
            with self.tile("Field", "analysis-field"):
                await self.field_tile(choice, fields)
            with self.tile("Current against bias", "analysis-iv"):
                chart = ChartView("analysis-iv-chart", "analysis-iv-chart", classes="tile-chart")
                chart.show(iv_chart(self.model.choices(choice.study), choice.directory))
            with self.tile("Quantities", "analysis-quantities"):
                self.quantities_tile(choice)
            with self.tile("Axial cut", "analysis-cut"):
                if fields is None:
                    ui.label("The cut draws once the run's fields are read.").classes("later")
                else:
                    cut = ChartView(
                        "analysis-cut-chart", "analysis-cut-chart", classes="tile-chart"
                    )
                    cut.show(cut_chart(((choice.label, fields),), self.quantity, self.cut_r_nm))

    def explain(self, choice: RunChoice, state: str, read: bool) -> None:
        assert self.model is not None
        if state == "removed":
            self.say(
                "This run's solve was cleaned from the store. Rebuild it to see its fields: the "
                "rebuild is checked against its record."
            )
        elif state == "unsolved":
            self.say("This run did not reach its solve: it has no fields.")
        elif not read:
            key = (choice.directory, "fields")
            if key in _FAILED:
                self.say(f"The run's fields did not read: {_FAILED[key]}")
            else:
                _render(key, FieldsRequest(run=str(choice.directory)))
                self.say("Reading the run's fields…")
        else:
            self.say(f"{choice.label}, of study {choice.study}.")

    def tile(self, title: str, control: str) -> Any:  # noqa: ANN401 - a NiceGUI element
        with (
            ui.element("section")
            .classes("analysis-tile")
            .props(f'data-control={control} aria-label="{title}"') as tile
        ):
            heading(title, 2)
        return tile

    def empty_tiles(self, text: str) -> None:
        with self.view_box:
            ui.label(text).classes("later")

    def field_controls(self, quantities: tuple[str, ...]) -> None:
        names = {
            key: f"{key} ({field_unit(key)})" if field_unit(key) else key for key in quantities
        }
        ui.select(names, value=self.quantity, label="Quantity", on_change=self.on_quantity).props(
            "dense data-control=analysis-quantity"
        ).classes("w-full")
        ui.select(
            ["", *colour_maps()],
            value=self.palette or "",
            label="Colour map",
            on_change=self.on_palette,
        ).props("dense data-control=analysis-colour-map").classes("w-full")
        ui.toggle(
            {"cut": "Cut", "probe": "Probe"}, value=self.placing, on_change=self.on_placing
        ).props(
            'dense no-caps data-control=analysis-placing aria-label="A click on the map places"'
        )
        ui.number("Cut at r (nm)", value=self.cut_r_nm, on_change=self.on_cut).props(
            "dense debounce=600 data-control=analysis-cut-r"
        )

    def probe_controls(self, fields: Any) -> None:  # noqa: ANN401 - a run's SolutionFields
        heading("Probes", 3)
        if not self.probes:
            ui.label("A click on the map with Probe chosen places one.").classes("field-hint")
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
        pressed = "true" if self.on_mesh else "false"
        ui.button("On the mesh", on_click=self.toggle_mesh).props(
            f"flat dense no-caps data-control=analysis-on-mesh aria-pressed={pressed}"
        )
        if fields is None:
            ui.label("The map draws once the run's fields are read.").classes("later")
            return
        if self.on_mesh:
            self.scene_frame(choice.directory, scene_field(self.quantity), None, "analysis-scene")
            return
        shown = await run.io_bound(
            map_of, self.model, choice.directory, self.quantity, self.palette
        )
        if shown is None:
            return
        query = urlencode(
            {
                "run": _relative(self.model, choice.directory),
                "quantity": self.quantity,
                "palette": self.palette or "",
            }
        )
        drawing = map_drawing(
            shown,
            f"/api/analysis/image?{query}",
            cut_r_nm=self.cut_r_nm,
            probes=tuple(self.probes),
        )
        ui.element("div").props("id=analysis-map data-control=analysis-map").classes("tile-map")
        await ui.run_javascript(
            f"nano.map('analysis-map', {json.dumps(drawing.json())})", timeout=60
        )

    def scene_frame(
        self, run_dir: Path, scene: str, colour_range: tuple[float, float] | None, control: str
    ) -> None:
        assert self.model is not None
        stem = scene_stem(scene, colour_range)
        key = (run_dir, stem)
        if (run_dir / "viewer" / f"{stem}.json").is_file():
            query = {"run": _relative(self.model, run_dir), "field": scene}
            if colour_range is not None:
                query["range"] = f"{colour_range[0]!r},{colour_range[1]!r}"
            ui.element("iframe").props(
                f'src="/api/analysis/view?{urlencode(query)}" data-control={control} '
                f'title="{scene} on the mesh"'
            ).classes("tile-scene")
        elif key in _FAILED:
            ui.label(f"The field did not draw on the mesh: {_FAILED[key]}").classes("state-err")
        else:
            _render(
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
                _render((path, "fields"), FieldsRequest(run=str(path)))
        if any(fields is None for fields in held):
            self.say("Reading the two runs' fields…")
        else:
            self.say(f"{compared.runs[0]} against {compared.runs[1]}.")
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
            both,
            value=compared.quantity,
            label="Quantity",
            on_change=lambda e: self.set_compared(quantity=e.value),
        ).props("dense data-control=analysis-quantity").classes("w-full")
        ui.toggle(
            {view: VIEW_NAMES[view] for view in COMPARISON_VIEWS},
            value=compared.view,
            on_change=lambda e: self.set_compared(view=e.value),
        ).props('dense no-caps data-control=analysis-view aria-label="The comparison shows"')
        ui.select(
            ["", *colour_maps()],
            value=compared.colour_map or "",
            label="Colour map",
            on_change=lambda e: self.set_compared(colour_map=e.value or None),
        ).props("dense data-control=analysis-colour-map").classes("w-full")
        ui.number("Cut at r (nm)", value=self.cut_r_nm, on_change=self.on_cut).props(
            "dense debounce=600 data-control=analysis-cut-r"
        )

    async def comparison_tiles(
        self, compared: ComparisonFile, runs: tuple[Path, ...], held: list[Any]
    ) -> None:
        assert self.model is not None and self.compared is not None
        ready = all(fields is not None for fields in held)
        name = self.compared
        if compared.view == "mesh":
            if ready:
                joint = joint_range(held[0], held[1], compared.quantity)
                for index, path in enumerate(runs):
                    with self.tile(compared.runs[index], f"analysis-pair-{index}"):
                        self.scene_frame(
                            path, scene_field(compared.quantity), joint, f"analysis-scene-{index}"
                        )
        else:
            maps = await run.io_bound(comparison_maps, self.model, name) if ready else None
            shown = ("difference",) if compared.view == "difference" else ("first", "second")
            for which in shown:
                title = (
                    "Second less first"
                    if which == "difference"
                    else compared.runs[0 if which == "first" else 1]
                )
                with self.tile(title, f"analysis-compare-{which}"):
                    if maps is None:
                        ui.label("The map draws once both runs' fields are read.").classes("later")
                        continue
                    query = urlencode({"which": which})
                    drawing = map_drawing(
                        maps[which],
                        f"/api/analysis/compare/{name}/image?{query}",
                        cut_r_nm=self.cut_r_nm,
                        probes=tuple(self.probes),
                    )
                    host = f"analysis-map-{which}"
                    ui.element("div").props(f"id={host} data-control={host}").classes("tile-map")
                    await ui.run_javascript(
                        f"nano.map('{host}', {json.dumps(drawing.json())})", timeout=60
                    )
        with self.tile("Axial cut", "analysis-cut"):
            if not ready:
                ui.label("The cut draws once both runs' fields are read.").classes("later")
            else:
                cut = ChartView("analysis-cut-chart", "analysis-cut-chart", classes="tile-chart")
                cut.show(
                    cut_chart(
                        tuple(zip(compared.runs, held, strict=True)),
                        compared.quantity,
                        self.cut_r_nm,
                    )
                )

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
        await self.redraw()

    async def on_palette(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.palette = event.value or None
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
        r_nm, z_nm = float(args.get("r", 0.0)), float(args.get("z", 0.0))
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

    async def toggle_mesh(self) -> None:
        self.on_mesh = not self.on_mesh
        await self.redraw()

    def open_runs(self, choice: RunChoice) -> None:
        self.shell.study = choice.study
        self.shell.recorded_shown = str(choice.directory)
        ui.navigate.to("/study/runs")

    def rebuild(self, choice: RunChoice) -> None:
        assert self.model is not None
        threads = int(str(self.shell.settings.value("threads_per_solve")))
        queue_rebuild(self.shell.queue, self.model.project, choice.directory, threads=threads)
        ui.notify("The rebuild is queued; the queue names each number it moves.")


def analysis_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Analysis tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        del field
        shell.last_tool["analysis"] = tool.id
        _AnalysisPage(shell, tool, built).build()

    return page

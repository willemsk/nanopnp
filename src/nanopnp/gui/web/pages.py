"""The workbench's pages, written in NiceGUI over the server's FastAPI app."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response
from nicegui import app as nicegui_app
from nicegui import events, ui

from nanopnp.gui.web.assets import ASSETS, TOKENS
from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.continuum_tools import continuum_page
from nanopnp.gui.web.frame import Route, Views, current_suite, frame, heading
from nanopnp.gui.web.link import Extent, png
from nanopnp.gui.web.molecular import MolecularModel
from nanopnp.gui.web.molview import (
    COLOURINGS,
    REPRESENTATIONS,
    annotation,
    frame_count,
    scene,
    structure_text,
)
from nanopnp.gui.web.physics import PhysicsModel
from nanopnp.gui.web.physics_tools import physics_page
from nanopnp.gui.web.plane import COLOURINGS as MESH_COLOURINGS
from nanopnp.gui.web.plane import IMAGES, image_png, physics_plane, plane
from nanopnp.gui.web.screens import SUITES, TOOL_SUITES, VIEWS, Suite, Tool, screen, tool_view
from nanopnp.gui.web.settings_page import SettingsPage
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.tools import OVERLAY_MOST, charge_colours, tool_page

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from fastapi import FastAPI

    from nanopnp.api.case import Case

__all__ = ["ROUTES", "install"]

MAP_WIDTH_PX = 330
BLANK = Extent(0.0, 1.0, 0.0, 1.0, MAP_WIDTH_PX, 440)
STYLESHEETS = (
    '<link rel="stylesheet" href="/tokens.css"><link rel="stylesheet" href="/workbench.css">'
)


def _route_of(suite: Suite, tool: Tool) -> Route:
    view = tool_view(suite, tool)
    # A view the page draws itself hides the frame's view region.
    return Route(suite.id, None if view == "page" else view)


ROUTES: dict[str, Route] = {
    # A suite with tools of its own opens the last one used, beside its view (WB-40); the frame
    # reads its path as that tool's.
    **{f"/{suite.id}": Route(suite.id, None) for suite in SUITES},
    **{f"/{suite.id}": Route(suite.id, VIEWS[suite.id]) for suite in TOOL_SUITES},
    **{
        f"/{suite.id}/{tool.id}": _route_of(suite, tool)
        for suite in TOOL_SUITES
        for tool in suite.tools
    },
    screen("st-charge").path: Route("study", "molecule"),
    "/settings": Route(None),
}
"""Every path the frame routes: its suite, and the view the frame shows beside it."""


def _blank_map() -> bytes:
    return png(b"\xe6\xe8\xec\xff" * BLANK.width * BLANK.height, BLANK.width, BLANK.height)


# The SVG of a residue's charged atoms, drawn over the map's picture.
def _markers(extent: Extent, markers: list[tuple[float, float, float]]) -> str:
    out = []
    for r_nm, z_nm, charge in markers:
        x, y = extent.pixel(r_nm, z_nm)
        colour = "#b4231a" if charge > 0 else "#1d4ed8"
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="none" stroke="#000" stroke-width="3"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="none" stroke="{colour}" '
            'stroke-width="1.5"/>'
        )
    return "".join(out)


def install(app: FastAPI, shell: Shell, secret: str) -> None:  # noqa: C901
    """Register the screens and their data routes on ``app``, and attach NiceGUI to it."""

    @app.get("/api/structure")
    def structure() -> Response:
        """Serve the first frame as PDB text, which the viewer reads."""
        link = shell.bench.link
        text = "" if link is None else link.structure_pdb
        return Response(text, media_type="chemical/x-pdb")

    @app.get("/api/map")
    def charge_map() -> Response:
        """Serve the charge map as a PNG."""
        link = shell.bench.link
        return Response(
            _blank_map() if link is None else link.map_png(charge_colours(shell)),
            media_type="image/png",
        )

    @app.get("/api/scene")
    def charge_scene() -> JSONResponse:
        """Serve the scene of the charge screen: the study's first frame, as Mol* styles it."""
        if shell.bench.link is None:
            return JSONResponse(None)
        return JSONResponse(scene(None, structure_url="/api/structure", annotation_url=None))

    def molecular(name: str) -> MolecularModel:
        project = shell.bench.project
        if project is None or name not in project.items("molecular"):
            raise HTTPException(404, f"no molecular model {name!r}")
        return MolecularModel(project, name, shell.queue)

    def continuum(name: str) -> ContinuumModel:
        project = shell.bench.project
        if project is None or name not in project.items("continuum"):
            raise HTTPException(404, f"no continuum model {name!r}")
        return ContinuumModel(project, name, shell.queue)

    @app.get("/api/continuum/{name}/plane")
    def continuum_plane(
        name: str,
        tool: str = "geometry",
        image: str = "mean",
        colour: str = "material",
        band: str = "",
        pick: str = "",
        held: str = "",
    ) -> JSONResponse:
        """Serve what the (r, z) view draws of a model for one tool, less the mesh it holds."""
        if image not in IMAGES or colour not in MESH_COLOURINGS:
            raise HTTPException(422, "an unknown picture or colouring")
        try:
            low, _, high = band.partition(",")
            outlined = (float(low), float(high)) if band else None
            model = continuum(name)
            with model.keyed_once():
                drawn = plane(
                    model,
                    tool,
                    image=image,
                    colour=colour,
                    band=outlined,
                    pick=pick,
                    mesh_held=held,
                )
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        return JSONResponse(drawn.json())

    @app.get("/api/physics/{name}/plane")
    def physics_view(
        name: str,
        tool: str = "electrolyte",
        within: str = "",
        against: str = "driver",
        pick: str = "",
        held: str = "",
    ) -> JSONResponse:
        """Serve what the view draws of a physics model for one tool, inside the study shown."""
        project = shell.bench.project
        if project is None or name not in project.items("physics"):
            raise HTTPException(404, f"no physics model {name!r}")
        model = PhysicsModel(project, name, shell.queue, shown_in=within or None)
        try:
            # A case the study refuses still loads: the view resolves it, and says it does not.
            case: Case | None = project.physics_case(name, model.within())
        except REFUSED:
            case = None
        try:
            with model.keyed_once():
                drawn = physics_plane(
                    case,
                    project.session().store,
                    tool,
                    against=against,
                    pick=pick or None,
                    mesh_held=held,
                )
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        return JSONResponse(drawn.json())

    @app.get("/api/continuum/{name}/image")
    def continuum_image(name: str, layer: str = "mean") -> Response:
        """Serve one picture of a model's built stages as a PNG."""
        if layer not in IMAGES:
            raise HTTPException(422, f"layer: {layer!r} is not one of {', '.join(IMAGES)}")
        found = image_png(continuum(name), layer)
        if found is None:
            raise HTTPException(404, f"the {layer} picture of {name!r} is not built")
        return Response(found, media_type="image/png")

    @app.get("/api/molecular/{name}/structure")
    def molecular_structure(name: str, frame: int = 0) -> Response:
        """Serve what the view draws of a model: one built frame, else its source file."""
        text, form = structure_text(molecular(name), frame)
        return Response(text, media_type="chemical/x-pdb" if form == "pdb" else "chemical/x-cif")

    @app.get("/api/molecular/{name}/annotation")
    def molecular_annotation(name: str, by: str = "chain") -> JSONResponse:
        """Serve one colour per residue, as a MolViewSpec annotation."""
        if by not in COLOURINGS:
            raise HTTPException(422, f"by: {by!r} is not one of {', '.join(COLOURINGS)}")
        return JSONResponse(annotation(molecular(name), by, positive=charge_colours(shell)))

    @app.get("/api/molecular/{name}/scene")
    def molecular_scene(
        name: str,
        representation: str = "cartoon",
        colour: str = "chain",
        frame: int = 0,
        overlay: int = 0,
        side: int = 0,
        clip: int = 0,
    ) -> JSONResponse:
        """Serve the MolViewSpec scene of a model, or null where it has nothing to draw."""
        if representation not in REPRESENTATIONS or colour not in COLOURINGS:
            raise HTTPException(422, "an unknown representation or colouring")
        model = molecular(name)
        with model.keyed_once():
            text, form = structure_text(model)
            if not text:
                return JSONResponse(None)
            # The viewer keeps what it read from an address, so a rebuilt structure takes a new one.
            stamp = f"{hashlib.sha256(text.encode()).hexdigest()[:12]}-{charge_colours(shell)}"
            return JSONResponse(
                scene(
                    model,
                    structure_url=f"/api/molecular/{name}/structure?v={stamp}",
                    # Until a stage is built there is nothing to colour by: Mol*'s colours stand.
                    annotation_url=(
                        f"/api/molecular/{name}/annotation?by={colour}&v={stamp}"
                        if annotation(model, colour)
                        else None
                    ),
                    representation=representation,
                    form=form,
                    frames=(
                        range(min(frame_count(model), OVERLAY_MOST))
                        if overlay
                        else (max(frame, 0),)
                    ),
                    side_on=model.membrane()[0] if side or clip else None,
                    clip=bool(clip),
                )
            )

    nicegui_app.add_static_files("/vendor/molstar", ASSETS / "molstar")
    # Our own small files are not cached (max-age 0): NiceGUI's hour of caching would hide an edit
    # that `nanopnp gui --dev` restarted the server for.
    for local, url in (
        (TOKENS, "/tokens.css"),
        (ASSETS / "bridge.js", "/bridge.js"),
        (ASSETS / "plane.js", "/plane.js"),
        (ASSETS / "workbench.css", "/workbench.css"),
        (ASSETS / "frame.js", "/frame.js"),
        (ASSETS / "frame.css", "/frame.css"),
    ):
        nicegui_app.add_static_file(local_file=local, url_path=url, max_cache_age=0)

    def page_of(suite: Suite, tool: Tool) -> Callable[..., None]:
        pages = {"molecular": tool_page, "continuum": continuum_page, "physics": physics_page}
        return pages[suite.id](shell, tool)

    def suite_page(suite: Suite) -> Callable[..., None]:
        if suite in TOOL_SUITES:

            def last(built: Views, field: str = "") -> None:
                chosen = shell.last_tool.get(suite.id)
                tool = next((t for t in suite.tools if t.id == chosen), suite.tools[0])
                page_of(suite, tool)(built, field)

            return last

        def page(built: Views) -> None:
            bench = shell.bench
            with ui.column().props("data-control=suite-body"):
                heading(f"{suite.title} suite", 1)
                ui.label(f"This suite builds {suite.builds}.")
                for tool in suite.tools:
                    if f"/{suite.id}/{tool.id}" in ROUTES:
                        ui.link(tool.title, f"/{suite.id}/{tool.id}").props(
                            f"data-control=open-{tool.id}"
                        )
                    else:
                        ui.label(f"{tool.title}: in a later package").classes("later")
                if suite.id == "study":
                    ui.label(f"State: {bench.name}").props("data-control=state")
                    with ui.row().props("data-control=stages"):
                        for stage in bench.stages:
                            ui.badge(stage)
                        if not bench.stages:
                            ui.label("No stage has run.")
                    if bench.refusal:
                        ui.label(f"✕ blocked: {bench.refusal}").classes("refused")
                    if bench.notice:
                        ui.label(bench.notice)

            async def ready() -> None:
                await built.settled()
                await ui.run_javascript("document.body.dataset.screenReady = '1'", timeout=10)

            ui.timer(0.1, ready, once=True)

        return page

    def charge(built: Views, residue: str = "", linked: int = 1) -> None:
        bench = shell.bench
        link = bench.link
        extent = BLANK if link is None else link.extent
        state = {"key": "", "linked": bool(linked)}
        buttons: dict[str, ui.button] = {}

        async def select(key: str, *, move_mol: bool = True) -> None:
            if link is None or key not in link:
                return
            if state["key"] in buttons:
                buttons[state["key"]].props("aria-pressed=false")
            state["key"] = key
            if key in buttons:
                buttons[key].props("aria-pressed=true")
            image.content = _markers(extent, link.residue_markers(key))
            status.text = f"Residue {key}"
            await ui.run_javascript(f"nano.show({key!r})" if move_mol else "nano.drawn()")

        async def on_map(event: events.MouseEventArguments) -> None:
            if link is None or not state["linked"]:
                return
            found = link.residues_at(*extent.point(event.image_x, event.image_y))
            if found:
                await select(found[0][0])

        async def on_mol(event: events.GenericEventArguments) -> None:
            if state["linked"]:
                await select(event.args["key"], move_mol=False)

        def toggle_link() -> None:
            state["linked"] = not state["linked"]
            chip.text = "Linked" if state["linked"] else "Unlinked"
            unlink.text = "Unlink" if state["linked"] else "Link"

        built.listen("mol_pick", on_mol)
        with ui.column().classes("items-start"):
            heading("Charge on the mesh", 1)
            with ui.row().props("data-control=strip").style(f"width:{MAP_WIDTH_PX}px;gap:2px"):
                for key, name, _ in [] if link is None else link.residues():
                    buttons[key] = (
                        ui.button(f"{key} {name}", on_click=lambda _, k=key: select(k))
                        .props(
                            "flat dense no-caps size=sm aria-pressed=false "
                            f"data-control=strip-item data-residue={key}"
                        )
                        .classes("strip-item")
                    )
            with ui.column():
                with ui.row().classes("items-center"):
                    chip = ui.badge("Linked" if linked else "Unlinked").props(
                        "data-control=link-chip"
                    )
                    unlink = ui.button("Unlink" if linked else "Link", on_click=toggle_link).props(
                        "flat dense no-caps data-control=unlink"
                    )
                    status = ui.label(
                        bench.refusal
                        or bench.notice
                        or ("Pick a residue." if link else "No case is loaded.")
                    ).props("data-control=status")
                image = (
                    ui.interactive_image("/api/map", on_mouse=on_map, events=["click"], cross=False)
                    .props("data-control=map")
                    .style(f"width:{MAP_WIDTH_PX}px")
                )

        async def start() -> None:
            await built.show_molecule(None if link is None else "/api/scene", "study")
            if residue:
                await select(residue)

        ui.timer(0.1, start, once=True)

    def settings_page(built: Views, setting: str = "") -> None:
        SettingsPage(shell, built, setting).build()

        async def ready() -> None:
            await built.settled()
            if setting:
                await ui.run_javascript(
                    f"document.getElementById('setting-{setting}')?.scrollIntoView()", timeout=10
                )
            await ui.run_javascript("document.body.dataset.screenReady = '1'", timeout=10)

        ui.timer(0.1, ready, once=True)

    pages: dict[str, Callable[..., None]] = {
        **{f"/{suite.id}": suite_page(suite) for suite in SUITES},
        **{
            f"/{suite.id}/{tool.id}": page_of(suite, tool)
            for suite in TOOL_SUITES
            for tool in suite.tools
        },
        screen("st-charge").path: charge,
        "/settings": settings_page,
    }

    def build(panel: str = "", palette: str = "", dialog: str = "") -> None:
        ui.add_head_html(
            '<link rel="stylesheet" href="/vendor/molstar/molstar.css">'
            + STYLESHEETS
            + '<script src="/vendor/molstar/molstar.js"></script><script src="/bridge.js"></script>'
            + '<script src="/plane.js"></script>'
        )
        with frame(
            shell,
            ROUTES,
            panel=panel or None,
            palette=palette or None,
            dialog=dialog or None,
        ) as built:
            current = f"/{current_suite(shell)}"
            ui.sub_pages({"/": pages[current], **pages}, data={"built": built})

    # One page builds the frame once; the sub-pages route every path beneath it.
    @ui.page("/")
    def root(panel: str = "", palette: str = "", dialog: str = "") -> None:
        build(panel, palette, dialog)

    @ui.page("/{_:path}")
    def anywhere(panel: str = "", palette: str = "", dialog: str = "") -> None:
        build(panel, palette, dialog)

    ui.run_with(app, storage_secret=secret, title="nanopnp workbench")

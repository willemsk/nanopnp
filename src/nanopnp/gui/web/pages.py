"""The workbench's pages, written in NiceGUI over the server's FastAPI app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import RedirectResponse, Response
from nicegui import app as nicegui_app
from nicegui import events, ui

from nanopnp.gui.web.assets import ASSETS, TOKENS
from nanopnp.gui.web.frame import frame
from nanopnp.gui.web.link import Extent, png
from nanopnp.gui.web.screens import SUITES, Suite, screen
from nanopnp.gui.web.shell import Shell
from nanopnp.io.project import ITEM_SUITES, split_reference

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from fastapi import FastAPI

__all__ = ["install"]

MAP_WIDTH_PX = 330
BLANK = Extent(0.0, 1.0, 0.0, 1.0, MAP_WIDTH_PX, 440)
STYLESHEETS = (
    '<link rel="stylesheet" href="/tokens.css"><link rel="stylesheet" href="/workbench.css">'
)


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


def install(app: FastAPI, shell: Shell, secret: str) -> None:
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
        return Response(_blank_map() if link is None else link.map_png, media_type="image/png")

    nicegui_app.add_static_files("/vendor/molstar", ASSETS / "molstar")
    # Our own small files are not cached (max-age 0): NiceGUI's hour of caching would hide an edit
    # that `nanopnp gui --dev` restarted the server for.
    for local, url in (
        (TOKENS, "/tokens.css"),
        (ASSETS / "bridge.js", "/bridge.js"),
        (ASSETS / "workbench.css", "/workbench.css"),
        (ASSETS / "frame.js", "/frame.js"),
        (ASSETS / "frame.css", "/frame.css"),
    ):
        nicegui_app.add_static_file(local_file=local, url_path=url, max_cache_age=0)

    async def ready() -> None:
        await ui.run_javascript("document.body.dataset.screenReady = '1'", timeout=10)

    def current_suite() -> str:
        current = shell.bench.project.current if shell.bench.project else None
        try:
            kind, _ = split_reference(current or "")
        except ValueError:
            return "molecular"
        return ITEM_SUITES[kind]

    @ui.page("/")
    def root() -> RedirectResponse:
        return RedirectResponse(f"/{current_suite()}")

    def suite_page(suite: Suite) -> None:
        @ui.page(f"/{suite.id}")
        def page(panel: str = "", palette: int = 0, dialog: str = "") -> None:
            bench = shell.bench
            ui.add_head_html(STYLESHEETS)
            with frame(
                shell, suite.id, panel=panel or None, palette=bool(palette), dialog=dialog or None
            ):
                with ui.column().props("data-control=suite-body"):
                    ui.label(suite.title).classes("text-h5")
                    ui.label(f"This suite builds {suite.builds}.")
                    for tool in suite.tools:
                        if tool == "Charge on the mesh":
                            ui.link(tool, screen("st-charge").path).props(
                                "data-control=open-charge"
                            )
                        else:
                            ui.label(f"{tool}: in a later package").classes("later")
                    if suite.id == "study":
                        ui.label(f"State: {bench.name}").props("data-control=state")
                        with ui.row().props("data-control=stages"):
                            for stage in bench.stages:
                                ui.badge(stage)
                            if not bench.stages:
                                ui.label("No stage has run.")
                        if bench.refusal:
                            ui.label(f"✕ refused: {bench.refusal}").classes("refused")
                        if bench.notice:
                            ui.label(bench.notice)
            ui.timer(0.1, ready, once=True)

    for suite in SUITES:
        suite_page(suite)

    @ui.page(screen("st-charge").path)
    def charge(residue: str = "", linked: int = 1) -> None:
        ui.add_head_html(
            '<link rel="stylesheet" href="/vendor/molstar/molstar.css">'
            + STYLESHEETS
            + '<script src="/vendor/molstar/molstar.js"></script><script src="/bridge.js"></script>'
        )
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

        ui.on("mol_pick", on_mol)
        with frame(shell, "study"):
            with ui.row().classes("items-start no-wrap"):
                with ui.column():
                    ui.element("div").props("id=mol data-control=molecule")
                    with ui.row().props("data-control=strip").style("width:560px;gap:2px"):
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
                        unlink = ui.button(
                            "Unlink" if linked else "Link", on_click=toggle_link
                        ).props("flat dense no-caps data-control=unlink")
                        status = ui.label(
                            bench.refusal
                            or bench.notice
                            or ("Pick a residue." if link else "No case is loaded.")
                        ).props("data-control=status")
                    image = (
                        ui.interactive_image(
                            "/api/map", on_mouse=on_map, events=["click"], cross=False
                        )
                        .props("data-control=map")
                        .style(f"width:{MAP_WIDTH_PX}px")
                    )

        async def start() -> None:
            # A long timeout: Mol* builds in seconds on a machine with no GPU.
            await ui.run_javascript(
                f"nano.init({'null' if link is None else repr('/api/structure')})", timeout=60
            )
            if residue:
                await select(residue)

        ui.timer(0.1, start, once=True)

    ui.run_with(app, storage_secret=secret, title="nanopnp workbench")

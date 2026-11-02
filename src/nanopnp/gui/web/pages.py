"""The workbench's pages, written in NiceGUI over the server's FastAPI app."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Response
from nicegui import app as nicegui_app
from nicegui import events, ui

from nanopnp.gui.web.link import Extent, png
from nanopnp.gui.web.screens import screen

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from fastapi import FastAPI

    from nanopnp.gui.web.states import Workbench

__all__ = ["install"]

ASSETS = Path(__file__).resolve().parent / "assets"
# The wheel carries tokens.css beside the assets; a checkout reads the design's own copy.
TOKENS = (
    ASSETS / "tokens.css"
    if (ASSETS / "tokens.css").is_file()
    else Path(__file__).resolve().parents[4] / "docs" / "design" / "tokens.css"
)
MAP_WIDTH_PX = 330
BLANK = Extent(0.0, 1.0, 0.0, 1.0, MAP_WIDTH_PX, 440)
STYLE = (
    "body{background:var(--bg);color:var(--ink);font-family:var(--font-ui)}"
    "#mol{position:relative;width:560px;height:420px;background:var(--canvas-3d)}"
    "[data-control=strip],[data-control=stages]{min-height:1.75rem}"
)


def _blank_map() -> bytes:
    return png(b"\xe6\xe8\xec\xff" * BLANK.width * BLANK.height, BLANK.width, BLANK.height)


def _markers(extent: Extent, markers: list[tuple[float, float, float]]) -> str:
    """Return the SVG of a residue's charged atoms, drawn over the map's picture."""
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


def install(app: FastAPI, bench: Workbench, secret: str) -> None:
    """Register the screens and their data routes on ``app``, and attach NiceGUI to it."""
    link = bench.link

    @app.get("/api/structure")
    def structure() -> Response:
        """Serve the first frame as PDB text, which the viewer reads."""
        text = "" if link is None else link.structure_pdb
        return Response(text, media_type="chemical/x-pdb")

    @app.get("/api/map")
    def charge_map() -> Response:
        """Serve the charge map as a PNG."""
        return Response(_blank_map() if link is None else link.map_png, media_type="image/png")

    nicegui_app.add_static_files("/vendor/molstar", ASSETS / "molstar")
    nicegui_app.add_static_file(local_file=TOKENS, url_path="/tokens.css")
    nicegui_app.add_static_file(local_file=ASSETS / "bridge.js", url_path="/bridge.js")

    async def ready() -> None:
        await ui.run_javascript("document.body.dataset.screenReady = '1'")

    @ui.page(screen("home").path)
    def home() -> None:
        ui.add_head_html(f'<link rel="stylesheet" href="/tokens.css"><style>{STYLE}</style>')
        ui.label("nanopnp workbench").classes("text-h5")
        ui.label(f"State: {bench.name}").props("data-control=state")
        with ui.row().props("data-control=stages"):
            for stage in bench.stages:
                ui.badge(stage)
            if not bench.stages:
                ui.label("No stage has run.")
            if bench.refusal:
                ui.label(f"Refused: {bench.refusal}")
        ui.link("Charge on the mesh", screen("st-charge").path).props("data-control=open-charge")
        ui.timer(0.1, ready, once=True)

    @ui.page(screen("st-charge").path)
    def charge(residue: str = "", linked: int = 1) -> None:
        ui.add_head_html(
            '<link rel="stylesheet" href="/vendor/molstar/molstar.css">'
            '<link rel="stylesheet" href="/tokens.css">'
            '<script src="/vendor/molstar/molstar.js"></script><script src="/bridge.js"></script>'
            f"<style>{STYLE}</style>"
        )
        extent = BLANK if link is None else link.extent
        state = {"key": "", "linked": bool(linked)}
        buttons: dict[str, ui.button] = {}

        async def select(key: str, *, move_mol: bool = True) -> None:
            if link is None or key not in link:
                return
            if state["key"] in buttons:
                buttons[state["key"]].props("color=grey-3 text-color=black")
            state["key"] = key
            if key in buttons:
                buttons[key].props("color=primary text-color=white")
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
        with ui.row().classes("items-start no-wrap"):
            with ui.column():
                ui.element("div").props("id=mol data-control=molecule")
                with ui.row().props("data-control=strip").style("width:560px;gap:2px"):
                    for key, name, _ in [] if link is None else link.residues():
                        buttons[key] = ui.button(
                            f"{key} {name}", on_click=lambda _, k=key: select(k)
                        ).props(f"dense no-caps size=sm data-control=strip-item data-residue={key}")
            with ui.column():
                with ui.row().classes("items-center"):
                    chip = ui.badge("Linked" if linked else "Unlinked").props(
                        "data-control=link-chip"
                    )
                    unlink = ui.button("Unlink" if linked else "Link", on_click=toggle_link).props(
                        "flat dense data-control=unlink"
                    )
                    status = ui.label(
                        bench.refusal or ("Pick a residue." if link else "No case is loaded.")
                    ).props("data-control=status")
                image = (
                    ui.interactive_image("/api/map", on_mouse=on_map, events=["click"], cross=False)
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

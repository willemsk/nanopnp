"""The NiceGUI candidate: the hard screen, written in Python over the shared server."""

from __future__ import annotations

import argparse
from pathlib import Path

from nicegui import app as nicegui_app
from nicegui import ui

from server.app import app, link, point, structure_path
from server.run import serve

HERE = Path(__file__).resolve().parent
MOLSTAR = HERE.parent / "react" / "node_modules" / "molstar" / "build" / "viewer"
TOKENS = HERE.parents[2] / "docs" / "design" / "tokens.css"

nicegui_app.add_static_files("/vendor/molstar", MOLSTAR)
nicegui_app.add_static_file(local_file=TOKENS, url_path="/tokens.css")
nicegui_app.add_static_file(local_file=HERE / "bridge.js", url_path="/bridge.js")

MAP_WIDTH = 330


def markers_svg(markers: list[tuple[float, float, float]]) -> str:
    extent = link().extent
    w, h = extent["width"], extent["height"]
    out = []
    for r, z, q in markers:
        x = (r - extent["r_low"]) / (extent["r_high"] - extent["r_low"]) * w
        y = (extent["z_high"] - z) / (extent["z_high"] - extent["z_low"]) * h
        colour = "#b4231a" if q > 0 else "#1d4ed8"
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="none" stroke="#000" stroke-width="3"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="none" stroke="{colour}" stroke-width="1.5"/>'
        )
    return "".join(out)


@ui.page("/")
def index(tab: str = "study", residue: str = "", linked: int = 1) -> None:
    ui.add_head_html(
        '<link rel="stylesheet" href="/vendor/molstar/molstar.css">'
        '<link rel="stylesheet" href="/tokens.css">'
        '<script src="/vendor/molstar/molstar.js"></script><script src="/bridge.js"></script>'
        "<style>body{background:var(--bg);color:var(--ink);font-family:var(--font-ui)}"
        "#mol{position:relative;width:560px;height:420px;background:var(--canvas-3d)}</style>"
    )
    extent = link().extent
    state = {"key": None, "linked": bool(linked)}
    residues = link().residues()
    buttons: dict[str, ui.button] = {}

    async def select(key: str, *, move_mol: bool = True) -> None:
        previous = state["key"]
        state["key"] = key
        if previous in buttons:
            buttons[previous].props("color=grey-3 text-color=black")
        if key in buttons:
            buttons[key].props("color=primary text-color=white")
        image.content = markers_svg(link().residue_markers(key))
        status.text = f"Residue {key}"
        if move_mol:
            await ui.run_javascript(f"nano.show({key!r})")
        else:
            await ui.run_javascript("nano.drawn()")

    async def on_map(event) -> None:
        if not state["linked"]:
            return
        r = extent["r_low"] + event.image_x / extent["width"] * (extent["r_high"] - extent["r_low"])
        z = extent["z_high"] - event.image_y / extent["height"] * (extent["z_high"] - extent["z_low"])
        found = point(r, z)["residues"]
        if found:
            await select(str(found[0]["key"]))

    async def on_mol(event) -> None:
        if state["linked"]:
            key = event.args["key"]
            await select(key, move_mol=False)

    def toggle_link() -> None:
        state["linked"] = not state["linked"]
        chip.text = "Linked" if state["linked"] else "Unlinked"
        unlink.text = "Unlink" if state["linked"] else "Link"

    ui.on("mol_pick", on_mol)
    with ui.tabs().props("data-control=tabs") as tabs:
        study = ui.tab("Charge on the mesh").props("data-control=tab-study")
        sketch = ui.tab("Sketcher").props("data-control=tab-sketcher")
    with ui.tab_panels(tabs, value=sketch if tab == "sketcher" else study).props("keep-alive"):
        with ui.tab_panel(study):
            with ui.row().classes("items-start no-wrap"):
                with ui.column():
                    ui.element("div").props("id=mol data-control=molecule")
                    with ui.row().props("data-control=strip").style("max-width:560px;gap:2px"):
                        for item in residues:
                            key = str(item["key"])
                            buttons[key] = (
                                ui.button(f'{item["name"]}{key}', on_click=lambda _, k=key: select(k))
                                .props(f"dense no-caps size=sm data-control=strip-item data-residue={key}")
                            )
                with ui.column():
                    with ui.row().classes("items-center"):
                        chip = ui.badge("Linked" if linked else "Unlinked").props("data-control=link-chip")
                        unlink = ui.button("Unlink" if linked else "Link", on_click=toggle_link).props("flat dense data-control=unlink")
                        status = ui.label("")
                    image = (
                        ui.interactive_image("/api/map", on_mouse=on_map, events=["click"], cross=False)
                        .props("data-control=map")
                        .style(f"width:{MAP_WIDTH}px")
                    )
        with ui.tab_panel(sketch):
            ui.label("The sketcher arrives in a later phase.").props("data-control=banner")
            ui.html('<canvas data-control="sketcher-canvas" width="400" height="200" '
                    'style="border:1px solid var(--control-edge)"></canvas>')

    async def start() -> None:
        if tab == "sketcher":
            await ui.run_javascript("document.body.dataset.screenReady = '1'")
            return
        await ui.run_javascript("nano.init()", timeout=60)
        if residue:
            await select(residue)

    ui.timer(0.1, start, once=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    ui.run_with(app, storage_secret="spike")
    serve(app, args.port)


if __name__ in {"__main__", "__mp_main__"}:
    main()

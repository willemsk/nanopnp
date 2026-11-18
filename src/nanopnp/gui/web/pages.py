"""The workbench's pages, written in NiceGUI over the server's FastAPI app."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, Literal, cast

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response
from nicegui import app as nicegui_app
from nicegui import ui

from nanopnp.gui.web.assets import ASSETS, TOKENS
from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.continuum_tools import continuum_page
from nanopnp.gui.web.frame import Route, Views, current_suite, frame, heading
from nanopnp.gui.web.molecular import MolecularModel
from nanopnp.gui.web.molview import (
    COLOURINGS,
    REPRESENTATIONS,
    annotation,
    charge_rows,
    first_frame_pdb,
    frame_count,
    has_backbone,
    pqr_frame,
    pqr_pdb,
    scene,
    structure_text,
    study_side_view,
)
from nanopnp.gui.web.physics import PhysicsModel
from nanopnp.gui.web.physics_tools import physics_page
from nanopnp.gui.web.plane import COLOURINGS as MESH_COLOURINGS
from nanopnp.gui.web.plane import (
    IMAGES,
    charge_plane,
    electrolyte_plane,
    image_png,
    physics_plane,
    plane,
    png,
)
from nanopnp.gui.web.screens import SUITES, TOOL_SUITES, VIEWS, Suite, Tool, tool_view
from nanopnp.gui.web.settings_page import SettingsPage
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.study import StudyModel
from nanopnp.gui.web.study_tools import study_page
from nanopnp.gui.web.tools import OVERLAY_MOST, charge_colours, tool_page

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from fastapi import FastAPI

    from nanopnp.api.case import Case

__all__ = ["ROUTES", "install"]

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
    "/settings": Route(None),
}
"""Every path the frame routes: its suite, and the view the frame shows beside it."""


def install(app: FastAPI, shell: Shell, secret: str) -> None:  # noqa: C901
    """Register the screens and their data routes on ``app``, and attach NiceGUI to it."""

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
        pick: str = "",
        held: str = "",
        mesh: str = "",
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
        if case is None and tool == "electrolyte":
            # A model with no salt forms no case, but its own block draws the curves against the
            # driver, which read no salt.
            electrolyte = model.own_electrolyte()
            if electrolyte is not None:
                return JSONResponse(electrolyte_plane(electrolyte, None).json())
        try:
            drawn = physics_plane(
                case,
                project.session().store,
                tool,
                pick=pick or None,
                mesh_held=held,
                mesh=bool(mesh),
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

    def study(name: str) -> StudyModel:
        project = shell.bench.project
        if project is None or name not in project.items("study"):
            raise HTTPException(404, f"no study {name!r}")
        return StudyModel(project, name, shell.queue)

    def colours(positive: str) -> Literal["blue", "red"]:
        if positive not in ("blue", "red"):
            raise HTTPException(422, f"positive: {positive!r} is not blue or red")
        return cast("Literal['blue', 'red']", positive)

    @app.get("/api/study/{name}/charge/plane")
    def study_charge(
        name: str, layer: str = "lattice", residue: str = "", positive: str = "blue"
    ) -> JSONResponse:
        """Serve a study's charge on the mesh as the (r, z) view draws it, a residue marked."""
        if layer not in ("lattice", "deployed"):
            raise HTTPException(422, f"layer: {layer!r} is not lattice or deployed")
        model = study(name)
        with model.keyed_once():
            charge = model.artefacts().get("charge")
            charges = model.charges()
            markers = charges.markers(residue) if charges is not None and residue in charges else []
            digest = "" if charge is None else charge.hash[:12]
            drawn = charge_plane(
                model.charge_map(),
                model.conservation(),
                image_url=f"/api/study/{name}/charge/image?positive={positive}&v={digest}",
                positive=colours(positive),
                deployed=model.elements(),
                layer="deployed" if layer == "deployed" else "lattice",
                picked=(residue, markers) if markers else None,
            )
        return JSONResponse(drawn.json())

    @app.get("/api/study/{name}/charge/image")
    def study_charge_image(name: str, positive: str = "blue") -> Response:
        """Serve a study's charge lattice as a PNG, a positive charge in the named colour."""
        shown = study(name).charge_map()
        if shown is None:
            raise HTTPException(404, f"study {name!r} stores no charge lattice")
        import numpy as np

        blue = colours(positive) == "blue"
        # Where the lattice carries no charge the canvas shows through, on either theme.
        values = np.where(shown.image.values == 0.0, np.nan, shown.image.values)
        image = replace(shown.image, values=values, palette="diverging_r" if blue else "diverging")
        return Response(png(image.rgba(), image.width, image.height), media_type="image/png")

    @app.get("/api/study/{name}/residues")
    def study_residues(name: str, r: float, z: float) -> JSONResponse:
        """Serve the residues that add most charge at a point of the map, the most first."""
        charges = study(name).charges()
        found = [] if charges is None else charges.at(r, z)
        return JSONResponse([{"key": key, "e_per_nm3": value} for key, value in found])

    @app.get("/api/study/{name}/structure")
    def study_structure(name: str) -> Response:
        """Serve the study's atoms as PDB text: its protonated first frame, else its PQR."""
        model = study(name)
        table = model.table()
        pqr = None if table is not None else pqr_frame(model.pqr())
        text = first_frame_pdb(table) if table is not None else "" if pqr is None else pqr_pdb(pqr)
        return Response(text, media_type="chemical/x-pdb")

    @app.get("/api/study/{name}/annotation")
    def study_annotation(name: str, positive: str = "blue") -> JSONResponse:
        """Serve one colour per residue by its net charge, as a MolViewSpec annotation."""
        model = study(name)
        table = model.table()
        pqr = None if table is not None else pqr_frame(model.pqr())
        return JSONResponse(charge_rows(table, pqr, positive=colours(positive)))

    @app.get("/api/study/{name}/scene")
    def study_scene(
        name: str, positive: str = "blue", v: str = "", subunit: int = 0
    ) -> JSONResponse:
        """Serve the scene of a study's structure from the side, cut at the axis or one subunit.

        Its residues are coloured by their charge.
        """
        model = study(name)
        table = model.table()
        pqr = None if table is not None else pqr_frame(model.pqr())
        seen = study_side_view(table, pqr)
        if seen is None:
            return JSONResponse(None)
        alone = bool(subunit) and seen.chain is not None
        return JSONResponse(
            scene(
                None,
                structure_url=f"/api/study/{name}/structure?v={v}",
                annotation_url=f"/api/study/{name}/annotation?positive={colours(positive)}&v={v}",
                # Atoms with no backbone, as a fixture's charges, draw as balls: a cartoon
                # draws nothing of them.
                representation="cartoon" if has_backbone(table, pqr) else "spacefill",
                clip=not alone,
                side_on=replace(seen, alone=alone),
            )
        )

    def pump() -> None:
        # The server's one queue: each build, run and sweep member waits for a slot here.
        queue = shell.queue
        queue.limit = int(str(shell.settings.value("solves_at_once")))
        queue.tick()

    nicegui_app.timer(0.25, pump)

    nicegui_app.add_static_files("/vendor/molstar", ASSETS / "molstar")
    nicegui_app.add_static_files("/vendor/katex", ASSETS / "katex")
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
        pages = {
            "molecular": tool_page,
            "continuum": continuum_page,
            "physics": physics_page,
            "study": study_page,
        }
        return pages[suite.id](shell, tool)

    def suite_page(suite: Suite) -> Callable[..., None]:
        if suite in TOOL_SUITES:

            def last(built: Views, field: str = "") -> None:
                chosen = shell.last_tool.get(suite.id)
                tool = next((t for t in suite.tools if t.id == chosen), suite.tools[0])
                page_of(suite, tool)(built, field)

            return last

        def page(built: Views) -> None:
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

            async def ready() -> None:
                await built.settled()
                await ui.run_javascript("document.body.dataset.screenReady = '1'", timeout=10)

            ui.timer(0.1, ready, once=True)

        return page

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
        "/settings": settings_page,
    }

    def build(panel: str = "", palette: str = "", dialog: str = "") -> None:
        ui.add_head_html(
            '<link rel="stylesheet" href="/vendor/molstar/molstar.css">'
            + '<link rel="stylesheet" href="/vendor/katex/katex.min.css">'
            + STYLESHEETS
            + '<script src="/vendor/molstar/molstar.js"></script><script src="/bridge.js"></script>'
            + '<script src="/plane.js"></script>'
            + '<script src="/vendor/katex/katex.min.js"></script>'
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

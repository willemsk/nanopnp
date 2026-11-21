"""The workbench's pages, written in NiceGUI over the server's FastAPI app."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast
from urllib.parse import urlencode

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from nicegui import app as nicegui_app
from nicegui import ui

from nanopnp.gui.render import (
    RENDERER_DIRECTORY,
    RENDERER_ROUTE,
    RENDERER_URL,
    host_page,
    scene_stem,
)
from nanopnp.gui.web.analysis import AnalysisModel, FieldMap, cut_chart, dark_palette
from nanopnp.gui.web.analysis_tools import Scales, analysis_page, comparison_maps, map_of
from nanopnp.gui.web.assets import ASSETS, TOKENS
from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.continuum_tools import continuum_page
from nanopnp.gui.web.frame import Route, Views, current_suite, frame, heading
from nanopnp.gui.web.meso import VOLUMES, MesoModel
from nanopnp.gui.web.meso_tools import meso_page
from nanopnp.gui.web.molecular import MolecularModel
from nanopnp.gui.web.molview import (
    COLOURINGS,
    REPRESENTATIONS,
    Isosurfaces,
    annotation,
    chain_rows,
    charge_rows,
    first_frame_pdb,
    frame_count,
    has_backbone,
    moved_rows,
    overlaid,
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
    charge_ends,
    charge_plane,
    image_png,
    physics_plane,
    plane,
    png,
)
from nanopnp.gui.web.screens import SUITES, TOOL_SUITES, VIEWS, Suite, Tool, tool_view
from nanopnp.gui.web.settings_page import SettingsPage
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.study_tools import study_page
from nanopnp.gui.web.tools import OVERLAY_MOST, charge_colours, tool_page
from nanopnp.io.manifest import RUN_RECORD_FILENAME

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from fastapi import FastAPI

    from nanopnp.api.case import Case

__all__ = ["ROUTES", "install"]

STYLESHEETS = (
    '<link rel="stylesheet" href="/tokens.css"><link rel="stylesheet" href="/workbench.css">'
)
MESO_COLOURINGS = ("charge", "chain", "moved")
"""What a Meso scene colours its residues by: their charge, their chain, or an edit's moves."""


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
        tool: str = "region",
        image: str = "mean",
        colour: str = "material",
        band: str = "",
        pick: str = "",
        held: str = "",
    ) -> JSONResponse:
        """Serve what Region or Mesh draws of a model in the (r, z) view, less the mesh held."""
        if tool not in ("region", "mesh"):
            raise HTTPException(422, f"tool: {tool!r} is not Region or Mesh")
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
        tool: str = "conditions",
        within: str = "",
        pick: str = "",
        held: str = "",
        mesh: str = "",
    ) -> JSONResponse:
        """Serve what the (r, z) view draws of a physics model, inside the study shown."""
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

    def analysed(run: str) -> tuple[AnalysisModel, Path]:
        project = shell.bench.project
        if project is None:
            raise HTTPException(404, "no project is open")
        root = project.root.resolve()
        path = (root / run).resolve()
        if not path.is_relative_to(root) or not (path / RUN_RECORD_FILENAME).is_file():
            raise HTTPException(404, f"no run {run!r} in the project")
        return AnalysisModel(project), path

    def ranged(text: str) -> tuple[float, float] | None:
        if not text:
            return None
        try:
            low, high = (float(part) for part in text.split(","))
        except ValueError:
            raise HTTPException(422, f"range {text!r} is not two numbers") from None
        return low, high

    @app.get("/api/analysis/image")
    def analysis_image(
        run: str,
        quantity: str,
        palette: str = "",
        dark: str = "",
        frame: str = "",
        range: str = "",
    ) -> Response:
        """Serve one run's map of a quantity as a PNG, NaN transparent.

        ``frame=whole`` spans the run's whole domain; else the map is the pore's close-up.
        """
        model, path = analysed(run)
        try:
            shown = map_of(
                model,
                path,
                quantity,
                palette or None,
                ranged(range),
                whole=frame == "whole",
                positive=charge_colours(shell),
            )
        except (KeyError, ValueError) as error:
            raise HTTPException(422, str(error)) from None
        if shown is None:
            raise HTTPException(404, f"the fields of run {run!r} are not read yet")
        if dark:
            shown = replace(shown, palette=dark_palette(shown.palette))
        return Response(shown.png(), media_type="image/png")

    @app.get("/api/analysis/scene")
    def analysis_scene(run: str, field: str, range: str = "") -> FileResponse:
        """Serve a run's scene of one field, written once by a render child."""
        _, path = analysed(run)
        scene = path / "viewer" / f"{scene_stem(field, ranged(range))}.json"
        if not scene.is_file():
            raise HTTPException(404, f"no scene of {field!r} is written for run {run!r}")
        return FileResponse(scene, media_type="application/json")

    @app.get("/api/analysis/view")
    def analysis_view(
        run: str, field: str, range: str = "", frame: str = "", reverse: str = ""
    ) -> HTMLResponse:
        """Serve the page that fetches a run's scene and draws it with the shipped renderer.

        ``frame``, ``r0,r1,z0,z1`` in nm, is the region the camera opens on; ``reverse`` hands
        the renderer its colour range high to low.
        """
        analysed(run)
        query = urlencode({"run": run, "field": field, **({"range": range} if range else {})})
        opened: tuple[float, float, float, float] | None = None
        if frame:
            try:
                r0, r1, z0, z1 = (float(value) for value in frame.split(","))
            except ValueError:
                raise HTTPException(422, f"frame: {frame!r} is not r0,r1,z0,z1") from None
            opened = (r0, r1, z0, z1)
        return HTMLResponse(
            host_page(
                f"/api/analysis/scene?{query}",
                RENDERER_URL,
                f"{field} on the mesh",
                frame_nm=opened,
                reverse=bool(reverse),
            )
        )

    def compared_maps(
        name: str, *, whole: bool = False, scales: Scales | None = None
    ) -> tuple[AnalysisModel, dict[str, FieldMap]]:
        project = shell.bench.project
        if project is None or name not in project.items("comparison"):
            raise HTTPException(404, f"no comparison {name!r}")
        model = AnalysisModel(project)
        try:
            maps = comparison_maps(
                model, name, whole=whole, positive=charge_colours(shell), scales=scales
            )
        except (KeyError, ValueError) as error:
            raise HTTPException(422, str(error)) from None
        if maps is None:
            raise HTTPException(404, f"the fields of comparison {name!r} are not read yet")
        return model, maps

    @app.get("/api/analysis/compare/{name}/image")
    def compare_image(
        name: str,
        which: str,
        dark: str = "",
        frame: str = "",
        pair: str = "",
        difference: str = "",
    ) -> Response:
        """Serve one map of a comparison: ``first``, ``second``, ``mirrored`` or ``difference``.

        ``pair`` and ``difference``, each ``low,high``, are the scales a backdrop takes from
        its close-up; both or neither.
        """
        pair_range, difference_range = ranged(pair), ranged(difference)
        if (pair_range is None) != (difference_range is None):
            raise HTTPException(422, "pair and difference are given both or neither")
        scales = (
            None
            if pair_range is None or difference_range is None
            else (pair_range, difference_range)
        )
        _, maps = compared_maps(name, whole=frame == "whole", scales=scales)
        if which not in maps:
            raise HTTPException(422, f"which {which!r} is not one of {', '.join(maps)}")
        shown = maps[which]
        if dark:
            shown = replace(shown, palette=dark_palette(shown.palette))
        return Response(shown.png(), media_type="image/png")

    @app.get("/api/analysis/compare/{name}/cut")
    def compare_cut(name: str, r: float = 0.0) -> JSONResponse:
        """Serve a comparison's axial cut at ``r`` nm, a series per run."""
        model, _ = compared_maps(name)
        compared = model.comparison(name)
        held = [model.fields(model.run_path(item)) for item in compared.runs]
        if any(fields is None for fields in held):
            raise HTTPException(404, f"the fields of comparison {name!r} are not read yet")
        runs = tuple(
            (label, fields) for label, fields in zip(compared.runs, held, strict=True) if fields
        )
        return JSONResponse(cut_chart(runs, compared.quantity, r).json())

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

    def meso(name: str) -> MesoModel:
        project = shell.bench.project
        if project is None or name not in project.items("continuum"):
            raise HTTPException(404, f"no continuum model {name!r}")
        return MesoModel(project, name, shell.queue)

    def colours(positive: str) -> Literal["blue", "red"]:
        if positive not in ("blue", "red"):
            raise HTTPException(422, f"positive: {positive!r} is not blue or red")
        return cast("Literal['blue', 'red']", positive)

    @app.get("/api/meso/{name}/plane")
    def meso_plane(
        name: str, tool: str = "density", image: str = "", residue: str = ""
    ) -> JSONResponse:
        """Serve what Density or Outline draws of a model in stage 1's frame, a residue marked."""
        if tool not in ("density", "outline"):
            raise HTTPException(422, f"tool: {tool!r} is not density or outline")
        model = meso(name)
        try:
            with model.keyed_once():
                atoms = model.residue_atoms() if residue else None
                markers = [] if atoms is None else atoms.markers(residue)
                drawn = plane(
                    model,
                    tool,
                    image=image or ("density" if tool == "density" else "mean"),
                    marked=(atoms.group(residue), markers) if atoms and markers else None,
                )
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        return JSONResponse(drawn.json())

    @app.get("/api/meso/{name}/image")
    def meso_image(name: str, layer: str = "mean") -> Response:
        """Serve one picture of a model's stages 2 and 3 as a PNG."""
        if layer not in IMAGES:
            raise HTTPException(422, f"layer: {layer!r} is not one of {', '.join(IMAGES)}")
        found = image_png(meso(name), layer)
        if found is None:
            raise HTTPException(404, f"the {layer} picture of {name!r} is not built")
        return Response(found, media_type="image/png")

    @app.get("/api/meso/{name}/atoms")
    def meso_atoms(name: str, r: float, z: float) -> JSONResponse:
        """Serve the residues whose atoms stage 2 smears nearest a point, in kernel widths."""
        atoms = meso(name).density_atoms()
        found = [] if atoms is None else atoms.nearest(abs(r), z)
        return JSONResponse([{"key": key, "widths": widths} for key, widths in found])

    @app.get("/api/meso/{name}/charge/plane")
    def meso_charge(
        name: str,
        layer: str = "lattice",
        residue: str = "",
        positive: str = "blue",
        span: float = 0.0,
    ) -> JSONResponse:
        """Serve a model's charge on the mesh as the (r, z) view draws it, a residue marked.

        ``span``, where above zero, is how far the colour scale runs each side of zero, in the
        layer's unit; by default it opens on the layer's clip.
        """
        if layer not in ("lattice", "deployed"):
            raise HTTPException(422, f"layer: {layer!r} is not lattice or deployed")
        opened = span if span > 0.0 else None
        model = meso(name)
        with model.keyed_once():
            charge = model.artefacts().get("charge")
            charges = model.charges()
            markers = charges.markers(residue) if charges is not None and residue in charges else []
            digest = "" if charge is None else charge.hash[:12]
            spanned = "" if opened is None else f"&span={opened:.6g}"
            drawn = charge_plane(
                model.charge_map(),
                model.conservation(),
                image_url=(
                    f"/api/meso/{name}/charge/image?positive={positive}&v={digest}{spanned}"
                ),
                positive=colours(positive),
                deployed=model.elements(),
                layer="deployed" if layer == "deployed" else "lattice",
                picked=(residue, markers) if markers else None,
                span=opened,
            )
        return JSONResponse(drawn.json())

    @app.get("/api/meso/{name}/charge/image")
    def meso_charge_image(
        name: str, positive: str = "blue", span: float = 0.0, middle: str = "light"
    ) -> Response:
        """Serve a model's charge lattice as a PNG, a positive charge in the named colour.

        ``span`` is as the drawing's; ``middle=dark`` draws zero dark, for the dark theme.
        """
        if middle not in ("light", "dark"):
            raise HTTPException(422, f"middle: {middle!r} is not light or dark")
        shown = meso(name).charge_map()
        if shown is None:
            raise HTTPException(404, f"continuum model {name!r} stores no charge lattice")
        import numpy as np

        blue = colours(positive) == "blue"
        # Where the lattice carries no charge the canvas shows through, on either theme.
        values = np.where(shown.image.values == 0.0, np.nan, shown.image.values)
        top = span if span > 0.0 else shown.clip if shown.clip > 0.0 else shown.image.scale[1]
        dark = middle == "dark"
        image = replace(
            shown.image,
            values=values,
            scale=(-top, top),
            palette=("diverging_dark_r" if dark else "diverging_r")
            if blue
            else ("diverging_dark" if dark else "diverging"),
        )
        return Response(png(image.rgba(), image.width, image.height), media_type="image/png")

    @app.get("/api/meso/{name}/residues")
    def meso_residues(name: str, r: float, z: float) -> JSONResponse:
        """Serve the residues that add most charge at a point of the map, the most first."""
        charges = meso(name).charges()
        found = [] if charges is None else charges.at(r, z)
        return JSONResponse([{"key": key, "e_per_nm3": value} for key, value in found])

    @app.get("/api/meso/{name}/structure")
    def meso_structure(name: str) -> Response:
        """Serve the model's atoms as PDB text: its protonated first frame, else its PQR."""
        model = meso(name)
        table = model.table()
        pqr = None if table is not None else pqr_frame(model.pqr())
        text = first_frame_pdb(table) if table is not None else "" if pqr is None else pqr_pdb(pqr)
        return Response(text, media_type="chemical/x-pdb")

    @app.get("/api/meso/{name}/annotation")
    def meso_annotation(name: str, colour: str = "charge", positive: str = "blue") -> JSONResponse:
        """Serve one colour per residue, by its chain or its net charge, as an annotation.

        ``moved`` colours the residues the held edit of the outline moves, every copy, each way.
        """
        if colour not in MESO_COLOURINGS:
            raise HTTPException(
                422, f"colour: {colour!r} is not one of {', '.join(MESO_COLOURINGS)}"
            )
        model = meso(name)
        table = model.table()
        pqr = None if table is not None else pqr_frame(model.pqr())
        if colour == "chain":
            return JSONResponse(chain_rows(table, pqr))
        if colour == "moved":
            moved, atoms = model.moved(), model.residue_atoms()
            if moved is None or atoms is None:
                return JSONResponse([])
            out = {copy for key in moved.out for copy in atoms.copies(key)}
            into = {copy for key in moved.in_ for copy in atoms.copies(key)}
            return JSONResponse(moved_rows(table, pqr, out, into))
        return JSONResponse(charge_rows(table, pqr, positive=colours(positive)))

    @app.get("/api/meso/{name}/volume")
    def meso_volume(name: str, which: str = "full") -> Response:
        """Serve one overlay volume, the charge in 3D or its mean about the axis, as OpenDX.

        A sync route, so the first read's seconds of work run off the event loop.
        """
        if which not in VOLUMES:
            raise HTTPException(422, f"which: {which!r} is not one of {', '.join(VOLUMES)}")
        text = meso(name).volume_text(which)
        if text is None:
            raise HTTPException(404, f"continuum model {name!r} deposits no charge to overlay")
        return Response(text, media_type="text/plain")

    @app.get("/api/meso/{name}/scene")
    def meso_scene(  # noqa: PLR0913
        name: str,
        colour: str = "charge",
        positive: str = "blue",
        v: str = "",
        subunit: int = 0,
        full: float = 0.0,
        revolved: float = 0.0,
        edit: str = "",
        representation: str = "",
    ) -> JSONResponse:
        """Serve the scene of a model's molecule from the side, cut at the axis or one subunit.

        ``full`` and ``revolved``, where above zero, draw that overlay volume's two isosurfaces
        at plus and minus that level, in e/nm^3. ``edit`` names the held edit the ``moved``
        colouring is drawn for, so a new edit takes a new annotation and the same structure.
        ``representation`` is one of Mol*'s looks; by default a cartoon, or balls where the
        atoms hold no backbone.
        """
        if colour not in MESO_COLOURINGS:
            raise HTTPException(
                422, f"colour: {colour!r} is not one of {', '.join(MESO_COLOURINGS)}"
            )
        if representation and representation not in REPRESENTATIONS:
            raise HTTPException(
                422,
                f"representation: {representation!r} is not one of {', '.join(REPRESENTATIONS)}",
            )
        model = meso(name)
        table = model.table()
        pqr = None if table is not None else pqr_frame(model.pqr())
        seen = study_side_view(table, pqr)
        if seen is None:
            return JSONResponse(None)
        alone = bool(subunit) and seen.chain is not None
        painted = f"colour={colour}&positive={colours(positive)}&v={v}&edit={edit}"
        ends = charge_ends(colours(positive))
        drawn = scene(
            None,
            structure_url=f"/api/meso/{name}/structure?v={v}",
            annotation_url=f"/api/meso/{name}/annotation?{painted}",
            # Atoms with no backbone, as a fixture's charges, draw as balls: a cartoon
            # draws nothing of them.
            representation=representation
            if representation
            else "cartoon"
            if has_backbone(table, pqr)
            else "spacefill",
            # A pore of two chains or more is cut at its axis; fewer are seen whole.
            clip=not alone and seen.chain is not None,
            side_on=replace(seen, alone=alone),
        )
        volumes = [
            Isosurfaces(f"/api/meso/{name}/volume?which={which}&v={v}", level, *ends)
            for which, level in (("full", full), ("revolved", revolved))
            if level > 0.0
        ]
        return JSONResponse(overlaid(drawn, volumes))

    def pump() -> None:
        # The server's one queue: each build, run and sweep member waits for a slot here.
        queue = shell.queue
        queue.limit = int(str(shell.settings.value("solves_at_once")))
        queue.tick()

    nicegui_app.timer(0.25, pump)

    nicegui_app.add_static_files("/vendor/molstar", ASSETS / "molstar")
    nicegui_app.add_static_files("/vendor/katex", ASSETS / "katex")
    nicegui_app.add_static_files("/vendor/uplot", ASSETS / "uplot")
    nicegui_app.add_static_files(RENDERER_ROUTE, RENDERER_DIRECTORY)
    # Our own small files are not cached (max-age 0): NiceGUI's hour of caching would hide an edit
    # that `nanopnp gui --dev` restarted the server for.
    for local, url in (
        (TOKENS, "/tokens.css"),
        (ASSETS / "bridge.js", "/bridge.js"),
        (ASSETS / "plane.js", "/plane.js"),
        (ASSETS / "chart.js", "/chart.js"),
        (ASSETS / "workbench.css", "/workbench.css"),
        (ASSETS / "frame.js", "/frame.js"),
        (ASSETS / "frame.css", "/frame.css"),
    ):
        nicegui_app.add_static_file(local_file=local, url_path=url, max_cache_age=0)

    def page_of(suite: Suite, tool: Tool) -> Callable[..., None]:
        pages = {
            "molecular": tool_page,
            "meso": meso_page,
            "continuum": continuum_page,
            "physics": physics_page,
            "study": study_page,
            "analysis": analysis_page,
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
            + '<link rel="stylesheet" href="/vendor/uplot/uPlot.min.css">'
            + STYLESHEETS
            + '<script src="/vendor/molstar/molstar.js"></script><script src="/bridge.js"></script>'
            + '<script src="/plane.js"></script>'
            + '<script src="/vendor/uplot/uPlot.iife.min.js"></script>'
            + '<script src="/chart.js"></script>'
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

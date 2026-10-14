"""The field viewer's render side: one spawned process, one scene, written as a file."""

from __future__ import annotations

import json
import logging
import multiprocessing
import queue as queue_module
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Literal, TypeAlias

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from multiprocessing.process import BaseProcess
    from multiprocessing.queues import Queue

    from nanopnp.core.typing import Expression, Mesh
    from nanopnp.io.artefact import Artefact
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.numerics.measures import Measures

logger = logging.getLogger(__name__)

__all__ = [
    "CHI_RANGE",
    "MESH_SCENE_STEM",
    "READY_FLAG",
    "RENDERER_DIRECTORY",
    "RENDERER_INTEGRITY",
    "RENDERER_SOURCE",
    "RENDERER_VERSION",
    "VIEWER_DIRNAME",
    "ChargeQuantity",
    "ChargeRequest",
    "DeployedCoefficient",
    "MeshRequest",
    "RenderFailed",
    "RenderProcess",
    "RenderRequest",
    "Rendered",
    "RenderedCharge",
    "RenderedMesh",
    "deployed_coefficient",
    "host_document",
    "readiness_script",
    "render",
    "render_charge",
    "render_mesh",
    "renderer_source",
]

# The webgui version netgen.webgui's template pins for the locked NGSolve; test_gui_render reads the
# pin.
RENDERER_VERSION = "0.2.39"

RENDERER_INTEGRITY = (
    "sha512-"
    "yDd6YR7EjHGfeUC+rbn6/WvTWWkwJSU1KcsqWYzP5qJyN3IN9ax2vuUROvn8epKRKtuerLJ2qTSPp8A1yZubqw=="
)

RENDERER_DIRECTORY = Path(__file__).resolve().parent / "assets" / "webgui"

# Shipped, not fetched (CON-09): the LGPL-2.1+ webgui build bundles three.js (MIT) and dat.gui
# (Apache-2.0), redistributed unmodified beside their licence texts and a NOTICE.
RENDERER_SOURCE = (RENDERER_DIRECTORY / "webgui.js").as_uri()

# Never an artefact and never hashed: a picture of a converged state is a view of a result (§5.3.2).
VIEWER_DIRNAME = "viewer"

# Not scene-*, so a field render's sweep of its own previous pair leaves the mesh picture alone.
MESH_SCENE_STEM = "mesh"

ChargeQuantity: TypeAlias = Literal["charge", "chi"]

# Fixed: a solid fraction lies in [0, 1], and a scale following the data would make a constant 1
# look varying.
CHI_RANGE = (0.0, 1.0)

READY_FLAG = "__nanopnp_viewer"

# A string.Template: the document is mostly CSS and JavaScript, so neither an f-string nor
# str.format fits.
_DOCUMENT = Template("""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>$title</title>
    <meta name="viewport" content="width=device-width, user-scalable=no"/>
    <style>
      body { margin: 0; overflow: hidden; background: #ffffff; }
      canvas { cursor: grab; }
      canvas:active { cursor: grabbing; }
    </style>
  </head>
  <body>
    <script src="$renderer"></script>
    <script>
      var render_data = $scene;
      window.$flag = {
        ready: false,
        renderer_loaded: typeof webgui !== "undefined",
        error: "",
        renderer: $renderer_literal
      };
      try {
        var scene = new webgui.Scene();
        scene.init(document.body, render_data, {preserveDrawingBuffer: false});
        window.$flag.ready = true;
      } catch (error) {
        window.$flag.error = String(error);
      }
    </script>
  </body>
</html>
""")


def renderer_source() -> str:
    """Return the address the host document loads the renderer from."""
    return RENDERER_SOURCE


def readiness_script() -> str:
    """Return the JavaScript that reports whether the scene is ready, as a JSON object."""
    return (
        f"JSON.stringify(window.{READY_FLAG} || "
        "{ready: false, renderer_loaded: false, "
        'error: "the document did not run its initialisation", renderer: ""})'
    )


def host_document(scene: str, *, renderer: str, title: str) -> str:
    """Return the HTML document that draws one scene.

    Parameters
    ----------
    scene
        The scene, already serialised as JSON.
    renderer
        The URL the document loads the renderer from.
    title
        The document title.
    """
    return _DOCUMENT.substitute(
        title=title,
        renderer=renderer,
        renderer_literal=json.dumps(renderer),
        # json.dumps leaves '/' unescaped: a '</script>' in a scene string would end this element
        # early, reported as a renderer that never arrived.
        scene=scene.replace("</", "<\\/"),
        flag=READY_FLAG,
    )


@dataclass(frozen=True)
class RenderRequest:
    """What the child is asked for: a finished run and one of its fields.

    Parameters
    ----------
    field
        The attribute name, or ``""`` for the model's first field.
    """

    run: str
    field: str = ""
    renderer: str = RENDERER_SOURCE


@dataclass(frozen=True)
class Rendered:
    """A scene was written; the paths and the field vocabulary of the solution."""

    document: str
    scene: str
    field: str
    fields: tuple[str, ...]
    elements: int


@dataclass(frozen=True)
class RenderFailed:
    """Nothing was drawn; the message is the diagnostic."""

    error: str
    message: str


@dataclass(frozen=True)
class MeshRequest:
    """What the child is asked for by the geometry tab: a run's stage-6 mesh."""

    run: str
    renderer: str = RENDERER_SOURCE


@dataclass(frozen=True)
class RenderedMesh:
    """The mesh was drawn by material; its paths and the figures its gates measured.

    Parameters
    ----------
    quality
        VER-10's figures and the ``(r, z)`` centroid of each least value.
    wall
        Stage 6's wall-size gate statistics; empty for a supplied mesh.
    """

    document: str
    scene: str
    elements: int
    materials: tuple[str, ...]
    quality: dict[str, object]
    wall: dict[str, object]


@dataclass(frozen=True)
class ChargeRequest:
    """What the charge tab asks for: a run's deployed charge or ``chi``."""

    run: str
    quantity: ChargeQuantity = "charge"
    renderer: str = RENDERER_SOURCE


@dataclass(frozen=True)
class RenderedCharge:
    """The deployed coefficient was drawn; the paths and the scale it was drawn on.

    Parameters
    ----------
    colour_range
        The fixed ``(min, max)`` of the colour map.
    limit
        The largest magnitude the scene samples, printed beside the picture.
    """

    document: str
    scene: str
    quantity: ChargeQuantity
    name: str
    units: str
    colour_range: tuple[float, float]
    limit: float
    elements: int
    materials: tuple[str, ...]


RenderEvent: TypeAlias = Rendered | RenderedMesh | RenderedCharge | RenderFailed


def _state_path(run: Path) -> Path:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import RUN_RECORD_FILENAME
    from nanopnp.solve.state import STATE_KEY

    record_path = run / RUN_RECORD_FILENAME
    if not record_path.is_file():
        raise FileNotFoundError(
            f"{record_path} is not there, so this directory records no run to draw"
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    artefacts = record.get("artefacts", {})
    solve = artefacts.get("solve")
    if solve is None:
        walked = ", ".join(sorted(artefacts)) or "nothing"
        raise FileNotFoundError(
            f"{record_path} records no solve artefact; the run produced {walked}, so there is "
            "no converged state to draw"
        )
    root = record.get("store")
    if root is None:
        raise FileNotFoundError(
            f"{record_path} names no artefact store, so the converged state it refers to cannot "
            "be located"
        )
    artefact = Store(Path(root)).get(str(solve["schema"]), str(solve["hash"]))
    if artefact is None:
        raise FileNotFoundError(
            f"{solve['schema']} {solve['hash'][:12]} is not in the store at {root}; the run "
            "record refers to a converged state that has been removed"
        )
    payload = artefact.payload.get(STATE_KEY)
    if payload is None:
        carried = ", ".join(sorted(artefact.payload)) or "nothing"
        raise FileNotFoundError(
            f"the solve artefact carries no {STATE_KEY!r} payload; it carries {carried}, so there "
            "is no state to restore"
        )
    return Path(payload)


def _recorded_artefact(run: Path, stage: str, *, needed: str | None) -> Artefact | None:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import RUN_RECORD_FILENAME

    record = json.loads((run / RUN_RECORD_FILENAME).read_text(encoding="utf-8"))
    entry = record.get("artefacts", {}).get(stage)
    root = record.get("store")
    if entry is None or root is None:
        return None
    artefact = Store(Path(root)).get(str(entry["schema"]), str(entry["hash"]))
    if artefact is None and needed is not None:
        raise FileNotFoundError(
            f"{entry['schema']} {entry['hash'][:12]} is not in the store at {root}; the run "
            f"record refers to {needed} that has been removed"
        )
    return artefact


def _stage7_need(resolved: ResolvedCase) -> str | None:
    if resolved.deposits_charge:
        return "a deposited charge"
    if resolved.derives_eps_r:
        return "a derived solid fraction"
    return None


def _write_scene(
    run: Path, stem: str, scene: dict[str, object], *, renderer: str, title: str
) -> tuple[Path, Path]:
    directory = run / VIEWER_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)
    scene_path = directory / f"{stem}.json"
    document_path = directory / f"{stem}.html"
    payload = json.dumps(scene)
    _replace(scene_path, payload)
    _replace(document_path, host_document(payload, renderer=renderer, title=title))
    logger.info("%s scene written to %s (%d bytes)", title, document_path, len(payload))
    return scene_path, document_path


def _element_count(mesh: Mesh, domain: str | None) -> int:
    import numpy as np

    if domain is None:
        return int(mesh.ne)
    # The mask has one bit per material, so the elements' 1-based indices are looked up as an array,
    # not by a loop over ~121k elements on every render.
    keep = mesh.Materials(domain).Mask()
    wanted = np.array([keep[index] for index in range(len(keep))], dtype=bool)
    materials = np.asarray(mesh.ngmesh.Elements2D().NumPy()["index"], dtype=np.int64) - 1
    return int(np.count_nonzero(wanted[materials]))


def _replace(path: Path, text: str) -> None:
    part = path.with_name(f"{path.name}.part")
    part.write_text(text, encoding="utf-8")
    part.replace(path)


def render(request: RenderRequest) -> Rendered:
    """Restore a finished run and write one field's scene into its ``viewer/``.

    Raises FileNotFoundError if the run records no converged state, and KeyError if the field is
    not one this solution carries.
    """
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.pipeline.case import load_case, resolve
    from nanopnp.post.export import (
        attribute_name,
        field_scale,
    )
    from nanopnp.solve.state import restore

    run = Path(request.run)
    state = _state_path(run)
    case = load_case(run / CASE_FILENAME)
    resolved = resolve(case)
    solution = restore(
        state,
        resolved=resolved,
        mesh_artefact=_recorded_artefact(
            run, "mesh", needed="a generated mesh" if case.inputs.mesh is None else None
        ),
        charge_artefact=_recorded_artefact(run, "charge", needed=_stage7_need(resolved)),
    )
    # Any model: each reports the NUM-09 scale set that turns its state into SI numbers (§5.4.3).
    model = solution.model
    # A 'number'-element field is a scalar unknown with no spatial extent: nothing to draw.
    drawable = [declared for declared in model.fields if declared.element != "number"]
    names = tuple(attribute_name(declared.name) for declared in drawable)
    if not names:
        raise KeyError(f"{model.name!r} declares no field with a spatial extent to draw")
    wanted = request.field or names[0]
    if wanted not in names:
        raise KeyError(f"no field {wanted!r} in this solution; it carries {', '.join(names)}")
    declared = drawable[names.index(wanted)]

    from ngsolve.webgui import Draw

    mesh = solution.space.mesh
    # Restricted to the field's domain as the IF-07 export is: over the whole mesh a concentration
    # would read zero in the membrane, like a depletion.
    region = mesh if declared.domain is None else mesh.Materials(declared.domain)
    drawn = solution.component(declared.name) * field_scale(declared.name, model.scales)
    scene = Draw(drawn, region, show=False, order=declared.order).GetData()
    elements = _element_count(mesh, declared.domain)

    directory = run / VIEWER_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)
    stem = "".join(character if character.isalnum() else "-" for character in wanted)
    scene_path = directory / f"scene-{stem}.json"
    document_path = directory / f"scene-{stem}.html"
    payload = json.dumps(scene)
    # One field's pair at a time: each copy is tens of megabytes at the reference mesh size.
    for stale in directory.glob("scene-*"):
        if stale not in (scene_path, document_path) and stale.is_file():
            stale.unlink()
    # Written beside and renamed, so a render stopped part-way leaves no half-written document;
    # a killed child's .part is swept on the next render.
    _replace(scene_path, payload)
    _replace(document_path, host_document(payload, renderer=request.renderer, title=wanted))
    logger.info("scene for %s written to %s (%d bytes)", wanted, document_path, len(payload))
    return Rendered(
        document=str(document_path),
        scene=str(scene_path),
        field=wanted,
        fields=names,
        elements=elements,
    )


def render_mesh(request: MeshRequest) -> RenderedMesh:
    """Draw a run's stage-6 mesh by material into its ``viewer/``, with its gate figures."""
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.mesh.ingest import deployed_mesh
    from nanopnp.pipeline.case import load_case, resolve

    run = Path(request.run)
    resolved = resolve(load_case(run / CASE_FILENAME))
    artefact = _recorded_artefact(
        run, "mesh", needed="a generated mesh" if resolved.mesh is None else None
    )
    if artefact is None and resolved.mesh is None:
        raise FileNotFoundError(
            f"{run} records no stage-6 artefact, so there is no generated mesh to draw; run the "
            "build through 'mesh' first"
        )
    ingested = deployed_mesh(resolved, artefact)
    mesh = ingested.mesh
    materials = tuple(str(name) for name in mesh.GetMaterials())

    from ngsolve.webgui import Draw

    colour = mesh.MaterialCF({name: float(index) for index, name in enumerate(materials)})
    scene = Draw(colour, mesh, show=False).GetData()
    report = ingested.quality
    quality: dict[str, object] = {
        "min_sicn": report.min_sicn,
        "min_gamma": report.min_gamma,
        "floor": report.summary()["floor"],
        "worst_sicn_at_nm": report.centroid(report.worst_sicn_element),
        "worst_gamma_at_nm": report.centroid(report.worst_gamma_element),
    }
    sizing = artefact.summary.get("sizing") if artefact is not None else None
    wall = dict(sizing.get("wall_statistics", {})) if isinstance(sizing, dict) else {}

    scene_path, document_path = _write_scene(
        run, MESH_SCENE_STEM, scene, renderer=request.renderer, title="mesh"
    )
    return RenderedMesh(
        document=str(document_path),
        scene=str(scene_path),
        elements=int(mesh.ne),
        materials=materials,
        quality=quality,
        wall=wall,
    )


@dataclass(frozen=True)
class DeployedCoefficient:
    """A run's deployed charge or ``chi``, as the solve assembles it."""

    mesh: Mesh
    coefficient: Expression
    measures: Measures
    name: str
    units: str


def deployed_coefficient(run: Path, quantity: ChargeQuantity) -> DeployedCoefficient:
    """Return the coefficient a run's solve reads for ``quantity``, on its deployed mesh.

    Raises FileNotFoundError if a needed stage artefact has left the store, and KeyError if the
    run carries no such coefficient.
    """
    from nanopnp.charge.dielectric import SOLID_FRACTION
    from nanopnp.charge.fields import CANONICAL_UNITS
    from nanopnp.charge.stage import case_fields, read_fields
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.mesh.ingest import deployed_mesh
    from nanopnp.numerics.measures import AXISYMMETRIC
    from nanopnp.pipeline.case import load_case, resolve
    from nanopnp.post.export import FIXED_CHARGE_ATTRIBUTE

    resolved = resolve(load_case(run / CASE_FILENAME))
    mesh_artefact = _recorded_artefact(
        run, "mesh", needed="a generated mesh" if resolved.mesh is None else None
    )
    if mesh_artefact is None and resolved.mesh is None:
        raise FileNotFoundError(
            f"{run} records no stage-6 artefact, so there is no deployed mesh to draw on; run "
            "the build through 'charge' first"
        )
    stage7 = _stage7_need(resolved)
    charge_artefact = _recorded_artefact(run, "charge", needed=stage7)
    if stage7 is not None and charge_artefact is None:
        raise FileNotFoundError(
            f"{run} records no stage-7 artefact, and case {resolved.name!r} reads {stage7} from "
            "one; run the build through 'charge' first"
        )
    mesh = deployed_mesh(resolved, mesh_artefact).mesh
    order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
    measures = AXISYMMETRIC.at_order(order)
    read = None
    if resolved.charge is not None or resolved.eps_r is not None:
        read = read_fields(resolved)
    fields = case_fields(resolved, read, charge_artefact, mesh, measures=measures)
    if quantity == "charge":
        if fields.charge is None:
            raise KeyError(
                f"case {resolved.name!r} carries no fixed charge: it neither deposits one in "
                "stage 7 nor supplies one through inputs.charge, so there is nothing to draw"
            )
        return DeployedCoefficient(
            mesh=mesh,
            coefficient=fields.charge.volume_density_C_m3(),
            measures=measures,
            name=FIXED_CHARGE_ATTRIBUTE,
            units=CANONICAL_UNITS["volume_charge_density"],
        )
    if fields.eps_r is None:
        raise KeyError(
            f"case {resolved.name!r} has no solid fraction: its permittivity is sharp, one value "
            "per material, so there is no chi to draw"
        )
    return DeployedCoefficient(
        mesh=mesh,
        coefficient=fields.eps_r.chi(),
        measures=measures,
        name=SOLID_FRACTION,
        units=CANONICAL_UNITS[SOLID_FRACTION],
    )


def render_charge(request: ChargeRequest) -> RenderedCharge:
    """Draw a run's deployed charge or ``chi`` into its ``viewer/``."""
    run = Path(request.run)
    deployed = deployed_coefficient(run, request.quantity)

    from ngsolve.webgui import Draw

    mesh = deployed.mesh
    scene = Draw(
        deployed.coefficient, mesh, show=False, order=deployed.measures.element_order
    ).GetData()
    # The sampled extremes are drawn and the range fixed, so autoscale cannot move zero off centre.
    sampled = (float(scene["funcmin"]), float(scene["funcmax"]))
    if request.quantity == "charge":
        limit = max(abs(sampled[0]), abs(sampled[1]))
        # An all-zero field still needs a range a colour map can divide by.
        colour_range = (-limit, limit) if limit > 0.0 else (-1.0, 1.0)
    else:
        limit = sampled[1]
        colour_range = CHI_RANGE
    scene["funcmin"], scene["funcmax"] = colour_range
    scene["autoscale"] = False
    scene["gui_settings"] = {
        **scene.get("gui_settings", {}),
        "autoscale": False,
        "colormap_min": colour_range[0],
        "colormap_max": colour_range[1],
    }

    scene_path, document_path = _write_scene(
        run, request.quantity, scene, renderer=request.renderer, title=deployed.name
    )
    return RenderedCharge(
        document=str(document_path),
        scene=str(scene_path),
        quantity=request.quantity,
        name=deployed.name,
        units=deployed.units,
        colour_range=colour_range,
        limit=limit,
        elements=int(mesh.ne),
        materials=tuple(str(name) for name in mesh.GetMaterials()),
    )


AnyRequest: TypeAlias = RenderRequest | MeshRequest | ChargeRequest


def _worker(request: AnyRequest, events: Queue[RenderEvent]) -> None:
    try:
        if isinstance(request, MeshRequest):
            events.put(render_mesh(request))
        elif isinstance(request, ChargeRequest):
            events.put(render_charge(request))
        else:
            events.put(render(request))
    except BaseException as error:
        events.put(RenderFailed(error=type(error).__qualname__, message=str(error)))


@dataclass
class RenderProcess:
    """One background render: start it, then drain what it posted."""

    request: AnyRequest
    _process: BaseProcess | None = field(default=None, repr=False)
    _events: Queue[RenderEvent] | None = field(default=None, repr=False)
    # The child always ends by posting one event, so an exit before any was drained means it died
    # unanswered.
    answered: bool = field(default=False, repr=False)

    def start(self) -> None:
        """Spawn the child and begin the render; raise RuntimeError if already started."""
        if self._process is not None:
            raise RuntimeError(
                "this RenderProcess has already been started; construct another one rather than "
                "restarting it, or its first render's events would be drained into the second"
            )
        context = multiprocessing.get_context("spawn")
        self._events = context.Queue()
        self._process = context.Process(
            target=_worker,
            args=(self.request, self._events),
            name=f"nanopnp-render-{Path(self.request.run).name}",
            daemon=True,
        )
        self._process.start()

    def drain(self) -> tuple[RenderEvent, ...]:
        """Return every event posted since the last call, oldest first."""
        if self._events is None:
            return ()
        found: list[RenderEvent] = []
        while True:
            try:
                found.append(self._events.get_nowait())
            except queue_module.Empty:
                self.answered = self.answered or bool(found)
                return tuple(found)

    @property
    def running(self) -> bool:
        """Whether the child is alive."""
        return self._process is not None and self._process.is_alive()

    def terminate(self, timeout: float = 1.0) -> None:
        """Stop the child and wait for it to go, killing it after ``timeout`` seconds.

        A superseded render must stop before a new one sweeps the shared ``viewer/`` directory.
        """
        if self._process is None:
            return
        if self._process.is_alive():
            self._process.terminate()
        self._process.join(timeout)
        if self._process.is_alive():
            self._process.kill()
            self._process.join(timeout)

    def join(self, timeout: float | None = None) -> None:
        """Wait for the child to exit."""
        if self._process is not None:
            self._process.join(timeout)

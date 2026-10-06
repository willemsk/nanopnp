"""The field viewer's render side: one spawned process, one scene, written as a file.

The viewer draws a **live** ``GridFunction``, which is what ``ngsolve.webgui``
takes, and a live grid function exists only in a process that has NGSolve loaded
and a mesh built. So this module is a second child alongside
:mod:`nanopnp.gui.solver`'s, and the shell holds neither.

**The state is restored through the stage-10 gate, not read out of an export.**
:func:`nanopnp.solve.state.restore` rebuilds the space, the model and the
residual from the stored coefficient record and *refuses* a record that does not
describe this case, this mesh, this discretisation and this model. It is a gate
and never an adaptation, so what is drawn is the operator that was actually
solved. The IF-07 XDMF pair is a P2 node set written for a reader like ParaView;
drawing from it would put an interpolation between the solve and the picture, and
would make the viewer unable to say which solve it was showing.

**The scene crosses as a file.** A ``webgui`` scene is a plain dict of numbers
and base64 strings costing 193 B per element at order 1 and 321 B at order 2, so
a scene of the 120,917-triangle reference mesh is 23 to 39 MB
(`.knowledge/07-software-stack.md` §5). That does not belong on a
:class:`multiprocessing.Queue` polled every 100 ms, and it does not belong in
``QWebEngineView.setHtml``, which percent-encodes its argument into a data URL.
What crosses the queue is a path.

**Two files are written per field and only one field is kept.** The scene is
written as JSON — the data, round-trippable and inspectable — and the host
document embeds the same JSON rather than fetching it as a subresource, because
whether Chromium permits a ``file://`` document to load a ``file://`` subresource
is a policy question that cannot be settled on a machine where Qt WebEngine
cannot be constructed at all, and a document that silently failed to load its
data is exactly the blank panel QR-12 is written against. That costs two copies,
so the previous field's pair is removed when a new one is rendered: this is a
display artefact, not a cache. Collapsing the two into one subresource load is a
one-line change for whoever can watch the picture draw. The embedded copy differs
from the file by one escape — ``</`` inside a script element would end it in the
parser — which ``JSON.parse`` and the JavaScript literal both read back as what
the file holds; see :func:`host_document`.

**We build the host document ourselves.** ``netgen.webgui.GenerateHTML`` takes a
``template`` argument, assigns it and then substitutes into the module global
regardless (`.knowledge/07-software-stack.md` §5, **[verified]**), so a caller
cannot redirect the renderer through it. The document is a stylesheet, a script
tag and four lines of initialisation; building it is what makes the renderer
source a single constant.

**The charge picture is the coefficient the solve assembles** (WP31 D7). The
deployed ``rho`` and the stage-7 ``chi`` are drawn through
:func:`deployed_coefficient`, which reaches them by the solve's own route: the
deployed mesh, then :func:`~nanopnp.charge.stage.case_fields` on the stage-7
artefact the run recorded. Neither is re-deposited or re-derived, and neither
picture is an artefact. ``rho`` is drawn on ``[-L, L]``, ``L`` the largest
magnitude the scene samples, so zero sits at the centre of the colour map and
a neutral region never reads as charged (D8); ``chi`` on ``[0, 1]``, fixed.

**Nothing here names a field or a unit.** The vocabulary is
:func:`nanopnp.io.fields.attribute_name` and the §6.3 scale table beside it —
the same two the IF-07 export uses, so the viewer and the file cannot disagree
about what a number means.
"""

from __future__ import annotations

import json
import logging
import multiprocessing
import queue as queue_module
from dataclasses import dataclass, field, replace
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Literal, TypeAlias

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from multiprocessing.process import BaseProcess
    from multiprocessing.queues import Queue

    from nanopnp.core.typing import Expression, Mesh
    from nanopnp.io.artefact import Artefact
    from nanopnp.io.case import ResolvedCase
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

RENDERER_VERSION = "0.2.39"
"""The npm ``webgui`` version shipped beside this module.

The version ``netgen.webgui``'s own template pins for the NGSolve release in the
lock, because the scene :meth:`WebGLScene.GetData` emits is that renderer's input
format and nothing else's. ``tests/tier1/test_gui_render.py`` reads the pin out of
the installed ``netgen/webgui.py`` and fails when an upgrade moves it.
"""

RENDERER_INTEGRITY = (
    "sha512-"
    "yDd6YR7EjHGfeUC+rbn6/WvTWWkwJSU1KcsqWYzP5qJyN3IN9ax2vuUROvn8epKRKtuerLJ2qTSPp8A1yZubqw=="
)
"""npm's published ``dist.integrity`` for :data:`RENDERER_VERSION`'s tarball.

The vendored tarball in ``third_party/`` is checked against it, and the shipped
``webgui.js`` against that tarball, so what is drawn with is what npm published.
"""

RENDERER_DIRECTORY = Path(__file__).resolve().parent / "assets" / "webgui"
"""Where the renderer, its three licence texts and its NOTICE are installed.

Package data, so it travels in the wheel and is collected into the bundle; the
bundle's PyInstaller recipe puts it at the same path relative to this module.
"""

RENDERER_SOURCE = (RENDERER_DIRECTORY / "webgui.js").as_uri()
"""The ``file:`` URL the host document loads the renderer from.

Shipped, not fetched (WP15 OQ-1; CON-09): the npm
``webgui`` build is LGPL-2.1-or-later and bundles three.js (MIT) and dat.gui
(Apache-2.0), redistributed unmodified as a separate file beside their licence
texts and a NOTICE naming the corresponding source. A document fetching from a
CDN drew nothing on a machine with no route to it and reported ``loadFinished``
anyway; this one needs no network. It is still one constant behind
:func:`renderer_source`, and :func:`readiness_script` still asks the page whether
it arrived, because an installation missing the file is a blank panel too.
"""

VIEWER_DIRNAME = "viewer"
"""Subdirectory of a run directory the scene and its document are written into.

Never registered as an artefact and never hashed. §5.3.2's "a cancelled run
writes no artefact" has to keep meaning what it says, and a picture of a
converged state is not a result — it is a view of one.
"""

MESH_SCENE_STEM = "mesh"
"""Stem of the stage-6 mesh's scene and document under ``viewer/`` (WP24 D12).

Not ``scene-*``, so a field render's sweep of its own previous pair leaves the
mesh picture alone, and the other way round."""

ChargeQuantity: TypeAlias = Literal["charge", "chi"]
"""What the charge tab's deployed picture shows: the fixed charge or the solid fraction.

Each is also the stem of its pair under ``viewer/`` (WP31 D7)."""

CHI_RANGE = (0.0, 1.0)
"""The colour range of a ``chi`` picture, fixed: a solid fraction lies in [0, 1]
(VER-30's range gate), so a scale that followed the data would make a field
held at 1 look like one that varies (WP31 D8)."""

READY_FLAG = "__nanopnp_viewer"
"""Name of the global the document sets while it tries to draw.

Read back by the viewer widget's readiness probe. ``loadFinished`` is a statement
about the *document*: Qt reaches ``loadFinished(True)`` on a page whose renderer
never arrived, with nothing but ``webgui is not defined`` in a console nobody
sees (`.knowledge/07-software-stack.md` §5). This global is the statement about
the picture.

It carries ``renderer_loaded`` **separately from** ``error``, recorded before the
scene is built, because a missing renderer and a scene that threw are one
exception otherwise: ``new webgui.Scene()`` on a page whose script never arrived
raises ``ReferenceError: webgui is not defined``, which is indistinguishable from
a genuine failure inside the renderer unless the document says which it was. The
two want different diagnostics — one names a source to reach, the other names a
scene to fix — so the document answers the question rather than leaving the panel
to parse an exception message for the word ``webgui``.
"""

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
"""The host document. One rendering path, ours, with the renderer as its variable.

A :class:`string.Template` and not ``str.format``: the house rule is f-strings
and never ``.format()``, and a template that is mostly CSS and JavaScript cannot
be an f-string. ``$``-substitution also leaves every brace below as itself,
where ``.format`` needed each one doubled and would raise on the first one added
to the stylesheet without its pair."""


def renderer_source() -> str:
    """Return the address the host document loads the renderer from.

    A function and not a bare read of :data:`RENDERER_SOURCE` so that the
    viewer, the probe and the tests all read the source from one place.
    """
    return RENDERER_SOURCE


def readiness_script() -> str:
    """Return the JavaScript the viewer evaluates once the document has loaded.

    Returns a JSON object, never a bare boolean: a probe that could only say
    "not ready" would leave the panel unable to distinguish a renderer that
    never arrived from a scene that threw while initialising, and those want
    different diagnostics (QR-12).
    """
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
        The document title; the field's own attribute name, which comes from
        :func:`nanopnp.io.fields.attribute_name` and never from this package.
    """
    return _DOCUMENT.substitute(
        title=title,
        renderer=renderer,
        renderer_literal=json.dumps(renderer),
        # ``json.dumps`` does not escape ``/``, so a ``</script>`` anywhere in a
        # scene's strings would close this element in the parser before the
        # assignment completed — a page that loads, sets no flag, and is
        # reported as a renderer that never arrived. The escape is invisible to
        # ``JSON.parse`` and to the JavaScript literal alike.
        scene=scene.replace("</", "<\\/"),
        flag=READY_FLAG,
    )


# -- what crosses the boundary ------------------------------------------------


@dataclass(frozen=True)
class RenderRequest:
    """What the child is asked for: a finished run, and one field of it.

    Parameters
    ----------
    run
        The run directory, holding ``run.json`` and ``case.yaml``.
    field
        The field's attribute name, or ``""`` for the model's first field. The
        vocabulary is :func:`nanopnp.io.fields.attribute_name`'s, so a name the
        shell offers is a name the export writes.
    renderer
        The URL the document loads the renderer from.
    """

    run: str
    field: str = ""
    renderer: str = RENDERER_SOURCE


@dataclass(frozen=True)
class Rendered:
    """A scene was written, and this is where it is.

    Parameters
    ----------
    document
        The host document, to be loaded as a **file** URL.
    scene
        The scene JSON beside it.
    field
        The attribute name that was drawn.
    fields
        Every attribute name this solution offers, in the model's own field
        order. The viewer's selector is exactly this and nothing else.
    elements
        How many elements the drawn region carried, recorded so that a scene's
        size is attributable.
    """

    document: str
    scene: str
    field: str
    fields: tuple[str, ...]
    elements: int


@dataclass(frozen=True)
class RenderFailed:
    """Nothing was drawn, and this is why.

    The message is the diagnostic as the gate or the reader wrote it — a
    :class:`~nanopnp.solve.state.StateMismatchError` already names the first key
    that differs and both values (QR-12), and restating it here would be a second
    wording of one fact.
    """

    error: str
    message: str


@dataclass(frozen=True)
class MeshRequest:
    """What the child is asked for by the geometry tab: a run's stage-6 mesh (WP24 D12).

    Parameters
    ----------
    run
        The run directory, holding ``run.json`` and ``case.yaml``; a walk
        through stage 6 writes one, ``--upto mesh`` included.
    renderer
        The URL the document loads the renderer from.
    """

    run: str
    renderer: str = RENDERER_SOURCE


@dataclass(frozen=True)
class RenderedMesh:
    """The mesh was drawn, by material, and this is where, beside what its gates measured.

    Parameters
    ----------
    document, scene
        The host document and the scene JSON under the run's ``viewer/``.
    elements
        Triangles drawn: the mesh file's own count.
    materials
        The mesh's materials, in the order their colour index follows.
    quality
        VER-10's figures: the least SICN and gamma, the floor, and the ``(r, z)``
        centroid of the element holding each least value, in the model frame.
    wall
        Stage 6's wall-size gate statistics, as its artefact recorded them; empty
        for a supplied mesh, which is not generated and has no such gate.
    """

    document: str
    scene: str
    elements: int
    materials: tuple[str, ...]
    quality: dict[str, object]
    wall: dict[str, object]


@dataclass(frozen=True)
class ChargeRequest:
    """What the charge tab asks for: a run's deployed charge or ``chi`` (WP31 D7).

    Parameters
    ----------
    run
        The run directory, holding ``run.json`` and ``case.yaml``; a walk
        through stage 7 writes one, ``--upto charge`` included.
    quantity
        ``"charge"`` for the fixed volume charge density, ``"chi"`` for the
        solid fraction.
    renderer
        The URL the document loads the renderer from.
    """

    run: str
    quantity: ChargeQuantity = "charge"
    renderer: str = RENDERER_SOURCE


@dataclass(frozen=True)
class RenderedCharge:
    """The deployed coefficient was drawn, and this is where, on what scale.

    Parameters
    ----------
    document, scene
        The host document and the scene JSON, ``viewer/<quantity>.*``.
    quantity
        What was drawn.
    name, units
        The quantity's name and unit: IF-07's
        :data:`~nanopnp.io.fields.FIXED_CHARGE_ATTRIBUTE` in C m^-3, or the
        solid fraction, dimensionless.
    colour_range
        The fixed ``(min, max)`` of the colour map: ``(-L, L)`` for the charge,
        :data:`CHI_RANGE` for ``chi`` (D8).
    limit
        ``L``, the largest magnitude the scene samples, printed beside the
        picture; for ``chi`` the largest value sampled.
    elements
        Triangles drawn: the whole deployed mesh.
    materials
        The mesh's materials, so a generated exclusion shell is named.
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
"""Everything the render child may post. Frozen, picklable and plain."""


# -- the child ----------------------------------------------------------------


def _state_path(run: Path) -> Path:
    """Return the stage-10 payload the run recorded, or say why there is none.

    Raises
    ------
    FileNotFoundError
        If the run directory has no record, if the run never reached the solve,
        or if the artefact the record names is not in the store any more. Each
        is a different sentence, because each has a different remedy.
    """
    from nanopnp.io.run import RUN_RECORD_FILENAME
    from nanopnp.io.store import Store
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
    """Return the artefact the run recorded for ``stage``, or ``None`` if it recorded none.

    A run on a generated mesh is restored onto the file stage 6 wrote, which is
    that artefact's payload (WP21 D12), and a producer case's deposited charge is
    read from its stage-7 artefact and never re-deposited (WP28 D9); a run on a
    supplied mesh or field re-reads ``inputs:`` and needs neither.
    :func:`_state_path` has already checked the record and the store, so a missing
    entry here is a run that recorded no such stage.

    Parameters
    ----------
    needed
        What the restore reads from the artefact, as the refusal names it, when it
        reads it; ``None`` when the restore can do without it.

    Raises
    ------
    FileNotFoundError
        If the artefact is ``needed`` and has been removed from the store, as
        :func:`_state_path` refuses a removed state. Without this a removed
        stage-7 artefact would reach the restore as none at all, which refuses it
        as a run that never reached stage 7.
    """
    from nanopnp.io.run import RUN_RECORD_FILENAME
    from nanopnp.io.store import Store

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
    """Return what a case reads from its stage-7 artefact, as a refusal names it, or ``None``.

    A deposited charge and a derived ``chi`` are read from that artefact and from
    nowhere else (WP28 D9, WP30 D5); a supplied field is re-read from ``inputs:``.
    """
    if resolved.deposits_charge:
        return "a deposited charge"
    if resolved.derives_eps_r:
        return "a derived solid fraction"
    return None


def _write_scene(
    run: Path, stem: str, scene: dict[str, object], *, renderer: str, title: str
) -> tuple[Path, Path]:
    """Write a scene and its host document to ``viewer/<stem>.*``, each through a rename.

    Returns
    -------
    tuple
        The scene's path and the document's path.
    """
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
    """Return how many elements the drawn region carries.

    ``mesh.ne`` is the whole mesh, and every field but the potential declares a
    ``domain`` — Nernst-Planck and the flow are solved on the fluid only
    (PHY-03) — so a concentration's picture holds strictly fewer elements than
    the mesh does. Counting the region is what makes :attr:`Rendered.elements`
    attributable to the scene's size rather than to the mesh's.

    Counted through the material mask, as
    :func:`nanopnp.io.fields.p2_nodes` counts the same restriction for the
    IF-07 export, so the picture and the file agree about what was drawn. The
    mask has one bit per *material*, so its ``NumSet()`` is not the count; the
    elements' own 1-based material indices are looked up in it as an array,
    rather than by a Python loop over some 121k elements on every render.
    """
    import numpy as np

    if domain is None:
        return int(mesh.ne)
    keep = mesh.Materials(domain).Mask()
    wanted = np.array([keep[index] for index in range(len(keep))], dtype=bool)
    materials = np.asarray(mesh.ngmesh.Elements2D().NumPy()["index"], dtype=np.int64) - 1
    return int(np.count_nonzero(wanted[materials]))


def _replace(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` through a sibling, so the move is atomic.

    A render is superseded whenever the panel is repointed at another field, and
    a child stopped part-way through a multi-megabyte write would otherwise
    leave a truncated document for the next load to find — a blank panel whose
    diagnostic would name the renderer rather than the write (QR-12).
    """
    part = path.with_name(f"{path.name}.part")
    part.write_text(text, encoding="utf-8")
    part.replace(path)


def render(request: RenderRequest) -> Rendered:
    """Restore a finished run and write one field's scene into its ``viewer/``.

    Parameters
    ----------
    request
        The run, the field and the renderer source.

    Returns
    -------
    Rendered
        The paths written and the field vocabulary this solution offers.

    Raises
    ------
    FileNotFoundError
        If the run directory records no converged state; see :func:`_state_path`.
    nanopnp.solve.state.StateMismatchError
        If the stored record does not describe this case. Allowed to propagate
        with the gate's own message: a viewer that adapted a mismatched state
        would draw a picture of an operator nobody solved.
    KeyError
        If ``field`` names an attribute this solution does not carry; the
        message lists the ones it does.
    """
    from nanopnp.io.case import load_case, resolve
    from nanopnp.io.fields import attribute_name, field_scale
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.solve.state import restore

    run = Path(request.run)
    state = _state_path(run)
    case = load_case(run / CASE_FILENAME)
    resolved = resolve(case)
    solution = restore(
        state,
        case=case,
        mesh_artefact=_recorded_artefact(
            run, "mesh", needed="a generated mesh" if case.inputs.mesh is None else None
        ),
        charge_artefact=_recorded_artefact(run, "charge", needed=_stage7_need(resolved)),
    )
    # Any model: each reports the NUM-09 scale set that turns its nondimensional
    # state into the SI numbers the attribute names promise (section 5.4.3).
    model = solution.model
    # The model's own declaration, named by the export's own vocabulary. A
    # "number"-element field is a scalar unknown with no spatial extent, so there
    # is nothing to draw of it.
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
    # Restricted to the region the field is defined on, exactly as the IF-07
    # export restricts it. Drawn over the whole mesh, a concentration would be
    # zero inside the membrane and a reader could not tell that from a converged
    # depletion.
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
    # One field's pair at a time: at the reference mesh size each copy is tens of
    # megabytes, and this is a display artefact rather than a cache.
    for stale in directory.glob("scene-*"):
        if stale not in (scene_path, document_path) and stale.is_file():
            stale.unlink()
    # Written beside and moved into place, so that a render stopped part-way
    # through — the panel supersedes one whenever a field is reselected — leaves
    # no half-written document for the next load to find. A ``.part`` left by a
    # killed child is swept by the loop above on the next render.
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
    """Draw a run's stage-6 mesh by material into its ``viewer/``, with its gate figures (WP24 D12).

    The mesh is read through :func:`~nanopnp.mesh.ingest.deployed_mesh`, the
    route every consumer of a run's mesh takes, so what is drawn is what stage 7
    and the solve read. Colour is the material's index in the mesh's own order:
    the pore wall is 0.05 nm against a 250 nm reservoir, and ``webgui``'s zoom
    is what spans that, so a picture by material is what shows the junction.

    Raises
    ------
    FileNotFoundError
        If the run records no stage-6 artefact, or it has left the store.
    """
    from nanopnp.io.case import load_case, resolve
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.mesh.ingest import deployed_mesh

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
    """A run's deployed charge or ``chi``, as the solve assembles it (WP31 D7).

    Parameters
    ----------
    mesh
        The deployed mesh.
    coefficient
        ``rho`` in C m^-3, or ``chi``.
    measures
        The solve's quadrature policy, at its element order: the order the
        picture samples at, and the one its charge is integrated at.
    name, units
        As :class:`RenderedCharge` names them.
    """

    mesh: Mesh
    coefficient: Expression
    measures: Measures
    name: str
    units: str


def deployed_coefficient(run: Path, quantity: ChargeQuantity) -> DeployedCoefficient:
    """Return the coefficient a run's solve reads for ``quantity``, on its deployed mesh.

    The route :func:`nanopnp.solve.state.restore` takes: the deployed mesh, then
    :func:`~nanopnp.charge.stage.case_fields` over the supplied fields and the
    stage-7 artefact the run recorded. A producer's charge and a derived ``chi``
    are read from that artefact and from nowhere else (WP28 D9, WP30 D5).

    Raises
    ------
    FileNotFoundError
        If the run records no stage-6 or stage-7 artefact it needs, or one has
        left the store.
    KeyError
        If the run carries no such coefficient: no fixed charge, or a sharp
        permittivity per material with no ``chi`` at all.
    """
    from nanopnp.charge.dielectric import SOLID_FRACTION
    from nanopnp.charge.fields import CANONICAL_UNITS
    from nanopnp.charge.stage import case_fields, read_fields
    from nanopnp.io.case import load_case, resolve
    from nanopnp.io.fields import FIXED_CHARGE_ATTRIBUTE
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.mesh.ingest import deployed_mesh
    from nanopnp.numerics.measures import AXISYMMETRIC

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
    measures = replace(AXISYMMETRIC, element_order=order)
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
    """Draw a run's deployed charge or ``chi`` into its ``viewer/`` (WP31 D7, D8).

    Raises
    ------
    FileNotFoundError, KeyError
        As :func:`deployed_coefficient` raises them.
    """
    run = Path(request.run)
    deployed = deployed_coefficient(run, request.quantity)

    from ngsolve.webgui import Draw

    mesh = deployed.mesh
    scene = Draw(
        deployed.coefficient, mesh, show=False, order=deployed.measures.element_order
    ).GetData()
    # The extremes webgui sampled are what is drawn; the range is then fixed,
    # so the viewer's autoscale cannot move zero off the centre (D8).
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
"""Everything the render child may be asked for."""


def _worker(request: AnyRequest, events: Queue[RenderEvent]) -> None:
    """Render one scene and post where it went, or why it did not.

    Never raises, for the reason :func:`nanopnp.gui.solver._worker` gives: an
    exception that escaped would leave the parent waiting on a queue that will
    never carry another event.
    """
    try:
        if isinstance(request, MeshRequest):
            events.put(render_mesh(request))
        elif isinstance(request, ChargeRequest):
            events.put(render_charge(request))
        else:
            events.put(render(request))
    except BaseException as error:
        events.put(RenderFailed(error=type(error).__qualname__, message=str(error)))


# -- the parent ---------------------------------------------------------------


@dataclass
class RenderProcess:
    """One background render: start it, drain what it said.

    Polled rather than awaited, like :class:`~nanopnp.gui.solver.SolverProcess`,
    so the object is driven identically by a Qt timer and by a test. There is no
    *cooperative* cancellation: a render is one ``GetData`` and one write, and a
    token checked between them would stop nothing. :meth:`terminate` is the
    other thing, and it is not a nicety — two children of one run write into one
    ``viewer/`` directory and each sweeps the other's files away, so a render
    whose answer is no longer wanted has to be stopped rather than left to
    finish.
    """

    request: AnyRequest
    _process: BaseProcess | None = field(default=None, repr=False)
    _events: Queue[RenderEvent] | None = field(default=None, repr=False)
    answered: bool = field(default=False, repr=False)
    """Whether :meth:`drain` has ever returned an event.

    The child always ends by posting one, a scene or a refusal, so a child that has
    exited while this is still false died without answering and the caller must say
    so (CODE_REVIEW_003 CR-7).
    """

    def start(self) -> None:
        """Spawn the child and begin the render.

        Raises
        ------
        RuntimeError
            If this process has already been started; construct another one
            rather than restarting it.
        """
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
        """Stop the child and wait briefly for it to go.

        For a render that has been superseded. Two children of one run write
        into the same ``viewer/`` directory and each removes the ``scene-*``
        pair it did not write, so a superseded render left to finish can delete
        the document the panel has just been told to load. Waiting rather than
        signalling and returning is what makes "the old child is gone" true
        before the new one sweeps the directory. A child that outlives
        ``timeout`` after SIGTERM, stuck in a long NGSolve call that does not
        return to the interpreter, is killed and waited for again: returning
        with it alive would let it race the new one after all.

        Idempotent, and a no-op on a child that has already exited.
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

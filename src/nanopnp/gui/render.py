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
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from multiprocessing.process import BaseProcess
    from multiprocessing.queues import Queue

    from nanopnp.core.typing import Mesh
    from nanopnp.io.artefact import Artefact

logger = logging.getLogger(__name__)

__all__ = [
    "READY_FLAG",
    "RENDERER_DIRECTORY",
    "RENDERER_INTEGRITY",
    "RENDERER_SOURCE",
    "RENDERER_VERSION",
    "VIEWER_DIRNAME",
    "RenderFailed",
    "RenderProcess",
    "RenderRequest",
    "Rendered",
    "host_document",
    "readiness_script",
    "render",
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

Shipped, not fetched (WP15 OQ-1, ruled 22 September 2026; CON-09): the npm
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


RenderEvent: TypeAlias = Rendered | RenderFailed
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


def _mesh_artefact(run: Path) -> Artefact | None:
    """Return the stage-6 artefact the run recorded, or ``None`` if it recorded none.

    A run on a generated mesh is restored onto the file stage 6 wrote, which is
    that artefact's payload (WP21 D12); a run on a supplied mesh re-reads
    ``inputs.mesh`` and needs none. :func:`_state_path` has already checked the
    record and the store, so a missing entry here is a run that recorded no mesh.
    """
    from nanopnp.io.run import RUN_RECORD_FILENAME
    from nanopnp.io.store import Store

    record = json.loads((run / RUN_RECORD_FILENAME).read_text(encoding="utf-8"))
    mesh = record.get("artefacts", {}).get("mesh")
    root = record.get("store")
    if mesh is None or root is None:
        return None
    return Store(Path(root)).get(str(mesh["schema"]), str(mesh["hash"]))


def _element_count(mesh: Mesh, domain: str | None) -> int:
    """Return how many elements the drawn region carries.

    ``mesh.ne`` is the whole mesh, and every field but the potential declares a
    ``domain`` — Nernst-Planck and the flow are solved on the fluid only
    (PHY-03) — so a concentration's picture holds strictly fewer elements than
    the mesh does. Counting the region is what makes :attr:`Rendered.elements`
    attributable to the scene's size rather than to the mesh's.

    Counted through the material mask, as
    :func:`nanopnp.io.fields.p2_nodes` counts the same restriction for the
    IF-07 export, so the picture and the file agree about what was drawn.
    """
    import ngsolve as ngs

    if domain is None:
        return int(mesh.ne)
    keep = mesh.Materials(domain).Mask()
    return sum(1 for element in mesh.Elements(ngs.VOL) if keep[element.index])


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
    from nanopnp.io.case import load_case
    from nanopnp.io.fields import attribute_name, field_scale
    from nanopnp.io.manifest import CASE_FILENAME
    from nanopnp.physics.models import CoupledModel
    from nanopnp.solve.state import restore

    run = Path(request.run)
    solution = restore(
        _state_path(run), case=load_case(run / CASE_FILENAME), mesh_artefact=_mesh_artefact(run)
    )
    model = solution.model
    if not isinstance(model, CoupledModel):
        # The same refusal stage 12 makes for the IF-07 export, for the same
        # reason: the NUM-09 scale set is what turns the nondimensional state
        # into the SI numbers the attribute names promise, and a model that
        # declares none has no SI picture to draw.
        raise TypeError(
            f"{model.name!r} declares no scale set, so its fields cannot be drawn in the SI units "
            "their names carry"
        )
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


def _worker(request: RenderRequest, events: Queue[RenderEvent]) -> None:
    """Render one scene and post where it went, or why it did not.

    Never raises, for the reason :func:`nanopnp.gui.solver._worker` gives: an
    exception that escaped would leave the parent waiting on a queue that will
    never carry another event.
    """
    try:
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

    request: RenderRequest
    _process: BaseProcess | None = field(default=None, repr=False)
    _events: Queue[RenderEvent] | None = field(default=None, repr=False)

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
        before the new one sweeps the directory.

        Idempotent, and a no-op on a child that has already exited.
        """
        if self._process is None:
            return
        if self._process.is_alive():
            self._process.terminate()
        self._process.join(timeout)

    def join(self, timeout: float | None = None) -> None:
        """Wait for the child to exit."""
        if self._process is not None:
            self._process.join(timeout)

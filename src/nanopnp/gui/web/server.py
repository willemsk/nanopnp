"""The workbench's local server: loopback only, one ready line, a token, stops with its input."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import signal
import socket
import sys
import tempfile
import threading
import time
import webbrowser
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from http import cookies
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

import uvicorn
from fastapi import FastAPI

from nanopnp.api.project import Project
from nanopnp.core.public import __version__
from nanopnp.gui.web import settings
from nanopnp.gui.web.builds import cancel_builds
from nanopnp.gui.web.pages import install
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.states import STATES, Workbench, boot, boot_case, boot_project, cap_store

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from nanopnp.gui.solver import SolverProcess

__all__ = [
    "COOKIE",
    "HOST",
    "READY",
    "Guard",
    "build_app",
    "main",
    "open_last_project",
    "serve",
    "track",
]

HOST = "127.0.0.1"
"""The only interface the server binds (ADR-004's NOTE, the desktop wrapper)."""

READY = re.compile(r"^nanopnp-gui ready (http://127\.0\.0\.1:\d+/\?token=[\w-]+)$")
"""The one line a wrapper reads from standard output to learn the address."""

COOKIE = "nanopnp_token"
"""The prefix of the launch cookie's name, which ``Guard`` completes with a digest of the token."""


def open_last_project() -> bool:
    """Whether the workbench opens the last project when it starts without one."""
    return bool(settings.load().value("open_last_project"))


def _ready_line(url: str, *, as_json: bool) -> str:
    return json.dumps({"ready": url}) if as_json else f"nanopnp-gui ready {url}"


_FORBIDDEN = b"forbidden: a foreign Host, or neither the launch token nor its cookie"
_CHILDREN: list[SolverProcess] = []


def track(process: SolverProcess) -> None:
    """Register a running solve, so the server cancels it when it stops."""
    _CHILDREN.append(process)


def _stop_children() -> None:
    for process in _CHILDREN:
        if process.running:
            process.cancel()
    _CHILDREN.clear()
    cancel_builds()


class Guard:
    """ASGI middleware: refuse a foreign Host, and a request without the launch token.

    A page opened with ``?token=`` receives the token as an ``HttpOnly``, ``SameSite=Strict``
    cookie, so that its later requests and its websocket carry it without the query. The cookie's
    name carries a digest of the token: a browser keeps one cookie per name for every port of
    127.0.0.1, so two workbenches sharing a name would overwrite each other's token.
    """

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token
        self.cookie = f"{COOKIE}_{hashlib.sha256(token.encode()).hexdigest()[:12]}"
        self.hosts: frozenset[str] = frozenset()

    def _is_token(self, candidate: str) -> bool:
        # Bytes, because compare_digest refuses a str outside ASCII, and a request may send any.
        return hmac.compare_digest(candidate.encode(), self.token.encode())

    # Returns (allowed, set_cookie).
    def _allowed(self, scope: Scope) -> tuple[bool, bool]:
        headers = {key.lower(): value for key, value in scope["headers"]}
        if headers.get(b"host", b"").decode("latin-1") not in self.hosts:
            return False, False
        query = parse_qs(scope["query_string"].decode("latin-1")).get("token", [""])[0]
        if self._is_token(query):
            return True, True
        jar: cookies.SimpleCookie = cookies.SimpleCookie()
        jar.load(headers.get(b"cookie", b"").decode("latin-1"))
        morsel = jar.get(self.cookie)
        return morsel is not None and self._is_token(morsel.value), False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass an allowed request on; answer any other with 403."""
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        allowed, set_cookie = self._allowed(scope)
        if not allowed:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
                return
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                }
            )
            await send({"type": "http.response.body", "body": _FORBIDDEN})
            return
        if not set_cookie or scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def with_cookie(message: Message) -> None:
            if message["type"] == "http.response.start":
                value = f"{self.cookie}={self.token}; HttpOnly; SameSite=Strict; Path=/"
                message = {
                    **message,
                    "headers": [*message["headers"], (b"set-cookie", value.encode())],
                }
            await send(message)

        await self.app(scope, receive, with_cookie)


def build_app(token: str, bench: Workbench) -> Guard:
    """Return the FastAPI app, with the screens of ``bench`` installed, behind its guard.

    The guard learns its allowed Host values once the port is bound, so the caller sets
    ``guard.hosts`` before serving.
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        _stop_children()

    app = FastAPI(title="nanopnp workbench", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Say that the server is up, and which version of nanopnp runs it."""
        return {"status": "ok", "version": __version__}

    install(app, Shell(bench), token)
    return Guard(app, token)


# A uvicorn server that announces the address it bound, once, on standard output.
class _Server(uvicorn.Server):
    def __init__(
        self, config: uvicorn.Config, guard: Guard, token: str, *, browser: bool, as_json: bool
    ) -> None:
        super().__init__(config)
        self._json = as_json
        self._guard = guard
        self._token = token
        self._browser = browser

    # Bind, then name the address (ADR-004's NOTE describes the wrapper that reads it).
    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets)
        if not self.started:
            return
        port = self.servers[0].sockets[0].getsockname()[1]
        self._guard.hosts = frozenset({f"{HOST}:{port}", f"localhost:{port}"})
        url = f"http://{HOST}:{port}/?token={self._token}"
        print(_ready_line(url, as_json=self._json), flush=True)
        if self._browser:
            webbrowser.open(url)


ANNOUNCE_WAIT_S = 60.0
"""How long ``--dev`` waits for its address to accept a connection before it prints nothing."""

_DEV_ENVIRONMENT = (
    "NANOPNP_GUI_TOKEN",
    "NANOPNP_GUI_WORK",
    "NANOPNP_GUI_CASE",
    "NANOPNP_GUI_STATE",
    "NANOPNP_GUI_PROJECT",
    "NANOPNP_GUI_WALK",
)


def _watch_input(server: uvicorn.Server | None) -> None:
    sys.stdin.read()
    if server is not None:
        server.should_exit = True
    else:
        os.kill(os.getpid(), signal.SIGINT)  # the reloading supervisor stops on it


def _boot(
    case: str | None,
    state: str | None,
    work: Path,
    project: str | None = None,
    *,
    walk: bool = False,
) -> Workbench:
    if project:
        opened = Project.open(project)
        if walk:
            return boot_project(opened)
        cap_store(opened)
        return Workbench(opened.name, project=opened)
    if case:
        return boot_case(Path(case), work)
    return boot(state or "empty", work)


def dev_app() -> Guard:
    """Return the app of a ``--dev`` worker, which the reloading supervisor starts afresh.

    The supervisor passes the launch token, the folder that keeps the store between reloads, and
    the case or state in environment variables.
    """
    token, work, case, state, project, walk = (os.environ.get(name) for name in _DEV_ENVIRONMENT)
    assert token is not None and work is not None
    guard = build_app(token, _boot(case, state, Path(work), project, walk=bool(walk)))
    port = int(os.environ["NANOPNP_GUI_PORT"])
    guard.hosts = frozenset({f"{HOST}:{port}", f"localhost:{port}"})
    return guard


def _announce(url: str, port: int, *, browser: bool, as_json: bool) -> None:
    # The reloading supervisor binds the port before its first worker has started, so the first
    # connection that succeeds is the earliest moment the address works; the ready line and the
    # browser wait for it, as the plain server's do for its bind.
    deadline = time.monotonic() + ANNOUNCE_WAIT_S
    while time.monotonic() < deadline:
        try:
            socket.create_connection((HOST, port), timeout=1.0).close()
        except OSError:
            time.sleep(0.1)
            continue
        print(_ready_line(url, as_json=as_json), flush=True)
        if browser:
            webbrowser.open(url)
        return


# Serve with reload: a change to a page, a style sheet or the bridge restarts the worker.
def _serve_dev(
    boot_environment: dict[str, str],
    port: int,
    token: str,
    work: Path,
    *,
    browser: bool,
    as_json: bool,
) -> None:
    if port == 0:  # a reloading server keeps one address, so it is chosen before the first worker
        with socket.socket() as probe:
            probe.bind((HOST, 0))
            port = probe.getsockname()[1]
    os.environ.update(
        NANOPNP_GUI_TOKEN=token,
        NANOPNP_GUI_WORK=str(work),
        NANOPNP_GUI_PORT=str(port),
        **boot_environment,
    )
    url = f"http://{HOST}:{port}/?token={token}"
    threading.Thread(
        target=_announce,
        args=(url, port),
        kwargs={"browser": browser, "as_json": as_json},
        daemon=True,
    ).start()
    threading.Thread(target=_watch_input, args=(None,), daemon=True).start()
    uvicorn.run(
        "nanopnp.gui.web.server:dev_app",
        factory=True,
        host=HOST,
        port=port,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],
        reload_includes=["*.py", "*.css", "*.js"],
        log_level="warning",
    )


def serve(
    *,
    case: Path | None = None,
    state: str | None = None,
    project: Path | None = None,
    walk: bool = False,
    port: int = 0,
    no_browser: bool = False,
    dev: bool = False,
    as_json: bool = False,
) -> int:
    """Serve the workbench on the loopback interface until standard input closes or a signal.

    The ready line goes to standard output once the address accepts a connection, as one JSON
    object ``{"ready": url}`` where ``as_json`` is set. A desktop wrapper starts the server with
    ``no_browser`` and port 0, reads that line, loads its address, and closes the standard input
    to stop the server. A ``project`` opens as it is, with nothing walked, unless ``walk`` takes
    its first study to the charge stage, as a fixture state does.
    """
    token = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="nanopnp-gui-") as work:
        if dev:
            boot_environment = {
                "NANOPNP_GUI_CASE": str(case or ""),
                "NANOPNP_GUI_STATE": state or "",
                "NANOPNP_GUI_PROJECT": str(project or ""),
                "NANOPNP_GUI_WALK": "1" if walk else "",
            }
            _serve_dev(
                boot_environment,
                port,
                token,
                Path(work),
                browser=not no_browser,
                as_json=as_json,
            )
            return 0
        opened = None if project is None else str(project)
        guard = build_app(token, _boot(str(case or ""), state, Path(work), opened, walk=walk))
        config = uvicorn.Config(guard, host=HOST, port=port, log_level="warning")
        server = _Server(config, guard, token, browser=not no_browser, as_json=as_json)
        threading.Thread(target=_watch_input, args=(server,), daemon=True).start()
        server.run()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``python -m nanopnp.gui.web.server``, the entry a desktop wrapper starts."""
    parser = argparse.ArgumentParser(prog="nanopnp gui", description=serve.__doc__)
    parser.add_argument("case", nargs="?", type=Path, help="a case file, walked to its charge")
    parser.add_argument("--state", choices=STATES, help="a fixture state in place of a case")
    parser.add_argument(
        "--project", type=Path, help="a project folder, opened with its first study walked"
    )
    parser.add_argument("--port", type=int, default=0, help="the port; 0 picks a free one")
    parser.add_argument("--no-browser", action="store_true", help="open no browser")
    parser.add_argument("--dev", action="store_true", help="reload on a change to the source")
    parser.add_argument("--json", action="store_true", help="write the ready line as JSON")
    args = parser.parse_args(argv)
    if args.case is not None and args.state is not None:
        parser.error("give a case file or --state, not both")
    if args.project is not None and (args.case is not None or args.state is not None):
        parser.error("give a project folder or a case file or --state, not more than one")
    return serve(
        case=args.case,
        state=args.state,
        project=args.project,
        walk=args.project is not None,
        port=args.port,
        no_browser=args.no_browser,
        dev=args.dev,
        as_json=args.json,
    )


if __name__ == "__main__":  # pragma: no cover - run as a script, never imported by a test
    sys.exit(main())
